"""
Moira -- primary_direction_geometry.py
Standalone primary-direction geometry owner.

Boundary
--------
Owns the explicit computational laws used by the currently admitted
primary-direction method families, plus the truth surface that states whether a
method is mathematically sovereign or still using a shared narrow law.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from .constants import DEG2RAD
from .primary_direction_latitudes import PrimaryDirectionLatitudeDoctrine
from .primary_direction_methods import PrimaryDirectionMethod
from .primary_direction_spaces import PrimaryDirectionSpace

if TYPE_CHECKING:
    from .primary_directions import SpeculumEntry

__all__ = [
    "PrimaryDirectionGeometryLaw",
    "PrimaryDirectionGeometrySovereignty",
    "PrimaryDirectionGeometryTruth",
    "primary_direction_geometry_truth",
    "compute_primary_direction_arcs",
]


class _SpeculumLike(Protocol):
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
    PLACIDUS_MUNDANE = "placidus_mundane"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"
    PTOLEMAIC_PROPORTIONAL_SEMI_ARC = "ptolemaic_proportional_semi_arc"
    MERIDIAN_EQUATORIAL = "meridian_equatorial"
    MORINUS_SHARED_EQUATORIAL = "morinus_shared_equatorial"
    REGIOMONTANUS_UNDER_POLE = "regiomontanus_under_pole"
    CAMPANUS_SPECULUM = "campanus_speculum"
    TOPOCENTRIC_UNDER_POLE = "topocentric_under_pole"


class PrimaryDirectionGeometrySovereignty(StrEnum):
    SOVEREIGN = "sovereign"
    SHARED_NARROW = "shared_narrow"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionGeometryTruth:
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
            law=PrimaryDirectionGeometryLaw.MORINUS_SHARED_EQUATORIAL,
            sovereignty=PrimaryDirectionGeometrySovereignty.SHARED_NARROW,
            shared_with=(PrimaryDirectionMethod.MERIDIAN,),
        ),
        PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            law=PrimaryDirectionGeometryLaw.REGIOMONTANUS_UNDER_POLE,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
        ),
        PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionGeometryTruth(
            method=PrimaryDirectionMethod.CAMPANUS,
            law=PrimaryDirectionGeometryLaw.CAMPANUS_SPECULUM,
            sovereignty=PrimaryDirectionGeometrySovereignty.SOVEREIGN,
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


def _mundane_arcs(sig: _SpeculumLike, prom: _SpeculumLike) -> tuple[float, float]:
    req_ha = _required_ha(sig.f, prom.dsa, prom.nsa)
    direct = req_ha - prom.ha
    converse = -direct
    return direct, converse


def _placidian_mundane_position(significator: _SpeculumLike, armc: float) -> float:
    if significator.upper:
        ratio = abs(significator.ha) / significator.dsa if significator.dsa > 1e-9 else 0.0
        if significator.is_eastern:
            return (armc + 90.0 * ratio) % 360.0
        return (armc - 90.0 * ratio) % 360.0

    ic_ra = (armc + 180.0) % 360.0
    lower_md = abs(abs(significator.ha) - significator.dsa)
    ratio = lower_md / significator.nsa if significator.nsa > 1e-9 else 0.0
    if significator.is_eastern:
        return (ic_ra - 90.0 * ratio) % 360.0
    return (ic_ra + 90.0 * ratio) % 360.0


def _placidian_classic_semi_arc_arcs(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    oa_asc: float,
    armc: float,
    geo_lat: float,
) -> tuple[float, float]:
    mp_sig = _placidian_mundane_position(sig, armc)
    phi = geo_lat * DEG2RAD
    dec = prom.dec * DEG2RAD
    offset = (oa_asc - mp_sig) * DEG2RAD
    term = math.tan(dec) * math.tan(phi) * math.cos(offset)
    term = max(-1.0, min(1.0, term))
    ra_end = (math.degrees(math.asin(term)) + mp_sig) % 360.0
    direct = (prom.ra - ra_end) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _meridian_distance(entry: _SpeculumLike) -> float:
    if entry.upper:
        return abs(entry.ha)
    return 180.0 - abs(entry.ha)


def _semi_arc(entry: _SpeculumLike) -> float:
    return entry.dsa if entry.upper else entry.nsa


def _ptolemaic_proportional_semi_arc_arcs(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
) -> tuple[float, float]:
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
        return 0.0, 0.0
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
    direct %= 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _ptolemaic_ascensional_difference(entry: _SpeculumLike, *, geo_lat: float) -> float:
    phi = geo_lat * DEG2RAD
    dec = entry.dec * DEG2RAD
    term = max(-1.0, min(1.0, math.tan(dec) * math.tan(phi)))
    return math.degrees(math.asin(term))


def _ptolemaic_oblique_ascension(entry: _SpeculumLike, *, geo_lat: float) -> float:
    ad = _ptolemaic_ascensional_difference(entry, geo_lat=geo_lat)
    if geo_lat >= 0.0:
        return (entry.ra - ad) % 360.0
    return (entry.ra + ad) % 360.0


def _ptolemaic_oblique_descension(entry: _SpeculumLike, *, geo_lat: float) -> float:
    ad = _ptolemaic_ascensional_difference(entry, geo_lat=geo_lat)
    if geo_lat >= 0.0:
        return (entry.ra + ad) % 360.0
    return (entry.ra - ad) % 360.0


def _ptolemaic_angular_arcs(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    armc: float,
    geo_lat: float,
) -> tuple[float, float] | None:
    if sig.name == "MC":
        direct = (prom.ra - armc) % 360.0
        return direct, (-direct) % 360.0
    if sig.name == "IC":
        direct = (prom.ra - ((armc + 180.0) % 360.0)) % 360.0
        return direct, (-direct) % 360.0
    if sig.name == "ASC":
        oa_asc = (armc + 90.0) % 360.0
        direct = (_ptolemaic_oblique_ascension(prom, geo_lat=geo_lat) - oa_asc) % 360.0
        return direct, (-direct) % 360.0
    if sig.name == "DSC":
        oa_asc = (armc + 90.0) % 360.0
        direct = (_ptolemaic_oblique_descension(prom, geo_lat=geo_lat) - oa_asc) % 360.0
        return direct, (-direct) % 360.0
    return None


def _shared_campanus_regio_zenith_distance(entry: _SpeculumLike, *, geo_lat: float) -> float:
    md = math.radians(_meridian_distance(entry))
    phi = geo_lat * DEG2RAD
    dec = entry.dec * DEG2RAD
    a = math.atan(math.cos(phi) * math.tan(md))
    b = math.atan(math.tan(phi) * math.cos(md))
    c = b + dec
    f = math.atan(math.sin(phi) * math.sin(md) * math.tan(c))
    return math.degrees(a + f)


def _shared_campanus_regio_pole(entry: _SpeculumLike, *, geo_lat: float) -> float:
    phi = geo_lat * DEG2RAD
    zd = math.radians(_shared_campanus_regio_zenith_distance(entry, geo_lat=geo_lat))
    pole = math.asin(max(-1.0, min(1.0, math.sin(phi) * math.sin(zd))))
    return math.degrees(pole)


def _under_pole_w(entry: _SpeculumLike, pole_deg: float, *, eastern: bool) -> float:
    dec = entry.dec * DEG2RAD
    pole = pole_deg * DEG2RAD
    offset = math.asin(max(-1.0, min(1.0, math.tan(dec) * math.tan(pole))))
    if eastern:
        return (entry.ra - math.degrees(offset)) % 360.0
    return (entry.ra + math.degrees(offset)) % 360.0


def _under_pole_arcs(sig: _SpeculumLike, prom: _SpeculumLike, *, pole_deg: float) -> tuple[float, float]:
    eastern = sig.is_eastern
    w_sig = _under_pole_w(sig, pole_deg, eastern=eastern)
    w_prom = _under_pole_w(prom, pole_deg, eastern=eastern)
    direct = (w_prom - w_sig) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _regiomontanus_under_pole_arcs(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    geo_lat: float,
) -> tuple[float, float]:
    return _under_pole_arcs(sig, prom, pole_deg=_shared_campanus_regio_pole(sig, geo_lat=geo_lat))


def _campanus_under_pole_arcs(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    geo_lat: float,
) -> tuple[float, float]:
    return _under_pole_arcs(sig, prom, pole_deg=_shared_campanus_regio_pole(sig, geo_lat=geo_lat))


def _topocentric_pole(entry: _SpeculumLike, *, geo_lat: float) -> float:
    sa = _semi_arc(entry)
    if sa <= 1e-9:
        return 0.0
    md_ratio = _meridian_distance(entry) / sa
    phi = geo_lat * DEG2RAD
    return math.degrees(math.atan(md_ratio * math.tan(phi)))


def _topocentric_under_pole_arcs(
    sig: _SpeculumLike,
    prom: _SpeculumLike,
    *,
    geo_lat: float,
) -> tuple[float, float]:
    return _under_pole_arcs(sig, prom, pole_deg=_topocentric_pole(sig, geo_lat=geo_lat))


def _zodiacal_longitude_arcs(sig: _SpeculumLike, prom: _SpeculumLike) -> tuple[float, float]:
    direct = (sig.lon - prom.lon) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _zodiacal_projected_arcs(sig: _SpeculumLike, prom: _SpeculumLike) -> tuple[float, float]:
    direct = (sig.ra - prom.ra) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _equatorial_arcs(sig: _SpeculumLike, prom: _SpeculumLike) -> tuple[float, float]:
    direct = (sig.ra - prom.ra) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


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
    if method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
        angular = _ptolemaic_angular_arcs(sig, prom, armc=armc, geo_lat=geo_lat)
        if angular is not None:
            return angular

    if space is PrimaryDirectionSpace.IN_ZODIACO:
        if method is PrimaryDirectionMethod.REGIOMONTANUS:
            return _regiomontanus_under_pole_arcs(sig, prom, geo_lat=geo_lat)
        if method is PrimaryDirectionMethod.CAMPANUS:
            return _campanus_under_pole_arcs(sig, prom, geo_lat=geo_lat)
        if method is PrimaryDirectionMethod.TOPOCENTRIC:
            return _topocentric_under_pole_arcs(sig, prom, geo_lat=geo_lat)
        if method in (
            PrimaryDirectionMethod.MERIDIAN,
            PrimaryDirectionMethod.MORINUS,
        ):
            return _equatorial_arcs(sig, prom)
        if method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
            return _ptolemaic_proportional_semi_arc_arcs(sig, prom)
        if latitude_doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED:
            return _zodiacal_longitude_arcs(sig, prom)
        return _zodiacal_projected_arcs(sig, prom)

    if method is PrimaryDirectionMethod.REGIOMONTANUS:
        return _regiomontanus_under_pole_arcs(sig, prom, geo_lat=geo_lat)
    if method is PrimaryDirectionMethod.CAMPANUS:
        return _campanus_under_pole_arcs(sig, prom, geo_lat=geo_lat)
    if method is PrimaryDirectionMethod.TOPOCENTRIC:
        return _topocentric_under_pole_arcs(sig, prom, geo_lat=geo_lat)
    if method in (
        PrimaryDirectionMethod.MERIDIAN,
        PrimaryDirectionMethod.MORINUS,
    ):
        return _equatorial_arcs(sig, prom)
    if method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
        return _ptolemaic_proportional_semi_arc_arcs(sig, prom)
    if method in (
        PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
    ):
        return _placidian_classic_semi_arc_arcs(
            sig,
            prom,
            oa_asc=oa_asc,
            armc=armc,
            geo_lat=geo_lat,
        )
    return _mundane_arcs(sig, prom)
