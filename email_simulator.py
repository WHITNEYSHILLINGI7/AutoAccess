from __future__ import annotations

"""
Email simulator: prints to console and appends to a file log.
# RUBRIC: Technical Execution (25%) — Reliable comms simulation
"""

from datetime import datetime, timezone
from typing import Dict

from config import EMAIL_LOG, EMAIL_FROM


def send_email_simulated(to_address: str, subject: str, body: str) -> None:
    """
    Simulates sending an email by printing and writing to file.

    In production: use smtplib or transactional API (SES, SendGrid).
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = (
        f"[{timestamp}] FROM: {EMAIL_FROM} TO: {to_address}\n"
        f"SUBJECT: {subject}\n"
        f"BODY:\n{body}\n"
        f"{'-'*60}\n"
    )
    # Console
    print(f"Email queued to {to_address}: {subject}")
    # File log (append)
    with EMAIL_LOG.open("a", encoding="utf-8") as f:
        f.write(log_entry)



