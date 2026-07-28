"""
Moira -- primary_directions/geometry.py
Standalone geometry owner for the primary-directions subsystem.

Boundary
--------
Owns the explicit computational laws used by the currently admitted
primary-direction method families, plus the compatibility truth surface that
states whether a method owns a distinct admitted runtime law or still uses a
shared narrow law.  Its historical ``sovereignty`` field is not a claim of
whole-subsystem lineage clearance or external-authority validation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from .._strenum import StrEnum
from numbers import Real
from typing import Protocol

from ..constants import DEG2RAD
from .latitudes import PrimaryDirectionLatitudeDoctrine
from .methods import (
    PrimaryDirectionMethod,
    classify_primary_direction_method,
    primary_direction_method_truth,
)
from .spaces import PrimaryDirectionSpace

__all__ = [
    "PrimaryDirectionGeometryLaw",
    "PrimaryDirectionGeometrySovereignty",
    "PrimaryDirectionGeometryTruth",
    "primary_direction_geometry_truth",
    "compute_primary_direction_arc",
    "compute_primary_direction_arcs",
]


_DOMAIN_TOLERANCE = 1e-12


def _checked_unit_argument(value: float, *, object_name: str) -> float:
    """Return a numerically rounded inverse-trig argument or fail closed.

    Values outside the real unit interval describe a missing spherical
    intersection.  Only round-off immediately adjacent to an endpoint may be
    coalesced; a physical no-solution case must not be turned into a tangent.
    """
    if not math.isfinite(value):
        raise ValueError(f"{object_name} requires a finite spherical argument")
    if value < -1.0 - _DOMAIN_TOLERANCE or value > 1.0 + _DOMAIN_TOLERANCE:
        raise ValueError(f"{object_name} has no real spherical solution")
    return max(-1.0, min(1.0, value))


class _SpeculumLike(Protocol):
    """Vessel: Protocol defining the minimum coordinate surface required for mundane geometry computations."""
    name: str
    lon: float
    lat: float
    ra: float
    dec: float
    ha: float
    dsa: float
    nsa: float
    upper: bool
    f: float
    is_eastern: bool


class PrimaryDirectionGeometryLaw(StrEnum):
    """Vessel: Enumeration of specific mathematical laws for primary direction arcs."""
    PLACIDUS_MUNDANE = "placidus_mundane"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"
    PTOLEMAIC_PROPORTIONAL_SEMI_ARC = "ptolemaic_proportional_semi_arc"
    MERIDIAN_EQUATORIAL = "meridian_equatorial"
    REGIOMONTANUS_UNDER_POLE = "regiomontanus_under_pole"
    CAMPANUS_SPECULUM = "campanus_speculum"
    TOPOCENTRIC_UNDER_POLE = "topocentric_under_pole"


class PrimaryDirectionGeometrySovereignty(StrEnum):
    """Compatibility classification for a distinct or shared runtime law.

    ``SOVEREIGN`` is the retained public token for a method-specific admitted
    implementation.  It does not attest historical completeness, lineage
    ownership across all five repository axes, or external-oracle validation.
    """
    SOVEREIGN = "sovereign"
    SHARED_NARROW = "shared_narrow"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionGeometryTruth:
    """Vessel: Record of one method's admitted runtime geometry identity."""
    method: PrimaryDirectionMethod
    law: PrimaryDirectionGeometryLaw
    sovereignty: PrimaryDirectionGeometrySovereignty
    shared_with: tuple[PrimaryDirectionMethod, ...] = ()

    def __post_init__(self) -> None:
        if self.sovereignty is PrimaryDirectionGeometrySovereignty.SOVEREIGN and self.shared_with:
            raise ValueError(
                "PrimaryDirectionGeometryTruth invariant failed: sovereign law may not declare shared_with"
            )
        if self.sovereignty is PrimaryDirectionGeometrySovereignty.SHARED_NARROW and not self.shared_with:
            raise ValueError(
                "PrimaryDirectionGeometryTruth invariant failed: shared narrow law must declare shared_with"
            )


def primary_direction_geometry_truth(
    method: PrimaryDirectionMethod,
) -> PrimaryDirectionGeometryTruth:
    mapping = {
        PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            law=PrimaryDirectionGeometryLaw.PLACIDUS_MUNDANE,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            law=PrimaryDirectionGeometryLaw.PTOLEMAIC_PROPORTIONAL_SEMI_ARC,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            law=PrimaryDirectionGeometryLaw.PLACIDIAN_CLASSIC_SEMI_ARC,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
        PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.MERIDIAN,
            law=PrimaryDirectionGeometryLaw.MERIDIAN_EQUATORIAL,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
        PrimaryDirectionMethod.MORINUS: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.MORINUS,
            law=PrimaryDirectionGeometryLaw.REGIOMONTANUS_UNDER_POLE,
            sovereignty=PrimaryDirectionGeometrySovereignty.SHARED_NARROW,
            shared_with=(PrimaryDirectionMethod.REGIOMONTANUS,),
        ),
        PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            law=PrimaryDirectionGeometryLaw.REGIOMONTANUS_UNDER_POLE,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
        PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.CAMPANUS,
            law=PrimaryDirectionGeometryLaw.CAMPANUS_SPECULUM,
            sovereignty=PrimaryDirectionGeometrySovereignty.SHARED_NARROW,
            shared_with=(PrimaryDirectionMethod.REGIOMONTANUS,),
        ),
        PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.TOPOCENTRIC,
            law=PrimaryDirectionGeometryLaw.TOPOCENTRIC_UNDER_POLE,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
    }
    return mapping[method]


def _required_ha(f: float, dsa: float, nsa: float) -> float:
    if abs(f) <= 1.0:
        return f * dsa
    if f > 1.0:
        return dsa + (f - 1.0) * nsa
    return -dsa - (-f - 1.0) * nsa


def _mundane_arc(sig: _SpeculumLike, prom: _SpeculumLike) -> float:
    req_ha = _required_ha(sig.f, prom.dsa, prom.nsa)
    return req_ha - prom.ha


def _placidian_mundane_position(significator: _SpeculumLike, armc: float) -> float:
    if significator.upper:
        if significator.dsa <= 1e-9:
            raise ValueError("Placidian mundane position requires a non-zero diurnal semi-arc")
        ratio = abs(significator.ha) / significator.dsa
        if significator.is_eastern:
            return (armc + 90.0 * ratio) % 360.0
        return (armc - 90.0 * ratio) % 360.0

    if significator.nsa <= 1e-9:
        raise ValueError("Placidian mundane position requires a non-zero nocturnal semi-arc")
    lower_md = abs(abs(significator.ha) - significator.dsa)
    ratio = lower_md / significator.nsa
    if ratio > 1.0 + _DOMAIN_TOLERANCE:
        raise ValueError("Placidian mundane position lies outside its nocturnal quadrant")

    # Mundane position is one continuous four-quadrant coordinate.  The lower
    # eastern quadrant begins at the eastern horizon (ARMC + 90) and advances
    # to the IC (ARMC + 180); the lower western quadrant begins at the western
    # horizon (ARMC - 90) and advances in the opposite sense to the same IC.
    # Starting the interpolation at the IC reverses both quadrants and creates
    # a 90-degree jump at each horizon.
    if significator.is_eastern:
        return (armc + 90.0 * (1.0 + ratio)) % 360.0
    return (armc - 90.0 * (1.0 + ratio)) % 360.0


def _placidian_classic_semi_arc_arc(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    oa_asc: float,
    armc: float,
    geo_lat: float,
) -> float:
    mp_sig = _placidian_mundane_position(sig, armc)
    phi = geo_lat * DEG2RAD
    dec = prom.dec * DEG2RAD
    offset = (oa_asc - mp_sig) * DEG2RAD
    term = _checked_unit_argument(
        math.tan(dec) * math.tan(phi) * math.cos(offset),
        object_name="Placidian classic semi-arc endpoint",
    )
    ra_end = (math.degrees(math.asin(term)) + mp_sig) % 360.0
    return (prom.ra - ra_end) % 360.0


def _meridian_distance(entry: _SpeculumLike) -> float:
    if entry.upper:
        return abs(entry.ha)
    return 180.0 - abs(entry.ha)


def _semi_arc(entry: _SpeculumLike) -> float:
    return entry.dsa if entry.upper else entry.nsa


def _ptolemaic_proportional_semi_arc_arc(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
) -> float:
    """
    Ptolemy / semi-arc on the current admitted branch.

    Governing law:
    - PD = MD(sig) / SA(sig)
    - PP = SA(prom) * PD
    - arc = PP - MD(prom) if the promissor moves away from the meridian
    - arc = MD(prom) - PP if the promissor moves toward the meridian
    """
    sig_sa = _semi_arc(sig)
    prom_sa = _semi_arc(prom)
    if sig_sa <= 1e-9 or prom_sa <= 1e-9:
        raise ValueError("Ptolemaic proportional semi-arc requires non-zero semi-arcs")
    proportional_distance = _meridian_distance(sig) / sig_sa
    projected_position = prom_sa * proportional_distance
    prom_md = _meridian_distance(prom)
    moving_away_from_meridian = (prom.upper and prom.is_western) or (
        (not prom.upper) and prom.is_eastern
    )
    if moving_away_from_meridian:
        direct = projected_position - prom_md
    else:
        direct = prom_md - projected_position
    return direct % 360.0


def _ptolemaic_ascensional_difference(entry: _SpeculumLike, *, geo_lat: float) -> float:
    phi = geo_lat * DEG2RAD
    dec = entry.dec * DEG2RAD
    term = _checked_unit_argument(
        math.tan(dec) * math.tan(phi),
        object_name="Ptolemaic ascensional difference",
    )
    return math.degrees(math.asin(term))


def _ptolemaic_oblique_ascension(entry: _SpeculumLike, *, geo_lat: float) -> float:
    ad = _ptolemaic_ascensional_difference(entry, geo_lat=geo_lat)
    # AD already carries the sign of geographic latitude through tan(phi).
    return (entry.ra - ad) % 360.0


def _ptolemaic_oblique_descension(entry: _SpeculumLike, *, geo_lat: float) -> float:
    ad = _ptolemaic_ascensional_difference(entry, geo_lat=geo_lat)
    return (entry.ra + ad) % 360.0


def _ptolemaic_angular_arc(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    armc: float,
    geo_lat: float,
) -> float | None:
    if sig.name == "MC":
        return (prom.ra - armc) % 360.0
    if sig.name == "IC":
        return (prom.ra - ((armc + 180.0) % 360.0)) % 360.0
    if sig.name == "ASC":
        oa_asc = (armc + 90.0) % 360.0
        return (_ptolemaic_oblique_ascension(prom, geo_lat=geo_lat) - oa_asc) % 360.0
    if sig.name == "DSC":
        oa_asc = (armc + 90.0) % 360.0
        return (_ptolemaic_oblique_descension(prom, geo_lat=geo_lat) - oa_asc) % 360.0
    return None


def _shared_campanus_regio_sin_zenith_distance(
    entry: _SpeculumLike,
    *,
    geo_lat: float,
) -> float:
    """Sine of the angle between the meridian and the body's house circle.

    In the admitted Campanus-Regiomontanus conjunction geometry, the house
    circle is the great-circle plane through the body and the north-south
    horizon axis.  In meridian-centred equatorial coordinates, the angle
    between that plane and the meridian has components

        transverse = cos(dec) sin(HA)
        meridional = cos(phi) cos(dec) cos(HA) + sin(phi) sin(dec).

    Their ``hypot`` ratio is the branch-independent ``sin(ZD)`` required by
    ``sin(pole) = sin(phi) sin(ZD)``.  This vector/plane invariant remains
    continuous through MD=90, unlike a chain of principal ``atan(tan(...))``
    reductions.
    """
    if not math.isfinite(geo_lat) or not -90.0 < geo_lat < 90.0:
        raise ValueError("Campanus-Regiomontanus geometry requires geographic latitude in (-90, 90)")
    if not math.isfinite(entry.dec) or not math.isfinite(entry.ha):
        raise ValueError("Campanus-Regiomontanus geometry requires finite equatorial coordinates")

    phi = geo_lat * DEG2RAD
    dec = entry.dec * DEG2RAD
    ha = entry.ha * DEG2RAD
    transverse = math.cos(dec) * math.sin(ha)
    meridional = (
        math.cos(phi) * math.cos(dec) * math.cos(ha)
        + math.sin(phi) * math.sin(dec)
    )
    plane_norm = math.hypot(transverse, meridional)
    if plane_norm <= 1e-15:
        raise ValueError("Campanus-Regiomontanus house circle is singular at the horizon axis")
    return abs(transverse) / plane_norm


def _shared_campanus_regio_pole(entry: _SpeculumLike, *, geo_lat: float) -> float:
    phi = geo_lat * DEG2RAD
    sin_zd = _shared_campanus_regio_sin_zenith_distance(entry, geo_lat=geo_lat)
    pole_argument = _checked_unit_argument(
        math.sin(phi) * sin_zd,
        object_name="Campanus-Regiomontanus pole",
    )
    pole = math.asin(pole_argument)
    return math.degrees(pole)


def _under_pole_w(entry: _SpeculumLike, pole_deg: float, *, eastern: bool) -> float:
    dec = entry.dec * DEG2RAD
    pole = pole_deg * DEG2RAD
    offset_argument = _checked_unit_argument(
        math.tan(dec) * math.tan(pole),
        object_name="Oblique ascension under pole",
    )
    offset = math.asin(offset_argument)
    if eastern:
        return (entry.ra - math.degrees(offset)) % 360.0
    return (entry.ra + math.degrees(offset)) % 360.0


def _under_pole_arc(sig: _SpeculumLike, prom: _SpeculumLike, *, pole_deg: float) -> float:
    eastern = sig.is_eastern
    w_sig = _under_pole_w(sig, pole_deg, eastern=eastern)
    w_prom = _under_pole_w(prom, pole_deg, eastern=eastern)
    return (w_prom - w_sig) % 360.0


def _regiomontanus_under_pole_arc(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    geo_lat: float,
) -> float:
    return _under_pole_arc(sig, prom, pole_deg=_shared_campanus_regio_pole(sig, geo_lat=geo_lat))


def _campanus_under_pole_arc(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    geo_lat: float,
) -> float:
    return _under_pole_arc(sig, prom, pole_deg=_shared_campanus_regio_pole(sig, geo_lat=geo_lat))


def _topocentric_pole(entry: _SpeculumLike, *, geo_lat: float) -> float:
    sa = _semi_arc(entry)
    if sa <= 1e-9:
        raise ValueError("Topocentric pole requires a non-zero semi-arc")
    md_ratio = _meridian_distance(entry) / sa
    phi = geo_lat * DEG2RAD
    return math.degrees(math.atan(md_ratio * math.tan(phi)))


def _topocentric_under_pole_arc(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    geo_lat: float,
) -> float:
    return _under_pole_arc(sig, prom, pole_deg=_topocentric_pole(sig, geo_lat=geo_lat))


def _zodiacal_longitude_arc(sig: _SpeculumLike, prom: _SpeculumLike) -> float:
    return (sig.lon - prom.lon) % 360.0


def _zodiacal_projected_arc(sig: _SpeculumLike, prom: _SpeculumLike) -> float:
    return (sig.ra - prom.ra) % 360.0


def _equatorial_arc(sig: _SpeculumLike, prom: _SpeculumLike) -> float:
    return (sig.ra - prom.ra) % 360.0


def _primary_direction_arc(
    method: PrimaryDirectionMethod,
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    space: PrimaryDirectionSpace,
    latitude_doctrine: PrimaryDirectionLatitudeDoctrine,
    geo_lat: float,
    armc: float,
    oa_asc: float,
) -> float:
    """The single arc of direction the primum mobile turns to carry ``prom`` to
    the circle of position of ``sig`` under the active geometry law.

    This is the ordered geometry primitive. Traditional converse applies it a
    second time with significator and promissor roles exchanged (see
    ``compute_primary_direction_arcs``); signed-primary-motion doctrine instead
    classifies this one result by its signed shortest circular displacement.
    """
    if method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
        angular = _ptolemaic_angular_arc(sig, prom, armc=armc, geo_lat=geo_lat)
        if angular is not None:
            return angular

    if space is PrimaryDirectionSpace.IN_ZODIACO:
        if method in (
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.MORINUS,
        ):
            return _regiomontanus_under_pole_arc(sig, prom, geo_lat=geo_lat)
        if method is PrimaryDirectionMethod.CAMPANUS:
            return _campanus_under_pole_arc(sig, prom, geo_lat=geo_lat)
        if method is PrimaryDirectionMethod.TOPOCENTRIC:
            return _topocentric_under_pole_arc(sig, prom, geo_lat=geo_lat)
        if method is PrimaryDirectionMethod.MERIDIAN:
            return _equatorial_arc(sig, prom)
        if method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
            return _ptolemaic_proportional_semi_arc_arc(sig, prom)
        if latitude_doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED:
            return _zodiacal_longitude_arc(sig, prom)
        return _zodiacal_projected_arc(sig, prom)

    if method in (
        PrimaryDirectionMethod.REGIOMONTANUS,
        PrimaryDirectionMethod.MORINUS,
    ):
        return _regiomontanus_under_pole_arc(sig, prom, geo_lat=geo_lat)
    if method is PrimaryDirectionMethod.CAMPANUS:
        return _campanus_under_pole_arc(sig, prom, geo_lat=geo_lat)
    if method is PrimaryDirectionMethod.TOPOCENTRIC:
        return _topocentric_under_pole_arc(sig, prom, geo_lat=geo_lat)
    if method is PrimaryDirectionMethod.MERIDIAN:
        return _equatorial_arc(sig, prom)
    if method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
        return _ptolemaic_proportional_semi_arc_arc(sig, prom)
    if method in (
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
    ):
        return _placidian_classic_semi_arc_arc(
            sig,
            prom,
            oa_asc=oa_asc,
            armc=armc,
            geo_lat=geo_lat,
        )
    return _mundane_arc(sig, prom)


def compute_primary_direction_arc(
    method: PrimaryDirectionMethod,
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    space: PrimaryDirectionSpace,
    latitude_doctrine: PrimaryDirectionLatitudeDoctrine,
    geo_lat: float,
    armc: float,
    oa_asc: float,
) -> float:
    """Return one ordered promissor-to-significator arc of primary motion.

    This is the geometry object used by signed-primary-motion doctrine: it
    performs one ordered construction and does not calculate a role-exchanged
    companion arc.
    """
    if not isinstance(method, PrimaryDirectionMethod):
        raise ValueError("Primary-direction geometry requires a typed method")
    if not isinstance(space, PrimaryDirectionSpace):
        raise ValueError("Primary-direction geometry requires a typed space")
    if not isinstance(latitude_doctrine, PrimaryDirectionLatitudeDoctrine):
        raise ValueError("Primary-direction geometry requires a typed latitude doctrine")
    method_classification = classify_primary_direction_method(
        primary_direction_method_truth(method)
    )
    if space is PrimaryDirectionSpace.IN_ZODIACO and not method_classification.zodiacal:
        raise ValueError(
            f"Primary-direction method {method.value!r} does not admit in_zodiaco geometry"
        )
    for name, value in (
        ("geographic latitude", geo_lat),
        ("ARMC", armc),
        ("oblique ascension of the ascendant", oa_asc),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"Primary-direction geometry requires finite real {name}")
    if not -90.0 < float(geo_lat) < 90.0:
        raise ValueError("Primary-direction geometry requires geographic latitude in (-90, 90)")
    return _primary_direction_arc(
        method,
        sig,
        prom,
        space=space,
        latitude_doctrine=latitude_doctrine,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )


def compute_primary_direction_arcs(
    method: PrimaryDirectionMethod,
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    space: PrimaryDirectionSpace,
    latitude_doctrine: PrimaryDirectionLatitudeDoctrine,
    geo_lat: float,
    armc: float,
    oa_asc: float,
) -> tuple[float, float]:
    """Return traditional ``(direct, converse)`` role-exchanged arcs.

    Governing doctrine (J. B. Morin, *Astrologia Gallica* Book 22,
    *De Directionibus*, Section I, Chapter 7): direct and converse are "a single
    operation." The arc is always taken in the circle of position of the
    *preceding* terminus, so the converse arc of significator-to-promissor is the
    direct arc of promissor-to-significator -- the same law with the two roles
    exchanged, not the negation of the direct arc.

    For the symmetric method families (the equatorial Meridian law and the
    zodiacal laws) role exchange coincides with sign reversal, so converse still
    equals ``-direct`` there. For the asymmetric families (the semi-arc and
    under-the-pole laws, whose arc is taken in a terminus-specific circle of
    position) the two constructions differ, and role exchange is the correct one.
    """
    direct = compute_primary_direction_arc(
        method,
        sig,
        prom,
        space=space,
        latitude_doctrine=latitude_doctrine,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    converse = compute_primary_direction_arc(
        method,
        prom,
        sig,
        space=space,
        latitude_doctrine=latitude_doctrine,
        geo_lat=geo_lat,
        armc=armc,
        oa_asc=oa_asc,
    )
    return direct, converse
