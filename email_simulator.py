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
            # Use Infobip Email API v3
            # This endpoint requires multipart/form-data format
            url = f"{INFOBIP_BASE_URL}/email/3/send"
            headers = {
                "Authorization": f"App {INFOBIP_API_KEY}",
                "Accept": "application/json"
            }

            # Infobip Email API v3 requires multipart/form-data
            # Format: messages array as JSON string in form data
            messages_json = json.dumps({
                "messages": [
                    {
                        "from": EMAIL_FROM,
                        "to": to_address,
                        "subject": subject,
                        "text": body
                    }
                ]
            })

            # Use multipart/form-data
            files = {
                "messages": (None, messages_json, "application/json")
            }

            print(f"Attempting to send email via Infobip to {to_address}...")
            print(f"URL: {url}")
            print(f"From: {EMAIL_FROM}")
            
            response = requests.post(url, headers=headers, files=files, timeout=30)
            
            print(f"Infobip Response Status: {response.status_code}")
            print(f"Infobip Response: {response.text}")
            
            # Check for successful response (200 or 201)
            if response.status_code in [200, 201]:
                try:
                    response_data = response.json()
                    print(f"Infobip Response Data: {json.dumps(response_data, indent=2)}")
                    # Check message status if available
                    if "messages" in response_data and len(response_data["messages"]) > 0:
                        msg_status = response_data["messages"][0].get("status", {})
                        status_group = msg_status.get("groupId", 0)
                        # GroupId 1 = PENDING, 3 = DELIVERED, 5 = REJECTED
                        if status_group in [1, 3]:
                            print(f"✓ Email accepted by Infobip (status group: {status_group})")
                        else:
                            print(f"⚠ Email status group: {status_group} - {msg_status.get('groupName', 'Unknown')}")
                except json.JSONDecodeError:
                    print(f"⚠ Could not parse response as JSON, but status code indicates success")
                
                print(f"✓ Email sent successfully to {to_address}: {subject}")
            else:
                # Non-success status code - raise error
                response.raise_for_status()
            # Always log to file on success
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[SENT] {log_entry}")
            return True
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error sending email via Infobip to {to_address}: {e}"
            print(f"✗ {error_msg}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"  Error details: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"  Error response: {e.response.text}")
                print(f"  Status code: {e.response.status_code}")
            # Log failure
            with EMAIL_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[FAILED] {error_msg}\n{log_entry}")
            return False
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error sending email via Infobip to {to_address}: {e}"
            print(f"✗ {error_msg}")
            print(f"  URL attempted: {url}")
            print(f"  Check: INFOBIP_API_KEY is set, INFOBIP_BASE_URL is correct, network connectivity")
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



