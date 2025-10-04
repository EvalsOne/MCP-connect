from pathlib import Path

from e2b import AsyncTemplate

TEMPLATE_DIR = Path(__file__).resolve().parent

template = AsyncTemplate().from_dockerfile(
    str(TEMPLATE_DIR / "e2b.Dockerfile"),
)
