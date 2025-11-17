# Infobip Email Configuration Guide

## Required Environment Variables in Railway

Set these in Railway Dashboard → Your Service → Variables:

```bash
USE_REAL_EMAIL=true
INFOBIP_API_KEY=your-infobip-api-key-here
INFOBIP_BASE_URL=https://api.infobip.com
EMAIL_FROM=your-verified-sender@company.com
```

## Important Notes

### 1. Base URL Format
- **Correct:** `https://api.infobip.com` (standard base URL)
- **Alternative:** `https://wg698q.api.infobip.com` (if using a specific subdomain)
- The endpoint will be: `{BASE_URL}/email/3/send`

### 2. API Key Format
- Your Infobip API key should be a long alphanumeric string
- It's used in the Authorization header as: `App {API_KEY}`
- Make sure there are no extra spaces or quotes

### 3. Sender Email (EMAIL_FROM)
- Must be a **verified sender** in your Infobip account
- Format: `name@domain.com` or `"Name" <name@domain.com>`
- The domain must be verified in Infobip dashboard

### 4. API Payload Format
The code now uses the correct Infobip Email API v3 format:
```json
{
  "messages": [
    {
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Subject",
      "text": "Email body"
    }
  ]
}
```

## Verification Steps

1. **Check Railway Environment Variables:**
   - Go to Railway Dashboard → Your Service → Variables
   - Verify all variables are set correctly
   - Make sure `USE_REAL_EMAIL` is exactly `true` (lowercase)

2. **Test Email Sending:**
   - Try employee login to trigger OTP email
   - Check Railway logs for detailed output:
     - Look for "Attempting to send email via Infobip..."
     - Check response status code
     - Review any error messages

3. **Common Issues:**

   **Issue: "Email simulation mode"**
   - **Fix:** Set `USE_REAL_EMAIL=true` in Railway variables

   **Issue: "Failed to send email via Infobip"**
   - Check `INFOBIP_API_KEY` is correct
   - Verify `INFOBIP_BASE_URL` is correct (try `https://api.infobip.com`)
   - Ensure `EMAIL_FROM` is a verified sender in Infobip
   - Check Railway logs for specific error details

   **Issue: HTTP 401 Unauthorized**
   - Invalid API key
   - Check API key has no extra spaces

   **Issue: HTTP 400 Bad Request**
   - Invalid sender email (not verified)
   - Invalid recipient email format
   - Check payload format in logs

   **Issue: HTTP 403 Forbidden**
   - Sender email not verified in Infobip
   - API key doesn't have email sending permissions

## Testing the Configuration

After setting environment variables, the logs will show:
- `Attempting to send email via Infobip to...`
- `Infobip Response Status: 200` (success) or error code
- `Infobip Response Data: {...}` with message status

## Getting Your Infobip API Key

1. Log in to Infobip dashboard: https://portal.infobip.com
2. Go to Settings → API Keys
3. Create a new API key or use existing one
4. Make sure it has Email API permissions

## Verifying Sender Email

1. Log in to Infobip dashboard
2. Go to Email → Senders
3. Add and verify your sender email/domain
4. Use the verified email in `EMAIL_FROM`

## Support

- Infobip Documentation: https://www.infobip.com/docs/api
- Infobip Email API: https://www.infobip.com/docs/email
- Check Railway logs for detailed error messages


