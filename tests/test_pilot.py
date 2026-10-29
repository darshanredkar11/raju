import copy, pytest
from sanjay_pilot.cache import TTLCache
from sanjay_pilot.service import SalesPilot
from sanjay_pilot.validation import ValidationError, validate_email, validate_market_proposal, validate_draft
from sanjay_pilot.auth import allowed_google_email

class FakeCursor(list):
 def sort(self,key,direction=1):
  self.sort(key=lambda d:(d.get(key) is not None,d.get(key)),reverse=direction<0)
  return self
 def limit(self,n): return FakeCursor(self[:n])

class FakeCollection:
 def __init__(self):self.docs={}
 def insert_one(self,d):self.docs[d['_id']]=copy.deepcopy(d)
 def find_one(self,q,projection=None):
  d=self.docs.get(q.get('_id'))
  return copy.deepcopy(d) if d and all(d.get(k)==v for k,v in q.items() if k!='_id') else None
 def find(self,q=None,projection=None):
  q=q or {}
  def matches(d,query):
   for k,v in query.items():
    if k=='$or':
     if not any(matches(d,part) for part in v): return False
    elif isinstance(v,dict) and '$in' in v:
     if d.get(k) not in v['$in']: return False
    elif isinstance(v,dict) and ('$gte' in v or '$lt' in v):
     val=d.get(k)
     if val is None or ('$gte' in v and val<v['$gte']) or ('$lt' in v and val>=v['$lt']): return False
    elif d.get(k)!=v: return False
   return True
  return FakeCursor([copy.deepcopy(d) for d in self.docs.values() if matches(d,q)])
 def count_documents(self,q):
  return len(list(self.find(q)))
 def delete_one(self,q):
  d=self.find_one(q)
  if d: self.docs.pop(d['_id'],None)
 def update_one(self,q,u):
  d=self.find_one(q)
  if d:self.docs[d['_id']].update(u['$set'])
  return type('R',(),{'matched_count':int(bool(d))})()

def test_cache_bounded_ttl_and_delete():
 c=TTLCache(2,10);c.set('a',1);c.set('b',2);c.get('a');c.set('c',3);assert c.get('b') is None and c.get('a')==1;c.delete('a');assert c.get('a') is None

def test_expired_cache_value():
 import time
 c=TTLCache(2,10);c.set('x',1,.001);time.sleep(.01);assert c.get('x') is None

def test_any_verified_google_account_can_sign_in():
 assert allowed_google_email('owner@sanjay.example',True)
 assert allowed_google_email('attacker@gmail.com',True)
 assert not allowed_google_email('owner@sanjay.example',False)
 assert not allowed_google_email('not-an-email',True)

def test_email_validation_rejects_injection():
 assert validate_email(' Sales@Example.com ')=='sales@example.com'
 for x in ('x@y.com\\r\\nBcc:a@b.com','bad','a@b'):
  with pytest.raises(ValidationError):validate_email(x)

def test_market_requires_https_and_confidence():
 p=validate_market_proposal(market='Germany',rationale='Relevant chemical import market',evidence_url='https://example.com/research',confidence=.6);assert p['status']=='pending_approval'
 with pytest.raises(ValidationError):validate_market_proposal(market='X',rationale='short',evidence_url='http://example.com',confidence=2)

def test_email_draft_never_sends_and_approval_binds_exact_content():
 c=FakeCollection();s=SalesPilot(c);d=s.create_email_draft('buyer@example.com','Introduction','Could we discuss your requirements?');assert d['sent'] is False and d['status']=='pending_approval'
 with pytest.raises(ValidationError):s.approve_email_draft(d['_id'],{'recipient':'attacker@example.com','subject':d['subject'],'body':d['body']})
 a=s.approve_email_draft(d['_id'],{'recipient':d['recipient'],'subject':d['subject'],'body':d['body']});assert a['status']=='approved' and a['sent'] is False

def test_market_is_not_automatically_approved():
 c=FakeCollection();s=SalesPilot(c);p=s.propose_market('Germany','Potential market supported by evidence','https://example.com/report',.65);assert c.docs[p['_id']]['status']=='pending_approval'

def test_prohibited_claim_blocked():
 with pytest.raises(ValidationError):validate_draft(recipient='buyer@example.com',subject='Hello',body='We offer guaranteed purity.')


def test_app_starts_with_google_only_routes_and_protects_api(monkeypatch):
 import importlib
 from fastapi.testclient import TestClient
 monkeypatch.setenv('SESSION_SECRET','s'*48)
 monkeypatch.delenv('MONGODB_URI',raising=False)
 monkeypatch.delenv('GOOGLE_CLIENT_ID',raising=False)
 monkeypatch.delenv('GOOGLE_CLIENT_SECRET',raising=False)
 app_module=importlib.import_module('sanjay_pilot.app')
 client=TestClient(app_module.app)
 assert client.get('/health').status_code==200
 assert client.get('/').status_code==200
 assert client.get('/api/pending').status_code==401
 assert client.get('/auth/password').status_code==404


def test_market_research_discards_hallucinated_evidence_urls(monkeypatch):
 import asyncio, json
 from sanjay_pilot import research
 monkeypatch.setenv('LLM_API_KEY','test-key')
 class Response:
  def raise_for_status(self): pass
  def json(self): return {'choices':[{'message':{'content':json.dumps({'proposals':[{'market':'Germany','rationale':'Evidence supports an importer segment','evidence_url':'https://source.example/report','confidence':0.7},{'market':'France','rationale':'No cited source','evidence_url':'https://invented.example/fake','confidence':0.8}]})}}]}
 class Client:
  def __init__(self,*a,**k): pass
  async def __aenter__(self): return self
  async def __aexit__(self,*a): pass
  async def post(self,*a,**k): return Response()
 monkeypatch.setattr(research.httpx,'AsyncClient',Client)
 result=asyncio.run(research.propose_markets_with_llm(product_facts='Verified product facts',buyer_segments='importers',target_region='Europe',sources=[{'title':'source','url':'https://source.example/report','content':'Evidence'}]))
 assert len(result)==1 and result[0]['evidence_url']=='https://source.example/report'


def test_agent_chat_and_daily_progress_end_to_end(monkeypatch):
 import asyncio, importlib
 from datetime import datetime, timezone
 from fastapi.testclient import TestClient
 monkeypatch.setenv('SESSION_SECRET','z'*48)
 monkeypatch.delenv('MONGODB_URI',raising=False)
 module=importlib.import_module('sanjay_pilot.app')
 store=FakeCollection()
 module.pilot=SalesPilot(store)
 module.app.dependency_overrides[module.current_user]=lambda:{'email':'tester@gmail.com','name':'Tester'}
 module.app.dependency_overrides[module.require_csrf]=lambda:None
 async def fake_reply(**kwargs):
  assert kwargs['message']=='What should I do today?'
  return 'Start by reviewing the pending approvals.'
 monkeypatch.setattr(module,'generate_agent_reply',fake_reply)
 client=TestClient(module.app)
 response=client.post('/api/chat',json={'message':'What should I do today?'})
 assert response.status_code==200 and response.json()['reply'].startswith('Start by reviewing')
 history=client.get('/api/chat/history')
 assert history.status_code==200 and len(history.json()['messages'])==2
 progress=client.get('/api/progress')
 assert progress.status_code==200 and progress.json()['today']['chat_messages']==2
 activity=client.get('/api/activity')
 assert activity.status_code==200 and len(activity.json())==2
 module.app.dependency_overrides.clear()

def test_chat_input_rejects_blank_and_unknown_fields(monkeypatch):
 import importlib
 from fastapi.testclient import TestClient
 monkeypatch.setenv('SESSION_SECRET','z'*48)
 module=importlib.import_module('sanjay_pilot.app')
 module.app.dependency_overrides[module.current_user]=lambda:{'email':'tester@gmail.com','name':'Tester'}
 module.app.dependency_overrides[module.require_csrf]=lambda:None
 client=TestClient(module.app)
 assert client.post('/api/chat',json={'message':'   '}).status_code==422
 assert client.post('/api/chat',json={'message':'hello','unexpected':'no'}).status_code==422
 module.app.dependency_overrides.clear()
