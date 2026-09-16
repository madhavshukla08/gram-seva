"""
database.py — SQLite persistence layer for ग्राम सेवा portal.
Replaces the old in-memory st.session_state list with a real database
so complaints survive restarts and multiple users see the same data.
"""

import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "gram_seva.db"

STATUS_FLOW = ["Submitted", "In Progress", "Resolved", "Closed"]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,          -- 'admin' or 'officer'
                phone TEXT,
                email TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,          -- e.g. GRV-A1B2C3
                village TEXT NOT NULL,
                ward TEXT,
                category TEXT,
                urgency TEXT,
                summary TEXT,
                original_text TEXT,
                citizen_name TEXT,
                citizen_phone TEXT,
                email TEXT,
                latitude REAL,
                longitude REAL,
                photo_path TEXT,
                video_path TEXT,
                status TEXT NOT NULL DEFAULT 'Submitted',
                resolution_notes TEXT,
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def new_complaint_id():
    return "GRV-" + uuid.uuid4().hex[:6].upper()


def create_complaint(**kwargs):
    cid = new_complaint_id()
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO complaints
            (id, village, ward, category, urgency, summary, original_text,
             citizen_name, citizen_phone, latitude, longitude, photo_path, video_path,
             status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            cid, kwargs.get("village"), kwargs.get("ward"),
            kwargs.get("category"), kwargs.get("urgency"), kwargs.get("summary"),
            kwargs.get("original_text"), kwargs.get("citizen_name"), kwargs.get("citizen_phone"),
            kwargs.get("latitude"), kwargs.get("longitude"),
            kwargs.get("photo_path"), kwargs.get("video_path"),
            "Submitted", now, now,
        ))
    return cid


def get_complaint(complaint_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        return dict(row) if row else None


def get_all_complaints(status_filter=None, village_filter=None, urgency_filter=None):
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    if status_filter and status_filter != "सभी":
        query += " AND status = ?"
        params.append(status_filter)
    if village_filter and village_filter != "सभी":
        query += " AND village = ?"
        params.append(village_filter)
    if urgency_filter and urgency_filter != "सभी":
        query += " AND urgency = ?"
        params.append(urgency_filter)
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_status(complaint_id, new_status, notes=None, assigned_to=None):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute("""
            UPDATE complaints
            SET status = ?, resolution_notes = COALESCE(?, resolution_notes),
                assigned_to = COALESCE(?, assigned_to), updated_at = ?
            WHERE id = ?
        """, (new_status, notes, assigned_to, now, complaint_id))


def get_villages():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT village FROM complaints ORDER BY village").fetchall()
        return [r["village"] for r in rows]


def get_analytics():
    """Returns dicts ready for charting: category counts, urgency counts, status counts, daily trend."""
    with get_conn() as conn:
        by_category = conn.execute(
            "SELECT category, COUNT(*) as n FROM complaints GROUP BY category"
        ).fetchall()
        by_urgency = conn.execute(
            "SELECT urgency, COUNT(*) as n FROM complaints GROUP BY urgency"
        ).fetchall()
        by_status = conn.execute(
            "SELECT status, COUNT(*) as n FROM complaints GROUP BY status"
        ).fetchall()
        by_village = conn.execute(
            "SELECT village, COUNT(*) as n FROM complaints GROUP BY village ORDER BY n DESC LIMIT 10"
        ).fetchall()
        daily = conn.execute(
            "SELECT substr(created_at,1,10) as day, COUNT(*) as n FROM complaints GROUP BY day ORDER BY day"
        ).fetchall()
    return {
        "by_category": [dict(r) for r in by_category],
        "by_urgency": [dict(r) for r in by_urgency],
        "by_status": [dict(r) for r in by_status],
        "by_village": [dict(r) for r in by_village],
        "daily": [dict(r) for r in daily],
    }
