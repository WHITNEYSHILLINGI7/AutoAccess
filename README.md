# AutoAccess — End-to-End User Account Automation System

**Tech stack**: Python, Flask, pandas, SQLite, Gunicorn, Infobip/SMTP  
**Process**: User Account Management (onboarding/offboarding)  
**Trigger**: HR uploads `new_hires.xlsx` via web interface  
**Outcome**: Accounts created, roles assigned, emails sent, audit logged, dashboard updated

## 🚀 Live Deployment

**Production URL**: https://autoaccess-production-7de8.up.railway.app/

## Problem & Justification

- Manual HR → IT entry takes 15–20 min/user, ~8% error rate, delayed onboarding
- High repetition, error-prone, security-critical, ideal for automation
- Need for secure employee self-service portal with OTP authentication

## Solution & Architecture

```
HR Upload (Excel/CSV) 
  → Flask Web App validates 
  → Simulated AD (JSON) 
  → Assign Roles & Permissions 
  → Email Notification (Infobip/SMTP) 
  → Audit to SQLite 
  → Admin Dashboard
  → Employee Portal (OTP Login)
```

## Key Features

- ✅ **Web-based file upload** - HR can upload Excel/CSV files via web interface
- ✅ **Automated user creation** - Validates and creates user accounts automatically
- ✅ **Role-based access control** - Assigns groups and permissions based on department
- ✅ **Email notifications** - Sends welcome emails and OTP codes via Infobip or SMTP
- ✅ **Employee self-service portal** - OTP-based login for employees
- ✅ **Admin dashboard** - View users, manage accounts, send notifications
- ✅ **REST API** - Full API for external integrations
- ✅ **Audit logging** - Complete audit trail of all actions
- ✅ **Error handling** - Comprehensive validation and error reporting

## File Structure

```
autoaccess-project/
├── app.py                  # Flask web application (main entry point)
├── autoaccess.py           # File processing and automation logic
├── dashboard.py            # Streamlit real-time dashboard (optional)
├── simulate_ad.py          # JSON-based AD simulation
├── email_simulator.py      # Email sending (Infobip/SMTP)
├── database.py             # SQLite audit logging
├── api_auth.py             # API authentication and rate limiting
├── config.py               # Configuration and settings
├── run_production.py       # Production runner script
├── entrypoint.sh           # Docker entrypoint script
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── Procfile                # Railway/Heroku process file
├── railway.toml            # Railway deployment config
├── requirements.txt        # Python dependencies
├── api/
│   └── index.py           # Vercel serverless function
├── templates/             # Flask HTML templates
│   ├── base.html
│   ├── landing.html
│   ├── login.html
│   ├── index.html         # Admin dashboard
│   ├── upload.html
│   ├── employee_login.html
│   ├── employee_verify.html
│   ├── employee_dashboard.html
│   └── ...
├── static/                # CSS and images
├── uploads/               # Uploaded HR files
├── data/                  # Application data
│   ├── users.json         # Simulated AD
│   ├── autoaccess.db      # SQLite audit log
│   └── sent_emails.txt    # Email log
└── slides/                # Presentation files
```

## Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd AutoAccess
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```
   Access at: http://localhost:5000

3. **Optional - Run Streamlit dashboard:**
   ```bash
   streamlit run dashboard.py
   ```
   Access at: http://localhost:8501

### Production Deployment (Railway)

See [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) for detailed deployment instructions.

**Quick deploy:**
1. Push code to GitHub
2. Connect repository to Railway
3. Set environment variables (see below)
4. Railway auto-deploys on push

## Configuration

### Environment Variables

#### Required for Production

```bash
# Flask Configuration
AUTOACCESS_SECRET_KEY=your-secret-key-here
AUTOACCESS_ADMIN_USER=admin
AUTOACCESS_ADMIN_PASS=your-secure-password

# Email Configuration (choose one method)
USE_REAL_EMAIL=true
```

#### Email Configuration - Option 1: Infobip (Recommended for Production)

```bash
USE_REAL_EMAIL=true
INFOBIP_API_KEY=your-infobip-api-key
INFOBIP_BASE_URL=https://api.infobip.com
EMAIL_FROM=your-verified-sender@yourdomain.com
```

**Important:** 
- Sender email must be from a **verified domain** in Infobip
- Cannot use Gmail addresses (gmail.com domain cannot be verified)
- For demo accounts, recipient emails must be whitelisted

See [INFOBIP_CONFIG.md](INFOBIP_CONFIG.md) for detailed Infobip setup.

#### Email Configuration - Option 2: SMTP (Gmail, Outlook, etc.)

```bash
USE_REAL_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

**For Gmail:**
- Enable "App Passwords" in Google Account settings
- Use the app password, not your regular password
- Settings: https://myaccount.google.com/apppasswords

#### Optional Configuration

```bash
# API Configuration
AUTOACCESS_API_ENABLED=true
AUTOACCESS_API_KEY=your-api-key-for-external-access

# Rate Limiting
API_RATE_LIMIT_REQUESTS=100
API_RATE_LIMIT_WINDOW=60
```

### Email Priority

The system checks email configuration in this order:
1. **Infobip** - If `USE_REAL_EMAIL=true` AND `INFOBIP_API_KEY` is set
2. **SMTP** - If `USE_REAL_EMAIL=true` AND SMTP credentials are set
3. **Simulation** - If `USE_REAL_EMAIL=false` (logs to file only)

## How It Works

### 1. Admin Workflow

1. **Login** - Admin logs in at `/login`
2. **Upload File** - Upload Excel/CSV file at `/upload`
3. **Validation** - System validates all rows:
   - Required fields: name, email, department, role, join_date, status
   - Email format validation
   - Department must exist in role matrix
   - Duplicate email detection
4. **Processing** - For each valid row:
   - Creates user account in simulated AD
   - Assigns role-based groups and permissions
   - Generates temporary password
   - Sends welcome email with credentials
5. **Audit** - All actions logged to SQLite database
6. **Dashboard** - View users, metrics, and audit logs

### 2. Employee Portal Workflow

1. **Request OTP** - Employee enters email at `/employee/login`
2. **OTP Generation** - System generates 6-digit OTP code
3. **Email Delivery** - OTP sent via configured email service (Infobip/SMTP)
4. **Verification** - Employee enters OTP code at `/employee/verify`
5. **Access** - Employee gains access to dashboard with:
   - Personal account information
   - Notifications
   - Permission-based features

### 3. User Management

- **Edit Users** - Update user details, department, role, status
- **Deactivate Users** - Offboard users (removes access)
- **Send Notifications** - Send custom messages to users
- **Bulk Operations** - Via REST API

## Routes & Endpoints

### Web Routes

- `/` - Landing page
- `/login` - Admin login
- `/dashboard` - Admin dashboard (protected)
- `/upload` - File upload page (protected)
- `/download/sample` - Download sample Excel template
- `/users/<username>/edit` - Edit user (protected)
- `/users/<username>/notify` - Send notification (protected)
- `/users/<username>/deactivate` - Deactivate user (protected)
- `/notifications` - Admin notifications (protected)
- `/employee/login` - Employee login (OTP request)
- `/employee/verify` - Employee OTP verification
- `/employee/dashboard` - Employee dashboard (protected)
- `/employee/notifications` - Employee notifications (protected)

### REST API Endpoints

All API endpoints require API key authentication via `X-API-Key` header.

**Users:**
- `GET /api/users` - List all users (with filters)
- `GET /api/users/<username>` - Get specific user
- `POST /api/users` - Create new user
- `PUT /api/users/<username>` - Update user
- `DELETE /api/users/<username>` - Delete user
- `POST /api/users/bulk-update` - Bulk update users
- `POST /api/users/bulk-deactivate` - Bulk deactivate users
- `GET /api/users/export` - Export users (JSON/CSV)
- `POST /api/users/import` - Import users

**Audit & Reports:**
- `GET /api/audit` - Get audit log
- `GET /api/reports/users` - User reports with statistics
- `GET /api/reports/export` - Export reports (CSV/Excel)

See API documentation in code comments for detailed request/response formats.

## Admin Login

**Default credentials:**
- Username: `admin`
- Password: `admin123!`

**Override via environment variables:**
- `AUTOACCESS_ADMIN_USER`
- `AUTOACCESS_ADMIN_PASS`
- `AUTOACCESS_SECRET_KEY` (Flask session secret)

⚠️ **Important:** Change default credentials in production!

## Role-Based Access Control

### Departments & Roles

The system supports these departments with predefined access:

- **Finance** - Full ledger access, journal posting, reports
- **HR** - HR portal access, ticket creation
- **Marketing** - Campaign viewing
- **IT** - Admin console, deployment access
- **Intern** - Read-only access

Roles are configured in `config.py` via `ROLE_ACCESS_MATRIX`.

## Email System

### Email Types

1. **Welcome Emails** - Sent when new users are created
   - Contains: Username, temporary password, department, role
   - Template: `EMAIL_BODY_TEMPLATE` in `config.py`

2. **OTP Emails** - Sent for employee login
   - Contains: 6-digit OTP code
   - Expires: When browser session ends

3. **Summary Emails** - Sent to HR/IT after batch processing
   - Contains: Created count, deactivated count, error count

4. **Error Notifications** - Sent to admin when validation errors occur

### Email Providers

**Infobip (Recommended for Production):**
- High deliverability
- Requires verified sender domain
- API-based sending
- See [INFOBIP_CONFIG.md](INFOBIP_CONFIG.md)

**SMTP (Gmail, Outlook, etc.):**
- Easy setup
- Works with any SMTP server
- Good for development/testing
- Gmail requires App Passwords

## Database Schema

### SQLite Tables

**audit_log:**
- `id` - Primary key
- `event_time` - Timestamp
- `action` - Action type (create_user, email_sent, etc.)
- `username` - User affected
- `details` - Additional details

**errors:**
- `id` - Primary key
- `event_time` - Timestamp
- `source` - Error source
- `message` - Error message
- `row_data` - Row data that caused error

**notifications:**
- `id` - Primary key
- `created_at` - Timestamp
- `sender_username` - Who sent it
- `recipient_email` - Recipient
- `subject` - Notification subject
- `message` - Notification body
- `is_read` - Read status

## Deployment

### Railway (Current Production)

1. **Connect GitHub repository**
2. **Set environment variables** in Railway dashboard
3. **Auto-deploys** on push to main branch
4. **Uses Dockerfile** for containerization
5. **Gunicorn** as WSGI server

See [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) for detailed instructions.

### Docker

```bash
docker build -t autoaccess .
docker run -p 5000:5000 --env-file .env autoaccess
```

### Docker Compose

```bash
docker-compose up -d
```

## Development

### Running Tests

```bash
# Run application
python app.py

# Run file watcher (optional)
python autoaccess.py

# Run Streamlit dashboard (optional)
streamlit run dashboard.py
```

### Project Structure

- **Flask App** (`app.py`) - Main web application with routes
- **Business Logic** (`autoaccess.py`) - File processing and validation
- **Data Layer** (`database.py`, `simulate_ad.py`) - Data persistence
- **Email Service** (`email_simulator.py`) - Email sending abstraction
- **Configuration** (`config.py`) - Centralized settings

## Troubleshooting

### Email Not Sending

1. **Check environment variables:**
   - `USE_REAL_EMAIL=true` must be set
   - Email provider credentials must be configured

2. **Infobip Issues:**
   - Verify sender domain is verified in Infobip dashboard
   - For demo accounts, whitelist recipient emails
   - Check Infobip logs for delivery status

3. **SMTP Issues:**
   - Verify SMTP credentials
   - For Gmail, use App Passwords
   - Check firewall/network restrictions

4. **Check logs:**
   - Railway logs show detailed email sending status
   - Look for `✓ Email sent successfully` or error messages

See [EMAIL_FIX.md](EMAIL_FIX.md) and [INFOBIP_TROUBLESHOOTING.md](INFOBIP_TROUBLESHOOTING.md) for more help.

### Common Issues

**"Email simulation mode"**
- Set `USE_REAL_EMAIL=true` in environment variables

**"Failed to send email via Infobip"**
- Check sender domain is verified
- Verify API key is correct
- Check recipient is whitelisted (demo accounts)

**"SMTP credentials not configured"**
- Set `SMTP_USERNAME` and `SMTP_PASSWORD`
- For Gmail, use App Password

## Security Considerations

- ✅ **API Key Authentication** - All API endpoints require API keys
- ✅ **Rate Limiting** - API endpoints have rate limiting
- ✅ **Session Management** - Flask sessions with secret keys
- ✅ **Input Validation** - Comprehensive validation of all inputs
- ✅ **SQL Injection Protection** - Parameterized queries
- ⚠️ **Change default admin credentials** in production
- ⚠️ **Use strong secret keys** for Flask sessions
- ⚠️ **Enable HTTPS** in production (Railway provides this)

## Measurable Outcomes

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time/user | 20 min | 30 sec | 98% faster |
| Weekly IT hrs | 17 hrs | <1 hr | 16 hrs saved |
| Error rate | 8% | <0.5% | 95% reduction |
| Email delivery | Manual | Automated | 100% automated |

## Recent Updates

### v2.0 (Latest)
- ✅ **OTP Email System** - Employee login with email-based OTP
- ✅ **Infobip Integration** - Production email delivery via Infobip API
- ✅ **SMTP Support** - Fallback to SMTP (Gmail, Outlook, etc.)
- ✅ **Railway Deployment** - Production deployment on Railway
- ✅ **Improved Error Handling** - Better email error reporting
- ✅ **Employee Portal** - Self-service employee dashboard
- ✅ **REST API** - Complete API for external integrations
- ✅ **Rate Limiting** - API rate limiting for security
- ✅ **Bulk Operations** - Bulk user management via API

### v1.0
- Initial release with basic automation
- File upload and processing
- Simulated AD and email
- Admin dashboard

## Documentation

- [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) - Railway deployment guide
- [INFOBIP_CONFIG.md](INFOBIP_CONFIG.md) - Infobip email configuration
- [EMAIL_FIX.md](EMAIL_FIX.md) - Email troubleshooting guide
- [INFOBIP_TROUBLESHOOTING.md](INFOBIP_TROUBLESHOOTING.md) - Infobip-specific issues
- [PROJECT_REVIEW.md](PROJECT_REVIEW.md) - Code review and recommendations

## License

[Add your license here]

## Support

For issues or questions:
- Check the troubleshooting guides above
- Review application logs
- Check Railway deployment logs
- Review error messages in the dashboard

## Contributing

[Add contribution guidelines if applicable]
