"""
JWT Token utilities for authentication
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app

# Secret key for signing JWT tokens
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "school-timetable-secret-dev-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def generate_token(user_id: int, email: str, role: str, organization_id: int | None = None) -> str:
    """Generate JWT token for a user, optionally scoped to an organization"""
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "organization_id": organization_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


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
    """Extract org token from the X-Org-Token header."""
    return request.headers.get("X-Org-Token")


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


def get_token_from_request() -> str:
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


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
        
        # Add user info to request context
        request.user = payload
        return f(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            
            if not token:
                return jsonify({"error": "Missing authentication token"}), 401
            
            payload = verify_token(token)
            if "error" in payload:
                return jsonify(payload), 401
            
            if payload.get("role") not in allowed_roles:
                return jsonify({"error": f"Forbidden: requires {allowed_roles}"}), 403
            
            # Add user info to request context
            request.user = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator
