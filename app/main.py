# app/main.py
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth
from app.middleware import RequestLoggerMiddleware, http_exception_handler
from app.contacts import routes as contacts_routes

# import templates & campaigns routers lazily after deps exist
from app.templates import routes as templates_routes
from app.campaigns import routes as campaigns_routes

# CORRECT import: import the APIRouter instance from the module
from app.storage.router import router as storage_router
from app.routes import send_bulk
from app.routes import send_bulk_test
from app.routes import analytics_routes
from app.routes import sendgrid_webhook
from app.routes import unsubscribe as unsubscribe_routes





# 1. Calculate the Project Root
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Define the path to the 'static' folder
STATIC_DIR = BASE_DIR / "static"

# 3. Create it if it doesn't exist
if not STATIC_DIR.exists():
    print(f"⚠️ Static directory missing at {STATIC_DIR}, creating it...")
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "uploads").mkdir(exist_ok=True)

app = FastAPI(title=settings.APP_NAME)

# 4. Mount the directory
print(f"✅ Mounting static files from: {STATIC_DIR}")
print(f"🔧 BACKEND_PUBLIC_URL: {settings.BACKEND_PUBLIC_URL}") 
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# add CORS middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is reachable"}

# add middleware
app.add_middleware(RequestLoggerMiddleware)

# register exception handler
app.add_exception_handler(Exception, http_exception_handler)

# include routers
app.include_router(send_bulk_test.router)
app.include_router(send_bulk.router)
app.include_router(auth.router)
app.include_router(contacts_routes.router)
app.include_router(templates_routes.router)
app.include_router(campaigns_routes.router)
app.include_router(analytics_routes.router)
print("DEBUG: Including sendgrid_webhook router")
app.include_router(sendgrid_webhook.router)
app.include_router(unsubscribe_routes.router)
from app.routes import dashboard_routes
app.include_router(dashboard_routes.router)
app.include_router(storage_router)
@app.get("/")
async def root():
    return {"status": "ok", "app": settings.APP_NAME}
