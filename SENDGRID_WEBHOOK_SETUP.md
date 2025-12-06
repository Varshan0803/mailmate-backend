# SendGrid Webhook Setup Guide

## 🎯 Overview

Your webhook handler is already implemented and ready at: `/sendgrid/webhook`

This guide will help you configure SendGrid to send event notifications (opens, clicks, bounces, etc.) to your application.

---

## ✅ Current Configuration

Your `.env` file has:
```env
SENDGRID_PUBLIC_KEY=MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAExruGbUkDqdtq0Hr5BVJ32lNPO3ek4SV2DrhrqZ6zQ2w3KC0bnEVxg3pVyia7x8gOVyiXq1YtYjG2u/4J5G+Iew==
SENDGRID_WEBHOOK_DISABLE_VERIFY=True
```

**For Production**: Set `SENDGRID_WEBHOOK_DISABLE_VERIFY=False` to enable signature verification.

---

## 🌐 Step 1: Expose Your Local Server to Internet

Since SendGrid needs to reach your webhook endpoint, you need to expose your local server.

### Option A: Using ngrok (Recommended)

1. **Download ngrok**: https://ngrok.com/download
2. **Start ngrok tunnel**:
   ```powershell
   ngrok http 8000
   ```
3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

### Option B: Using LocalTunnel

```powershell
npm install -g localtunnel
lt --port 8000
```

### Option C: Using Cloudflare Tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

---

## 🔧 Step 2: Configure SendGrid Event Webhook

1. **Go to SendGrid Dashboard**: https://app.sendgrid.com/

2. **Navigate to Settings → Mail Settings → Event Webhook**
   - Or direct link: https://app.sendgrid.com/settings/mail_settings

3. **Click "Event Webhook"**

4. **Enable Event Notifications**: Toggle "ON"

5. **HTTP Post URL**: Enter your public URL
   ```
   https://your-ngrok-url.ngrok.io/sendgrid/webhook
   ```
   Example: `https://abc123.ngrok.io/sendgrid/webhook`

6. **Select Events to Track**:
   - ✅ Delivered
   - ✅ Opened
   - ✅ Clicked
   - ✅ Bounced
   - ✅ Spam Report
   - ✅ Unsubscribe (optional)
   - ✅ Dropped (optional)
   - ✅ Deferred (optional)

7. **Authorization Method**: 
   - For testing: Leave blank or select "None"
   - For production: Use "Signed Event Webhook"

8. **Test Your Integration**: Click "Test Your Integration" button
   - SendGrid will send a test event
   - Check your server logs for incoming webhook

9. **Save Settings**

---

## 🧪 Step 3: Test the Webhook

### Test 1: Manual Test with Sample Payload

```powershell
# Activate your venv first
venv\Scripts\activate

# Run the test script
python test_webhook.py
```

### Test 2: Send a Real Test Email

Use your `/send-bulk-test` endpoint or send via SendGrid dashboard and check:
- Open the email
- Click a link
- Check your email_logs collection for updates

---

## 📊 Step 4: Verify Events are Being Received

### Check Server Logs
Your FastAPI server should show:
```
INFO:     POST /sendgrid/webhook HTTP/1.1" 200 OK
```

### Check Database
```powershell
python verify_email_logs.py
```

Look for:
- `open_count > 0` when emails are opened
- `click_count > 0` when links are clicked
- `open_events` and `click_events` arrays populated

### Check Specific Campaign
```bash
GET http://localhost:8000/analytics/{campaign_id}/summary
```

---

## 🔐 Security: Enable Signature Verification (Production)

Once testing is complete, enable signature verification:

1. **Update `.env`**:
   ```env
   SENDGRID_WEBHOOK_DISABLE_VERIFY=False
   ```

2. **Restart your server**

3. **SendGrid Setup**:
   - In Event Webhook settings
   - Select "Signed Event Webhook"
   - Use your public key (already in .env)

---

## 🐛 Troubleshooting

### Webhook Not Receiving Events

1. **Check ngrok/tunnel is running**:
   ```powershell
   # ngrok should show HTTP requests
   ```

2. **Check FastAPI logs**:
   ```powershell
   # Terminal running: uvicorn app.main:app --reload --port 8000
   ```

3. **Verify URL in SendGrid**:
   - Must be HTTPS (ngrok provides this)
   - Must end with `/sendgrid/webhook`
   - Example: `https://abc123.ngrok.io/sendgrid/webhook`

4. **Test endpoint manually**:
   ```powershell
   curl -X POST http://localhost:8000/sendgrid/webhook -H "Content-Type: application/json" -d '[{"event":"delivered","email":"test@example.com","timestamp":1700000000,"campaign_id":"test123"}]'
   ```

### Signature Verification Fails

1. **Check public key** in `.env` matches SendGrid
2. **Ensure no extra spaces** in SENDGRID_PUBLIC_KEY
3. **For testing**: Set `SENDGRID_WEBHOOK_DISABLE_VERIFY=True`
4. **Check logs** for specific error messages

### Events Not Updating Database

1. **Check MongoDB connection**: Verify MONGO_URI in `.env`
2. **Check email/campaign_id match**: Webhook must have correct campaign_id
3. **Check server logs** for errors processing events
4. **Verify migration ran**: All logs should have `open_count` and `click_count` fields

---

## 📱 Webhook Event Examples

### Open Event
```json
{
  "email": "user@example.com",
  "timestamp": 1700000000,
  "event": "open",
  "campaign_id": "691f2c60df19bb45ea3bd05e",
  "sg_message_id": "abc123.filter.sendgrid.net",
  "useragent": "Mozilla/5.0...",
  "ip": "192.168.1.1"
}
```

### Click Event
```json
{
  "email": "user@example.com",
  "timestamp": 1700000000,
  "event": "click",
  "url": "https://example.com/link",
  "campaign_id": "691f2c60df19bb45ea3bd05e",
  "sg_message_id": "abc123.filter.sendgrid.net"
}
```

---

## 🎯 Expected Database Updates

After webhook processes events:

```javascript
{
  "_id": ObjectId("..."),
  "campaign_id": "691f2c60df19bb45ea3bd05e",
  "email": "user@example.com",
  "status": "delivered",
  "open_count": 3,           // ← Incremented on each open
  "click_count": 2,          // ← Incremented on each click
  "open_events": [
    {"timestamp": ISODate("2025-11-24T10:15:00Z")},
    {"timestamp": ISODate("2025-11-24T11:30:00Z")},
    {"timestamp": ISODate("2025-11-24T14:45:00Z")}
  ],
  "click_events": [
    {"timestamp": ISODate("2025-11-24T10:16:00Z")},
    {"timestamp": ISODate("2025-11-24T11:31:00Z")}
  ],
  "updated_at": ISODate("2025-11-24T14:45:00Z")
}
```

---

## ✅ Success Checklist

- [ ] FastAPI server running on port 8000
- [ ] ngrok/tunnel exposing server to internet
- [ ] SendGrid Event Webhook configured with public URL
- [ ] Selected events: delivered, opened, clicked, bounced, spam report
- [ ] Test integration passed in SendGrid dashboard
- [ ] Sent test email and opened it
- [ ] Verified `open_count` increased in database
- [ ] Analytics endpoint showing correct metrics
- [ ] Server logs showing webhook requests
- [ ] No errors in logs

---

## 📞 Need Help?

- Check server logs: `uvicorn app.main:app --reload --port 8000`
- Check webhook logs in SendGrid dashboard
- Verify database: `python verify_email_logs.py`
- Test endpoint: `python test_webhook.py`
