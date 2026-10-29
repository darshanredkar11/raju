import re
from email.utils import parseaddr
from urllib.parse import urlparse

class ValidationError(ValueError): pass
_EMAIL = re.compile(r'^[^\s@<>]+@[^\s@<>]+\.[A-Za-z]{2,63}$')
_BLOCKED = ('guaranteed purity','certified food grade','medical grade','zero risk','regulatory approved')

def require_text(value, field, max_length=500):
    if not isinstance(value,str): raise ValidationError(f'{field} must be text')
    value=value.strip()
    if not value or len(value)>max_length or '\x00' in value: raise ValidationError(f'{field} is empty or invalid length')
    return value

def validate_email(value):
    email=require_text(value,'email',254); _, parsed=parseaddr(email)
    if parsed != email or not _EMAIL.fullmatch(email): raise ValidationError('valid email address required')
    return email.lower()

def validate_evidence_url(value):
    url=require_text(value,'evidence_url',2048); parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password: raise ValidationError('evidence URL must be HTTPS and must not contain credentials')
    return url

def validate_draft(*,recipient,subject,body):
    recipient=validate_email(recipient); subject=require_text(subject,'subject',180); body=require_text(body,'body',8000)
    if any(p in (subject+' '+body).casefold() for p in _BLOCKED): raise ValidationError('draft contains a prohibited unverified product/compliance claim')
    if len(re.findall(r'https?://',body,flags=re.I))>2: raise ValidationError('draft contains too many links')
    return {'recipient':recipient,'subject':subject,'body':body,'status':'pending_approval','sent':False}

def validate_market_proposal(*,market,rationale,evidence_url,confidence):
    market=require_text(market,'market',120); rationale=require_text(rationale,'rationale',1500); evidence_url=validate_evidence_url(evidence_url)
    if isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not 0<=confidence<=1: raise ValidationError('confidence must be between 0 and 1')
    return {'market':market,'rationale':rationale,'evidence_url':evidence_url,'confidence':float(confidence),'status':'pending_approval'}

def approve_exact_draft(stored, submitted):
    if any(submitted.get(k)!=stored.get(k) for k in ('recipient','subject','body')): raise ValidationError('draft changed after review; approval must be repeated')
    result=validate_draft(recipient=stored['recipient'],subject=stored['subject'],body=stored['body']); result['status']='approved'; result['sent']=False
    return result
