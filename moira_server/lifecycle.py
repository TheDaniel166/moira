"""Startup lifecycle for the Moira REST access surface."""

from __future__ import annotations

from moira import MissingEphemerisKernelError, Moira
from moira.spk_reader import KernelPool, set_kernel_path
from moira._spk_body_kernel import small_body_readers_from_manifest

from .config import ServerConfig


def create_engine(config: ServerConfig) -> Moira:
    """Create the stable per-process engine instance."""

    if config.kernel_path is not None:
        set_kernel_path(config.kernel_path)

    engine = Moira()
    if config.require_kernel_ready and not engine.is_kernel_available():
        raise MissingEphemerisKernelError(engine.get_kernel_status())

    # Load sovereign small-body kernels (Type 13 + native fast path) if configured.
    # These will be used by asteroid/comet services for high-performance website queries.
    if config.small_body_manifest:
        try:
            small_body_kernels = small_body_readers_from_manifest(config.small_body_manifest)
            # Store on engine for services to pick up (or use global pool pattern).
            # For now we attach a convenience attribute the services can use.
            engine._small_body_kernels = small_body_kernels  # type: ignore[attr-defined]
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load sovereign small body manifest from {config.small_body_manifest}: {exc}"
            ) from exc

    return engine
