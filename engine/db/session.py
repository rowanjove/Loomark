import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from engine.config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create a connection with WAL mode and row factory."""
    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency read/write
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

@contextmanager
def get_db(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize database tables, FTS5 virtual tables, and triggers."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(db_path) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
        conn.executescript(sql_script)
        # Check and recover any dangling FETCHING URLs from previous crash
        conn.execute("UPDATE urls SET status='QUEUED' WHERE status='FETCHING';")
        conn.execute("UPDATE crawl_jobs SET status='PAUSED' WHERE status='RUNNING';")

        # Migrate monitor_schedules columns if missing
        try:
            cursor = conn.execute("PRAGMA table_info(monitor_schedules);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "schedule_type" not in columns:
                conn.execute("ALTER TABLE monitor_schedules ADD COLUMN schedule_type TEXT NOT NULL DEFAULT 'interval';")
            if "cron_expression" not in columns:
                conn.execute("ALTER TABLE monitor_schedules ADD COLUMN cron_expression TEXT;")
        except Exception:
            pass
