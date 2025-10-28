#!/bin/bash
# Wrapper to ensure chrome-devtools-mcp connects to the running Chrome instance
set -euo pipefail

REMOTE_URL=${CHROME_REMOTE_DEBUGGING_URL:-http://127.0.0.1:9222}
ARGS=("$@")

# Pass HTTP debugging endpoint to MCP as per README (--browserUrl)
exec chrome-devtools-mcp --browserUrl "$REMOTE_URL" "${ARGS[@]}"
