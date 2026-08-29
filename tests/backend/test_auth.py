"""
Backend Authentication Unit Tests.
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
from app.models import User

# In-memory SQLite DB setup
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestAuthEndpoints(unittest.TestCase):

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

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    def test_user_registration_success(self):
        payload = {
            "username": "coder123",
            "email": "coder123@example.com",
            "password": "SecurePassword123!",
        }
        res = self.client.post("/auth/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["username"], "coder123")
        self.assertEqual(data["user"]["email"], "coder123@example.com")

        # Verify DB entry
        user = self.db.query(User).filter(User.username == "coder123").first()
        self.assertIsNotNone(user)
        self.assertNotEqual(user.hashed_password, "SecurePassword123!")

    def test_duplicate_username_and_email_rejected(self):
        payload = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        }
        res1 = self.client.post("/auth/register", json=payload)
        self.assertEqual(res1.status_code, 201)

        # Duplicate username
        res2 = self.client.post("/auth/register", json={
            "username": "alice",
            "email": "another@example.com",
            "password": "password123",
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Username already registered", res2.json()["detail"])

        # Duplicate email
        res3 = self.client.post("/auth/register", json={
            "username": "bob",
            "email": "alice@example.com",
            "password": "password123",
        })
        self.assertEqual(res3.status_code, 400)
        self.assertIn("Email address already registered", res3.json()["detail"])

    def test_login_valid_credentials(self):
        self.client.post("/auth/register", json={
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "mypassword",
        })

        res = self.client.post("/auth/login", json={
            "username": "charlie",
            "password": "mypassword",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["username"], "charlie")

    def test_login_invalid_password(self):
        self.client.post("/auth/register", json={
            "username": "dave",
            "email": "dave@example.com",
            "password": "correctpassword",
        })

        res = self.client.post("/auth/login", json={
            "username": "dave",
            "password": "wrongpassword",
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Incorrect username or password", res.json()["detail"])

    def test_get_me_protected_endpoint(self):
        reg_res = self.client.post("/auth/register", json={
            "username": "eve",
            "email": "eve@example.com",
            "password": "evepassword",
        })
        token = reg_res.json()["access_token"]

        # Missing token -> 401
        res_no_auth = self.client.get("/auth/me")
        self.assertEqual(res_no_auth.status_code, 401)

        # Valid Bearer token -> 200
        res_auth = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_auth.status_code, 200)
        self.assertEqual(res_auth.json()["username"], "eve")
        self.assertEqual(res_auth.json()["email"], "eve@example.com")


if __name__ == "__main__":
    unittest.main()
