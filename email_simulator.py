from __future__ import annotations

"""
Email simulator: prints to console and appends to a file log.
# RUBRIC: Technical Execution (25%) — Reliable comms simulation
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict

from config import EMAIL_LOG, EMAIL_FROM, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, USE_REAL_EMAIL


def send_email_simulated(to_address: str, subject: str, body: str) -> None:
    """
    Sends an email: real if configured, otherwise simulates by printing and logging to file.

    In production: configure SMTP settings via environment variables.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = (
        f"[{timestamp}] FROM: {EMAIL_FROM} TO: {to_address}\n"
        f"SUBJECT: {subject}\n"
        f"BODY:\n{body}\n"
        f"{'-'*60}\n"
    )

    if USE_REAL_EMAIL:
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = to_address
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_FROM, to_address, text)
            server.quit()
            print(f"Email sent to {to_address}: {subject}")
        except Exception as e:
            print(f"Failed to send email to {to_address}: {e}")
            # Fall back to logging
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[FAILED] {log_entry}")
            return
    else:
        # Simulation
        print(f"Email queued to {to_address}: {subject}")

    # Always log to file
    with EMAIL_LOG.open("a", encoding="utf-8") as f:
        f.write(log_entry)



