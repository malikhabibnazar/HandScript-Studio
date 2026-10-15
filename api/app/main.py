"""Application entrypoint."""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.engine import process_one_tick
from app.routes import router

_stop = threading.Event()


def _worker_loop() -> None:
    while not _stop.is_set():
        db = SessionLocal()
        try:
            process_one_tick(db)
        except Exception:
            logging.exception("batch worker tick failed")
            db.rollback()
        finally:
            db.close()
        _stop.wait(get_settings().worker_tick_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _stop.clear()
    init_db()
    thread = None
    if get_settings().embedded_worker:
        thread = threading.Thread(target=_worker_loop, name="handscript-worker", daemon=True)
        thread.start()
    yield
    _stop.set()
    if thread is not None:
        thread.join(timeout=2)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HandScript Studio", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
