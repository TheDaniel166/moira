"""
Internal kernel-readiness mixin for the public Moira facade.

This module holds facade orchestration only. It does not own kernel I/O,
ephemeris math, or public export policy; those remain in ``moira.spk_reader``
and ``moira.facade`` respectively.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .spk_reader import MissingKernelError


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class KernelFacadeMixin:
    """RITE: The Gatekeeper — the layer that proves a living kernel is present
    before any celestial computation may begin, and routes every public call
    through a consistent reader context.

THEOREM: Mixin that owns kernel discovery, health reporting, reader
         initialisation, and the `__getattribute__` guard that wraps every
         public method call in an active `use_reader_override` context.

RITE OF PURPOSE:
    KernelFacadeMixin enforces the contract that ``moira.Moira`` never
    silently operates on an absent kernel.  It discovers and opens the
    SPK kernel on first use, surfaces kernel status to callers, and
    ensures that downstream mixin methods receive a consistent reader
    without needing to manage it themselves.

LAW OF OPERATION:
    Responsibilities:
        - Discover and open the planetary SPK kernel on initialisation.
        - Report kernel presence via ``is_kernel_available`` and
          ``get_kernel_status``.
        - Wrap every non-private public method call in
          ``use_reader_override(self._reader_obj)`` so that engine
          modules see a consistent reader for the duration of the call.
        - Raise ``MissingEphemerisKernelError`` when a computation is
          attempted without a valid kernel.
    Non-responsibilities:
        - Does not own or implement any astronomical computation.
        - Does not manage thread-level concurrency beyond reader routing.
    Dependencies:
        - moira.spk_reader.SpkReader
        - moira.facade.use_reader_override (context manager)
    Structural invariants:
        - ``_reader_obj`` is either None or a valid SpkReader instance.
        - ``_kernel_init_error`` captures the most recent init failure.

Canon: Moira Sovereign Facade Architecture; moira.facade kernel policy.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_kernel.KernelFacadeMixin",
    "risk": "high",
    "api": {"frozen": ["is_kernel_available", "get_kernel_status", "kernel_status", "available_kernels", "configure_kernel_path", "download_missing_kernels"], "internal": ["_reader", "_reader_obj", "_try_initialize_reader"]},
    "state": {"mutable": true, "owners": ["_reader_obj", "_kernel_path", "_kernel_init_error"]},
    "effects": {"signals_emitted": [], "io": ["kernel_file_open"], "mutation": "instance_state"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "raise"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change", "kernel_policy"]}
}
[/MACHINE_CONTRACT]
    """

    def __init__(self, kernel_path: str | None = None) -> None:
        facade = _facade_module()
        self._kernel_path: str | None = kernel_path
        self._reader_obj: Any | None = None
        self._kernel_init_error: FileNotFoundError | MissingKernelError | None = None

        self._try_initialize_reader()

    def _try_initialize_reader(self) -> None:
        facade = _facade_module()
        try:
            path = self._kernel_path
            if path is None:
                from ._kernel_paths import find_planetary_kernel

                discovered = find_planetary_kernel()
                if discovered is not None:
                    path = str(discovered)
            if path is None:
                raise MissingKernelError(
                    "No planetary kernel is configured and none was found on disk."
                )
            self._reader_obj = facade.SpkReader(Path(path))
            self._kernel_init_error = None
        except (FileNotFoundError, MissingKernelError) as exc:
            self._reader_obj = None
            self._kernel_init_error = exc

    def __getattribute__(self, name: str):
        attr = object.__getattribute__(self, name)
        if (
            callable(attr)
            and not name.startswith("_")
            and name not in {
                "is_kernel_available",
                "get_kernel_status",
                "kernel_status",
                "available_kernels",
                "configure_kernel_path",
                "download_missing_kernels",
            }
        ):

            def _wrapped(*args, **kwargs):
                reader = object.__getattribute__(self, "_reader_obj")
                if reader is None:
                    return attr(*args, **kwargs)
                with _facade_module().use_reader_override(reader):
                    return attr(*args, **kwargs)

            return _wrapped
        return attr

    @property
    def _reader(self):
        if self._reader_obj is None:
            self._try_initialize_reader()
        if self._reader_obj is None:
            raise _facade_module().MissingEphemerisKernelError(self.get_kernel_status())
        return self._reader_obj

    def is_kernel_available(self) -> bool:
        if self._reader_obj is not None:
            return True
        self._try_initialize_reader()
        return self._reader_obj is not None

    @property
    def kernel_status(self) -> str:
        return self.get_kernel_status()

    def get_kernel_status(self) -> str:
        facade = _facade_module()
        if self._reader_obj is not None:
            return f"Kernel ready: {self._reader_obj.path}"

        if self._kernel_path:
            base = (
                f"No ephemeris kernel is loaded. Configured path: {self._kernel_path}. "
                f"User kernel directory: {facade.user_kernels_dir()}."
            )
        else:
            base = (
                "No planetary kernel is configured. "
                f"User kernel directory: {facade.user_kernels_dir()}."
            )
        if self._kernel_init_error is not None:
            base = f"{base} Last load error: {self._kernel_init_error}"
        return (
            f"{base} Run `moira-download-kernels` or configure a kernel path with "
            "`Moira.configure_kernel_path(path)`."
        )

    @property
    def available_kernels(self) -> list[str]:
        facade = _facade_module()
        from ._kernel_paths import PLANETARY_KERNELS

        planetary = [
            name for name in PLANETARY_KERNELS if facade.find_kernel(name).exists()
        ]
        supplemental = [
            name
            for name in [
                "asteroids.bsp",
                "sb441-n373s.bsp",
                "centaurs.bsp",
                "minor_bodies.bsp",
            ]
            if facade.find_kernel(name).exists()
        ]
        return planetary + supplemental

    def configure_kernel_path(self, path: str) -> None:
        self._kernel_path = path
        self._try_initialize_reader()
        if self._reader_obj is None:
            raise _facade_module().MissingEphemerisKernelError(self.get_kernel_status())

    def download_missing_kernels(self, interactive: bool = False) -> None:
        from .download_kernels import download_missing

        download_missing(interactive=interactive)
        self._try_initialize_reader()
