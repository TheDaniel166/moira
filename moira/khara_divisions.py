"""Inclusive Moon Navamsa and Lagna Drekkana counts from Jataka Parijata."""
from dataclasses import dataclass, field
from typing import Literal

from .constants import SIGNS
from .varga import _varga_partition, varga_sign_index
from .vedic_dignities import _SIGN_RULER

__all__ = ["KharaCell", "KharaDivision", "KharaDivisionsResult", "khara_divisions"]


@dataclass(frozen=True, slots=True)
class KharaCell:
    """A half-open zodiac cell, its one-based ordinals, and its varga projection."""

    zodiac_ordinal: int
    sign_ordinal: int
    zodiac_sign: str
    arc_start_arcseconds: int
    arc_end_arcseconds: int
    varga_sign: str
    varga_lord: str


@dataclass(frozen=True, slots=True)
class KharaDivision:
    """The seed and the cell found by counting it as the first."""

    reference: Literal["Moon", "Lagna"]
    sidereal_longitude: float
    division: Literal[9, 3]
    count: Literal[64, 22]
    seed: KharaCell
    target: KharaCell


@dataclass(frozen=True, slots=True)
class KharaDivisionsResult:
    """Both counts in the Jataka Parijata V.56 inclusive profile."""

    navamsa_64: KharaDivision
    drekkana_22: KharaDivision
    profile_id: Literal["jataka_parijata_inclusive"] = field(init=False, default="jataka_parijata_inclusive")
    source_reference: str = field(init=False, default="Jataka Parijata, Sastri vol. I, V.56 and I.25, 30, 32–33")


def _cell(index: int, division: int) -> KharaCell:
    sign_index, ordinal = divmod(index, division)
    width = 108_000 // division
    # Use the interior of the exact cell for the established varga projection.
    projected = varga_sign_index((index + 0.5) * width / 3600, division)
    return KharaCell(index + 1, ordinal + 1, SIGNS[sign_index],
                     index * width, (index + 1) * width, SIGNS[projected], _SIGN_RULER[projected])


def khara_divisions(moon_sidereal_longitude: float, lagna_sidereal_longitude: float) -> KharaDivisionsResult:
    """Count 64 D9 cells from the Moon and 22 trinal D3 cells from Lagna."""
    moon, d9, _ = _varga_partition(moon_sidereal_longitude, 9)
    lagna, d3, _ = _varga_partition(lagna_sidereal_longitude, 3)
    return KharaDivisionsResult(
        KharaDivision("Moon", moon, 9, 64, _cell(d9, 9), _cell((d9 + 63) % 108, 9)),
        KharaDivision("Lagna", lagna, 3, 22, _cell(d3, 3), _cell((d3 + 21) % 36, 3)),
    )
