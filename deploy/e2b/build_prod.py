import asyncio
import argparse
from e2b import AsyncTemplate
from e2b.template.types import LogEntry
from template import make_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E2B template (prod variant)")
    # Variant convenience selector: reuse dev variants (mcp-dev-* series templates)
    parser.add_argument(
        "--variant",
        choices=["full", "simple", "minimal"],
        default="full",
        help=(
            "Choose base template: full (GUI + noVNC), simple (headless Chrome), minimal (fastest). "
            "This selects the corresponding Dockerfile under deploy/e2b."
        ),
    )
    parser.add_argument(
        "--dockerfile",
        default=None,
        help="Relative or absolute path to Dockerfile (overrides --variant if provided)",
    )
    parser.add_argument(
        "--alias",
        default=None,
        help="Template alias to register (default uses mcp-dev-* naming by variant)",
    )
    parser.add_argument("--cpu", type=int, default=2, help="CPU count to allocate during build (default: 2)")
    parser.add_argument("--memory-mb", type=int, default=2048, help="Memory in MB to allocate during build (default: 2048)")
    parser.add_argument("--skip-cache", action="store_true", default=True, help="Skip build cache (default: True)")
    parser.add_argument("--verbose", action="store_true", help="Show verbose build logs (default: quiet)")
    return parser.parse_args()


async def main():
    args = parse_args()

    # Resolve dockerfile from variant unless explicitly provided
    variant_to_df = {
        "full": "e2b.Dockerfile",
        "simple": "e2b.Dockerfile.simple",
        "minimal": "e2b.Dockerfile.minimal",
    }
    chosen_df = args.dockerfile or variant_to_df[args.variant]
    tmpl = make_template(chosen_df)

    # Resolve alias default based on variant if not provided
    if not args.alias:
        # Use mcp-dev-* series naming per request
        variant_to_alias = {
            "full": "mcp-dev-gui",
            "simple": "mcp-dev-simple",
            "minimal": "mcp-dev-minimal",
        }
        args.alias = variant_to_alias[args.variant]

    def log_handler(entry: LogEntry) -> None:
        # Quiet mode: only show errors, filter noisy Dockerfile COMMENT warnings
        msg = (entry.message or "").strip()
        if msg.startswith("Unsupported instruction: COMMENT"):
            return
        if args.verbose:
            print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {msg}")
        else:
            if (entry.level or "").lower() in ("error", "fatal"):
                print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {msg}")

    await AsyncTemplate.build(
        tmpl,
        alias=args.alias,
        on_build_logs=log_handler,
        cpu_count=args.cpu,
        memory_mb=args.memory_mb,
        skip_cache=args.skip_cache,
    )

    # Minimal success summary
    print("✅ Template built")
    print(f"🏷️  Alias: {args.alias}")
    print(f"📄  Dockerfile: {chosen_df}")


if __name__ == "__main__":
    asyncio.run(main())
