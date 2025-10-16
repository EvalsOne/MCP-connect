# 🌐 MCP Bridge — E2B Sandbox Deployment

Run MCP Bridge in an isolated E2B cloud sandbox environment.

[English](README.md) • [简体中文](README.zh-CN.md)

## ⚡ Quick Start

### 1) Install dependencies

```bash
pip install e2b requests
```

### 2) Set API key

Sign up and get an E2B API key: https://e2b.dev/dashboard

```bash
export E2B_API_KEY=your-api-key-here
```

### 3) Build sandbox templates

```bash
cd deploy/e2b

# 开发环境
python build_dev.py

# 或生产环境
python build_prod.py
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
  - What: assign a human-friendly alias to the built template. Defaults based on `--variant`:
    - `full` → `mcp-dev-gui`
    - `simple` → `mcp-dev-simple`
    - `minimal` → `mcp-dev-minimal`
  - Example: `--alias mcp-dev-gui`

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
# Use built-in simple variant (no X desktop, noVNC, headless Chrome) and alias as mcp-dev-simple
python build_dev.py --variant simple --cpu 2 --memory-mb 2048

# Use minimal variant (no X/Chrome/noVNC, fastest startup) and alias as mcp-dev-minimal
python build_dev.py --variant minimal --cpu 1 --memory-mb 1024 --skip-cache

# Use default Dockerfile, set alias to mcp-dev-gui, allocate 4 CPU and 4GB RAM
python build_dev.py --alias mcp-dev-gui --cpu 4 --memory-mb 4096
```

---

## 💻 Use the Sandbox

### Option 1: Quick demo script (recommended for beginners)

Run the prebuilt quickstart script:

```bash
# GUI mode (default)
python sandbox_deploy.py --template-id <template-id-or-alias>

# Headless mode (skip X/Chrome/VNC/noVNC)
python sandbox_deploy.py --template-id <template-id-or-alias> --headless
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

Important environment variables

- `E2B_API_KEY`: required; the script checks this and exits if missing. Example:

```bash
export E2B_API_KEY='your-api-key-here'
```

- `E2B_TEMPLATE_ID`: alternative to `--template-id` (CLI takes precedence)
- `E2B_SANDBOX_TIMEOUT`: default timeout in seconds, same as `--timeout`

Examples

```bash
# Specify template and wait for readiness
python sandbox_deploy.py --template-id mcp-xyz123 --sandbox-id demo1

# Read template ID from env, disable internet, do not wait for readiness
export E2B_TEMPLATE_ID=mcp-xyz123
python sandbox_deploy.py --no-internet --no-wait
```



### Option 2: Custom Python code

```python
from e2b import AsyncSandbox
import asyncio

async def main():
    # Create sandbox instance (replace with your template ID)
    sandbox = await AsyncSandbox.create('mcp-xyz123')

    try:
        # Start MCP Bridge service
        process = await sandbox.process.start(
            cmd="cd /app && ACCESS_TOKEN=my-token npm start"
        )

        # Wait for the service to start
        await asyncio.sleep(5)

        # Call the API
        result = await sandbox.commands.run(
            'curl http://localhost:3000/health'
        )
        print(f'Health: {result.stdout}')

        # Use your sandbox...

    finally:
        # Cleanup
        await sandbox.kill()

asyncio.run(main())
```

---

## 📁 Template Layout

| File | Description |
|------|-------------|
| `template.py` | Sandbox template configuration |
| `build_dev.py` | Dev template build script |
| `build_prod.py` | Prod template build script |
| `e2b.Dockerfile` | Full sandbox image definition |
| `e2b.Dockerfile.minimal` | Minimal image (core only) |
| `servers.json` | MCP servers configuration |
| `startup.sh` | Sandbox startup script |
| `nginx.conf` | Nginx reverse proxy config |
| `view_sandbox_logs.py` | Log viewer tool |
| `e2b_sandbox_manager.py` | Sandbox management tool |

---

## 🔍 Manage & Debug

### View sandbox logs

```bash
python view_sandbox_logs.py <sandbox-id>
```

### Manage sandbox instances

New `e2b_sandbox_manager.py` supports:

```bash
# Create a sandbox (template ID or alias)
python e2b_sandbox_manager.py --template-id <template-or-alias> --sandbox-id demo1

# Disable waiting for health / disable internet
python e2b_sandbox_manager.py --template-id <template-or-alias> --no-wait --no-internet

# List active sandboxes (current process context cache)
python e2b_sandbox_manager.py list

# Stop a sandbox
python e2b_sandbox_manager.py stop <sandbox_id>

# Stop all sandboxes
python e2b_sandbox_manager.py stop-all
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
