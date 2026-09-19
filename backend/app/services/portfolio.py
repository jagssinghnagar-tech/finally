"""Portfolio service: valuation, trades, snapshots."""

from __future__ import annotations

from app.db import repo
from app.services import state


class TradeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def get_portfolio() -> dict:
    cash = float(repo.get_cash())
    positions = []
    holdings = 0.0
    for p in repo.list_positions():
        ticker, qty, avg = p["ticker"], float(p["quantity"]), float(p["avg_cost"])
        price = state.price_cache.get_price(ticker)
        if price is None:
            price = avg
        value = qty * price
        holdings += value
        positions.append(
            {
                "ticker": ticker,
                "quantity": qty,
                "avg_cost": avg,
                "current_price": price,
                "market_value": value,
                "unrealized_pnl": (price - avg) * qty,
                "pnl_percent": ((price - avg) / avg * 100) if avg else 0.0,
            }
        )
    cost = sum(x["avg_cost"] * x["quantity"] for x in positions)
    return {
        "cash_balance": cash,
        "positions": positions,
        "total_value": cash + holdings,
        "unrealized_pnl": holdings - cost,
    }


def record_snapshot() -> float:
    total = get_portfolio()["total_value"]
    repo.insert_snapshot(total)
    return total


def get_history() -> list[dict]:
    return [
        {"total_value": s["total_value"], "recorded_at": s["recorded_at"]}
        for s in repo.list_snapshots()
    ]


def execute_trade(ticker: str, side: str, quantity: float) -> dict:
    ticker = (ticker or "").strip().upper()
    side = (side or "").strip().lower()
    if side not in ("buy", "sell"):
        raise TradeError("invalid_side", "Side must be 'buy' or 'sell'")
    if not ticker:
        raise TradeError("invalid_ticker", "Ticker is required")
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise TradeError("invalid_quantity", "Quantity must be a number") from None
    if not quantity > 0:
        raise TradeError("invalid_quantity", "Quantity must be positive")
    price = state.price_cache.get_price(ticker)
    if price is None:
        raise TradeError("no_price", f"No price available for {ticker}")
    try:
        repo.apply_trade(ticker, side, quantity, price)
    except repo.TradeError as e:
        raise TradeError(e.code, e.message) from None
    record_snapshot()
    return {
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "total": quantity * price,
    }
