# Phase 3 Design Document: Hardened Docker Sandbox Architecture

This document specifies the technical design, security policy, and operational semantics of the **Phase 3 Hardened Docker Sandbox** for the GDG Remote Runtime Environment / Online Judge.

---

## 1. Architecture Overview

```
                          ┌────────────────────────┐
                          │    Submission Job      │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │  SubmissionWorkspace   │  (Host tempdir /sandbox)
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │  Docker Compilation    │  (gdg-runner /sandbox:rw)
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │     Judge Engine       │
                          └───────────┬────────────┘
                                      │
                         For each testcase via Executor Protocol
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │     DockerExecutor     │
                          └───────────┬────────────┘
                                      │
               Fresh Container per Testcase: judge-{sub}-{idx}-{uuid}
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │ Ephemeral Docker Run   │  (gdg-runner /sandbox:ro)
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │    Output & Verdict    │  (ACCEPTED, TLE, MLE, etc.)
                          └────────────────────────┘
```

The system strictly decouples the high-level judging logic from the underlying execution environment via the `Executor` protocol interface.

---

## 2. Docker Security Policy (`SandboxPolicy`)

All execution and compilation containers are spawned with an immutable security policy configured in `worker/sandbox_policy.py`:

| Parameter | Configuration | Security Objective |
| :--- | :--- | :--- |
| **Network Isolation** | `--network none` | Completely isolates container from network interfaces. |
| **Root Filesystem** | `--read-only` | Prevents modifications to container filesystem. |
| **Temporary FS** | `--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m` | Minimal non-executable temporary storage. |
| **CPU Quota** | `--cpus=1.0` | Prevents CPU exhaustion attacks. |
| **Memory Limit** | `--memory=256m` | Caps RAM allocation to 256 MB. |
| **Swap Limit** | `--memory-swap=256m` | Disables additional swap memory to enforce hard OOM limits. |
| **PID Limit** | `--pids-limit=64` | Prevents process bombs (e.g. `fork()` bombs). |
| **Capabilities** | `--cap-drop=ALL` | Drops all Linux capabilities. |
| **Privileges** | `--security-opt=no-new-privileges` | Prevents privilege escalation (`suid`/`sgid`). |
| **File Descriptors** | `--ulimit nofile=64:64` | Limits max open files per container. |
| **Core Dumps** | `--ulimit core=0:0` | Disables core dump generation. |
| **User Identity** | `--user 1000:1000` | Runs processes under unprivileged user `sandboxuser`. |

### Forbidden Settings
- `--privileged`
- `--network host` / `--pid host` / `--ipc host`
- `--security-opt seccomp=unconfined`
- Docker socket (`/var/run/docker.sock`) mounting inside sandbox containers.

---

## 3. Compile Architecture

To protect the host filesystem from preprocessor attacks (e.g. `#include </etc/shadow>`), compilation is performed inside Docker:

- **Input**: `source.cpp` written to `SubmissionWorkspace`.
- **Mount**: Host workspace directory mounted as `/sandbox:rw`.
- **Command**: `g++ -std=c++17 -O2 /sandbox/source.cpp -o /sandbox/main`
- **Timeout**: 10.0 seconds.
- **Output Cap**: 64 KB captured stdout/stderr.
- **Container Cleanup**: Container removed immediately after compilation exits.

---

## 4. Execution Architecture & Container Lifecycle

For every testcase, `DockerExecutor` launches a **fresh container instance**:

1. **Unique Name Generation**: `judge-{submission_id}-{test_index}-{uuid}`
2. **Mount**: Workspace directory mounted as read-only (`/sandbox:ro`).
3. **Stdin Streaming**: Testcase input piped directly through container `stdin`.
4. **Execution Command**: `/sandbox/main`
5. **Output Streaming**: Streams `stdout` and `stderr` incrementally up to **1 MB** limit (`limits.max_output_bytes`). If limit is reached, container is killed (`docker kill`), flagging `OUTPUT_LIMIT_EXCEEDED`.
6. **Timeout Enforcement**: If wall-clock duration exceeds **2.0 seconds** (`limits.timeout_s`), executes `docker kill <container_name>`, reaps process, flagging `TIME_LIMIT_EXCEEDED`.
7. **Post-Execution Inspection**: Before container removal, executes `docker inspect --format '{{.State.OOMKilled}}' <container_name>`. If `True`, flags `MEMORY_LIMIT_EXCEEDED`.
8. **Container Removal**: Container removed via `docker rm -f <container_name>` inside a `finally` block.

---

## 5. Exit Code & Verdict Mapping Table

| Event / Return Code | `OOMKilled` | `timed_out` | Verdict Status |
| :--- | :--- | :--- | :--- |
| **Docker CLI 125 / Daemon Error** | Any | Any | `SYSTEM_ERROR` |
| **Runner Image Missing** | Any | Any | `SYSTEM_ERROR` |
| **Container OOM Killed** | `True` | Any | `MEMORY_LIMIT_EXCEEDED` |
| **Wall-Clock Timeout** | Any | `True` | `TIME_LIMIT_EXCEEDED` |
| **Output Cap Exceeded** | Any | Any | `OUTPUT_LIMIT_EXCEEDED` |
| **Exit Code 137 (SIGKILL)** | `False` | `False` | `RUNTIME_ERROR` |
| **Exit Code 139 (SIGSEGV)** | `False` | `False` | `RUNTIME_ERROR` |
| **Exit Code 134 (SIGABRT)** | `False` | `False` | `RUNTIME_ERROR` |
| **Exit Code 136 (SIGFPE)** | `False` | `False` | `RUNTIME_ERROR` |
| **Exit Code > 0 (Normal Exit)**| `False` | `False` | `RUNTIME_ERROR` |
| **Exit Code 0 (Match)** | `False` | `False` | `ACCEPTED` |
| **Exit Code 0 (Mismatch)** | `False` | `False` | `WRONG_ANSWER` |

---

## 6. Security Testing Strategy

The test suite in `tests/worker/test_docker_executor.py` validates:

1. **Docker Command Generation**: Verifies correct security arguments.
2. **Docker Daemon Failure**: Simulates CLI/daemon failures returning `SYSTEM_ERROR`.
3. **Execution Lifecycle**: Validates inspect and cleanup behavior.
4. **Infinite Loop**: Validates timeout and process group termination (`TIME_LIMIT_EXCEEDED`).
5. **Memory Exhaustion**: Validates `OOMKilled` detection (`MEMORY_LIMIT_EXCEEDED`).
6. **Excessive Output**: Validates buffer limits (`OUTPUT_LIMIT_EXCEEDED`).
7. **Network Isolation**: Validates network socket restrictions (`--network none`).
8. **Read-Only Root FS**: Validates write protection (`--read-only`).
9. **Non-Root Execution**: Validates `UID != 0` (`sandboxuser`).
10. **Stale Container Cleanup**: Guarantees zero leftover `judge-*` containers.
