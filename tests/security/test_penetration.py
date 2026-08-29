"""
Phase 6.5 Security Hardening & Hostile Code Penetration Suite.

Automated security tests for judge containment, resource limits, attack vectors,
and error message sanitization.
"""

import sys
import unittest
from pathlib import Path

# Add backend and worker to sys.path
WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "worker"
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(WORKER_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from app.models.submission import SubmissionStatus
from app.schemas.submission import sanitize_error_message
from executor import DockerExecutor, LocalExecutor
from judge import Judge
from sandbox_policy import DEFAULT_SANDBOX_POLICY
from worker import is_docker_available


class TestSecurityPenetration(unittest.TestCase):

    def setUp(self):
        self.use_docker = is_docker_available()
        self.executor = DockerExecutor(policy=DEFAULT_SANDBOX_POLICY) if self.use_docker else LocalExecutor()
        self.judge = Judge(executor=self.executor, use_docker_compiler=self.use_docker)

    def test_fork_bomb_process_containment(self):
        """Verify fork bomb attack is safely contained (PID limit error caught or process terminated)."""
        fork_bomb_py = (
            "import os\n"
            "try:\n"
            "    for i in range(500):\n"
            "        os.fork()\n"
            "except Exception:\n"
            "    pass\n"
            "print('contained')\n"
        )
        testcases = [{"input": "", "expected": "contained"}]
        res = self.judge.evaluate("sub-fork", fork_bomb_py, testcases, language="python")
        self.assertIn(
            res.status,
            [
                SubmissionStatus.ACCEPTED,
                SubmissionStatus.WRONG_ANSWER,
                SubmissionStatus.RUNTIME_ERROR,
                SubmissionStatus.TIME_LIMIT_EXCEEDED,
            ],
        )

    def test_network_exfiltration_blocked(self):
        """Verify outbound network connections fail or are blocked (--network none)."""
        net_code_py = (
            "import socket\n"
            "try:\n"
            "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "    s.settimeout(1.0)\n"
            "    s.connect(('8.8.8.8', 53))\n"
            "    print('CONNECTED')\n"
            "except Exception:\n"
            "    print('BLOCKED')\n"
        )
        testcases = [{"input": "", "expected": "BLOCKED"}]
        res = self.judge.evaluate("sub-net", net_code_py, testcases, language="python")
        self.assertEqual(res.status, SubmissionStatus.ACCEPTED)

    def test_host_filesystem_traversal_restricted(self):
        """Verify attempted access to sensitive host files (e.g. docker.sock or root SSH keys) inside judge container fails."""
        file_trap_py = (
            "import os\n"
            "found = 0\n"
            "if os.path.exists('/var/run/docker.sock'): found += 1\n"
            "if os.path.exists('/root/.ssh/id_rsa'): found += 1\n"
            "print(found)\n"
        )
        testcases = [{"input": "", "expected": "0"}]
        res = self.judge.evaluate("sub-trap", file_trap_py, testcases, language="python")
        self.assertEqual(res.status, SubmissionStatus.ACCEPTED)

    def test_memory_oom_spike_handling(self):
        """Verify allocating excessive memory triggers MEMORY_LIMIT_EXCEEDED or RUNTIME_ERROR."""
        oom_py = "arr = bytearray(400 * 1024 * 1024)\nprint('allocated')\n"
        testcases = [{"input": "", "expected": "allocated"}]
        res = self.judge.evaluate("sub-oom", oom_py, testcases, language="python")
        self.assertIn(res.status, [SubmissionStatus.MEMORY_LIMIT_EXCEEDED, SubmissionStatus.RUNTIME_ERROR])

    def test_output_flooding_containment(self):
        """Verify infinite stdout output stream triggers OUTPUT_LIMIT_EXCEEDED."""
        flood_py = "import sys\nfor _ in range(50000):\n    sys.stdout.write('A' * 1000)\n"
        testcases = [{"input": "", "expected": "short"}]
        res = self.judge.evaluate("sub-flood", flood_py, testcases, language="python")
        self.assertEqual(res.status, SubmissionStatus.OUTPUT_LIMIT_EXCEEDED)

    def test_error_message_sanitization_masks_internal_host_paths(self):
        """Verify internal path leaking is prevented in public API responses."""
        raw_error = "Traceback in /Users/niteshjain/.gemini/antigravity/scratch/gdg-remote-runtime/worker/executor.py line 45: /var/run/docker.sock permission denied"
        sanitized = sanitize_error_message(SubmissionStatus.SYSTEM_ERROR.value, raw_error)
        self.assertNotIn("/Users/niteshjain", sanitized)
        self.assertNotIn("docker.sock", sanitized)
        self.assertNotIn("executor.py", sanitized)
        self.assertEqual(sanitized, "Judge system error. Please try again later.")


if __name__ == "__main__":
    unittest.main()
