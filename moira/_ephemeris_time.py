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
    _tt_to_tdb_with_receipt,
    tdb_to_tt,
    tt_to_ut,
)
from .spk_reader import (
    KernelReader,
    OutOfRangeError,
    _EphemerisKernelIdentity,
)


class _EphemerisTimeBasisError(RuntimeError):
    """Raised when a basis-sensitive clock product lacks one target identity."""

    def __init__(
        self,
        message: str,
        *,
        direction: str = "UT1_TO_TDB",
        provisional_identity_label: str | None = None,
        final_identity_label: str | None = None,
        iterations: int = 0,
        source_product: str | None = None,
        round_trip_residual_days: float | None = None,
    ) -> None:
        super().__init__(message)
        self.direction = direction
        self.provisional_identity_label = provisional_identity_label
        self.final_identity_label = final_identity_label
        self.iterations = iterations
        self.source_product = source_product
        self.round_trip_residual_days = round_trip_residual_days


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


@dataclass(frozen=True, slots=True)
class _BoundEphemerisTime:
    """One stable UT1/TT/TDB coordinate and its source-owned receipt."""

    jd_ut1: float
    epoch_tt: float
    epoch_tdb: float
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
    identity: _EphemerisKernelIdentity
    raw_delta_t: _ResolvedDeltaT
    identity_iterations: int
    tt_tdb_iterations: int


_EPHEMERIS_IDENTITY_MAX_ITERATIONS = 6


def _reader_identity_at(
    reader: KernelReader,
    epoch_tdb: float,
    *,
    snapshot=None,
) -> _EphemerisKernelIdentity | None:
    """Return the reader's private content identity at one TDB epoch."""

    resolver_tdb = getattr(reader, "_ephemeris_kernel_identity_at_tdb", None)
    if callable(resolver_tdb):
        if snapshot is None:
            identity = resolver_tdb(epoch_tdb)
        else:
            try:
                identity = resolver_tdb(epoch_tdb, snapshot=snapshot)
            except TypeError:
                identity = resolver_tdb(epoch_tdb)
    else:
        # Historical private adapters selected identity on TT.  Preserve that
        # behavior while making the new boundary's scale explicit.
        resolver_tt = getattr(reader, "_ephemeris_kernel_identity_at", None)
        if callable(resolver_tt):
            identity = resolver_tt(tdb_to_tt(epoch_tdb))
        else:
            identity = getattr(reader, "_integration_kernel_identity", None)
            if identity is None:
                identity = getattr(reader, "_kernel_identity", None)
    if identity is None:
        return None
    if not isinstance(identity, _EphemerisKernelIdentity):
        raise _EphemerisTimeBasisError(
            "reader exposes an invalid private ephemeris identity vessel"
        )
    return identity


def _bind_ephemeris_time(
    jd_ut1: float,
    reader: KernelReader,
    *,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
    snapshot=None,
) -> _BoundEphemerisTime:
    """Bind UT1, TT, TDB and one serving ephemeris identity atomically."""

    _require_representable_time_jd("jd_ut1", jd_ut1)
    resolved = _resolve_delta_t_for_ut1(
        jd_ut1,
        year=year,
        delta_t_policy=delta_t_policy,
    )

    identity: _EphemerisKernelIdentity | None = None
    provisional_label: str | None = None
    last_label: str | None = None
    for iteration in range(1, _EPHEMERIS_IDENTITY_MAX_ITERATIONS + 1):
        correction = 0.0
        if resolved.retarget_mode == "declared" and identity is not None:
            target_ndot = identity.lunar_tidal_acceleration_arcsec_per_cy2
            if target_ndot is None:
                raise _EphemerisTimeBasisError(
                    "historical Delta-T cannot be translated to the unadmitted "
                    f"tidal basis of {identity.summary_label!r}",
                    provisional_identity_label=provisional_label,
                    final_identity_label=identity.summary_label,
                    iterations=iteration,
                    source_product=resolved.source_product,
                )
            correction = resolved.correction_to(target_ndot)

        seconds = resolved.seconds + correction
        epoch_tt = math.fsum((float(jd_ut1), seconds / 86400.0))
        conversion = _tt_to_tdb_with_receipt(epoch_tt)
        candidate = _reader_identity_at(
            reader, conversion.epoch_tdb, snapshot=snapshot
        )
        if candidate is None:
            configured = getattr(reader, "_kernel_identity", None)
            if isinstance(configured, _EphemerisKernelIdentity):
                raise OutOfRangeError(
                    "planetary ephemeris does not cover the requested epoch "
                    f"JD(TDB) {conversion.epoch_tdb}",
                    out_of_range_times=True,
                )
            raise _EphemerisTimeBasisError(
                "orbital time binding requires a content-identified planetary "
                "ephemeris source",
                provisional_identity_label=provisional_label,
                final_identity_label=None,
                iterations=iteration,
                source_product=resolved.source_product,
            )

        if provisional_label is None:
            provisional_label = candidate.summary_label
        if candidate == identity:
            return _BoundEphemerisTime(
                jd_ut1=float(jd_ut1),
                epoch_tt=epoch_tt,
                epoch_tdb=conversion.epoch_tdb,
                delta_t_seconds=seconds,
                delta_t_correction_seconds=correction,
                tdb_minus_tt_seconds=conversion.tdb_minus_tt_seconds,
                identity=candidate,
                raw_delta_t=resolved,
                identity_iterations=iteration,
                tt_tdb_iterations=conversion.iterations,
            )
        last_label = None if identity is None else identity.summary_label
        identity = candidate

    raise _EphemerisTimeBasisError(
        "UT1-to-TDB binding did not converge on one planetary ephemeris identity",
        provisional_identity_label=provisional_label,
        final_identity_label=last_label,
        iterations=_EPHEMERIS_IDENTITY_MAX_ITERATIONS,
        source_product=resolved.source_product,
    )


def _ephemeris_delta_t(
    jd_ut1: float,
    reader: KernelReader,
    *,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
    snapshot=None,
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

    raw_jd_tt = math.fsum((float(jd_ut1), resolved.seconds / 86400.0))
    raw_tdb = _tt_to_tdb_with_receipt(raw_jd_tt).epoch_tdb
    identity = _reader_identity_at(reader, raw_tdb, snapshot=snapshot)
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
    corrected_jd_tt = math.fsum((float(jd_ut1), seconds / 86400.0))
    corrected_tdb = _tt_to_tdb_with_receipt(corrected_jd_tt).epoch_tdb
    corrected_identity = _reader_identity_at(
        reader, corrected_tdb, snapshot=snapshot
    )
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
    snapshot=None,
) -> float:
    """Convert UT1 to the TT coordinate consumed by ``reader``."""

    bound = _ephemeris_delta_t(
        jd_ut1,
        reader,
        year=year,
        delta_t_policy=delta_t_policy,
        snapshot=snapshot,
    )
    return jd_ut1 + bound.seconds / 86400.0


def _ephemeris_tt_to_ut1(
    jd_tt: float,
    reader: KernelReader,
    *,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
    snapshot=None,
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
            snapshot=snapshot,
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
        snapshot=snapshot,
    )
    tolerance = 4.0 * math.ulp(max(1.0, abs(jd_tt)))
    if abs(recovered_tt - jd_tt) > tolerance:
        raise RuntimeError("ephemeris TT-to-UT1 inversion did not converge")
    return jd_ut1
