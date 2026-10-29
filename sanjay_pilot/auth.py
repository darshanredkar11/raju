import os

class AuthConfigurationError(RuntimeError): pass

def allowed_google_email(email: str, verified: bool) -> bool:
    if not verified or not isinstance(email, str) or email.count('@') != 1: return False
    allowed = {x.strip().lower() for x in os.getenv('GOOGLE_ALLOWED_EMAILS','').split(',') if x.strip()}
    domains = {x.strip().lower().lstrip('@') for x in os.getenv('GOOGLE_ALLOWED_DOMAINS','').split(',') if x.strip()}
    normalized = email.strip().lower()
    return normalized in allowed or normalized.rsplit('@',1)[1] in domains

def require_session_secret() -> str:
    secret = os.getenv('SESSION_SECRET','')
    if len(secret) < 32: raise AuthConfigurationError('SESSION_SECRET must be at least 32 characters')
    return secret
