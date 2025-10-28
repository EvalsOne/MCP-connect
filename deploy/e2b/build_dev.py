import asyncio
import argparse
from e2b import AsyncTemplate
from e2b.template.types import LogEntry
from template import make_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E2B template (dev variant)")
    # Variant convenience selector: maps to known Dockerfiles in deploy/e2b
    parser.add_argument(
        "--variant",
        choices=["full", "simple", "minimal"],
        default="full",
        help=(
            "Convenience selector for template Dockerfile: "
            "full=e2b.Dockerfile (GUI + noVNC), simple=e2b.Dockerfile.simple (headless Chrome, no X/noVNC), "
            "minimal=e2b.Dockerfile.minimal (no X/noVNC, fastest)"
        ),
    )
    parser.add_argument(
        "--dockerfile",
        default=None,
        help="Relative or absolute path to Dockerfile (overrides --variant if provided)"
    )
    parser.add_argument(
        "--alias",
        default=None,
        help="Template alias to register (default varies by --variant)"
    )
    parser.add_argument("--cpu", type=int, default=2, help="CPU count to allocate during build (default: 2)")
    parser.add_argument("--memory-mb", type=int, default=2048, help="Memory in MB to allocate during build (default: 2048)")
    parser.add_argument("--skip-cache", action="store_true", help="Skip build cache (default: use cache)")
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
        variant_to_alias = {
            "full": "mcp-dev-gui",
            "simple": "mcp-dev-simple",
            "minimal": "mcp-dev-minimal",
        }
        args.alias = variant_to_alias[args.variant]

    def log_handler(entry: LogEntry) -> None:
        # E2B's Dockerfile parser sometimes emits noisy warnings like
        # "Unsupported instruction: COMMENT" for standard '#' comments.
        # These do not affect the build and can be safely ignored.
        msg = (entry.message or "").strip()
        if msg.startswith("Unsupported instruction: COMMENT"):
            return
        print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {msg}")

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
    print(f"📄  Dockerfile: {chosen_df}")
    print("\nTo list templates:")
    print("  e2b template list")
    print("To show a specific template:")
    print(f"  e2b template show {args.alias}")
    print("\nUse the resulting template ID with e2b_sandbox_manager.py --template-id <id>")


if __name__ == "__main__":
    asyncio.run(main())
