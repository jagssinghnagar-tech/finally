"""Repository functions (single-user, user_id='default').

Every function takes an optional trailing ``conn`` (sqlite3.Connection). If omitted,
a short-lived connection is opened, committed and closed. Rows return as dicts.

Cash:        get_cash() -> float ; set_cash(amount)
Watchlist:   list_watchlist() -> [{id,user_id,ticker,added_at}] ; add_watchlist(ticker) -> bool
             (False if already present) ; remove_watchlist(ticker) -> bool
Positions:   list_positions() ; get_position(ticker) -> dict|None ;
             upsert_position(ticker, quantity, avg_cost) (deletes row if quantity <= 0) ;
             delete_position(ticker) -> bool
Trades:      insert_trade(ticker, side, quantity, price) -> dict ; list_trades(limit=None) (newest first)
Snapshots:   insert_snapshot(total_value) -> dict ; list_snapshots(limit=None) (oldest first)
Chat:        insert_chat_message(role, content, actions=None) -> dict (actions JSON-serialised) ;
             list_chat_messages(limit=50) (most recent N, oldest first; actions decoded)
Atomic:      apply_trade(ticker, side, quantity, price) -> {trade, cash, position|None}
             Validates and applies cash + position + trade in one transaction.
             Raises TradeError(code, message); code is 'insufficient_cash' |
             'insufficient_shares' | 'invalid_trade'.
Tickers are upper-cased.
"""
import json
from contextlib import contextmanager

from .connection import get_connection, new_id, now_iso

USER = "default"
_EPS = 1e-9


class TradeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@contextmanager
def _use(conn):
    if conn is not None:
        yield conn
        return
    c = get_connection()
    try:
        yield c
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally:
        c.close()


def _rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def _t(ticker: str) -> str:
    return ticker.strip().upper()


# Cash
def get_cash(conn=None) -> float:
    with _use(conn) as c:
        return c.execute("SELECT cash_balance FROM users_profile WHERE id=?", (USER,)).fetchone()[0]


def set_cash(amount: float, conn=None) -> None:
    with _use(conn) as c:
        c.execute("UPDATE users_profile SET cash_balance=? WHERE id=?", (amount, USER))


# Watchlist
def list_watchlist(conn=None) -> list[dict]:
    with _use(conn) as c:
        return _rows(c.execute("SELECT * FROM watchlist WHERE user_id=? ORDER BY added_at, rowid", (USER,)))


def add_watchlist(ticker: str, conn=None) -> bool:
    with _use(conn) as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO watchlist (id,user_id,ticker,added_at) VALUES (?,?,?,?)",
            (new_id(), USER, _t(ticker), now_iso()),
        )
        return cur.rowcount > 0


def remove_watchlist(ticker: str, conn=None) -> bool:
    with _use(conn) as c:
        return c.execute("DELETE FROM watchlist WHERE user_id=? AND ticker=?", (USER, _t(ticker))).rowcount > 0


# Positions
def list_positions(conn=None) -> list[dict]:
    with _use(conn) as c:
        return _rows(c.execute("SELECT * FROM positions WHERE user_id=? ORDER BY ticker", (USER,)))


def get_position(ticker: str, conn=None) -> dict | None:
    with _use(conn) as c:
        r = c.execute("SELECT * FROM positions WHERE user_id=? AND ticker=?", (USER, _t(ticker))).fetchone()
        return dict(r) if r else None


def delete_position(ticker: str, conn=None) -> bool:
    with _use(conn) as c:
        return c.execute("DELETE FROM positions WHERE user_id=? AND ticker=?", (USER, _t(ticker))).rowcount > 0


def upsert_position(ticker: str, quantity: float, avg_cost: float, conn=None) -> None:
    with _use(conn) as c:
        if quantity <= _EPS:
            delete_position(ticker, c)
            return
        c.execute(
            "INSERT INTO positions (id,user_id,ticker,quantity,avg_cost,updated_at) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(user_id,ticker) DO UPDATE SET quantity=excluded.quantity, "
            "avg_cost=excluded.avg_cost, updated_at=excluded.updated_at",
            (new_id(), USER, _t(ticker), quantity, avg_cost, now_iso()),
        )


# Trades
def insert_trade(ticker: str, side: str, quantity: float, price: float, conn=None) -> dict:
    row = {"id": new_id(), "user_id": USER, "ticker": _t(ticker), "side": side,
           "quantity": quantity, "price": price, "executed_at": now_iso()}
    with _use(conn) as c:
        c.execute("INSERT INTO trades VALUES (:id,:user_id,:ticker,:side,:quantity,:price,:executed_at)", row)
    return row


def list_trades(limit: int | None = None, conn=None) -> list[dict]:
    with _use(conn) as c:
        q = "SELECT * FROM trades WHERE user_id=? ORDER BY executed_at DESC, rowid DESC"
        args: tuple = (USER,)
        if limit is not None:
            q += " LIMIT ?"
            args += (limit,)
        return _rows(c.execute(q, args))


# Snapshots
def insert_snapshot(total_value: float, conn=None) -> dict:
    row = {"id": new_id(), "user_id": USER, "total_value": total_value, "recorded_at": now_iso()}
    with _use(conn) as c:
        c.execute("INSERT INTO portfolio_snapshots VALUES (:id,:user_id,:total_value,:recorded_at)", row)
    return row


def list_snapshots(limit: int | None = None, conn=None) -> list[dict]:
    """Oldest first; with limit, the most recent ``limit`` rows."""
    with _use(conn) as c:
        q = "SELECT * FROM portfolio_snapshots WHERE user_id=? ORDER BY recorded_at DESC, rowid DESC"
        args: tuple = (USER,)
        if limit is not None:
            q += " LIMIT ?"
            args += (limit,)
        return _rows(c.execute(q, args))[::-1]


# Chat
def insert_chat_message(role: str, content: str, actions=None, conn=None) -> dict:
    row = {"id": new_id(), "user_id": USER, "role": role, "content": content,
           "actions": json.dumps(actions) if actions is not None else None, "created_at": now_iso()}
    with _use(conn) as c:
        c.execute("INSERT INTO chat_messages VALUES (:id,:user_id,:role,:content,:actions,:created_at)", row)
    return {**row, "actions": actions}


def list_chat_messages(limit: int = 50, conn=None) -> list[dict]:
    """Most recent ``limit`` messages, oldest first."""
    with _use(conn) as c:
        rows = _rows(c.execute(
            "SELECT * FROM chat_messages WHERE user_id=? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (USER, limit)))
    for r in rows:
        r["actions"] = json.loads(r["actions"]) if r["actions"] else None
    return rows[::-1]


# Atomic trade
def apply_trade(ticker: str, side: str, quantity: float, price: float, conn=None) -> dict:
    """Validate and apply a trade atomically (cash + position + trade log)."""
    ticker = _t(ticker)
    if side not in ("buy", "sell") or quantity <= 0 or price <= 0:
        raise TradeError("invalid_trade", "Side must be buy/sell; quantity and price must be positive.")
    own = conn is None
    c = conn or get_connection()
    try:
        if own:
            c.execute("BEGIN IMMEDIATE")
        cash = get_cash(c)
        pos = get_position(ticker, c)
        held = pos["quantity"] if pos else 0.0
        cost = quantity * price
        if side == "buy":
            if cost > cash + _EPS:
                raise TradeError("insufficient_cash", f"Need ${cost:,.2f} but only ${cash:,.2f} available.")
            new_qty = held + quantity
            avg = (held * pos["avg_cost"] + cost) / new_qty if pos else price
            cash -= cost
        else:
            if quantity > held + _EPS:
                raise TradeError("insufficient_shares", f"Cannot sell {quantity} {ticker}; only {held} held.")
            new_qty = held - quantity
            avg = pos["avg_cost"]
            cash += cost
        set_cash(cash, c)
        upsert_position(ticker, new_qty, avg, c)
        trade = insert_trade(ticker, side, quantity, price, c)
        result = {"trade": trade, "cash": cash, "position": get_position(ticker, c)}
        if own:
            c.commit()
        return result
    except BaseException:
        if own:
            c.rollback()
        raise
    finally:
        if own:
            c.close()
