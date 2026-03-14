"""JWT verification helpers for Supabase tokens."""

from __future__ import annotations

import json
from functools import lru_cache

import httpx
import jwt
from jwt import algorithms

from src.app.config import get_settings


@lru_cache
def get_jwks() -> dict:
    """Return cached JWKS with Supabase API key headers."""
    settings = get_settings()
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_anon_key}",
    }
    response = httpx.get(jwks_url, headers=headers, timeout=5.0)
    response.raise_for_status()
    return response.json()


def _get_signing_key(token: str):
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        return None
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            if header.get("alg", "").startswith("ES"):
                return algorithms.ECAlgorithm.from_jwk(json.dumps(key))
            if header.get("alg", "").startswith("RS"):
                return algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            raise ValueError("Unsupported JWT algorithm")
    return None


def decode_access_token(token: str) -> dict:
    """Decode and validate a Supabase JWT."""
    settings = get_settings()
    issuer = settings.supabase_jwt_issuer or f"{settings.supabase_url}/auth/v1"
    signing_key = _get_signing_key(token)
    if signing_key is None:
        if not settings.supabase_jwt_secret:
            raise ValueError("Missing SUPABASE_JWT_SECRET for HS256 tokens")
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            issuer=issuer,
            leeway=settings.supabase_jwt_leeway_seconds,
            options={"verify_aud": True, "verify_iss": True},
        )
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256", "ES256"],
        audience=settings.supabase_jwt_audience,
        issuer=issuer,
        leeway=settings.supabase_jwt_leeway_seconds,
        options={"verify_aud": True, "verify_iss": True},
    )
