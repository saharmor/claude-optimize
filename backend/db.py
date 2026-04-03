"""SQLite database module for Claude Optimize.

Provides connection management (WAL mode, foreign keys), a lightweight
migration runner, and helper functions used by the store layer.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "claude_optimize.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def get_connection() -> sqlite3.Connection:
    """Return a new connection with WAL mode and foreign keys enabled."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations() -> None:
    """Apply any pending SQL migrations from the migrations/ directory.

    Migrations are numbered files like 001_initial.sql, 002_foo.sql, etc.
    Each is run once and recorded in `schema_migrations`.
    """
    conn = get_connection()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
        )
        conn.commit()

        applied = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        if not MIGRATIONS_DIR.is_dir():
            logger.info("No migrations directory found at %s", MIGRATIONS_DIR)
            return

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for mfile in migration_files:
            version = mfile.stem  # e.g. "001_initial"
            if version in applied:
                continue

            logger.info("Applying migration: %s", version)
            sql = mfile.read_text()
            # Run each statement individually within a single transaction
            # (executescript implicitly commits, breaking atomicity with the
            # migration-recording INSERT below).
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            logger.info("Migration %s applied successfully", version)

    except Exception:
        logger.exception("Migration failed")
        raise
    finally:
        conn.close()


def recover_stuck_jobs() -> None:
    """Mark any scan_runs or apply_jobs stuck in 'running'/'pending' as 'failed'.

    This handles the case where the server crashed mid-job.
    """
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute(
            """UPDATE scan_runs SET status = 'failed', error_text = 'Server restarted during scan',
               completed_at = ? WHERE status IN ('pending', 'running')""",
            (now,),
        )
        if cursor.rowcount:
            logger.info("Recovered %d stuck scan_runs", cursor.rowcount)

        # Also mark any stuck analyzer runs as failed
        cursor = conn.execute(
            """UPDATE scan_analyzer_runs SET status = 'failed', completed_at = ?
               WHERE status IN ('pending', 'running')""",
            (now,),
        )
        if cursor.rowcount:
            logger.info("Recovered %d stuck scan_analyzer_runs", cursor.rowcount)

        cursor = conn.execute(
            """UPDATE apply_jobs SET status = 'failed', error_text = 'Server restarted during apply',
               completed_at = ? WHERE status IN ('pending', 'running')""",
            (now,),
        )
        if cursor.rowcount:
            logger.info("Recovered %d stuck apply_jobs", cursor.rowcount)

        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Run migrations and recover stuck jobs. Call once at startup."""
    run_migrations()
    recover_stuck_jobs()
