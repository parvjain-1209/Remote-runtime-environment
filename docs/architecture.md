# GDG Remote Runtime Environment — Architecture & Production System Design

## 1. System Overview

The **GDG Remote Runtime Environment** is a production-grade, secure, multi-tenant code execution platform designed for competitive programming and automated grading. The system safely compiles and executes code written in C++, Python 3, and Java 21 inside ephemeral, isolated Docker judge containers.

```
                           ┌──────────────────┐
                           │  React Frontend  │  (Vite + TypeScript SPA, Port 5173/80)
                           └────────┬─────────┘
                                    │ HTTP REST API (JWT Authorization)
                                    ▼
                           ┌──────────────────┐
                           │ FastAPI Backend  │  (Port 8000)
                           └────────┬─────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
               SQL│                                   │ XADD MAXLEN 10000
                  ▼                                   ▼
         ┌──────────────────┐               ┌──────────────────┐
         │ PostgreSQL 16 DB │               │  Redis Stream    │
         └────────┬─────────┘               └────────┬─────────┘
                  │                                  │
                  │ Atomic DB Status Claim           │ Consumer Group Read
                  └─────────────────┬────────────────┘
                                    ▼
                           ┌──────────────────┐
                           │  Python Worker   │  (Background Processing Service)
                           └────────┬─────────┘
                                    │ Ephemeral `docker run` per testcase
                                    ▼
                           ┌──────────────────┐
                           │  Docker Sandbox  │  (gdg-runner: g++, python3, openjdk21)
                           └──────────────────┘
```

---

## 2. Core Components

### 2.1 Backend (FastAPI API Layer)
- **Role**: Validates submission requests, manages authentication (bcrypt + JWT), seeds problem catalogs, and exposes system telemetry metrics.
- **Endpoints**:
  - `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
  - `GET /problems/`, `GET /problems/{id}`
  - `POST /submissions/`, `GET /submissions/{id}`
  - `GET /users/me/stats`
  - `GET /metrics` (System observability & telemetry)
  - `GET /health` (DB & Redis stream status)

### 2.2 Redis Queue (Asynchronous Stream Broker)
- **Role**: Decouples API submission requests from asynchronous worker execution.
- **Consumer Group**: `worker_group` consuming from stream `submission_jobs`.
- **Reliability Features**: Stream capping (`MAXLEN ~ 10000`), `XAUTOCLAIM` for abandoned message recovery, and idempotency checks.

### 2.3 Worker Engine (Background Judge Worker)
- **Role**: Atomically claims queued submissions (`QUEUED` -> `COMPILING`), invokes the judge pipeline, and persists verdicts (`ACCEPTED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `OUTPUT_LIMIT_EXCEEDED`, `COMPILATION_ERROR`, `RUNTIME_ERROR`, `SYSTEM_ERROR`).
- **Production Guardrail**: Requires Docker CLI accessibility. If Docker is unavailable, immediately fails submission with `SYSTEM_ERROR` and sanitizes error logs without exposing host internals.

### 2.4 Docker Sandbox Container (`gdg-runner:latest`)
- **Base Image**: Alpine Linux 3.19.
- **Installed Tools**: `g++` (13.2), `python3` (3.11), `openjdk21-jdk` (OpenJDK 21).
- **Security Containment Flags**:
  - `--read-only` (Root filesystem is read-only except workspace volume)
  - `--network none` (Complete outbound network exfiltration block)
  - `--pids-limit 64` (Process/fork bomb containment)
  - `--memory 256m --memory-swap 256m` (Strict memory ceiling)
  - `--user 1000:1000` (Unprivileged non-root execution)
  - `--cap-drop ALL` (Drops Linux capabilities)

---

## 3. Threat Containment Matrix (Phase 6.5 Verified)

| Attack Vector | Malicious Strategy | Containment Mechanism | Outcome Verdict |
|---------------|--------------------|------------------------|-----------------|
| **Fork Bomb** | `while(1) fork();` | `--pids-limit 64` | `RUNTIME_ERROR` / Process Terminated |
| **Network Exfiltration** | Outbound socket connection / `curl` | `--network none` | Socket Connection Failed |
| **Host File Traversal** | Reading `/etc/shadow` or `docker.sock` | Read-only container, unprivileged user, isolated workspace | Access Denied / File Not Found |
| **Memory Spike** | Allocating > 256MB RAM | `--memory 256m --memory-swap 256m` | `MEMORY_LIMIT_EXCEEDED` |
| **Output Flooding** | Infinite `cout << "A"` stream | `max_output_bytes = 64KB` buffer cap | `OUTPUT_LIMIT_EXCEEDED` |
| **Path Leaking** | Inducing internal stack traces | `sanitize_error_message()` filter | Host paths replaced with generic message |

---

## 4. Production Deployment & Scaffolding

### 4.1 Deployment Commands

1. **Clone repository & prepare environment variables**:
   ```bash
   cp .env.production.example .env.production
   ```

2. **Build runner judge image**:
   ```bash
   docker build -t gdg-runner:latest docker/runner
   ```

3. **Launch production Docker Compose stack**:
   ```bash
   docker compose up -d --build
   ```

4. **Verify cluster status**:
   ```bash
   docker compose ps
   curl http://localhost:8000/health
   curl http://localhost:8000/metrics
   ```

---

## 5. Observability Telemetry API (`GET /metrics`)

Sample JSON response from production monitoring endpoint:

```json
{
  "status": "HEALTHY",
  "total_submissions": 42,
  "accepted_submissions": 35,
  "acceptance_rate_percent": 83.33,
  "verdict_breakdown": {
    "QUEUED": 0,
    "COMPILING": 0,
    "RUNNING": 0,
    "ACCEPTED": 35,
    "WRONG_ANSWER": 4,
    "TIME_LIMIT_EXCEEDED": 1,
    "MEMORY_LIMIT_EXCEEDED": 1,
    "OUTPUT_LIMIT_EXCEEDED": 1,
    "COMPILATION_ERROR": 0,
    "RUNTIME_ERROR": 0,
    "SYSTEM_ERROR": 0
  },
  "queue_metrics": {
    "redis_status": "HEALTHY",
    "pending_queue_length": 0,
    "stream_name": "submission_jobs"
  },
  "database_status": "CONNECTED"
}
```
