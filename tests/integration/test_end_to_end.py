"""
Phase 4 Integration & End-to-End Test Suite.
Tests full flow: API -> PostgreSQL -> Redis Stream -> Worker -> Judge -> DB Result -> API GET verdict.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend and worker to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "worker"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(WORKER_DIR))

from app.database import Base, get_db
from app.main import app
from app.models.problem import Problem
from app.models.submission import Submission, SubmissionStatus
from app.models.testcase import TestCase
from app.services.queue_client import queue_client
from worker import Worker

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestEndToEndIntegration(unittest.TestCase):

    def override_get_db(self):
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def setUp(self):
        import worker as worker_mod
        worker_mod.SessionLocal = TestingSessionLocal

        Base.metadata.create_all(bind=engine)
        app.dependency_overrides[get_db] = self.override_get_db
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

        self.patcher = patch.object(queue_client, "enqueue_submission", return_value="msg-1")
        self.mock_enqueue = self.patcher.start()

        # Seed test problem
        self.p1 = Problem(
            id=1,
            title="Sum Problem",
            description="Sum integers",
            time_limit_ms=2000,
            memory_limit_mb=256,
        )
        self.db.add(self.p1)
        self.db.flush()

        tc1 = TestCase(problem_id=1, input="2 3\n", expected_output="5\n", is_sample=True)
        tc2 = TestCase(problem_id=1, input="10 20\n", expected_output="30\n", is_sample=False)
        self.db.add_all([tc1, tc2])
        self.db.commit()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    def test_e2e_accepted_submission(self):
        code = """
        #include <iostream>
        int main() {
            int a, b;
            if (std::cin >> a >> b) {
                std::cout << a + b;
            }
            return 0;
        }
        """
        res_post = self.client.post("/submissions/", json={"problem_id": 1, "language": "cpp", "source_code": code})
        self.assertEqual(res_post.status_code, 201)
        sub_id = res_post.json()["id"]
        self.assertEqual(res_post.json()["status"], "QUEUED")

        worker = Worker()
        worker.redis_client = MagicMock()

        # Mock Docker availability to True for testing DockerExecutor flow
        with patch("worker.is_docker_available", return_value=True), \
             patch("executor.DockerExecutor.run") as mock_exec_run, \
             patch("compiler.compile_code_docker") as mock_compile:

            from compiler import CompileResult
            from executor import ExecutionResult
            mock_compile.return_value = CompileResult(
                success=True, stdout="", stderr="", duration_ms=20.0, timed_out=False
            )
            mock_exec_run.side_effect = [
                ExecutionResult(stdout="5", stderr="", return_code=0, duration_ms=10.0, timed_out=False, output_limit_exceeded=False),
                ExecutionResult(stdout="30", stderr="", return_code=0, duration_ms=12.0, timed_out=False, output_limit_exceeded=False),
            ]

            success = worker.process_submission_id(sub_id)
            self.assertTrue(success)

        res_get = self.client.get(f"/submissions/{sub_id}")
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertEqual(data["status"], "ACCEPTED")
        self.assertIsNotNone(data["execution_time_ms"])
        self.assertIsNone(data["error_message"])
        self.assertEqual(len(data["testcase_results"]), 2)
        self.assertEqual(data["testcase_results"][0]["status"], "ACCEPTED")

    def test_e2e_compilation_error(self):
        code = "int main() { std::cout << missing_var; return 0; }"
        res_post = self.client.post("/submissions/", json={"problem_id": 1, "language": "cpp", "source_code": code})
        self.assertEqual(res_post.status_code, 201)
        sub_id = res_post.json()["id"]

        worker = Worker()
        worker.redis_client = MagicMock()

        with patch("worker.is_docker_available", return_value=True), \
             patch("compiler.compile_code_docker") as mock_compile:
            from compiler import CompileResult
            mock_compile.return_value = CompileResult(
                success=False, stdout="", stderr="error: 'missing_var' was not declared in this scope", duration_ms=20.0, timed_out=False, error_message="error: 'missing_var' was not declared in this scope"
            )
            worker.process_submission_id(sub_id)

        res_get = self.client.get(f"/submissions/{sub_id}")
        self.assertEqual(res_get.json()["status"], "COMPILATION_ERROR")
        self.assertIn("missing_var", res_get.json()["error_message"])

    def test_idempotency_duplicate_delivery(self):
        sub = Submission(
            id="sub-already-terminal",
            problem_id=1,
            source_code="int main(){}",
            language="cpp",
            status=SubmissionStatus.ACCEPTED.value,
        )
        self.db.add(sub)
        self.db.commit()

        worker = Worker()
        worker.redis_client = MagicMock()

        with patch("worker.Judge.evaluate") as mock_judge_eval:
            processed = worker.process_submission_id("sub-already-terminal")
            self.assertTrue(processed)
            mock_judge_eval.assert_not_called()

        res_get = self.client.get("/submissions/sub-already-terminal")
        self.assertEqual(res_get.json()["status"], "ACCEPTED")


if __name__ == "__main__":
    unittest.main()
