"""Watchlist service."""

from __future__ import annotations

import re

from app.db import repo
from app.services import state

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


class WatchlistError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_ticker(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not _TICKER_RE.match(t):
        raise WatchlistError("invalid_ticker", f"Invalid ticker: {ticker!r}")
    return t


def _entry(ticker: str) -> dict:
    u = state.price_cache.get(ticker)
    return {
        "ticker": ticker,
        "price": u.price if u else None,
        "previous_price": u.previous_price if u else None,
        "change": u.change if u else None,
        "change_percent": u.change_percent if u else None,
        "direction": u.direction if u else "flat",
    }


def get_watchlist() -> list[dict]:
    return [_entry(r["ticker"]) for r in repo.list_watchlist()]


async def add_ticker(ticker: str) -> dict:
    t = normalize_ticker(ticker)
    repo.add_watchlist(t)
    if state.market_source is not None:
        await state.market_source.add_ticker(t)
    return _entry(t)


async def remove_ticker(ticker: str) -> None:
    t = normalize_ticker(ticker)
    repo.remove_watchlist(t)
    # Keep streaming prices for tickers still held in positions.
    held = {p["ticker"] for p in repo.list_positions()}
    if state.market_source is not None and t not in held:
        await state.market_source.remove_ticker(t)
