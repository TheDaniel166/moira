"""Opt-in H13/H32/H36/H40 longitude sets with exact rational-turn metadata.

Only primitive fractions below half a turn are new targets; reducible members
already belong to lower harmonics. Names are unambiguous fraction labels.
Published alternatives and the 12/H orb policy are documented in the Aspect
Backend Standard. These sets do not change Aspect.ALL or ASPECT_TIERS.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from .constants import AspectDefinition

__all__ = ["OptionalAspect", "OPTIONAL_ASPECT_SETS", "OPTIONAL_ASPECT_FRACTIONS"]

_NUMERATORS = {
    13: (1, 2, 3, 4, 5, 6),
    32: (1, 3, 5, 7, 9, 11, 13, 15),
    36: (1, 5, 7, 11, 13, 17),
    40: (1, 3, 7, 9, 11, 13, 17, 19),
}
_REFERENCE_ORB_DEG = 12.0


@dataclass(frozen=True, slots=True)
class OptionalAspect:
    """Exact rational identity and immutable geometry for an optional target."""

    numerator: int
    denominator: int
    definition: AspectDefinition


OPTIONAL_ASPECT_SETS: Mapping[str, tuple[OptionalAspect, ...]] = MappingProxyType({
    f"H{denominator}": tuple(
        OptionalAspect(
            numerator,
            denominator,
            AspectDefinition(
                f"H{denominator} {numerator}/{denominator}",
                360 * numerator / denominator,
                _REFERENCE_ORB_DEG / denominator,
                f"{numerator}/{denominator}",
                False,
            ),
        )
        for numerator in numerators
    )
    for denominator, numerators in _NUMERATORS.items()
})
OPTIONAL_ASPECT_FRACTIONS: Mapping[str, tuple[int, int]] = MappingProxyType({
    aspect.definition.name: (aspect.numerator, aspect.denominator)
    for aspects in OPTIONAL_ASPECT_SETS.values() for aspect in aspects
})


def _normalized_optional_sets(values: Sequence[str]) -> tuple[str, ...]:
    """Validate, freeze, and order set keys in catalog order, ignoring case."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (tuple, list)):
        raise ValueError("optional_sets must be a list or tuple of H13, H32, H36, H40")
    if any(not isinstance(value, str) or value != value.strip() for value in values):
        raise ValueError("optional_sets must contain trimmed set names")
    keys = tuple(value.upper() for value in values)
    if len(set(keys)) != len(keys):
        raise ValueError("optional_sets must be unique")
    if any(key not in OPTIONAL_ASPECT_SETS for key in keys):
        raise ValueError("optional_sets must name H13, H32, H36, or H40")
    return tuple(key for key in OPTIONAL_ASPECT_SETS if key in keys)


def _optional_definitions(values: Sequence[str]) -> tuple[AspectDefinition, ...]:
    return tuple(
        aspect.definition
        for key in _normalized_optional_sets(values)
        for aspect in OPTIONAL_ASPECT_SETS[key]
    )
