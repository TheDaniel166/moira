"""Startup lifecycle for the Moira REST access surface."""

from __future__ import annotations

from moira import MissingEphemerisKernelError, Moira
from moira.spk_reader import set_kernel_path

from .config import ServerConfig


def create_engine(config: ServerConfig) -> Moira:
    """Create the stable per-process engine instance."""

    if config.kernel_path is not None:
        set_kernel_path(config.kernel_path)

    engine = Moira()
    if config.require_kernel_ready and not engine.is_kernel_available():
        raise MissingEphemerisKernelError(engine.get_kernel_status())
    return engine
