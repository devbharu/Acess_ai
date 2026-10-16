import hashlib
import hmac
import time
import base64
import json
from functools import wraps
from flask import request, jsonify, g
from .config import SECRET_KEY, JWT_EXPIRATION_HOURS
from .database import get_db

def hash_password(password: str) -> str:
    salt = "accessai_salt_secure_2026"
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return h.hex()

def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed)

def generate_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(time.time()) + (JWT_EXPIRATION_HOURS * 3600),
        "iat": int(time.time()),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def decode_token(token: str):
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Add padding if needed
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None  # expired
        return payload
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        
        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = payload.get("sub")
        with get_db() as conn:
            user = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return jsonify({"error": "User not found"}), 401
            if hasattr(user, "keys"):
                g.current_user = dict(user)
            else:
                g.current_user = {"id": user[0], "name": user[1], "email": user[2]}
            g.user_id = user_id
            
        return f(*args, **kwargs)
    return decorated
