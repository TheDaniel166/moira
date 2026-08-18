"""
Score-free Hellenistic relational condition.

Owns testimony, adherence, and the assemble-condition vessel. Reuses
whole-sign superiority and malefic enclosure. Does not score, rank, or
admit aktinobolia geometry in 6.3.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .aspects import (
    AspectMotionState,
    HellenisticAspectEvaluationStatus,
    HellenisticOvercomingRelation,
    HellenisticSuperiorityTruth,
    aspect_motion_witness,
    find_whole_sign_aspects,
    hellenistic_superiority_truth,
)
from .dignities import besieging_truth
from .dignities_types import BesiegingTruth

CLASSICAL_7: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
)

DEFAULT_ADHERENCE_ORB_DEG = 3.0
DEFAULT_ENCLOSURE_ORB_DEG = 12.0
RAY_NOT_ADMITTED_REASON = "doctrine_not_admitted"

__all__ = [
    "CLASSICAL_7",
    "DEFAULT_ADHERENCE_ORB_DEG",
    "DEFAULT_ENCLOSURE_ORB_DEG",
    "RAY_NOT_ADMITTED_REASON",
    "HellenisticTestimonyWitness",
    "HellenisticTestimonyTruth",
    "HellenisticAdherenceTruth",
    "HellenisticRayTruth",
    "HellenisticPlanetOvercomingTruth",
    "HellenisticAssembleCondition",
    "assemble_hellenistic_condition",
]


def _require_finite_longitude(name: str, value: float) -> float:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return value % 360.0


def _circular_distance(left: float, right: float) -> float:
    delta = abs((left % 360.0) - (right % 360.0))
    return min(delta, 360.0 - delta)


def _classical_positions(
    positions: dict[str, float],
) -> dict[str, float]:
    if not isinstance(positions, dict):
        raise TypeError("positions must be a dict of body longitudes")
    resolved: dict[str, float] = {}
    for name in CLASSICAL_7:
        if name not in positions:
            continue
        resolved[name] = _require_finite_longitude(
            f"positions[{name!r}]",
            positions[name],
        )
    if not resolved:
        raise ValueError("positions must include at least one classical planet")
    return resolved


@dataclass(frozen=True, slots=True)
class HellenisticTestimonyWitness:
    """One whole-sign Ptolemaic regard of the subject."""

    body: str
    aspect: str
    angle_deg: float
    superiority: HellenisticSuperiorityTruth


@dataclass(frozen=True, slots=True)
class HellenisticTestimonyTruth:
    """Who regards the subject by whole-sign aspect; who is averse."""

    status: HellenisticAspectEvaluationStatus
    subject: str
    witnesses: tuple[HellenisticTestimonyWitness, ...]
    averse_bodies: tuple[str, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is HellenisticAspectEvaluationStatus.EVALUATED:
            if self.reason is not None:
                raise ValueError(
                    "HellenisticTestimonyTruth evaluated results cannot carry a reason"
                )
        elif not self.reason:
            raise ValueError(
                "HellenisticTestimonyTruth not_evaluable results require a reason"
            )


@dataclass(frozen=True, slots=True)
class HellenisticAdherenceTruth:
    """Applying or exact bodily conjunction within the admitted orb."""

    status: HellenisticAspectEvaluationStatus
    subject: str
    orb_deg: float
    adhered: bool | None
    partner: str | None
    distance_deg: float | None
    motion_state: str | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.orb_deg) or not (0.0 < self.orb_deg <= 180.0):
            raise ValueError("HellenisticAdherenceTruth orb_deg must be in (0, 180]")
        if self.status is HellenisticAspectEvaluationStatus.EVALUATED:
            if self.adhered is None or self.reason is not None:
                raise ValueError(
                    "HellenisticAdherenceTruth evaluated results require "
                    "adhered and no reason"
                )
        elif self.adhered is not None or not self.reason:
            raise ValueError(
                "HellenisticAdherenceTruth not_evaluable results require "
                "no adhered flag and an explicit reason"
            )


@dataclass(frozen=True, slots=True)
class HellenisticRayTruth:
    """Aktinobolia placeholder. 6.3.0 does not invent the ray geometry."""

    status: HellenisticAspectEvaluationStatus
    subject: str
    reason: str

    def __post_init__(self) -> None:
        if self.status is not HellenisticAspectEvaluationStatus.NOT_EVALUABLE:
            raise ValueError(
                "HellenisticRayTruth is not_evaluable until a geometric "
                "ray object is admitted"
            )
        if self.reason != RAY_NOT_ADMITTED_REASON:
            raise ValueError(
                "HellenisticRayTruth reason must be doctrine_not_admitted"
            )


@dataclass(frozen=True, slots=True)
class HellenisticPlanetOvercomingTruth:
    """Tenth-sign overcoming of the subject by other classical bodies."""

    status: HellenisticAspectEvaluationStatus
    subject: str
    overcame_by: tuple[str, ...]
    overcomes: tuple[str, ...]
    receipts: tuple[HellenisticSuperiorityTruth, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is HellenisticAspectEvaluationStatus.EVALUATED:
            if self.reason is not None:
                raise ValueError(
                    "HellenisticPlanetOvercomingTruth evaluated results "
                    "cannot carry a reason"
                )
        elif not self.reason:
            raise ValueError(
                "HellenisticPlanetOvercomingTruth not_evaluable results "
                "require an explicit reason"
            )


@dataclass(frozen=True, slots=True)
class HellenisticAssembleCondition:
    """Score-free assembly of named relational receipts for one planet."""

    subject: str
    testimony: HellenisticTestimonyTruth
    overcoming: HellenisticPlanetOvercomingTruth
    enclosure: BesiegingTruth
    adherence: HellenisticAdherenceTruth
    ray: HellenisticRayTruth


def _testimony_truth(
    subject: str,
    positions: dict[str, float],
) -> HellenisticTestimonyTruth:
    if subject not in positions:
        return HellenisticTestimonyTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject=subject,
            witnesses=(),
            averse_bodies=(),
            reason="subject_longitude_not_supplied",
        )
    aspects = find_whole_sign_aspects(positions)
    witnesses: list[HellenisticTestimonyWitness] = []
    for aspect in aspects:
        if subject not in {aspect.body1, aspect.body2}:
            continue
        other = aspect.body2 if aspect.body1 == subject else aspect.body1
        superiority = aspect.hellenistic_superiority_truth
        if superiority is None:
            raise ValueError(
                "whole-sign aspect did not preserve superiority truth"
            )
        witnesses.append(
            HellenisticTestimonyWitness(
                body=other,
                aspect=aspect.aspect,
                angle_deg=aspect.angle,
                superiority=superiority,
            )
        )
    present = set(positions)
    witnessed = {item.body for item in witnesses}
    averse = tuple(
        name
        for name in CLASSICAL_7
        if name in present and name != subject and name not in witnessed
    )
    return HellenisticTestimonyTruth(
        status=HellenisticAspectEvaluationStatus.EVALUATED,
        subject=subject,
        witnesses=tuple(witnesses),
        averse_bodies=averse,
    )


def _overcoming_truth(
    subject: str,
    positions: dict[str, float],
) -> HellenisticPlanetOvercomingTruth:
    if subject not in positions:
        return HellenisticPlanetOvercomingTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject=subject,
            overcame_by=(),
            overcomes=(),
            receipts=(),
            reason="subject_longitude_not_supplied",
        )
    receipts: list[HellenisticSuperiorityTruth] = []
    overcame_by: list[str] = []
    overcomes: list[str] = []
    subject_lon = positions[subject]
    for other in CLASSICAL_7:
        if other == subject or other not in positions:
            continue
        receipt = hellenistic_superiority_truth(
            subject_lon,
            positions[other],
            None,
            body1=subject,
            body2=other,
        )
        receipts.append(receipt)
        relation = receipt.overcoming_truth.relation
        if relation is HellenisticOvercomingRelation.BODY2_OVERCOMES_BODY1:
            overcame_by.append(other)
        elif relation is HellenisticOvercomingRelation.BODY1_OVERCOMES_BODY2:
            overcomes.append(other)
    return HellenisticPlanetOvercomingTruth(
        status=HellenisticAspectEvaluationStatus.EVALUATED,
        subject=subject,
        overcame_by=tuple(overcame_by),
        overcomes=tuple(overcomes),
        receipts=tuple(receipts),
    )


def _adherence_truth(
    subject: str,
    positions: dict[str, float],
    speeds: dict[str, float] | None,
    orb_deg: float,
) -> HellenisticAdherenceTruth:
    if not isfinite(orb_deg) or not (0.0 < orb_deg <= 180.0):
        raise ValueError("adherence orb_deg must be finite and in (0, 180]")
    if subject not in positions:
        return HellenisticAdherenceTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject=subject,
            orb_deg=orb_deg,
            adhered=None,
            partner=None,
            distance_deg=None,
            motion_state=None,
            reason="subject_longitude_not_supplied",
        )
    subject_lon = positions[subject]
    candidates: list[tuple[float, str]] = []
    for other, longitude in positions.items():
        if other == subject:
            continue
        distance = _circular_distance(subject_lon, longitude)
        if distance <= orb_deg:
            candidates.append((distance, other))
    if not candidates:
        return HellenisticAdherenceTruth(
            status=HellenisticAspectEvaluationStatus.EVALUATED,
            subject=subject,
            orb_deg=orb_deg,
            adhered=False,
            partner=None,
            distance_deg=None,
            motion_state=None,
        )
    candidates.sort()
    nearest_distance, nearest = candidates[0]
    ties = [name for distance, name in candidates if distance == nearest_distance]
    if len(ties) > 1:
        return HellenisticAdherenceTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject=subject,
            orb_deg=orb_deg,
            adhered=None,
            partner=None,
            distance_deg=nearest_distance,
            motion_state=None,
            reason="ambiguous_nearest_partner",
        )
    if speeds is None or subject not in speeds or nearest not in speeds:
        return HellenisticAdherenceTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject=subject,
            orb_deg=orb_deg,
            adhered=None,
            partner=nearest,
            distance_deg=nearest_distance,
            motion_state=None,
            reason="speeds_not_supplied",
        )
    witness = aspect_motion_witness(
        subject,
        subject_lon,
        nearest,
        positions[nearest],
        "Conjunction",
        speed1_deg_per_day=speeds[subject],
        speed2_deg_per_day=speeds[nearest],
        reference_frame="caller_supplied_ecliptic_longitudes",
        timescale="caller_supplied_daily_speeds",
    )
    adhered = witness.state in {
        AspectMotionState.APPLYING,
        AspectMotionState.EXACT,
    }
    return HellenisticAdherenceTruth(
        status=HellenisticAspectEvaluationStatus.EVALUATED,
        subject=subject,
        orb_deg=orb_deg,
        adhered=adhered,
        partner=nearest,
        distance_deg=nearest_distance,
        motion_state=witness.state.value,
    )


def _enclosure_truth(
    subject: str,
    positions: dict[str, float],
    orb_deg: float,
) -> BesiegingTruth:
    """Reuse malefic enclosure. Do not invent a subject longitude."""

    if subject not in positions:
        return besieging_truth(
            0.0,
            positions,
            planet_name=subject,
            orb=orb_deg,
        )
    return besieging_truth(
        positions[subject],
        positions,
        planet_name=subject,
        orb=orb_deg,
    )


def assemble_hellenistic_condition(
    subject: str,
    positions: dict[str, float],
    speeds: dict[str, float] | None = None,
    *,
    adherence_orb_deg: float = DEFAULT_ADHERENCE_ORB_DEG,
    enclosure_orb_deg: float = DEFAULT_ENCLOSURE_ORB_DEG,
) -> HellenisticAssembleCondition:
    """Assemble named relational receipts for one classical planet."""

    if not isinstance(subject, str) or not subject or subject != subject.strip():
        raise ValueError("subject must be a non-empty trimmed string")
    resolved = _classical_positions(positions)
    resolved_speeds: dict[str, float] | None = None
    if speeds is not None:
        if not isinstance(speeds, dict):
            raise TypeError("speeds must be a dict of daily motions or None")
        resolved_speeds = {
            name: speeds[name]
            for name in resolved
            if name in speeds and isfinite(speeds[name])
        }
    return HellenisticAssembleCondition(
        subject=subject,
        testimony=_testimony_truth(subject, resolved),
        overcoming=_overcoming_truth(subject, resolved),
        enclosure=_enclosure_truth(subject, resolved, enclosure_orb_deg),
        adherence=_adherence_truth(
            subject,
            resolved,
            resolved_speeds,
            adherence_orb_deg,
        ),
        ray=HellenisticRayTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject=subject,
            reason=RAY_NOT_ADMITTED_REASON,
        ),
    )
