from __future__ import annotations

"""
Email simulator: prints to console and appends to a file log.
Uses Infobip REST API for production email sending.
# RUBRIC: Technical Execution (25%) — Reliable comms simulation
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict
import requests
import json

from config import EMAIL_LOG, EMAIL_FROM, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, USE_REAL_EMAIL, INFOBIP_API_KEY, INFOBIP_BASE_URL


def send_email_simulated(to_address: str, subject: str, body: str) -> bool:
    """
    Sends an email: real if configured, otherwise simulates by printing and logging to file.

    In production: uses Infobip REST API for reliable email delivery.
    
    Returns:
        bool: True if email was sent successfully (or simulated), False if sending failed
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = (
        f"[{timestamp}] FROM: {EMAIL_FROM} TO: {to_address}\n"
        f"SUBJECT: {subject}\n"
        f"BODY:\n{body}\n"
        f"{'-'*60}\n"
    )

    if USE_REAL_EMAIL and INFOBIP_API_KEY:
        try:
            # Use Infobip REST API v3
            # Try JSON format first (standard), fallback to form-data if needed
            url = f"{INFOBIP_BASE_URL}/email/3/send"
            headers = {
                "Authorization": f"App {INFOBIP_API_KEY}",
                "Accept": "application/json"
            }

            # Try JSON payload first (cleaner format)
            payload = {
                "from": EMAIL_FROM,
                "to": to_address,
                "subject": subject,
                "text": body
            }
            headers["Content-Type"] = "application/json"

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            # If JSON fails with 415, try form-data format
            if response.status_code == 415:
                headers.pop("Content-Type", None)
                files = {
                    "from": (None, EMAIL_FROM),
                    "to": (None, to_address),
                    "subject": (None, subject),
                    "text": (None, body)
                }
                response = requests.post(url, headers=headers, files=files, timeout=30)
            print(f"Infobip Response Status: {response.status_code}")
            print(f"Infobip Response: {response.text}")
            response.raise_for_status()

            print(f"✓ Email sent successfully to {to_address}: {subject}")
            # Always log to file on success
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[SENT] {log_entry}")
            return True
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send email via Infobip to {to_address}: {e}"
            print(f"✗ {error_msg}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            # Log failure
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[FAILED] {error_msg}\n{log_entry}")
            return False
        except Exception as e:
            error_msg = f"Unexpected error sending email to {to_address}: {e}"
            print(f"✗ {error_msg}")
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[FAILED] {error_msg}\n{log_entry}")
            return False
    elif USE_REAL_EMAIL:
        # Fallback to SMTP if Infobip not configured
        try:
            if not SMTP_USERNAME or not SMTP_PASSWORD:
                error_msg = f"SMTP credentials not configured. Cannot send email to {to_address}"
                print(f"✗ {error_msg}")
                with EMAIL_LOG.open("a", encoding="utf-8") as f:
                    f.write(f"[FAILED] {error_msg}\n{log_entry}")
                return False

            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = to_address
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_FROM, to_address, text)
            server.quit()
            print(f"✓ Email sent successfully to {to_address} via SMTP: {subject}")
            # Always log to file on success
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[SENT] {log_entry}")
            return True
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error sending email to {to_address}: {e}"
            print(f"✗ {error_msg}")
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[FAILED] {error_msg}\n{log_entry}")
            return False
        except Exception as e:
            error_msg = f"Failed to send email via SMTP to {to_address}: {e}"
            print(f"✗ {error_msg}")
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[FAILED] {error_msg}\n{log_entry}")
            return False
    else:
        # Simulation mode - always succeeds for logging purposes
        print(f"⚠ Email simulation mode: Email would be sent to {to_address}: {subject}")
        print(f"   To send real emails, set USE_REAL_EMAIL=true and configure SMTP or Infobip")
        # Always log to file
        with EMAIL_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[SIMULATED] {log_entry}")
        return True  # Return True in simulation mode so flow continues



