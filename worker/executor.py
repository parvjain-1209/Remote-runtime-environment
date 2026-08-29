"""
Executor Module.

Defines the Executor Protocol interface, LocalExecutor for local & unprivileged cloud testing/execution,
and DockerExecutor for hardened multi-language containerized execution (C++, Python, Java).
"""

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from sandbox_policy import DEFAULT_SANDBOX_POLICY, ExecutionLimits, SandboxPolicy

logger = logging.getLogger("worker.executor")


@dataclass(frozen=True)
class ExecutionResult:
    """
    Structured outcome of binary / script execution against a single testcase.
    """
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
    timed_out: bool
    output_limit_exceeded: bool
    oom_killed: bool = False
    is_docker_system_error: bool = False
    signal_number: Optional[int] = None
    error_message: Optional[str] = None


class Executor(ABC):
    """
    Abstract Protocol interface for running compiled binaries / scripts.
    """

    @abstractmethod
    def run(
        self,
        binary_path: Union[str, Path],
        stdin_data: str,
        limits: Optional[ExecutionLimits] = None,
        language: str = "cpp",
    ) -> ExecutionResult:
        """
        Executes code with stdin data under specified resource limits and language settings.
        """
        pass


def find_executable(binary_name: str, fallback_paths: Optional[List[str]] = None) -> str:
    """
    Resolves binary executable path using shutil.which and absolute fallback paths.
    """
    which_path = shutil.which(binary_name)
    if which_path and Path(which_path).exists():
        return which_path

    if fallback_paths:
        for fp in fallback_paths:
            if Path(fp).exists() and os.access(fp, os.X_OK):
                return fp

    return binary_name


class LocalExecutor(Executor):
    """
    Cloud-resilient executor running compiled binaries and scripts directly on host via subprocess.
    Requires no root privileges or Docker daemon.
    """

    def run(
        self,
        binary_path: Union[str, Path],
        stdin_data: str,
        limits: Optional[ExecutionLimits] = None,
        language: str = "cpp",
    ) -> ExecutionResult:
        if limits is None:
            limits = ExecutionLimits()

        bin_path = Path(binary_path).resolve()
        cwd = bin_path.parent
        lang = language.lower()

        if not bin_path.exists():
            err_msg = f"Target binary path '{bin_path}' does not exist."
            logger.error(f"[LocalExecutor] {err_msg}")
            print(f"[LocalExecutor ERROR] {err_msg}", file=sys.stderr)
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                error_message=err_msg,
            )

        if lang == "python":
            py_bin = find_executable("python3", [sys.executable, "/usr/bin/python3", "/usr/local/bin/python3"])
            exec_cmd = [py_bin, str(bin_path)]
            timeout_s = limits.timeout_s * 2.0
        elif lang == "java":
            java_bin = find_executable("java", ["/usr/bin/java", "/usr/local/bin/java", "/usr/lib/jvm/default-java/bin/java"])
            exec_cmd = [java_bin, "-Xmx256m", "-cp", str(cwd), "Main"]
            timeout_s = limits.timeout_s * 2.0
        else:  # cpp
            exec_cmd = [str(bin_path)]
            timeout_s = limits.timeout_s

        stdout_chunks = []
        stderr_chunks = []
        stdout_size = 0
        stderr_size = 0

        output_exceeded = threading.Event()
        lock = threading.Lock()

        # Safely attempt process group creation (handling non-root / restricted container environments)
        proc = None
        has_pgid = False

        try:
            proc = subprocess.Popen(
                exec_cmd,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            has_pgid = True
        except (PermissionError, OSError) as pe:
            logger.warning(f"[LocalExecutor] start_new_session=True failed ({pe}), retrying without process group session.")
            try:
                proc = subprocess.Popen(
                    exec_cmd,
                    cwd=cwd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                has_pgid = False
            except Exception as ex:
                tb_str = traceback.format_exc()
                logger.error(f"[LocalExecutor] Failed to launch process '{exec_cmd}': {ex}\n{tb_str}")
                print(f"[LocalExecutor ERROR] Failed to launch process '{exec_cmd}': {ex}\n{tb_str}", file=sys.stderr)
                return ExecutionResult(
                    stdout="",
                    stderr=f"LocalExecutor process launch error: {str(ex)}",
                    return_code=-1,
                    duration_ms=0.0,
                    timed_out=False,
                    output_limit_exceeded=False,
                    error_message=f"Failed to launch process: {str(ex)}",
                )
        except Exception as ex:
            tb_str = traceback.format_exc()
            logger.error(f"[LocalExecutor] Unexpected launch exception for '{exec_cmd}': {ex}\n{tb_str}")
            print(f"[LocalExecutor ERROR] Unexpected launch exception for '{exec_cmd}': {ex}\n{tb_str}", file=sys.stderr)
            return ExecutionResult(
                stdout="",
                stderr=f"LocalExecutor process launch error: {str(ex)}",
                return_code=-1,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                error_message=f"Failed to launch process: {str(ex)}",
            )

        pgid = proc.pid

        def kill_process_group():
            if has_pgid:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                    return
                except (OSError, ProcessLookupError, PermissionError):
                    pass
            try:
                proc.kill()
            except (OSError, ProcessLookupError, PermissionError):
                pass

        def read_pipe(pipe, chunks_list, is_stdout):
            nonlocal stdout_size, stderr_size
            try:
                while True:
                    chunk = pipe.read(4096)
                    if not chunk:
                        break
                    with lock:
                        chunk_len = len(chunk.encode("utf-8"))
                        if is_stdout:
                            stdout_size += chunk_len
                        else:
                            stderr_size += chunk_len

                        if stdout_size + stderr_size > limits.max_output_bytes:
                            output_exceeded.set()
                            allowed = max(0, limits.max_output_bytes - (stdout_size + stderr_size - chunk_len))
                            chunks_list.append(chunk[:allowed])
                            kill_process_group()
                            break
                        else:
                            chunks_list.append(chunk)
            except Exception as ex:
                logger.debug(f"[LocalExecutor] Pipe read notice: {ex}")
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        t_out = threading.Thread(target=read_pipe, args=(proc.stdout, stdout_chunks, True))
        t_err = threading.Thread(target=read_pipe, args=(proc.stderr, stderr_chunks, False))
        t_out.daemon = True
        t_err.daemon = True
        t_out.start()
        t_err.start()

        if stdin_data and proc.stdin:
            try:
                proc.stdin.write(stdin_data)
                proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass
        if proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass

        start_time = time.monotonic()
        timed_out = False

        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_group()
            try:
                proc.wait(timeout=1.0)
            except Exception:
                pass
        finally:
            kill_process_group()

        t_out.join(timeout=1.0)
        t_err.join(timeout=1.0)

        duration_ms = (time.monotonic() - start_time) * 1000.0

        full_stdout = "".join(stdout_chunks)
        full_stderr = "".join(stderr_chunks)
        ret_code = proc.returncode if proc.returncode is not None else -1

        sig_num: Optional[int] = None
        if ret_code < 0:
            sig_num = abs(ret_code)

        err_msg: Optional[str] = None
        if timed_out:
            err_msg = f"Execution timed out after {timeout_s} seconds."
        elif output_exceeded.is_set():
            err_msg = f"Output size limit ({limits.max_output_bytes} bytes) exceeded."
        elif sig_num is not None:
            err_msg = f"Process terminated by signal {sig_num}."

        return ExecutionResult(
            stdout=full_stdout,
            stderr=full_stderr,
            return_code=ret_code,
            duration_ms=round(duration_ms, 2),
            timed_out=timed_out,
            output_limit_exceeded=output_exceeded.is_set(),
            signal_number=sig_num,
            error_message=err_msg,
        )


class DockerExecutor(Executor):
    """
    Hardened Docker-based container executor supporting C++, Python, and Java.
    """

    def __init__(
        self,
        policy: Optional[SandboxPolicy] = None,
        submission_id: str = "default",
        test_index: int = 0,
    ):
        self.policy = policy or DEFAULT_SANDBOX_POLICY
        self.submission_id = submission_id
        self.test_index = test_index

    def run(
        self,
        binary_path: Union[str, Path],
        stdin_data: str,
        limits: Optional[ExecutionLimits] = None,
        language: str = "cpp",
    ) -> ExecutionResult:
        if limits is None:
            limits = self.policy.execution_limits

        bin_path = Path(binary_path).resolve()
        ws_dir = bin_path.parent
        lang = language.lower()

        if not bin_path.exists():
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                error_message=f"Target file '{bin_path}' not found.",
            )

        unique_id = uuid.uuid4().hex[:8]
        container_name = f"judge-{self.submission_id}-{self.test_index}-{unique_id}"

        docker_args = self.policy.to_docker_args(
            container_name=container_name,
            workspace_dir=ws_dir,
            mount_read_only=True,
        )

        if lang == "python":
            exec_args = [self.policy.runner_image, "python3", "/sandbox/main.py"]
            timeout_s = limits.timeout_s * 2.0
        elif lang == "java":
            exec_args = [self.policy.runner_image, "java", "-Xmx256m", "-cp", "/sandbox", "Main"]
            timeout_s = limits.timeout_s * 2.0
        else:  # cpp
            exec_args = [self.policy.runner_image, "/sandbox/main"]
            timeout_s = limits.timeout_s

        full_cmd = docker_args + exec_args

        stdout_chunks = []
        stderr_chunks = []
        stdout_size = 0
        stderr_size = 0

        output_exceeded = threading.Event()
        lock = threading.Lock()

        try:
            proc = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except FileNotFoundError:
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=125,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                is_docker_system_error=True,
                error_message="Docker CLI executable not found on host.",
            )
        except Exception as ex:
            tb_str = traceback.format_exc()
            logger.error(f"[DockerExecutor] Failed to spawn Docker container process: {ex}\n{tb_str}")
            print(f"[DockerExecutor ERROR] {ex}\n{tb_str}", file=sys.stderr)
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=125,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                is_docker_system_error=True,
                error_message=f"Failed to spawn Docker container process: {str(ex)}",
            )

        def kill_container():
            try:
                subprocess.run(
                    ["docker", "kill", container_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3.0,
                    check=False,
                )
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        def read_pipe(pipe, chunks_list, is_stdout):
            nonlocal stdout_size, stderr_size
            try:
                while True:
                    chunk = pipe.read(4096)
                    if not chunk:
                        break
                    with lock:
                        chunk_len = len(chunk.encode("utf-8"))
                        if is_stdout:
                            stdout_size += chunk_len
                        else:
                            stderr_size += chunk_len

                        if stdout_size + stderr_size > limits.max_output_bytes:
                            output_exceeded.set()
                            allowed = max(0, limits.max_output_bytes - (stdout_size + stderr_size - chunk_len))
                            chunks_list.append(chunk[:allowed])
                            kill_container()
                            break
                        else:
                            chunks_list.append(chunk)
            except Exception:
                pass
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        t_out = threading.Thread(target=read_pipe, args=(proc.stdout, stdout_chunks, True))
        t_err = threading.Thread(target=read_pipe, args=(proc.stderr, stderr_chunks, False))
        t_out.daemon = True
        t_err.daemon = True
        t_out.start()
        t_err.start()

        if stdin_data and proc.stdin:
            try:
                proc.stdin.write(stdin_data)
                proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass
        if proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass

        start_time = time.monotonic()
        timed_out = False

        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_container()
            try:
                proc.wait(timeout=2.0)
            except Exception:
                pass

        t_out.join(timeout=1.0)
        t_err.join(timeout=1.0)

        duration_ms = (time.monotonic() - start_time) * 1000.0
        full_stdout = "".join(stdout_chunks)
        full_stderr = "".join(stderr_chunks)

        if proc.returncode is not None and isinstance(proc.returncode, int):
            ret_code = proc.returncode
        else:
            ret_code = 137 if timed_out else 125

        is_system_error = (ret_code == 125)
        oom_killed = False

        if not is_system_error:
            oom_killed = self._inspect_oom_killed(container_name)

        sig_num: Optional[int] = None
        if ret_code > 128:
            sig_num = ret_code - 128
        elif ret_code < 0:
            sig_num = abs(ret_code)

        err_msg: Optional[str] = None
        if is_system_error:
            err_msg = f"Docker daemon failure (exit code {ret_code}): {full_stderr.strip()}"
        elif timed_out:
            err_msg = f"Execution timed out after {timeout_s} seconds."
        elif oom_killed:
            err_msg = "Execution exceeded memory limit (OOMKilled)."
        elif output_exceeded.is_set():
            err_msg = f"Output size limit ({limits.max_output_bytes} bytes) exceeded."
        elif sig_num is not None:
            err_msg = f"Process terminated by signal {sig_num}."

        try:
            return ExecutionResult(
                stdout=full_stdout,
                stderr=full_stderr,
                return_code=ret_code,
                duration_ms=round(duration_ms, 2),
                timed_out=timed_out,
                output_limit_exceeded=output_exceeded.is_set(),
                oom_killed=oom_killed,
                is_docker_system_error=is_system_error,
                signal_number=sig_num,
                error_message=err_msg,
            )
        finally:
            self._cleanup_container(container_name)

    def _inspect_oom_killed(self, container_name: str) -> bool:
        try:
            res = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.OOMKilled}}", container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3.0,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip().lower() == "true":
                return True
        except Exception:
            pass
        return False

    def _cleanup_container(self, container_name: str) -> None:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
                check=False,
            )
        except Exception:
            pass
