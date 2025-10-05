import asyncio
import argparse
from e2b import AsyncTemplate
from e2b.template.types import LogEntry
from template import make_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E2B template (prod variant)")
    parser.add_argument("--dockerfile", default="e2b.Dockerfile", help="Relative or absolute path to Dockerfile (default: e2b.Dockerfile)")
    parser.add_argument("--alias", default="mcp-prod-gui", help="Template alias to register (default: mcp-prod-gui)")
    parser.add_argument("--skip-cache", action="store_true", default=True, help="Skip build cache (default: True)")
    parser.add_argument("--cpu", type=int, default=2, help="CPU count to allocate during build (default: 2)")
    parser.add_argument("--memory-mb", type=int, default=2048, help="Memory in MB to allocate during build (default: 2048)")
    return parser.parse_args()


async def main():
    args = parse_args()
    tmpl = make_template(args.dockerfile)

    def log_handler(entry: LogEntry) -> None:
        print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {entry.message}")

    await AsyncTemplate.build(
        tmpl,
        alias=args.alias,
        on_build_logs=log_handler,
        skip_cache=args.skip_cache,
        cpu_count=args.cpu,
        memory_mb=args.memory_mb,
    )


if __name__ == "__main__":
    asyncio.run(main())
