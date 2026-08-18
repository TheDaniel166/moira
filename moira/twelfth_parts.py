"""
Natal Hellenistic twelfth-parts (dodekatemoria).

Owns the 2°30′ equal division of a 30° sign and the ordinary 12× natal
projection. Does not own Vedic Dwadashamsa, Nine Parts, or electional
Sahl/Dorotheus twelfth-part clauses.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .constants import SIGNS, sign_of

TWELFTH_PART_SPAN_DEG = 2.5
TWELFTH_PARTS_PER_SIGN = 12
SIGN_SPAN_DEG = 30.0

__all__ = [
    "TWELFTH_PART_SPAN_DEG",
    "TWELFTH_PARTS_PER_SIGN",
    "TwelfthPartPosition",
    "twelfth_part_of",
]


@dataclass(frozen=True, slots=True)
class TwelfthPartPosition:
    """Score-free natal twelfth-part of one ecliptic longitude."""

    occupied_sign: str
    occupied_sign_degree: float
    slice_index: int
    twelfth_part_sign: str
    projected_longitude: float
    source_longitude: float

    def __post_init__(self) -> None:
        if self.occupied_sign not in SIGNS:
            raise ValueError(
                f"TwelfthPartPosition.occupied_sign must be a zodiac sign, "
                f"got {self.occupied_sign!r}"
            )
        if self.twelfth_part_sign not in SIGNS:
            raise ValueError(
                f"TwelfthPartPosition.twelfth_part_sign must be a zodiac sign, "
                f"got {self.twelfth_part_sign!r}"
            )
        if type(self.slice_index) is not int or not (
            0 <= self.slice_index < TWELFTH_PARTS_PER_SIGN
        ):
            raise ValueError(
                "TwelfthPartPosition.slice_index must be an int in 0..11, "
                f"got {self.slice_index!r}"
            )
        if not (
            0.0 <= self.occupied_sign_degree < SIGN_SPAN_DEG
            and isfinite(self.occupied_sign_degree)
        ):
            raise ValueError(
                "TwelfthPartPosition.occupied_sign_degree must be finite "
                f"and in [0, 30), got {self.occupied_sign_degree!r}"
            )
        if not isfinite(self.projected_longitude):
            raise ValueError(
                "TwelfthPartPosition.projected_longitude must be finite"
            )
        if not isfinite(self.source_longitude):
            raise ValueError(
                "TwelfthPartPosition.source_longitude must be finite"
            )


def twelfth_part_of(longitude: float) -> TwelfthPartPosition:
    """
    Project one ecliptic longitude to its natal twelfth-part.

    ``projected_longitude = (sign_start + 12 × degree_in_sign) mod 360``.
    Slice seams are left-closed and right-open.
    """

    if not isfinite(longitude):
        raise ValueError(
            f"twelfth_part_of longitude must be finite, got {longitude!r}"
        )
    source = longitude % 360.0
    occupied_sign, _symbol, occupied_degree = sign_of(source)
    sign_index = SIGNS.index(occupied_sign)
    slice_index = min(
        TWELFTH_PARTS_PER_SIGN - 1,
        int(occupied_degree / TWELFTH_PART_SPAN_DEG),
    )
    twelfth_index = (sign_index + slice_index) % 12
    projected = (
        sign_index * SIGN_SPAN_DEG + occupied_degree * TWELFTH_PARTS_PER_SIGN
    ) % 360.0
    return TwelfthPartPosition(
        occupied_sign=occupied_sign,
        occupied_sign_degree=occupied_degree,
        slice_index=slice_index,
        twelfth_part_sign=SIGNS[twelfth_index],
        projected_longitude=projected,
        source_longitude=source,
    )
