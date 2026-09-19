"""Chat orchestration: context -> LLM -> auto-execute -> persist."""

import asyncio
import inspect
import json
import logging
import os
from collections.abc import Callable
from typing import Any

from app.llm.mock import mock_response
from app.llm.schema import LLMResponse

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}  # only for DEFAULT_MODEL
MODEL = DEFAULT_MODEL  # kept for backwards compat; effective model read from LLM_MODEL
HISTORY_LIMIT = 20
LLM_ATTEMPTS = 3  # free models often 429/502 transiently
LLM_RETRY_DELAY = 2.0

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant. Analyze portfolio composition, risk "
    "concentration and P&L. Suggest trades with reasoning. Execute trades when the user "
    "asks or agrees. Manage the watchlist proactively. Be concise and data-driven. "
    "Always respond with valid JSON: "
    '{"message": str, "trades": [{"ticker", "side": "buy|sell", "quantity"}], '
    '"watchlist_changes": [{"ticker", "action": "add|remove"}]}. '
    "Leave arrays empty if no action is needed."
)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def call_llm(messages: list[dict]) -> str:
    from litellm import completion

    model = os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODEL
    kwargs: dict = {"num_retries": 3, "timeout": 90}
    if model == DEFAULT_MODEL:
        kwargs["extra_body"] = EXTRA_BODY
    if not model.endswith(":free"):
        kwargs["reasoning_effort"] = "low"
    response = completion(
        model=model, messages=messages, response_format=LLMResponse, **kwargs
    )
    return response.choices[0].message.content


def _default_deps() -> dict[str, Callable]:
    from app.db import repo
    from app.services import portfolio, watchlist

    return {
        "get_portfolio": portfolio.get_portfolio,
        "execute_trade": portfolio.execute_trade,
        "get_watchlist": watchlist.get_watchlist,
        "add_ticker": watchlist.add_ticker,
        "remove_ticker": watchlist.remove_ticker,
        "insert_chat_message": repo.insert_chat_message,
        "list_chat_messages": repo.list_chat_messages,
        "call_llm": call_llm,
    }


def parse_llm_output(raw: str | None) -> LLMResponse:
    """Parse structured output; never raises."""
    if not raw:
        return LLMResponse(message="Sorry, I received an empty response. Please try again.")
    try:
        return LLMResponse.model_validate_json(raw)
    except Exception:
        logger.warning("Malformed LLM output: %r", raw[:200])
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get("message"), str):
                return LLMResponse(message=data["message"])
        except Exception:
            pass
        return LLMResponse(message="Sorry, I could not process that response. Please try again.")


async def run_chat(message: str, deps: dict[str, Callable] | None = None) -> dict:
    """Run one chat turn. `deps` (full dict) may be injected for tests."""
    d = deps if deps is not None else _default_deps()
    history = await _maybe_await(d["list_chat_messages"](HISTORY_LIMIT))

    if os.environ.get("LLM_MOCK", "").lower() == "true":
        parsed = mock_response(message)
    else:
        try:
            portfolio = await _maybe_await(d["get_portfolio"]())
            watchlist = await _maybe_await(d["get_watchlist"]())
            context = json.dumps({"portfolio": portfolio, "watchlist": watchlist}, default=str)
            msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": "Current portfolio state (JSON): " + context},
            ]
            for h in history or []:
                msgs.append({"role": h["role"], "content": h["content"]})
            msgs.append({"role": "user", "content": message})
            raw = None
            for attempt in range(LLM_ATTEMPTS):
                try:
                    raw = await asyncio.to_thread(d["call_llm"], msgs)
                    break
                except Exception:
                    if attempt == LLM_ATTEMPTS - 1:
                        raise
                    logger.warning("LLM attempt %d failed; retrying", attempt + 1)
                    await asyncio.sleep(LLM_RETRY_DELAY * (attempt + 1))
            parsed = parse_llm_output(raw)
        except Exception:
            # Do not persist anything: history must not be polluted by failures.
            logger.exception("LLM call failed")
            return {
                "message": "Sorry, the AI service is unavailable right now.",
                "trades": [],
                "watchlist_changes": [],
                "error": "llm_unavailable",
            }
    await _maybe_await(d["insert_chat_message"]("user", message, None))

    trades: list[dict] = []
    for t in parsed.trades:
        ticker = t.ticker.upper()
        entry: dict = {"ticker": ticker, "side": t.side, "quantity": t.quantity}
        try:
            result = await _maybe_await(d["execute_trade"](ticker, t.side, t.quantity))
            entry["status"] = "executed"
            if isinstance(result, dict) and "price" in result:
                entry["price"] = result["price"]
        except Exception as e:
            entry.update(
                status="failed",
                error=getattr(e, "code", "error"),
                message=getattr(e, "message", str(e)),
            )
        trades.append(entry)

    changes: list[dict] = []
    for c in parsed.watchlist_changes:
        ticker = c.ticker.upper()
        entry = {"ticker": ticker, "action": c.action}
        try:
            fn = d["add_ticker"] if c.action == "add" else d["remove_ticker"]
            await _maybe_await(fn(ticker))
            entry["status"] = "executed"
        except Exception as e:
            entry.update(
                status="failed",
                error=getattr(e, "code", "error"),
                message=getattr(e, "message", str(e)),
            )
        changes.append(entry)

    actions = {"trades": trades, "watchlist_changes": changes}
    await _maybe_await(d["insert_chat_message"]("assistant", parsed.message, actions))
    return {"message": parsed.message, **actions}
