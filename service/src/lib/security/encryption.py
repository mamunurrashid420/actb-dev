"""Encryption helpers for sensitive configs."""

import base64
import json

from cryptography.fernet import Fernet, InvalidToken

from src.app.config import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.app_kms_key:
        raise RuntimeError("APP_KMS_KEY is not configured")
    key = settings.app_kms_key.encode("utf-8")
    # Accept raw 32-byte keys by base64-encoding them.
    if len(key) == 32:
        key = base64.urlsafe_b64encode(key)
    return Fernet(key)


def encrypt_payload(payload: dict) -> str:
    """Encrypt a JSON-serializable payload."""
    token = _get_fernet().encrypt(json.dumps(payload).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_payload(token: str) -> dict:
    """Decrypt a payload token to a dict."""
    try:
        decrypted = _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted payload") from exc
    return json.loads(decrypted)
