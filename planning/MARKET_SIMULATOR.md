# Market Simulator

Approach and code structure for simulating stock prices when `MASSIVE_API_KEY` is not set. Code: `backend/app/market/simulator.py` and `seed_prices.py`.

## 1. Goals

- Realistic-looking, continuously moving prices at ~500 ms cadence with zero external dependencies.
- Correlated moves (tech moves together) and occasional dramatic shocks, to make the UI visually interesting.
- Prices positive, smooth and never explode over a demo session.
- Same `MarketDataSource` interface as the Massive client.

## 2. Model: Geometric Brownian Motion

Per tick, for each ticker:

```
S(t+dt) = S(t) * exp( (mu - sigma²/2) * dt + sigma * sqrt(dt) * Z )
```

| Symbol | Meaning |
|---|---|
| `S` | price |
| `mu` | annualised drift (expected return) |
| `sigma` | annualised volatility |
| `dt` | tick length as a fraction of a trading year |
| `Z` | standard normal (correlated across tickers) |

The log form guarantees positive prices. `dt = 0.5 / (252 * 6.5 * 3600) ≈ 8.48e-8`, so one tick moves a price by roughly `sigma * sqrt(dt)` ≈ 0.007% for σ=0.25. That is sub-cent for a $190 stock, and moves accumulate naturally: over a simulated trading day the standard deviation is ~σ/√252 (≈1.6% for σ=0.25).

## 3. Correlation

Independent noise per ticker looks fake. Instead:

1. Build an n×n correlation matrix `C` from sector groups (`seed_prices.py`):
   - tech ↔ tech: **0.6** (AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX)
   - finance ↔ finance: **0.5** (JPM, V)
   - anything involving TSLA: **0.3** (does its own thing)
   - cross-sector and unknown tickers: **0.3**
2. Cholesky factor `L = cholesky(C)`.
3. Each tick: draw `z ~ N(0, I_n)`, use `Z = L @ z`.

`L` is rebuilt (O(n²), n < 50) whenever a ticker is added or removed. With ≤1 ticker there is no matrix and `Z = z`. Correlations ≤ 0.6 with a 0.3 floor keep `C` positive-definite, so Cholesky never fails.

## 4. Random shock events

Each tick each ticker has probability `event_probability` (default **0.001**) of a jump: multiply by `1 ± U(0.02, 0.05)` with a random sign. With 10 tickers at 2 ticks/s that is about one event every 50 s across the watchlist, enough for "drama" without chaos. Set `event_probability=0` in tests for determinism.

## 5. Seed data and parameters

`seed_prices.py`:

| Ticker | Seed | σ | μ |
|---|---|---|---|
| AAPL | 190 | 0.22 | 0.05 |
| GOOGL | 175 | 0.25 | 0.05 |
| MSFT | 420 | 0.20 | 0.05 |
| AMZN | 185 | 0.28 | 0.05 |
| TSLA | 250 | 0.50 | 0.03 |
| NVDA | 800 | 0.40 | 0.08 |
| META | 500 | 0.30 | 0.05 |
| JPM | 195 | 0.18 | 0.04 |
| V | 280 | 0.17 | 0.04 |
| NFLX | 600 | 0.35 | 0.05 |

Tickers not listed (added dynamically) start at `random.uniform(50, 300)` with `DEFAULT_PARAMS = {sigma: 0.25, mu: 0.05}`.

## 6. Code structure

```
GBMSimulator            pure math, synchronous, no I/O, easy to unit test
  __init__(tickers, dt=DEFAULT_DT, event_probability=0.001)
  step() -> {ticker: price}          # hot path; advances all tickers one tick, rounds to 2dp
  add_ticker / remove_ticker         # rebuild Cholesky
  get_price / get_tickers
  _add_ticker_internal               # batch init without rebuilding
  _rebuild_cholesky
  _pairwise_correlation (static)

SimulatorDataSource(MarketDataSource)   asyncio wrapper
  start(tickers)   create GBMSimulator, seed cache immediately, spawn _run_loop task
  _run_loop        while True: step() -> cache.update(...) ; sleep(update_interval)
  add_ticker       sim.add_ticker + immediate cache seed (price available at once)
  remove_ticker    sim.remove_ticker + cache.remove
  stop             cancel task, await it, swallow CancelledError
```

Separating `GBMSimulator` (math) from `SimulatorDataSource` (lifecycle) lets tests run thousands of `step()` calls synchronously.

Loop resilience: the step is wrapped in `try/except` with `logger.exception`, so one bad tick never kills the background task.

## 7. Behaviour worth knowing

- **Seeding on start/add:** the cache is populated before the first tick, so SSE and `GET /api/watchlist` always have a price, including for a just-added ticker (this satisfies PLAN.md §13).
- **Rounding:** simulator prices are rounded to 2 dp per tick. Internal state stays unrounded, so tiny drifts are not lost.
- **Ticker case:** normalise at the API boundary; `GBMSimulator` treats symbols as exact keys.
- **Drift is negligible per tick** (mu·dt ≈ 1e-9); the visible movement comes from the diffusion and shocks.
- **Session-less:** no market hours, gaps or overnight behaviour. Prices restart from seeds each process start (they are not persisted).

## 8. Possible extensions (not built)

- Persist last prices in SQLite so restarts continue rather than reset.
- Optional volatility clustering (GARCH-style σ) or mean reversion for more "market-like" charts.
- A `previous_close` per ticker (= seed price) for day-change % (see MARKET_INTERFACE.md §6).
- Seeded RNG (`np.random.default_rng(seed)`) exposed as a constructor arg for fully reproducible E2E runs.

## 9. Tests (`tests/market/test_simulator*.py`)

Covered: positive prices; correct tick count; add/remove rebuilds Cholesky; correlation values; shock events firing when probability is 1.0; default params for unknown tickers; source lifecycle (start seeds cache, add seeds immediately, remove evicts, stop cancels task).

Quick manual check: `cd backend && uv run market_data_demo.py` shows a live Rich terminal table.
