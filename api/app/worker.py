"""External worker. Polls PostgreSQL and, when configured, waits on Redis."""
from __future__ import annotations

import gc
import logging
import time

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.engine import process_one_tick


def _wait() -> None:
    settings = get_settings()
    if not settings.redis_url:
        time.sleep(settings.worker_tick_seconds)
        return
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url)
        client.blpop("handscript:jobs", timeout=1)
        client.close()
    except Exception:
        time.sleep(settings.worker_tick_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_db()
    while True:
        db = SessionLocal()
        advanced = None
        try:
            advanced = process_one_tick(db)
        except Exception:
            logging.exception("batch worker tick failed")
            db.rollback()
        finally:
            db.close()
            gc.collect()
        if not advanced:
            _wait()


if __name__ == "__main__":
    main()
