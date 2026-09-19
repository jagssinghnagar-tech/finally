# Stage 1: build the Next.js static export
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/app/db/finally.db PYTHONUNBUFFERED=1
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
COPY backend/app ./app
RUN uv sync --frozen --no-dev
COPY --from=frontend /build/out ./static
RUN mkdir -p /app/db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
