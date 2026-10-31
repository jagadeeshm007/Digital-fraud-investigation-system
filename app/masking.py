import hashlib
import hmac as _hmac

from app.config import settings

_KEY = bytes.fromhex(settings.masking_hmac_key)

PII_FIELDS = frozenset({
    "name", "phone", "email", "address", "identity_number",
    "ip_address", "location", "beneficiary_name",
})


def mask(value: str, field: str) -> str:
    try:
        h = _hmac.new(_KEY, f"{field}:{value}".encode(), hashlib.sha256)
        return f"***-{h.hexdigest()[:6]}"
    except Exception:
        return "[masked]"


def mask_dict(d: dict) -> dict:
    return {k: (mask(str(v), k) if k in PII_FIELDS and v is not None else v) for k, v in d.items()}
