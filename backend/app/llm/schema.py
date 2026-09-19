from typing import Literal

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeRequest] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)
