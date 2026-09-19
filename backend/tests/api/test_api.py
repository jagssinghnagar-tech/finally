import asyncio
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    with TestClient(create_app(static_dir=tmp_path / "nostatic")) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_portfolio_initial(client):
    d = client.get("/api/portfolio").json()
    assert d["cash_balance"] == 10000.0 and d["positions"] == []
    assert d["total_value"] == 10000.0


def test_watchlist_default_has_prices(client):
    w = client.get("/api/watchlist").json()
    assert len(w) == 10 and all(x["price"] for x in w)


def test_watchlist_add_remove(client):
    r = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert r.status_code == 200 and r.json()["ticker"] == "PYPL" and r.json()["price"]
    assert "PYPL" in [x["ticker"] for x in client.get("/api/watchlist").json()]
    assert client.delete("/api/watchlist/PYPL").status_code == 200
    assert "PYPL" not in [x["ticker"] for x in client.get("/api/watchlist").json()]


def test_watchlist_invalid(client):
    assert client.post("/api/watchlist", json={"ticker": "b@d!"}).status_code == 400


def test_buy_sell_cycle(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "buy"})
    assert r.status_code == 200
    p = r.json()["portfolio"]
    assert p["cash_balance"] < 10000 and p["positions"][0]["quantity"] == 5
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "sell"})
    assert r.status_code == 200 and r.json()["portfolio"]["positions"] == []
    assert len(client.get("/api/portfolio/history").json()["snapshots"]) >= 2


def test_insufficient_cash(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1e6, "side": "buy"})
    assert r.status_code == 400 and r.json()["error"] == "insufficient_cash"


def test_insufficient_shares(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert r.status_code == 400 and r.json()["error"] == "insufficient_shares"


def test_chat_concurrent_429(client, monkeypatch):
    async def slow(message):
        await asyncio.sleep(0.5)
        return {"message": message, "trades": [], "watchlist_changes": []}

    monkeypatch.setattr(routes, "run_chat", slow)
    results = []
    t = threading.Thread(
        target=lambda: results.append(client.post("/api/chat", json={"message": "a"}).status_code)
    )
    t.start()
    time.sleep(0.15)
    results.append(client.post("/api/chat", json={"message": "b"}).status_code)
    t.join()
    assert sorted(results) == [200, 429]


def test_chat_ok(client, monkeypatch):
    async def fake(message):
        return {"message": "hi", "trades": [], "watchlist_changes": []}

    monkeypatch.setattr(routes, "run_chat", fake)
    assert client.post("/api/chat", json={"message": "x"}).json()["message"] == "hi"
