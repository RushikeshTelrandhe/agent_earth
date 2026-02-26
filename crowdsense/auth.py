"""
Crowdsense Authentication
==========================
Lightweight JWT auth with JSON-file user persistence.
No database required — suitable for pilot deployment.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional

import bcrypt
import jwt
from flask import request, jsonify

SECRET_KEY = os.environ.get("CROWDSENSE_SECRET", "agent_earth_crowdsense_pilot_2026")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

REGIONS = {
    0: "Region 0",
    1: "Region 1",
    2: "Region 2",
    3: "Region 3",
    4: "Region 4",
    5: "Region 5",
}


def _load_users() -> list:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_users(users: list) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def signup(name: str, email: str, password: str, region_id: int) -> Dict[str, Any]:
    users = _load_users()
    if any(u["email"] == email for u in users):
        return {"error": "Email already registered"}
    if region_id not in REGIONS:
        return {"error": f"Invalid region. Must be 0-{len(REGIONS)-1}"}

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "email": email,
        "password": hashed,
        "region_id": region_id,
        "region_name": REGIONS[region_id],
        "created_at": time.time(),
    }
    users.append(user)
    _save_users(users)

    token = jwt.encode(
        {"user_id": user["id"], "region_id": region_id, "exp": time.time() + 86400 * 7},
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}


def login(email: str, password: str) -> Dict[str, Any]:
    users = _load_users()
    user = next((u for u in users if u["email"] == email), None)
    if not user:
        return {"error": "Invalid credentials"}
    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return {"error": "Invalid credentials"}

    token = jwt.encode(
        {"user_id": user["id"], "region_id": user["region_id"], "exp": time.time() + 86400 * 7},
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}


def decode_token(token: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def require_auth(f):
    """Decorator: extracts JWT from Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing auth token"}), 401
        payload = decode_token(auth_header[7:])
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.user = payload  # type: ignore
        return f(*args, **kwargs)
    return decorated
