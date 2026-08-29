"""
FastAPI Application Entry Point.
"""

import subprocess
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, metrics, problems, submissions, users
from app.config import settings
from app.database import init_db
from app.services.queue_client import queue_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    init_db()
    # Spawn the background execution worker on startup
    worker_proc = subprocess.Popen(
        [sys.executable, "worker/worker.py"],
        env={**sys.modules['os'].environ, "PYTHONPATH": "."}
    )
    yield
    worker_proc.terminate()


app = FastAPI(
    title="GDG Remote Runtime Environment API",
    description="Backend API for competitive programming code execution and judging platform.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH"]:
        content_length = request.headers.get("content-length")
        max_bytes = settings.max_request_body_bytes
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request body size exceeds maximum limit of {max_bytes} bytes."},
                    )
            except ValueError:
                pass
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(metrics.router)


@app.get("/health", tags=["Health"])
def health_check():
    redis_ok = queue_client.ping()
    return {
        "status": "ok" if redis_ok else "degraded",
        "service": "gdg-remote-runtime-backend",
        "redis": redis_ok,
    }
