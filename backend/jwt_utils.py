"""
JWT Token utilities for authentication
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app

# Secret key for signing JWT tokens.
# Must be provided via env in production; we refuse to boot on a public default
# so tokens can't be forged by anyone who has read the source.
_DEV_FALLBACK_SECRET = "dev-only-insecure-jwt-secret"
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("FLASK_ENV") == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY (or SECRET_KEY) must be set in production. "
            "Refusing to start with an insecure default."
        )
    SECRET_KEY = _DEV_FALLBACK_SECRET
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

# Names of the httpOnly cookies that carry the auth tokens. Keeping them here
# means the route layer and the verifiers agree on a single source of truth.
ACCESS_COOKIE_NAME = "access_token"
ORG_COOKIE_NAME = "org_token"


def generate_token(user_id: int, email: str, role: str, organization_id: int | None = None,
                   token_version: int = 0) -> str:
    """Generate JWT token for a user, optionally scoped to an organization.

    ``token_version`` ("tv" claim) must match the user's current
    ``User.token_version``; bumping that column invalidates every outstanding
    token at once ("log out of all devices").
    """
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "organization_id": organization_id,
        "tv": token_version or 0,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def check_token_version(payload: dict) -> bool:
    """True when the token's "tv" claim matches the user's current version.

    Tokens minted before versioning existed carry no claim and are treated as
    version 0, so a bump revokes them too.
    """
    from models import User  # local import to avoid a circular dependency

    user = User.query.get(payload.get("user_id"))
    if user is None:
        return False
    return (user.token_version or 0) == payload.get("tv", 0)


ORG_TOKEN_EXPIRY_DAYS = 30


def generate_org_token(organization_id: int, slug: str) -> str:
    """Generate a long-lived JWT token representing an authenticated organization."""
    payload = {
        "organization_id": organization_id,
        "slug": slug,
        "scope": "organization",
        "exp": datetime.utcnow() + timedelta(days=ORG_TOKEN_EXPIRY_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_org_token_from_request() -> str | None:
    """Extract the org token.

    Prefers the X-Org-Token header (used by non-browser clients and during the
    cookie migration) and falls back to the httpOnly ``org_token`` cookie that
    the browser sends automatically.
    """
    header = request.headers.get("X-Org-Token")
    if header:
        return header
    return request.cookies.get(ORG_COOKIE_NAME)


def verify_org_token(token: str) -> dict:
    """Verify an org token. Returns payload or { 'error': ... }."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "organization":
            return {"error": "Not an organization token"}
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Organization session expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid organization token"}


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}


def get_token_from_request() -> str | None:
    """Extract the user JWT.

    Prefers the ``Authorization: Bearer <token>`` header for backward
    compatibility, then falls back to the httpOnly ``access_token`` cookie so
    browsers no longer need to expose the token to JavaScript.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]

    return request.cookies.get(ACCESS_COOKIE_NAME)


def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        
        payload = verify_token(token)
        if "error" in payload:
            return jsonify(payload), 401

        if not check_token_version(payload):
            return jsonify({"error": "Session revoked. Please sign in again."}), 401

        # Add user info to request context
        request.user = payload
        return f(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """Decorator to require specific roles.

    Accepts either varargs (`role_required("admin", "principal")`) or a single
    list/tuple (`role_required(["admin", "principal"])`); both are flattened so
    a stray list argument can't silently forbid every request.
    """
    flattened = set()
    for role in allowed_roles:
        if isinstance(role, (list, tuple, set)):
            flattened.update(role)
        else:
            flattened.add(role)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            
            if not token:
                return jsonify({"error": "Missing authentication token"}), 401
            
            payload = verify_token(token)
            if "error" in payload:
                return jsonify(payload), 401

            if not check_token_version(payload):
                return jsonify({"error": "Session revoked. Please sign in again."}), 401

            if payload.get("role") not in flattened:
                return jsonify({"error": f"Forbidden: requires {sorted(flattened)}"}), 403
            
            # Add user info to request context
            request.user = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator
