"""
auth.py — simple username/password auth with roles (admin / officer).
Uses salted SHA-256 hashing (fine for an internal admin tool; swap for
bcrypt/argon2 + a managed auth provider before any real production use).
"""

import hashlib
import os
from datetime import datetime
from database import get_conn


def _hash(password, salt):
    return hashlib.sha256((salt + password).encode()).hexdigest()


def create_user(username, password, role="officer", phone=None):
    salt = os.urandom(8).hex()
    pw_hash = f"{salt}${_hash(password, salt)}"
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, phone, created_at) VALUES (?,?,?,?,?)",
            (username, pw_hash, role, phone, now),
        )


def authenticate(username, password):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        return None
    salt, stored_hash = row["password_hash"].split("$")
    if _hash(password, salt) == stored_hash:
        return {"username": row["username"], "role": row["role"], "phone": row["phone"]}
    return None


def seed_default_admin():
    """Creates a default admin (admin / admin123) the first time the app runs."""
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone()
    if not exists:
        create_user("admin", "admin123", role="admin")
