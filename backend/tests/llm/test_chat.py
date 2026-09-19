import json

from app.llm import run_chat
from app.llm.chat import parse_llm_output


class TradeError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def make_deps(llm_out="", fail=False):
    store = []
    calls = []

    def execute_trade(t, s, q):
        calls.append(("trade", t, s, q))
        if fail:
            raise TradeError("insufficient_cash", "no cash")
        return {"price": 190.0}

    deps = {
        "get_portfolio": lambda: {"cash": 10000},
        "get_watchlist": lambda: [],
        "execute_trade": execute_trade,
        "add_ticker": lambda t: calls.append(("add", t)),
        "remove_ticker": lambda t: calls.append(("remove", t)),
        "insert_chat_message": lambda r, c, a: store.append((r, c, a)),
        "list_chat_messages": lambda n: [],
        "call_llm": lambda m: llm_out,
    }
    return deps, store, calls


async def test_mock_buy(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    deps, store, calls = make_deps()
    r = await run_chat("please buy", deps=deps)
    assert calls == [("trade", "AAPL", "buy", 1)]
    assert r["trades"][0]["status"] == "executed"
    assert [s[0] for s in store] == ["user", "assistant"]
    assert store[1][2]["trades"]


async def test_mock_watchlist_and_default(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    deps, _, calls = make_deps()
    await run_chat("add something", deps=deps)
    assert calls == [("add", "PYPL")]
    r = await run_chat("how am I doing", deps=deps)
    assert r["trades"] == [] and r["message"]


async def test_trade_failure_reported(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    deps, _, _ = make_deps(fail=True)
    r = await run_chat("buy", deps=deps)
    assert r["trades"][0]["status"] == "failed"
    assert r["trades"][0]["error"] == "insufficient_cash"


async def test_real_path_parses(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    out = json.dumps(
        {"message": "ok", "trades": [{"ticker": "tsla", "side": "sell", "quantity": 2}]}
    )
    deps, _, calls = make_deps(llm_out=out)
    r = await run_chat("hi", deps=deps)
    assert calls == [("trade", "TSLA", "sell", 2)]
    assert r["message"] == "ok"


async def test_malformed_output(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    deps, _, calls = make_deps(llm_out="not json")
    r = await run_chat("hi", deps=deps)
    assert calls == [] and r["message"]


def test_parse_variants():
    assert parse_llm_output(None).message
    assert parse_llm_output('{"message": "x", "trades": "bad"}').message == "x"
    assert parse_llm_output('{"message": "y"}').trades == []


async def test_llm_failure_not_persisted(monkeypatch):
    monkeypatch.setattr("app.llm.chat.LLM_RETRY_DELAY", 0)
    monkeypatch.setenv("LLM_MOCK", "false")
    deps, store, calls = make_deps()

    def boom(m):
        raise RuntimeError("402")

    deps["call_llm"] = boom
    r = await run_chat("hi", deps=deps)
    assert r["error"] == "llm_unavailable"
    assert store == [] and calls == []
