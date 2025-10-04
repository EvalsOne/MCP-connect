# MCP Connect
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

    ███╗   ███╗ ██████╗██████╗      ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗
    ████╗ ████║██╔════╝██╔══██╗    ██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝
    ██╔████╔██║██║     ██████╔╝    ██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   
    ██║╚██╔╝██║██║     ██╔═══╝     ██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   
    ██║ ╚═╝ ██║╚██████╗██║         ╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   
    ╚═╝     ╚═╝ ╚═════╝╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   

The Model Context Protocol (MCP) is powerful, but most MCP servers only speak stdio. That makes them awkward to call directly from cloud or remote AI agents that expect HTTP transports.

MCP Connect lets you expose local stdio-based MCP servers over HTTP in two complementary ways:

1. Streamable HTTP over SSE (`POST /mcp/:serverId`): Maintain a persistent session for bidirectional, incremental, event-stream interaction (notifications, partial results, long‑running tool calls).
2. Classic request/response (`POST /bridge`): Start (or reuse) a local MCP server process and execute a single JSON-RPC call.

Core Features:
- Dual transports: one-shot HTTP and stateful streaming (SSE)
- Protocol bridge: transparent translation between HTTP (JSON / SSE frames) and local stdio JSON-RPC
- Zero changes to existing servers: declare them via `MCP_SERVERS` and they become `/mcp/<serverId>` endpoints
- Session lifecycle & TTL: idle eviction via `STREAM_SESSION_TTL_MS` prevents orphaned processes
- Security: optional bearer token plus CORS origin allow‑list (`ALLOWED_ORIGINS`)
- Multi-server mapping: manage and expose multiple heterogeneous MCP servers from a single process
- Built-in tunneling: Ngrok integration to publish a secure public URL quickly
- Lightweight Node.js footprint: fast startup; includes E2B sandbox deployment template
- Structured logging: consistent, queryable logs for observability and debugging

In short, MCP Connect brings local stdio-only MCP capabilities safely and efficiently to remote/cloud AI environments without modifying the underlying servers.

## What's new

- Added Streamable HTTP mode on top of the classic request/response bridge
- New quick-deploy scripts and configs under `deploy/e2b` for launching in an E2B sandbox
- Refreshed `.env` configuration section for clarity and accuracy

## How it works

```
+-----------------+   HTTP (JSON)               +------------------+      stdio      +------------------+
|                 |   /bridge                   |                  |                 |                  |
|  Cloud AI tools | <------------------------>  |  Node.js Bridge  | <------------>  |    MCP Server    |
|   (Remote)      |                             |    (Local)       |                 |     (Local)      |
|                 |   HTTP (SSE stream)         |                  |                 |                  |
|                 |   /mcp/:serverId            |                  |                 |                  |
+-----------------+         Tunnels (optional)  +------------------+                 +------------------+
```

## Prerequisites

- Node.js

## Quick Start

1. Clone the repository
   ```bash
   git clone https://github.com/EvalsOne/MCP-connect.git
   ```
   and enter the directory
   ```bash
   cd MCP-connect
   ```
2. Copy `.env.example` to `.env` and configure the port and `AUTH_TOKEN` (optional):
   ```bash
   cp .env.example .env
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. (Optional) Configure streamable server mappings by defining `MCP_SERVERS` in `.env`:
   ```env
   MCP_SERVERS={
     "mcp-server-fetch": {
       "command": "uvx",
       "args": ["mcp-server-fetch"]
     }
   }
   ```
   Each key becomes an HTTP endpoint at `/mcp/<serverId>` that proxies to the listed stdio MCP server.
5. Run MCP Connect
   ```bash
   # build MCP Connect
   npm run build
   # run MCP Connect
   npm run start
   # or, run in dev mode (supports hot reloading by nodemon)
   npm run dev
   ```
Now MCP connect should be running on 3000 port.

## API Endpoints

After MCP Connect is running, there are three endpoints exposed:

- `GET /health`: Health check endpoint
- `POST /bridge`: Main bridge endpoint for receiving requests from the cloud
- `POST /mcp/:serverId`: Streamable HTTP endpoints that proxies to the configured stdio MCP server

For example, the following is a configuration of the official [`mcp-server-fetch`](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch):

```json
{
  "command": "uvx",
  "args": ["mcp-server-fetch"]
}
```

You can send a request to the bridge as the following to list the tools of the MCP server and call a specific tool.

## Exposing MCP Connect to the Internet

There are two primary ways to make your local MCP endpoints (`/bridge` and `/mcp/:serverId`) reachable from remote AI agents or cloud services:

### 1. Running with Ngrok Tunnel

MCP Connect has built-in Ngrok integration.

Steps:
1. Obtain an auth token: https://dashboard.ngrok.com/authtokens
2. Add to your `.env`:
  ```env
  NGROK_AUTH_TOKEN=your_ngrok_auth_token
  ```
3. Start with tunnel:
  ```bash
  # Production mode with tunnel
  npm run start:tunnel

  # Development mode with tunnel (auto reload)
  npm run dev:tunnel
  ```
4. The console logs will display a public HTTPS URL. Your original local endpoints are now accessible at that base URL (e.g. `https://<random>.ngrok-free.app/bridge`).

Notes / Tips:
- Protect your endpoints with `AUTH_TOKEN` before tunneling.
- Use `ALLOWED_ORIGINS` to further scope who can call the tunnel URL from browsers.
- Rotate your Ngrok token periodically.

### 2. Deploying with an E2B Sandbox

For a more controlled, reproducible remote environment, you can launch MCP Connect inside an E2B sandbox using the provided template under `deploy/e2b`.

#### a) Install the E2B CLI / SDK

Install via pip (recommended in a virtualenv):
```bash
pip install --upgrade e2b
```

Set your API key (either export or create a project `.env`):
```env
E2B_API_KEY=your_api_key_here
```

#### b) Build the template (choose dev or prod)

Using Make shortcuts:
```bash
make e2b:build:dev   # fast, dev-oriented image
make e2b:build:prod  # minimized production image
```

Or directly with Python scripts:
```bash
python deploy/e2b/build_dev.py
python deploy/e2b/build_prod.py
```

#### c) Launch a sandbox from the template

```bash
python deploy/e2b/e2b_sandbox_manager.py
```
This manager script (see its console output) will create a sandbox instance based on the built `mcp` template and print its sandbox ID plus any exposed ingress URLs (e.g. a web/VNC interface such as:
```
https://443-<example1>.e2b.app/novnc/vnc.html?autoconnect=1
https://443-<example2>.e2b.app/novnc/vnc.html?autoconnect=1
```
Your MCP Connect HTTP server (port 3000) will typically be reachable via the sandbox domain as soon as the process starts.

#### d) View logs / run ad-hoc commands inside the sandbox

Use the provided log helper to stream logs or execute a command in-place (replace `<sandbox_id>`):
```bash
python deploy/e2b/view_sandbox_logs.py <sandbox_id> --exec "sudo nginx -s reload"
```
(Example shows reloading nginx if you enabled the included reverse proxy.)

#### e) Access MCP Connect endpoints

Once the sandbox reports the public base URL, test:
```bash
curl -H "Authorization: Bearer $AUTH_TOKEN" \
    -X POST https://<sandbox-domain>/bridge \
    -d '{"method":"tools/list","serverPath":"uvx","args":["mcp-server-fetch"],"params":{},"env":{}}'
```

#### f) Rebuild / iterate

Modify code locally, rebuild the template (dev variant for speed), and relaunch a sandbox to pick up the changes.

Security Recommendations:
- Always set `AUTH_TOKEN` in production or shared sandboxes.
- Limit session TTL via `STREAM_SESSION_TTL_MS` for streamed endpoints.
- Avoid embedding long-lived sandbox URLs in public docs; rotate as needed.

If you only need a quick ephemeral public URL, choose Ngrok. If you need a reproducible, inspectable remote runtime with richer tooling and potential additional services (nginx, extra MCP servers), use an E2B sandbox.

## Streamable HTTP Endpoint

When `MCP_SERVERS` defines one or more servers, MCP Connect exposes a Streamable HTTP transport at `/mcp/:serverId`.

1. **Initialize a session** (omit `Mcp-Session-Id` so the bridge assigns one):
   ```bash
   curl -i \
     -H 'Authorization: Bearer <AUTH_TOKEN>' \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -X POST http://localhost:3000/mcp/mcp-server-fetch \
     -d '{
           "jsonrpc": "2.0",
           "id": 1,
           "method": "initialize",
           "params": {
             "protocolVersion": "2025-03-26",
             "capabilities": {},
             "implementation": { "name": "demo-client", "version": "0.1.0" }
           }
         }'
   ```
   The response headers include `Mcp-Session-Id`; reuse it on subsequent requests.

2. **Stream a request** (expect Server-Sent Events):
   ```bash
   curl -N \
     -H 'Authorization: Bearer <AUTH_TOKEN>' \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -H 'Mcp-Session-Id: <session-from-step-1>' \
     -X POST http://localhost:3000/mcp/mcp-server-fetch \
     -d '[{
           "jsonrpc": "2.0",
           "id": 42,
           "method": "tools/call",
           "params": {"name": "fetch", "arguments": {"url": "https://example.com"}}
         }]'
   ```
   The terminal prints SSE frames containing the server's responses and notifications. When the final response for the supplied request IDs is delivered the stream closes automatically.

3. **Send responses or notifications back** using the same session:
   ```bash
   curl \
     -H 'Authorization: Bearer <AUTH_TOKEN>' \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -H 'Mcp-Session-Id: <session-from-step-1>' \
     -X POST http://localhost:3000/mcp/mcp-server-fetch \
     -d '{"jsonrpc":"2.0","id":99,"result":{}}'
   ```
   Requests without JSON-RPC `id` values return HTTP 202 to acknowledge the message.

**Listing tools:**

```bash
curl -X POST http://localhost:3000/bridge \
     -d '{
       "method": "tools/list",
       "serverPath": "uvx",
       "args": ["mcp-server-fetch"],
       "params": {},
       "env": {}
     }'
```

**Calling a tool:**

Using the `fetch` tool to retrieve a URL

```bash
curl -X POST http://localhost:3000/bridge \
     -d '{
       "method": "tools/call",
       "serverPath": "uvx",
       "args": ["mcp-server-fetch"],
       "params": {
         "name": "fetch",
         "arguments": {
            "url": "https://example.com"
         }
       },
       "env": {}
     }'
```

## Authentication

MCP Connect uses a simple token-based authentication system. The token is stored in the `.env` file. If the token is set, MCP Connect will use it to authenticate the request.

Sample request with token:

```bash
curl -X POST http://localhost:3000/bridge \
     -H "Authorization: Bearer <your_auth_token>" \
     -d '{
       "method": "tools/list",
       "serverPath": "uvx",
       "args": ["mcp-server-fetch"],
       "params": {},
       "env": {}
     }'
```

## Configuration

Environment variables:

- `PORT`: HTTP server port (default: 3000)
- `AUTH_TOKEN`: Bearer token for securing `/bridge` and `/mcp/*` endpoints (optional)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `ALLOWED_ORIGINS`: Comma-separated list of allowed Origins for CORS on the HTTP bridge (optional)
- `MCP_SERVERS`: JSON object describing stdio MCP servers exposable via Streamable HTTP (optional)
- `STREAM_SESSION_TTL_MS`: Idle timeout for streamable MCP sessions in milliseconds (default: `300000`)
- `NGROK_AUTH_TOKEN`: Ngrok auth token used by `start:tunnel` and `dev:tunnel` (optional)
- `NODE_ENV`: Standard Node environment flag like `development` or `production` (optional)

Example minimal `.env`:

```env
PORT=3000
AUTH_TOKEN=your_token_here
LOG_LEVEL=INFO
MCP_SERVERS={"mcp-server-fetch":{"command":"uvx","args":["mcp-server-fetch"]}}
```

## Deploying to an E2B Sandbox

We provide a ready-to-use E2B sandbox template and build scripts under `deploy/e2b` to spin up MCP Connect quickly in a controlled environment.

Prerequisites:

- E2B account and API key (see `deploy/e2b/README.md`)
- Python installed

Build the template:

```bash
# For development
make e2b:build:dev

# For production
make e2b:build:prod
```

Set your API key (either in a `.env` file or environment):

```env
E2B_API_KEY=your_api_key_here
```

For more details, see `deploy/e2b/README.md`.

## Using MCP Connect with ConsoleX AI to access local MCP Server

The following is a demo of using MCP Connect to access a local MCP Server on [ConsoleX AI](https://consolex.ai):

[![MCP Connect Live Demo](readme/thumbnail.png)](https://github-production-user-asset-6210df.s3.amazonaws.com/6077178/400736575-19dec583-7911-4221-bd87-3e6032ea7732.mp4)

## License

MIT License
