"""Conditional Earth-fixed solar vectors over represented UT1/TT boxes.

This composes Moira's served split solar vectors, FW precession, 2000A
nutation amplitude, GAST and tabulated polar motion bounds in the order of
``_earth_fixed_solar_shadow``. All source, native build, library-math and
arithmetic premises remain unattested. These are successful-output bounds for
the selected numerical model, not an event, live-route or physical-accuracy
certificate. UT1 and TT are independent inputs; no conversion is established.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_nutation_amplitudes import bound_conditional_nutation_amplitudes
from ._eclipse_phase_pole import bound_fw_mean_ecliptic_pole
from ._eclipse_polar_motion_bounds import bound_conditional_polar_motion, _trig_rounded
from ._eclipse_sidereal_bounds import bound_conditional_sidereal_time
from ._eclipse_solar_serving import bound_conditional_solar_serving_axis
from .constants import DEG2RAD


class EclipseEarthFixedBoundsUnavailable(EnclosureUnavailable):
    """The selected source route or an orientation branch is not enclosed."""


@dataclass(frozen=True, slots=True)
class ConditionalEarthFixedSolarBounds:
    """Successful-source bounds for selected ITRF shadow vectors.

    The input boxes are independent represented UT1 and TT values. The axis,
    Sun, fundamental-plane point and Besselian basis match the named serving
    source only under the required, unattested numerical and source premises.
    Other shadow fields, route success and eclipse occurrence are not proved.
    """

    ut1_anchor_jd: float
    ut1_offset_days: I
    tt_anchor_jd: float
    tt_offset_days: I
    axis_unit_away_from_sun: tuple[I, I, I]
    sun_xyz_itrf_km: tuple[I, I, I]
    fundamental_plane_point_xyz_km: tuple[I, I, I]
    fundamental_east_unit_itrf: tuple[I, I, I]
    fundamental_north_unit_itrf: tuple[I, I, I]
    gast_degrees: I
    polar_table_sha256: str
    nutation_coefficients_sha256: str
    source_and_arithmetic_attested: bool = False
    split_route_and_successful_source_required: bool = True
    ut1_tt_correspondence_proved: bool = False
    source_route_totality_proved: bool = False
    eclipse_occurrence_certified: bool = False
    event_wide_path_certified: bool = False
    physical_accuracy_certified: bool = False


def _dot(a, b):
    """Enclose the source's three products and left-associated additions."""
    terms = tuple(_rounded(x * y) for x, y in zip(a, b))
    return _rounded(_rounded(terms[0] + terms[1]) + terms[2])


def _matmul(a, b):
    return tuple(tuple(_dot(a[i], tuple(b[k][j] for k in range(3)))
                       for j in range(3)) for i in range(3))


def _matvec(matrix, vector):
    return tuple(_dot(row, vector) for row in matrix)


def _rx(angle):
    sine, cosine = _trig_rounded(angle)
    zero, one = I.point(0), I.point(1)
    return ((one, zero, zero), (zero, cosine, sine), (zero, -sine, cosine))


def _rz(angle):
    sine, cosine = _trig_rounded(angle)
    zero, one = I.point(0), I.point(1)
    return ((cosine, sine, zero), (-sine, cosine, zero), (zero, zero, one))


def _cross(a, b):
    return tuple(_rounded(_rounded(a[i] * b[j]) - _rounded(a[j] * b[i]))
                 for i, j in ((1, 2), (2, 0), (0, 1)))


def _unit(vector):
    norm2 = _dot(vector, vector)
    if norm2.lo <= 0:
        raise EclipseEarthFixedBoundsUnavailable("terrestrial vector norm may vanish")
    norm = _rounded(norm2.sqrt(128))
    if norm.lo <= 0:
        raise EclipseEarthFixedBoundsUnavailable("terrestrial vector norm may round to zero")
    inverse = _rounded(I.point(1) / norm)
    return tuple(_rounded(value * inverse) for value in vector)


def _mean_obliquity_degrees(centuries):
    """Enclose the source's P03 polynomial in its Python operation order."""
    coefficients = (84381.406, -46.836769, -0.0001831,
                    0.00200340, -0.000000576, -0.0000000434)
    value = I.point(coefficients[0])
    for power, coefficient in enumerate(coefficients[1:], 1):
        term = _rounded(I.point(coefficient) * _rounded(centuries ** power))
        value = _rounded(value + term)
    return _rounded(value / I.point(3600.0))


def bound_conditional_earth_fixed_solar_vectors(
    reader, ut1_anchor_jd: float, ut1_offset_days: I,
    tt_anchor_jd: float, tt_offset_days: I, *,
    assume_ieee_arithmetic: bool = False,
    assume_correctly_rounded_integer_powers: bool = False,
    assume_finite_unit_trig_within_one_ulp: bool = False,
    assume_registered_nutation_tables_match: bool = False,
    assume_builtin_sum_error: bool = False,
    assume_correctly_rounded_sqrt: bool = False,
    max_route_calls: int = 40, max_polar_segments: int = 512,
) -> ConditionalEarthFixedSolarBounds:
    """Enclose selected served ITRF vectors on the FW branch.

    Both inputs describe independent represented binary64 UT1 and TT boxes;
    their real-world or conversion relation is not established. All supplied
    premise flags must be explicitly true. They include IEEE binary64 nearest
    and gradual underflow, correctly rounded integer powers/sqrt, finite
    unit-range sine/cosine within one ulp, the solar-axis three-term sum error
    bound, matching registered nutation tables/caches, and unchanged source,
    constants, compiled native route and table contents. ``math.radians`` is
    assumed to multiply by the represented ``math.pi / 180`` constant with
    binary64 rounding. Successful source execution and the split solar route
    are prerequisites, not conclusions. Unresolved branch or norm boxes fail
    closed. FW epochs outside or crossing +/-50 centuries are unsupported.
    """
    flags = (assume_ieee_arithmetic, assume_correctly_rounded_integer_powers,
             assume_finite_unit_trig_within_one_ulp, assume_registered_nutation_tables_match,
             assume_builtin_sum_error, assume_correctly_rounded_sqrt)
    if not all(type(flag) is bool for flag in flags):
        raise TypeError("Earth-fixed arithmetic premises must be booleans")
    if not all(flags):
        raise EclipseEarthFixedBoundsUnavailable("Earth-fixed source and arithmetic premises are required")
    try:
        vectors = bound_conditional_solar_serving_axis(
            reader, tt_anchor_jd, tt_offset_days, max_route_calls=max_route_calls,
            assume_builtin_sum_error=True, assume_correctly_rounded_sqrt=True,
        )
        if vectors.axis.status != "forward":
            raise EclipseEarthFixedBoundsUnavailable("no finite forward solar shadow axis")
        precession = bound_fw_mean_ecliptic_pole(tt_anchor_jd, tt_offset_days)
        nutation = bound_conditional_nutation_amplitudes(
            tt_anchor_jd, tt_offset_days, assume_ieee_arithmetic=True,
            assume_finite_unit_trig=True, assume_registered_tables_and_caches_match=True,
        )
        sidereal = bound_conditional_sidereal_time(
            ut1_anchor_jd, ut1_offset_days, tt_anchor_jd, tt_offset_days,
            nutation.longitude_degrees, assume_ieee_arithmetic=True,
            assume_correctly_rounded_integer_powers=True, assume_finite_unit_trig=True,
        )
        polar = bound_conditional_polar_motion(
            ut1_anchor_jd, ut1_offset_days, max_segments=max_polar_segments,
        )
        eps0 = _mean_obliquity_degrees(precession.centuries)
        eps = _rounded(_rounded(eps0 + nutation.obliquity_degrees) * I.point(DEG2RAD))
        eps0_rad = _rounded(eps0 * I.point(DEG2RAD))
        dpsi_rad = _rounded(nutation.longitude_degrees * I.point(DEG2RAD))
        nutation_matrix = _matmul(_rx(-eps), _matmul(_rz(-dpsi_rad), _rx(eps0_rad)))
        precession_nutation = _matmul(nutation_matrix, precession.precession_matrix)
        gast_rad = _rounded(sidereal.gast_degrees * I.point(math.pi / 180.0))
        sin_gast, cos_gast = _trig_rounded(gast_rad)
        polar_transpose = tuple(tuple(polar.matrix[j][i] for j in range(3)) for i in range(3))

        def tete_to_itrf(vector):
            x = _rounded(_rounded(cos_gast * vector[0]) + _rounded(sin_gast * vector[1]))
            y = _rounded(_rounded(-sin_gast * vector[0]) + _rounded(cos_gast * vector[1]))
            return _matvec(polar_transpose, (x, y, vector[2]))

        def icrf_to_itrf(vector):
            return tete_to_itrf(_matvec(precession_nutation, vector))

        axis = _unit(icrf_to_itrf(vectors.axis.axis_unit))
        sun = icrf_to_itrf(vectors.vectors.sun_retarded_km)
        plane = tuple(_rounded(moon - _rounded(vectors.axis.axis_projection_km * direction))
                      for moon, direction in zip(vectors.vectors.moon_retarded_km, vectors.axis.axis_unit))
        plane = icrf_to_itrf(plane)
        pole = _unit(tete_to_itrf((I.point(0), I.point(0), I.point(1))))
        sunward = tuple(-value for value in axis)
        east = _unit(_cross(pole, sunward))
        north = _unit(_cross(sunward, east))
        return ConditionalEarthFixedSolarBounds(
            float(ut1_anchor_jd), ut1_offset_days, float(tt_anchor_jd), tt_offset_days,
            axis, sun, plane, east, north, sidereal.gast_degrees,
            polar.table_sha256, nutation.coefficient_sha256,
        )
    except (EnclosureUnavailable, IntervalBudgetError, IntervalDomainError,
            OverflowError, ZeroDivisionError) as exc:
        raise EclipseEarthFixedBoundsUnavailable(f"Earth-fixed solar bound unavailable: {exc}") from exc
