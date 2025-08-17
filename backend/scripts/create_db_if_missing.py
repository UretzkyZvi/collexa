import os
import sys
import urllib.parse as up

try:
    import psycopg2  # type: ignore
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # type: ignore
except Exception as e:
    print(f"psycopg2 not installed in venv: {e}")
    sys.exit(1)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not set in environment")
    sys.exit(1)

p = up.urlparse(DATABASE_URL)
if not p.path or p.path == "/":
    print("DATABASE_URL has no database name in path")
    sys.exit(1)

dbname = p.path.lstrip("/")
# Build admin URL pointing to 'postgres' database, preserving query
admin_path = "/postgres"
admin_url = up.urlunparse(
    (p.scheme, p.netloc, admin_path, p.params, p.query, p.fragment)
)

try:
    conn = psycopg2.connect(admin_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
except Exception as e:
    print(f"Failed to connect to admin DB 'postgres': {e}")
    print(
        "You may need to ensure the 'postgres' database exists or provide an admin DB."
    )
    sys.exit(1)

try:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
    exists = cur.fetchone() is not None
    if exists:
        print(f"Database '{dbname}' already exists — skipping creation.")
    else:
        cur.execute(f'CREATE DATABASE "{dbname}"')
        print(f"Database '{dbname}' created.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to check/create database '{dbname}': {e}")
    sys.exit(1)
