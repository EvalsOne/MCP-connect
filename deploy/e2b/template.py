from pathlib import Path
from typing import Union

from e2b import AsyncTemplate

TEMPLATE_DIR = Path(__file__).resolve().parent

def make_template(dockerfile: Union[str, Path] = None) -> AsyncTemplate:
    """Factory to build an AsyncTemplate from a chosen Dockerfile.

    Args:
        dockerfile: Optional path (absolute or relative) to a Dockerfile. If omitted,
            defaults to the full featured 'e2b.Dockerfile'. A common alternative is
            'e2b.Dockerfile.minimal'.

    Returns:
        AsyncTemplate instance prepared from the specified Dockerfile.
    """
    if dockerfile is None:
        dockerfile = TEMPLATE_DIR / "e2b.Dockerfile"
    else:
        dockerfile = Path(dockerfile)
        if not dockerfile.is_absolute():
            dockerfile = (TEMPLATE_DIR / dockerfile).resolve()
    if not dockerfile.exists():  # Fail early with a clearer message
        raise FileNotFoundError(f"Dockerfile not found: {dockerfile}")
    return AsyncTemplate().from_dockerfile(str(dockerfile))

# Backwards compatibility: preserve previous 'template' symbol using default Dockerfile
template = make_template()

