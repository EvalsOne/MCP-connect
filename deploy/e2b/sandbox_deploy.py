#!/usr/bin/env python3
"""
E2B Sandbox Manager for MCP-enabled Web Sandbox
Creates and manages e2b sandboxes with pre-configured MCP servers
"""

import os
import sys
import asyncio
import argparse
from typing import Optional, Dict, Any, Tuple, Callable, Type, Union
from dataclasses import dataclass
#############################
# Sandbox client import logic
#############################
# We try modern async-first APIs before falling back to legacy ones.
SandboxType = Any  # alias for type hints after dynamic import
_sandbox_create_fn: Optional[Callable[..., Any]] = None
_sandbox_kind: str = "unknown"
try:  # Preferred: new async sandbox interface
    from e2b import AsyncSandbox as _AsyncSandbox  # type: ignore
    # Async interface typically exposes an async classmethod .create
    if hasattr(_AsyncSandbox, 'create'):
        _sandbox_create_fn = _AsyncSandbox.create  # type: ignore
        SandboxType = _AsyncSandbox  # type: ignore
        _sandbox_kind = 'async'
except Exception:  # pragma: no cover
    _sandbox_create_fn = None

if _sandbox_create_fn is None:
    try:  # Legacy: e2b_code_interpreter Sandbox (sync create)
        from e2b_code_interpreter import Sandbox as _LegacySandbox  # type: ignore
        if hasattr(_LegacySandbox, 'create'):
            # Legacy create is synchronous; we will offload with to_thread
            _sandbox_create_fn = _LegacySandbox.create  # type: ignore
            SandboxType = _LegacySandbox  # type: ignore
            _sandbox_kind = 'legacy'
    except Exception:  # pragma: no cover
        _sandbox_create_fn = None

if _sandbox_create_fn is None:  # Final guard: give a clear error early
    raise RuntimeError(
        "Unable to import E2B Sandbox client. Install or upgrade 'e2b' (preferred) or 'e2b-code-interpreter'."
    )
try:
    from e2b.sandbox.commands.command_handle import CommandExitException  # type: ignore
except Exception:  # pragma: no cover
    class CommandExitException(Exception):
        pass
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SandboxConfig:
    """Configuration for E2B Sandbox

    template_id is now mandatory (no default). Provide via constructor, CLI --template-id,
    or environment variable E2B_TEMPLATE_ID.
    """
    template_id: str = ""
    timeout: int = 3600  # 1 hour default timeout in seconds
    api_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    auth_token: str = "demo#e2b"
    port: int = 3000
    host: str = "127.0.0.1"
    secure: bool = True
    # Optional: heartbeat to keep sandbox/public URL active (seconds, 0 to disable)
    keepalive_interval: int = 60
    platform_keepalive_interval: int = 120
    display: str = ":99"
    xvfb_resolution: str = "1920x1080x24"
    vnc_port: int = 5900
    novnc_port: int = 6080
    novnc_path: str = "/novnc/"
    novnc_webroot: str = "/usr/share/novnc"
    vnc_password: Optional[str] = ""

class E2BSandboxManager:
    """Manager for E2B Sandboxes with MCP support"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize the sandbox manager

        Args:
            config: Optional sandbox configuration
        """
        self.config = config or SandboxConfig()
        if not self.config.template_id:
            # Allow fallback to environment variable
            env_tid = os.getenv("E2B_TEMPLATE_ID", "").strip()
            if env_tid:
                self.config.template_id = env_tid
        if not self.config.template_id:
            raise ValueError("template_id is required (use --template-id or set E2B_TEMPLATE_ID)")

        if not self.config.novnc_path.endswith("/"):
            self.config.novnc_path = f"{self.config.novnc_path}/"

        # Allow overriding timeout via environment variable (seconds)
        env_timeout = os.getenv("E2B_SANDBOX_TIMEOUT")
        if env_timeout:
            try:
                self.config.timeout = int(env_timeout)
            except ValueError:
                logger.warning("Invalid E2B_SANDBOX_TIMEOUT; using default %s", self.config.timeout)

        self.active_sandboxes: Dict[str, Dict[str, Any]] = {}

    async def create_sandbox(
        self,
        sandbox_id: Optional[str] = None,
        enable_internet: bool = True,
        wait_for_ready: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new E2B sandbox with MCP servers pre-configured

        Args:
            sandbox_id: Optional custom ID for the sandbox
            enable_internet: Whether to enable internet access
            wait_for_ready: Whether to wait for services to be ready

        Returns:
            Dictionary containing sandbox information
        """
        try:
            logger.info(f"Creating sandbox with template: {self.config.template_id}")

            # Create sandbox with custom template using whichever client was imported
            if _sandbox_kind == 'async':
                # Async API: call directly
                sandbox = await _sandbox_create_fn(  # type: ignore
                    template=self.config.template_id,
                    timeout=self.config.timeout,
                    metadata=self.config.metadata,
                    secure=self.config.secure,
                    allow_internet_access=enable_internet,
                )
            else:
                # Legacy sync API: run in thread
                sandbox = await asyncio.to_thread(
                    _sandbox_create_fn,  # type: ignore
                    template=self.config.template_id,
                    timeout=self.config.timeout,
                    metadata=self.config.metadata,
                    secure=self.config.secure,
                    allow_internet_access=enable_internet,
                )

            logger.info("Sandbox launched; startup services handled by image entrypoint")

            # Generate sandbox ID if not provided
            if not sandbox_id:
                sandbox_id = f"sandbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # Bootstrap services inside sandbox and persist handles
            bootstrap_info = await self._bootstrap_services(sandbox)

            handles = bootstrap_info["handles"]

            self.active_sandboxes[sandbox_id] = {
                "sandbox": sandbox,
                "process_handles": handles,
                "envs": bootstrap_info["envs"],
            }

            logger.info(f"Sandbox created with ID: {sandbox.sandbox_id}")

            # Enable internet access if requested
            if enable_internet:
                logger.info("Enabling internet access for sandbox...")
                # E2B sandboxes have internet access by default in newer versions
                # If using older version, you might need to configure this differently

            # Prepare candidate public URLs (both http/https)
            https_url = self._get_public_url(sandbox, secure=True)
            http_url = self._get_public_url(sandbox, secure=False)

            # Wait for services to be ready if requested, and discover which URL is healthy
            healthy_url = None
            probe_result = {"https_ok": False, "http_ok": False}
            if wait_for_ready:
                logger.info("Waiting for services to be ready (probing http and https /health)...")
                ready_info = await self._wait_for_services(sandbox, https_url, http_url)
                healthy_url = ready_info.get("healthy_url")
                probe_result = {k: ready_info.get(k, False) for k in ("https_ok", "http_ok")}

            # Choose public_url based on health probe or user preference as fallback
            if healthy_url:
                public_url = healthy_url
                fallback_url = http_url if healthy_url.startswith("https") else https_url
            else:
                # If no healthy result yet, pick according to self.config.secure but keep fallback
                if self.config.secure:
                    public_url = https_url
                    fallback_url = http_url
                else:
                    public_url = http_url
                    fallback_url = https_url

            # Prepare response
            sandbox_headers = sandbox.connection_config.sandbox_headers or {}

            # Derive displayed port for nginx based on the chosen URL
            nginx_port = 443 if public_url.startswith("https") else 80
            novnc_url = f"{public_url.rstrip('/')}{self.config.novnc_path}vnc.html"

            result = {
                "success": True,
                "sandbox_id": sandbox_id,
                "e2b_sandbox_id": sandbox.sandbox_id,
                "public_url": public_url,
                "novnc_url": novnc_url,
                "services": {
                    "nginx": {
                        "url": public_url,
                        "port": nginx_port,
                        "status": "running",
                        "pid": handles["nginx"].pid if handles.get("nginx") else None,
                    },
                    "mcp_connect": {
                        "url": f"{public_url}/bridge",
                        "port": self.config.port,
                        "auth_token": self.config.auth_token,
                        "status": "running",
                        "pid": handles["mcp_connect"].pid if handles.get("mcp_connect") else None,
                    },
                    "chrome_devtools": {
                        "debug_port": 9222,
                        "display": self.config.display,
                        "status": "running",
                        "pid": handles["chrome"].pid if handles.get("chrome") else None,
                    },
                    "virtual_display": {
                        "display": self.config.display,
                        "resolution": self.config.xvfb_resolution,
                        "status": "running",
                    },
                    "vnc": {
                        "port": self.config.vnc_port,
                        "status": "running",
                        "password_hint": "auth_token" if not self.config.vnc_password else "custom",
                    },
                    "novnc": {
                        "url": novnc_url,
                        "port": self.config.novnc_port,
                        "path": self.config.novnc_path,
                        "status": "running",
                        "requires_password": True,
                        "password_hint": "auth_token" if not self.config.vnc_password else "custom",
                    },
                },
                "security": {
                    "secure": self.config.secure,
                    "access_token": sandbox_headers.get("X-Access-Token"),
                },
                "created_at": datetime.now().isoformat(),
                "timeout_seconds": self.config.timeout,
                "internet_access": bool(enable_internet),
                "probes": probe_result
            }

            if fallback_url and fallback_url != public_url:
                key = "public_url_http" if self.config.secure else "public_url_https"
                result[key] = fallback_url

            logger.info(f"Sandbox ready: {public_url}")

            # Start keepalive loops if configured
            if self.config.keepalive_interval and self.config.keepalive_interval > 0:
                try:
                    task = asyncio.create_task(self._keepalive_loop(sandbox_id))
                    self.active_sandboxes[sandbox_id]["keepalive_task"] = task
                except Exception as e:
                    logger.warning("Failed to start keepalive loop: %s", str(e))
            if self.config.platform_keepalive_interval and self.config.platform_keepalive_interval > 0:
                try:
                    ptask = asyncio.create_task(self._platform_keepalive_loop(sandbox_id))
                    self.active_sandboxes[sandbox_id]["platform_keepalive_task"] = ptask
                except Exception as e:
                    logger.warning("Failed to start platform keepalive loop: %s", str(e))
            return result

        except Exception as e:
            logger.error(f"Failed to create sandbox: {str(e)}")
            if "sandbox" in locals():
                try:
                    await self._kill(sandbox)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Unable to clean up sandbox after failure: {cleanup_error}"
                    )
            return {
                "success": False,
                "error": str(e),
                "sandbox_id": sandbox_id
            }

    async def _bootstrap_services(self, sandbox) -> Dict[str, Any]:
        """Mirror startup.sh to initialise required services inside the sandbox."""

        display = self.config.display
        xvfb_resolution = self.config.xvfb_resolution
        xvfb_width, xvfb_height = self._parse_resolution(xvfb_resolution)
        vnc_port = str(self.config.vnc_port)
        novnc_port = str(self.config.novnc_port)
        if self.config.vnc_password is None:
            vnc_password = self.config.auth_token
        else:
            vnc_password = self.config.vnc_password
        novnc_webroot = self.config.novnc_webroot

        envs = {
            "AUTH_TOKEN": self.config.auth_token,
            "PORT": str(self.config.port),
            "HOST": self.config.host,
            # Allow forcing dependency reinstall similar to startup.sh
            "NPM_CI_ALWAYS": os.getenv("NPM_CI_ALWAYS", "0"),
        }

        service_envs = {
            **envs,
            "DISPLAY": display,
            "XVFB_DISPLAY": display,
            "XVFB_RESOLUTION": xvfb_resolution,
            "XVFB_WIDTH": xvfb_width,
            "XVFB_HEIGHT": xvfb_height,
            "VNC_PORT": vnc_port,
            "NOVNC_PORT": novnc_port,
            "NOVNC_WEBROOT": novnc_webroot,
            "VNC_PASSWORD": vnc_password,
        }

        logger.info("Configuring MCP environment variables inside sandbox...")
        env_file_contents = (
            f"AUTH_TOKEN={self.config.auth_token}\n"
            f"PORT={self.config.port}\n"
            f"HOST={self.config.host}\n"
            "LOG_LEVEL=info\n"
        )

        # Ensure mcp-connect dir exists and write .env
        await self._run(sandbox, "mkdir -p /home/user/mcp-connect", background=False, envs=envs, cwd="/home/user")
        await self._write(sandbox, "/home/user/mcp-connect/.env", env_file_contents)

        # If a local nginx.conf exists in repo, push it into the sandbox and apply
        try:
            repo_dir = os.path.dirname(os.path.abspath(__file__))
            local_nginx_conf = os.path.join(repo_dir, "nginx.conf")
            if os.path.isfile(local_nginx_conf):
                logger.info("Found local nginx.conf; pushing to sandbox and applying...")
                with open(local_nginx_conf, "r", encoding="utf-8") as f:
                    nginx_conf_content = f.read()

                # Write to a temp location and move with sudo
                await self._write(sandbox, "/home/user/nginx.conf.tmp", nginx_conf_content)

                # Test and apply the configuration if nginx is already present
                apply_cmd = (
                    "bash -lc "
                    "'set -e; "
                    "sudo cp /home/user/nginx.conf.tmp /etc/nginx/sites-available/default; "
                    "if pgrep -x nginx >/dev/null; then "
                    "  sudo nginx -t && sudo nginx -s reload; "
                    "else echo nginx not running yet; fi'"
                )
                await self._run(sandbox, apply_cmd, background=False, cwd="/home/user")
            else:
                logger.debug("No local nginx.conf found; keeping image default")
        except Exception as e:
            logger.warning("Failed to push/apply nginx.conf: %s", str(e))

        # Ensure startup.sh exists and use it to bootstrap services (Xvfb/x11vnc/noVNC/nginx/etc.)
        logger.info("Ensuring startup.sh is available inside sandbox")
        startup_exists = False
        try:
            startup_check = await self._run(sandbox, "bash -lc 'if [ -f /home/user/startup.sh ]; then echo FOUND; else echo MISSING; fi'", background=False, cwd="/home/user")
            startup_exists = 'FOUND' in (startup_check.stdout or '')
        except CommandExitException:
            startup_exists = False

        repo_dir = os.path.dirname(os.path.abspath(__file__))
        local_startup = os.path.join(repo_dir, "startup.sh")
        local_wrapper = os.path.join(repo_dir, "chrome-devtools-wrapper.sh")
        local_servers = os.path.join(repo_dir, "servers.json")

        if not os.path.isfile(local_startup):
            logger.warning("Local startup.sh not found at %s; cannot upload", local_startup)
        else:
            with open(local_startup, "r", encoding="utf-8") as handle:
                startup_contents = handle.read()

            logger.info("Uploading startup.sh to sandbox (overwriting existing copy)")
            await self._write(sandbox, "/home/user/startup.sh", startup_contents)
            startup_exists = True

        if os.path.isfile(local_wrapper):
            logger.info("Uploading chrome-devtools wrapper script to sandbox")
            with open(local_wrapper, "r", encoding="utf-8") as handle:
                wrapper_contents = handle.read()
            await self._write(sandbox, "/home/user/chrome-devtools-wrapper.sh", wrapper_contents)
            try:
                await self._run(sandbox, "bash -lc 'chmod +x /home/user/chrome-devtools-wrapper.sh'", background=False, cwd="/home/user")
            except CommandExitException as e:
                logger.warning("Failed to chmod chrome-devtools-wrapper.sh: %s", getattr(e, 'stderr', '') or str(e))
        else:
            logger.warning("chrome-devtools wrapper script missing at %s", local_wrapper)

        if os.path.isfile(local_servers):
            logger.info("Updating MCP servers.json inside sandbox")
            with open(local_servers, "r", encoding="utf-8") as handle:
                servers_contents = handle.read()
            await self._run(sandbox, "mkdir -p /home/user/.config/mcp", background=False, cwd="/home/user")
            await self._write(sandbox, "/home/user/.config/mcp/servers.json", servers_contents)
        else:
            logger.warning("servers.json not found at %s", local_servers)

        if startup_exists:
            try:
                await self._run(sandbox, "bash -lc 'chmod +x /home/user/startup.sh'", background=False, cwd="/home/user")
            except CommandExitException as e:
                logger.warning("Failed to chmod startup.sh: %s", getattr(e, 'stderr', '') or str(e))

            logger.info("Launching startup.sh to initialise GUI and proxy services")
            try:
                start_cmd = (
                    "bash -lc '"
                    "if [ -f /home/user/startup_sh.pid ] && kill -0 $(cat /home/user/startup_sh.pid) 2>/dev/null; then "
                    "  echo startup.sh already running; "
                    "else "
                    "  nohup /home/user/startup.sh > /home/user/startup.log 2>&1 & "
                    "  echo $! > /home/user/startup_sh.pid; "
                    "fi'"
                )
                await self._run(sandbox, start_cmd, background=False, envs=service_envs, cwd="/home/user")
            except CommandExitException as e:
                logger.error("Failed to launch startup.sh: %s", getattr(e, 'stderr', '') or str(e))
                raise

            logger.info("startup.sh launched; allowing services time to come up")
            await asyncio.sleep(5)
        else:
            logger.warning("startup.sh is not present inside sandbox; GUI services may be unavailable")

        # Handles retained for compatibility with existing return structure
        chrome_handle = None
        nginx_handle = None

        # Start MCP-connect only if PORT is not listening
        logger.info("Ensuring MCP-connect is running on port %s...", self.config.port)
        port = self.config.port
        # Probe MCP-connect via HTTP health to avoid relying on ss/lsof
        try:
            port_probe = await self._run(sandbox, f"bash -lc \"code=$(curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/health || true); echo $code\"", background=False, cwd="/home/user")
            mcp_listening = '200' in (port_probe.stdout or '')
        except CommandExitException:
            mcp_listening = False

        logger.info("Launching MCP-connect server if needed...")
        mcp_envs = {**envs, "LOG_LEVEL": "info"}
        mcp_handle = None
        if not mcp_listening:
            # Final dependency guard before starting the server (idempotent, fast when up-to-date)
            try:
                logger.info("Performing final dependency check before starting MCP-connect...")
                final_dep_cmd = (
                    "bash -lc "
                    "'set -e; cd /home/user/mcp-connect; "
                    "FORCE=${NPM_CI_ALWAYS:-0}; "
                    "if [ \"$FORCE\" = \"1\" ] || [ ! -d node_modules ] || [ package-lock.json -nt node_modules ] || [ package.json -nt node_modules ]; then "
                    "  echo \"Final dep check: installing/updating npm dependencies...\"; npm ci --no-audit || npm install --no-audit; "
                    "else "
                    "  echo \"Final dep check: node_modules up-to-date; skipping\"; "
                    "fi'"
                )
                await self._run(sandbox, final_dep_cmd, background=False, envs=envs, cwd="/home/user")
            except CommandExitException as e:
                logger.warning(
                    "Final dependency check reported an error (continuing to start anyway): %s",
                    getattr(e, 'stderr', '') or str(e),
                )
            # Start MCP-connect detached via nohup and record PID + log
            mcp_start_cmd = (
                "bash -lc "
                "'set -e; cd /home/user/mcp-connect; "
                "nohup npm run start > start.log 2>&1 & echo $! > mcp.pid'"
            )
            await self._run(sandbox, mcp_start_cmd, background=False, envs=mcp_envs, cwd="/home/user")
        else:
            logger.info("Port %s already listening; skipping MCP-connect launch", port)

        return {
            "handles": {
                "chrome": chrome_handle,
                "nginx": nginx_handle,
                "mcp_connect": mcp_handle,
                "xvfb": None,
                "fluxbox": None,
                "x11vnc": None,
                "novnc": None,
            },
            "envs": mcp_envs,
        }

    @staticmethod
    def _parse_resolution(resolution: str) -> Tuple[str, str]:
        """Extract width and height from an Xvfb resolution string (e.g. 1920x1080x24)."""
        try:
            parts = resolution.lower().split("x")
            width = parts[0] if parts else "1920"
            height = parts[1] if len(parts) > 1 else "1080"
        except Exception:
            return "1920", "1080"

        width_digits = ''.join(ch for ch in width if ch.isdigit()) or "1920"
        height_digits = ''.join(ch for ch in height if ch.isdigit()) or "1080"
        return width_digits, height_digits

    def _get_public_url(self, sandbox, secure: Optional[bool] = None) -> str:
        """
        Get the public URL for the sandbox

        Args:
            sandbox: The E2B sandbox instance

        Returns:
            The public URL for accessing the sandbox
        """
        target_secure = self.config.secure if secure is None else secure

        port = 443 if target_secure else 80
        scheme = "https" if target_secure else "http"

        try:
            hostname = sandbox.get_host(port)
            return f"{scheme}://{hostname}"
        except Exception:
            # attempt alternate port as last resort
            alt_port = 80 if target_secure else 443
            alt_scheme = "https" if alt_port == 443 else "http"
            hostname = sandbox.get_host(alt_port)
            return f"{alt_scheme}://{hostname}"

    async def _wait_for_services(
        self,
        sandbox,
        https_url: str,
        http_url: str,
        max_attempts: int = 30,
        delay: float = 2.0
    ) -> Dict[str, Any]:
        """
        Probe both HTTPS and HTTP health endpoints to determine readiness.

        Args:
            sandbox: The sandbox instance
            https_url: Candidate HTTPS public URL
            http_url: Candidate HTTP public URL
            max_attempts: Maximum number of attempts
            delay: Delay between attempts in seconds

        Returns:
            Dict with keys: https_ok (bool), http_ok (bool), healthy_url (str|None)
        """
        try:
            import httpx  # local import to allow absence handling
        except Exception:
            logger.warning("httpx not installed; skipping readiness probes and returning insecure URL preference.")
            return {"https_ok": False, "http_ok": False, "healthy_url": None}

        https_ok = False
        http_ok = False
        healthy_url = None

        for attempt in range(max_attempts):
            try:
                # Try HTTPS first (ignore TLS validation issues because of self-signed cert)
                async with httpx.AsyncClient(verify=False, timeout=5) as client:
                    # HTTPS
                    try:
                        resp = await client.get(f"{https_url}/health")
                        if resp.status_code == 200:
                            https_ok = True
                            healthy_url = https_url
                    except Exception:
                        pass
                    # HTTP
                    try:
                        resp = await client.get(f"{http_url}/health")
                        if resp.status_code == 200:
                            http_ok = True
                            if healthy_url is None:
                                healthy_url = http_url
                    except Exception:
                        pass

            except Exception:
                # ignore session-level errors; we'll retry
                pass

            if https_ok or http_ok:
                logger.info(
                    f"Services are ready (https_ok={https_ok}, http_ok={http_ok}, healthy={healthy_url})"
                )
                return {"https_ok": https_ok, "http_ok": http_ok, "healthy_url": healthy_url}

            logger.debug(
                f"Attempt {attempt + 1}/{max_attempts}: Services not ready yet (https={https_url}, http={http_url})"
            )
            await asyncio.sleep(delay)

        logger.warning(
            f"Services did not become ready after {max_attempts} attempts. Will continue without readiness guarantee."
        )
        return {"https_ok": https_ok, "http_ok": http_ok, "healthy_url": healthy_url}

    async def list_sandboxes(self) -> Dict[str, Any]:
        """
        List all active sandboxes

        Returns:
            Dictionary containing list of active sandboxes
        """
        sandboxes_info = []

        for sandbox_id, entry in self.active_sandboxes.items():
            sandbox = entry["sandbox"]
            sandboxes_info.append({
                "sandbox_id": sandbox_id,
                "e2b_sandbox_id": sandbox.sandbox_id,
                "public_url": self._get_public_url(sandbox),
                "status": "active"
            })

        return {
            "success": True,
            "count": len(sandboxes_info),
            "sandboxes": sandboxes_info
        }

    async def stop_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Stop and remove a sandbox

        Args:
            sandbox_id: The ID of the sandbox to stop

        Returns:
            Dictionary containing operation status
        """
        try:
            if sandbox_id not in self.active_sandboxes:
                return {
                    "success": False,
                    "error": f"Sandbox {sandbox_id} not found"
                }

            sandbox_entry = self.active_sandboxes[sandbox_id]
            sandbox = sandbox_entry["sandbox"]

            logger.info(f"Stopping sandbox: {sandbox_id}")

            # Cancel keepalive task if running
            try:
                task = sandbox_entry.get("keepalive_task")
                if task:
                    task.cancel()
            except Exception:
                pass
            try:
                ptask = sandbox_entry.get("platform_keepalive_task")
                if ptask:
                    ptask.cancel()
            except Exception:
                pass

            # Attempt to terminate services gracefully even if detached
            stop_cmds = [
                "bash -lc 'if [ -f /home/user/mcp-connect/mcp.pid ]; then kill $(cat /home/user/mcp-connect/mcp.pid) 2>/dev/null || true; rm -f /home/user/mcp-connect/mcp.pid; else pkill -f \"npm run start\" 2>/dev/null || true; fi'",
                "sudo nginx -s quit",
                "bash -lc 'if [ -f /home/user/chrome.pid ]; then kill $(cat /home/user/chrome.pid) 2>/dev/null || true; rm -f /home/user/chrome.pid; else pkill -f -- \"--remote-debugging-port=9222\" 2>/dev/null || true; fi'",
                "bash -lc 'if [ -f /home/user/novnc.pid ]; then kill $(cat /home/user/novnc.pid) 2>/dev/null || true; rm -f /home/user/novnc.pid; else pkill -f websockify 2>/dev/null || true; fi'",
                "bash -lc 'if [ -f /home/user/x11vnc.pid ]; then kill $(cat /home/user/x11vnc.pid) 2>/dev/null || true; rm -f /home/user/x11vnc.pid; else pkill -f x11vnc 2>/dev/null || true; fi'",
                "bash -lc 'if [ -f /home/user/fluxbox.pid ]; then kill $(cat /home/user/fluxbox.pid) 2>/dev/null || true; rm -f /home/user/fluxbox.pid; else pkill -x fluxbox 2>/dev/null || true; fi'",
                f"bash -lc 'if [ -f /home/user/xvfb.pid ]; then kill $(cat /home/user/xvfb.pid) 2>/dev/null || true; rm -f /home/user/xvfb.pid; else pkill -f \"Xvfb {self.config.display}\" 2>/dev/null || true; fi'",
            ]
            for cmd in stop_cmds:
                try:
                    await self._run(sandbox, cmd, background=False, cwd="/home/user")
                except Exception:
                    pass
            # Stop the sandbox itself
            await self._kill(sandbox)

            # Remove from active sandboxes
            del self.active_sandboxes[sandbox_id]

            return {
                "success": True,
                "message": f"Sandbox {sandbox_id} stopped successfully"
            }

        except Exception as e:
            logger.error(f"Failed to stop sandbox: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def stop_all_sandboxes(self) -> Dict[str, Any]:
        """
        Stop all active sandboxes

        Returns:
            Dictionary containing operation status
        """
        results = []

        for sandbox_id in list(self.active_sandboxes.keys()):
            result = await self.stop_sandbox(sandbox_id)
            results.append({
                "sandbox_id": sandbox_id,
                "stopped": result["success"]
            })

        return {
            "success": True,
            "stopped_count": len(results),
            "results": results
        }

    async def _keepalive_loop(self, sandbox_id: str) -> None:
        """Periodically ping the public URL to avoid idle eviction and refresh mapping.

        This loop will:
        - Probe both HTTPS and HTTP /health endpoints (TLS verification disabled for self-signed)
        - Prefer HTTPS when both are healthy
        - Log status each cycle
        """
        try:
            import httpx
        except Exception:
            logger.warning("httpx not installed; disabling keepalive probes.")
            return
        interval = max(5, int(self.config.keepalive_interval))  # floor to >=5s
        while True:
            try:
                entry = self.active_sandboxes.get(sandbox_id)
                if not entry:
                    return
                sandbox = entry["sandbox"]
                https_url = self._get_public_url(sandbox, secure=True)
                http_url = self._get_public_url(sandbox, secure=False)

                https_ok = False
                http_ok = False
                async with httpx.AsyncClient(verify=False, timeout=5) as client:
                    try:
                        r1 = await client.get(f"{https_url}/health")
                        https_ok = (r1.status_code == 200)
                    except Exception:
                        https_ok = False
                    try:
                        r2 = await client.get(f"{http_url}/health")
                        http_ok = (r2.status_code == 200)
                    except Exception:
                        http_ok = False

                if https_ok or http_ok:
                    chosen = https_url if https_ok else http_url
                    logger.debug("Keepalive OK for %s (https=%s, http=%s)", sandbox_id, https_ok, http_ok)
                else:
                    logger.warning("Keepalive probe failed for %s (https=%s, http=%s)", sandbox_id, https_ok, http_ok)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("Keepalive loop error: %s", str(e))
                await asyncio.sleep(interval)

    async def _platform_keepalive_loop(self, sandbox_id: str) -> None:
        """Ping the sandbox with a no-op command periodically to keep session active."""
        interval = max(10, int(self.config.platform_keepalive_interval))
        while True:
            try:
                entry = self.active_sandboxes.get(sandbox_id)
                if not entry:
                    return
                sandbox = entry["sandbox"]
                # Execute a very cheap no-op
                await self._run(sandbox, "bash -lc 'true'", False)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("Platform keepalive error: %s", str(e))
                await asyncio.sleep(interval)

    # ---------------- Helper abstraction layer for async vs legacy sandbox APIs ----------------
    @staticmethod
    def _is_coro(obj: Any) -> bool:
        return asyncio.iscoroutine(obj) or asyncio.isfuture(obj)

    async def _run(self, sandbox: Any, *args, **kwargs) -> Any:
        """Invoke sandbox.commands.run handling async or sync implementations."""
        runner = getattr(sandbox, 'commands', None)
        if runner is None:
            raise RuntimeError("Sandbox object missing 'commands' interface")
        fn = getattr(runner, 'run', None)
        if fn is None:
            raise RuntimeError("Sandbox.commands missing 'run' method")
        try:
            result = fn(*args, **kwargs)
            if self._is_coro(result):  # Async API
                return await result
            # Legacy returns an object directly
            return result
        except Exception:
            # Some legacy variants may require threading if blocking; fallback
            return await asyncio.to_thread(fn, *args, **kwargs)

    async def _write(self, sandbox: Any, path: str, content: str) -> None:
        files = getattr(sandbox, 'files', None)
        if files is None:
            raise RuntimeError("Sandbox object missing 'files' interface")
        fn = getattr(files, 'write', None)
        if fn is None:
            raise RuntimeError("Sandbox.files missing 'write' method")
        result = fn(path, content)
        if self._is_coro(result):
            await result

    async def _kill(self, sandbox: Any) -> None:
        fn = getattr(sandbox, 'kill', None)
        if fn is None:
            return
        result = fn()
        if self._is_coro(result):
            await result

async def main():
    """CLI entrypoint: allow specifying --template-id and --sandbox-id."""
    parser = argparse.ArgumentParser(description="Create an E2B sandbox running MCP Connect")
    parser.add_argument("--template-id", required=False, help="Template ID or alias to use (or set E2B_TEMPLATE_ID)")
    parser.add_argument("--sandbox-id", default="mcp_test_sandbox", help="Logical sandbox identifier label")
    parser.add_argument("--no-internet", action="store_true", help="Disable internet access inside sandbox")
    parser.add_argument("--no-wait", action="store_true", help="Do not wait for service readiness")
    parser.add_argument("--timeout", type=int, default=3600, help="Sandbox timeout seconds (default 3600)")
    args = parser.parse_args()

    template_id = (args.template_id or os.getenv("E2B_TEMPLATE_ID", "")).strip()
    if not template_id:
        print("❌ Error: Missing template ID. Provide --template-id or set E2B_TEMPLATE_ID.")
        sys.exit(2)
    config = SandboxConfig(template_id=template_id, timeout=args.timeout, metadata={"purpose": "mcp-dev-gui"})
    manager = E2BSandboxManager(config)
    logger.info("Creating E2B sandbox (template=%s sandbox_id=%s)...", template_id, args.sandbox_id)
    result = await manager.create_sandbox(
        sandbox_id=args.sandbox_id,
        enable_internet=not args.no_internet,
        wait_for_ready=not args.no_wait,
    )
    if not result.get("success"):
        print(f"❌ Failed to create sandbox: {result.get('error')}")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ SANDBOX CREATED SUCCESSFULLY!")
    print("="*60)
    print(f"\n📦 Sandbox ID: {result['sandbox_id']}")
    print(f"🌐 Public URL: {result['public_url']}")
    print(f"\n🔧 Services:")
    for service_name, service_info in result['services'].items():
        print(f"  - {service_name}:")
        print(f"    URL: {service_info.get('url', 'N/A')}")
        print(f"    Status: {service_info['status']}")
        if 'auth_token' in service_info:
            print(f"    Auth Token: {service_info['auth_token']}")
    print(f"\n⏱️  Timeout: {result['timeout_seconds']} seconds")
    print(f"🕐 Created: {result['created_at']}")
    print("\n" + "="*60)

    # Keep sandbox running for demonstration
    print("\n⌨️  Press Ctrl+C to stop the sandbox...")
    try:
        await asyncio.sleep(3600)  # Keep running for 1 hour max
    except KeyboardInterrupt:
        print("\n🛑 Stopping sandbox...")
        await manager.stop_all_sandboxes()
        print("✅ Sandbox stopped")

if __name__ == "__main__":
    # Check for E2B API key
    if not os.getenv('E2B_API_KEY'):
        print("❌ Error: E2B_API_KEY environment variable not set")
        print("Please set your E2B API key:")
        print("  export E2B_API_KEY='your-api-key-here'")
        sys.exit(1)

    # Run the main function
    asyncio.run(main())
