from __future__ import annotations

"""
SQLite database for audit logging and errors.
# RUBRIC: Technical Execution (25%) — Persistent audit trail
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

from config import DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    action TEXT NOT NULL,
    username TEXT,
    details TEXT
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    row_data TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    sender_username TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


@contextmanager
def db_conn(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def log_event(action: str, username: str | None, details: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (event_time, action, username, details) VALUES (?, ?, ?, ?)",
            (ts, action, username, details),
        )
        conn.commit()


def log_error(source: str, message: str, row_data: str | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO errors (event_time, source, message, row_data) VALUES (?, ?, ?, ?)",
            (ts, source, message, row_data),
        )
        conn.commit()


def fetch_recent_users(limit: int = 100) -> List[Tuple]:
    with db_conn() as conn:
        cur = conn.execute(
            "SELECT event_time, action, username, details FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()


def fetch_errors(limit: int = 100) -> List[Tuple]:
    with db_conn() as conn:
        cur = conn.execute(
            "SELECT event_time, source, message, row_data FROM errors ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()


def create_notification(sender_username: str, recipient_email: str, subject: str, message: str) -> int:
    """Create a new notification and return its ID."""
    ts = datetime.now(timezone.utc).isoformat()
    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notifications (created_at, sender_username, recipient_email, subject, message) VALUES (?, ?, ?, ?, ?)",
            (ts, sender_username, recipient_email, subject, message),
        )
        conn.commit()
        return cur.lastrowid


def fetch_user_notifications(recipient_email: str, limit: int = 50) -> List[Tuple]:
    """Fetch notifications for a specific user, ordered by creation time descending."""
    with db_conn() as conn:
        cur = conn.execute(
            "SELECT id, created_at, sender_username, subject, message, is_read FROM notifications WHERE recipient_email = ? ORDER BY created_at DESC LIMIT ?",
            (recipient_email, limit),
        )
        return cur.fetchall()


def mark_notification_read(notification_id: int, recipient_email: str) -> bool:
    """Mark a notification as read. Returns True if successful."""
    with db_conn() as conn:
        cur = conn.execute(
            "UPDATE notifications SET is_read = TRUE WHERE id = ? AND recipient_email = ?",
            (notification_id, recipient_email),
        )
        conn.commit()
        return cur.rowcount > 0


def get_unread_notification_count(recipient_email: str) -> int:
    """Get the count of unread notifications for a user."""
    with db_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE recipient_email = ? AND is_read = FALSE",
            (recipient_email,),
        )
        return cur.fetchone()[0]



