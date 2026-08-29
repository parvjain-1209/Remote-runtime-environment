# GDG Remote Runtime Environment / Online Judge

A secure, scalable remote code execution and judging platform built for competitive programming and coding evaluations.

> **Status Notice (Phase 6.3 Complete)**: All phases through Phase 6.3 (User Statistics & Personal Dashboard) are complete, fully verified, and passing 44/44 unit and integration tests. Features include user registration, JWT authentication, personal solver statistics (`/users/me/stats`), difficulty breakdown ratios (`Easy`, `Medium`, `Hard`), verdict distribution metrics, and a frontend User Dashboard.

---

## System Architecture

```
                         ┌─────────────────┐
                         │ React Frontend  │  (Port 5173 - User Dashboard & Auth Context)
                         └────────┬────────┘
                                  │ HTTP REST (Authorization: Bearer <JWT>)
                                  ▼
                         ┌─────────────────┐
                         │ FastAPI Backend │  (Port 8000 - /users/me/stats, /auth/*, 100KB Cap)
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

## User Statistics Endpoints (Phase 6.3)

| Method | Endpoint | Description | Auth Required | Response |
|--------|----------|-------------|---------------|----------|
| `GET` | `/users/me/stats` | Aggregated user solver metrics, difficulty ratios, and verdict counts | Yes (Bearer Token) | `UserStatsResponse` |
| `GET` | `/users/me/submissions` | Paginated submission history belonging strictly to current user | Yes (Bearer Token) | `SubmissionListResponse` |

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

Run the complete 44-test suite locally:

```bash
.venv/bin/python3 -m unittest discover -s tests -v
```

All 44 tests pass cleanly.
