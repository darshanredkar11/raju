import copy, pytest
from sanjay_pilot.cache import TTLCache
from sanjay_pilot.service import SalesPilot
from sanjay_pilot.validation import ValidationError, validate_email, validate_market_proposal, validate_draft
from sanjay_pilot.auth import allowed_google_email

class FakeCollection:
 def __init__(self):self.docs={}
 def insert_one(self,d):self.docs[d['_id']]=copy.deepcopy(d)
 def find_one(self,q):
  d=self.docs.get(q.get('_id'))
  return copy.deepcopy(d) if d and all(d.get(k)==v for k,v in q.items() if k!='_id') else None
 def update_one(self,q,u):
  d=self.find_one(q)
  if d:self.docs[d['_id']].update(u['$set'])
  return type('R',(),{'matched_count':int(bool(d))})()

def test_cache_bounded_ttl_and_delete():
 c=TTLCache(2,10);c.set('a',1);c.set('b',2);c.get('a');c.set('c',3);assert c.get('b') is None and c.get('a')==1;c.delete('a');assert c.get('a') is None

def test_expired_cache_value():
 import time
 c=TTLCache(2,10);c.set('x',1,.001);time.sleep(.01);assert c.get('x') is None

def test_google_identity_requires_verified_allowlist(monkeypatch):
 monkeypatch.setenv('GOOGLE_ALLOWED_DOMAINS','sanjay.example');assert allowed_google_email('owner@sanjay.example',True);assert not allowed_google_email('owner@sanjay.example',False);assert not allowed_google_email('attacker@gmail.com',True)

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
