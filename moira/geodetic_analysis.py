"""Full Geodetic houses, static overlays, and supplied-place comparisons.

All house and aspect doctrine is delegated to the existing owning engines.
Coordinates are caller supplied; this module neither geocodes nor scores places.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Sequence

from .aspects import AspectData, AspectPolicy, aspects_to_point
from .geodetic import (
    GeodeticChart, GeodeticLocation, _armc_from_mc, _circular_delta,
    geodetic_chart_at_location, geodetic_mc,
)
from .geodetic_inputs import GeodeticBodySnapshot, _ENGINE_FRAME, _label
from .houses import HouseCusps, HousePlacement, HousePolicy, assign_house, houses_from_armc

__all__ = [
    "GeodeticHouseChart", "GeodeticOverlayPlacement", "GeodeticNatalOverlay",
    "GeodeticNamedLocation", "GeodeticLocationDifference", "GeodeticLocationResult",
    "GeodeticLocationComparison", "geodetic_house_chart", "geodetic_natal_overlay",
    "compare_geodetic_locations",
]


@dataclass(frozen=True, slots=True)
class GeodeticHouseChart:
    """Location-native angles and twelve cusps with their house policy receipt."""

    angles: GeodeticChart
    houses: HouseCusps
    location: GeodeticLocation
    source_frame: str
    jd_ut1: float | None = None
    jd_tt: float | None = None
    ayanamsa_system: str | None = None

    @property
    def targets(self):
        """Fresh angle map; angles remain distinct from numbered cusps."""
        return {"MC": self.angles.mc, "IC": geodetic_mc(self.angles.mc, -180),
                "ASC": self.angles.asc, "DSC": geodetic_mc(self.angles.asc, -180)}


@dataclass(frozen=True, slots=True)
class GeodeticOverlayPlacement:
    """A snapshot body's longitude-based membership, with cusp witness."""

    body_id: str
    placement: HousePlacement


@dataclass(frozen=True, slots=True)
class GeodeticNatalOverlay:
    """Static placements and contacts; no applying or separating inference."""

    house_chart: GeodeticHouseChart
    snapshot: GeodeticBodySnapshot
    placements: tuple[GeodeticOverlayPlacement, ...]
    contacts: tuple[AspectData, ...]
    aspect_policy: AspectPolicy
    target_longitudes: tuple[tuple[str, float], ...]
    coincident_targets: tuple[tuple[str, str], ...]
    placement_semantics: str = "ecliptic_longitude_not_3d_mundane"

    @property
    def complete(self):
        """Whether every requested source body was available."""
        return self.snapshot.complete


def geodetic_house_chart(
    location: GeodeticLocation, *, obliquity: float, system: str,
    zodiac: str = "tropical", ayanamsa_deg: float | None = None,
    ayanamsa_system: str | None = None, house_policy: HousePolicy | None = None,
    sun_longitude: float | None = None, source_frame: str = _ENGINE_FRAME,
    jd_ut1: float | None = None, jd_tt: float | None = None,
) -> GeodeticHouseChart:
    """Build a house figure from tropical ARMC, with strict default policy.

    ``sun_longitude`` is explicitly tropical, including for sidereal figures.
    Epochs, when known, describe the supplied obliquity/frame reference. A
    solar-dependent system requires its Sun explicitly; no body is inserted.
    """
    _label(system, "system")
    _label(source_frame, "source_frame")
    for name, value in (("jd_ut1", jd_ut1), ("jd_tt", jd_tt)):
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if (jd_ut1 is None) != (jd_tt is None):
        raise ValueError("supply both UT1 and TT reference epochs, or neither")
    if ayanamsa_system is not None:
        _label(ayanamsa_system, "ayanamsa_system")
        if zodiac != "sidereal":
            raise ValueError("tropical chart cannot name an ayanamsa system")
    angles = geodetic_chart_at_location(location, obliquity, ayanamsa_deg, zodiac)
    active_policy = HousePolicy.strict() if house_policy is None else house_policy
    houses = houses_from_armc(
        _armc_from_mc(geodetic_mc(location.longitude_deg), obliquity), obliquity,
        location.latitude_deg, system, policy=active_policy,
        sun_longitude=sun_longitude, ayanamsa_offset=angles.ayanamsa_deg,
    )
    # The house engine chooses its physical meridian branch. A branch it
    # cannot express as the requested location-native MC is not relabelled.
    if abs(_circular_delta(houses.mc, angles.mc)) > 1e-8 or abs(_circular_delta(houses.asc, angles.asc)) > 1e-8:
        raise ValueError("house engine angles disagree with Geodetic branch")
    return GeodeticHouseChart(angles, houses, location, source_frame, jd_ut1, jd_tt, ayanamsa_system)


def geodetic_natal_overlay(
    house_chart: GeodeticHouseChart, snapshot: GeodeticBodySnapshot, *,
    aspect_policy: AspectPolicy, angles: Sequence[str] = ("MC", "IC", "ASC", "DSC"),
    include_cusps: bool = False,
) -> GeodeticNatalOverlay:
    """Place the common snapshot and detect policy-controlled static contacts.

    Unknown epochs may match unknown epochs, but a known reference is never
    silently equated with an unknown or different one. Targets retain names
    even when a numbered cusp and an angle have the same longitude.
    """
    if not isinstance(house_chart, GeodeticHouseChart) or not isinstance(snapshot, GeodeticBodySnapshot):
        raise TypeError("house_chart and snapshot must be Geodetic vessels")
    if not isinstance(aspect_policy, AspectPolicy):
        raise TypeError("aspect_policy must be AspectPolicy")
    if isinstance(angles, str) or len(set(angles)) != len(angles) or any(a not in house_chart.targets for a in angles):
        raise ValueError("angles must be unique MC, IC, ASC or DSC selections")
    if not angles and not include_cusps:
        raise ValueError("select at least one angle or cusp target")
    if (house_chart.source_frame != snapshot.source_frame
            or house_chart.jd_ut1 != snapshot.jd_ut1 or house_chart.jd_tt != snapshot.jd_tt):
        raise ValueError("snapshot and house chart require common frame and epochs")
    base = house_chart.angles
    if base.zodiac != snapshot.zodiac or base.ayanamsa_deg != snapshot.ayanamsa_deg or house_chart.ayanamsa_system != snapshot.ayanamsa_system:
        raise ValueError("snapshot and house chart require common zodiac and reference ayanamsa")
    targets = [(name, house_chart.targets[name]) for name in angles]
    if include_cusps:
        targets.extend((f"Cusp {i + 1}", value) for i, value in enumerate(house_chart.houses.cusps))
    placements = tuple(GeodeticOverlayPlacement(p.body_id, assign_house(p.selected_longitude_deg, house_chart.houses)) for p in snapshot.positions)
    contacts = tuple(contact for name, lon in targets for contact in aspects_to_point(lon, snapshot.longitudes, point_name=name, policy=aspect_policy))
    coincidences = tuple((name, other) for i, (name, lon) in enumerate(targets)
                         for other, value in targets[i + 1:] if abs(_circular_delta(lon, value)) < 1e-9)
    return GeodeticNatalOverlay(house_chart, snapshot, placements, contacts, aspect_policy, tuple(targets), coincidences)


@dataclass(frozen=True, slots=True)
class GeodeticNamedLocation:
    """Unique caller-owned ID and optional display name for a supplied place."""

    location_id: str
    location: GeodeticLocation
    display_name: str | None = None

    def __post_init__(self):
        _label(self.location_id, "location_id")
        if not isinstance(self.location, GeodeticLocation):
            raise TypeError("location must be GeodeticLocation")
        if self.display_name is not None:
            _label(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class GeodeticLocationDifference:
    """Circular angles, changed houses and contact keys versus a named baseline."""

    baseline_id: str
    angle_deltas_deg: tuple[tuple[str, float], ...]
    house_changes: tuple[tuple[str, int, int], ...]
    added_contacts: tuple[tuple[str, str, float], ...]
    removed_contacts: tuple[tuple[str, str, float], ...]


@dataclass(frozen=True, slots=True)
class GeodeticLocationResult:
    """One supplied place's calculation or explicit collected failure."""

    place: GeodeticNamedLocation
    overlay: GeodeticNatalOverlay | None
    difference: GeodeticLocationDifference | None = None
    failure_type: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class GeodeticLocationComparison:
    """Shared snapshot and ordered results; no inferred suitability score."""

    snapshot: GeodeticBodySnapshot
    results: tuple[GeodeticLocationResult, ...]
    order_by: str
    baseline_id: str | None

    @property
    def complete(self):
        """Whether all requested bodies and places produced results."""
        return self.snapshot.complete and all(r.overlay is not None for r in self.results)


def _contact_keys(overlay):
    return {(c.body1, c.body2, c.angle) for c in overlay.contacts}


def compare_geodetic_locations(
    locations: Sequence[GeodeticNamedLocation], snapshot: GeodeticBodySnapshot, *,
    obliquity: float, system: str, aspect_policy: AspectPolicy,
    house_policy: HousePolicy | None = None, sun_longitude: float | None = None,
    error_policy: str = "raise", order_by: str = "input",
) -> GeodeticLocationComparison:
    """Compose individual overlays from one snapshot, preserving caller order.

    Optional ``minimum_contact_orb`` sorting is a geometric metric only;
    ties preserve input order. The baseline is the first valid input place,
    regardless of output sorting. Structural input errors always raise.
    """
    if not isinstance(snapshot, GeodeticBodySnapshot):
        raise TypeError("snapshot must be GeodeticBodySnapshot")
    if isinstance(locations, str) or not locations or any(not isinstance(p, GeodeticNamedLocation) for p in locations):
        raise ValueError("locations must be a nonempty sequence of named locations")
    if len({p.location_id for p in locations}) != len(locations):
        raise ValueError("duplicate location IDs")
    if error_policy not in ("raise", "collect") or order_by not in ("input", "minimum_contact_orb"):
        raise ValueError("unsupported failure or ordering policy")
    if not isinstance(aspect_policy, AspectPolicy):
        raise TypeError("aspect_policy must be AspectPolicy")
    _label(system, "system")
    if not math.isfinite(obliquity) or not 22 <= obliquity <= 25:
        raise ValueError("obliquity must be in [22, 25]")
    if house_policy is not None and not isinstance(house_policy, HousePolicy):
        raise TypeError("house_policy must be HousePolicy")
    if sun_longitude is None:
        sun_longitude = next((p.tropical_longitude_deg for p in snapshot.positions if p.body_id == "Sun"), None)
    results = []
    baseline = None
    baseline_id = None
    for place in locations:
        try:
            figure = geodetic_house_chart(
                place.location, obliquity=obliquity, system=system,
                zodiac=snapshot.zodiac, ayanamsa_deg=snapshot.ayanamsa_deg,
                ayanamsa_system=snapshot.ayanamsa_system, house_policy=house_policy,
                sun_longitude=sun_longitude, source_frame=snapshot.source_frame,
                jd_ut1=snapshot.jd_ut1, jd_tt=snapshot.jd_tt,
            )
            overlay = geodetic_natal_overlay(figure, snapshot, aspect_policy=aspect_policy)
        except ValueError as exc:
            if error_policy == "raise":
                raise
            results.append(GeodeticLocationResult(place, None, failure_type=type(exc).__name__, reason=str(exc)))
            continue
        if baseline is None:
            baseline, baseline_id = overlay, place.location_id
        previous = {p.body_id: p.placement.house for p in baseline.placements}
        differences = GeodeticLocationDifference(
            baseline_id,
            tuple((name, _circular_delta(value, baseline.house_chart.targets[name])) for name, value in figure.targets.items()),
            tuple((p.body_id, previous[p.body_id], p.placement.house) for p in overlay.placements if previous[p.body_id] != p.placement.house),
            tuple(sorted(_contact_keys(overlay) - _contact_keys(baseline))),
            tuple(sorted(_contact_keys(baseline) - _contact_keys(overlay))),
        )
        results.append(GeodeticLocationResult(place, overlay, differences))
    if order_by == "minimum_contact_orb":
        results.sort(key=lambda r: min((c.orb for c in r.overlay.contacts), default=math.inf) if r.overlay else math.inf)
    return GeodeticLocationComparison(snapshot, tuple(results), order_by, baseline_id)
