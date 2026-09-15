# FinAlly — AI Trading Workstation

A visually stunning AI-powered trading workstation that streams live market data, simulates portfolio trading, and integrates an LLM chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as a capstone project for an agentic AI coding course.

## Features

- **Live price streaming** via SSE with green/red flash animations
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills
- **Portfolio visualizations** — heatmap (treemap), P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests and auto-executes trades
- **Watchlist management** — track tickers manually or via AI
- **Dark terminal aesthetic** — Bloomberg-inspired, data-dense layout

## Architecture

Single Docker container serving everything on port 8000:

- **Frontend**: Next.js (static export) with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python/uv) with SSE streaming
- **Database**: SQLite with lazy initialization
- **AI**: LiteLLM → OpenRouter (Cerebras inference) with structured outputs
- **Market data**: Built-in GBM simulator (default) or Massive API (optional)

## Status

🚧 In development. The **market data subsystem** (simulator, Massive API client, SSE streaming, price cache) is complete — see `backend/` and [`planning/MARKET_DATA_SUMMARY.md`](planning/MARKET_DATA_SUMMARY.md). The frontend, portfolio/trading API, AI chat, database layer, and Docker packaging are not yet built. Full spec: [`planning/PLAN.md`](planning/PLAN.md).

## Backend Dev Setup

```bash
cd backend
uv sync --extra dev
uv run market_data_demo.py   # live terminal dashboard with simulated prices
uv run --extra dev pytest -v # run tests
```

See [`backend/README.md`](backend/README.md) for details.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (for AI chat, not yet implemented) | OpenRouter API key |
| `MASSIVE_API_KEY` | No | Massive (Polygon.io) key for real market data; omit to use simulator |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

## Project Structure

```
finally/
├── backend/     # FastAPI uv project (market data done; portfolio/AI/db pending)
├── planning/    # Project documentation and agent contracts
└── db/          # SQLite volume mount (runtime, not yet used)
```

Planned but not yet present: `frontend/` (Next.js), `test/` (Playwright E2E), `scripts/` (start/stop helpers), `Dockerfile`.

## License

See [LICENSE](LICENSE).
