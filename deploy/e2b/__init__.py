"""
E2B MCP Sandbox Manager

Provides SandboxConfig and E2BSandboxManager for managing E2B sandboxes
with MCP servers and browser automation support.
"""
from sandbox_deploy import (
    E2BSandboxManager,
    SandboxConfig,
    CommandExitException,
)

__version__ = "0.1.0"
__all__ = [
    "E2BSandboxManager",
    "SandboxConfig", 
    "CommandExitException",
]
