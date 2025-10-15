# E2B MCP Sandbox Manager - Installation Guide

Python package for managing E2B sandboxes with MCP (Model Context Protocol) support, browser automation, and VNC access.

## Features

- 🚀 **E2B Sandbox Management**: Create and manage E2B sandboxes programmatically
- 🌐 **MCP Server Support**: Pre-configured MCP servers including Chrome DevTools
- 🖥️ **Virtual Display**: Xvfb, VNC, and noVNC support for headless browser automation
- 🔒 **Security**: Built-in authentication and secure connections
- 📊 **Health Monitoring**: Automatic health checks and keepalive mechanisms
- ⚙️ **Flexible Configuration**: Extensive configuration options via SandboxConfig

## Installation

### From GitHub (Direct)

```bash
pip install git+https://github.com/EvalsOne/MCP-bridge.git#subdirectory=deploy/e2b
```

### From GitHub (in requirements.txt)

```
e2b-mcp-sandbox @ git+https://github.com/EvalsOne/MCP-bridge.git@main#subdirectory=deploy/e2b
```

### From Local Clone

```bash
git clone https://github.com/EvalsOne/MCP-bridge.git
cd MCP-bridge/deploy/e2b
pip install -e .
```

## Quick Start

### As a Library

```python
import asyncio
from sandbox_deploy import E2BSandboxManager, SandboxConfig

async def main():
    # Configure the sandbox
    config = SandboxConfig(
        template_id="your-e2b-template-id",
        auth_token="your-secure-token",
        port=3000,
        timeout=3600
    )
    
    # Create manager
    manager = E2BSandboxManager(config)
    
    # Create sandbox
    result = await manager.create_sandbox(
        sandbox_id="my-sandbox",
        enable_internet=True,
        wait_for_ready=True
    )
    
    if result["success"]:
        print(f"Sandbox URL: {result['public_url']}")
        print(f"noVNC URL: {result['novnc_url']}")
        
        # Keep sandbox alive
        await asyncio.sleep(3600)
        
        # Clean up
        await manager.stop_sandbox("my-sandbox")

if __name__ == "__main__":
    asyncio.run(main())
```

### As a CLI Tool

```bash
# Set your E2B API key
export E2B_API_KEY='your-api-key'
export E2B_TEMPLATE_ID='your-template-id'

# Create a sandbox
python -m sandbox_deploy --sandbox-id my-sandbox --timeout 7200

# Or use the installed command
e2b-mcp-sandbox --sandbox-id my-sandbox
```

## Configuration

### SandboxConfig Options

```python
@dataclass
class SandboxConfig:
    template_id: str              # E2B template ID (required)
    timeout: int = 3600           # Sandbox timeout in seconds
    auth_token: str = "demo#e2b"  # Authentication token
    port: int = 3000              # MCP-connect port
    host: str = "127.0.0.1"       # MCP-connect host
    secure: bool = True           # Use HTTPS
    keepalive_interval: int = 60  # URL keepalive interval (seconds)
    platform_keepalive_interval: int = 120  # Platform keepalive (seconds)
    display: str = ":99"          # X display number
    xvfb_resolution: str = "1920x1080x24"  # Virtual display resolution
    vnc_port: int = 5900          # VNC server port
    novnc_port: int = 6080        # noVNC web port
    novnc_path: str = "/novnc/"   # noVNC URL path
    vnc_password: Optional[str] = ""  # VNC password (uses auth_token if empty)
```

### Environment Variables

- `E2B_API_KEY`: Your E2B API key (required)
- `E2B_TEMPLATE_ID`: Default template ID
- `E2B_SANDBOX_TIMEOUT`: Override default timeout
- `NPM_CI_ALWAYS`: Force npm dependency reinstall (0 or 1)

## API Reference

### E2BSandboxManager

Main class for managing E2B sandboxes.

#### Methods

- `async create_sandbox(sandbox_id, enable_internet, wait_for_ready)`: Create a new sandbox
- `async stop_sandbox(sandbox_id)`: Stop a specific sandbox
- `async stop_all_sandboxes()`: Stop all active sandboxes
- `async list_sandboxes()`: List all active sandboxes

### Return Value Structure

```python
{
    "success": True,
    "sandbox_id": "my-sandbox",
    "e2b_sandbox_id": "e2b-xxxxx",
    "public_url": "https://xxxxx.e2b.dev",
    "novnc_url": "https://xxxxx.e2b.dev/novnc/vnc.html",
    "services": {
        "nginx": {...},
        "mcp_connect": {...},
        "chrome_devtools": {...},
        "virtual_display": {...},
        "vnc": {...},
        "novnc": {...}
    },
    "security": {...},
    "created_at": "2025-10-07T12:00:00",
    "timeout_seconds": 3600,
    "internet_access": True
}
```

## Dependencies

- `e2b>=0.17.0`: E2B SDK
- `httpx>=0.24.0`: Async HTTP client (for health checks)
- Python 3.8+

## License

MIT License - See LICENSE file for details.

## Links

- Repository: https://github.com/EvalsOne/MCP-bridge
- E2B Documentation: https://e2b.dev/docs
- MCP Specification: https://modelcontextprotocol.io
