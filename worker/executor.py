"""
Executor Module.

Defines the Executor Protocol interface, LocalExecutor for local testing,
and DockerExecutor for hardened containerized execution.
"""

import json
import os
import signal
import subprocess
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from sandbox_policy import DEFAULT_SANDBOX_POLICY, ExecutionLimits, SandboxPolicy


@dataclass(frozen=True)
class ExecutionResult:
    """
    Structured outcome of binary execution against a single testcase.
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
    Abstract Protocol interface for running compiled binaries.
    """

    @abstractmethod
    def run(
        self,
        binary_path: Union[str, Path],
        stdin_data: str,
        limits: Optional[ExecutionLimits] = None
    ) -> ExecutionResult:
        """
        Executes a compiled binary with stdin data under specified resource limits.
        """
        pass


class LocalExecutor(Executor):
    """
    Development and testing executor running binaries directly on host via subprocess.
    
    WARNING: LocalExecutor is dev/test infrastructure ONLY and MUST NOT be exposed
    directly through production submission API endpoints.
    """

    def run(
        self,
        binary_path: Union[str, Path],
        stdin_data: str,
        limits: Optional[ExecutionLimits] = None
    ) -> ExecutionResult:
        if limits is None:
            limits = ExecutionLimits()

        bin_path = Path(binary_path).resolve()
        cwd = bin_path.parent

        if not bin_path.exists():
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                error_message=f"Binary path '{bin_path}' does not exist.",
            )

        stdout_chunks = []
        stderr_chunks = []
        stdout_size = 0
        stderr_size = 0

        output_exceeded = threading.Event()
        lock = threading.Lock()

        try:
            proc = subprocess.Popen(
                [str(bin_path)],
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except Exception as ex:
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                error_message=f"Failed to launch process: {str(ex)}",
            )

        pgid = proc.pid

        def kill_process_group():
            try:
                os.killpg(pgid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                try:
                    proc.kill()
                except (OSError, ProcessLookupError):
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
            proc.wait(timeout=limits.timeout_s)
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
            err_msg = f"Execution timed out after {limits.timeout_s} seconds."
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
    Hardened Docker-based container executor.
    
    Launches a fresh container per testcase with strict security options
    (--network none, --read-only, --tmpfs, --memory, --cpus, --pids-limit, --cap-drop ALL).
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
        limits: Optional[ExecutionLimits] = None
    ) -> ExecutionResult:
        if limits is None:
            limits = self.policy.execution_limits

        bin_path = Path(binary_path).resolve()
        ws_dir = bin_path.parent

        if not bin_path.exists():
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=-1,
                duration_ms=0.0,
                timed_out=False,
                output_limit_exceeded=False,
                error_message=f"Compiled binary '{bin_path}' not found.",
            )

        # Unique container name: judge-{submission_id}-{test_index}-{uuid}
        unique_id = uuid.uuid4().hex[:8]
        container_name = f"judge-{self.submission_id}-{self.test_index}-{unique_id}"

        # Construct docker run command
        docker_args = self.policy.to_docker_args(
            container_name=container_name,
            workspace_dir=ws_dir,
            mount_read_only=True,
        )
        full_cmd = docker_args + [self.policy.runner_image, "/sandbox/main"]

        stdout_chunks = []
        stderr_chunks = []
        stdout_size = 0
        stderr_size = 0

        output_exceeded = threading.Event()
        lock = threading.Lock()

        # Launch docker run process
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

        # Send stdin to container
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
            proc.wait(timeout=limits.timeout_s)
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

        # Check Docker CLI exit code 125 (Docker system launch failure)
        is_system_error = (ret_code == 125)
        oom_killed = False

        if not is_system_error:
            # Perform container inspection for OOMKilled flag before container removal
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
            err_msg = f"Execution timed out after {limits.timeout_s} seconds."
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
            # Strict container cleanup in finally block
            self._cleanup_container(container_name)

    def _inspect_oom_killed(self, container_name: str) -> bool:
        """Runs docker inspect to check if the container was OOMKilled."""
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
        """Removes the execution container."""
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
