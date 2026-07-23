"""Private binding between source-owned Delta-T and an opened ephemeris.

Generic clock functions in :mod:`moira.julian` preserve their source product.
This module performs the separate composition required by reader-backed SPK
work: a historical reconstructed Delta-T may be translated only after the
reader has established its DE/LE identity from kernel content.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .julian import (
    DeltaTPolicy,
    _ResolvedDeltaT,
    _require_representable_time_jd,
    _resolve_delta_t_for_ut1,
    tt_to_ut,
)
from .spk_reader import (
    KernelReader,
    OutOfRangeError,
    _EphemerisKernelIdentity,
)


class _EphemerisTimeBasisError(RuntimeError):
    """Raised when a basis-sensitive clock product lacks one target identity."""


@dataclass(frozen=True, slots=True)
class _BoundEphemerisDeltaT:
    """One source-aware Delta-T bound to a verified ephemeris identity."""

    raw: _ResolvedDeltaT
    identity: _EphemerisKernelIdentity | None
    correction_seconds: float
    seconds: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.correction_seconds):
            raise ValueError("ephemeris Delta-T correction must be finite")
        if not math.isfinite(self.seconds):
            raise ValueError("bound ephemeris Delta-T must be finite")


def _reader_identity_at(
    reader: KernelReader,
    jd_tt: float,
) -> _EphemerisKernelIdentity | None:
    """Return the reader's private content identity at one TT epoch."""

    resolver = getattr(reader, "_ephemeris_kernel_identity_at", None)
    if callable(resolver):
        identity = resolver(jd_tt)
    else:
        identity = getattr(reader, "_kernel_identity", None)
    if identity is None:
        return None
    if not isinstance(identity, _EphemerisKernelIdentity):
        raise _EphemerisTimeBasisError(
            "reader exposes an invalid private ephemeris identity vessel"
        )
    return identity


def _ephemeris_delta_t(
    jd_ut1: float,
    reader: KernelReader,
    *,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
) -> _BoundEphemerisDeltaT:
    """Bind the UT1 epoch's source Delta-T to ``reader`` explicitly.

    Direct EOP, aggregate, future-scenario, and policy-locked products remain
    numerically unchanged.  A declared historical tidal basis requires a
    content-derived target basis.  Reader selection is checked at both the raw
    and corrected TT epochs so a pool boundary cannot silently change the
    governing DE/LE solution.
    """

    _require_representable_time_jd("jd_ut1", jd_ut1)
    resolved = _resolve_delta_t_for_ut1(
        jd_ut1,
        year=year,
        delta_t_policy=delta_t_policy,
    )
    if resolved.retarget_mode != "declared":
        return _BoundEphemerisDeltaT(
            raw=resolved,
            identity=None,
            correction_seconds=0.0,
            seconds=resolved.seconds,
        )

    raw_jd_tt = jd_ut1 + resolved.seconds / 86400.0
    identity = _reader_identity_at(reader, raw_jd_tt)
    if identity is None:
        configured_identity = getattr(reader, "_kernel_identity", None)
        if isinstance(configured_identity, _EphemerisKernelIdentity):
            raise OutOfRangeError(
                "planetary ephemeris does not cover the requested historical "
                f"epoch JD(TT) {raw_jd_tt}",
                out_of_range_times=True,
            )
        raise _EphemerisTimeBasisError(
            "historical Delta-T requires a content-identified planetary "
            "ephemeris reader"
        )
    target_ndot = identity.lunar_tidal_acceleration_arcsec_per_cy2
    if target_ndot is None:
        raise _EphemerisTimeBasisError(
            "historical Delta-T cannot be translated to the unadmitted tidal "
            f"basis of {identity.summary_label!r}"
        )

    correction = resolved.correction_to(target_ndot)
    seconds = resolved.seconds + correction
    corrected_jd_tt = jd_ut1 + seconds / 86400.0
    corrected_identity = _reader_identity_at(reader, corrected_jd_tt)
    if corrected_identity != identity:
        before = identity.summary_label
        after = None if corrected_identity is None else corrected_identity.summary_label
        raise _EphemerisTimeBasisError(
            "Delta-T translation crosses an ambiguous planetary-kernel "
            f"identity boundary: {before!r} -> {after!r}"
        )

    return _BoundEphemerisDeltaT(
        raw=resolved,
        identity=identity,
        correction_seconds=correction,
        seconds=seconds,
    )


def _ut1_to_ephemeris_tt(
    jd_ut1: float,
    reader: KernelReader,
    *,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
) -> float:
    """Convert UT1 to the TT coordinate consumed by ``reader``."""

    bound = _ephemeris_delta_t(
        jd_ut1,
        reader,
        year=year,
        delta_t_policy=delta_t_policy,
    )
    return jd_ut1 + bound.seconds / 86400.0


def _ephemeris_tt_to_ut1(
    jd_tt: float,
    reader: KernelReader,
    *,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
) -> float:
    """Invert :func:`_ut1_to_ephemeris_tt` on the same bound clock surface."""

    _require_representable_time_jd("jd_tt", jd_tt)
    jd_ut1 = tt_to_ut(
        jd_tt,
        year=year,
        delta_t_policy=delta_t_policy,
    )
    for _ in range(12):
        bound = _ephemeris_delta_t(
            jd_ut1,
            reader,
            year=year,
            delta_t_policy=delta_t_policy,
        )
        next_ut1 = jd_tt - bound.seconds / 86400.0
        if next_ut1 == jd_ut1:
            break
        jd_ut1 = next_ut1

    recovered_tt = _ut1_to_ephemeris_tt(
        jd_ut1,
        reader,
        year=year,
        delta_t_policy=delta_t_policy,
    )
    tolerance = 4.0 * math.ulp(max(1.0, abs(jd_tt)))
    if abs(recovered_tt - jd_tt) > tolerance:
        raise RuntimeError("ephemeris TT-to-UT1 inversion did not converge")
    return jd_ut1
