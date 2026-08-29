"""
Backend FastAPI API Unit Tests.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, get_db
from app.main import app
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.testcase import TestCase
from app.services.queue_client import queue_client

# Setup in-memory SQLite database with StaticPool for test isolation
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class TestFastAPIEndpoints(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

        # Seed sample problem
        p1 = Problem(
            id=1,
            title="Add Numbers",
            description="Print sum of two integers.",
            input_description="Two integers",
            output_description="Single integer",
            time_limit_ms=2000,
            memory_limit_mb=256,
        )
        self.db.add(p1)
        self.db.flush()

        tc_sample = TestCase(problem_id=1, input="2 3\n", expected_output="5\n", is_sample=True)
        tc_hidden = TestCase(problem_id=1, input="10 20\n", expected_output="30\n", is_sample=False)
        self.db.add_all([tc_sample, tc_hidden])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_list_problems(self):
        response = self.client.get("/problems/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Add Numbers")

    def test_get_problem_detail_hides_hidden_testcases(self):
        response = self.client.get("/problems/1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Add Numbers")
        self.assertEqual(len(data["sample_testcases"]), 1)
        self.assertEqual(data["sample_testcases"][0]["input"], "2 3\n")

    def test_get_nonexistent_problem(self):
        response = self.client.get("/problems/999")
        self.assertEqual(response.status_code, 404)

    def test_create_submission_validation(self):
        # Invalid language -> Pydantic validator returns 422
        res1 = self.client.post("/submissions/", json={"problem_id": 1, "language": "python", "source_code": "print(1)"})
        self.assertIn(res1.status_code, [400, 422])

        # Empty source code -> Pydantic validator returns 422
        res2 = self.client.post("/submissions/", json={"problem_id": 1, "language": "cpp", "source_code": ""})
        self.assertIn(res2.status_code, [400, 422])

        # Nonexistent problem -> 404
        res3 = self.client.post("/submissions/", json={"problem_id": 99, "language": "cpp", "source_code": "int main(){}"})
        self.assertEqual(res3.status_code, 404)

        # Exceeds 64 KB limit in source code validation -> 422
        large_code = "int main() { " + ("//" * 35000) + " }"
        res4 = self.client.post("/submissions/", json={"problem_id": 1, "language": "cpp", "source_code": large_code})
        self.assertIn(res4.status_code, [400, 422])

    def test_oversized_payload_rejected_by_middleware(self):
        # Multi-MB payload cap middleware test (> 100 KB)
        huge_code = "A" * (200 * 1024)
        res = self.client.post(
            "/submissions/",
            content=f'{{"problem_id": 1, "language": "cpp", "source_code": "{huge_code}"}}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 413)

    def test_create_and_get_submission_flow(self):
        original_enqueue = queue_client.enqueue_submission
        queue_client.enqueue_submission = lambda sub_id: "msg-12345"

        try:
            code = "#include <iostream>\nint main() { return 0; }"
            res = self.client.post("/submissions/", json={"problem_id": 1, "language": "cpp", "source_code": code})
            self.assertEqual(res.status_code, 201)
            sub_data = res.json()
            self.assertEqual(sub_data["status"], "QUEUED")

            # Retrieve submission
            sub_id = sub_data["id"]
            res_get = self.client.get(f"/submissions/{sub_id}")
            self.assertEqual(res_get.status_code, 200)
            self.assertEqual(res_get.json()["id"], sub_id)
            self.assertEqual(res_get.json()["status"], "QUEUED")
        finally:
            queue_client.enqueue_submission = original_enqueue

    def test_submission_history_pagination(self):
        # Create multiple submissions
        sub1 = Submission(id="sub-1", problem_id=1, source_code="code1", language="cpp", status="ACCEPTED")
        sub2 = Submission(id="sub-2", problem_id=1, source_code="code2", language="cpp", status="WRONG_ANSWER")
        self.db.add_all([sub1, sub2])
        self.db.commit()

        response = self.client.get("/submissions/?problem_id=1&limit=10&offset=0")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["submissions"]), 2)

    def test_sanitized_error_message_does_not_expose_internal_paths(self):
        sub = Submission(
            id="sub-err",
            problem_id=1,
            source_code="code",
            language="cpp",
            status="SYSTEM_ERROR",
            error_message="Worker process failure: /var/run/docker.sock permission denied in /app/worker/executor.py",
        )
        self.db.add(sub)
        self.db.commit()

        res = self.client.get("/submissions/sub-err")
        self.assertEqual(res.status_code, 200)
        # Ensure internal path details are hidden from client response
        self.assertEqual(res.json()["error_message"], "Judge system error. Please try again later.")

    def test_database_outage_returns_503(self):
        with patch("app.services.submission_service.SubmissionService.create_submission") as mock_create:
            from fastapi import HTTPException
            mock_create.side_effect = HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
            res = self.client.post("/submissions/", json={"problem_id": 1, "language": "cpp", "source_code": "int main(){}"})
            self.assertEqual(res.status_code, 503)


if __name__ == "__main__":
    unittest.main()
