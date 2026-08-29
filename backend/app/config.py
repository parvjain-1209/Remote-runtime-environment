"""
Centralized Configuration for GDG Remote Runtime Backend & Worker.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

is_in_docker = os.path.exists("/.dockerenv")


@dataclass
class Settings:
    """Application and environment settings."""
    database_url_raw: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@postgres:5432/onlinejudge"
            if is_in_docker
            else "postgresql://postgres:postgres@localhost:5432/onlinejudge",
        )
    )
    redis_url_raw: str = field(
        default_factory=lambda: os.getenv(
            "REDIS_URL",
            "redis://redis:6379/0" if is_in_docker else "redis://localhost:6379/0",
        )
    )
    redis_stream_name: str = field(default_factory=lambda: os.getenv("REDIS_STREAM_NAME", "submission_jobs"))
    redis_consumer_group: str = field(default_factory=lambda: os.getenv("REDIS_CONSUMER_GROUP", "judge_workers"))
    worker_consumer_name: str = field(default_factory=lambda: os.getenv("WORKER_CONSUMER_NAME", "worker-1"))
    source_code_max_bytes: int = field(default_factory=lambda: int(os.getenv("SOURCE_CODE_MAX_BYTES", str(64 * 1024)))) # 64 KB limit
    max_request_body_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_REQUEST_BODY_BYTES", str(100 * 1024)))) # 100 KB payload limit
    stale_job_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("STALE_JOB_TIMEOUT_SECONDS", "30.0")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    # JWT Authentication Security Settings
    jwt_secret_key: str = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", "gdg-remote-runtime-secret-key-change-in-prod-2026"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))) # 24 hours

    # Workspace paths for Docker-out-of-Docker path resolution
    worker_workspace_dir: str = field(default_factory=lambda: os.getenv("WORKER_WORKSPACE_DIR", "./runtime-workspaces"))
    host_workspace_dir_raw: str = field(default_factory=lambda: os.getenv("HOST_WORKSPACE_DIR", ""))

    cors_origins_raw: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))

    @property
    def database_url(self) -> str:
        url = self.database_url_raw
        if is_in_docker and "@localhost:" in url:
            url = url.replace("@localhost:", "@postgres:")
        if is_in_docker and "@127.0.0.1:" in url:
            url = url.replace("@127.0.0.1:", "@postgres:")
        return url

    @property
    def redis_url(self) -> str:
        url = self.redis_url_raw
        if is_in_docker and "redis://localhost:" in url:
            url = url.replace("redis://localhost:", "redis://redis:")
        if is_in_docker and "redis://127.0.0.1:" in url:
            url = url.replace("redis://127.0.0.1:", "redis://redis:")
        return url

    @property
    def host_workspace_dir(self) -> str:
        if self.host_workspace_dir_raw.strip():
            return self.host_workspace_dir_raw.strip()
        return str(Path.cwd().resolve() / "runtime-workspaces")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
