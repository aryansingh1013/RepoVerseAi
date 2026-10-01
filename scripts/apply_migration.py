"""Apply the Phase 1 Supabase migration.

Two ways to run the migration — pick ONE:

OPTION A (recommended, no password needed):
  1. Open https://supabase.com/dashboard -> your project
  2. SQL Editor -> New query
  3. Paste the full content of supabase/migrations/00001_init.sql
  4. Run, then verify with:  python scripts/apply_migration.py --check

OPTION B (programmatic, needs the database password):
  Get the Postgres password from Dashboard -> Project Settings -> Database,
  then run:
      python scripts/apply_migration.py --password "YOUR_DB_PASSWORD"

  Or paste the full connection string from the dashboard (recommended,
  use the 'Connection pooling' / Transaction pooler string):
      python scripts/apply_migration.py --dsn "postgresql://postgres.xxx:PASSWORD@aws-0-xx-xxxx-x.pooler.supabase.com:6543/postgres"

  This executes the SQL over a direct Postgres connection (psycopg2).

Flags:
  --check     Only verify whether tables exist (no changes)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

MIGRATION_PATH = os.path.join(os.path.dirname(__file__), "..", "supabase", "migrations", "00001_init.sql")

EXPECTED_TABLES = [
    "profiles", "repositories", "repository_branches", "repository_commits",
    "files", "symbols", "chunks", "indexing_jobs",
    "conversations", "messages", "citations",
    "skills", "skill_runs", "user_settings",
]


def check_tables(verbose: bool = True) -> tuple[list, list]:
    from backend.database.client import get_supabase_admin
    admin = get_supabase_admin()
    existing, missing = [], []
    for t in EXPECTED_TABLES:
        try:
            admin.table(t).select("*").limit(1).execute()
            existing.append(t)
        except Exception as e:
            msg = str(e)
            if "Could not find the table" in msg or "does not exist" in msg or "schema cache" in msg:
                missing.append(t)
            else:
                existing.append(t)  # reachable but errored otherwise
    if verbose:
        print(f"Existing tables : {len(existing)}/{len(EXPECTED_TABLES)}")
        if missing:
            print("MISSING:", ", ".join(missing))
            print("\nMigration not fully applied yet. See instructions at top of scripts/apply_migration.py")
        else:
            print("ALL TABLES PRESENT - migration applied.")
    return existing, missing


def load_sql() -> str:
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        return f.read()


def run_via_postgres(dsn: str):
    """Execute the migration SQL over a direct Postgres connection."""
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Run:  pip install psycopg2-binary")
        sys.exit(1)

    sql = load_sql()
    print(f"Connecting: {dsn.split('@')[-1]} ...")
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("Migration executed successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"Migration FAILED: {exc}")
        sys.exit(1)
    finally:
        conn.close()
    check_tables()


def run_via_rest(password: str):
    """Try the Supabase /pg endpoint (works only on some projects)."""
    import requests
    sql = load_sql()

    url = os.getenv("SUPABASE_URL") or input("SUPABASE_URL: ").strip()
    resp = requests.post(
        f"{url.rstrip('/')}/pg",
        json={"query": sql},
        headers={
            "Authorization": f"Bearer {password}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    print(f"HTTP {resp.status_code}")
    if resp.status_code in (200, 201):
        print("Migration executed.")
        check_tables()
    else:
        print(resp.text[:2000])
        print("\n/pg endpoint unavailable. Use --dsn (Option B) or the SQL Editor (Option A).")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply/verify the Phase 1 Supabase migration")
    parser.add_argument("--check", action="store_true", help="only verify table existence")
    parser.add_argument("--password", help="Postgres password — tries /pg endpoint first")
    parser.add_argument("--dsn", help="Full Postgres connection string (most reliable programmatic option)")
    args = parser.parse_args()

    if args.dsn:
        run_via_postgres(args.dsn)
    elif args.password:
        run_via_rest(args.password)
    else:
        existing, missing = check_tables()
        if missing and not args.check:
            print("\nTo apply the migration now, run with --password or use the SQL Editor (Option A).")
