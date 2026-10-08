import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app import admin, auth, complaints
from app.config import ROOT, settings
from app.db import SessionLocal
from app.modules import import_models, mount_modules, synchronize

logger = logging.getLogger(__name__)
import_models()
local_limits = defaultdict(deque)
redis = Redis.from_url(settings().redis_url) if settings().redis_url else None


@asynccontextmanager
async def lifespan(app):
    with SessionLocal() as db:
        synchronize(db)
    yield
    if redis:
        await redis.aclose()


app = FastAPI(
    title="Nellai Green & Civic API",
    version="0.1.0",
    description="API-first civic and environmental platform. See docs/module-development.md to extend it.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers_and_limits(request: Request, call_next):
    if int(request.headers.get("content-length", "0")) > (settings().max_upload_mb + 1) * 1024 * 1024:
        return JSONResponse({"detail": "Request is too large"}, status_code=413)
    ip = request.client.host if request.client else "unknown"
    group = "auth" if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/register"} else "api"
    limit = 15 if group == "auth" else 240
    key = f"nellai:rate:{ip}:{group}"
    if redis:
        try:
            count = await redis.eval(
                "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",
                1,
                key,
            )
        except Exception:
            logger.exception("Rate-limit store unavailable")
            return JSONResponse({"detail": "Service temporarily unavailable"}, status_code=503)
    else:
        cutoff = time.monotonic() - 60
        bucket = local_limits[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        bucket.append(time.monotonic())
        count = len(bucket)
        if len(local_limits) > 10000:
            for old_key in list(local_limits):
                if local_limits[old_key][-1] < cutoff:
                    del local_limits[old_key]
    if count > limit:
        return JSONResponse(
            {"detail": "Too many requests. Try again in one minute."},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        {"detail": "A conflicting record already exists or a referenced record is missing"}, status_code=409
    )


@app.exception_handler(StaleDataError)
async def stale_error(request, exc):
    return JSONResponse(
        {"detail": "This record changed concurrently. Reload and try again."}, status_code=409
    )


@app.get("/health", tags=["Health"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "version": "0.1.0",
        "database": "postgresql"
        if settings().database_url.startswith("postgresql")
        else "sqlite-development",
    }


for router in [auth.router, complaints.router, admin.router]:
    app.include_router(router, prefix="/api/v1")
mount_modules(app)

# Local demo serves the compiled web app from the same origin. Docker uses nginx.
if (ROOT / "web" / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "web" / "dist", html=True), name="web")
