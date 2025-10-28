#!/bin/bash
# Wrapper to ensure chrome-devtools-mcp connects to the running Chrome instance
set -euo pipefail

REMOTE_URL=${CHROME_REMOTE_DEBUGGING_URL:-http://127.0.0.1:9222}
ARGS=("$@")

resolve_ws_url() {
  local url="$1"
  if [[ "$url" =~ ^https?:// ]]; then
    local json
    if ! json=$(curl -fsS "$url/json/version"); then
      echo "Failed to query Chrome debugger version info from $url" >&2
      return 1
    fi
    local ws
    ws=$(python3 - <<'PYJSON'
import json, sys
try:
    data = json.load(sys.stdin)
    ws = data.get("webSocketDebuggerUrl")
    if not ws:
        raise SystemExit(1)
    print(ws)
except Exception:
    raise SystemExit(1)
PYJSON
    <<<"$json" 2>/dev/null) || {
      echo "Failed to parse webSocketDebuggerUrl from Chrome response" >&2
      return 1
    }
    echo "$ws"
  else
    echo "$url"
  fi
}

WS_URL=$(resolve_ws_url "$REMOTE_URL")
exec chrome-devtools-mcp --browser "$WS_URL" "${ARGS[@]}"
