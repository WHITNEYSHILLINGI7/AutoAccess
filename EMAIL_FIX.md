# OTP Email Sending Fix

## Problem
OTPs were not being sent to employee emails in the deployed application because:
1. Email sending failures were silent - the function didn't return success/failure status
2. No error handling or user feedback when emails failed
3. Configuration issues weren't clearly reported

## What Was Fixed

### 1. Email Function Now Returns Status
- `send_email_simulated()` now returns `bool`: `True` on success, `False` on failure
- Better error handling with specific exception catching
- Improved error messages and logging

### 2. OTP Flow Handles Email Failures
- Checks if email was actually sent
- Shows helpful error messages to users
- Logs failures to database for admin review
- Still allows login even if email fails (for debugging)

### 3. Better Infobip API Support
- Tries JSON format first (standard)
- Falls back to form-data if JSON fails (415 error)
- More detailed error logging with response codes

### 4. Improved Error Messages
- Clear feedback when emails are in simulation mode
- Specific messages for missing credentials
- Server-side logging for all email failures

## How to Enable Real Email Sending

### Option 1: Using Infobip (Recommended for Production)

1. **Set environment variables:**
   ```bash
   export USE_REAL_EMAIL=true
   export INFOBIP_API_KEY=your-infobip-api-key
   export INFOBIP_BASE_URL=https://wg698q.api.infobip.com
   export EMAIL_FROM=your-sender@company.com
   ```

2. **In Vercel/Deployment:**
   - Go to your project settings
   - Add these environment variables:
     - `USE_REAL_EMAIL` = `true`
     - `INFOBIP_API_KEY` = (your actual API key)
     - `INFOBIP_BASE_URL` = `https://wg698q.api.infobip.com`
     - `EMAIL_FROM` = (your verified sender email)

### Option 2: Using SMTP (Gmail, Outlook, etc.)

1. **Set environment variables:**
   ```bash
   export USE_REAL_EMAIL=true
   export SMTP_SERVER=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USERNAME=your-email@gmail.com
   export SMTP_PASSWORD=your-app-password
   export EMAIL_FROM=your-email@gmail.com
   ```

2. **For Gmail specifically:**
   - Enable "App Passwords" in your Google Account
   - Use the app password, not your regular password
   - Settings: https://myaccount.google.com/apppasswords

### Option 3: Docker/Docker Compose

Update your `docker-compose.yml` or `.env` file:
```yaml
environment:
  - USE_REAL_EMAIL=true
  - INFOBIP_API_KEY=${INFOBIP_API_KEY}
  - INFOBIP_BASE_URL=${INFOBIP_BASE_URL:-https://wg698q.api.infobip.com}
  - EMAIL_FROM=${EMAIL_FROM:-noreply@company.com}
```

## Testing Email Configuration

### Check Email Logs
After attempting to send an OTP, check:
- **File:** `data/sent_emails.txt` - All email attempts are logged here
- **Database:** `data/autoaccess.db` - Check `errors` table for email failures
- **Console/Server Logs:** Look for `✗` or `✓` symbols indicating success/failure

### Test Steps
1. Set `USE_REAL_EMAIL=true`
2. Configure either Infobip or SMTP credentials
3. Try employee login with a valid email
4. Check logs to see if email was sent
5. Verify email was received (check spam folder too)

## Common Issues

### "Email simulation mode" Message
- **Cause:** `USE_REAL_EMAIL` is not set to `"true"` (case-insensitive)
- **Fix:** Set environment variable `USE_REAL_EMAIL=true`

### "SMTP credentials not configured"
- **Cause:** `SMTP_USERNAME` or `SMTP_PASSWORD` is empty when using SMTP
- **Fix:** Set both environment variables with valid credentials

### "Failed to send email via Infobip"
- **Cause:** Invalid API key, wrong base URL, or API endpoint issue
- **Fix:** 
  - Verify `INFOBIP_API_KEY` is correct
  - Check `INFOBIP_BASE_URL` matches your Infobip account
  - Review server logs for specific error messages

### Email Sent but Not Received
- **Check spam folder**
- Verify sender email (`EMAIL_FROM`) is properly configured
- For Gmail: Ensure "Less secure app access" or App Passwords are enabled
- For Infobip: Verify sender domain is verified in Infobip dashboard

## Debugging Tips

1. **Check server logs** - Look for email-related messages:
   - `✓ Email sent successfully` = Success
   - `✗ Failed to send email` = Failure (check error details)
   - `⚠ Email simulation mode` = Not configured for real emails

2. **Check email log file:**
   ```bash
   tail -f data/sent_emails.txt
   ```

3. **Check database errors:**
   ```python
   from database import fetch_errors
   errors = fetch_errors(limit=10)
   for error in errors:
       print(error)
   ```

4. **Test email configuration independently:**
   ```python
   from email_simulator import send_email_simulated
   result = send_email_simulated("test@example.com", "Test", "Test email")
   print(f"Email sent: {result}")
   ```

## Changes Made to Files

### `email_simulator.py`
- Changed return type from `None` to `bool`
- Added proper error handling with specific exception types
- Improved Infobip API call (JSON + form-data fallback)
- Better error messages and logging
- Checks for missing credentials before attempting send

### `app.py`
- Updated OTP sending to check email result
- Added error handling for failed emails
- Better user feedback messages
- Logs email failures to database

## Next Steps

1. **Configure email settings** using one of the options above
2. **Test OTP sending** with a valid employee email
3. **Monitor logs** to ensure emails are being sent successfully
4. **Remove OTP from error messages** in production (currently shown in simulation mode for debugging)

## Security Note

⚠️ **Important:** In production, ensure OTP codes are NOT shown in error messages. The current implementation shows them in simulation mode only, but consider removing this entirely for production deployments.

