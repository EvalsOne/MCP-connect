#!/bin/bash
# Create /home/user/startup.sh script that initializes all services
set -e

cat > /home/user/startup.sh <<'EOF'
#!/bin/bash

# E2B Custom Template Startup Script
# Starts nginx, virtual display services (Xvfb + VNC + noVNC), Chrome, and MCP-connect

set -euo pipefail

LOG_DIR=/home/user

log() {
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%SZ')" "$*"
}

log "Starting E2B MCP Sandbox..."

AUTH_TOKEN=${AUTH_TOKEN:-demo#e2b}
PORT=${PORT:-3000}
HOST=${HOST:-127.0.0.1}
DISPLAY=${DISPLAY:-:99}
XVFB_DISPLAY=${XVFB_DISPLAY:-$DISPLAY}
XVFB_RESOLUTION=${XVFB_RESOLUTION:-1920x1080x24}
VNC_PORT=${VNC_PORT:-5900}
NOVNC_PORT=${NOVNC_PORT:-6080}
NOVNC_WEBROOT=${NOVNC_WEBROOT:-/usr/share/novnc}
VNC_PASSWORD=${VNC_PASSWORD:-}

RESOLUTION_META=${XVFB_RESOLUTION}
XVFB_WIDTH=${XVFB_WIDTH:-${RESOLUTION_META%%x*}}
HEIGHT_WITH_DEPTH=${RESOLUTION_META#*x}
XVFB_HEIGHT=${XVFB_HEIGHT:-${HEIGHT_WITH_DEPTH%%x*}}

export AUTH_TOKEN PORT HOST DISPLAY XVFB_DISPLAY XVFB_RESOLUTION XVFB_WIDTH XVFB_HEIGHT VNC_PORT NOVNC_PORT NOVNC_WEBROOT

log "Using AUTH_TOKEN=${AUTH_TOKEN} PORT=${PORT} HOST=${HOST} DISPLAY=${XVFB_DISPLAY}"

# Prepare MCP-connect configuration
cd /home/user/mcp-connect || { log "mcp-connect directory missing"; exit 1; }
cat > .env <<ENVFILE
# Quote values to avoid dotenv comment parsing (e.g. # in tokens)
AUTH_TOKEN="${AUTH_TOKEN}"
PORT="${PORT}"
HOST="${HOST}"
LOG_LEVEL="info"
ENVFILE

log "Node.js / npm versions:"
node -v || log "node not found"
npm -v || log "npm not found"

FORCE_INSTALL=${NPM_CI_ALWAYS:-0}
if [ -f package.json ]; then
    if [ "$FORCE_INSTALL" = "1" ]; then
        log "FORCE_INSTALL enabled: running npm ci"
        npm ci --no-audit || npm install --no-audit || { log "npm install failed"; exit 1; }
    elif [ ! -d node_modules ]; then
        log "node_modules missing: installing deps"
        npm ci --no-audit || npm install --no-audit || { log "npm install failed"; exit 1; }
    elif [ package-lock.json -nt node_modules ] || [ package.json -nt node_modules ]; then
        log "package files newer than node_modules: re-installing deps"
        npm ci --no-audit || npm install --no-audit || { log "npm install failed"; exit 1; }
    else
        log "node_modules present and up-to-date; skipping npm install"
    fi
else
    log "package.json missing; cannot install dependencies"
    exit 1
fi

# Virtual display components ---------------------------------------------------
DISPLAY_NUM=${XVFB_DISPLAY#:}
DISPLAY_NUM=${DISPLAY_NUM%%.*}
DISPLAY_SOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"

log "Cleaning up stale Xvfb state for display ${XVFB_DISPLAY}"
pkill -f -- "Xvfb ${XVFB_DISPLAY}" >/dev/null 2>&1 || true
rm -f "/tmp/.X${DISPLAY_NUM}-lock" "${DISPLAY_SOCKET}" >/dev/null 2>&1 || true
mkdir -p /tmp/.X11-unix
chmod 1777 /tmp/.X11-unix || true

log "Ensuring Xvfb is running on ${XVFB_DISPLAY}"
nohup Xvfb "${XVFB_DISPLAY}" -screen 0 "${XVFB_RESOLUTION}" -nolisten tcp > "${LOG_DIR}/xvfb.log" 2>&1 &
XVFB_PID=$!
echo ${XVFB_PID} > "${LOG_DIR}/xvfb.pid"

for attempt in $(seq 1 20); do
    if [ -S "${DISPLAY_SOCKET}" ]; then
        log "Xvfb socket ${DISPLAY_SOCKET} is ready"
        break
    fi
    log "Waiting for Xvfb socket ${DISPLAY_SOCKET} (attempt ${attempt})"
    sleep 0.5
done

if [ ! -S "${DISPLAY_SOCKET}" ]; then
    log "WARNING: Xvfb socket ${DISPLAY_SOCKET} did not appear"
fi

export DISPLAY="${XVFB_DISPLAY}"

log "Preparing fluxbox configuration"
FLUXBOX_DIR=/home/user/.fluxbox
if [ ! -d "${FLUXBOX_DIR}" ]; then
    mkdir -p "${FLUXBOX_DIR}"
    OWNED=0
    for candidate in /etc/X11/fluxbox /usr/share/fluxbox; do
        if [ -d "$candidate" ]; then
            cp -r "$candidate"/* "${FLUXBOX_DIR}/" 2>/dev/null || true
            OWNED=1
            break
        fi
    done
    if [ "$OWNED" -eq 0 ]; then
        cat > "${FLUXBOX_DIR}/init" <<'FLUXINIT'
session.menuFile:     ~/.fluxbox/menu
session.keyFile:      ~/.fluxbox/keys
session.slitlistFile: ~/.fluxbox/slitlist
session.appsFile:     ~/.fluxbox/apps
session.screen0.rootCommand:  true
FLUXINIT
    fi
    touch "${FLUXBOX_DIR}/menu" "${FLUXBOX_DIR}/keys" "${FLUXBOX_DIR}/apps" "${FLUXBOX_DIR}/slitlist"
fi

log "Ensuring fluxbox window manager is running"
pkill -x fluxbox >/dev/null 2>&1 || true
nohup fluxbox > "${LOG_DIR}/fluxbox.log" 2>&1 &
FLUXBOX_PID=$!
echo ${FLUXBOX_PID} > "${LOG_DIR}/fluxbox.pid"

if [ -n "${VNC_PASSWORD}" ]; then
    log "Configuring VNC password file"
    mkdir -p /home/user/.vnc
    x11vnc -storepasswd "${VNC_PASSWORD}" /home/user/.vnc/passwd >/dev/null 2>&1
    chmod 600 /home/user/.vnc/passwd
    X11VNC_AUTH_OPTS=("-rfbauth" "/home/user/.vnc/passwd")
else
    log "VNC password not set; starting x11vnc without authentication"
    X11VNC_AUTH_OPTS=("-nopw")
fi

log "Ensuring x11vnc is running on port ${VNC_PORT}"
pkill -f -- "x11vnc.*:${VNC_PORT}" >/dev/null 2>&1 || true
# Guard against external envs that inject unsupported libvncserver flags
unset X11VNC_OPTS X11VNC_OPTIONS X11VNC_ARGS X11VNC_QUALITY X11VNC_COMPRESSION TIGHT_QUALITY TIGHT_COMPRESSLEVEL VNC_QUALITY VNC_COMPRESSLEVEL || true
nohup x11vnc -display "${XVFB_DISPLAY}" \
    -rfbport "${VNC_PORT}" \
    -localhost \
    -forever \
    -shared \
    -ncache 0 \
    "${X11VNC_AUTH_OPTS[@]}" \
    -o "${LOG_DIR}/x11vnc.log" \
    > /dev/null 2>&1 &
X11VNC_PID=$!
echo ${X11VNC_PID} > "${LOG_DIR}/x11vnc.pid"

log "Ensuring noVNC web server is running on port ${NOVNC_PORT}"
pkill -f -- "websockify.*${NOVNC_PORT}" >/dev/null 2>&1 || true
nohup websockify --web="${NOVNC_WEBROOT}" \
    "${NOVNC_PORT}" \
    127.0.0.1:"${VNC_PORT}" \
    > "${LOG_DIR}/novnc.log" 2>&1 &
NOVNC_PID=$!
echo ${NOVNC_PID} > "${LOG_DIR}/novnc.pid"

# Minimal readiness check + auto-retry x11vnc with safe flags
for i in $(seq 1 10); do
  if nc -z 127.0.0.1 "${VNC_PORT}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! nc -z 127.0.0.1 "${VNC_PORT}" >/dev/null 2>&1; then
  echo "x11vnc not listening on ${VNC_PORT}, retrying with minimal flags" >> "${LOG_DIR}/x11vnc.log"
  pkill -f -- "x11vnc.*:${VNC_PORT}" >/dev/null 2>&1 || true
  sleep 0.5
  nohup x11vnc -display "${XVFB_DISPLAY}" \
      -rfbport "${VNC_PORT}" \
      -localhost \
      -forever \
      -shared \
      "${X11VNC_AUTH_OPTS[@]}" \
      -o "${LOG_DIR}/x11vnc.log" \
      > /dev/null 2>&1 &
  X11VNC_PID=$!
  echo ${X11VNC_PID} > "${LOG_DIR}/x11vnc.pid"
fi

# Chrome (non-headless) --------------------------------------------------------
log "Ensuring Chrome (DevTools) is running on display ${XVFB_DISPLAY}"
if pgrep -f -- '--remote-debugging-port=9222' >/dev/null 2>&1; then
    log "Chrome DevTools already running"
    CHROME_PID=$(pgrep -f -- '--remote-debugging-port=9222' | head -n 1)
else
    mkdir -p /home/user/.chrome-data
    export XDG_RUNTIME_DIR=/home/user/.xdg
    mkdir -p "${XDG_RUNTIME_DIR}"
    nohup google-chrome \
        --no-sandbox \
        --disable-dev-shm-usage \
        --remote-debugging-port=9222 \
        --remote-debugging-address=0.0.0.0 \
        --disable-gpu \
        --disable-features=VizDisplayCompositor \
        --disable-software-rasterizer \
        --no-first-run \
        --window-size=${XVFB_WIDTH},${XVFB_HEIGHT} \
        --user-data-dir=/home/user/.chrome-data \
        about:blank \
        > "${LOG_DIR}/chrome.log" 2>&1 &
    CHROME_PID=$!
    echo ${CHROME_PID} > "${LOG_DIR}/chrome.pid"
fi

# nginx proxy ------------------------------------------------------------------
log "Ensuring nginx reverse proxy is running"
if pgrep -x nginx >/dev/null 2>&1; then
    log "nginx already running"
    NGINX_PID=$(pgrep -x nginx | head -n 1)
else
    sudo nginx -g 'daemon off;' &
    NGINX_PID=$!
fi

sleep 2

# MCP-connect ------------------------------------------------------------------
log "Ensuring MCP-connect server is running on port ${PORT}"
if curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/health" | grep -q '^200$'; then
    log "mcp-connect already healthy on port ${PORT}"
    MCP_PID=""
else
    npm run start > "${LOG_DIR}/mcp.log" 2>&1 &
    MCP_PID=$!
    echo ${MCP_PID} > "${LOG_DIR}/mcp.pid"
fi

log "Waiting for mcp-connect to become healthy..."
code=""
for _ in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/health" || true)
    if [ "$code" = "200" ]; then
        log "mcp-connect is healthy (HTTP 200)"
        break
    fi
    sleep 2
done

if [ "$code" != "200" ]; then
    log "mcp-connect failed to become healthy (last code: $code)"
    log "--- tail chrome.log ---"
    tail -n 50 "${LOG_DIR}/chrome.log" 2>/dev/null || true
    log "--- tail nginx error.log ---"
    sudo tail -n 50 /var/log/nginx/error.log 2>/dev/null || true
    exit 1
fi

cleanup() {
    log "Shutting down services..."
    for pid_var in MCP_PID NGINX_PID CHROME_PID NOVNC_PID X11VNC_PID FLUXBOX_PID XVFB_PID; do
        pid_value=${!pid_var:-}
        if [ -n "$pid_value" ] && kill -0 "$pid_value" >/dev/null 2>&1; then
            kill "$pid_value" 2>/dev/null || true
        fi
    done
}

trap cleanup SIGTERM SIGINT

if [ -n "${MCP_PID:-}" ]; then
    wait "${MCP_PID}"
else
    while true; do
        sleep 3600
    done
fi
EOF

chmod +x /home/user/startup.sh
chown user:user /home/user/startup.sh
