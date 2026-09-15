# FinAlly — AI Trading Workstation

A Bloomberg-terminal-style trading simulator with an AI copilot. Streams live (simulated or real) market data, tracks a virtual $10,000 portfolio, and lets an LLM chat assistant analyze positions and execute trades on the user's behalf.

Full specification: [PLAN.md](./PLAN.md)

## Stack

- **Frontend**: Next.js (TypeScript, static export)
- **Backend**: FastAPI (Python, `uv`), serving both `/api/*` and the static frontend on one port
- **Database**: SQLite (`db/finally.db`), lazily initialized and seeded
- **Real-time data**: Server-Sent Events (`/api/stream/prices`)
- **AI**: LiteLLM → OpenRouter (Cerebras inference), structured JSON outputs
- **Deployment**: single Docker container, port 8000

## Quick Start

```bash
cp .env.example .env      # add OPENROUTER_API_KEY
./scripts/start_mac.sh    # or scripts/start_windows.ps1
```

Opens `http://localhost:8000` — no login required.

## Key Design Choices

- **Market orders only** — no order book, no partial fills, simple portfolio math
- **Simulator by default** — GBM-based price simulation; set `MASSIVE_API_KEY` for real data via Massive/Polygon
- **Single-user** — hardcoded `user_id="default"`, SQLite instead of a database server
- **Auto-executed AI trades** — no confirmation dialogs; simulated money, demo-friendly, showcases agentic AI

## Status

Market data component (simulator + Massive client) is complete — see [MARKET_DATA_SUMMARY.md](./MARKET_DATA_SUMMARY.md). Portfolio, watchlist, chat/LLM integration, frontend, and Docker packaging are still to be built.
