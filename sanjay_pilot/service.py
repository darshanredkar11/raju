from datetime import datetime, timezone
from uuid import uuid4
from .cache import TTLCache
from .validation import validate_draft, validate_market_proposal, approve_exact_draft

class SalesPilot:
    def __init__(self, collection, cache=None): self.collection=collection; self.cache=cache or TTLCache()
    def add_product_document(self, *, name, kind, storage_key, checksum):
        if kind not in {'catalogue','TDS','SDS'}: raise ValueError('kind must be catalogue, TDS or SDS')
        if not all(isinstance(v,str) and v.strip() for v in (name,storage_key,checksum)): raise ValueError('document metadata is incomplete')
        doc={'_id':str(uuid4()),'type':'product_document','name':name.strip(),'kind':kind,'storage_key':storage_key.strip(),'checksum':checksum.strip(),'created_at':datetime.now(timezone.utc)}
        self.collection.insert_one(doc); self.cache.set('product:'+doc['_id'],doc); return doc
    def propose_market(self, market, rationale, evidence_url, confidence):
        doc=validate_market_proposal(market=market,rationale=rationale,evidence_url=evidence_url,confidence=confidence)
        doc.update({'_id':str(uuid4()),'type':'market_proposal','created_at':datetime.now(timezone.utc),'approved_at':None})
        self.collection.insert_one(doc); return doc
    def approve_market(self, market_id):
        now=datetime.now(timezone.utc)
        result=self.collection.update_one({'_id':market_id,'type':'market_proposal','status':'pending_approval','approved_at':None},{'$set':{'status':'approved','approved_at':now}})
        if result.matched_count != 1: raise LookupError('pending market proposal not found')
        return {'_id':market_id,'status':'approved','approved_at':now}
    def create_email_draft(self, recipient, subject, body, source_ids=None):
        doc=validate_draft(recipient=recipient,subject=subject,body=body)
        doc.update({'_id':str(uuid4()),'type':'email_draft','source_ids':list(source_ids or []),'created_at':datetime.now(timezone.utc),'approved_at':None})
        self.collection.insert_one(doc); return doc
    def approve_email_draft(self, draft_id, reviewed):
        stored=self.collection.find_one({'_id':draft_id,'type':'email_draft','status':'pending_approval','sent':False})
        if not stored: raise LookupError('pending draft not found')
        approve_exact_draft(stored,reviewed); now=datetime.now(timezone.utc)
        result=self.collection.update_one({'_id':draft_id,'type':'email_draft','status':'pending_approval','sent':False,'recipient':stored['recipient'],'subject':stored['subject'],'body':stored['body']},{'$set':{'status':'approved','approved_at':now}})
        if result.matched_count != 1: raise LookupError('draft changed or was approved concurrently; reload and review again')
        self.cache.delete('draft:'+draft_id)
        return {'_id':draft_id,'status':'approved','approved_at':now,'sent':False}
