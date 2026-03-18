# MCP Connect

    ███╗   ███╗ ██████╗██████╗      ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗
    ████╗ ████║██╔════╝██╔══██╗    ██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝
    ██╔████╔██║██║     ██████╔╝    ██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   
    ██║╚██╔╝██║██║     ██╔═══╝     ██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   
    ██║ ╚═╝ ██║╚██████╗██║         ╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   
    ╚═╝     ╚═╝ ╚═════╝╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   


<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D20.0.0-brightgreen)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4+-blue)](https://www.typescriptlang.org/)

**Lightweight bridge that exposes local MCP servers as HTTP APIs**

</div>

---

## What Is MCP Connect?

MCP Connect is an HTTP gateway that lets you call local MCP servers (that speak stdio) through Streamable HTTP or a classic request/response bridge.

### What's New

- Added Streamable HTTP mode on top of the classic request/response bridge
- New quick-deploy scripts and configs under `deploy/e2b` for launching in an E2B sandbox

## How It Works

```
+-----------------+   HTTP (JSON)               +------------------+      stdio      +------------------+
|                 |   /bridge                   |                  |                 |                  |
|  Cloud AI tools | <------------------------>  |  Node.js Bridge  | <------------>  |    MCP Server    |
|   (Remote)      |                             |    (Local)       |                 |     (Local)      |
|                 |   HTTP (SSE stream)         |                  |                 |                  |
|                 |   /mcp/:serverId            |                  |                 |                  |
+-----------------+         Tunnels (optional)  +------------------+                 +------------------+
```

**Key Features**

| Feature | Description |
|--------|-------------|
| 🚀 Dual modes | Call local stdio MCP servers via Streamable HTTP or the classic HTTP bridge |
| 🔄 Session management | Maintain conversational continuity with sessions |
| 🔐 Security | Bearer token auth + CORS allowlist |
| 🌐 Public access | Built-in Ngrok tunnel to expose endpoints externally |
| ☁️ Cloud deploy | One-click deploy to E2B cloud sandbox |
---

## Quick Start

### Prerequisites

- Node.js >= 22.0.0 (recommended)
- npm or yarn

### 1) Install

```bash
git clone https://github.com/EvalsOne/MCP-connect.git
cd mcp-connect
npm install
```

### 2) Preparations

**A. Set up initial environment variables**

```bash
cp .env.example .env
```

Set `ACCESS_TOKEN` in `.env` before starting the server. Startup fails if it is empty.

**B. Configure MCP servers**

For Streamable HTTP method, each MCP server needs to be configurated separately, edit file to add more configurations other than the existing sample servers.
```bash
vim mcp-servers.json  
```

### 3) Run

```bash
# Build and start
npm run build
npm start

# Or use dev mode (hot reload)
npm run dev

# Enable Ngrok tunnel
npm run start:tunnel
```

After you see the startup banner, visit http://localhost:3000/health to check server status.


---

## Usage

### Mode 1: Streamable HTTP bridge

General-purpose and compatible with any MCP client that supports Streamable HTTP.

In Streamable HTTP mode, each MCP server is assigned a unique route. Example: add the `fetch` MCP server in `mcp-servers.json`.

```json
{
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"],
      "description": "HTTP/HTTPS content fetcher"
    }
  }
}
```

Once started, access the `fetch` MCP server with your favorite MCP client (e.g. Claude Code, Cursor, Codex, GitHub Copilot...)

```
http://localhost:3000/mcp/fetch
```

Note: You must configure `mcp-servers.json` before starting the service, otherwise the server won't be available.

---

### Mode 2: Classic request/response bridge

Non-standard invocation where you implement methods like `tools/list`, `tools/call`, etc.

Include ``Authorization: Bearer <token>`` in every request header. `ACCESS_TOKEN` is required at startup.

#### Example 1: List available tools

```bash
curl -X POST http://localhost:3000/bridge \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "serverPath": "uvx",
    "args": ["mcp-server-fetch"],
    "method": "tools/list",
    "params": {}
  }'
```

#### Example 2: Call a tool

```bash
curl -X POST http://localhost:3000/bridge \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "serverPath": "uvx",
    "args": ["mcp-server-fetch"],
    "method": "tools/call",
    "params": {
      "name": "fetch",
      "arguments": {
        "url": "https://example.com"
      }
    }
  }'
```

### Security

#### Authentication
MCP Connect requires a token-based authentication system. Set `ACCESS_TOKEN` in `.env` before startup. If it is empty, the server exits with a configuration error.

```bash
Authorization: Bearer <your_auth_token>
```

#### Allowed Origins
In production, set `ALLOWED_ORIGINS` to restrict cross-origin requests:

```env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

If `ALLOWED_ORIGINS` is set, non-matching origins are rejected.

---

## API Reference

### `GET /health`

Health check endpoint (no auth required)

Response:
```json
{"status": "ok"}
```

---


### `POST /mcp/:serverId`

Streaming HTTP mode

Path params:
- `serverId`: server ID defined in `MCP_SERVERS`

Headers:
- `Authorization: Bearer <token>` (required)
- `Accept: application/json, text/event-stream` (required)
- `mcp-session-id: <session-id>` (optional, reuse existing session)

Body:
```json
[
  {"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}},
  {"jsonrpc":"2.0","method":"notifications/initialized"}
]
```

---

### `POST /bridge`

Original request/response bridge mode

Headers:
- `Authorization: Bearer <token>` (required)
- `Content-Type: application/json`

Body:
```json
{
  "serverPath": "Executable command or URL (http/https/ws/wss)",
  "method": "JSON-RPC method name",
  "params": {},
  "args": ["optional command-line args"],
  "env": {"OPTIONAL_ENV_VAR": "value"}
}
```

Supported methods:
- `tools/list`, `tools/call`
- `prompts/list`, `prompts/get`
- `resources/list`, `resources/read`
- `resources/subscribe`, `resources/unsubscribe`
- `completion/complete`
- `logging/setLevel`

---

## Expose Publicly via Ngrok

1. Get a token: https://dashboard.ngrok.com/get-started/your-authtoken

2. Add to `.env`:
   ```env
   NGROK_AUTH_TOKEN=your-token-here
   ```

3. Start the service:
   ```bash
   npm run start:tunnel
   ```

4. The console will show public URLs:
   ```
   Tunnel URL: https://abc123.ngrok.io
   MCP Bridge URL: https://abc123.ngrok.io/bridge
   ```

---

## Quick Deploy to E2B Sandbox

E2B provides isolated cloud sandboxes, ideal for running untrusted MCP servers safely.

### Step 1: Prepare E2B environment

```bash
# Sign up at https://e2b.dev and get an API key
pip install e2b
export E2B_API_KEY=your-e2b-api-key
```

Optionally set a bearer token for the bridge (preferred env for E2B deployments):

```bash
export E2B_MCP_AUTH_TOKEN=your-secure-token
```

### Step 2: Build sandbox templates

```bash
cd deploy/e2b
python build.py
```

### Step 3: Launch from template

```bash
python sandbox_deploy.py --template-id mcp-dev-gui
```

See：[E2B deployment guide](deploy/e2b/README.md) for details.

---

## Logging & Monitoring

### Log files

- `combined.log`: all levels
- `error.log`: error level only

### Levels

Control verbosity via `LOG_LEVEL`:

```env
LOG_LEVEL=DEBUG  # development
LOG_LEVEL=INFO   # production (default)
LOG_LEVEL=WARN   # warnings + errors
```

---

## Development

### Project layout

```
src/
├── server/
│   └── http-server.ts      # HTTP server and routes
├── client/
│   └── mcp-client-manager.ts  # MCP client manager
├── stream/
│   ├── session-manager.ts   # session lifecycle
│   └── stream-session.ts    # SSE session implementation
├── config/
│   └── config.ts            # config loading & validation
├── utils/
│   ├── logger.ts            # Winston logger
│   └── tunnel.ts            # Ngrok tunnel management
└── index.ts                 # entry point
```

---

## Contributing

Issues and PRs are welcome!

---

<div align="center">

**If this project helps you, please ⭐️ Star it!**

</div>
