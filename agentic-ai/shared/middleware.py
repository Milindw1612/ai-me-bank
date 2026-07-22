"""PII tokenisation — customer name, PAN, Aadhaar, account/card number never enter LLM prompts."""
import hashlib
import hmac
import json
from base64 import b64encode, b64decode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from shared.config import settings

_key_bytes: bytes | None = None


def _get_key() -> bytes:
    global _key_bytes
    if _key_bytes is None:
        raw = settings.pii_encryption_key
        _key_bytes = hashlib.sha256(raw.encode()).digest()
    return _key_bytes


# ── Encryption (AES-256-GCM) ───────────────────────────────────────────────

def encrypt_pii(plaintext: str) -> str:
    """Returns base64(nonce + ciphertext + tag) — safe to store in DB."""
    import os
    aesgcm = AESGCM(_get_key())
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return b64encode(nonce + ct).decode()


def decrypt_pii(token: str) -> str:
    raw = b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(_get_key())
    return aesgcm.decrypt(nonce, ct, None).decode()


# ── Deterministic token (for lookup / join keys) ───────────────────────────

def tokenise(value: str) -> str:
    """HMAC-SHA256 hex digest — same input always produces same token for DB lookups."""
    return hmac.new(_get_key(), value.encode(), hashlib.sha256).hexdigest()


# ── PII scrubber for LLM prompt sanitisation ──────────────────────────────

_PII_FIELDS = {"name", "customer_name", "email", "phone", "mobile", "pan", "aadhaar",
               "account_number", "card_number", "ifsc", "address", "gstin",
               "outstanding_balance", "loan_amount", "salary"}


def scrub_for_llm(data: dict) -> dict:
    """
    Recursively replace any dict key that looks like PII/sensitive-financial with a placeholder.
    Safe to pass the result directly into an LLM system/user prompt.
    """
    clean = {}
    for k, v in data.items():
        if k.lower() in _PII_FIELDS:
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = scrub_for_llm(v)
        elif isinstance(v, list):
            clean[k] = [scrub_for_llm(i) if isinstance(i, dict) else i for i in v]
        else:
            clean[k] = v
    return clean


def safe_json(data: dict) -> str:
    """Scrub then serialise — use this when embedding data in LLM prompts."""
    return json.dumps(scrub_for_llm(data), indent=2, ensure_ascii=False)
