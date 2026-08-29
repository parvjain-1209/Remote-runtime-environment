"""
Backend Database Models & Relationships Unit Tests.
"""

import sys
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base
from app.models.problem import Problem
from app.models.submission import Submission, SubmissionStatus
from app.models.testcase import TestCase

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestDatabaseModels(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_problem_and_testcase_cascade_delete(self):
        problem = Problem(
            id=10,
            title="Cascade Test",
            description="Testing cascade delete",
        )
        self.db.add(problem)
        self.db.commit()

        tc1 = TestCase(problem_id=10, input="1\n", expected_output="1\n", is_sample=True)
        tc2 = TestCase(problem_id=10, input="2\n", expected_output="2\n", is_sample=False)
        self.db.add_all([tc1, tc2])
        self.db.commit()

        self.assertEqual(self.db.query(TestCase).filter(TestCase.problem_id == 10).count(), 2)

        # Delete problem
        self.db.delete(problem)
        self.db.commit()

        # Check cascading deletion of associated testcases
        self.assertEqual(self.db.query(TestCase).filter(TestCase.problem_id == 10).count(), 0)

    def test_submission_lifecycle_and_status(self):
        problem = Problem(id=20, title="Sub Test", description="Desc")
        self.db.add(problem)
        self.db.commit()

        sub = Submission(
            id="sub-test-uuid-20",
            problem_id=20,
            source_code="int main(){}",
            language="cpp",
            status=SubmissionStatus.QUEUED.value,
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)

        self.assertIsNotNone(sub.id)
        self.assertEqual(sub.status, "QUEUED")
        self.assertIsNone(sub.execution_time_ms)
        self.assertIsNone(sub.memory_used_mb)

        # Update verdict
        sub.status = SubmissionStatus.ACCEPTED.value
        sub.execution_time_ms = 42.5
        self.db.commit()

        fetched = self.db.query(Submission).filter(Submission.id == sub.id).first()
        self.assertEqual(fetched.status, "ACCEPTED")
        self.assertEqual(fetched.execution_time_ms, 42.5)


if __name__ == "__main__":
    unittest.main()
