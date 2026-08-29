"""
Unit tests for Phase 3 & 4 Docker Executor and Sandbox Policy.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add worker and backend to sys.path
WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "worker"
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(WORKER_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from executor import DockerExecutor, ExecutionResult
from judge import Judge, JudgeResult
from sandbox_policy import SandboxPolicy, DEFAULT_SANDBOX_POLICY
from worker import Worker, is_docker_available
from app.models.submission import Submission, SubmissionStatus
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestDockerPolicy(unittest.TestCase):

    def setUp(self):
        self.policy = SandboxPolicy(
            cpu_limit=0.5,
            memory_limit="128m",
            memory_swap="128m",
            pids_limit=32,
            tmpfs_size="32m",
            execution_timeout_seconds=1.5,
            compilation_timeout_seconds=5.0,
            max_output_bytes=512 * 1024,
            network_disabled=True,
            read_only_root_fs=True,
            cap_drop=["ALL"],
            no_new_privileges=True,
            execution_user="1000:1000",
            runner_image="gdg-runner:latest",
        )

    def test_docker_args_construction(self):
        ws_path = Path("/tmp/test_workspace").resolve()
        args = self.policy.to_docker_args(
            container_name="test-container",
            workspace_dir="/tmp/test_workspace",
            mount_read_only=True,
        )

        self.assertIn("docker", args)
        self.assertIn("run", args)
        self.assertIn("--name", args)
        self.assertIn("test-container", args)
        self.assertIn("--network", args)
        self.assertIn("none", args)
        self.assertIn("--tmpfs", args)
        self.assertIn("/tmp:rw,noexec,nosuid,nodev,size=32m", args)
        self.assertIn("--memory=128m", args)
        self.assertIn("--memory-swap=128m", args)
        self.assertIn("--cpus=0.5", args)
        self.assertIn("--pids-limit=32", args)
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn("--user", args)
        self.assertIn("1000:1000", args)
        self.assertIn("-v", args)
        self.assertIn(f"{ws_path}:/sandbox:ro", args)
        self.assertIn("--read-only", args)
        self.assertIn("--security-opt=no-new-privileges", args)

    def test_default_workspace_path_mapping_resolves_to_host_path(self):
        # REGRESSION TEST: Catches bug where /runtime-workspaces/submission_xyz is incorrectly passed as host mount source
        container_ws = "/runtime-workspaces/submission_xyz123"

        # Scenario 1: WORKER_WORKSPACE_DIR set, HOST_WORKSPACE_DIR set to project dir
        with patch.dict(os.environ, {"WORKER_WORKSPACE_DIR": "/runtime-workspaces", "HOST_WORKSPACE_DIR": "/host/project/runtime-workspaces"}):
            args1 = self.policy.to_docker_args(
                container_name="judge-test-1",
                workspace_dir=container_ws,
                mount_read_only=True,
            )
            mount_flag = [a for a in args1 if "/sandbox:ro" in a][0]
            self.assertEqual(mount_flag, "/host/project/runtime-workspaces/submission_xyz123:/sandbox:ro")
            self.assertFalse(mount_flag.startswith("/runtime-workspaces/submission_xyz123:"))

        # Scenario 2: DEFAULT SETTINGS (HOST_WORKSPACE_DIR is empty string)
        with patch.dict(os.environ, {"WORKER_WORKSPACE_DIR": "/runtime-workspaces", "HOST_WORKSPACE_DIR": ""}):
            args2 = self.policy.to_docker_args(
                container_name="judge-test-2",
                workspace_dir=container_ws,
                mount_read_only=True,
            )
            mount_flag2 = [a for a in args2 if "/sandbox:ro" in a][0]
            expected_cwd_base = str(Path.cwd().resolve() / "runtime-workspaces")
            self.assertEqual(mount_flag2, f"{expected_cwd_base}/submission_xyz123:/sandbox:ro")
            self.assertFalse(mount_flag2.startswith("/runtime-workspaces/submission_xyz123:"))


class TestDockerExecutorUnit(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dummy_binary = Path(self.temp_dir.name) / "main"
        self.dummy_binary.write_bytes(b"dummy")

        self.executor = DockerExecutor(
            policy=DEFAULT_SANDBOX_POLICY,
            submission_id="sub-123",
            test_index=0,
        )

    def tearDown(self):
        self.temp_dir.cleanup()
        Base.metadata.drop_all(bind=engine)

    @patch("subprocess.Popen")
    def test_docker_cli_missing_system_error(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("docker command not found")

        res = self.executor.run(binary_path=self.dummy_binary, stdin_data="1 2\n")

        self.assertTrue(res.is_docker_system_error)
        self.assertEqual(res.return_code, 125)
        self.assertIn("Docker CLI executable not found", res.error_message)

    @patch("subprocess.Popen")
    def test_docker_exit_code_125_system_error(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.returncode = 125
        mock_proc.stdout.read.return_value = ""
        mock_proc.stderr.read.return_value = "docker: Error response from daemon: OOM error."
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        res = self.executor.run(binary_path=self.dummy_binary, stdin_data="1 2\n")

        self.assertTrue(res.is_docker_system_error)
        self.assertEqual(res.return_code, 125)
        self.assertIn("Docker daemon failure", res.error_message)

    @patch("subprocess.Popen")
    def test_docker_oom_killed_detection(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.returncode = 137
        mock_proc.stdout.read.return_value = ""
        mock_proc.stderr.read.return_value = "Killed"
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        with patch.object(self.executor, "_inspect_oom_killed", return_value=True):
            res = self.executor.run(binary_path=self.dummy_binary, stdin_data="1 2\n")

            self.assertTrue(res.oom_killed)
            self.assertFalse(res.is_docker_system_error)

    @patch("subprocess.Popen")
    def test_docker_timeout_handling(self, mock_popen):
        import subprocess
        mock_proc = MagicMock()
        mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="docker run", timeout=2.0)
        mock_proc.stdout.read.return_value = ""
        mock_proc.stderr.read.return_value = ""
        mock_popen.return_value = mock_proc

        res = self.executor.run(binary_path=self.dummy_binary, stdin_data="1 2\n")

        self.assertTrue(res.timed_out)
        self.assertFalse(res.is_docker_system_error)

    def test_judge_memory_limit_exceeded_verdict(self):
        mock_exec = MagicMock()
        mock_exec.run.return_value = ExecutionResult(
            stdout="", stderr="Killed", return_code=137, duration_ms=50.0, timed_out=False, output_limit_exceeded=False, oom_killed=True
        )

        judge = Judge(executor=mock_exec, use_docker_compiler=False)

        with patch("compiler.compile_cpp") as mock_compile:
            from compiler import CompileResult
            def fake_compile(*args, **kwargs):
                bin_path = args[1] if len(args) > 1 else kwargs.get("output_path")
                if bin_path:
                    Path(bin_path).write_bytes(b"dummy binary")
                return CompileResult(success=True, stdout="", stderr="", duration_ms=10.0, timed_out=False)

            mock_compile.side_effect = fake_compile

            res = judge.evaluate(
                submission_id="sub-oom",
                source_code="int main(){}",
                testcases=[{"input": "1", "expected": "1"}],
            )

            self.assertEqual(res.status, SubmissionStatus.MEMORY_LIMIT_EXCEEDED)

    def test_judge_system_error_verdict(self):
        mock_exec = MagicMock()
        mock_exec.run.return_value = ExecutionResult(
            stdout="", stderr="Daemon error", return_code=125, duration_ms=0.0, timed_out=False, output_limit_exceeded=False, is_docker_system_error=True
        )

        judge = Judge(executor=mock_exec, use_docker_compiler=False)

        with patch("compiler.compile_cpp") as mock_compile:
            from compiler import CompileResult
            def fake_compile(*args, **kwargs):
                bin_path = args[1] if len(args) > 1 else kwargs.get("output_path")
                if bin_path:
                    Path(bin_path).write_bytes(b"dummy binary")
                return CompileResult(success=True, stdout="", stderr="", duration_ms=10.0, timed_out=False)

            mock_compile.side_effect = fake_compile

            res = judge.evaluate(
                submission_id="sub-sys-err",
                source_code="int main(){}",
                testcases=[{"input": "1", "expected": "1"}],
            )

            self.assertEqual(res.status, SubmissionStatus.SYSTEM_ERROR)

    @patch("worker.is_docker_available", return_value=False)
    @patch("executor.LocalExecutor")
    def test_docker_unavailable_never_triggers_local_executor(self, mock_local_exec_class, mock_is_docker):
        # PRIORITY 3 REGRESSION TEST: Prove LocalExecutor is NEVER called when Docker is unavailable
        import worker as worker_mod
        worker_mod.SessionLocal = TestingSessionLocal

        db = TestingSessionLocal()
        sub = Submission(id="sub-no-docker", problem_id=1, source_code="int main(){}", language="cpp", status="QUEUED")
        db.add(sub)
        db.commit()
        db.close()

        worker = Worker()
        worker.redis_client = MagicMock()

        processed = worker.process_submission_id("sub-no-docker")
        self.assertTrue(processed)

        # Verify LocalExecutor was NEVER instantiated
        mock_local_exec_class.assert_not_called()

        # Verify verdict is SYSTEM_ERROR
        db_check = TestingSessionLocal()
        fetched = db_check.query(Submission).filter(Submission.id == "sub-no-docker").first()
        self.assertEqual(fetched.status, "SYSTEM_ERROR")
        self.assertIn("Docker execution environment unavailable", fetched.error_message)
        db_check.close()

    def test_stale_job_recovery_timing(self):
        # PRIORITY 4 REGRESSION TEST: Verify fresh jobs are NOT reset while truly stale jobs ARE reset
        import worker as worker_mod
        worker_mod.SessionLocal = TestingSessionLocal

        now = datetime.now(timezone.utc)
        fresh_time = now - timedelta(seconds=5)  # 5s ago (< 30s timeout)
        stale_time = now - timedelta(seconds=60) # 60s ago (> 30s timeout)

        db = TestingSessionLocal()
        sub_fresh = Submission(id="sub-fresh", problem_id=1, source_code="code", language="cpp", status="COMPILING", started_at=fresh_time)
        sub_stale = Submission(id="sub-stale", problem_id=1, source_code="code", language="cpp", status="COMPILING", started_at=stale_time)
        db.add_all([sub_fresh, sub_stale])
        db.commit()
        db.close()

        worker = Worker()
        worker.redis_client = MagicMock()

        worker.recover_stale_jobs()

        db_check = TestingSessionLocal()
        fresh_check = db_check.query(Submission).filter(Submission.id == "sub-fresh").first()
        stale_check = db_check.query(Submission).filter(Submission.id == "sub-stale").first()

        # Fresh job MUST remain COMPILING
        self.assertEqual(fresh_check.status, "COMPILING")

        # Stale job MUST be reset to QUEUED
        self.assertEqual(stale_check.status, "QUEUED")
        db_check.close()


if __name__ == "__main__":
    unittest.main()
