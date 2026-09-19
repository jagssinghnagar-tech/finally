from app.llm.schema import LLMResponse, TradeRequest, WatchlistChange


def mock_response(message: str) -> LLMResponse:
    """Deterministic mock LLM reply, no network."""
    m = message.lower()
    if "buy" in m:
        return LLMResponse(
            message="Buying 1 share of AAPL for you.",
            trades=[TradeRequest(ticker="AAPL", side="buy", quantity=1)],
        )
    if "sell" in m:
        return LLMResponse(
            message="Selling 1 share of AAPL.",
            trades=[TradeRequest(ticker="AAPL", side="sell", quantity=1)],
        )
    if "add" in m:
        return LLMResponse(
            message="Adding PYPL to your watchlist.",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )
    if "remove" in m:
        return LLMResponse(
            message="Removing PYPL from your watchlist.",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="remove")],
        )
    return LLMResponse(
        message="Your portfolio looks reasonably balanced. Consider diversifying "
        "and keeping some cash in reserve."
    )
