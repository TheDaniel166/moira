"""
Valens-style from→to transmission graph.

Builds computational edges from caller-owned natal points and existing
profection, Decennial, and Zodiacal Releasing receipts. Does not store
effect prose, polarity, or scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ._strenum import StrEnum
from .constants import SIGNS
from .hellenistic import HELLENISTIC_CLASSICAL_PLANETS, HELLENISTIC_PROFILE_LOTS
from .profections import DOMICILE_RULERS


__all__ = [
    "TransmissionEdge",
    "TransmissionEndpointKind",
    "TransmissionGraph",
    "TransmissionKind",
    "TransmissionStatus",
    "valens_transmission_graph",
]


class TransmissionStatus(StrEnum):
    """Whether one transmission edge or graph was evaluable."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


class TransmissionEndpointKind(StrEnum):
    """Admitted endpoint family: planet, whole-sign place, or lot."""

    PLANET = "planet"
    PLACE = "place"
    LOT = "lot"


class TransmissionKind(StrEnum):
    """Named from-to relation reused from existing period or natal receipts."""

    PROFECTED_YEAR_TO_MONTH = "profected_year_to_month"
    DECENNIAL_L1_TO_L2 = "decennial_l1_to_l2"
    ZR_L1_TO_L2 = "zr_l1_to_l2"
    NATAL_POINT_TO_PLACE = "natal_point_to_place"


@dataclass(frozen=True, slots=True)
class TransmissionEdge:
    """One from→to relation. No effect or quality fields exist."""

    source: str
    source_kind: TransmissionEndpointKind
    target: str
    target_kind: TransmissionEndpointKind
    kind: TransmissionKind
    period_ref: str | None
    natal_ref: str | None
    status: TransmissionStatus
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is TransmissionStatus.EVALUATED:
            if self.reason is not None:
                raise ValueError("evaluated transmission edges cannot carry a reason")
        elif not self.reason:
            raise ValueError(
                "not_evaluable transmission edges require an explicit reason"
            )
        if self.period_ref is not None and self.natal_ref is not None:
            raise ValueError("a transmission edge cannot be both period and natal")


@dataclass(frozen=True, slots=True)
class TransmissionGraph:
    """Closed set of computational transmission edges."""

    status: TransmissionStatus
    edges: tuple[TransmissionEdge, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is TransmissionStatus.EVALUATED:
            if self.reason is not None:
                raise ValueError("evaluated transmission graphs cannot carry a reason")
        elif not self.reason:
            raise ValueError(
                "not_evaluable transmission graphs require an explicit reason"
            )


def _place_from_asc(longitude: float, asc_longitude: float) -> int:
    sign = int((longitude % 360.0) // 30.0)
    asc_sign = int((asc_longitude % 360.0) // 30.0)
    return ((sign - asc_sign) % 12) + 1


def valens_transmission_graph(
    *,
    positions: dict[str, float] | None = None,
    lots: dict[str, float] | None = None,
    asc_longitude: float | None = None,
    profection_lord: str | None = None,
    profection_monthly_lords: tuple[str, ...] | list[str] | None = None,
    decennial_l1: str | None = None,
    decennial_l2: str | None = None,
    zr_l1_sign: str | None = None,
    zr_l2_sign: str | None = None,
) -> TransmissionGraph:
    """Assemble from→to edges. Missing families are omitted, not invented."""

    edges: list[TransmissionEdge] = []
    if profection_lord is not None:
        if not profection_monthly_lords or len(profection_monthly_lords) != 12:
            return TransmissionGraph(
                status=TransmissionStatus.NOT_EVALUABLE,
                edges=(),
                reason="profection_monthly_lords_must_contain_twelve_lords",
            )
        for index, lord in enumerate(profection_monthly_lords):
            edges.append(
                TransmissionEdge(
                    source=profection_lord,
                    source_kind=TransmissionEndpointKind.PLANET,
                    target=lord,
                    target_kind=TransmissionEndpointKind.PLANET,
                    kind=TransmissionKind.PROFECTED_YEAR_TO_MONTH,
                    period_ref=f"month_{index + 1}",
                    natal_ref=None,
                    status=TransmissionStatus.EVALUATED,
                )
            )
    if decennial_l1 is not None or decennial_l2 is not None:
        if not decennial_l1 or not decennial_l2:
            return TransmissionGraph(
                status=TransmissionStatus.NOT_EVALUABLE,
                edges=(),
                reason="decennial_levels_must_be_supplied_together",
            )
        edges.append(
            TransmissionEdge(
                source=decennial_l1,
                source_kind=TransmissionEndpointKind.PLANET,
                target=decennial_l2,
                target_kind=TransmissionEndpointKind.PLANET,
                kind=TransmissionKind.DECENNIAL_L1_TO_L2,
                period_ref="decennial_current",
                natal_ref=None,
                status=TransmissionStatus.EVALUATED,
            )
        )
    if zr_l1_sign is not None or zr_l2_sign is not None:
        if zr_l1_sign not in SIGNS or zr_l2_sign not in SIGNS:
            return TransmissionGraph(
                status=TransmissionStatus.NOT_EVALUABLE,
                edges=(),
                reason="zr_signs_must_be_admitted_zodiac_names",
            )
        edges.append(
            TransmissionEdge(
                source=DOMICILE_RULERS[zr_l1_sign],
                source_kind=TransmissionEndpointKind.PLANET,
                target=DOMICILE_RULERS[zr_l2_sign],
                target_kind=TransmissionEndpointKind.PLANET,
                kind=TransmissionKind.ZR_L1_TO_L2,
                period_ref="zr_current",
                natal_ref=None,
                status=TransmissionStatus.EVALUATED,
            )
        )
        edges.append(
            TransmissionEdge(
                source=zr_l1_sign,
                source_kind=TransmissionEndpointKind.PLACE,
                target=zr_l2_sign,
                target_kind=TransmissionEndpointKind.PLACE,
                kind=TransmissionKind.ZR_L1_TO_L2,
                period_ref="zr_current_signs",
                natal_ref=None,
                status=TransmissionStatus.EVALUATED,
            )
        )
    if positions is not None or lots is not None:
        if asc_longitude is None or not isfinite(asc_longitude):
            return TransmissionGraph(
                status=TransmissionStatus.NOT_EVALUABLE,
                edges=(),
                reason="natal_point_to_place_requires_asc_longitude",
            )
        for name in HELLENISTIC_CLASSICAL_PLANETS:
            if positions is None or name not in positions:
                continue
            if not isfinite(positions[name]):
                raise ValueError(f"positions[{name!r}] must be finite")
            house = _place_from_asc(positions[name], asc_longitude)
            edges.append(
                TransmissionEdge(
                    source=name,
                    source_kind=TransmissionEndpointKind.PLANET,
                    target=str(house),
                    target_kind=TransmissionEndpointKind.PLACE,
                    kind=TransmissionKind.NATAL_POINT_TO_PLACE,
                    period_ref=None,
                    natal_ref=name,
                    status=TransmissionStatus.EVALUATED,
                )
            )
        for name in HELLENISTIC_PROFILE_LOTS:
            if lots is None or name not in lots:
                continue
            if not isfinite(lots[name]):
                raise ValueError(f"lots[{name!r}] must be finite")
            house = _place_from_asc(lots[name], asc_longitude)
            edges.append(
                TransmissionEdge(
                    source=name,
                    source_kind=TransmissionEndpointKind.LOT,
                    target=str(house),
                    target_kind=TransmissionEndpointKind.PLACE,
                    kind=TransmissionKind.NATAL_POINT_TO_PLACE,
                    period_ref=None,
                    natal_ref=name,
                    status=TransmissionStatus.EVALUATED,
                )
            )
    if not edges:
        return TransmissionGraph(
            status=TransmissionStatus.NOT_EVALUABLE,
            edges=(),
            reason="no_admitted_transmission_inputs",
        )
    return TransmissionGraph(status=TransmissionStatus.EVALUATED, edges=tuple(edges))
