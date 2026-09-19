# Massive API Reference (formerly Polygon.io)

How FinAlly uses the Massive REST API to get real-time and end-of-day prices for multiple tickers.

## 1. Overview

| Item | Value |
|---|---|
| Base URL | `https://api.massive.com` (legacy `https://api.polygon.io` still works) |
| Python package | `massive` (`uv add massive`), Python 3.9+ |
| Auth | API key; `RESTClient(api_key=...)` or `MASSIVE_API_KEY` env var. Sent as `Authorization: Bearer <key>` (client handles it); raw REST may also use `?apiKey=` |
| Timestamps | Unix **milliseconds** (`t`, `lastTrade.t`); some fields are nanoseconds — check per endpoint |
| Response style | JSON. Raw REST uses short keys (`o,h,l,c,v,vw,t,T`); the Python client maps them to snake_case model attributes |

### Plans, data recency and rate limits

| Plan | Recency | Rate limit | Snapshot endpoints |
|---|---|---|---|
| Basic (free) | End of day | 5 req/min | **Not included** (snapshots are Starter+) |
| Starter / Developer | 15-minute delayed | Unlimited (stay < ~100 req/s) | Yes |
| Advanced / Business | Real-time | Unlimited | Yes |

Consequences for FinAlly:

- **Real-time multi-ticker prices** → Full Market Snapshot (one call for all tickers). Needs a paid plan.
- **Free-tier fallback / end-of-day** → Grouped Daily Bars or Previous Close (allowed on all plans, EOD data).
- Poll interval: paid 2–15 s; free 15 s+ (5 calls/min budget, so never more than one call per 12 s).
- Verify your plan against the current docs; entitlements change. A 403 (`NOT_AUTHORIZED`) means the plan lacks the endpoint.

## 2. Client setup

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient()                       # reads MASSIVE_API_KEY
client = RESTClient(api_key="your_key")     # or explicit
```

The client is **synchronous**. From asyncio, wrap calls with `asyncio.to_thread(...)` (as `massive_client.py` does).

## 3. Endpoints

### 3.1 Full Market Snapshot — real-time, many tickers, one call (primary)

`GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT`

- `tickers` — optional, comma-separated, case-insensitive. Omit to get the whole market (large payload; avoid).
- `include_otc` — optional, default `false`.
- Snapshot data is cleared daily ~3:30 AM ET and repopulates from ~4:00 AM ET as exchanges report.

```python
snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)
for s in snapshots:
    print(s.ticker, s.last_trade.price, s.todays_change_percent)
    print("  day  :", s.day.open, s.day.high, s.day.low, s.day.close, s.day.volume)
    print("  prev :", s.prev_day.close)
```

Response (per ticker, raw JSON):

```json
{
  "ticker": "AAPL",
  "todaysChange": -4.54,
  "todaysChangePerc": -3.50,
  "updated": 1675190399000000000,
  "day":     {"o":129.61,"h":130.15,"l":125.07,"c":125.07,"v":111237700,"vw":127.35},
  "min":     {"o":125.1,"h":125.2,"l":125.0,"c":125.07,"v":52000,"vw":125.1,"t":1675190340000},
  "prevDay": {"o":129.6,"h":131.0,"l":128.9,"c":129.61,"v":98000000,"vw":129.9},
  "lastTrade": {"p":125.07,"s":100,"x":4,"t":1675190399000000000},
  "lastQuote": {"P":125.08,"S":10,"p":125.06,"s":5,"t":1675190399500000000}
}
```

Fields FinAlly uses: `last_trade.price` (current price), `last_trade.timestamp` (time), `prev_day.close` (day-change baseline), `todays_change_percent`.

Caveats:
- `day` resets at market open; pre-market values may be zero/previous session. Fall back to `prev_day.close` or `min.close` if `last_trade` is missing.
- `last_trade.timestamp` units: the current `massive_client.py` divides by 1000 (ms). Snapshot `lastTrade.t` may be **nanoseconds** in raw JSON — confirm against a live response and normalise in one place (see MARKET_INTERFACE.md §6).

### 3.2 Single-ticker Snapshot

`GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}`

```python
s = client.get_snapshot_ticker(SnapshotMarketType.STOCKS, "AAPL")
print(s.last_trade.price, s.last_quote.bid_price, s.last_quote.ask_price)
```

Use for detail views; for many tickers always prefer 3.1 (one call vs N).

### 3.3 Grouped Daily Bars — end of day, whole market, one call

`GET /v2/aggs/grouped/locale/us/market/stocks/{date}` — `date` = `YYYY-MM-DD`; `adjusted` (default true), `include_otc` (default false). Available on **all** plans (EOD on Basic).

```python
bars = client.get_grouped_daily_aggs("2026-09-18", adjusted=True)
wanted = {"AAPL", "GOOGL", "MSFT"}
eod = {b.ticker: b.close for b in bars if b.ticker in wanted}
```

Raw result item: `{"T":"AAPL","o":..,"h":..,"l":..,"c":..,"v":..,"vw":..,"t":1758225600000,"n":..}`. Returns nothing for weekends/holidays — walk back to the previous trading day.

### 3.4 Previous Day Bar (single ticker)

`GET /v2/aggs/ticker/{ticker}/prev`

```python
for a in client.get_previous_close_agg("AAPL"):
    print(a.close, a.open, a.high, a.low, a.volume)
```

One call per ticker → on the free tier (5/min) this only suits a handful of tickers. Prefer 3.3.

### 3.5 Custom Bars (aggregates) — history / charts

`GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}`

```python
for a in client.list_aggs("AAPL", 1, "day", "2026-08-01", "2026-09-18", limit=50000):
    print(a.timestamp, a.open, a.high, a.low, a.close, a.volume)
```

Not needed for live polling; useful for seeding sparklines/history later.

### 3.6 Last Trade / Last Quote (single ticker)

```python
t = client.get_last_trade("AAPL");  print(t.price, t.size)
q = client.get_last_quote("AAPL");  print(q.bid, q.ask)
```

Real-time entitlement required for un-delayed data; one call per ticker, so not used for polling.

## 4. Polling pattern used by FinAlly

```python
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

async def poll(api_key, get_tickers, cache, interval=15.0):
    client = RESTClient(api_key=api_key)
    while True:
        tickers = get_tickers()
        if tickers:
            try:
                snaps = await asyncio.to_thread(
                    client.get_snapshot_all, SnapshotMarketType.STOCKS, tickers=tickers)
                for s in snaps:
                    cache.update(s.ticker, s.last_trade.price)   # ts normalised in adapter
            except Exception as e:                                # 401/403/429/network
                print("poll failed:", e)                          # retry next tick
        await asyncio.sleep(interval)
```

## 5. Errors

| Status | Meaning | Handling |
|---|---|---|
| 401 | Bad/missing key | Log clearly; keep serving last cached prices; do not crash |
| 403 | Plan lacks endpoint (e.g. snapshot on free tier) | Log once; fall back to EOD grouped bars (see MARKET_INTERFACE.md §7) |
| 404 | Unknown ticker | Skip ticker; never abort the whole batch |
| 429 | Rate limit | Back off; lengthen interval |
| 5xx | Server | Client retries (3 by default); otherwise next poll |

Unknown tickers are simply absent from a multi-ticker snapshot — compare requested vs returned.

## 6. Sources

- Full Market Snapshot: https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot
- Grouped Daily Bars: https://massive.com/docs/rest/stocks/aggregates/daily-market-summary
- Python client: https://github.com/massive-com/client-python
