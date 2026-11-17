"""Runtime configuration (environment variables only; no secrets in code)."""
import os
from pathlib import Path


def data_dir() -> Path:
    p = Path(os.environ.get("RAW_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
    p.mkdir(parents=True, exist_ok=True)
    (p / "uploads").mkdir(exist_ok=True)
    return p


def database_url() -> str:
    # SQLite by default (zero-cost local dev). Set RAW_DATABASE_URL=postgresql+psycopg://... for Postgres.
    return os.environ.get("RAW_DATABASE_URL", f"sqlite:///{data_dir() / 'raw.db'}")


MAX_UPLOAD_BYTES = int(os.environ.get("RAW_MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
MAX_URL_BYTES = int(os.environ.get("RAW_MAX_URL_BYTES", 1 * 1024 * 1024))
RATE_LIMIT_PER_MIN = int(os.environ.get("RAW_RATE_LIMIT_PER_MIN", 240))
WORKER_THREADS = int(os.environ.get("RAW_WORKER_THREADS", 2))
# Real providers read keys from the server environment only; they never reach clients.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
