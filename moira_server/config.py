"""Typed configuration for the Moira REST access surface."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class ServerConfig:
    """Minimal phase-1 server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"
    kernel_path: str | None = None
    small_body_manifest: str | None = None   # Path to sovereign small-body manifest.json for fast Type 13 native asteroids/comets
    docs_enabled: bool = True
    require_kernel_ready: bool = False

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Build config from environment variables."""

        docs_raw = os.getenv("MOIRA_SERVER_DOCS_ENABLED", "1").strip().lower()
        require_raw = os.getenv("MOIRA_SERVER_REQUIRE_KERNEL", "0").strip().lower()
        return cls(
            host=os.getenv("MOIRA_SERVER_HOST", "127.0.0.1"),
            port=int(os.getenv("MOIRA_SERVER_PORT", "8000")),
            log_level=os.getenv("MOIRA_SERVER_LOG_LEVEL", "info"),
            kernel_path=os.getenv("MOIRA_SERVER_KERNEL_PATH") or None,
            small_body_manifest=os.getenv("MOIRA_SERVER_SMALL_BODY_MANIFEST") or None,
            docs_enabled=docs_raw not in {"0", "false", "no", "off"},
            require_kernel_ready=require_raw in {"1", "true", "yes", "on"},
        )
