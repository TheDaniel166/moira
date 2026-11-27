"""Source-owned Pushkara Navamsa and Pushkara Bhaga assessments."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from .constants import SIGNS
from .varga import _navamsa_partition

__all__ = ["PushkaraBhagaProfile", "PushkaraResult", "pushkara"]

_NAVAMSA_SOURCE = "Vidyamadhaviyam, Shama Sastry 1923, Vishnusarma on 1.18 (printed p. 31)"
_NAVAMSA_ORDINALS = ((7, 9), (3, 5), (6, 8), (1, 3))


class PushkaraBhagaProfile(str, Enum):
    """Two independently attested Pushkara Bhaga degree tables."""

    JATAKA_PARIJATA_SASTRI = "jataka_parijata_sastri"
    VIDYAMADHAVIYAM_1923 = "vidyamadhaviyam_1923"


_BHAGA_TABLES = {
    PushkaraBhagaProfile.JATAKA_PARIJATA_SASTRI: (
        (21, 14, 18, 8, 19, 9, 24, 11, 23, 14, 19, 9),
        "Jataka Parijata, Sastri vol. I, 1.58 (printed p. 39)",
        "moon",
    ),
    PushkaraBhagaProfile.VIDYAMADHAVIYAM_1923: (
        (21, 14, 24, 7) * 3,
        "Vidyamadhaviyam, Shama Sastry 1923, 1.18 with Vishnusarma (printed pp. 30–31)",
        "sign_degree",
    ),
}


@dataclass(frozen=True, slots=True)
class PushkaraResult:
    """One longitude compared with the Navamsa rule and a selected Bhaga table."""

    sidereal_longitude: float
    sign: str
    degree_in_sign: float
    navamsa_ordinal: int
    navamsa_sign: str
    pushkara_navamsa_ordinals: tuple[int, int]
    in_pushkara_navamsa: bool
    navamsa_source_reference: str
    bhaga_profile: PushkaraBhagaProfile
    bhaga_source_reference: str
    bhaga_source_subject: Literal["moon", "sign_degree"]
    bhaga_degree_ordinal: int
    bhaga_degree_interval: tuple[int, int]
    in_pushkara_bhaga: bool


def pushkara(sidereal_longitude: float, *, bhaga_profile: PushkaraBhagaProfile) -> PushkaraResult:
    """Evaluate a longitude geometrically against both independently sourced rules.

    Bhaga degree n is represented by the half-open interval [n - 1, n) within
    the sign. The source subject records where the selected text attaches its
    doctrine. Membership itself describes an angle, independent of chart body.
    """
    if not isinstance(bhaga_profile, PushkaraBhagaProfile):
        raise TypeError("bhaga_profile must be a PushkaraBhagaProfile")
    longitude, segment, _ = _navamsa_partition(sidereal_longitude)
    sign_index, within_sign = divmod(segment, 9)
    degree_in_sign = longitude - 30 * sign_index
    ordinal = within_sign + 1
    navamsas = _NAVAMSA_ORDINALS[sign_index % 4]
    degrees, bhaga_source, bhaga_subject = _BHAGA_TABLES[bhaga_profile]
    degree = degrees[sign_index]
    return PushkaraResult(
        sidereal_longitude=longitude,
        sign=SIGNS[sign_index],
        degree_in_sign=degree_in_sign,
        navamsa_ordinal=ordinal,
        navamsa_sign=SIGNS[segment % 12],
        pushkara_navamsa_ordinals=navamsas,
        in_pushkara_navamsa=ordinal in navamsas,
        navamsa_source_reference=_NAVAMSA_SOURCE,
        bhaga_profile=bhaga_profile,
        bhaga_source_reference=bhaga_source,
        bhaga_source_subject=bhaga_subject,
        bhaga_degree_ordinal=degree,
        bhaga_degree_interval=(degree - 1, degree),
        in_pushkara_bhaga=degree - 1 <= degree_in_sign < degree,
    )
