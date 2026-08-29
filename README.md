# GDG Remote Runtime Environment / Online Judge

A secure, scalable remote code execution and judging platform built for competitive programming and coding evaluations.

> **Status Notice (Phase 5 Complete)**: All phases (Phase 1 through Phase 5) are complete, fully verified, and passing 34/34 unit and integration tests. The platform features a responsive React + TypeScript frontend, FastAPI backend, Redis Streams job queue, PostgreSQL database, and hardened Docker container execution sandbox.

---

## System Architecture

```
                         ┌─────────────────┐
                         │ React Frontend  │  (Port 5173 - React 18 + Vite + TS)
                         └────────┬────────┘
                                  │ HTTP REST
                                  ▼
                         ┌─────────────────┐
                         │ FastAPI Backend │  (Port 8000 - 100KB Body Cap, CORS)
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

## Features

### Frontend UI (Phase 5)
- **Problem List View**: Searchable list of problems showing time & memory limits.
- **Problem Workspace**: Split-screen problem statement, sample testcases, C++ code editor with line numbers, starter template reset, live polling lifecycle (`QUEUED` -> `COMPILING` -> `RUNNING` -> verdict), per-testcase breakdown matrix, and sanitized error box.
- **Submission History**: Paginated audit log (`GET /submissions/?limit=10&offset=0`) displaying status, runtime metrics, and testcase breakdown details.
- **System Health Indicator**: Header pill monitoring live API and Redis stream status.

### Security Hardening (Phase 4.1)
- `--network none` (complete network isolation)
- `--read-only` root filesystem
- `--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m`
- `--memory=256m` & `--memory-swap=256m`
- `--cpus=1.0` & `--pids-limit=64`
- `--cap-drop=ALL` & `--security-opt=no-new-privileges`
- `--user 1000:1000` (`sandboxuser`)
- No `LocalExecutor` fallback in production (Docker unavailable -> `SYSTEM_ERROR`)
- Error message sanitization (hides host paths, stack traces, Docker internals)

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

Run the complete 34-test suite locally:

```bash
.venv/bin/python3 -m unittest discover -s tests/backend -v
.venv/bin/python3 -m unittest discover -s tests/worker -v
.venv/bin/python3 -m unittest discover -s tests/integration -v
```

All 34 tests pass cleanly.
