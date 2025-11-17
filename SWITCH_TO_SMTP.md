# Switch from Infobip to SMTP (Gmail)

## Problem
Infobip is rejecting emails because:
- **Error:** "Sending domain missing mandatory DNS records (code 6036)"
- **Reason:** REJECTED_VALIDATION_FAILED
- **Issue:** You cannot verify gmail.com domain in Infobip (only Google can)

## Solution: Use Gmail SMTP Instead

You already have Gmail SMTP configured! Just need to disable Infobip.

## Steps to Switch to SMTP:

### In Railway Dashboard:

1. **Go to your service → Variables**

2. **Remove or empty the Infobip variables:**
   - Delete `INFOBIP_API_KEY` OR set it to empty string `""`
   - Keep `INFOBIP_BASE_URL` (or delete it, doesn't matter)

3. **Keep these SMTP variables (already set):**
   ```
   USE_REAL_EMAIL=true
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=whitneyshillingi5@gmail.com
   SMTP_PASSWORD=rlqg icou mkmu yjkq
   EMAIL_FROM=whitneyshillingi5@gmail.com
   ```

4. **Railway will auto-redeploy**

5. **Test again** - emails will now send via Gmail SMTP

## How It Works:

The code automatically falls back to SMTP when:
- `USE_REAL_EMAIL=true` 
- AND `INFOBIP_API_KEY` is empty/not set
- AND SMTP credentials are configured

## Why SMTP is Better Here:

✅ **No domain verification needed** - Gmail handles it
✅ **Immediate delivery** - Works right away
✅ **Gmail-to-Gmail reliability** - Very high deliverability
✅ **Already configured** - Just need to disable Infobip

## After Switching:

You'll see in logs:
- `Email sent successfully to ... via SMTP: ...`
- Instead of Infobip messages

Emails will be delivered immediately via Gmail SMTP!


