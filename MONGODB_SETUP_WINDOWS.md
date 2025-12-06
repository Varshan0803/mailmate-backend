# 🍃 MongoDB Setup for Windows

## Error: `mongosh is not recognized`

This means MongoDB is either:
1. Not installed on your computer
2. Installed but not in your system PATH

## Solutions

### Option 1: Install MongoDB (Recommended)

#### A. Download and Install MongoDB Community Edition

1. **Download MongoDB:**
   - Go to: https://www.mongodb.com/try/download/community
   - Select:
     - Version: Latest (e.g., 7.0)
     - Platform: Windows
     - Package: MSI
   - Click "Download"

2. **Install MongoDB:**
   - Run the downloaded `.msi` file
   - Choose "Complete" installation
   - ✅ **Important**: Check "Install MongoDB as a Service"
   - ✅ Check "Install MongoDB Compass" (GUI tool - optional but helpful)
   - Click "Install"

3. **Verify Installation:**
   ```powershell
   mongod --version
   mongosh --version
   ```

#### B. Add MongoDB to PATH (if installed but not working)

1. Find MongoDB installation folder (usually):
   ```
   C:\Program Files\MongoDB\Server\7.0\bin
   ```

2. Add to PATH:
   - Press `Win + X` → System → Advanced system settings
   - Click "Environment Variables"
   - Under "System variables", find "Path"
   - Click "Edit"
   - Click "New"
   - Add: `C:\Program Files\MongoDB\Server\7.0\bin`
   - Click OK on all windows
   - **Restart PowerShell/Command Prompt**

### Option 2: Use MongoDB Atlas (Cloud - Easiest)

If you don't want to install MongoDB locally:

1. **Sign up for MongoDB Atlas:**
   - Go to: https://www.mongodb.com/cloud/atlas/register
   - Create a free account

2. **Create a Free Cluster:**
   - Choose "M0 FREE" tier
   - Choose a cloud provider and region
   - Click "Create Cluster"

3. **Get Connection String:**
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Copy the connection string (looks like):
     ```
     mongodb+srv://username:password@cluster.mongodb.net/
     ```

4. **Update your `.env` file:**
   ```env
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/mailmate?retryWrites=true&w=majority
   ```

### Option 3: Use Docker (If you have Docker installed)

```powershell
# Pull MongoDB image
docker pull mongo

# Run MongoDB container
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Check if running
docker ps

# Connect to MongoDB
docker exec -it mongodb mongosh
```

### Option 4: Use MongoDB Portable (No Installation)

If you can't install MongoDB:

1. Download MongoDB Community Edition (ZIP version)
2. Extract to a folder (e.g., `C:\mongodb`)
3. Create data directory:
   ```powershell
   mkdir C:\data\db
   ```
4. Run MongoDB manually:
   ```powershell
   cd C:\mongodb\bin
   .\mongod.exe --dbpath=C:\data\db
   ```

## Quick Check Commands

After installation, test:

```powershell
# Check if MongoDB service is running
Get-Service -Name MongoDB

# Start MongoDB service (if installed as service)
Start-Service MongoDB

# Or try old command (might work if older MongoDB)
mongo --version
```

## For Your Project

Once MongoDB is running, your `.env` should have:

```env
MONGO_URI=mongodb://localhost:27017/mailmate
```

Then your FastAPI app will connect automatically!

## Troubleshooting

### If MongoDB service won't start:
```powershell
# Check MongoDB logs
# Usually at: C:\Program Files\MongoDB\Server\7.0\log\mongod.log

# Or start manually to see errors
cd "C:\Program Files\MongoDB\Server\7.0\bin"
.\mongod.exe
```

### If port 27017 is already in use:
```powershell
# Find what's using port 27017
netstat -ano | findstr :27017

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

## Recommendation

**For quick start:** Use **MongoDB Atlas (Option 2)** - it's free and works immediately!

**For development:** Install MongoDB locally (Option 1) - better for offline work.

