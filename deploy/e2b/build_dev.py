import asyncio
import argparse
from e2b import AsyncTemplate
from e2b.template.types import LogEntry
from template import make_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E2B template (dev variant)")
    parser.add_argument("--dockerfile", default="e2b.Dockerfile", help="Relative or absolute path to Dockerfile (default: e2b.Dockerfile)")
    parser.add_argument("--alias", default="mcp-dev-gui", help="Template alias to register (default: mcp-dev-gui)")
    parser.add_argument("--cpu", type=int, default=2, help="CPU count to allocate during build (default: 2)")
    parser.add_argument("--memory-mb", type=int, default=2048, help="Memory in MB to allocate during build (default: 2048)")
    parser.add_argument("--skip-cache", action="store_true", help="Skip build cache (default: use cache)")
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
        cpu_count=args.cpu,
        memory_mb=args.memory_mb,
        skip_cache=args.skip_cache,
    )

    print("✅ Template built successfully!")
    print(f"🏷️  Template Alias: {args.alias}")
    print("\nTo list templates:")
    print("  e2b template list")
    print("To show a specific template:")
    print(f"  e2b template show {args.alias}")
    print("\nUse the resulting template ID with e2b_sandbox_manager.py --template-id <id>")


if __name__ == "__main__":
    asyncio.run(main())
