# GDG Remote Runtime Environment / Online Judge

A secure, scalable remote code execution and judging platform built for competitive programming and coding evaluations.

> **Status Notice (Phase 6 Finalized & Production Ready)**: All phases through Phase 6.6 (Security Hardening, Penetration Testing, Observability, Multi-Language Support, and Production Deployment Scaffolding) are complete, fully verified, and passing 54/54 automated tests. Features include multi-language Docker sandboxed execution (C++, Python 3, Java 21), hostile code security penetration suite, real-time platform telemetry (`/metrics`), and production Docker Compose deployment scripts.

---

## System Architecture

```
                         ┌─────────────────┐
                         │ React Frontend  │  (Port 5173 - Language Selector: C++, Python, Java)
                         └────────┬────────┘
                                  │ HTTP REST (Authorization: Bearer <JWT>)
                                  ▼
                         ┌─────────────────┐
                         │ FastAPI Backend │  (Port 8000 - /submissions/, /users/me/stats, /metrics)
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
                              │     │  Container   │  (Language Strategy: C++, Python, Java)
                              │     └──────┬───────┘
                              │            │
                              │            ▼
                              │     ┌──────────────┐
                              │     │ Docker       │  (Fresh container per testcase)
                              │     │ Sandbox      │  (gdg-runner: g++, python3, openjdk21)
                              │     └──────┬───────┘
                              │            │
                              └────────────┘
```

---

## Supported Languages & Resource Controls

| Language | Canonical Name | Compiler / Validation | Execution Command | Time Limit Multiplier |
|----------|----------------|-----------------------|-------------------|-----------------------|
| C++ (g++ 13) | `cpp` | `g++ -O3 main.cpp -o main` | `/sandbox/main` | 1.0x |
| Python (3.11) | `python` | `python3 -m py_compile main.py` | `python3 /sandbox/main.py` | 2.0x |
| Java (OpenJDK 21) | `java` | `javac Main.java` | `java -Xmx256m -cp /sandbox Main` | 2.0x |

---

## Production Security & Penetration Containment (Phase 6.5)

- **Fork Bomb / Process Exhaustion**: Contained by `--pids-limit 64`.
- **Network Exfiltration Block**: Enforced by `--network none`.
- **Host Filesystem Traversal**: Blocked by read-only root mount `--read-only` and unprivileged user sandbox.
- **Memory Ceiling**: Strict `--memory 256m --memory-swap 256m` limits.
- **Output Flooding**: Controlled by `64 KB` stdout output cap.
- **Error Sanitization**: Replaces stack traces and internal host paths with sanitized error messages.

---

## Platform Observability & Telemetry (`GET /metrics`)

Access real-time platform metrics at `http://localhost:8000/metrics`:
- Total Submissions & Accepted Count
- Overall Acceptance Rate Percentage
- Per-Verdict Breakdown Matrix
- Redis Queue Depth & Status
- Database Connectivity Health

---

## Production Quick Start

1. **Configure Production Environment**:
   ```bash
   cp .env.production.example .env.production
   ```

2. **Build Multi-Language Runner Image**:
   ```bash
   docker build -t gdg-runner:latest docker/runner
   ```

3. **Launch Production Container Stack**:
   ```bash
   docker compose up -d --build
   ```

4. **Verify Application Services**:
   - **Frontend UI**: `http://localhost:5173`
   - **Backend API Docs**: `http://localhost:8000/docs`
   - **System Telemetry**: `http://localhost:8000/metrics`
   - **Health Check**: `http://localhost:8000/health`

---

## Automated Test Suites (54/54 Passed)

Run the full automated test suite (Backend, Worker, Integration, Security):

```bash
.venv/bin/python3 -m unittest discover -s tests/backend -v
.venv/bin/python3 -m unittest discover -s tests/worker -v
.venv/bin/python3 -m unittest discover -s tests/integration -v
.venv/bin/python3 -m unittest discover -s tests/security -v
```

All 54 tests pass cleanly with 0 regressions.
