#!/usr/bin/env bash
# Start FinAlly (idempotent). Usage: start_mac.sh [--build] [--no-open]
set -euo pipefail
cd "$(dirname "$0")/.."
BUILD=0; OPEN=1
for a in "$@"; do case "$a" in --build) BUILD=1;; --no-open) OPEN=0;; esac; done
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example"; }
mkdir -p db
if [ "$BUILD" = 1 ] || ! docker image inspect finally >/dev/null 2>&1; then
  docker build -t finally .
fi
docker rm -f finally >/dev/null 2>&1 || true
docker run -d --name finally -p 8000:8000 -v "$(pwd)/db:/app/db" --env-file .env finally >/dev/null
URL=http://localhost:8000
echo "FinAlly running at $URL"
if [ "$OPEN" = 1 ]; then
  (open "$URL" || xdg-open "$URL") >/dev/null 2>&1 || true
fi
