"""
Application-level encryption for PII at rest.

Sensitive student fields (parent names, phone, address, blood group) are
encrypted with Fernet (AES-128-CBC + HMAC) before they touch the database, so a
leaked DB dump or disk image does not expose minors' personal data in clear.

Design notes:
* The key comes from ``PII_ENCRYPTION_KEY`` (a urlsafe-base64 Fernet key).
  Multiple comma-separated keys enable rotation: the first encrypts, any can
  decrypt (MultiFernet).
* If no key is configured, encryption is a no-op passthrough. This keeps local
  dev/tests working and means turning the feature on/off never corrupts data.
* Ciphertext is tagged with an ``enc::`` prefix. On read, values without the
  prefix are returned as-is, so pre-existing plaintext rows keep working until a
  one-time backfill (``flask backfill-pii-encryption``) encrypts them.
"""

import os

from sqlalchemy.types import TypeDecorator, Text

_PREFIX = "enc::"


def _build_fernet():
    raw = os.getenv("PII_ENCRYPTION_KEY") or os.getenv("PII_ENCRYPTION_KEYS")
    if not raw:
        return None
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        return None
    try:
        from cryptography.fernet import Fernet, MultiFernet
        fernets = [Fernet(k.encode()) for k in keys]
        return MultiFernet(fernets) if len(fernets) > 1 else fernets[0]
    except Exception:
        # Bad key / cryptography missing: fail safe to passthrough rather than
        # taking the whole app down. Readiness/docs surface that PII is unencrypted.
        return None


# Cached so we don't rebuild the cipher on every column access. Tests can flip
# the env var and call reload_encryption() to exercise both modes.
_state = {"fernet": _build_fernet()}


def reload_encryption():
    _state["fernet"] = _build_fernet()


def encryption_enabled():
    return _state["fernet"] is not None


def encrypt_value(value):
    if value is None:
        return None
    fernet = _state["fernet"]
    if fernet is None:
        return value
    token = fernet.encrypt(str(value).encode()).decode()
    return _PREFIX + token


def decrypt_value(value):
    if value is None or not isinstance(value, str):
        return value
    if not value.startswith(_PREFIX):
        return value  # legacy plaintext
    fernet = _state["fernet"]
    if fernet is None:
        return value  # no key to decrypt with; return raw rather than crash
    try:
        return fernet.decrypt(value[len(_PREFIX):].encode()).decode()
    except Exception:
        return value


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(_PREFIX)


class EncryptedString(TypeDecorator):
    """Transparent encrypt-on-write / decrypt-on-read string column.

    Stored as TEXT because ciphertext is far longer than the plaintext.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        return decrypt_value(value)
