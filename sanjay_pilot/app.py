from __future__ import annotations
import os, secrets, time
from collections import OrderedDict, deque
from typing import Annotated
from fastapi import FastAPI, Depends, Header, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pathlib import Path
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
from .llm import generate_sales_draft, generate_agent_reply, LLMConfigurationError
from .service import SalesPilot
from .research import search_market_sources, propose_markets_with_llm, MarketResearchConfigurationError, MarketResearchError
import httpx
from .validation import ValidationError

app=FastAPI(title="Sanjay Chemicals Sales Pilot",docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(SessionMiddleware,secret_key=require_session_secret(),same_site="lax",https_only=os.getenv("COOKIE_SECURE","true").lower()=="true",max_age=8*60*60)
oauth=OAuth()
if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    oauth.register(name="google",client_id=os.environ["GOOGLE_CLIENT_ID"],client_secret=os.environ["GOOGLE_CLIENT_SECRET"],server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",client_kwargs={"scope":"openid email profile"})
mongo=None; pilot=None; product_bucket=None; _indexes_ready=False
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
    global _indexes_ready
    if pilot is None:raise HTTPException(503,"MongoDB is not configured")
    if not _indexes_ready and hasattr(pilot.collection,"create_index"):
        try:
            pilot.collection.create_index([("type",1),("created_at",-1)],name="type_created_at")
            pilot.collection.create_index([("type",1),("owner_email",1),("created_at",-1)],name="type_owner_created")
            pilot.collection.create_index([("status",1),("created_at",-1)],name="status_created")
            pilot.collection.create_index([("type",1),("checksum",1)],name="type_checksum")
            _indexes_ready=True
        except Exception as exc:
            raise HTTPException(503,"MongoDB is unavailable or required indexes could not be initialized") from exc
    return pilot

def get_product_document(svc, source_id, owner_email):
    # A verified Google identity gets its own isolated workspace by default.
    doc=svc.collection.find_one({'_id':source_id,'type':'product_document','created_by':owner_email})
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

class ChatInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    message:str=Field(min_length=1,max_length=4000)

class MarketResearchInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    product_facts:str=Field(default="",max_length=6000)
    source_ids:list[str]=Field(default_factory=list,max_length=20)
    target_region:str=Field(default="Global",min_length=2,max_length=100)
    buyer_segments:str=Field(default="importers, distributors and manufacturers",min_length=3,max_length=300)

@app.get("/health")
def health():
    return {
        "ok": True,
        "database_configured": pilot is not None,
        "google_sign_in_configured": hasattr(oauth, "google"),
        "llm_configured": bool(os.getenv("LLM_API_KEY")),
        "market_research_configured": bool(os.getenv("TAVILY_API_KEY") and os.getenv("LLM_API_KEY")),
        "harvey_runtime_connected": False,
        "agent_mode": "llm_api" if os.getenv("LLM_API_KEY") else "not_configured",
        "outbound_email_enabled": False,
    }

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Never send the authenticated application shell to an anonymous visitor.
    page = "dashboard.html" if request.session.get("user") else "login.html"
    return HTMLResponse(Path(__file__).with_name(page).read_text(encoding="utf-8"))

@app.get("/manual", response_class=HTMLResponse)
def user_manual(user=Depends(current_user)):
    return HTMLResponse(Path(__file__).with_name("manual.html").read_text(encoding="utf-8"))

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
    extracted=re.sub(r'\s+',' ',extracted).strip()[:100000]
    if len(extracted)<20: raise HTTPException(422,'No usable text found. Scanned PDFs need OCR before upload.')
    name=re.sub(r'[^A-Za-z0-9._ -]','_', (file.filename or 'product.pdf').split('/')[-1].replace(chr(92),'/').split('/')[-1])[:160]
    checksum=hashlib.sha256(raw).hexdigest()
    existing=svc.collection.find_one({'type':'product_document','checksum':checksum,'created_by':user['email']})
    if existing:
        return {'_id':str(existing['_id']),'name':existing.get('name',name),'kind':existing.get('kind',kind),'pages':existing.get('pages',0),'checksum':checksum,'duplicate':True}
    file_id=product_bucket.upload_from_stream(name,raw,metadata={'kind':kind,'sha256':checksum,'uploaded_by':user['email']})
    doc={'_id':secrets.token_hex(16),'type':'product_document','name':name,'kind':kind,'checksum':checksum,'gridfs_id':str(file_id),'text':extracted,'pages':len(reader.pages),'created_by':user['email'],'created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc)}
    svc.collection.insert_one(doc);svc.cache.set('product:'+doc['_id'],doc)
    return {'_id':doc['_id'],'name':name,'kind':kind,'pages':doc['pages'],'checksum':checksum}

@app.get('/api/products')
def list_products(user=Depends(current_user),svc=Depends(get_pilot)):
    return list(svc.collection.find({'type':'product_document','created_by':user['email']},{'_id':1,'name':1,'kind':1,'pages':1,'created_at':1}).sort('created_at',-1).limit(100))

def _today_bounds():
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    local_now=datetime.now(ZoneInfo('Asia/Kolkata'))
    now=local_now.astimezone(timezone.utc)
    start=local_now.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    return now,start

def _progress_data(svc, user_email):
    now,start=_today_bounds()
    coll=svc.collection
    def count(query): return coll.count_documents(query)
    chat_count=count({'type':'chat_message','owner_email':user_email,'created_at':{'$gte':start,'$lt':now}})
    doc_count=count({'type':'product_document','created_by':user_email,'created_at':{'$gte':start,'$lt':now}})
    market_count=count({'type':'market_proposal','created_by':user_email,'created_at':{'$gte':start,'$lt':now}})
    draft_count=count({'type':'email_draft','created_by':user_email,'created_at':{'$gte':start,'$lt':now}})
    pending_total=count({'status':'pending_approval','created_by':user_email})
    pending_items=list(coll.find({'status':'pending_approval','created_by':user_email},{'_id':1,'type':1,'market':1,'subject':1,'created_at':1}).sort('created_at',-1).limit(5))
    return {'today':{'date_label':now.astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).strftime('%A, %d %b'),'actions':chat_count+doc_count+market_count+draft_count,'chat_messages':chat_count,'documents':doc_count,'markets':market_count,'drafts':draft_count},'pending':{'total':pending_total,'items':[{'_id':str(x['_id']),'kind':x.get('type','item'),'title':x.get('market') or x.get('subject') or 'Approval item','created_at':x.get('created_at')} for x in pending_items]},'documents':{'total':count({'type':'product_document'})},'markets':{'today':market_count}}

@app.get('/api/progress')
def get_progress(user=Depends(current_user),svc=Depends(get_pilot)):
    return _progress_data(svc,user['email'])

@app.get('/api/chat/history')
def chat_history(user=Depends(current_user),svc=Depends(get_pilot)):
    messages=list(svc.collection.find({'type':'chat_message','owner_email':user['email']},{'_id':0,'role':1,'content':1,'created_at':1}).sort('created_at',1).limit(100))
    return {'messages':[{'role':m['role'],'content':m['content'],'created_at':m['created_at'].isoformat() if hasattr(m.get('created_at'),'isoformat') else str(m.get('created_at',''))} for m in messages]}

@app.post('/api/chat')
async def chat(payload:ChatInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'chat:'+user['email'],20,60)
    message=payload.message.strip()
    if not message: raise HTTPException(422,'Message cannot be blank')
    now,start=_today_bounds()
    coll=svc.collection
    history=list(coll.find({'type':'chat_message','owner_email':user['email']},{'_id':0,'role':1,'content':1,'created_at':1}).sort('created_at',-1).limit(12))
    history.reverse()
    docs=list(coll.find({'type':'product_document','created_by':user['email']},{'_id':0,'name':1,'kind':1,'text':1,'created_at':1}).sort('created_at',-1).limit(5))
    pending=list(coll.find({'status':'pending_approval','created_by':user['email']},{'_id':0,'type':1,'market':1,'rationale':1,'evidence_url':1,'subject':1,'recipient':1,'created_at':1}).sort('created_at',-1).limit(10))
    progress=_progress_data(svc,user['email'])['today']
    user_doc={'_id':secrets.token_hex(16),'type':'chat_message','owner_email':user['email'],'role':'user','content':message,'created_at':now}
    coll.insert_one(user_doc)
    actions=[]
    try:
        lower=message.casefold()
        wants_research=bool(re.search(r'\b(research|find|identify|explore)\b.{0,80}\b(markets?|export markets?|countries|buyers?)\b',lower)) or ('research' in lower and 'market' in lower)
        wants_draft=('draft' in lower or 'write' in lower or 'compose' in lower) and any(word in lower for word in ('email','outreach','buyer'))
        if wants_research:
            facts='\n\n'.join(f"Source document: {d.get('name','')} ({d.get('kind','')})\n{d.get('text','')}" for d in docs if d.get('text'))
            if len(facts.strip())<10:
                reply='I need verified product context before researching export markets. Upload the product catalogue, TDS or SDS in **Documents**, then ask me to research markets again. I will not guess your product range.'
            else:
                sources=await search_market_sources(f"chemical import demand distributors manufacturers global export markets. Product context: {facts[:800]}")
                recommendations=await propose_markets_with_llm(product_facts=facts,buyer_segments='importers, distributors and manufacturers',target_region='Global',sources=sources)
                for item in recommendations:
                    actions.append(svc.propose_market(item['market'],item['rationale'],item['evidence_url'],item['confidence'],created_by=user['email']))
                if actions:
                    reply='I found '+str(len(actions))+' evidence-linked market proposal(s). They are now in the approval queue; none is active yet.\n\n'+'\n'.join(f"• {x['market']} — {x['rationale']}\nEvidence: {x['evidence_url']}\nConfidence: {round(x['confidence']*100)}%" for x in actions)
                else:
                    reply='I searched the available sources but could not produce a market proposal with a verifiable source link. No proposal was added. Try a more specific product document or target region in Market Research.'
        elif wants_draft:
            email_match=re.search(r'(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}(?![\w.-])',message,re.I)
            facts='\n\n'.join(f"Source document: {d.get('name','')} ({d.get('kind','')})\n{d.get('text','')}" for d in docs if d.get('text'))
            if not email_match:
                reply='I can create an approval-ready draft. Please send the buyer email address and a sentence of buyer/company context, for example: “Draft an introduction email to buyer@example.com at Acme Imports; they distribute industrial chemicals in Germany.”'
            elif len(facts.strip())<10:
                reply='Before I draft a product-specific email, upload the catalogue, TDS or SDS in **Documents** so I can avoid unsupported specifications and claims.'
            else:
                generated=await generate_sales_draft(product_facts=facts,buyer_context=message,goal='Write a concise, factual first-touch B2B introduction')
                draft=svc.create_email_draft(email_match.group(0),generated['subject'],generated['body'],created_by=user['email'])
                actions.append(draft)
                reply='I created a draft for '+draft['recipient']+'. It is waiting in **Approvals** for you to review the exact subject and message. Nothing has been sent.'
        else:
            reply=await generate_agent_reply(message=message,history=history,product_documents=docs,pending_items=pending,today_summary=progress)
    except LLMConfigurationError as exc:
        coll.delete_one({'_id':user_doc['_id']})
        raise HTTPException(503,str(exc)) from exc
    except (MarketResearchConfigurationError,) as exc:
        coll.delete_one({'_id':user_doc['_id']})
        raise HTTPException(503,str(exc)) from exc
    except (MarketResearchError,httpx.HTTPError) as exc:
        coll.delete_one({'_id':user_doc['_id']})
        raise HTTPException(502,'The agent provider is temporarily unavailable or returned no usable research. Please retry.') from exc
    except ValidationError as exc:
        reply='I could not safely create that item: '+str(exc)+'. Please correct the input and try again.'
    except RuntimeError as exc:
        coll.delete_one({'_id':user_doc['_id']})
        raise HTTPException(502,str(exc)) from exc
    assistant_doc={'_id':secrets.token_hex(16),'type':'chat_message','owner_email':user['email'],'role':'assistant','content':reply,'created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc)}
    coll.insert_one(assistant_doc)
    return {'reply':reply,'created_at':assistant_doc['created_at'].isoformat(),'actions':[{'id':str(x.get('_id','')),'type':x.get('type','')} for x in actions]}

@app.get('/api/activity')
def activity(user=Depends(current_user),svc=Depends(get_pilot)):
    docs=list(svc.collection.find({'$or':[{'type':'chat_message','owner_email':user['email']},{'type':'product_document','created_by':user['email']},{'type':'market_proposal','created_by':user['email']},{'type':'email_draft','created_by':user['email']}]},{'_id':0,'type':1,'role':1,'content':1,'name':1,'kind':1,'market':1,'subject':1,'status':1,'created_at':1}).sort('created_at',-1).limit(100))
    labels={'chat_message':('Chat','◌'),'product_document':('Document uploaded','▤'),'market_proposal':('Market proposal','⌕'),'email_draft':('Email draft','✉')}
    return [{'title':labels.get(x.get('type'),('Activity','◷'))[0] if x.get('type')!='chat_message' else ('You messaged the agent' if x.get('role')=='user' else 'Agent responded'),'icon':labels.get(x.get('type'),('Activity','◷'))[1],'detail':(x.get('name') or x.get('market') or x.get('subject') or x.get('content',''))[:240],'status':x.get('status','recorded'),'created_at':x.get('created_at').isoformat() if hasattr(x.get('created_at'),'isoformat') else str(x.get('created_at',''))} for x in docs]

@app.get('/api/research/recent')
def recent_research(user=Depends(current_user),svc=Depends(get_pilot)):
    return list(svc.collection.find({'type':'market_proposal','created_by':user['email']},{'_id':1,'market':1,'rationale':1,'evidence_url':1,'confidence':1,'status':1,'created_at':1}).sort('created_at',-1).limit(50))

@app.post('/api/markets/research')
async def research_markets(payload:MarketResearchInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'research:'+user['email'],5)
    facts=payload.product_facts.strip()
    for source_id in payload.source_ids:
        doc=get_product_document(svc,source_id,user['email'])
        if not doc: raise HTTPException(422,'Unknown product document ID')
        facts+='\\n\\nSource document: '+doc['name']+' ('+doc['kind']+')\\n'+doc['text']
    if len(facts.strip())<10: raise HTTPException(422,'Select a product PDF or provide verified product facts')
    query=f"chemical import demand distributors manufacturers {payload.target_region} {payload.buyer_segments}. Product context: {facts[:800]}"
    try:
        sources=await search_market_sources(query)
        recommendations=await propose_markets_with_llm(product_facts=facts,buyer_segments=payload.buyer_segments,target_region=payload.target_region,sources=sources)
    except MarketResearchConfigurationError as exc: raise HTTPException(503,str(exc)) from exc
    except (MarketResearchError,httpx.HTTPError) as exc: raise HTTPException(502,'Market research provider failed; retry later') from exc
    proposals=[svc.propose_market(p['market'],p['rationale'],p['evidence_url'],p['confidence'],created_by=user['email']) for p in recommendations]
    return {'sources':[{'title':s['title'],'url':s['url']} for s in sources],'proposals':proposals}

@app.post('/api/markets')
def create_market(payload:MarketInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:return svc.propose_market(payload.market,payload.rationale,payload.evidence_url,payload.confidence,created_by=user['email'])
    except ValidationError as exc:raise HTTPException(422,str(exc)) from exc

@app.post('/api/markets/{market_id}/approve')
def approve_market(market_id:str,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:
        if not svc.collection.find_one({'_id':market_id,'type':'market_proposal','created_by':user['email'],'status':'pending_approval'}): raise LookupError('pending market proposal not found')
        return svc.approve_market(market_id,approved_by=user['email'])
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc

@app.post('/api/drafts/generate')
async def generate_draft(payload:GenerateInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:
        facts=payload.product_facts.strip()
        for source_id in payload.source_ids:
            doc=get_product_document(svc,source_id,user['email'])
            if not doc: raise HTTPException(422,'Unknown product document ID')
            facts += '\\n\\nSource document: '+doc['name']+' ('+doc['kind']+')\\n'+doc['text']
        if len(facts.strip())<10: raise HTTPException(422,'Select a product PDF or provide verified product facts')
        generated=await generate_sales_draft(product_facts=facts,buyer_context=payload.buyer_context,goal=payload.goal)
        return svc.create_email_draft(payload.recipient,generated['subject'],generated['body'],source_ids=payload.source_ids,created_by=user['email'])
    except LLMConfigurationError as exc:raise HTTPException(503,str(exc)) from exc
    except ValidationError as exc:raise HTTPException(422,str(exc)) from exc

@app.post('/api/drafts')
def create_draft(payload:DraftInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:return svc.create_email_draft(payload.recipient,payload.subject,payload.body,source_ids=payload.source_ids,created_by=user['email'])
    except ValidationError as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/api/pending')
def pending(user=Depends(current_user),svc=Depends(get_pilot)):
    return list(svc.collection.find({'status':'pending_approval','created_by':user['email']},{'_id':1,'type':1,'market':1,'rationale':1,'evidence_url':1,'confidence':1,'recipient':1,'subject':1,'body':1,'created_at':1}).sort('created_at',-1).limit(100))

@app.post('/api/drafts/{draft_id}/approve')
def approve_draft(draft_id:str,payload:DraftInput,request:Request,user=Depends(current_user),_:None=Depends(require_csrf),svc=Depends(get_pilot)):
    rate_limit(request,'write:'+user['email'],20)
    try:
        if not svc.collection.find_one({'_id':draft_id,'type':'email_draft','created_by':user['email'],'status':'pending_approval','sent':False}): raise LookupError('pending draft not found')
        return svc.approve_email_draft(draft_id,{'recipient':payload.recipient.lower(),'subject':payload.subject,'body':payload.body},approved_by=user['email'])
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except ValidationError as exc:raise HTTPException(409,str(exc)) from exc
