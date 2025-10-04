FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    gnupg \
    ca-certificates \
    lsb-release \
    sudo \
    python3 \
    python3-pip \
    build-essential \
    software-properties-common \
    nginx \
    openssl \
    xvfb \
    x11vnc \
    fluxbox \
    pcmanfm \
    lxmenu-data \
    tint2 \
    feh \
    novnc \
    websockify \
    
RUN <<'EOF' bash
set -e
TEMPL=/opt/mcp-desktop
install -d -o 1000 -g 1000 "$TEMPL/fluxbox" "$TEMPL/fluxbox/styles" "$TEMPL/tint2" "$TEMPL/pcmanfm/default"

cat <<'FILE' > "$TEMPL/fluxbox/init"
session.configVersion:    13
session.screen0.toolbar.tools:  RootMenu, WorkspaceName, Iconbar, Clock
session.screen0.toolbar.autoHide:    false
session.screen0.toolbar.placement:   BottomCenter
session.screen0.toolbar.widthPercent: 100
session.screen0.toolbar.height: 28
session.screen0.toolbar.layer:  Dock
session.screen0.toolbar.maxOver:  False
session.screen0.toolbar.alpha:   255
session.screen0.iconbar.mode:    Workspace
session.screen0.iconbar.focused: true
session.screen0.iconbar.unfocused:  true
session.screen0.menu.delay:  150
session.screen0.rootCommand:  pcmanfm --desktop --profile=default
session.styleFile: ~/.fluxbox/styles/MCP-Grey
session.screen0.workspaceNames: Workspace 1, Workspace 2, Workspace 3, Workspace 4
session.autoRaiseDelay:   250
session.slitlistFile: ~/.fluxbox/slitlist
session.appsFile: ~/.fluxbox/apps
session.tabsAttachArea:   0
session.tabFocusModel:    Follow
session.focusTabMinWidth: 0
session.clickRaises:  True
session.focusModel:   ClickFocus
session.clientMenu.usePixmap:    true
session.tabPadding:    0
session.ignoreBorder:  false
session.styleOverlay:  ~/.fluxbox/overlay
FILE

cat <<'FILE' > "$TEMPL/fluxbox/overlay"
window.focus.alpha: 255
window.unfocus.alpha: 220
toolbar.alpha: 255
menu.alpha: 255
FILE

cat <<'FILE' > "$TEMPL/fluxbox/menu"
[begin] (MCP)
  [exec] (Chrome) {/usr/bin/google-chrome --no-sandbox}
  [exec] (Terminal) {x-terminal-emulator}
  [exec] (File Manager) {pcmanfm}
  [separator]
  [exit] (Logout)
[end]
FILE

cat <<'FILE' > "$TEMPL/fluxbox/keys"
OnDesktop Mouse1 :HideMenus
Mod1 Tab :NextWindow {static groups}
Mod1 Shift Tab :PrevWindow {static groups}
Mod4 d :RootMenu
Mod4 Return :ExecCommand x-terminal-emulator
Mod4 c :ExecCommand google-chrome --no-sandbox
FILE

cat <<'FILE' > "$TEMPL/fluxbox/styles/MCP-Grey"
! minimal neutral style
toolbar: flat gradient vertical
  toolbar.color: #2b303b
  toolbar.colorTo: #232832
  toolbar.borderColor: #1c1f26
  toolbar.borderWidth: 1
window.title.focus: flat gradient vertical
  window.title.focus.color: #3b4252
  window.title.focus.colorTo: #2e3440
window.title.unfocus: flat gradient vertical
  window.title.unfocus.color: #434c5e
  window.title.unfocus.colorTo: #3b4252
window.button.focus: flat solid
  window.button.focus.color: #d8dee9
window.button.unfocus: flat solid
  window.button.unfocus.color: #a7adba
menu.frame: flat solid
  menu.frame.color: #2e3440
menu.title: flat solid
  menu.title.color: #3b4252
handle: flat solid
  handle.color: #2e3440
borderColor: #1c1f26
borderWidth: 2
FILE

:>"$TEMPL/fluxbox/slitlist"
:>"$TEMPL/fluxbox/apps"

cat <<'FILE' > "$TEMPL/pcmanfm/default/desktop-items-0.conf"
[*]
wallpaper_mode=color
wallpaper=
desktop_bg=#1d1f21
desktop_shadow=#000000
desktop_font=Sans 11
desktop_folder=$HOME/Desktop
show_desktop_bg=1
show_trash=1
show_mounts=1
show_documents=1
show_wm_menu=0
sort=name;ascending;
FILE

cat <<'FILE' > "$TEMPL/tint2/tint2rc"
# Minimal tint2 panel
panel_items = LTS
panel_monitor = all
panel_position = bottom center horizontal
panel_size = 100% 30
panel_margin = 0 0
panel_padding = 8 4 8
panel_background_id = 0
wm_menu = 1

rounded = 6
border_width = 1
border_color = #1c1f26 100
background_color = #2b303b 95
background_color_hover = #343b48 95

launcher_padding = 4 4 4
launcher_item_size = 28
launcher_icon_theme = Adwaita

# Taskbar
task_text = 1
urgent_nb_of_blink = 7
mouse_middle = none
mouse_right = close
mouse_scroll_up = toggle
mouse_scroll_down = iconify

time1_format = %H:%M
clock_font_color = #eceff4 100
clock_padding = 8 0

backgrounds = 1
background_id = 0
  background_color = #2b303b 95
  border_color = #1c1f26 100
  border_width = 1
  border_radius = 6
FILE

chown -R 1000:1000 "$TEMPL"
EOF
&& rm -rf /var/lib/apt/lists/*

# Locale and basic diagnostics/fonts/X11 utils for better UX & stability
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales tzdata \
    # diagnostics
    procps psmisc lsof net-tools iproute2 iputils-ping dnsutils jq \
    # X11 utilities / clipboard
    x11-xserver-utils xauth xclip xsel \
    # fonts & fontconfig (CJK + Emoji + western)
    fontconfig fonts-dejavu fonts-noto-cjk fonts-noto-color-emoji fonts-liberation \
    && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install uv (provides `uv` and `uvx`) for the sandbox user and expose globally
USER user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
USER root
RUN if [ -f /home/user/.local/bin/uv ]; then install -m 0755 /home/user/.local/bin/uv /usr/local/bin/uv; fi \
 && if [ -f /home/user/.local/bin/uvx ]; then install -m 0755 /home/user/.local/bin/uvx /usr/local/bin/uvx; else ln -sf /usr/local/bin/uv /usr/local/bin/uvx; fi

RUN wget --progress=dot:giga -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/google-chrome.deb \
    && rm -f /tmp/google-chrome.deb \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xdg-utils \
    xdotool \
    wmctrl \
    libgbm1 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Extra Chrome/GTK/Pango/ATK runtime libs + Mesa/GL stack + media codecs
RUN apt-get update && apt-get install -y --no-install-recommends \
    dbus-x11 \
    # GTK/ATK/Pango and friends used by many GUI apps and Chrome paths
    libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1 libxcb-dri3-0 libxcomposite1 \
    libxrandr2 libxdamage1 libxkbcommon0 libcups2 libcairo2 \
    libpango-1.0-0 libpangocairo-1.0-0 libatspi2.0-0 \
    # Mesa / OpenGL (software rendering fallback)
    mesa-utils libgl1 libgl1-mesa-dri libgles2 libegl1 libglx-mesa0 \
    # Media codecs / WebRTC helpers
    ffmpeg \
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
    && rm -rf /var/lib/apt/lists/*


RUN useradd -m -s /bin/bash -u 1000 user && \
    echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER user
WORKDIR /home/user

RUN git clone https://github.com/EvalsOne/MCP-connect.git /home/user/mcp-connect && \
    cd /home/user/mcp-connect && \
    npm install && \
    npm run build

USER root
RUN npm install -g chrome-devtools-mcp@latest
USER user

RUN mkdir -p /home/user/.config/mcp \
 && printf '%s\n' \
 '{' \
 '  "servers": {' \
 '    "chrome-devtools": {' \
 '      "command": "/home/user/chrome-devtools-wrapper.sh",' \
 '      "args": [],' \
 '      "env": {' \
 '        "CHROME_REMOTE_DEBUGGING_URL": "http://127.0.0.1:9222"' \
 '      }' \
 '    }' \
 '  }' \
 '}' \
 > /home/user/.config/mcp/servers.json \
 && chown user:user /home/user/.config/mcp/servers.json

RUN cat <<'EOF' > /home/user/chrome-devtools-wrapper.sh
#!/bin/bash
# Wrapper to ensure chrome-devtools-mcp connects to the running Chrome instance
set -euo pipefail

REMOTE_URL=${CHROME_REMOTE_DEBUGGING_URL:-http://127.0.0.1:9222}
ARGS=("$@")

# Pass HTTP debugging endpoint to MCP as per README (--browserUrl)
exec chrome-devtools-mcp --browserUrl "$REMOTE_URL" "${ARGS[@]}"
EOF
RUN chmod +x /home/user/chrome-devtools-wrapper.sh && chown user:user /home/user/chrome-devtools-wrapper.sh

USER root

RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -subj "/CN=localhost" \
        -keyout /etc/nginx/ssl/server.key \
        -out /etc/nginx/ssl/server.crt \
        >/dev/null 2>&1

RUN printf '%s\n' \
'server {' \
'    listen 443 default_server;' \
'    listen [::]:443 default_server;' \
'' \
'    server_name _;' \
'' \
'    location = / {' \
'        default_type text/plain;' \
'        return 200 "MCP sandbox ready\\n";' \
'    }' \
'' \
'    location / {' \
'        proxy_pass http://127.0.0.1:3000/;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_connect_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_read_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location /novnc/ {' \
'        proxy_pass http://127.0.0.1:6080/;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_set_header Origin $scheme://$host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_read_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location = /novnc/vnc.html {' \
'        if ($args = "") {' \
'            return 302 /novnc/vnc.html?lang=en;' \
'        }' \
'        if ($args !~ "(^|&)lang=") {' \
'            return 302 /novnc/vnc.html?$args&lang=en;' \
'        }' \
'        proxy_pass http://127.0.0.1:6080/vnc.html;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_set_header Origin $scheme://$host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_read_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location /websockify {' \
'        proxy_pass http://127.0.0.1:6080/websockify;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_set_header Origin $scheme://$host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_read_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location /health {' \
'        access_log off;' \
'        return 200 "healthy\\n";' \
'        add_header Content-Type text/plain;' \
'    }' \
'}' \
'' \
'server {' \
'    listen 80 default_server;' \
'    listen [::]:80 default_server;' \
'' \
'    server_name _;' \
'' \
'    location = / {' \
'        default_type text/plain;' \
'        return 200 "MCP sandbox ready\\n";' \
'    }' \
'' \
'    location / {' \
'        proxy_pass http://127.0.0.1:3000/;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_connect_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_read_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location /novnc/ {' \
'        proxy_pass http://127.0.0.1:6080/;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_set_header Origin $scheme://$host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_read_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location = /novnc/vnc.html {' \
'        if ($args = "") {' \
'            return 302 /novnc/vnc.html?lang=en;' \
'        }' \
'        if ($args !~ "(^|&)lang=") {' \
'            return 302 /novnc/vnc.html?$args&lang=en;' \
'        }' \
'        proxy_pass http://127.0.0.1:6080/vnc.html;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_set_header Origin $scheme://$host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_read_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location /websockify {' \
'        proxy_pass http://127.0.0.1:6080/websockify;' \
'        proxy_http_version 1.1;' \
'        proxy_set_header Upgrade $http_upgrade;' \
'        proxy_set_header Connection "upgrade";' \
'        proxy_set_header Host $host;' \
'        proxy_set_header Origin $scheme://$host;' \
'        proxy_cache_bypass $http_upgrade;' \
'        proxy_set_header X-Real-IP $remote_addr;' \
'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'        proxy_set_header X-Forwarded-Proto $scheme;' \
'        proxy_read_timeout 7d;' \
'        proxy_send_timeout 7d;' \
'        proxy_buffering off;' \
'    }' \
'' \
'    location /health {' \
'        access_log off;' \
'        return 200 "healthy\\n";' \
'        add_header Content-Type text/plain;' \
'    }' \
'}' \
> /etc/nginx/sites-available/default

RUN <<'CREATE_STARTUP' bash
set -e
cat <<'EOF' > /home/user/startup.sh
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
cat <<ENVFILE > .env
AUTH_TOKEN=${AUTH_TOKEN}
PORT=${PORT}
HOST=${HOST}
LOG_LEVEL=info
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
        cat <<'FLUXINIT' > "${FLUXBOX_DIR}/init"
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

log "Ensuring noVNC web server is running on port ${NOVNC_PORT}"
pkill -f -- "websockify.*${NOVNC_PORT}" >/dev/null 2>&1 || true
nohup websockify --web="${NOVNC_WEBROOT}" \
    "${NOVNC_PORT}" \
    127.0.0.1:"${VNC_PORT}" \
    > "${LOG_DIR}/novnc.log" 2>&1 &
NOVNC_PID=$!
echo ${NOVNC_PID} > "${LOG_DIR}/novnc.pid"

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
CREATE_STARTUP

RUN mkdir -p /home/user/app && \
    chown -R user:user /home/user/app

ENV AUTH_TOKEN="demo#e2b"
ENV PORT=3000
ENV HOST=127.0.0.1


USER user
WORKDIR /home/user

CMD /bin/sh -c 'echo MCP template ready'
