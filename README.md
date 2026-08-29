# GDG Remote Runtime Environment / Online Judge

A secure, scalable remote code execution and judging platform built for competitive programming and coding evaluations.

> **Status Notice (Phase 6.2 Complete)**: All phases through Phase 6.2 (User Authentication & JWT Authentication) are complete, fully verified, and passing 39/39 unit and integration tests. Features include user registration, bcrypt password hashing, JWT Bearer token authentication, submission ownership tracking, and tabbed frontend login/register UI.

---

## System Architecture

```
                         ┌─────────────────┐
                         │ React Frontend  │  (Port 5173 - Auth Context & JWT Token Storage)
                         └────────┬────────┘
                                  │ HTTP REST (Authorization: Bearer <JWT>)
                                  ▼
                         ┌─────────────────┐
                         │ FastAPI Backend │  (Port 8000 - /auth/*, OAuth2 Bearer, 100KB Cap)
                         └───────┬─────┬───┘
                                 │     │
                              SQL│     │ enqueue (xadd with MAXLEN ~ 10000)
                                 ▼     ▼
                         ┌──────────┐ ┌──────────┐
                         │PostgreSQL│ │  Redis   │  (Redis Streams: submission_jobs)
                         └────┬─────┘ └────┬─────┘
                              │            │
                              │            ▼
                              │     ┌──────────────┐
                              │     │ Python Worker│  (Atomic DB Claim: QUEUED -> COMPILING)
                              │     │  Container   │  (XAUTOCLAIM & Stale Job Recovery)
                              │     └──────┬───────┘
                              │            │
                              │            ▼
                              │     ┌──────────────┐
                              │     │ Docker       │  (Fresh container per testcase)
                              │     │ Sandbox      │  (--network none, --read-only, --user 1000:1000)
                              │     └──────┬───────┘
                              │            │
                              └────────────┘
```

---

## Authentication Endpoints (Phase 6.2)

| Method | Endpoint | Description | Request Body / Header | Response |
|--------|----------|-------------|-----------------------|----------|
| `POST` | `/auth/register` | Register new user account | `{"username", "email", "password"}` | `Token` (`access_token`, `user`) |
| `POST` | `/auth/login` | Authenticate credentials (JSON) | `{"username", "password"}` | `Token` (`access_token`, `user`) |
| `POST` | `/auth/token` | OAuth2 standard form login | Form-data `username`, `password` | `Token` (`access_token`, `user`) |
| `GET` | `/auth/me` | Fetch current user profile | `Authorization: Bearer <token>` | `UserResponse` (`id`, `username`, `email`) |

---

## Quick Start (Docker Compose)

1. **Build Runner Image**:
   ```bash
   docker build -t gdg-runner:latest docker/runner
   ```

2. **Launch All Services**:
   ```bash
   docker compose up -d --build
   ```

3. **Access Applications**:
   - **Frontend UI**: `http://localhost:5173`
   - **Backend API**: `http://localhost:8000`
   - **Health Check**: `http://localhost:8000/health`

---

## Automated Test Suite

Run the complete 39-test suite locally:

```bash
.venv/bin/python3 -m unittest discover -s tests -v
```

All 39 tests pass cleanly.
