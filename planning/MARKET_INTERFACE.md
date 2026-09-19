# Market Data Interface

Unified Python API for stock prices in FinAlly. Code lives in `backend/app/market/`. It uses the Massive API when `MASSIVE_API_KEY` is set, and the built-in simulator otherwise. Downstream code never knows which.

## 1. Design principles

1. **Push into a cache, read from the cache.** A data source runs a background task and writes to `PriceCache`. SSE, portfolio valuation, trade execution and LLM chat context all read the same cache (PLAN.md §13). Nothing calls a provider on the request path.
2. **One abstract interface, two implementations** (strategy pattern), chosen once by a factory.
3. **Immutable value objects** (`PriceUpdate`) cross module boundaries.
4. **Provider quirks stay inside the adapter** (units, missing fields, rate limits).

```
create_market_data_source(cache)
        │  MASSIVE_API_KEY set?
   ┌────┴─────────────┐
   ▼                  ▼
MassiveDataSource  SimulatorDataSource        (both: MarketDataSource ABC)
   └────────┬─────────┘
            ▼ cache.update(ticker, price[, ts])
        PriceCache ──► SSE /api/stream/prices
                   ├─► GET /api/portfolio, /api/watchlist
                   ├─► POST /api/portfolio/trade (fill price)
                   └─► POST /api/chat (portfolio context)
```

## 2. Module layout

| File | Responsibility |
|---|---|
| `models.py` | `PriceUpdate` frozen dataclass |
| `cache.py` | `PriceCache` thread-safe store + version counter |
| `interface.py` | `MarketDataSource` ABC |
| `simulator.py` | `GBMSimulator` + `SimulatorDataSource` (see MARKET_SIMULATOR.md) |
| `massive_client.py` | `MassiveDataSource` (see MASSIVE_API.md) |
| `factory.py` | `create_market_data_source()` |
| `stream.py` | `create_stream_router()` SSE endpoint |
| `seed_prices.py` | Seed prices, GBM params, correlation groups |
| `__init__.py` | Public exports |

## 3. Public API

### PriceUpdate

```python
@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float            # Unix seconds
    # properties: change, change_percent, direction ("up"|"down"|"flat")
    def to_dict(self) -> dict   # ticker, price, previous_price, timestamp, change, change_percent, direction
```

`previous_price` is the previous *cache update*, which drives the flash animation; it is not the prior day's close. The watchlist's "daily change %" needs a separate baseline (see §7).

### PriceCache

```python
cache = PriceCache()
cache.update(ticker, price, timestamp=None) -> PriceUpdate   # writers only
cache.get(ticker) -> PriceUpdate | None
cache.get_price(ticker) -> float | None
cache.get_all() -> dict[str, PriceUpdate]                    # shallow copy
cache.remove(ticker)
cache.version -> int                                          # bumped on every update
ticker in cache, len(cache)
```

The lock makes it safe for writers on threads and readers on the event loop. The first update for a ticker gives `previous_price == price` (direction `flat`).

### MarketDataSource (ABC)

```python
class MarketDataSource(ABC):
    async def start(self, tickers: list[str]) -> None   # once; begins background task
    async def stop(self) -> None                         # idempotent
    async def add_ticker(self, ticker: str) -> None      # no-op if present
    async def remove_ticker(self, ticker: str) -> None   # also evicts from cache
    def get_tickers(self) -> list[str]
```

### Factory

```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    return MassiveDataSource(api_key=key, price_cache=price_cache) if key \
           else SimulatorDataSource(price_cache=price_cache)
```

Returns an unstarted source.

## 4. Usage in the FastAPI app

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

cache = PriceCache()
source = create_market_data_source(cache)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await source.start(load_watchlist_tickers())   # from SQLite
    yield
    await source.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(create_stream_router(cache))

# Watchlist routes
#   POST   /api/watchlist   -> DB insert, then `await source.add_ticker(t)`
#   DELETE /api/watchlist/X -> DB delete, then `await source.remove_ticker(t)`
# Trades / portfolio / chat: `cache.get_price(t)`; a None price means reject the trade
```

Normalise tickers (`upper().strip()`) at the API boundary; both sources also do so on add.

## 5. SSE contract

`GET /api/stream/prices` sends ~every 500 ms, only when `cache.version` has changed:

```
data: {"AAPL": {"ticker":"AAPL","price":190.5,"previous_price":190.4,"timestamp":1758225600.1,"change":0.1,"change_percent":0.0525,"direction":"up"}, ...}
```

The stream carries all cached tickers as one JSON object keyed by ticker. It includes a `retry:` directive so `EventSource` auto-reconnects. The frontend accumulates sparkline history from these events.

## 6. Provider differences hidden by the adapters

| Concern | Simulator | Massive |
|---|---|---|
| Update cadence | 500 ms | Poll interval (15 s default; 2–5 s on paid) |
| New ticker price | Seeded synchronously in `add_ticker` (immediate) | Appears on next poll, up to one interval later |
| Timestamps | `time.time()` | Provider ms (÷1000). Normalise ms vs ns in one helper |
| Unknown ticker | Random start price in $50–300 | Absent from response, never cached |
| Failures | n/a | Logged, last price stays cached, retry next tick |

**Known gaps to close when wiring the rest of the app:**

1. **Add-ticker latency on Massive.** PLAN.md §13 wants `GET /api/watchlist` to always return a price. `MassiveDataSource.add_ticker` should trigger an immediate `_poll_once()` (or a single-ticker snapshot) so the price is in the cache before the route returns. Until then the API layer may return `price: null` for a just-added ticker.
2. **Daily change baseline.** Add an optional `previous_close` (Massive `prev_day.close`; simulator = seed price) so the watchlist can show day-change % separate from tick-to-tick change. Suggested: `PriceCache.update(..., previous_close=None)` and a `PriceUpdate.day_change_percent` property.
3. **Free-tier fallback.** Snapshots need a paid plan. On 403, `MassiveDataSource` should log once and fall back to end-of-day prices via `get_grouped_daily_aggs(<last trading day>)`, one call per poll cycle. Prices then do not move intraday; that is expected and should be surfaced in the UI or log.

## 7. End-of-day prices

Real-time and EOD share one shape (`PriceUpdate` in the cache), and no separate EOD API is exposed to the rest of the app:

- Massive: after the close, `last_trade.price` in the snapshot is the closing/last price, and `prev_day.close` is the prior EOD close.
- Free tier: the grouped-daily fallback in §6.3 populates the cache with the latest EOD close.
- Simulator: has no concept of a session; the price simply continues.

If a true history API is needed later (charts), add a separate `HistoryProvider` (`get_daily_closes(ticker, start, end)`) backed by `list_aggs`. Keep it out of `MarketDataSource`.

## 8. Testing

- Unit-test each source against the ABC (`tests/market/`; 73 tests currently).
- Mock `RESTClient` for Massive; never hit the network in CI.
- E2E uses the simulator (no key set).
- Factory test: env var unset / empty / whitespace → Simulator; set → Massive.

## 9. Configuration

| Env var | Effect |
|---|---|
| `MASSIVE_API_KEY` | Non-empty → Massive; empty/absent → simulator |
| (constructor) `poll_interval` | Massive poll seconds (default 15.0) |
| (constructor) `update_interval`, `event_probability` | Simulator tick (0.5 s) and shock chance (0.001) |
