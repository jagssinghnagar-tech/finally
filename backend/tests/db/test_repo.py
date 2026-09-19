import pytest

from app import db


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "sub" / "t.db"))


def test_seed():
    assert db.get_cash() == 10000.0
    assert [w["ticker"] for w in db.list_watchlist()] == db.DEFAULT_TICKERS
    db.init_db()  # idempotent
    assert len(db.list_watchlist()) == 10


def test_watchlist_crud():
    assert db.add_watchlist("pypl")
    assert not db.add_watchlist("PYPL")
    assert db.remove_watchlist("AAPL")
    assert not db.remove_watchlist("AAPL")
    tickers = [w["ticker"] for w in db.list_watchlist()]
    assert "PYPL" in tickers and "AAPL" not in tickers
    db.init_db()  # must not re-seed removed tickers
    assert "AAPL" not in [w["ticker"] for w in db.list_watchlist()]


def test_buy_sell_flow():
    r = db.apply_trade("AAPL", "buy", 10, 100)
    assert r["cash"] == 9000
    db.apply_trade("AAPL", "buy", 10, 200)
    p = db.get_position("AAPL")
    assert p["quantity"] == 20 and p["avg_cost"] == 150
    db.apply_trade("AAPL", "sell", 5, 160)
    assert db.get_position("AAPL")["quantity"] == 15
    assert db.get_cash() == 7000 + 800
    db.apply_trade("AAPL", "sell", 15, 160)
    assert db.get_position("AAPL") is None and db.list_positions() == []
    assert len(db.list_trades()) == 4
    assert db.list_trades(1)[0]["side"] == "sell"


def test_trade_errors_leave_state():
    with pytest.raises(db.TradeError) as e:
        db.apply_trade("AAPL", "buy", 1000, 100)
    assert e.value.code == "insufficient_cash"
    with pytest.raises(db.TradeError) as e:
        db.apply_trade("AAPL", "sell", 1, 100)
    assert e.value.code == "insufficient_shares"
    with pytest.raises(db.TradeError):
        db.apply_trade("AAPL", "buy", -1, 100)
    assert db.get_cash() == 10000 and db.list_trades() == []


def test_fractional_and_upsert_zero():
    db.upsert_position("TSLA", 1.5, 10)
    db.upsert_position("TSLA", 2.5, 11)
    assert db.get_position("TSLA")["quantity"] == 2.5
    db.upsert_position("TSLA", 0, 11)
    assert db.get_position("TSLA") is None
    assert not db.delete_position("TSLA")


def test_snapshots_and_chat():
    for v in (1, 2, 3):
        db.insert_snapshot(v)
    assert [s["total_value"] for s in db.list_snapshots()] == [1, 2, 3]
    assert [s["total_value"] for s in db.list_snapshots(2)] == [2, 3]
    db.insert_chat_message("user", "hi")
    db.insert_chat_message("assistant", "yo", {"trades": [1]})
    db.insert_chat_message("user", "again")
    m = db.list_chat_messages(2)
    assert [x["content"] for x in m] == ["yo", "again"]
    assert m[0]["actions"] == {"trades": [1]} and m[1]["actions"] is None
