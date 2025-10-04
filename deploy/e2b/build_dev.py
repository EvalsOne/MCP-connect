import asyncio
from e2b import AsyncTemplate
from template import template
from e2b.template.types import LogEntry


async def main():
    def log_handler(entry: LogEntry) -> None:
        print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {entry.message}")

    await AsyncTemplate.build(
        template,
        alias="mcp-dev-gui",
        on_build_logs=log_handler,
        cpu_count=2,
        memory_mb=2048,
        # skip_cache=True,
    )
    
    print(f"✅ Template built successfully!")
    print(f"🏷️  Template Alias: mcp-dev-gui")
    print(f"\nTo get the template ID, run:")
    print(f"e2b template list")
    print(f"or")
    print(f"e2b template show mcp-dev")
    print(f"\nThen update your sandbox manager with the template ID!")


if __name__ == "__main__":
    asyncio.run(main())
