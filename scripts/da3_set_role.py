"""
CLI script to update a user's role.
Usage: python scripts/da3_set_role.py <username> <role>
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

ALLOWED_ROLES = {"student", "instructor", "admin"}


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    elif url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    if "sslmode" not in url and "localhost" not in url and "127.0.0.1" not in url:
        sep = "&" if "?" in url else "?"
        url = url + sep + "sslmode=require"

    return url


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/da3_set_role.py <username> <role>", file=sys.stderr)
        sys.exit(1)

    username = sys.argv[1]
    role = sys.argv[2].lower()

    if role not in ALLOWED_ROLES:
        print(f"Error: Invalid role '{role}'. Allowed roles: {', '.join(sorted(ALLOWED_ROLES))}", file=sys.stderr)
        sys.exit(1)

    db_url = get_db_url()
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET role = %s WHERE username = %s RETURNING username, role;",
                (role, username)
            )
            row = cur.fetchone()
            if not row:
                print(f"Error: User '{username}' not found.", file=sys.stderr)
                sys.exit(1)
            conn.commit()
            print(f"username: {row[0]}, role: {row[1]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
