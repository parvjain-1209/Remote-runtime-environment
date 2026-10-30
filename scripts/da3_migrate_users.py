"""
Database Migration Script for Users Table.
Adds role, mfa_secret, and is_mfa_enabled columns.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()


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


def print_table(headers: list[str], rows: list[tuple]) -> None:
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


def main():
    db_url = get_db_url()
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'student';
                ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR(64);
                ALTER TABLE users ADD COLUMN IF NOT EXISTS is_mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
            """)
            conn.commit()

            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position;
            """)
            rows = cur.fetchall()

        print("Users table columns after migration:")
        print_table(["column_name", "data_type", "is_nullable", "column_default"], rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
