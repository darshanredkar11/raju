from __future__ import annotations
import os, secrets, time
from collections import OrderedDict, deque
from typing import Annotated
from fastapi import FastAPI, Depends, Header, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, ConfigDict
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from pymongo import MongoClient
from gridfs import GridFSBucket
from pypdf import PdfReader
from io import BytesIO
import hashlib, re
from .auth import allowed_google_email, require_session_secret
from .cache import TTLCache
from .llm import generate_sales_draft, LLMConfigurationError
from .service import SalesPilot
from .research import search_market_sources, propose_markets_with_llm, MarketResearchConfigurationError, MarketResearchError
import httpx
from .validation import ValidationError

app=FastAPI(title="Sanjay Chemicals Sales Pilot",docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(SessionMiddleware,secret_key=require_session_secret(),same_site="lax",https_only=os.getenv("COOKIE_SECURE","true").lower()=="true",max_age=8*60*60)
oauth=OAuth()
if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    oauth.register(name="google",client_id=os.environ["GOOGLE_CLIENT_ID"],client_secret=os.environ["GOOGLE_CLIENT_SECRET"],server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",client_kwargs={"scope":"openid email profile"})
mongo=None; pilot=None; product_bucket=None
if os.getenv("MONGODB_URI"):
    mongo=MongoClient(os.environ["MONGODB_URI"],serverSelectionTimeoutMS=5000,connectTimeoutMS=5000,connect=False)
    db=mongo[os.getenv("MONGODB_DATABASE","sanjay_sales")]
    product_bucket=GridFSBucket(db,bucket_name="product_docs")
    pilot=SalesPilot(db["sales_records"],TTLCache(max_items=512,ttl_seconds=60))

_hits=OrderedDict()
def rate_limit(request:Request,key:str,limit:int=30,window:int=60):
    now=time.monotonic()
    if key not in _hits and len(_hits)>=1024: _hits.popitem(last=False)
    q=_hits.setdefault(key,deque())
    while q and q[0]<now-window:q.popleft()
    if len(q)>=limit: raise HTTPException(429,"Too many requests")
    q.append(now); _hits.move_to_end(key)

def current_user(request:Request):
    user=request.session.get("user")
    if not user: raise HTTPException(401,"Sign in with Google")
    return user

def require_csrf(request:Request,x_csrf_token:Annotated[str|None,Header()]=None):
    expected=request.session.get("csrf")
    if not expected or not x_csrf_token or not secrets.compare_digest(expected,x_csrf_token):raise HTTPException(403,"CSRF validation failed")

def get_pilot():
    if pilot is None:raise HTTPException(503,"MongoDB is not configured")
    return pilot

def get_product_document(svc, source_id):
    doc=svc.cache.get('product:'+source_id)
    if doc is None:
        doc=svc.collection.find_one({'_id':source_id,'type':'product_document'})
        if doc is not None: svc.cache.set('product:'+source_id,doc)
    return doc

class MarketInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    market:str=Field(min_length=2,max_length=120)
    rationale:str=Field(min_length=10,max_length=1500)
    evidence_url:str=Field(min_length=10,max_length=2048)
    confidence:float=Field(strict=True,ge=0,le=1)
class DraftInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    recipient:str=Field(min_length=3,max_length=254)
    subject:str=Field(min_length=1,max_length=180)
    body:str=Field(min_length=1,max_length=8000)
    source_ids:list[str]=Field(default_factory=list,max_length=20)
class GenerateInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    recipient:str=Field(min_length=3,max_length=254)
    product_facts:str=Field(default="",max_length=6000)
    source_ids:list[str]=Field(default_factory=list,max_length=20)
    buyer_context:str=Field(min_length=10,max_length=6000)
    goal:str=Field(default="request a short introductory conversation",max_length=300)

class MarketResearchInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    product_facts:str=Field(default="",max_length=6000)
    source_ids:list[str]=Field(default_factory=list,max_length=20)
    target_region:str=Field(default="Global",min_length=2,max_length=100)
    buyer_segments:str=Field(default="importers, distributors and manufacturers",min_length=3,max_length=300)

@app.get("/health")
def health():
    return {"ok":True,"database_configured":pilot is not None,"outbound_email_enabled":False}

@app.get("/",response_class=HTMLResponse)
def home():
    return HTMLResponse("""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sanjay Chemicals | Sales Desk</title><style>
body{font:16px system-ui;background:#f4f6f8;color:#18212b;margin:0}main{max-width:1000px;margin:auto;padding:24px}header,.panel{background:white;border:1px solid #e0e5ea;border-radius:14px;padding:20px;margin:14px 0}h1{margin:0 0 6px}small{color:#5d6b79}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}input,textarea,button{font:inherit;width:100%;box-sizing:border-box;padding:10px;margin:5px 0;border:1px solid #c8d0d8;border-radius:8px}textarea{min-height:100px}button{background:#173b57;color:white;border:0;cursor:pointer}button.secondary{background:#e9eef2;color:#18212b}.item{border-top:1px solid #e0e5ea;padding:12px 0;overflow-wrap:anywhere}.status{font-weight:600}#app{display:none}#msg{white-space:pre-wrap;color:#8a3100}</style></head><body><main><header><h1>Sanjay Chemicals · Sales Desk</h1><small>Market proposals and email drafts. Nothing is sent from this pilot.</small><p id="identity">Checking sign-in…</p><button id="login" onclick="location.href='/auth/google'">Continue with Google</button><button id="logout" class="secondary" style="display:none" onclick="logout()">Sign out</button></header><div id="app"><section class="panel"><h2>Product documents</h2><form id="productForm"><select name="kind" required><option value="catalogue">Catalogue</option><option value="TDS">TDS</option><option value="SDS">SDS</option></select><input type="file" name="file" accept="application/pdf,.pdf" required><button>Upload PDF</button></form><div id="products">No documents uploaded yet.</div><small>PDF text extraction only; scanned/image-only PDFs need OCR before use.</small></section><div class="grid"><section class="panel"><h2>Research markets</h2><form id="researchForm"><textarea name="product_facts" placeholder="Optional product facts if no document is selected" maxlength="6000"></textarea><input name="target_region" value="Global" placeholder="Target region" required maxlength="100"><input name="buyer_segments" value="importers, distributors and manufacturers" placeholder="Buyer segments" required maxlength="300"><button>Research and propose for approval</button></form><small>Uses external search results; each suggestion stays pending until approved.</small></section><section class="panel"><h2>Propose a market manually</h2><form id="marketForm"><input name="market" placeholder="Market / country" required maxlength="120"><textarea name="rationale" placeholder="Why this market fits the product portfolio" required minlength="10" maxlength="1500"></textarea><input name="evidence_url" type="url" placeholder="HTTPS evidence URL" required><input name="confidence" type="number" min="0" max="1" step="0.01" value="0.5" required><button>Submit for approval</button></form></section><section class="panel"><h2>Draft outreach</h2><form id="draftForm"><input name="recipient" type="email" placeholder="Buyer email" required maxlength="254"><textarea name="product_facts" placeholder="Optional: add verified product facts if no document is selected" maxlength="6000"></textarea><div id="selectedProducts"><small>Select uploaded documents below, or paste facts above.</small></div><textarea name="buyer_context" placeholder="Buyer and company context, including source evidence" required minlength="10" maxlength="6000"></textarea><input name="goal" value="Request a short introductory conversation" maxlength="300"><button>Generate draft for review</button></form></section></div><section class="panel"><h2>Pending approvals</h2><button class="secondary" onclick="loadPending()">Refresh</button><div id="pending"></div></section></div><p id="msg"></p></main><script>
let csrf='';const msg=t=>document.getElementById('msg').textContent=t;async function api(path,opts={}){opts.headers={...(opts.headers||{}),'Content-Type':'application/json'};if(csrf)opts.headers['X-CSRF-Token']=csrf;const r=await fetch(path,{...opts,credentials:'same-origin'});if(r.status===401){showSignedOut();throw Error('Sign in with Google first')}const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||('HTTP '+r.status));return d}
function showSignedOut(){document.getElementById('login').style.display='block';document.getElementById('logout').style.display='none';document.getElementById('app').style.display='none';document.getElementById('identity').textContent='Not signed in'}
async function boot(){try{const me=await api('/me');document.getElementById('identity').textContent='Signed in as '+me.user.email;document.getElementById('login').style.display='none';document.getElementById('logout').style.display='block';document.getElementById('app').style.display='block';await loadPending();await loadProducts()}catch(e){showSignedOut()}}
async function loadProducts(){try{const items=await api('/api/products');const root=document.getElementById('products');root.innerHTML='';if(!items.length){root.textContent='No documents uploaded yet.';return}for(const x of items){const label=document.createElement('label');label.style.display='block';const cb=document.createElement('input');cb.type='checkbox';cb.value=x._id;cb.style.width='auto';label.append(cb,document.createTextNode(' '+x.name+' · '+x.kind+' · '+x.pages+' pages'));root.append(label)}}catch(e){msg(e.message)}}
async function loadPending(){try{const items=await api('/api/pending');const root=document.getElementById('pending');root.innerHTML='';if(!items.length){root.textContent='Nothing waiting for approval.';return}for(const x of items){const el=document.createElement('div');el.className='item';const title=document.createElement('strong');title.textContent=x.type==='market_proposal'?'Market: '+x.market:'Email: '+x.subject;el.append(title);const detail=document.createElement('p');detail.textContent=x.type==='market_proposal'?x.rationale+' · confidence '+x.confidence+' · '+x.evidence_url:x.recipient+'\n'+x.body;el.append(detail);if(x.type==='email_draft'||x.type==='market_proposal'){const b=document.createElement('button');b.textContent='Approve '+(x.type==='market_proposal'?'market proposal':'exact email draft');b.onclick=async()=>{try{if(x.type==='market_proposal')await api('/api/markets/'+encodeURIComponent(x._id)+'/approve',{method:'POST',body:'{}'});else await api('/api/drafts/'+encodeURIComponent(x._id)+'/approve',{method:'POST',body:JSON.stringify({recipient:x.recipient,subject:x.subject,body:x.body})});msg('Approval recorded. No email was sent.');await loadPending()}catch(e){msg(e.message)}};el.append(b)}root.append(el)}}catch(e){msg(e.message)}}
document.getElementById('productForm').onsubmit=async e=>{e.preventDefault();try{const r=await fetch('/api/products/upload',{method:'POST',headers:{'X-CSRF-Token':csrf},body:new FormData(e.target),credentials:'same-origin'});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||('HTTP '+r.status));msg('Uploaded '+d.name+'; '+d.pages+' pages indexed.');e.target.reset();await loadProducts()}catch(x){msg(x.message)}};
document.getElementById('researchForm').onsubmit=async e=>{e.preventDefault();try{const f=Object.fromEntries(new FormData(e.target));f.source_ids=Array.from(document.querySelectorAll('#products input:checked')).map(x=>x.value);const d=await api('/api/markets/research',{method:'POST',body:JSON.stringify(f)});msg('Research completed: '+d.proposals.length+' market proposals queued. Verify the source links before approval.');await loadPending()}catch(x){msg(x.message)}};
document.getElementById('marketForm').onsubmit=async e=>{e.preventDefault();try{const f=Object.fromEntries(new FormData(e.target));f.confidence=Number(f.confidence);await api('/api/markets',{method:'POST',body:JSON.stringify(f)});msg('Market proposal saved for approval.');e.target.reset();await loadPending()}catch(x){msg(x.message)}};
document.getElementById('draftForm').onsubmit=async e=>{e.preventDefault();try{const f=Object.fromEntries(new FormData(e.target));f.source_ids=Array.from(document.querySelectorAll('#products input:checked')).map(x=>x.value);const d=await api('/api/drafts/generate',{method:'POST',body:JSON.stringify(f)});msg('Draft saved for approval: '+d.subject);await loadPending()}catch(x){msg(x.message)}};
async function logout(){try{await api('/auth/logout',{method:'POST',body:'{}'});csrf='';showSignedOut();msg('Signed out')}catch(e){msg(e.message)}}
(async()=>{try{const q=new URLSearchParams(location.search);if(q.get('signed_in'))history.replaceState({},'', '/');const r=await fetch('/me',{credentials:'same-origin'});if(r.ok){const d=await r.json();csrf=d.csrf_token||''}await boot()}catch(e){showSignedOut()}})();
</script></body></html>""")

@app.head("/")
def home_head():
    return Response(status_code=200)

@app.get("/auth/google")
async def google_login(request:Request):
    rate_limit(request,'login:'+ (request.client.host if request.client else 'unknown'),10)
    if not hasattr(oauth,'google'):raise HTTPException(503,'Google OAuth is not configured')
    return await oauth.google.authorize_redirect(request,os.getenv('GOOGLE_REDIRECT_URI',str(request.url_for('google_callback'))))

@app.get('/auth/google/callback',name='google_callback')
async def google_callback(request:Request):
    if not hasattr(oauth,'google'):raise HTTPException(503,'Google OAuth is not configured')
    token=await oauth.google.authorize_access_token(request); info=token.get('userinfo') or await oauth.google.userinfo(token=token)
    email=info.get('email',''); verified=info.get('email_verified') is True
    if not allowed_google_email(email,verified):
        request.session.clear();raise HTTPException(403,'This verified Google account is not allowlisted')
    request.session.clear();request.session['user']={'email':email.strip().lower(),'name':str(info.get('name',''))[:120]};request.session['csrf']=secrets.token_urlsafe(32)
    return RedirectResponse('/?signed_in=1',status_code=303)

@app.get('/me')
def me(request:Request,user=Depends(current_user)):return {'user':user,'csrf_token':request.session['csrf']}

@app.post('/auth/logout')
def logout(request:Request,user=Depends(current_user),_:None=Depends(require_csrf)):
    request.session.clear();return {'signed_out':True}

@app.post('/api/products/upload')
async def upload_product(kind:str=Form(...),file:UploadFile=File(...),request:Request=None,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'upload:'+user['email'],10)
    if kind not in {'catalogue','TDS','SDS'}: raise HTTPException(422,'kind must be catalogue, TDS or SDS')
    raw=await file.read(10*1024*1024+1)
    if len(raw)>10*1024*1024: raise HTTPException(413,'PDF must be 10 MB or smaller')
    if not raw.startswith(b'%PDF-'): raise HTTPException(415,'Only valid PDF documents are accepted')
    try:
        reader=PdfReader(BytesIO(raw),strict=True)
        if len(reader.pages)>200: raise HTTPException(413,'PDF must have 200 pages or fewer')
        extracted=' '.join((page.extract_text() or '') for page in reader.pages)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(422,'PDF could not be parsed') from exc
    extracted=re.sub(r'\\s+',' ',extracted).strip()[:100000]
    if len(extracted)<20: raise HTTPException(422,'No usable text found. Scanned PDFs need OCR before upload.')
    name=re.sub(r'[^A-Za-z0-9._ -]','_', (file.filename or 'product.pdf').split('/')[-1].replace(chr(92),'/').split('/')[-1])[:160]
    checksum=hashlib.sha256(raw).hexdigest()
    file_id=product_bucket.upload_from_stream(name,raw,metadata={'kind':kind,'sha256':checksum,'uploaded_by':user['email']})
    doc={'_id':secrets.token_hex(16),'type':'product_document','name':name,'kind':kind,'checksum':checksum,'gridfs_id':str(file_id),'text':extracted,'pages':len(reader.pages),'created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc)}
    svc.collection.insert_one(doc);svc.cache.set('product:'+doc['_id'],doc)
    return {'_id':doc['_id'],'name':name,'kind':kind,'pages':doc['pages'],'checksum':checksum}

@app.get('/api/products')
def list_products(user=Depends(current_user),svc=Depends(get_pilot)):
    return list(svc.collection.find({'type':'product_document'},{'_id':1,'name':1,'kind':1,'pages':1,'created_at':1}).sort('created_at',-1).limit(100))

@app.post('/api/markets/research')
async def research_markets(payload:MarketResearchInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'research:'+user['email'],5)
    facts=payload.product_facts.strip()
    for source_id in payload.source_ids:
        doc=get_product_document(svc,source_id)
        if not doc: raise HTTPException(422,'Unknown product document ID')
        facts+='\\n\\nSource document: '+doc['name']+' ('+doc['kind']+')\\n'+doc['text']
    if len(facts.strip())<10: raise HTTPException(422,'Select a product PDF or provide verified product facts')
    query=f"chemical import demand distributors manufacturers {payload.target_region} {payload.buyer_segments}. Product context: {facts[:800]}"
    try:
        sources=await search_market_sources(query)
        recommendations=await propose_markets_with_llm(product_facts=facts,buyer_segments=payload.buyer_segments,target_region=payload.target_region,sources=sources)
    except MarketResearchConfigurationError as exc: raise HTTPException(503,str(exc)) from exc
    except (MarketResearchError,httpx.HTTPError) as exc: raise HTTPException(502,'Market research provider failed; retry later') from exc
    proposals=[svc.propose_market(p['market'],p['rationale'],p['evidence_url'],p['confidence']) for p in recommendations]
    return {'sources':[{'title':s['title'],'url':s['url']} for s in sources],'proposals':proposals}

@app.post('/api/markets')
def create_market(payload:MarketInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:return svc.propose_market(payload.market,payload.rationale,payload.evidence_url,payload.confidence)
    except ValidationError as exc:raise HTTPException(422,str(exc)) from exc

@app.post('/api/markets/{market_id}/approve')
def approve_market(market_id:str,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:return svc.approve_market(market_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@app.post('/api/drafts/generate')
async def generate_draft(payload:GenerateInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:
        facts=payload.product_facts.strip()
        for source_id in payload.source_ids:
            doc=get_product_document(svc,source_id)
            if not doc: raise HTTPException(422,'Unknown product document ID')
            facts += '\\n\\nSource document: '+doc['name']+' ('+doc['kind']+')\\n'+doc['text']
        if len(facts.strip())<10: raise HTTPException(422,'Select a product PDF or provide verified product facts')
        generated=await generate_sales_draft(product_facts=facts,buyer_context=payload.buyer_context,goal=payload.goal)
        return svc.create_email_draft(payload.recipient,generated['subject'],generated['body'],source_ids=payload.source_ids)
    except LLMConfigurationError as exc:raise HTTPException(503,str(exc)) from exc
    except ValidationError as exc:raise HTTPException(422,str(exc)) from exc

@app.post('/api/drafts')
def create_draft(payload:DraftInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:return svc.create_email_draft(payload.recipient,payload.subject,payload.body,source_ids=payload.source_ids)
    except ValidationError as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/api/pending')
def pending(user=Depends(current_user),svc=Depends(get_pilot)):
    return list(svc.collection.find({'status':'pending_approval'},{'_id':1,'type':1,'market':1,'rationale':1,'evidence_url':1,'confidence':1,'recipient':1,'subject':1,'body':1,'created_at':1}).sort('created_at',-1).limit(100))

@app.post('/api/drafts/{draft_id}/approve')
def approve_draft(draft_id:str,payload:DraftInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:return svc.approve_email_draft(draft_id,{'recipient':payload.recipient.lower(),'subject':payload.subject,'body':payload.body})
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except ValidationError as exc:raise HTTPException(409,str(exc)) from exc
