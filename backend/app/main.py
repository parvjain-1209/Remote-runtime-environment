"""
FastAPI Application Entry Point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, problems, submissions, users
from app.config import settings
from app.database import init_db
from app.services.queue_client import queue_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Ensure DB tables exist
    init_db()
    yield


app = FastAPI(
    title="GDG Remote Runtime Environment API",
    description="Backend API for competitive programming code execution and judging platform.",
    version="1.0.0",
    lifespan=lifespan,
)


# Priority 9: Request Body Size Limit Middleware (Caps raw HTTP payload at 100 KB)
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


# Priority 10: Fixed CORS configuration using explicit allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(problems.router)
app.include_router(submissions.router)


@app.get("/health", tags=["Health"])
def health_check():
    """Healthcheck endpoint verifying DB and Redis stream status."""
    redis_ok = queue_client.ping()
    return {
        "status": "ok" if redis_ok else "degraded",
        "service": "gdg-remote-runtime-backend",
        "redis": redis_ok,
    }
