#!/bin/bash

# E2B Custom Template Startup Script
# Starts nginx, virtual display services (Xvfb + VNC + noVNC), Chrome, and MCP-connect

set -euo pipefail

LOG_DIR=/home/user
STARTUP_VERSION="v2025-10-15-01"
DESKTOP_DIR=/home/user/Desktop
CONFIG_ROOT=/home/user/.config
FLUXBOX_DIR=/home/user/.fluxbox
PCMANFM_CONFIG_DIR=${CONFIG_ROOT}/pcmanfm/default
TINT2_CONFIG_DIR=${CONFIG_ROOT}/tint2
DESKTOP_TEMPLATE_DIR=/opt/mcp-desktop
CHROME_LAUNCHER=/home/user/bin/chrome-devtools.sh

log() {
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

log "Starting E2B MCP Sandbox..."
log "Startup script version: ${STARTUP_VERSION}"

# Read token from namespaced env first, then generic; no hardcoded default
AUTH_TOKEN=${E2B_MCP_AUTH_TOKEN:-${AUTH_TOKEN:-}}
PORT=${PORT:-3000}
HOST=${HOST:-127.0.0.1}
HEADLESS=${HEADLESS:-0}
DISPLAY=${DISPLAY:-:99}
XVFB_DISPLAY=${XVFB_DISPLAY:-$DISPLAY}
XVFB_RESOLUTION=${XVFB_RESOLUTION:-1920x1080x24}
VNC_PORT=${VNC_PORT:-5900}
NOVNC_PORT=${NOVNC_PORT:-6080}
NOVNC_WEBROOT=${NOVNC_WEBROOT:-/usr/share/novnc}
VNC_PASSWORD=${VNC_PASSWORD:-}
TINT2_ENABLED=${TINT2_ENABLED:-0}
FLUXBOX_TOOLBAR=${FLUXBOX_TOOLBAR:-true}

RESOLUTION_META=${XVFB_RESOLUTION}
XVFB_WIDTH=${XVFB_WIDTH:-${RESOLUTION_META%%x*}}
HEIGHT_WITH_DEPTH=${RESOLUTION_META#*x}
XVFB_HEIGHT=${XVFB_HEIGHT:-${HEIGHT_WITH_DEPTH%%x*}}

export AUTH_TOKEN PORT HOST DISPLAY XVFB_DISPLAY XVFB_RESOLUTION XVFB_WIDTH XVFB_HEIGHT VNC_PORT NOVNC_PORT NOVNC_WEBROOT

# Avoid printing the token value; only indicate whether it is set
if [ -n "${AUTH_TOKEN}" ]; then TOKEN_STATUS="set"; else TOKEN_STATUS="unset"; fi
log "Using AUTH_TOKEN=${TOKEN_STATUS} PORT=${PORT} HOST=${HOST} DISPLAY=${XVFB_DISPLAY} HEADLESS=${HEADLESS}"

prepare_mcp_env() {
    # Prepare MCP-connect configuration and ensure deps
    cd /home/user/mcp-connect || { log "mcp-connect directory missing"; exit 1; }
    cat <<ENVFILE > .env
# Quote values so dotenv won't treat # as comment
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
}

# If HEADLESS is enabled, run a lightweight startup and skip GUI entirely
if [ "${HEADLESS}" = "1" ] || [ "${HEADLESS}" = "true" ]; then
    log "HEADLESS mode: starting only nginx + mcp-connect"
    prepare_mcp_env

    # nginx proxy
    log "Ensuring nginx reverse proxy is running (headless)"
    if pgrep -x nginx >/dev/null 2>&1; then
        log "nginx already running"
        NGINX_PID=$(pgrep -x nginx | head -n 1)
    else
        sudo nginx -g 'daemon off;' &
        NGINX_PID=$!
    fi

    # MCP-connect
    log "Ensuring MCP-connect server is running on port ${PORT} (headless)"
    if curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/health" | grep -q '^200$'; then
        log "mcp-connect already healthy on port ${PORT}"
        MCP_PID=""
    else
        npm run start > "${LOG_DIR}/mcp.log" 2>&1 &
        MCP_PID=$!
        echo ${MCP_PID} > "${LOG_DIR}/mcp.pid"
    fi

    log "Waiting for mcp-connect to become healthy (headless)..."
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
        log "--- tail nginx error.log ---"
        sudo tail -n 50 /var/log/nginx/error.log 2>/dev/null || true
        exit 1
    fi

    cleanup() {
        log "Shutting down services (headless)..."
        if [ -n "${MCP_PID:-}" ] && kill -0 "${MCP_PID}" >/dev/null 2>&1; then
            kill "${MCP_PID}" 2>/dev/null || true
        fi
        if [ -n "${NGINX_PID:-}" ] && kill -0 "${NGINX_PID}" >/dev/null 2>&1; then
            sudo kill "${NGINX_PID}" 2>/dev/null || true
        fi
    }
    trap cleanup SIGTERM SIGINT

    if [ -n "${MCP_PID:-}" ]; then
        wait "${MCP_PID}"
    else
        while true; do
            sleep 3600
        done
    fi
    exit 0
fi

# Prepare MCP env and dependencies (GUI mode)
prepare_mcp_env

# Virtual display components ---------------------------------------------------
DISPLAY_NUM=${XVFB_DISPLAY#:}
DISPLAY_NUM=${DISPLAY_NUM%%.*}
DISPLAY_SOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"
XAUTH_FILE=${XAUTH_FILE:-/home/user/.Xauthority}

# Prepare Xauthority so both Xvfb and x11vnc can authenticate to the same display
log "Preparing Xauthority for display ${XVFB_DISPLAY}"
mkdir -p "$(dirname "${XAUTH_FILE}")"
# Generate a 16-byte hex cookie (fallback chain: mcookie -> openssl -> /dev/urandom)
COOKIE="$( (mcookie 2>/dev/null) || (openssl rand -hex 16 2>/dev/null) || (dd if=/dev/urandom bs=16 count=1 2>/dev/null | xxd -p -c 32) )"
if [ -z "${COOKIE}" ]; then
    log "ERROR: failed to generate Xauthority cookie"
    exit 1
fi
# Ensure we replace any existing cookie for this display
xauth -f "${XAUTH_FILE}" remove "${XVFB_DISPLAY}" >/dev/null 2>&1 || true
xauth -f "${XAUTH_FILE}" add "${XVFB_DISPLAY}" . "${COOKIE}" || { log "failed to write cookie to ${XAUTH_FILE}"; exit 1; }
chmod 600 "${XAUTH_FILE}" || true
export XAUTHORITY="${XAUTH_FILE}"

log "Cleaning up stale Xvfb state for display ${XVFB_DISPLAY}"
pkill -f -- "Xvfb ${XVFB_DISPLAY}" >/dev/null 2>&1 || true
rm -f "/tmp/.X${DISPLAY_NUM}-lock" "${DISPLAY_SOCKET}" >/dev/null 2>&1 || true
mkdir -p /tmp/.X11-unix
chmod 1777 /tmp/.X11-unix || true

log "Ensuring Xvfb is running on ${XVFB_DISPLAY}"
nohup Xvfb "${XVFB_DISPLAY}" -screen 0 "${XVFB_RESOLUTION}" -nolisten tcp -auth "${XAUTH_FILE}" > "${LOG_DIR}/xvfb.log" 2>&1 &
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

log "Preparing desktop directories and templates"
mkdir -p "${DESKTOP_DIR}" "${CONFIG_ROOT}" "${FLUXBOX_DIR}" "${PCMANFM_CONFIG_DIR}" "${TINT2_CONFIG_DIR}" "${CHROME_LAUNCHER%/*}" /home/user/.chrome-data

cat <<'SCRIPT' > "${CHROME_LAUNCHER}"
#!/bin/bash
set -euo pipefail
XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/home/user/.xdg}
mkdir -p "$XDG_RUNTIME_DIR"

/usr/bin/google-chrome \
  --disable-dev-shm-usage \
  --remote-debugging-port=9222 \
  --remote-debugging-address=127.0.0.1 \
  --disable-gpu \
  --disable-features=VizDisplayCompositor \
  --disable-software-rasterizer \
  --no-first-run \
  --start-maximized \
  --window-size=${XVFB_WIDTH},${XVFB_HEIGHT} \
  --user-data-dir=/home/user/.chrome-data \
  "$@" &
CHROME_LAUNCH_PID=$!

(
  # Try up to 20 times to find and resize the Chrome window
  for i in $(seq 1 20); do
    WID=$(xdotool search --onlyvisible --class google-chrome 2>/dev/null | head -n 1 || true)
    if [ -n "${WID:-}" ]; then
      # Move to 0,0 and size to display geometry
      read SCREEN_W SCREEN_H < <(xdotool getdisplaygeometry)
      xdotool windowmove "$WID" 0 0 || true
      xdotool windowsize "$WID" "$SCREEN_W" "$SCREEN_H" || true
      # Prefer maximize (not fullscreen) so panels stay visible
      wmctrl -x -r google-chrome.Google-chrome -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true
      break
    fi
    sleep 0.5
  done
) &

wait ${CHROME_LAUNCH_PID}
SCRIPT
chmod +x "${CHROME_LAUNCHER}"

if [ -d "${DESKTOP_TEMPLATE_DIR}/fluxbox" ]; then
    cp -rf "${DESKTOP_TEMPLATE_DIR}/fluxbox/." "${FLUXBOX_DIR}/"
fi
if [ -d "${DESKTOP_TEMPLATE_DIR}/pcmanfm/default" ]; then
    cp -rf "${DESKTOP_TEMPLATE_DIR}/pcmanfm/default/." "${PCMANFM_CONFIG_DIR}/"
fi
if [ -d "${DESKTOP_TEMPLATE_DIR}/tint2" ]; then
    cp -rf "${DESKTOP_TEMPLATE_DIR}/tint2/." "${TINT2_CONFIG_DIR}/"
fi

# Ensure Fluxbox toolbar is hidden to avoid double panels when using tint2
if [ -f "${FLUXBOX_DIR}/init" ]; then
  case "${FLUXBOX_TOOLBAR}" in
    1|true|TRUE|True)
      if grep -q '^session.screen0.toolbar.visible:' "${FLUXBOX_DIR}/init" 2>/dev/null; then
        sed -i 's/^session.screen0.toolbar.visible:.*/session.screen0.toolbar.visible:  true/' "${FLUXBOX_DIR}/init" || true
      else
        echo 'session.screen0.toolbar.visible:  true' >> "${FLUXBOX_DIR}/init"
      fi
      ;;
    *)
      # default: hide toolbar to avoid duplicate panels; may be re-enabled later if tint2 fails
      if grep -q '^session.screen0.toolbar.visible:' "${FLUXBOX_DIR}/init" 2>/dev/null; then
        sed -i 's/^session.screen0.toolbar.visible:.*/session.screen0.toolbar.visible:  false/' "${FLUXBOX_DIR}/init" || true
      else
        echo 'session.screen0.toolbar.visible:  false' >> "${FLUXBOX_DIR}/init"
      fi
      ;;
  esac
fi

cat <<'DESKTOP_ENTRY' > "${DESKTOP_DIR}/Chrome.desktop"
[Desktop Entry]
Name=Chrome
Exec=/home/user/bin/chrome-devtools.sh
Icon=google-chrome
Terminal=false
Type=Application
Categories=Network;WebBrowser;
DESKTOP_ENTRY

cat <<'DESKTOP_ENTRY' > "${DESKTOP_DIR}/Terminal.desktop"
[Desktop Entry]
Name=Terminal
Exec=/usr/bin/x-terminal-emulator
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=System;
DESKTOP_ENTRY
chmod +x "${DESKTOP_DIR}/"*.desktop

log "Ensuring fluxbox window manager is running"
pkill -x fluxbox >/dev/null 2>&1 || true
nohup fluxbox > "${LOG_DIR}/fluxbox.log" 2>&1 &
FLUXBOX_PID=$!
echo ${FLUXBOX_PID} > "${LOG_DIR}/fluxbox.pid"

log "Starting PCManFM desktop manager"
pkill -f "pcmanfm --desktop" >/dev/null 2>&1 || true
nohup pcmanfm --desktop --profile=default > "${LOG_DIR}/pcmanfm.log" 2>&1 &
PCMANFM_PID=$!
echo ${PCMANFM_PID} > "${LOG_DIR}/pcmanfm.pid"

if [ "${TINT2_ENABLED}" = "1" ] || [ "${TINT2_ENABLED}" = "true" ]; then
  log "Starting tint2 panel"
  pkill -x tint2 >/dev/null 2>&1 || true
  nohup tint2 > "${LOG_DIR}/tint2.log" 2>&1 &
  TINT2_PID=$!
  echo ${TINT2_PID} > "${LOG_DIR}/tint2.pid"
else
  log "TINT2_ENABLED=0; skipping tint2"
  TINT2_PID=""
fi

# If tint2 fails to start, re-enable Fluxbox toolbar as a fallback
(
  sleep 1
  if [ -n "${TINT2_PID}" ] && ! kill -0 ${TINT2_PID} >/dev/null 2>&1; then
    if [ -f "${FLUXBOX_DIR}/init" ] && [ "${FLUXBOX_TOOLBAR}" = "auto" ]; then
      if grep -q '^session.screen0.toolbar.visible:' "${FLUXBOX_DIR}/init" 2>/dev/null; then
        sed -i 's/^session.screen0.toolbar.visible:.*/session.screen0.toolbar.visible:  true/' "${FLUXBOX_DIR}/init" || true
      else
        echo 'session.screen0.toolbar.visible:  true' >> "${FLUXBOX_DIR}/init"
      fi
      pkill -HUP -x fluxbox >/dev/null 2>&1 || true
    fi
  fi
) &

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

# Dynamic tuning parameters ----------------------------------------------------
X11VNC_WAIT=${X11VNC_WAIT:-20}          # milliseconds to wait between screen polls
X11VNC_DEFER=${X11VNC_DEFER:-20}        # defer update batching (ms)
X11VNC_COMPRESSION=${X11VNC_COMPRESSION:-9}  # deprecated in some builds; kept for env parity
X11VNC_QUALITY=${X11VNC_QUALITY:-5}     # deprecated in some builds; kept for env parity
X11VNC_EXTRA=${X11VNC_EXTRA:-}          # extra raw args, space separated

X11VNC_TUNING_OPTS=(
    -wait "${X11VNC_WAIT}" \
    -defer "${X11VNC_DEFER}" \
    -noxdamage \
    -ncache 0 \
)

if [ -n "${X11VNC_EXTRA}" ]; then
    # shellcheck disable=SC2206
    EXTRA_SPLIT=( ${X11VNC_EXTRA} )
    X11VNC_TUNING_OPTS+=("${EXTRA_SPLIT[@]}")
fi

log "Ensuring x11vnc is running on port ${VNC_PORT}"
pkill -f -- "x11vnc.*:${VNC_PORT}" >/dev/null 2>&1 || true
# Log the effective x11vnc command (without revealing sensitive values)
{
    printf '%s %s' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "Launching x11vnc with: x11vnc -display ${XVFB_DISPLAY} -rfbport ${VNC_PORT} -localhost -forever -shared -auth ${XAUTH_FILE} ";
    printf '%s ' "${X11VNC_TUNING_OPTS[@]}" 2>/dev/null || true;
    printf '\n';
} >> "${LOG_DIR}/x11vnc.log" 2>/dev/null || true

# Guard against external envs that inject unsupported libvncserver flags
unset X11VNC_OPTS X11VNC_OPTIONS X11VNC_ARGS X11VNC_QUALITY X11VNC_COMPRESSION TIGHT_QUALITY TIGHT_COMPRESSLEVEL VNC_QUALITY VNC_COMPRESSLEVEL || true

nohup x11vnc -display "${XVFB_DISPLAY}" \
    -rfbport "${VNC_PORT}" \
    -localhost \
    -forever \
    -shared \
    -auth "${XAUTH_FILE}" \
        "${X11VNC_TUNING_OPTS[@]}" \
    "${X11VNC_AUTH_OPTS[@]}" \
    -o "${LOG_DIR}/x11vnc.log" \
    > /dev/null 2>&1 &
X11VNC_PID=$!
echo ${X11VNC_PID} > "${LOG_DIR}/x11vnc.pid"

# Quick readiness probe for x11vnc port to avoid silent failures
for i in $(seq 1 10); do
    if nc -z 127.0.0.1 "${VNC_PORT}" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done
if ! nc -z 127.0.0.1 "${VNC_PORT}" >/dev/null 2>&1; then
    log "WARNING: x11vnc not listening on port ${VNC_PORT}" 
    log "--- tail x11vnc.log ---"
    tail -n 50 "${LOG_DIR}/x11vnc.log" 2>/dev/null || true
    # Retry with minimal flags to avoid crashes from unsupported options
    pkill -f -- "x11vnc.*:${VNC_PORT}" >/dev/null 2>&1 || true
    sleep 0.5
    log "Retrying x11vnc with minimal flags..."
    nohup x11vnc -display "${XVFB_DISPLAY}" \
        -rfbport "${VNC_PORT}" \
        -localhost \
        -forever \
        -shared \
        -auth "${XAUTH_FILE}" \
        "${X11VNC_AUTH_OPTS[@]}" \
        -o "${LOG_DIR}/x11vnc.log" \
        > /dev/null 2>&1 &
    X11VNC_PID=$!
    echo ${X11VNC_PID} > "${LOG_DIR}/x11vnc.pid"
    sleep 1
    if nc -z 127.0.0.1 "${VNC_PORT}" >/dev/null 2>&1; then
        log "x11vnc recovered with minimal flags"
    else
        log "x11vnc still not listening on port ${VNC_PORT} after retry"
    fi
fi

log "Ensuring noVNC web server is running on port ${NOVNC_PORT}"
pkill -f -- "websockify.*${NOVNC_PORT}" >/dev/null 2>&1 || true
nohup websockify --web="${NOVNC_WEBROOT}" \
    "${NOVNC_PORT}" \
    127.0.0.1:"${VNC_PORT}" \
    > "${LOG_DIR}/novnc.log" 2>&1 &
NOVNC_PID=$!
echo ${NOVNC_PID} > "${LOG_DIR}/novnc.pid"

log "Waiting for noVNC to become ready on port ${NOVNC_PORT}"
NOVNC_READY=0
for attempt in $(seq 1 10); do
    if curl -fsS "http://127.0.0.1:${NOVNC_PORT}/vnc.html" >/dev/null 2>&1; then
        log "noVNC is reachable (HTTP 200)"
        NOVNC_READY=1
        break
    fi
    log "noVNC not ready yet (attempt ${attempt}); retrying..."
    sleep 1
done

if [ "${NOVNC_READY}" -ne 1 ]; then
    log "WARNING: noVNC did not become reachable on port ${NOVNC_PORT}"
fi

# Chrome (non-headless) --------------------------------------------------------
log "Ensuring Chrome (DevTools) is running on display ${XVFB_DISPLAY}"
if pgrep -f -- '--remote-debugging-port=9222' >/dev/null 2>&1; then
    log "Chrome DevTools already running"
    CHROME_PID=$(pgrep -f -- '--remote-debugging-port=9222' | head -n 1)
else
    export XDG_RUNTIME_DIR=/home/user/.xdg
    mkdir -p "${XDG_RUNTIME_DIR}"
    nohup "${CHROME_LAUNCHER}" \
        about:blank \
        > "${LOG_DIR}/chrome.log" 2>&1 &
    CHROME_PID=$!
    echo ${CHROME_PID} > "${LOG_DIR}/chrome.pid"
    (
        for i in $(seq 1 10); do
            if wmctrl -x -r google-chrome.Google-chrome -b add,maximized_vert,maximized_horz >/dev/null 2>&1; then
                break
            fi
            sleep 1
        done
    ) &
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
    for pid_var in MCP_PID NGINX_PID CHROME_PID NOVNC_PID X11VNC_PID FLUXBOX_PID PCMANFM_PID TINT2_PID XVFB_PID; do
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
    # Keep script alive so services stay up even if no MCP PID was captured
    while true; do
        sleep 3600
    done
fi
# Virtual display components ---------------------------------------------------
# (GUI mode only; HEADLESS already exited above)
