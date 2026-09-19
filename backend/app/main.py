"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.db import repo
from app.db.connection import init_db
from app.market import create_market_data_source, create_stream_router
from app.services import portfolio, state

# Project-root .env; real environment variables take precedence.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL = 30.0


async def _snapshot_loop(interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            portfolio.record_snapshot()
        except Exception:  # noqa: BLE001
            logger.exception("snapshot failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    source = create_market_data_source(state.price_cache)
    state.configure(state.price_cache, source)
    tickers = [r["ticker"] for r in repo.list_watchlist()]
    tickers += [p["ticker"] for p in repo.list_positions()]
    await source.start(list(dict.fromkeys(tickers)))
    task = asyncio.create_task(_snapshot_loop(SNAPSHOT_INTERVAL))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await source.stop()


def create_app(static_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.include_router(create_stream_router(state.price_cache))
    app.include_router(api_router)
    sdir = Path(static_dir) if static_dir else Path(os.environ.get("STATIC_DIR", "static"))
    if sdir.is_dir():
        app.mount("/", StaticFiles(directory=sdir, html=True), name="static")
    return app


app = create_app()
