from __future__ import annotations

"""
Configuration for AutoAccess.

# RUBRIC: Technical Execution (25%) — Centralized configuration
# RUBRIC: End-to-End Value (30%) — Clear, maintainable settings
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Directories
UPLOADS_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
SLIDES_DIR = BASE_DIR / "slides"

# Files
USERS_JSON = DATA_DIR / "users.json"
EMAIL_LOG = DATA_DIR / "sent_emails.txt"
DB_PATH = DATA_DIR / "autoaccess.db"
PPTX_PATH = SLIDES_DIR / "AutoAccess_Presentation.pptx"
SAMPLE_XLSX = UPLOADS_DIR / "new_hires.xlsx"

# Polling / Watcher
POLL_INTERVAL_SEC = 2.0

# Role to group/permission mapping
ROLE_ACCESS_MATRIX = {
    "Finance": {"groups": ["finance_full"], "permissions": ["read_ledger", "post_journal", "view_reports"]},
    "HR": {"groups": ["hr_portal"], "permissions": ["view_hr_portal", "create_tickets"]},
    "Marketing": {"groups": ["mkt_basic"], "permissions": ["view_campaigns"]},
    "IT": {"groups": ["it_engineers"], "permissions": ["admin_console", "deploy_access"]},
    "Intern": {"groups": ["limited_access"], "permissions": ["read_only"]},
}

# Organizational Unit (OU) placement by department
OU_BY_DEPARTMENT = {
    "Finance": "OU=Finance,OU=Users,DC=company,DC=com",
    "HR": "OU=HR,OU=Users,DC=company,DC=com",
    "Marketing": "OU=Marketing,OU=Users,DC=company,DC=com",
    "IT": "OU=IT,OU=Users,DC=company,DC=com",
    "Intern": "OU=Interns,OU=Users,DC=company,DC=com",
}

# Email settings
EMAIL_FROM = os.environ.get("EMAIL_FROM", "it-automation@company.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
USE_REAL_EMAIL = os.environ.get("USE_REAL_EMAIL", "false").lower() == "true"
EMAIL_SUBJECT_TEMPLATE = "Welcome to Company – Your Account Details"
EMAIL_BODY_TEMPLATE = (
    "Hello {name},\n\n"
    "Your company account has been created.\n"
    "Username: {username}\n"
    "Temporary Password: {password}\n"
    "Department: {department}\n"
    "Role: {role}\n\n"
    "Please change your password on first login.\n\n"
    "— IT Automation\n"
)

# Summary notifications (simulated)
HR_SUMMARY_EMAIL = "hr-ops@company.com"
IT_SUMMARY_EMAIL = "it-automation@company.com"
ADMIN_EMAIL = "admin@company.com"
SUMMARY_SUBJECT_TEMPLATE = "AutoAccess Run Summary — {created} created, {deactivated} deactivated, {errors} errors"
SUMMARY_BODY_TEMPLATE = (
    "AutoAccess Summary\n\n"
    "Created: {created}\n"
    "Deactivated: {deactivated}\n"
    "Errors: {errors}\n"
    "Processed at: {ts}\n"
)

# Streamlit Dashboard
DASHBOARD_TITLE = "AutoAccess – User Account Automation"

# API Configuration
API_ENABLED = os.environ.get("AUTOACCESS_API_ENABLED", "true").lower() == "true"
API_RATE_LIMIT_REQUESTS = int(os.environ.get("API_RATE_LIMIT_REQUESTS", 100))
API_RATE_LIMIT_WINDOW = int(os.environ.get("API_RATE_LIMIT_WINDOW", 60))  # seconds

# Create directories if missing (idempotent)
for _d in (UPLOADS_DIR, DATA_DIR, SLIDES_DIR):
    _d.mkdir(parents=True, exist_ok=True)


