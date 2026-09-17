"""
Gram Seva authentication
- Username/password login
- Email based OTP password reset
- Email change with OTP
"""

import hashlib
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from dotenv import load_dotenv
from database import get_conn

load_dotenv()


def _hash(password, salt):
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _make_password_hash(password):
    salt = secrets.token_hex(16)
    return f"{salt}${_hash(password, salt)}"


def _valid_email(email):
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            email.strip()
        )
    )


def _send_email(to_email, subject, body):
    sender = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not sender or not smtp_password:
        raise RuntimeError(
            "SMTP_EMAIL या SMTP_PASSWORD configured नहीं है."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, smtp_password)
        smtp.send_message(msg)


def _init_otp_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                purpose TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                target_email TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)


_init_otp_table()


def create_user(username, password, role="officer", phone=None, email=None):
    pw_hash = _make_password_hash(password)
    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users
            (username, password_hash, role, phone, email, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (username, pw_hash, role, phone, email, now),
        )


def authenticate(username, password):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if not row:
        return None

    salt, stored_hash = row["password_hash"].split("$")

    if _hash(password, salt) == stored_hash:
        return {
            "username": row["username"],
            "role": row["role"],
            "phone": row["phone"],
            "email": row["email"] if "email" in row.keys() else None,
        }

    return None


def get_user(username):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()


def get_user_by_email(email):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE lower(email) = lower(?)",
            (email.strip(),)
        ).fetchone()


def set_email(username, email):
    if not _valid_email(email):
        raise ValueError("Invalid email address")

    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET email = ? WHERE username = ?",
            (email.strip(), username)
        )


def _create_otp(username, purpose, target_email):
    otp = f"{secrets.randbelow(1000000):06d}"
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    expires = datetime.now() + timedelta(minutes=10)
    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE auth_otps
            SET used = 1
            WHERE username = ? AND purpose = ? AND used = 0
            """,
            (username, purpose)
        )

        conn.execute(
            """
            INSERT INTO auth_otps
            (username, purpose, otp_hash, target_email, expires_at, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (
                username,
                purpose,
                otp_hash,
                target_email,
                expires.isoformat(timespec="seconds"),
                now,
            )
        )

    return otp


def _verify_otp(username, purpose, otp):
    otp_hash = hashlib.sha256(otp.strip().encode()).hexdigest()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM auth_otps
            WHERE username = ?
              AND purpose = ?
              AND used = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (username, purpose)
        ).fetchone()

        if not row:
            return None

        expires = datetime.fromisoformat(row["expires_at"])

        if datetime.now() > expires:
            return None

        if otp_hash != row["otp_hash"]:
            return None

        conn.execute(
            "UPDATE auth_otps SET used = 1 WHERE id = ?",
            (row["id"],)
        )

        return row


def request_password_reset(identifier):
    """
    identifier can be username OR registered email.
    Sends a 6-digit OTP to the user's registered email.
    """

    identifier = identifier.strip()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ?
               OR lower(email) = lower(?)
            LIMIT 1
            """,
            (identifier, identifier)
        ).fetchone()

    if not row:
        return False, "Username/email नहीं मिला।"

    email = row["email"] if "email" in row.keys() else None

    if not email:
        return False, "इस account में registered email नहीं है।"

    otp = _create_otp(
        row["username"],
        "password_reset",
        email
    )

    _send_email(
        email,
        "Gram Seva - Password Reset OTP",
        f"""नमस्ते,

आपके Gram Seva Admin account का password reset करने के लिए OTP है:

{otp}

यह OTP 10 मिनट तक valid है।

अगर आपने password reset request नहीं की है, तो इस email को ignore करें।

Gram Seva
"""
    )

    return True, "OTP registered email पर भेज दिया गया है।"


def reset_password(identifier, otp, new_password):
    if len(new_password) < 8:
        return False, "Password कम से कम 8 characters का होना चाहिए।"

    identifier = identifier.strip()

    # Username OR registered email दोनों support करें
    with get_conn() as conn:
        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ?
               OR lower(email) = lower(?)
            LIMIT 1
            """,
            (identifier, identifier)
        ).fetchone()

    if not user:
        return False, "Username/email नहीं मिला।"

    username = user["username"]

    verified = _verify_otp(
        username,
        "password_reset",
        otp
    )

    if not verified:
        return False, "OTP गलत या expire हो चुका है।"

    password_hash = _make_password_hash(new_password)

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE username = ?
            """,
            (password_hash, username)
        )

    return True, "Password successfully reset हो गया।"


def request_email_change(username, current_password, new_email):
    """
    Admin अपनी email बदल सकता है।
    Current password + new email OTP दोनों required हैं.
    """

    if not _valid_email(new_email):
        return False, "Valid email address डालें।"

    user = authenticate(username, current_password)

    if not user:
        return False, "Current password गलत है।"

    with get_conn() as conn:
        existing = conn.execute(
            """
            SELECT username FROM users
            WHERE lower(email) = lower(?)
              AND username != ?
            """,
            (new_email.strip(), username)
        ).fetchone()

    if existing:
        return False, "यह email किसी दूसरे account में registered है।"

    otp = _create_otp(
        username,
        "email_change",
        new_email.strip()
    )

    _send_email(
        new_email.strip(),
        "Gram Seva - Verify New Email",
        f"""नमस्ते,

आपके Gram Seva Admin account में नई email verify करने के लिए OTP है:

{otp}

यह OTP 10 मिनट तक valid है।

Gram Seva
"""
    )

    return True, "नई email पर OTP भेज दिया गया है।"


def verify_email_change(username, otp):
    verified = _verify_otp(
        username,
        "email_change",
        otp
    )

    if not verified:
        return False, "OTP गलत या expire हो चुका है।"

    new_email = verified["target_email"]

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET email = ?
            WHERE username = ?
            """,
            (new_email, username)
        )

    return True, "Email successfully update हो गई।"


def seed_default_admin():
    """Creates default admin if it does not already exist."""
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = 'admin'"
        ).fetchone()

    if not exists:
        create_user(
            "admin",
            "admin123",
            role="admin"
        )
