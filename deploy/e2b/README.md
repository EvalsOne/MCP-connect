# 🌐 MCP Bridge — E2B Sandbox Deployment

Run MCP Bridge in an isolated E2B cloud sandbox environment.

## ⚡ Quick Start

### 1) Install dependencies

```bash
# set up and activate virual environment
cd deploy/e2b
python -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

### 2) Set API key

Sign up and get an E2B API key: https://e2b.dev/dashboard

```bash
export E2B_API_KEY=your-api-key-here
```

### 3) Build sandbox templates

```bash
cd deploy/e2b

python build.py --mode dev --variant full
python build.py --mode prod --variant minimal --skip-cache
```

Parameters

- `--variant`
  - What: quick template selection (maps to built-in Dockerfiles)
  - Options: `full` (GUI + noVNC), `simple` (no X desktop, headless Chrome), `minimal` (no X/Chrome/noVNC)
  - Default: `full`
  - Example: `--variant simple`

- `--dockerfile`
  - What: path to a Dockerfile to build the template image; overrides `--variant`
  - Example: `--dockerfile e2b.Dockerfile.minimal`

- `--alias`
  - What: assign a human-friendly alias to the built template. Defaults based on `--variant` and environment:

  Default for development:
    - `full` → `mcp-dev-gui`
    - `simple` → `mcp-dev-simple`
    - `minimal` → `mcp-dev-minimal`

  Default for production:
    - `full` → `mcp-prod-gui`
    - `simple` → `mcp-prod-simple`
    - `minimal` → `mcp-prod-minimal`

  
  - You can also use custom alias, example: `--alias custom-alias`

- `--cpu`
  - What: number of vCPUs allocated during build (int)
  - Default: `2`
  - Example: `--cpu 4`

- `--memory-mb`
  - What: memory size in MB (int)
  - Default: `2048`
  - Example: `--memory-mb 4096`

- `--skip-cache`
  - What: boolean flag; skip Docker cache to force rebuild of all layers. Dev defaults to cache, prod defaults to no cache.
  - Example: `--skip-cache`

Examples

```bash
python build.py --mode dev --variant simple --cpu 2 --memory-mb 2048
python build.py --mode dev --variant minimal --cpu 1 --memory-mb 1024 --skip-cache
python build.py --mode dev --alias mcp-dev-gui --cpu 4 --memory-mb 4096

python build.py --mode prod --variant full --quiet
python build.py --mode prod --variant simple --verbose
```

---

## 💻 Use the Sandbox

Run the prebuilt quickstart script:

```bash
# Full mode (with desktop GUI and Chrome)
python sandbox_deploy.py --template-id <template-id-or-alias> --auth-token <token>
```

This script will:
1. Create an E2B sandbox
2. Start the MCP Bridge service
3. Auto-test health check and tool calls
4. Print sandbox info

Parameters:

These map to `deploy/e2b/sandbox_deploy.py` CLI options (the script falls back to env vars and exits if required values are missing):

- `--template-id`
  - What: template ID or alias. Pass via CLI or set `E2B_TEMPLATE_ID`.
  - Required: yes (CLI or env). The script exits if missing.
  - Example: `--template-id mcp-xyz123`

- `--sandbox-id`
  - What: logical sandbox name (for local management/display)
  - Default: `mcp_test_sandbox`
  - Example: `--sandbox-id demo1`

- `--no-internet`
  - What: boolean flag; disable internet access in the sandbox (allow_internet_access=False)
  - Default: internet enabled unless specified

- `--no-wait`
  - What: boolean flag; do not wait for `/health` readiness after creating the sandbox
  - Default: wait for readiness (checks `/health`)

- `--timeout`
  - What: sandbox lifetime in seconds. Also settable via `E2B_SANDBOX_TIMEOUT`.
  - Default: `3600` (1 hour)
  - Example: `--timeout 7200`

- `--headless`
  - What: lightweight headless mode; skip Xvfb/fluxbox/Chrome/VNC/noVNC, keep Nginx + MCP-connect
  - Default: off (GUI mode)
  - Note: templates or aliases containing `simple` or `minimal` are treated as headless by default.

- `--auth-token`
  - What: sets the bridge API Bearer token. When omitted, the deploy flow prefers `E2B_MCP_AUTH_TOKEN` from the environment, then falls back to `AUTH_TOKEN` for compatibility. Requests must include `Authorization: Bearer <token>` when set.
  - Default: unset (server warns and allows unauthenticated access). For production, set a strong token.

- `--no-remote-fetch`
  - What: disable fetching latest `startup.sh`, `chrome-devtools-wrapper.sh`, and `mcp-servers.json` from a remote base inside the sandbox
  - Default: off (remote fetch enabled by config default)

- `--remote-base`
  - What: remote base URL used when fetching assets (e.g. `https://raw.githubusercontent.com/<org>/<repo>/<branch>/deploy/e2b`)
  - Default: `https://raw.githubusercontent.com/EvalsOne/MCP-bridge/main/deploy/e2b`

- `--probe-http`
  - What: also probe HTTP (port 80) `/health` alongside HTTPS during readiness and keepalive.
  - Default: off. By default, the manager only probes HTTPS to reduce noise when HTTP is not routed.

Important environment variables

- `E2B_API_KEY`: required; the script checks this and exits if missing. Example:

```bash
export E2B_API_KEY='your-api-key-here'
```

- `E2B_MCP_AUTH_TOKEN`: preferred environment variable for securing the MCP bridge in E2B deployments. Example:

```bash
export E2B_MCP_AUTH_TOKEN='your-secure-token'
```

- `AUTH_TOKEN`: legacy/generic alternative. Still accepted as a fallback if `E2B_MCP_AUTH_TOKEN` is not set.

- `E2B_TEMPLATE_ID`: alternative to `--template-id` (CLI takes precedence)
- `E2B_SANDBOX_TIMEOUT`: default timeout in seconds, same as `--timeout`
  
Note: Remote asset fetch control (`fetch_remote`, `remote_base`) is now configured via `SandboxConfig` or the CLI flags above, not environment variables.

Examples

```bash
# Specify template and wait for readiness
python sandbox_deploy.py --template-id mcp-xyz123 --sandbox-id demo1

# With explicit auth token
python sandbox_deploy.py --template-id mcp-xyz123 --auth-token 's3cr3t-token'

# Read template ID from env, disable internet, do not wait for readiness
export E2B_TEMPLATE_ID=mcp-xyz123
python sandbox_deploy.py --no-internet --no-wait

# Secure the bridge via environment variable (no CLI flag)
export E2B_MCP_AUTH_TOKEN='s3cr3t-token'
python sandbox_deploy.py --template-id mcp-xyz123 --sandbox-id demo1
```

---

## 📁 Template Layout

| File | Description |
|------|-------------|
| `template.py` | Sandbox template configuration |
| `build_dev.py` | Dev template build script |
| `build_prod.py` | Prod template build script |
| `e2b.Dockerfile` | Full sandbox image definition (with pre-built Desktop GUI and Chrome browser) |
| `e2b.Dockerfile.simple` | Simple image (with Chrome browser) |
| `e2b.Dockerfile.minimal` | Minimal image (core only) |
| `startup.sh` | Sandbox startup script |
| `nginx.conf` | Nginx reverse proxy config |
| `view_sandbox_logs.py` | Exec into sandbox for debug |
| `sandbox_deploy.py` | Sandbox management tool |

---

## 🔍 Manage & Debug

### Manage sandbox instances

New `sandbox_deploy.py` supports:

```bash
# Create a sandbox (template ID or alias)
python sandbox_deploy.py --template-id <template-or-alias> --sandbox-id demo1

# Disable waiting for health / disable internet
python sandbox_deploy.py --template-id <template-or-alias> --no-wait --no-internet
```

### Exec into sandbox for debug

```bash
python view_sandbox_logs.py <sandbox_id> --exec "<command_to_run>"
```

---

## 📖 More Resources

- **E2B docs**: https://e2b.dev/docs
- **MCP protocol**: https://modelcontextprotocol.io

---


**Enjoy running MCP Connect in the cloud!** 🎉
