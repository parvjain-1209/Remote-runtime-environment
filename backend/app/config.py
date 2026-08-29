"""
Centralized Configuration for GDG Remote Runtime Backend & Worker.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Settings:
    """Application and environment settings."""
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/onlinejudge"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_stream_name: str = os.getenv("REDIS_STREAM_NAME", "submission_jobs")
    redis_consumer_group: str = os.getenv("REDIS_CONSUMER_GROUP", "judge_workers")
    worker_consumer_name: str = os.getenv("WORKER_CONSUMER_NAME", "worker-1")
    source_code_max_bytes: int = int(os.getenv("SOURCE_CODE_MAX_BYTES", str(64 * 1024))) # 64 KB limit
    max_request_body_bytes: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(100 * 1024))) # 100 KB payload limit
    stale_job_timeout_seconds: float = float(os.getenv("STALE_JOB_TIMEOUT_SECONDS", "30.0"))
    environment: str = os.getenv("ENVIRONMENT", "development")

    # JWT Authentication Security Settings
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "gdg-remote-runtime-secret-key-change-in-prod-2026")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hours

    # Workspace paths for Docker-out-of-Docker path resolution
    worker_workspace_dir: str = os.getenv("WORKER_WORKSPACE_DIR", "./runtime-workspaces")
    host_workspace_dir_raw: str = os.getenv("HOST_WORKSPACE_DIR", "")

    @property
    def host_workspace_dir(self) -> str:
        if self.host_workspace_dir_raw.strip():
            return self.host_workspace_dir_raw.strip()
        # Fallback to current working directory + runtime-workspaces
        return str(Path.cwd().resolve() / "runtime-workspaces")

    # CORS origins
    cors_origins_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
