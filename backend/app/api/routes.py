"""REST routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services import portfolio, watchlist

try:  # LLM module is provided by another engineer
    from app.llm import run_chat
except ImportError:  # pragma: no cover
    run_chat = None

router = APIRouter(prefix="/api")
_chat_lock = asyncio.Lock()


class TradeIn(BaseModel):
    ticker: str
    quantity: float
    side: str


class TickerIn(BaseModel):
    ticker: str


class ChatIn(BaseModel):
    message: str


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message})


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/portfolio")
async def get_portfolio():
    return portfolio.get_portfolio()


@router.post("/portfolio/trade")
async def trade(body: TradeIn):
    try:
        result = portfolio.execute_trade(body.ticker, body.side, body.quantity)
    except portfolio.TradeError as e:
        return _err(400, e.code, e.message)
    return {"trade": result, "portfolio": portfolio.get_portfolio()}


@router.get("/portfolio/history")
async def history():
    return {"snapshots": portfolio.get_history()}


@router.get("/watchlist")
async def get_watchlist():
    return watchlist.get_watchlist()


@router.post("/watchlist")
async def add_watchlist(body: TickerIn):
    try:
        return await watchlist.add_ticker(body.ticker)
    except watchlist.WatchlistError as e:
        return _err(400, e.code, e.message)


@router.delete("/watchlist/{ticker}")
async def remove_watchlist(ticker: str):
    try:
        await watchlist.remove_ticker(ticker)
    except watchlist.WatchlistError as e:
        return _err(400, e.code, e.message)
    return {"status": "removed", "ticker": ticker.upper()}


@router.post("/chat")
async def chat(body: ChatIn):
    if run_chat is None:
        return _err(503, "llm_unavailable", "LLM module not available")
    if _chat_lock.locked():
        return _err(429, "chat_busy", "A chat request is already in progress")
    async with _chat_lock:
        try:
            return await run_chat(body.message)
        except Exception as e:  # noqa: BLE001
            return _err(500, "chat_failed", str(e))
