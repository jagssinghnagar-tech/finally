"""SQLite connection handling and lazy initialization."""
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
_SCHEMA = Path(__file__).with_name("schema.sql")
_init_lock = threading.Lock()
_initialized: set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def get_db_path() -> str:
    env = os.environ.get("DB_PATH")
    if env:
        return env
    root = Path(__file__).resolve().parents[3]  # backend/app/db -> project root
    return str(root / "db" / "finally.db")


def init_db(path: str | None = None) -> None:
    """Create tables and seed defaults if missing. Idempotent."""
    path = path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
        ts = now_iso()
        fresh = conn.execute("SELECT 1 FROM users_profile WHERE id='default'").fetchone() is None
        if fresh:
            conn.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES ('default', 10000.0, ?)",
                (ts,),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
                [(new_id(), t, ts) for t in DEFAULT_TICKERS],
            )
        conn.commit()
    finally:
        conn.close()


def get_connection(path: str | None = None) -> sqlite3.Connection:
    """Open a new connection (lazily initializing the DB once per path)."""
    path = path or get_db_path()
    if path not in _initialized or not Path(path).exists():
        with _init_lock:
            init_db(path)
            _initialized.add(path)
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
