#!/usr/bin/env bash
# Stop and remove the FinAlly container; db/ data is kept.
docker rm -f finally >/dev/null 2>&1 || true
echo "FinAlly stopped (data in ./db preserved)"
