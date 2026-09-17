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

    urgency = kwargs.get("urgency") or "Medium"
    department = kwargs.get("department") or "General"

    # Phase 1: priority is separate from the original urgency field.
    priority = kwargs.get("priority") or urgency

    sla_hours = kwargs.get("sla_hours")
    if sla_hours is None:
        sla_hours = calculate_sla_hours(urgency)

    sla_deadline = kwargs.get("sla_deadline")
    if sla_deadline is None:
        sla_deadline = calculate_sla_deadline(urgency, now)

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO complaints
            (id, village, ward, category, urgency, summary, original_text,
             citizen_name, citizen_phone, latitude, longitude, photo_path, video_path,
             status, resolution_notes, assigned_to, created_at, updated_at,
             department, sla_hours, sla_deadline, resolved_at,
             assigned_officer, priority, resolution_remarks, resolution_photo,
             citizen_feedback, citizen_rating, escalation_level)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            cid,
            kwargs.get("village"),
            kwargs.get("ward"),
            kwargs.get("category"),
            urgency,
            kwargs.get("summary"),
            kwargs.get("original_text"),
            kwargs.get("citizen_name"),
            kwargs.get("citizen_phone"),
            kwargs.get("latitude"),
            kwargs.get("longitude"),
            kwargs.get("photo_path"),
            kwargs.get("video_path"),
            "Submitted",
            kwargs.get("resolution_notes"),
            kwargs.get("assigned_to"),
            now,
            now,
            department,
            sla_hours,
            sla_deadline,
            None,
            kwargs.get("assigned_officer"),
            priority,
            kwargs.get("resolution_remarks"),
            kwargs.get("resolution_photo"),
            kwargs.get("citizen_feedback"),
            kwargs.get("citizen_rating"),
            kwargs.get("escalation_level", 0),
        ))

    add_complaint_update(
        cid,
        "Complaint Registered",
        updated_by="system",
        new_status="Submitted",
        remarks=f"Department: {department} | Priority: {priority} | SLA: {sla_hours} hours"
    )

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


def update_status(
    complaint_id,
    new_status,
    notes=None,
    assigned_to=None,
    assigned_officer=None,
    resolution_remarks=None,
    resolution_photo=None,
    escalation_level=None,
):
    now = datetime.now().isoformat(timespec="seconds")

    complaint = get_complaint(complaint_id)

    if not complaint:
        raise ValueError(f"Complaint not found: {complaint_id}")

    old_status = complaint["status"]
    old_assigned_to = complaint.get("assigned_to")
    old_assigned_officer = complaint.get("assigned_officer")

    # Keep legacy assigned_to and new assigned_officer compatible.
    officer = assigned_officer or assigned_to

    # Resolution remarks can come from the new field or old notes argument.
    remarks = resolution_remarks or notes

    with get_conn() as conn:
        conn.execute("""
            UPDATE complaints
            SET status = ?,
                resolution_notes = COALESCE(?, resolution_notes),
                assigned_to = COALESCE(?, assigned_to),
                assigned_officer = COALESCE(?, assigned_officer),
                resolution_remarks = COALESCE(?, resolution_remarks),
                resolution_photo = COALESCE(?, resolution_photo),
                escalation_level = COALESCE(?, escalation_level),
                resolved_at = CASE
                    WHEN ? IN ("Resolved", "Closed")
                         AND resolved_at IS NULL
                    THEN ?
                    ELSE resolved_at
                END,
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            notes,
            assigned_to or officer,
            officer,
            resolution_remarks,
            resolution_photo,
            escalation_level,
            new_status,
            now,
            now,
            complaint_id,
        ))

    # Timeline: status change
    if old_status != new_status:
        add_complaint_update(
            complaint_id,
            "Status Changed",
            updated_by=officer or "officer",
            old_status=old_status,
            new_status=new_status,
            remarks=remarks,
        )

    # Timeline: officer assignment
    if officer and officer != (old_assigned_officer or old_assigned_to):
        add_complaint_update(
            complaint_id,
            "Officer Assigned",
            updated_by=officer,
            new_status=new_status,
            remarks=f"Assigned to: {officer}",
        )

    # Timeline: resolution information
    if resolution_remarks or resolution_photo:
        add_complaint_update(
            complaint_id,
            "Resolution Evidence Added",
            updated_by=officer or "officer",
            new_status=new_status,
            remarks=resolution_remarks or "Resolution photo added",
        )

    # Timeline: note added without status change
    if notes and old_status == new_status and not resolution_remarks:
        add_complaint_update(
            complaint_id,
            "Resolution Note Added",
            updated_by=officer or "officer",
            new_status=new_status,
            remarks=notes,
        )

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


# ================================================================
# PHASE 1 — Department + SLA + Complaint Timeline
# ================================================================

def calculate_sla_hours(urgency):
    """Return SLA duration based on complaint urgency."""
    return {
        "High": 24,
        "Medium": 48,
        "Low": 72,
    }.get(urgency, 72)


def calculate_sla_deadline(urgency, created_at=None):
    """Calculate SLA deadline from complaint creation time."""
    from datetime import timedelta

    if created_at:
        start = datetime.fromisoformat(created_at)
    else:
        start = datetime.now()

    hours = calculate_sla_hours(urgency)
    return (
        start + timedelta(hours=hours)
    ).isoformat(timespec="seconds")


def add_complaint_update(
    complaint_id,
    action,
    updated_by=None,
    old_status=None,
    new_status=None,
    remarks=None,
):
    """Store a complaint timeline event."""

    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaint_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT NOT NULL,
                action TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                remarks TEXT,
                updated_by TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            INSERT INTO complaint_updates
            (
                complaint_id,
                action,
                old_status,
                new_status,
                remarks,
                updated_by,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint_id,
            action,
            old_status,
            new_status,
            remarks,
            updated_by,
            now,
        ))


def get_complaint_updates(complaint_id):
    """Return complete timeline for a complaint."""

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT *
            FROM complaint_updates
            WHERE complaint_id = ?
            ORDER BY created_at ASC
        """, (complaint_id,)).fetchall()

        return [dict(row) for row in rows]


def get_sla_state(complaint):
    """Return current SLA state."""

    deadline = complaint.get("sla_deadline")

    if not deadline:
        return "No SLA"

    try:
        deadline_dt = datetime.fromisoformat(deadline)
    except Exception:
        return "Invalid SLA"

    now = datetime.now()

    if complaint.get("status") in ("Resolved", "Closed"):
        return "Completed"

    if now > deadline_dt:
        return "Breached"

    remaining = deadline_dt - now

    if remaining.total_seconds() <= 6 * 3600:
        return "Due Soon"

    return "On Track"


def get_sla_counts():
    """Return SLA dashboard counts."""

    complaints = get_all_complaints()

    counts = {
        "On Track": 0,
        "Due Soon": 0,
        "Breached": 0,
        "Completed": 0,
        "No SLA": 0,
        "Invalid SLA": 0,
    }

    for complaint in complaints:
        state = get_sla_state(complaint)

        if state not in counts:
            counts[state] = 0

        counts[state] += 1

    return counts

# ================================================================
# PHASE 1 — Automatic SLA Escalation
# ================================================================

def auto_escalate_complaints():
    """
    Automatically escalate unresolved complaints whose SLA is breached.

    Escalation levels:
        0 = Normal
        1 = First escalation
        2 = Second escalation
        3 = Final escalation
    """

    complaints = get_all_complaints()
    escalated = []

    for complaint in complaints:
        if complaint.get("status") in ("Resolved", "Closed"):
            continue

        if get_sla_state(complaint) != "Breached":
            continue

        current_level = int(complaint.get("escalation_level") or 0)

        if current_level >= 3:
            continue

        new_level = current_level + 1

        with get_conn() as conn:
            conn.execute(
                """
                UPDATE complaints
                SET escalation_level = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_level,
                    datetime.now().isoformat(timespec="seconds"),
                    complaint["id"],
                ),
            )

        add_complaint_update(
            complaint["id"],
            "SLA Escalated",
            updated_by="system",
            new_status=complaint["status"],
            remarks=(
                f"SLA breached. "
                f"Escalation Level {current_level} → {new_level}"
            ),
        )

        escalated.append({
            "complaint_id": complaint["id"],
            "old_level": current_level,
            "new_level": new_level,
        })

    return escalated
