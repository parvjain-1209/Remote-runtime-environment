"""
Backend User Statistics Unit Tests.
"""

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, get_db
from app.main import app
from app.models import Problem, Submission, User

# In-memory SQLite DB setup
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestUserStatsEndpoints(unittest.TestCase):

    def override_get_db(self):
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        app.dependency_overrides[get_db] = self.override_get_db
        self.client = TestClient(app)
        self.db = TestingSessionLocal()

        # Seed test catalog problems
        p1 = Problem(id=1, title="Easy P1", description="desc", difficulty="Easy", time_limit_ms=1000, memory_limit_mb=256)
        p2 = Problem(id=2, title="Medium P2", description="desc", difficulty="Medium", time_limit_ms=1000, memory_limit_mb=256)
        p3 = Problem(id=3, title="Hard P3", description="desc", difficulty="Hard", time_limit_ms=1000, memory_limit_mb=256)
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        # Register standard test user
        reg_res = self.client.post("/auth/register", json={
            "username": "statscoder",
            "email": "stats@example.com",
            "password": "password123",
        })
        self.token = reg_res.json()["access_token"]
        self.user_id = reg_res.json()["user"]["id"]

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    def test_unauthenticated_stats_rejected(self):
        res = self.client.get("/users/me/stats")
        self.assertEqual(res.status_code, 401)

    def test_stats_new_user(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        res = self.client.get("/users/me/stats", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["user"]["username"], "statscoder")
        self.assertEqual(data["total_submissions"], 0)
        self.assertEqual(data["total_solved_problems"], 0)
        self.assertEqual(data["total_attempted_problems"], 0)
        self.assertEqual(data["acceptance_rate"], 0.0)
        self.assertEqual(data["solved_by_difficulty"]["Easy"], 0)
        self.assertEqual(data["solved_by_difficulty"]["Medium"], 0)
        self.assertEqual(data["total_by_difficulty"]["Easy"], 1)
        self.assertEqual(data["total_by_difficulty"]["Medium"], 1)
        self.assertEqual(data["total_by_difficulty"]["Hard"], 1)

    def test_stats_mixed_verdicts(self):
        # Add submissions for statscoder
        s1 = Submission(id="sub-101", problem_id=1, user_id=self.user_id, source_code="code", language="cpp", status="ACCEPTED")
        s2 = Submission(id="sub-102", problem_id=1, user_id=self.user_id, source_code="code", language="cpp", status="WRONG_ANSWER")
        s3 = Submission(id="sub-103", problem_id=2, user_id=self.user_id, source_code="code", language="cpp", status="TIME_LIMIT_EXCEEDED")
        s4 = Submission(id="sub-104", problem_id=2, user_id=self.user_id, source_code="code", language="cpp", status="ACCEPTED")
        self.db.add_all([s1, s2, s3, s4])
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.token}"}
        res = self.client.get("/users/me/stats", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_submissions"], 4)
        self.assertEqual(data["total_solved_problems"], 2)  # Problems 1 & 2 solved
        self.assertEqual(data["total_attempted_problems"], 2)
        self.assertEqual(data["acceptance_rate"], 50.0)  # 2 accepted out of 4 total
        self.assertEqual(data["solved_by_difficulty"]["Easy"], 1)
        self.assertEqual(data["solved_by_difficulty"]["Medium"], 1)
        self.assertEqual(data["solved_by_difficulty"]["Hard"], 0)
        self.assertEqual(data["verdict_counts"]["ACCEPTED"], 2)
        self.assertEqual(data["verdict_counts"]["WRONG_ANSWER"], 1)
        self.assertEqual(data["verdict_counts"]["TIME_LIMIT_EXCEEDED"], 1)

    def test_stats_duplicate_accepted_on_same_problem(self):
        # 2 ACCEPTED submissions on Problem 1
        s1 = Submission(id="sub-dup-1", problem_id=1, user_id=self.user_id, source_code="code", language="cpp", status="ACCEPTED")
        s2 = Submission(id="sub-dup-2", problem_id=1, user_id=self.user_id, source_code="code", language="cpp", status="ACCEPTED")
        self.db.add_all([s1, s2])
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.token}"}
        res = self.client.get("/users/me/stats", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_submissions"], 2)
        self.assertEqual(data["total_solved_problems"], 1)  # Unique solved problem count is 1!
        self.assertEqual(data["acceptance_rate"], 100.0)

    def test_user_submissions_isolation(self):
        # Register User 2
        reg2 = self.client.post("/auth/register", json={
            "username": "user2",
            "email": "user2@example.com",
            "password": "password123",
        })
        user2_id = reg2.json()["user"]["id"]

        s_user1 = Submission(id="sub-u1", problem_id=1, user_id=self.user_id, source_code="code", language="cpp", status="ACCEPTED")
        s_user2 = Submission(id="sub-u2", problem_id=1, user_id=user2_id, source_code="code", language="cpp", status="ACCEPTED")
        self.db.add_all([s_user1, s_user2])
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.token}"}
        res = self.client.get("/users/me/submissions", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total"], 1)
        self.assertEqual(data["submissions"][0]["id"], "sub-u1")


if __name__ == "__main__":
    unittest.main()
