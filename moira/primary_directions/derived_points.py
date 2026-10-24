"""Typed, source-bound derived significators for primary directions.

Boundary: owns typed catalogue-lot construction, Fortune formula selection,
and composition with an existing Ptolemaic predominator determination.
Does not select an office, infer sect,
accept arbitrary point coordinates, or change the underlying directional law.
Ptolemy III.10 supplies the unreversed Fortune; the existing lots catalogue
supplies the separately named sect-reversed convention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from numbers import Real
from typing import TYPE_CHECKING, Iterable

from .._strenum import StrEnum
from ..constants import Body
from ..hellenistic import HELLENISTIC_CLASSICAL_PLANETS
from ..hellenistic_offices import (
    HellenisticOfficeStatus,
    PREDOMINATOR_DOCTRINE_PTOLEMY,
    PtolemyPlaceTruth,
    PtolemyPredominatorDetermination,
)
from ..lots import (
    PARTS_DEFINITIONS, PartDefinition, ArabicPartsService, LotsComputationPolicy,
    LotsReferenceFailureMode, _evaluate_lot_definitions,
)

if TYPE_CHECKING:
    from ..chart import Chart
    from ..houses import HouseCusps

__all__ = [
    "PrimaryDirectionFortuneDoctrine",
    "PrimaryDirectionFortuneTarget",
    "PrimaryDirectionLotTarget",
    "PrimaryDirectionPredominatorTarget",
    "PrimaryDirectionDerivedPointTarget",
    "resolve_primary_direction_derived_point",
]

_NATAL_LOT_SOURCE_NAMES = frozenset(Body.ALL_PLANETS) | {
    "North Node", "South Node", "Mean Node", "True Node",
}


class PrimaryDirectionFortuneDoctrine(StrEnum):
    """Vessel: Explicitly distinct Fortune formula conventions."""

    PTOLEMAIC = "ptolemy_tetrabiblos_iii_10"
    SECT_REVERSED = "lots_sect_reversed"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionFortuneTarget:
    """Vessel: A zero-ecliptic-latitude Fortune with an explicit formula.

    Sect is caller supplied, as in the lots owner, and required only for the
    sect-reversed convention. Ptolemy's formula is unreversed at night.
    """

    doctrine: PrimaryDirectionFortuneDoctrine = PrimaryDirectionFortuneDoctrine.PTOLEMAIC
    is_day_chart: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.doctrine, PrimaryDirectionFortuneDoctrine):
            raise ValueError("Fortune requires a typed Fortune doctrine")
        if self.is_day_chart is not None and type(self.is_day_chart) is not bool:
            raise ValueError("Fortune is_day_chart must be bool or None")
        if self.doctrine is PrimaryDirectionFortuneDoctrine.SECT_REVERSED and self.is_day_chart is None:
            raise ValueError("sect-reversed Fortune requires explicit is_day_chart")

    @property
    def name(self) -> str:
        return "Fortune"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLotTarget:
    """Vessel: A named catalogue lot resolved from the current natal figure.

    The lots owner supplies its recipe, projector, arc and dependency policy.
    Sect and optional external longitudes are explicit, never inferred. All
    catalogue lots have zero assigned ecliptic latitude as directional points.
    A requested unresolved point raises under either lots failure mode.
    """

    lot_name: str
    is_day_chart: bool
    policy: LotsComputationPolicy = field(default_factory=LotsComputationPolicy)
    syzygy: float | None = None
    prenatal_new_moon: float | None = None
    prenatal_full_moon: float | None = None
    lord_of_hour: float | None = None

    def __post_init__(self) -> None:
        _catalogue_definition(self.lot_name)
        if type(self.is_day_chart) is not bool:
            raise ValueError("lot target requires explicit Boolean is_day_chart")
        if not isinstance(self.policy, LotsComputationPolicy):
            raise ValueError("lot target policy must be LotsComputationPolicy")
        ArabicPartsService._validate_policy(self.policy)
        for label in ("syzygy", "prenatal_new_moon", "prenatal_full_moon", "lord_of_hour"):
            value = getattr(self, label)
            if value is not None:
                object.__setattr__(self, label, _finite(value, f"lot target {label}") % 360.0)

    @property
    def name(self) -> str:
        # Fortune has an existing canonical identity. Other lot names are
        # namespaced to avoid interpreting a catalogue label as a body/aspect.
        return "Fortune" if self.lot_name == "Fortune" else f"Lot: {self.lot_name}"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPredominatorTarget:
    """Vessel: An existing selected office, retaining its canonical identity.

    A selected planet remains that planet, with native latitude; Ascendant
    maps to ASC and Lot of Fortune to the unreversed Fortune. An unresolved
    office raises with its original reason and never supplies a fallback.
    """

    determination: PtolemyPredominatorDetermination

    def __post_init__(self) -> None:
        det = self.determination
        if not isinstance(det, PtolemyPredominatorDetermination):
            raise ValueError("predominator target requires PtolemyPredominatorDetermination")
        if det.status is HellenisticOfficeStatus.NOT_EVALUABLE:
            raise ValueError(f"predominator not evaluable: {det.reason}")
        if (
            det.status is not HellenisticOfficeStatus.SELECTED
            or det.doctrine != PREDOMINATOR_DOCTRINE_PTOLEMY
            or det.predominator not in (*HELLENISTIC_CLASSICAL_PLANETS, "Ascendant", "Lot of Fortune")
            or not isinstance(det.selection_step, str) or not det.selection_step
            or det.reason is not None or type(det.is_day_chart) is not bool
        ):
            raise ValueError("invalid selected predominator determination")
        _finite(det.predominator_longitude, "predominator longitude")
        _finite(det.lot_of_fortune_longitude, "predominator Fortune longitude")
        if (
            not isinstance(det.places, tuple)
            or any(not isinstance(p, PtolemyPlaceTruth) for p in det.places)
            or len(det.places) != len(HELLENISTIC_CLASSICAL_PLANETS)
            or any(not isinstance(p.name, str) for p in det.places)
            or {p.name for p in det.places} != set(HELLENISTIC_CLASSICAL_PLANETS)
        ):
            raise ValueError("predominator requires the complete seven-planet place record")
        for place in det.places:
            _finite(place.longitude, "predominator place longitude")
            _finite(place.offset_from_ascendant_deg, "predominator place offset")

    @property
    def name(self) -> str:
        return {"Ascendant": "ASC", "Lot of Fortune": "Fortune"}.get(
            self.determination.predominator, self.determination.predominator
        )


PrimaryDirectionDerivedPointTarget = (
    PrimaryDirectionFortuneTarget | PrimaryDirectionPredominatorTarget | PrimaryDirectionLotTarget
)


def _catalogue_definition(name: str) -> PartDefinition:
    if not isinstance(name, str) or not name:
        raise ValueError("lot target requires an exact catalogue lot name")
    matches = [definition for definition in PARTS_DEFINITIONS if definition.name == name]
    if len(matches) != 1:
        raise ValueError(f"lot target requires a unique catalogue lot name: {name!r}")
    return matches[0]


def _is_derived_point_name(name: str) -> bool:
    if name == "Fortune":
        return True
    if not isinstance(name, str) or not name.startswith("Lot: ") or name == "Lot: Fortune":
        return False
    return sum(definition.name == name[5:] for definition in PARTS_DEFINITIONS) == 1


def _resolve_lot_points(
    targets: Iterable[PrimaryDirectionLotTarget], chart: Chart, houses: HouseCusps,
) -> dict[str, tuple[str, float, float]]:
    """Batch only requested catalogue definitions, grouped by explicit context."""
    groups = {}
    for target in targets:
        key = (target.is_day_chart, target.policy, target.syzygy, target.prenatal_new_moon,
               target.prenatal_full_moon, target.lord_of_hour)
        groups.setdefault(key, []).append(target)
    if not groups:
        return {}
    positions = {}
    for collection in (chart.planets, chart.nodes):
        for name, point in collection.items():
            # Chart entries cannot masquerade as derived references such as
            # Fortune/Spirit or replace the catalogue's dependency policy.
            if name not in _NATAL_LOT_SOURCE_NAMES:
                continue
            if name in positions:
                raise ValueError(f"duplicate lot chart source: {name}")
            positions[name] = _finite(point.longitude, f"lot source {name}") % 360.0
    if isinstance(houses.cusps, dict):
        if set(houses.cusps) != set(range(1, 13)):
            raise ValueError("lot targets require house cusps 1 through 12")
        raw_cusps = [houses.cusps[number] for number in range(1, 13)]
    else:
        raw_cusps = list(houses.cusps)
    if len(raw_cusps) != 12:
        raise ValueError("lot targets require exactly 12 house cusps")
    cusps = [_finite(cusp, "lot house cusp") % 360.0 for cusp in raw_cusps]
    asc = _finite(houses.asc, "lot Ascendant") % 360.0
    mc = _finite(houses.mc, "lot Midheaven") % 360.0
    resolved = {}
    service = ArabicPartsService()
    for (day, policy, syzygy, new_moon, full_moon, hour), group in groups.items():
        # Obtain named not-evaluable receipts even for RAISE policies. Point
        # construction requires a coordinate under both modes, so a missing
        # requested point always raises with its original receipt below.
        evaluation = _evaluate_lot_definitions(
            service,
            tuple(_catalogue_definition(target.lot_name) for target in group),
            positions, cusps, day,
            replace(policy, unresolved_reference_mode=LotsReferenceFailureMode.SKIP),
            asc_longitude=asc, mc_longitude=mc, syzygy=syzygy,
            prenatal_new_moon=new_moon, prenatal_full_moon=full_moon, lord_of_hour=hour,
        )
        parts = {part.name: part for part in evaluation.parts}
        missing = {item.name: item for item in evaluation.not_evaluable}
        for target in group:
            if target.lot_name in missing:
                receipt = missing[target.lot_name]
                raise ValueError(f"{target.name} not evaluable: {receipt.reason}; "
                                 f"missing references: {', '.join(receipt.missing_references)}")
            part = parts[target.lot_name]
            resolved[target.name] = (target.name, _finite(part.longitude, "lot longitude") % 360.0, 0.0)
    return resolved


def _resolve_primary_direction_derived_points(
    targets: Iterable[PrimaryDirectionDerivedPointTarget], chart: Chart, houses: HouseCusps,
) -> dict[str, tuple[str, float, float]]:
    """Request-local batch composition; no persistent coordinate cache."""
    targets = tuple(targets)
    resolved = _resolve_lot_points(
        (target for target in targets if isinstance(target, PrimaryDirectionLotTarget)), chart, houses)
    for target in targets:
        if not isinstance(target, PrimaryDirectionLotTarget):
            resolved[target.name] = resolve_primary_direction_derived_point(target, chart, houses)
    return resolved


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _same_longitude(actual: float, expected: float, label: str) -> None:
    # The determination stores the same natal longitudes, not a rounded
    # presentation. This tolerance covers floating point normalization only.
    if abs(((_finite(actual, label) % 360.0) - (expected % 360.0) + 180.0) % 360.0 - 180.0) > 1e-9:
        raise ValueError(f"predominator determination does not match chart: {label}")


def resolve_primary_direction_derived_point(
    target: PrimaryDirectionDerivedPointTarget,
    chart: Chart,
    houses: HouseCusps,
) -> tuple[str, float, float]:
    """Resolve a typed target against the current figure, preserving identity.

    Catalogue lots use the lots owner's recipes and source-reference policy.
    Fortune is constructed from natal ecliptic longitudes. Predominator
    composition checks all seven stored places, Ascendant offsets, Fortune,
    and the selected longitude against this chart; it never reruns selection.
    The determination does not carry an epoch, so this proves coordinate
    consistency, not the provenance of caller-supplied prenatal context.
    """
    if isinstance(target, PrimaryDirectionLotTarget):
        return _resolve_lot_points((target,), chart, houses)[target.name]
    if not isinstance(target, (PrimaryDirectionFortuneTarget, PrimaryDirectionPredominatorTarget)):
        raise ValueError("derived point requires a typed Fortune, predominator or catalogue-lot target")
    asc = _finite(houses.asc, "derived point Ascendant") % 360.0
    try:
        sun = _finite(chart.planets["Sun"].longitude, "Fortune Sun longitude") % 360.0
        moon = _finite(chart.planets["Moon"].longitude, "Fortune Moon longitude") % 360.0
    except KeyError as exc:
        raise ValueError("Fortune requires natal Sun and Moon") from exc
    fortune = (asc + moon - sun) % 360.0
    if isinstance(target, PrimaryDirectionFortuneTarget):
        if target.doctrine is PrimaryDirectionFortuneDoctrine.SECT_REVERSED and not target.is_day_chart:
            fortune = (asc + sun - moon) % 360.0
        return target.name, fortune, 0.0

    det = target.determination
    for place in det.places:
        point = chart.planets.get(place.name)
        if point is None:
            raise ValueError(f"predominator requires natal {place.name}")
        longitude = _finite(point.longitude, f"natal {place.name} longitude") % 360.0
        _same_longitude(place.longitude, longitude, place.name)
        _same_longitude(place.offset_from_ascendant_deg, (longitude - asc) % 360.0,
                        f"{place.name} Ascendant offset")
    _same_longitude(det.lot_of_fortune_longitude, fortune, "Fortune")
    if target.name == "ASC":
        longitude, latitude = asc, 0.0
    elif target.name == "Fortune":
        longitude, latitude = fortune, 0.0
    else:
        point = chart.planets[target.name]
        longitude = _finite(point.longitude, "selected planet longitude") % 360.0
        latitude = _finite(point.latitude, "selected planet latitude")
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("selected planet latitude must be in [-90, 90]")
    _same_longitude(det.predominator_longitude, longitude, "selected longitude")
    return target.name, longitude, latitude
