"""Shared runtime state (price cache + market data source), set by app lifespan."""

from __future__ import annotations

from app.market import MarketDataSource, PriceCache

price_cache: PriceCache = PriceCache()
market_source: MarketDataSource | None = None


def configure(cache: PriceCache, source: MarketDataSource | None) -> None:
    global price_cache, market_source
    price_cache = cache
    market_source = source
