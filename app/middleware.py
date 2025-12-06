# app/middleware.py
import time
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("mailmate")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        logger.info(f"start request: {request.method} {request.url.path}")
        try:
            response = await call_next(request)
        except Exception as exc:
            # let the global exception handler deal with it
            logger.exception("Exception during request")
            raise
        duration = (time.time() - start) * 1000
        logger.info(f"completed {request.method} {request.url.path} -> {response.status_code} ({duration:.1f}ms)")
        return response

# simple global exception handler (register in main)
async def http_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
