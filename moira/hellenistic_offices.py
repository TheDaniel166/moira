"""
Fail-closed Hellenistic office hunt.

Collects named predominator / house-master candidates and refuses to pick a
winner. Never imports Bonatti hyleg or longevity arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ._strenum import StrEnum
from .hellenistic import HELLENISTIC_CLASSICAL_PLANETS


OFFICE_NOT_ADMITTED_REASON = "doctrine_not_admitted"

__all__ = [
    "OFFICE_NOT_ADMITTED_REASON",
    "HellenisticOfficeCandidate",
    "HellenisticOfficeHunt",
    "HellenisticOfficeStatus",
    "hunt_hellenistic_offices",
]


class HellenisticOfficeStatus(StrEnum):
    """Office hunt outcome. 6.3.0 admits only fail-closed non-selection."""

    NOT_EVALUABLE = "not_evaluable"


@dataclass(frozen=True, slots=True)
class HellenisticOfficeCandidate:
    """One named candidate with only geometric facts."""

    name: str
    kind: str
    longitude: float | None
    house: int | None
    is_sect_light: bool | None
    is_angular: bool | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class HellenisticOfficeHunt:
    """Predominator and house-master remain unselected."""

    status: HellenisticOfficeStatus
    predominator: None
    house_master: None
    candidates: tuple[HellenisticOfficeCandidate, ...]
    reason: str

    def __post_init__(self) -> None:
        if self.status is not HellenisticOfficeStatus.NOT_EVALUABLE:
            raise ValueError(
                "HellenisticOfficeHunt is not_evaluable until a single hunt "
                "is admitted without a scored hybrid"
            )
        if self.predominator is not None or self.house_master is not None:
            raise ValueError("HellenisticOfficeHunt cannot select an office")
        if self.reason != OFFICE_NOT_ADMITTED_REASON:
            raise ValueError(
                "HellenisticOfficeHunt reason must be doctrine_not_admitted"
            )


def _place_from_asc(longitude: float, asc_longitude: float) -> int:
    sign = int((longitude % 360.0) // 30.0)
    asc_sign = int((asc_longitude % 360.0) // 30.0)
    return ((sign - asc_sign) % 12) + 1


def hunt_hellenistic_offices(
    *,
    positions: dict[str, float],
    is_day_chart: bool,
    asc_longitude: float | None = None,
    lots: dict[str, float] | None = None,
) -> HellenisticOfficeHunt:
    """
    Preserve office candidates. Do not choose a predominator or oikodespotes.
    """

    if not isinstance(is_day_chart, bool):
        raise TypeError("is_day_chart must be bool")
    if not isinstance(positions, dict):
        raise TypeError("positions must be a dict of body longitudes")
    sect_light = "Sun" if is_day_chart else "Moon"
    candidates: list[HellenisticOfficeCandidate] = []

    def add(
        name: str,
        kind: str,
        longitude: float | None,
        *,
        missing_reason: str | None = None,
    ) -> None:
        house = None
        angular = None
        if longitude is not None:
            if not isfinite(longitude):
                raise ValueError(f"{name} longitude must be finite")
            longitude = longitude % 360.0
            if asc_longitude is not None:
                if not isfinite(asc_longitude):
                    raise ValueError("asc_longitude must be finite")
                house = _place_from_asc(longitude, asc_longitude)
                angular = house in {1, 4, 7, 10}
        candidates.append(
            HellenisticOfficeCandidate(
                name=name,
                kind=kind,
                longitude=longitude,
                house=house,
                is_sect_light=name == sect_light if kind == "luminary" else None,
                is_angular=angular,
                reason=missing_reason,
            )
        )

    for name in HELLENISTIC_CLASSICAL_PLANETS:
        if name in positions:
            add(name, "luminary" if name in {"Sun", "Moon"} else "planet", positions[name])
        else:
            add(name, "luminary" if name in {"Sun", "Moon"} else "planet", None, missing_reason="longitude_not_supplied")
    if lots:
        for name, longitude in lots.items():
            add(name, "lot", longitude)
    if asc_longitude is not None:
        add("Ascendant", "angle", asc_longitude)
    else:
        add(
            "Ascendant",
            "angle",
            None,
            missing_reason="asc_longitude_not_supplied",
        )

    return HellenisticOfficeHunt(
        status=HellenisticOfficeStatus.NOT_EVALUABLE,
        predominator=None,
        house_master=None,
        candidates=tuple(candidates),
        reason=OFFICE_NOT_ADMITTED_REASON,
    )
