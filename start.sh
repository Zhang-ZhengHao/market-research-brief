#!/usr/bin/env bash
set -euo pipefail

: "${PORT:?PORT is required}"

if [ -d "$(pwd)/pydeps" ]; then
  export PYTHONPATH="$(pwd)/pydeps:${PYTHONPATH:-}"
fi

if [ -z "${INSIGHT_MONITOR_BUILD_SHA:-}" ]; then
  INSIGHT_MONITOR_BUILD_SHA="$(git rev-parse --short=12 HEAD 2>/dev/null || printf 'dev')"
  export INSIGHT_MONITOR_BUILD_SHA
fi

exec python3 -m streamlit run app.py \
  --global.developmentMode=false \
  --server.address=0.0.0.0 \
  --server.port="${PORT}" \
  --server.headless=true \
  --server.fileWatcherType=none \
  --browser.gatherUsageStats=false
