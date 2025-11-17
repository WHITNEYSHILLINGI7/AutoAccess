# Railway Deployment Guide for AutoAccess

## Quick Deploy to Railway

### Option 1: Deploy via Railway CLI (Recommended)

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Initialize Railway in your project:**
   ```bash
   railway init
   ```

4. **Deploy:**
   ```bash
   railway up
   ```

### Option 2: Deploy via Railway Dashboard

1. **Go to Railway Dashboard:**
   - Visit https://railway.app
   - Sign in with GitHub

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your AutoAccess repository

3. **Configure Service:**
   - Railway will auto-detect the Dockerfile
   - Or it will use the Procfile if Dockerfile is not preferred

4. **Set Environment Variables:**
   - Go to your service → Variables tab
   - Add the following variables (see below)

5. **Deploy:**
   - Railway will automatically deploy on every push to main
   - Or click "Deploy" to trigger manual deployment

## Required Environment Variables

Set these in Railway Dashboard → Your Service → Variables:

### Essential Variables
```bash
# Flask Configuration
AUTOACCESS_SECRET_KEY=your-secret-key-here-generate-random
AUTOACCESS_ADMIN_USER=admin
AUTOACCESS_ADMIN_PASS=your-secure-password

# Port (Railway sets this automatically, but you can override)
PORT=5000
```

### Email Configuration (Choose ONE option)

#### Option A: Using Infobip
```bash
USE_REAL_EMAIL=true
INFOBIP_API_KEY=your-infobip-api-key
INFOBIP_BASE_URL=https://wg698q.api.infobip.com
EMAIL_FROM=your-verified-sender@company.com
```

#### Option B: Using SMTP (Gmail, Outlook, etc.)
```bash
USE_REAL_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

### Optional Variables
```bash
# API Configuration
AUTOACCESS_API_ENABLED=true
AUTOACCESS_API_KEY=your-api-key-for-external-access

# Logging
FLASK_ENV=production
```

## Generate Secret Keys

Generate secure keys for production:

```bash
# Generate Flask secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Generate API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Deployment Methods

### Method 1: Using Dockerfile (Current Setup)
Railway will automatically detect and use the Dockerfile. This is the recommended method.

### Method 2: Using Procfile
If you prefer not to use Docker, Railway can use the Procfile:
- The Procfile uses Gunicorn for production-grade WSGI server
- Make sure `gunicorn` is in `requirements.txt` (already added)

## Post-Deployment Steps

1. **Get Your App URL:**
   - Railway will provide a URL like: `https://your-app.railway.app`
   - You can also set a custom domain in Railway settings

2. **Test the Application:**
   - Visit your Railway URL
   - Test admin login: `/login`
   - Test employee login: `/employee/login`

3. **Check Logs:**
   - In Railway Dashboard → Your Service → Deployments → View Logs
   - Look for startup messages and any errors

4. **Verify Email Configuration:**
   - Try employee login to trigger OTP email
   - Check Railway logs for email sending status
   - Look for `✓ Email sent successfully` or error messages

## Troubleshooting

### Application Won't Start
- **Check logs** in Railway dashboard
- **Verify PORT** environment variable is set (Railway sets this automatically)
- **Check requirements.txt** - all dependencies should be listed

### Emails Not Sending
- **Verify `USE_REAL_EMAIL=true`** is set
- **Check email credentials** (Infobip API key or SMTP credentials)
- **Review logs** for specific error messages
- **Check `data/sent_emails.txt`** if accessible (may need persistent storage)

### Database/File Storage Issues
- Railway uses **ephemeral storage** by default
- Files in `data/` directory will be lost on redeploy
- Consider using Railway's **Volume** service for persistent storage:
  1. Add a Volume service in Railway
  2. Mount it to `/app/data` in your service settings

### Port Issues
- Railway automatically sets `PORT` environment variable
- The app is configured to use `PORT` or default to 5000
- Don't hardcode port numbers

## Persistent Storage Setup (Recommended)

For production, you'll want persistent storage for:
- `data/autoaccess.db` (SQLite database)
- `data/sent_emails.txt` (email logs)
- `data/users.json` (user data)
- `uploads/` (uploaded files)

### Setup Railway Volume:

1. **Add Volume Service:**
   - In Railway dashboard, click "+ New" → "Volume"
   - Name it "autoaccess-data"

2. **Mount Volume:**
   - Go to your web service → Settings → Volumes
   - Mount the volume to `/app/data`

3. **Update Dockerfile** (if needed):
   - The Dockerfile already creates the `data/` directory
   - Volume mount will persist data across deployments

## Monitoring

- **Logs:** View real-time logs in Railway dashboard
- **Metrics:** Railway provides basic metrics (CPU, Memory, Network)
- **Health Checks:** The Dockerfile includes a healthcheck
- **Alerts:** Set up alerts in Railway for deployment failures

## Custom Domain

1. Go to your service → Settings → Domains
2. Click "Generate Domain" or "Add Custom Domain"
3. Follow Railway's instructions for DNS configuration

## Cost Considerations

- Railway offers a **free tier** with $5 credit/month
- After free tier: Pay-as-you-go pricing
- Monitor usage in Railway dashboard
- Consider using Railway's sleep feature for development

## Security Checklist

- [ ] Change default admin credentials
- [ ] Use strong `AUTOACCESS_SECRET_KEY`
- [ ] Set `AUTOACCESS_API_KEY` for API access
- [ ] Configure email properly (don't use simulation in production)
- [ ] Enable HTTPS (Railway provides this automatically)
- [ ] Review and restrict environment variables
- [ ] Set up persistent storage for database

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Check Railway status: https://status.railway.app

## Quick Deploy Command

```bash
# One-liner to deploy (after Railway CLI is installed and logged in)
railway up --detach
```


