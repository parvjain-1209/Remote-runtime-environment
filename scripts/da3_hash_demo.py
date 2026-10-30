"""
Database Hashing & Password Migration Demo Script.
Demonstrates legacy plain-text storage vs bcrypt hashed/salted storage.
"""

import os
import sys
import bcrypt
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Normalize dialect prefixes
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    elif url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    # Cloud PostgreSQL (e.g. Render) requires SSL
    if "sslmode" not in url and "localhost" not in url and "127.0.0.1" not in url:
        sep = "&" if "?" in url else "?"
        url = url + sep + "sslmode=require"

    return url


def print_table(headers: list[str], rows: list[tuple]) -> None:
    """Formats and prints rows as an aligned plain-text table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(separator)
    for row in rows:
        print(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))


def handle_before(conn) -> None:
    with conn.cursor() as cur:
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users_legacy_demo (
                id serial primary key,
                username text,
                email text,
                password text
            );
        """)
        # If table existed from an 'after' run where password was dropped, recreate
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users_legacy_demo' AND column_name = 'password';
        """)
        if not cur.fetchone():
            cur.execute("DROP TABLE users_legacy_demo;")
            cur.execute("""
                CREATE TABLE users_legacy_demo (
                    id serial primary key,
                    username text,
                    email text,
                    password text
                );
            """)
        else:
            cur.execute("TRUNCATE TABLE users_legacy_demo;")

        # Insert 3 fake users
        cur.execute("""
            INSERT INTO users_legacy_demo (username, email, password) VALUES
            (%s, %s, %s),
            (%s, %s, %s),
            (%s, %s, %s);
        """, (
            "alice", "alice@example.com", "Test@1234",
            "bob", "bob@example.com", "Test@1234",
            "carol", "carol@example.com", "Secret@5678",
        ))
        conn.commit()

        cur.execute("SELECT id, username, password FROM users_legacy_demo ORDER BY id;")
        rows = cur.fetchall()

    print_table(["id", "username", "password"], rows)


def handle_after(conn) -> None:
    with conn.cursor() as cur:
        # Add password_hash column if not present
        cur.execute("ALTER TABLE users_legacy_demo ADD COLUMN IF NOT EXISTS password_hash text;")

        # Fetch plain text passwords
        cur.execute("SELECT id, username, password FROM users_legacy_demo ORDER BY id;")
        rows = cur.fetchall()

        # Hash with bcrypt using 12 rounds of salt and update
        for row_id, username, plain_pw in rows:
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(plain_pw.encode("utf-8"), salt).decode("utf-8")
            cur.execute(
                "UPDATE users_legacy_demo SET password_hash = %s WHERE id = %s;",
                (hashed, row_id)
            )

        # Drop the plain-text column "password"
        cur.execute("ALTER TABLE users_legacy_demo DROP COLUMN IF EXISTS password;")
        conn.commit()

        # Print all rows
        cur.execute("SELECT id, username, password_hash FROM users_legacy_demo ORDER BY id;")
        updated_rows = cur.fetchall()

    print_table(["id", "username", "password_hash"], updated_rows)

    # Verify bcrypt hashes
    alice_hash = next((r[2] for r in updated_rows if r[1] == "alice"), None)
    bob_hash = next((r[2] for r in updated_rows if r[1] == "bob"), None)

    if alice_hash and bob_hash:
        alice_match = bcrypt.checkpw(b"Test@1234", alice_hash.encode("utf-8"))
        bob_match = bcrypt.checkpw(b"Test@1234", bob_hash.encode("utf-8"))
        print()
        print(f"alice password checkpw ('Test@1234'): {alice_match}")
        print(f"bob password checkpw ('Test@1234'): {bob_match}")
        print(f"alice == bob hash? {alice_hash == bob_hash}")


def handle_real(conn) -> None:
    with conn.cursor() as cur:
        # Read-only: never print emails or full hashes
        cur.execute("SELECT id, username, left(hashed_password, 30) FROM users ORDER BY id LIMIT 5;")
        rows = cur.fetchall()

    print_table(["id", "username", "left(hashed_password, 30)"], rows)


def handle_cleanup(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS users_legacy_demo;")
        conn.commit()
    print("Table users_legacy_demo dropped.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/da3_hash_demo.py [before|after|real|cleanup]")
        sys.exit(1)

    action = sys.argv[1].lower()
    db_url = get_db_url()

    conn = psycopg2.connect(db_url)
    try:
        if action == "before":
            handle_before(conn)
        elif action == "after":
            handle_after(conn)
        elif action == "real":
            handle_real(conn)
        elif action == "cleanup":
            handle_cleanup(conn)
        else:
            print(f"Unknown action: {action}. Choose from before, after, real, cleanup.")
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
