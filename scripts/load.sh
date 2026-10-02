#!/usr/bin/env bash
# Generate a little traffic so Grafana has latency and error samples.
set -euo pipefail
base="${1:-http://127.0.0.1:18000}"
count="${COUNT:-40}"
i=0
while [ "$i" -lt "$count" ]; do
  curl -fsS "$base/health" >/dev/null || true
  curl -fsS "$base/version" >/dev/null || true
  curl -s -o /dev/null "$base/error" || true
  i=$((i + 1))
done
echo "sent $count rounds to $base"
