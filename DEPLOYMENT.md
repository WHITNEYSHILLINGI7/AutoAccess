# AutoAccess Deployment Guide

## Overview

AutoAccess is an end-to-end user account automation system that can be deployed in various environments. This guide covers local development, production deployment, and containerized deployment options.

## Prerequisites

- Python 3.11+
- pip
- Docker & Docker Compose (for containerized deployment)
- SMTP server access (for email functionality)

## Quick Start (Local Development)

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd autoaccess
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env  # Edit .env with your settings
   ```

3. **Run the application:**
   ```bash
   python run_production.py
   ```

4. **Access the application:**
   - Web App: http://localhost:5000
   - Dashboard: http://localhost:8501

## Production Deployment Options

### Option 1: Direct Python Deployment

1. **Setup environment variables:**
   ```bash
   export AUTOACCESS_SECRET_KEY="your-secret-key"
   export AUTOACCESS_ADMIN_USER="admin"
   export AUTOACCESS_ADMIN_PASS="secure-password"
   export USE_REAL_EMAIL=true
   export SMTP_USERNAME="your-email@gmail.com"
   export SMTP_PASSWORD="your-app-password"
   ```

2. **Run with production runner:**
   ```bash
   python run_production.py
   ```

### Option 2: Docker Deployment

1. **Build and run with Docker:**
   ```bash
   docker build -t autoaccess .
   docker run -p 5000:5000 -p 8501:8501 --env-file .env autoaccess
   ```

### Option 3: Docker Compose (Recommended)

1. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **Check status:**
   ```bash
   docker-compose ps
   docker-compose logs
   ```

## Environment Configuration

### Required Environment Variables

```bash
# Flask Configuration
AUTOACCESS_SECRET_KEY=your-secret-key-here
AUTOACCESS_ADMIN_USER=admin
AUTOACCESS_ADMIN_PASS=secure-admin-password

# Email Configuration
USE_REAL_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=it-automation@company.com
```

### Optional Environment Variables

```bash
# Database (defaults to SQLite)
DATABASE_URL=postgresql://user:pass@localhost/autoaccess

# LDAP Integration (for production AD)
LDAP_SERVER=ldap://company.com
LDAP_BASE_DN=DC=company,DC=com
LDAP_BIND_USER=CN=AutoAccess,OU=ServiceAccounts,DC=company,DC=com
LDAP_BIND_PASSWORD=your-ldap-password

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/autoaccess.log
```

## Directory Structure for Deployment

```
/opt/autoaccess/
├── app.py
├── dashboard.py
├── autoaccess.py
├── config.py
├── requirements.txt
├── run_production.py
├── Dockerfile
├── docker-compose.yml
├── .env
├── data/
├── uploads/
├── slides/
├── logs/
└── static/
```

## Security Considerations

1. **Change default admin credentials** in production
2. **Use strong secret keys** for Flask sessions
3. **Configure HTTPS** in production (nginx/apache proxy)
4. **Restrict file upload types** and sizes
5. **Use environment variables** for sensitive data
6. **Regular security updates** for dependencies

## Monitoring and Maintenance

### Health Checks

- Flask app: `curl http://localhost:5000/`
- Streamlit dashboard: `curl http://localhost:8501/`

### Logs

- Application logs: Check console output or configured log files
- Audit logs: Stored in `data/autoaccess.db`
- Email logs: Stored in `data/sent_emails.txt`

### Backup

Regularly backup:
- `data/` directory (user data and audit logs)
- `uploads/` directory (uploaded files)
- Database files if using external DB

## Troubleshooting

### Common Issues

1. **Port conflicts:** Change ports in configuration or docker-compose.yml
2. **Email not sending:** Check SMTP credentials and firewall rules
3. **File permissions:** Ensure write access to data/, uploads/, slides/ directories
4. **Memory issues:** Increase Docker memory limits or system RAM

### Debug Mode

For debugging, set `FLASK_ENV=development` and check logs.

## Performance Tuning

- **Database:** Consider PostgreSQL for high-volume deployments
- **Caching:** Implement Redis for session storage in production
- **File storage:** Use cloud storage (S3, GCS) for uploaded files
- **Load balancing:** Deploy multiple instances behind a load balancer

## Support

For issues or questions:
- Check the README.md for detailed documentation
- Review application logs for error details
- Ensure all prerequisites are met
- Test with sample data before production use
