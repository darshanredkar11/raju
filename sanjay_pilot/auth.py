import os
import re

class AuthConfigurationError(RuntimeError): pass

def allowed_google_email(email: str, verified: bool) -> bool:
    """Allow any verified Google identity; no Workspace/domain allowlist is required."""
    if not verified or not isinstance(email,str): return False
    normalized=email.strip().lower()
    if len(normalized)>254 or normalized.count('@')!=1: return False
    local,domain=normalized.rsplit('@',1)
    if not local or not domain or '.' not in domain or any(ch.isspace() for ch in normalized): return False
    return True

def require_session_secret() -> str:
    secret=os.getenv('SESSION_SECRET','')
    if len(secret)<32: raise AuthConfigurationError('SESSION_SECRET must be at least 32 characters')
    return secret
