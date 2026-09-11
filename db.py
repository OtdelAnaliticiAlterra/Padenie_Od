import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def _build_url() -> str:
    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASS"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Не заданы переменные окружения: {', '.join(missing)}")

    pwd = urllib.parse.quote_plus(os.getenv("DB_PASS"))
    return (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{pwd}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )


_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_build_url(), pool_pre_ping=True)
    return _engine


def run_query(sql: str, params: dict):
    """Выполняет SQL с :named-параметрами и возвращает результат."""
    with get_engine().connect() as conn:
        return conn.execute(text(sql), params)