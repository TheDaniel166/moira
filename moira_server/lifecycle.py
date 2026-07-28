"""Startup lifecycle for the Moira REST access surface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from moira import MissingEphemerisKernelError, Moira
from moira.spk_reader import set_kernel_path
from moira._spk_body_kernel import small_body_readers_from_manifest

from .config import ServerConfig


_PREWARM_DATETIME_UTC = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)


@dataclass(slots=True)
class StartupReadiness:
    """Internal per-process startup decision state; not a transport schema."""

    prewarm_enabled: bool
    decision_complete: bool = False
    prewarm_completed: bool = False
    prewarm_duration_seconds: float | None = None
    prewarm_error: str | None = None

    @property
    def ready(self) -> bool:
        """Whether transport startup policy permits computational traffic."""

        if not self.decision_complete:
            return False
        if not self.prewarm_enabled:
            return True
        return self.prewarm_completed and self.prewarm_error is None

    def complete_without_prewarm(self) -> None:
        """Record that startup intentionally skipped the opt-in warmup."""

        self.decision_complete = True

    def complete_prewarm(self, duration_seconds: float) -> None:
        """Publish one successfully completed bounded warmup."""

        self.prewarm_completed = True
        self.prewarm_duration_seconds = duration_seconds
        self.prewarm_error = None
        self.decision_complete = True

    def fail_prewarm(self, exc: Exception, duration_seconds: float) -> None:
        """Keep readiness closed while retaining liveness for diagnosis."""

        self.prewarm_completed = False
        self.prewarm_duration_seconds = duration_seconds
        self.prewarm_error = f"{type(exc).__name__}: {exc}"
        self.decision_complete = True


def prewarm_engine(engine: Moira) -> float:
    """Materialize the default planetary path once and return elapsed seconds.

    The warmup is deliberately bounded to one all-planet, no-node chart at
    J2000. It does not populate the HTTP chart-result cache and does not touch
    supplemental small-body surfaces.
    """

    started = perf_counter()
    engine.chart(_PREWARM_DATETIME_UTC, include_nodes=False)
    return perf_counter() - started


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
