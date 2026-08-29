# GDG Remote Runtime Environment / Online Judge

A secure, scalable remote code execution and judging platform built for competitive programming and coding evaluations.

> **Status Notice (Phase 6.4 Complete)**: All phases through Phase 6.4 (Multi-Language Support: C++, Python 3, Java 21) are complete, fully verified, and passing 48/48 unit and integration tests. Features include multi-language Docker sandboxed execution, Python syntax checking (`py_compile`), Java compilation (`javac Main.java`), 2.0x time limit scaling for interpreted/JVM runtimes, and frontend language selector with boilerplate starter templates.

---

## System Architecture

```
                         ┌─────────────────┐
                         │ React Frontend  │  (Port 5173 - Language Selector: C++, Python, Java)
                         └────────┬────────┘
                                  │ HTTP REST (Authorization: Bearer <JWT>)
                                  ▼
                         ┌─────────────────┐
                         │ FastAPI Backend │  (Port 8000 - /submissions/, /users/me/stats)
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

## Supported Languages (Phase 6.4)

| Language | Canonical Name | Compiler / Validation | Execution Command | Time Limit Multiplier |
|----------|----------------|-----------------------|-------------------|-----------------------|
| C++ (g++ 13) | `cpp` | `g++ -O3 main.cpp -o main` | `/sandbox/main` | 1.0x |
| Python (3.11) | `python` | `python3 -m py_compile main.py` | `python3 /sandbox/main.py` | 2.0x |
| Java (OpenJDK 21) | `java` | `javac Main.java` | `java -Xmx256m -cp /sandbox Main` | 2.0x |

---

## Quick Start (Docker Compose)

1. **Build Multi-Language Runner Image**:
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

Run the complete 48-test suite locally:

```bash
.venv/bin/python3 -m unittest discover -s tests -v
```

All 48 tests pass cleanly.
