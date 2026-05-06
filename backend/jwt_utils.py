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


def generate_token(user_id: int, email: str, role: str) -> str:
    """Generate JWT token for user"""
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


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
