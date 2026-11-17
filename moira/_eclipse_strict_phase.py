"""Opt-in checked-RN mean-ecliptic phase from bounded SPK snapshots.

This policy uses exact-rational rounding checks, mathematical sin/cos, and
the strict scalar native snapshot evaluator. It is separate from the legacy
``planet_at`` route: it reduces directly to the FW or Vondrak/P03 mean ecliptic and
returns the exact determinant and dot of its rounded projected vectors,
without platform atan2, nutation or an angle. It is not a bitwise legacy
phase evaluator, a source/build attestation, or a complete search proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from . import julian
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_phase_astro import ConditionalPhasePlanetaryBounds
from ._eclipse_phase_exclusion import ConditionalPhaseExclusion
from ._eclipse_strict_trig import _bits, _checked_round, strict_scalar_sin_cos
from ._eclipse_variable_spk_bounds import guarded_variable_scalar_snapshot_evaluate
from .constants import ARCSEC2RAD, C_KM_PER_DAY, DEG2RAD


class EclipseStrictPhaseUnavailable(EnclosureUnavailable):
    """The opt-in strict phase policy cannot evaluate this bounded sample."""


@dataclass(frozen=True, slots=True)
class StrictMeanPhaseSample:
    """One snapshot phase with its exact projected determinant and dot."""

    tt_jd: float
    tdb_jd: float
    sun_ecliptic_xy: tuple[float, float]
    moon_ecliptic_xy: tuple[float, float]
    cross_km2: Fraction
    dot_km2: Fraction
    sun_iterations: int
    moon_iterations: int
    snapshot_hashes: tuple[str, ...]
    platform_sin_cos_or_atan2_required: bool = False
    native_snapshot_build_independently_attested: bool = False
    source_and_kernel_attested: bool = False
    legacy_phase_evaluator_attested: bool = False
    ut1_enclosed: bool = False
    complete_search_certified: bool = False


@dataclass(frozen=True, slots=True)
class StrictMeanPhaseEvidence:
    """A strict sample checked against error-widened reference boxes."""

    bounds: ConditionalPhaseExclusion
    sample: StrictMeanPhaseSample
    sample_contained_in_error_widened_reference: bool = True
    entire_strict_policy_proved: bool = False
    legacy_phase_evaluator_attested: bool = False
    complete_search_certified: bool = False


def _f(value: float) -> Fraction:
    return Fraction.from_float(value)


def _add(a: float, b: float) -> float:
    if a == 0.0 and b == 0.0 and (_bits(a) >> 63) and (_bits(b) >> 63):
        return -0.0
    return _checked_round(_f(a) + _f(b))


def _mul(a: float, b: float) -> float:
    if a == 0.0 or b == 0.0:
        return -0.0 if (_bits(a) ^ _bits(b)) >> 63 else 0.0
    return _checked_round(_f(a) * _f(b))


def _div(a: float, b: float) -> float:
    if b == 0.0:
        raise EclipseStrictPhaseUnavailable("strict phase division by zero")
    if a == 0.0:
        return -0.0 if (_bits(a) ^ _bits(b)) >> 63 else 0.0
    return _checked_round(_f(a) / _f(b))


def _sqrt(value: float) -> float:
    if value < 0:
        raise EclipseStrictPhaseUnavailable("strict phase sqrt outside domain")
    if value == 0.0:
        return value
    for precision in (128, 256, 512, 1024, 2048):
        bounds = I.point(value).sqrt(precision)
        low, high = _checked_round(bounds.lo), _checked_round(bounds.hi)
        if _bits(low) == _bits(high):
            return low
    raise EclipseStrictPhaseUnavailable("strict phase sqrt rounding unresolved")


def _norm(vector: tuple[float, float, float]) -> float:
    return _sqrt(_add(_add(_mul(vector[0], vector[0]), _mul(vector[1], vector[1])), _mul(vector[2], vector[2])))


def _strict_tdb(tt: float) -> float:
    """NAIF single-part fixed point with checked RN and strict scalar trig."""
    epoch = tt
    previous = None
    for _ in range(julian._TT_TDB_FIXED_POINT_MAX_ITERATIONS):
        seconds = _mul(_add(epoch, -julian.J2000), 86400.0)
        mean = _add(julian._NAIF_DELTET_M0_RADIANS,
                    _mul(julian._NAIF_DELTET_M1_RADIANS_PER_SECOND, seconds))
        quotient = round(_f(mean) / _f(math.tau))
        remainder = _f(mean) - quotient * _f(math.tau)
        mean = -0.0 if remainder == 0 and (_bits(mean) >> 63) else _checked_round(remainder)
        eccentric = _add(mean, _mul(julian._NAIF_DELTET_EB, strict_scalar_sin_cos(mean).sine))
        offset = _mul(julian._NAIF_DELTET_K_SECONDS, strict_scalar_sin_cos(eccentric).sine)
        epoch = _add(tt, _div(offset, 86400.0))
        if previous is not None and abs(_add(offset, -previous)) <= julian._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS:
            return epoch
        previous = offset
    raise EclipseStrictPhaseUnavailable("strict TT-to-TDB fixed point did not converge")


def _aberration(vector, velocity):
    distance = _norm(vector)
    if distance < 1e-10:
        return vector
    direction = tuple(_div(v, distance) for v in vector)
    beta = tuple(_div(v, C_KM_PER_DAY) for v in velocity)
    beta2 = _add(_add(_mul(beta[0], beta[0]), _mul(beta[1], beta[1])), _mul(beta[2], beta[2]))
    gamma = _div(1.0, _sqrt(_add(1.0, -beta2)))
    dot = _add(_add(_mul(direction[0], beta[0]), _mul(direction[1], beta[1])), _mul(direction[2], beta[2]))
    factor1 = _add(1.0, _div(dot, _add(1.0, gamma)))
    factor2 = _mul(gamma, _add(1.0, dot))
    apparent = tuple(_div(_add(u, _mul(factor1, v)), factor2) for u, v in zip(direction, beta))
    scale = _div(distance, _norm(apparent))
    return tuple(_mul(x, scale) for x in apparent)


def _mean_frame(tt: float):
    def centuries(jd):
        return _div(_add(jd, -2451545.0), 36525.0)

    def poly(t, coeffs):
        total = coeffs[0]
        for n, coefficient in enumerate(coeffs[1:], 1):
            total = _add(total, _mul(coefficient, _checked_round(_f(t) ** n)))
        return total

    def eps(jd):
        return _div(poly(centuries(jd), (84381.406, -46.836769, -0.0001831,
                                        0.00200340, -0.000000576, -0.0000000434)), 3600.0)

    def rx(angle):
        trig = strict_scalar_sin_cos(angle)
        s, c = trig.sine, trig.cosine
        return ((1.0, 0.0, 0.0), (0.0, c, s), (0.0, -s, c))

    def rz(angle):
        trig = strict_scalar_sin_cos(angle)
        s, c = trig.sine, trig.cosine
        return ((c, s, 0.0), (-s, c, 0.0), (0.0, 0.0, 1.0))

    def matmul(a, b):
        return tuple(tuple(_add(_add(_mul(a[i][0], b[0][j]), _mul(a[i][1], b[1][j])),
                                _mul(a[i][2], b[2][j])) for j in range(3)) for i in range(3))

    t = centuries(tt)
    if abs(t) > 50:
        from ._eclipse_strict_vondrak import strict_vondrak_precession_matrix

        precession = strict_vondrak_precession_matrix(tt)
        return matmul(rx(_mul(eps(tt), DEG2RAD)), precession)
    gamb = _mul(poly(t, (-0.052928, 10.556378, 0.4932044, -0.00031238, -0.000002788, 0.0000000260)), ARCSEC2RAD)
    phib = _mul(poly(t, (84381.412819, -46.811016, 0.0511268, 0.00053289, -0.000000440, -0.0000000176)), ARCSEC2RAD)
    psib = _mul(poly(t, (-0.041775, 5038.481484, 1.5584175, -0.00018522, -0.000026452, -0.0000000148)), ARCSEC2RAD)
    reconstructed = _add(2451545.0, _mul(t, 36525.0))
    epsa = _mul(eps(reconstructed), _div(math.pi, 180.0))
    precession = matmul(rx(-epsa), matmul(rz(-psib), matmul(rx(phib), rz(gamb))))
    return matmul(rx(_mul(eps(tt), DEG2RAD)), precession)


def evaluate_strict_mean_phase(bounds: ConditionalPhasePlanetaryBounds, tt_jd: float) -> StrictMeanPhaseSample:
    """Evaluate a bounded TT instant from the exact same SPK coefficient copies."""
    if not isinstance(bounds, ConditionalPhasePlanetaryBounds):
        raise TypeError("conditional planetary-vector bounds required")
    if isinstance(tt_jd, bool) or not isinstance(tt_jd, (int, float)) or not math.isfinite(tt_jd):
        raise ValueError("finite TT sample required")
    tt = float(tt_jd)
    if not bounds.tt_offset_days.contains(_f(tt) - _f(bounds.tt_anchor_jd)):
        raise ValueError("TT sample lies outside the bounded reception interval")
    if len(bounds.spk_usages) != 34:
        raise EclipseStrictPhaseUnavailable("strict phase requires unsplit positive-delay snapshot receipts")
    tdb = _strict_tdb(tt)
    if not bounds.tdb.tdb_offset_days.contains(_f(tdb) - _f(bounds.tt_anchor_jd)):
        raise ArithmeticError("strict TT-to-TDB escaped its conditional time box")
    hashes = []

    def state(index, center, target, offset):
        receipt = bounds.spk_usages[index]
        if (receipt.source.center, receipt.source.target) != (center, target):
            raise EclipseStrictPhaseUnavailable("strict phase snapshot route changed")
        sample = guarded_variable_scalar_snapshot_evaluate(receipt, tdb, offset)
        hashes.append(sample.record_snapshot_sha256)
        return sample

    emb, earth_leg = state(0, 0, 3, 0.0), state(1, 3, 399, 0.0)
    initial_sun, moon_leg = state(2, 0, 10, 0.0), state(3, 3, 301, 0.0)
    earth = tuple(_add(a, b) for a, b in zip(emb.position_km, earth_leg.position_km))
    velocity = tuple(_add(a, b) for a, b in zip(emb.velocity_km_per_day, earth_leg.velocity_km_per_day))
    moon_initial = tuple(_add(a, b) for a, b in zip(emb.position_km, moon_leg.position_km))

    def light_time(initial, start, pairs):
        xyz = tuple(_add(a, -b) for a, b in zip(initial, earth))
        delay = _div(_norm(xyz), C_KM_PER_DAY)
        for iteration in range(10):
            total = (0.0, 0.0, 0.0)
            for index, (center, target) in enumerate(pairs):
                emitted = state(start + iteration * len(pairs) + index, center, target, -delay).position_km
                total = tuple(_add(a, b) for a, b in zip(total, emitted))
            xyz = tuple(_add(a, -b) for a, b in zip(total, earth))
            next_delay = _div(_norm(xyz), C_KM_PER_DAY)
            if abs(_add(next_delay, -delay)) < 1e-14:
                return xyz, iteration + 1
            delay = next_delay
        return xyz, 10

    sun, sun_n = light_time(initial_sun.position_km, 4, ((0, 10),))
    moon, moon_n = light_time(moon_initial, 14, ((0, 3), (3, 301)))
    sun, moon = _aberration(sun, velocity), _aberration(moon, velocity)
    frame = _mean_frame(tt)

    def project(vector):
        return tuple(_add(_add(_mul(row[0], vector[0]), _mul(row[1], vector[1])), _mul(row[2], vector[2]))
                     for row in frame[:2])

    s, m = project(sun), project(moon)
    cross = _f(s[0]) * _f(m[1]) - _f(s[1]) * _f(m[0])
    dot = _f(s[0]) * _f(m[0]) + _f(s[1]) * _f(m[1])
    return StrictMeanPhaseSample(tt, tdb, s, m, cross, dot, sun_n, moon_n, tuple(hashes))


def evaluate_verified_strict_mean_phase(bounds: ConditionalPhaseExclusion, tt_jd: float) -> StrictMeanPhaseEvidence:
    """Check one strict snapshot sample against error-widened reference bounds.

    This establishes containment of that computed sample, not a global proof
    of the strict policy or attestation of the native binary/source.
    """
    if not isinstance(bounds, ConditionalPhaseExclusion):
        raise TypeError("conditional phase bounds required")
    sample = evaluate_strict_mean_phase(bounds.vector_bounds, tt_jd)
    margin = bounds.error_margin_km2
    cross = I(bounds.cross_km2.lo - margin, bounds.cross_km2.hi + margin)
    dot = I(bounds.dot_km2.lo - margin, bounds.dot_km2.hi + margin)
    if not cross.contains(sample.cross_km2) or not dot.contains(sample.dot_km2):
        raise ArithmeticError("strict phase sample escaped its error-widened reference boxes")
    if bounds.new_residual_sign is not None and sample.cross_km2 * bounds.new_residual_sign <= 0:
        raise ArithmeticError("strict phase sample contradicts conditional New Moon sign")
    if bounds.full_residual_sign is not None and sample.cross_km2 * bounds.full_residual_sign >= 0:
        raise ArithmeticError("strict phase sample contradicts conditional Full Moon sign")
    return StrictMeanPhaseEvidence(bounds, sample)
