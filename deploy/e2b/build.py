import asyncio
import argparse
from typing import Any, Optional

from e2b import AsyncTemplate
from template import make_template


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E2B template (unified dev/prod)")
    parser.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default="dev",
        help="Select build mode: dev or prod (affects default alias and log verbosity)",
    )
    parser.add_argument(
        "--variant",
        choices=["full", "simple", "minimal"],
        default="full",
        help=(
            "Convenience selector for template Dockerfile: "
            "full=e2b.Dockerfile (GUI + noVNC), simple=e2b.Dockerfile.simple (headless Chrome), "
            "minimal=e2b.Dockerfile.minimal (no X/noVNC, fastest)"
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
        help="Template alias to register (default varies by --mode and --variant)",
    )
    parser.add_argument("--cpu", type=int, default=2, help="CPU count to allocate during build (default: 2)")
    parser.add_argument("--memory-mb", type=int, default=2048, help="Memory in MB to allocate during build (default: 2048)")
    parser.add_argument("--skip-cache", action="store_true", help="Skip build cache (default: off)")
    parser.add_argument("--verbose", action="store_true", help="Show verbose build logs (default: normal)")
    parser.add_argument("--quiet", action="store_true", help="Only show errors (default: normal)")
    return parser.parse_args(argv)


async def main(args: Optional[argparse.Namespace] = None) -> None:
    args = args or parse_args()

    variant_to_df = {
        "full": "e2b.Dockerfile",
        "simple": "e2b.Dockerfile.simple",
        "minimal": "e2b.Dockerfile.minimal",
    }
    chosen_df = args.dockerfile or variant_to_df[args.variant]
    tmpl = make_template(chosen_df)

    if not args.alias:
        prefix = "mcp-dev-" if args.mode == "dev" else "mcp-prod-"
        variant_to_alias = {
            "full": f"{prefix}gui",
            "simple": f"{prefix}simple",
            "minimal": f"{prefix}minimal",
        }
        args.alias = variant_to_alias[args.variant]

    def log_handler(entry: Any) -> None:
        msg = (entry.message or "").strip()
        # Filter noisy Dockerfile COMMENT warnings
        if msg.startswith("Unsupported instruction: COMMENT"):
            return
        # Logging behavior: quiet -> only errors; verbose -> all; normal -> info+warn+error
        level = (entry.level or "").lower()
        if args.quiet:
            if level in ("error", "fatal"):
                print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {msg}")
            return
        if args.verbose:
            print(f"[{entry.timestamp.isoformat()}] {entry.level.upper()}: {msg}")
            return
        if level in ("info", "warn", "error", "fatal"):
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
    print("\nUse the resulting template ID with sandbox_deploy.py --template-id <id>")


if __name__ == "__main__":
    asyncio.run(main())

