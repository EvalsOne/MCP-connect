import asyncio
from e2b import AsyncTemplate
from template import template
from e2b.template.types import LogEntry


async def main():
    def log_handler(entry: LogEntry) -> None:
        print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {entry.message}")

    await AsyncTemplate.build(
        template,
        alias="mcp-prod-gui",
        on_build_logs=log_handler,
        skip_cache=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
