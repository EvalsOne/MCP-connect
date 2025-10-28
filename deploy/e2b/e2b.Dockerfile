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
    websockify

COPY scripts/setup-desktop-configs.sh /tmp/setup-desktop-configs.sh
RUN bash /tmp/setup-desktop-configs.sh \
 && rm -rf /var/lib/apt/lists/* /tmp/setup-desktop-configs.sh

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales tzdata \
    procps psmisc lsof net-tools iproute2 iputils-ping dnsutils jq \
    x11-xserver-utils xauth xclip xsel \
    fontconfig fonts-dejavu fonts-noto-cjk fonts-noto-color-emoji fonts-liberation \
    && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

RUN set -euo pipefail; \
        if id -u user >/dev/null 2>&1; then \
            echo "User 'user' already exists, skipping creation"; \
        else \
            useradd -m -s /bin/bash -u 1000 user; \
        fi; \
        if ! grep -q '^user .*NOPASSWD:ALL' /etc/sudoers; then \
            echo 'user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers; \
        fi

USER user
RUN set -euo pipefail; \
        echo "Installing uv (primary method)"; \
        if ! curl -fsSL https://astral.sh/uv/install.sh | sh -s --; then \
            echo "Primary uv installation failed; retrying (no flags)..."; \
            sleep 2; \
            curl -fsSL https://astral.sh/uv/install.sh | sh -s -- || { echo 'uv install failed'; exit 1; }; \
        fi; \
        test -x "$HOME/.local/bin/uv" || { echo 'uv binary missing after install'; exit 1; }
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

RUN apt-get update && apt-get install -y --no-install-recommends \
    dbus-x11 \
    libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1 libxcb-dri3-0 libxcomposite1 \
    libxrandr2 libxdamage1 libxkbcommon0 libcups2 libcairo2 \
    libpango-1.0-0 libpangocairo-1.0-0 libatspi2.0-0 \
    mesa-utils libgl1 libgl1-mesa-dri libgles2 libegl1 libglx-mesa0 \
    ffmpeg \
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
    && rm -rf /var/lib/apt/lists/*


USER user
WORKDIR /home/user

RUN git clone https://github.com/EvalsOne/MCP-connect.git /home/user/mcp-connect && \
    cd /home/user/mcp-connect && \
    npm install && \
    npm run build


USER root
RUN npm install -g chrome-devtools-mcp@latest
USER user

# RUN mkdir -p /home/user/.config/mcp
# COPY mcp-servers.json /home/user/.config/mcp/servers.json
# RUN chown user:user /home/user/.config/mcp/servers.json

COPY scripts/chrome-devtools-wrapper.sh /home/user/chrome-devtools-wrapper.sh
RUN chmod +x /home/user/chrome-devtools-wrapper.sh && chown user:user /home/user/chrome-devtools-wrapper.sh

USER root

COPY nginx.conf /etc/nginx/sites-available/default

COPY startup.sh /home/user/startup.sh
RUN chmod +x /home/user/startup.sh && chown user:user /home/user/startup.sh

RUN mkdir -p /home/user/app && \
    chown -R user:user /home/user/app

ENV HOST=127.0.0.1


USER user
WORKDIR /home/user

CMD /bin/sh -c 'echo MCP template ready'
