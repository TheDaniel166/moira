"""Conditional phase-residual exclusion on the Fukushima–Williams branch.

This is a private, successful-output-only calculation under the explicit,
unattested premises in its receipt and proof below. It is not wired into
eclipse search and is not an unconditional certificate. Vondrak, UT1/TT,
kernel identity, loaded binary identity and physical accuracy are not proved.

For the conservative error budget let u=2**-53 and V be an upper bound on
the absolute components of a vector, with 1 <= V <= 10**12. Assume the
actual FW matrix entries are <=2, floating operations are RN binary64 with
gradual underflow and no reassociation, sin/cos absolute error <=2u, and all
intermediates are finite. For magnitudes bounded by B>=1, one operation's
absolute error is <2uB, including subnormal rounding. A three-term matrix
product with factors bounded by 2 has arithmetic error <64u per entry.

Writing the exact nutation rotation as Rx(-e) Rz(-d) Rx(e0), each elementary
rotation differs from its real counterpart by <=2u per entry. The first
product differs by <64u; the second differs by <256u per entry. Multiplying
by the actual represented FW matrix adds <3*256u*2 + 64u < 2048u per entry.
Applying that matrix to a vector adds <3*2048u*V + 128u*V < 8192u*V per
component. The final ecliptic Rx(e) and its rounded projection add less than
another 8192u*V; using 100000u*V per XY component also covers the separately
rounded mean-ecliptic reference matrix. This bound includes either FMA or
separate operations because each outward interval retains the exact product.

The ideal projected XY norm is at most 11V: every component of P*v is <=6V,
and exact rotations preserve its Euclidean norm. The admitted reference
projection has at least one component >=V/10; the above perturbation and the
reference-matrix error keep the actual XY norm positive and below 12V. The
cross-product perturbation is less than 2**-29 * V_s * V_m, including both
vector errors and reference-matrix rounding. The reference determinant uses
the first two rows directly; it does not assume the represented FW or mean
matrix is exactly orthogonal.

For atan2 assume absolute error <=2**-45 radians. Require Python's represented
modulo by 360 to have circular error <=2**-42 degrees, including its 360-to-0
clamp, and standard RN arithmetic. The represented radians-to-degrees constant
has error <2**-40 degree/radian, checked below using a rational pi bracket.
Each longitude is in [0,360]; every subtraction/addition and modulo in the
actual phase and window residual is on magnitude <=720 degrees. Even 32
allowances of 2**-40 degrees plus the two atan2 errors stay below 2**-36
radians of circular angular error. This covers zero, 180, 360 and signed-zero
wraps. Consequently a returned zero residual implies actual XY cross-product
magnitude <=144*2**-36*V_s*V_m. Adding frame error is strictly below
2**-24*V_s*V_m. A cross interval outside that margin excludes zero on both
new/full branches, under all premises; every other outcome is unresolved.
The same margin bounds error in the projected dot product. When cross and dot
both exclude that margin, their signs identify one branch whose represented
residual has a single strict sign throughout: cross sign for New Moon when
dot is positive, and negative cross sign for Full Moon when dot is negative.
The other branch is left unresolved because its angular wrap can reverse sign.
The modeled route is the default geocentric-ecliptic Python ``planet_at``
reduction, its direct SpkReader type-2 routes, guarded planetary light-time,
native aberration/matrix helpers and shared deterministic apparent context.
Alternative readers, accelerated or modified reduction routes are not
attested or admitted. The two planet calls must use identical represented TT,
nutation and obliquity results. Zero exclusion alone does not exclude a sign
change between adjacent represented times or establish event ordering.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_phase_aberration import bound_phase_aberration
from ._eclipse_phase_astro import ConditionalPhasePlanetaryBounds, bound_phase_planetary_vectors
from ._eclipse_phase_pole import bound_fw_mean_ecliptic_pole, bound_mean_ecliptic_projection
from .constants import RAD2DEG


class EclipsePhaseExclusionUnavailable(EnclosureUnavailable):
    """A conditional phase proof's domain or premise cannot be established."""


@dataclass(frozen=True, slots=True)
class ConditionalPhaseExclusion:
    """Zero-residual evidence with unverified assumptions explicitly retained."""

    tt_anchor_jd: float
    tt_offset_days: I
    cross_km2: I
    dot_km2: I
    error_margin_km2: Fraction
    status: str
    new_residual_sign: int | None
    full_residual_sign: int | None
    vector_bounds: ConditionalPhasePlanetaryBounds
    arithmetic_premises: str = (
        "binary64 RN/gradual; fsum <=1 ulp; correctly rounded native FMA and sqrt; "
        "correctly rounded integer powers, including Python wrapper square; no unsafe reassociation; "
        "sin/cos absolute error <=2**-52; atan2 absolute error <=2**-45 radians; "
        "modulo circular error <=2**-42 degrees"
    )
    guarded_tt_tdb_and_planetary_light_time_required: bool = True
    identical_tt_and_frame_context_required: bool = True
    unchanged_source_kernel_and_constants_required: bool = True
    execution_environment_attested: bool = False
    native_build_and_loaded_image_attested: bool = False
    source_and_kernel_attested: bool = False
    ut1_enclosed: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False


def bound_fw_phase_zero_exclusion(reader, tt_anchor_jd: float, tt_offset_days: I) -> ConditionalPhaseExclusion:
    """Conditionally exclude both phase zero residuals over represented TT.

    A result of ``excluded`` is conditional on the unverified premises; an
    ``unresolved`` result does not establish a crossing. Provider failures,
    branch ambiguity and resource/domain limits raise EnclosureUnavailable.
    """
    # 3.141592653589793 < pi < 3.141592653589794. This intentionally loose
    # rational bracket still checks the represented conversion constant.
    pi_lo = Fraction(3141592653589793, 10**15)
    pi_hi = Fraction(3141592653589794, 10**15)
    conversion = Fraction.from_float(RAD2DEG)
    if max(abs(conversion - 180 / pi_lo), abs(conversion - 180 / pi_hi)) >= Fraction(1, 2**40):
        raise EclipsePhaseExclusionUnavailable("degree conversion exceeds the proved error budget")
    vectors = bound_phase_planetary_vectors(reader, tt_anchor_jd, tt_offset_days)
    pole = bound_fw_mean_ecliptic_pole(tt_anchor_jd, tt_offset_days)
    if any(entry.magnitude > 2 for row in pole.precession_matrix for entry in row):
        raise EclipsePhaseExclusionUnavailable("FW matrix entry exceeds the proved error domain")
    sun = bound_phase_aberration(vectors.sun_retarded_km, vectors.earth_velocity_km_per_day).position_km
    moon = bound_phase_aberration(vectors.moon_retarded_km, vectors.earth_velocity_km_per_day).position_km

    def peak_and_projection(vector):
        maximum = max(component.magnitude for component in vector)
        minimum = max(Fraction(0) if component.contains_zero else min(abs(component.lo), abs(component.hi))
                      for component in vector)
        if minimum < 1 or maximum > 10**12:
            raise EclipsePhaseExclusionUnavailable("vector magnitude exceeds the proved error domain")
        projected = bound_mean_ecliptic_projection(pole, vector)
        lower = max(Fraction(0) if component.contains_zero else min(abs(component.lo), abs(component.hi))
                    for component in projected[:2])
        if lower < maximum / 10:
            raise EclipsePhaseExclusionUnavailable("ecliptic projection may be degenerate")
        return maximum, projected

    sun_max, sun_projected = peak_and_projection(sun)
    moon_max, moon_projected = peak_and_projection(moon)
    # Use the projected 2D determinant directly. The represented FW matrix
    # is not exactly orthogonal, so its third row is not a substitute for
    # the cross product of the first two represented rows.
    cross = (sun_projected[0] * moon_projected[1] - sun_projected[1] * moon_projected[0]).quantize_outward(128)
    dot = (sun_projected[0] * moon_projected[0] + sun_projected[1] * moon_projected[1]).quantize_outward(128)
    margin = sun_max * moon_max / 2**24
    cross_sign = 1 if cross.lo > margin else -1 if cross.hi < -margin else None
    dot_sign = 1 if dot.lo > margin else -1 if dot.hi < -margin else None
    status = "excluded" if cross_sign is not None else "unresolved"
    new_sign = cross_sign if dot_sign == 1 else None
    full_sign = -cross_sign if dot_sign == -1 and cross_sign is not None else None
    return ConditionalPhaseExclusion(
        float(tt_anchor_jd), tt_offset_days, cross, dot, margin, status, new_sign, full_sign, vectors,
    )
