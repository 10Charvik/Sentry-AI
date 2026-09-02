"""
Minimal auth: a single shared admin API key checked against the
X-API-Key header. This is a reasonable first pass for a hackathon-scale
scaffold with one "admin" role — it is NOT the role-based auth (district
admin / field officer / public) the real platform needs. Swap this for
proper JWT-based auth with roles before this touches real districts.
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_admin_key(api_key: str = Security(_api_key_header)) -> bool:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured on the server — set ADMIN_API_KEY in .env",
        )
    if not api_key or api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass it in the X-API-Key header.",
        )
    return True
