# 🚀 How to Run MailMate Project

## Quick Start Guide

### Step 1: Check Prerequisites

Make sure you have these installed and running:

1. **Python 3.11+** ✅ (already have venv)
2. **MongoDB** - Check if running:
   ```bash
   mongosh
   # If it connects, MongoDB is running ✅
   ```
3. **Redis** - Check if running:
   ```bash
   redis-cli ping
   # Should return: PONG ✅
   ```

### Step 2: Create `.env` File

Create a `.env` file in the project root (`F:\helyxon\Helyxon-Task3-main\.env`) with:

```env
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/mailmate

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-minimum-32-characters-long-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=43200

# SendGrid Configuration
SENDGRID_API_KEY=SG.your-sendgrid-api-key-here
SENDGRID_PUBLIC_KEY=
SENDER_EMAIL=your-verified-email@example.com

# Application Configuration
APP_NAME=mailmate
BACKEND_PUBLIC_URL=http://localhost:8000
ENV=development
DEBUG=True

# Celery Configuration (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Step 3: Activate Virtual Environment

**Windows (PowerShell or Command Prompt):**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies (if needed)

```bash
pip install -r requirements.txt
```

### Step 5: Start the FastAPI Server

**Option A: Simple Command**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Option B: Using Python Module**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

### Step 6: Verify Server is Running

Open your browser:
- **Main API**: http://localhost:8000/
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

You should see the API documentation page! ✅

### Step 7: (Optional) Start Celery Worker

For scheduled email campaigns, open a **NEW terminal window**:

1. Navigate to project directory
2. Activate virtual environment
3. Run:
   ```bash
   celery -A app.utils.celery_app.celery_app worker --loglevel=info
   ```

## Complete Setup Checklist

- [ ] MongoDB is running (`mongosh` works)
- [ ] Redis is running (`redis-cli ping` returns PONG)
- [ ] `.env` file created with all required variables
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] FastAPI server started (`uvicorn app.main:app --reload`)
- [ ] Server accessible at http://localhost:8000
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] (Optional) Celery worker running

## Quick Test

Once server is running, test these endpoints:

### 1. Health Check
```bash
curl http://localhost:8000/
```
Expected: `{"status":"ok","app":"mailmate"}`

### 2. Test Analytics Endpoint
```bash
curl "http://localhost:8000/analytics/test-campaign-id/analytics_logs"
```
Expected: Returns analytics data with rates

### 3. View API Documentation
Open in browser: http://localhost:8000/docs

## Common Issues

### Issue: MongoDB Connection Error

**Fix:**
```bash
# Start MongoDB (if not running)
# Windows: mongod
# Linux: sudo systemctl start mongod
# Mac: brew services start mongodb-community

# Or use Docker:
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Issue: Redis Connection Error

**Fix:**
```bash
# Start Redis
# Linux: sudo systemctl start redis
# Mac: brew services start redis
# Windows: Download Redis or use WSL

# Or use Docker:
docker run -d -p 6379:6379 --name redis redis:latest
```

### Issue: Module Not Found

**Fix:**
```bash
# Make sure venv is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Issue: Port 8000 Already in Use

**Fix:**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001

# Or find and kill the process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill
```

## Running All Services

You'll need **2-3 terminal windows**:

### Terminal 1: FastAPI Server
```bash
cd F:\helyxon\Helyxon-Task3-main
venv\Scripts\activate
uvicorn app.main:app --reload
```

### Terminal 2: Celery Worker (Optional)
```bash
cd F:\helyxon\Helyxon-Task3-main
venv\Scripts\activate
celery -A app.utils.celery_app.celery_app worker --loglevel=info
```

### Terminal 3: ngrok (For webhook testing)
```bash
ngrok http 8000
```

## Next Steps After Starting

1. ✅ **Test the API**: Visit http://localhost:8000/docs
2. ✅ **Test Analytics**: Use `GET /analytics/{campaign_id}/analytics_logs`
3. ✅ **Send Test Email**: Use `POST /dev/test-email`
4. ✅ **Check Webhooks**: Configure SendGrid webhook URL

## Summary

**Minimum to run:**
1. Start MongoDB
2. Create `.env` file
3. Activate venv: `venv\Scripts\activate`
4. Run: `uvicorn app.main:app --reload`

**That's it!** Your API will be available at http://localhost:8000 🎉

