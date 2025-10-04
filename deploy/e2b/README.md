# mcp - E2B Sandbox Template

This is an E2B sandbox template that allows you to run code in a controlled environment.

## Prerequisites

Before you begin, make sure you have:
- An E2B account (sign up at [e2b.dev](https://e2b.dev))
- Your E2B API key (get it from your [E2B dashboard](https://e2b.dev/dashboard))
- Python installed

The E2B sandbox image also includes:

- Python 3 runtime (apt-managed)
- uv toolchain with `uv` and `uvx` available in PATH

## Configuration

1. Create a `.env` file in your project root or set the environment variable:
   ```
   E2B_API_KEY=your_api_key_here
   ```

## Building the Template

```bash
# For development
make e2b:build:dev

# For production
make e2b:build:prod
```

## Using the Template in a Sandbox

Once your template is built, you can use it in your E2B sandbox:

```python
from e2b import AsyncSandbox
import asyncio

async def main():
    # Create a new sandbox instance
    sandbox = await AsyncSandbox.create('mcp')
    
    # Your sandbox is ready to use!
    print('Sandbox created successfully')

# Run the async function
asyncio.run(main())
```

## Template Structure

- `template.py` - Defines the sandbox template configuration
- `build_dev.py` - Builds the template for development
- `build_prod.py` - Builds the template for production

## Python and uvx inside the sandbox

The sandbox includes Python 3 and uv/uvx. Typical usage patterns:

- Run a Python one-liner: `python3 -c "print('hello from sandbox')"`
- Execute a Python module via uvx: `uvx some-python-cli --help`
- Launch an MCP server (e.g., fetch server): `uvx mcp-server-fetch`

## Next Steps

1. Customize the template in `template.py` to fit your needs
2. Build the template using one of the methods above
3. Use the template in your E2B sandbox code
4. Check out the [E2B documentation](https://e2b.dev/docs) for more advanced usage