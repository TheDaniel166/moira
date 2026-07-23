"""
Church of Light natal Astrodynes - constitutional engine.

This module owns the source tables, computation truth, classification, fixed
doctrine, relations, integrated body profiles, sign/house and Class 5 summary
aggregates, network projection, and hardening contract for natal Astrodynes.
Package-root and facade exposure, plus the typed optional REST transport, are
curated at SCP Phase 12.

Governing sources
-----------------
* Elbert Benjamine and W. M. A. Drake, *The Astrodyne Manual* (1946).
* Church of Light, *Astrological Delineation with Astrodynes: Class 1 -
  The Planets*, page 3, ``Table of Essential Dignities``.
* Church of Light, *Astrological Delineation with Astrodynes: Class 5 -
  Summary - Societies, Trinities, Elements, & Qualities*.

The Astrodyne dignity table is its own Hermetic doctrine.  In particular,
Mercury is exalted at Aquarius 15 and falls at Leo 15.  Nothing in this module
delegates to or changes :mod:`moira.dignities`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


ASTRODYNE_PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)

ASTRODYNE_POINTS: tuple[str, ...] = ("M.C.", "Asc.")

# The manual assigns each angle point a fixed house-position power.
ASTRODYNE_ANGLE_POINT_POWER: float = 15.0

# Parallel has a fixed one-degree orb in every house/body column.
ASTRODYNE_PARALLEL_ORB_ARCMIN: float = 60.0

ASTRODYNE_SIGNS: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

ASTRODYNE_HOUSE_CLASSES: tuple[str, ...] = (
    "angular",
    "succedent",
    "cadent",
)


# ---------------------------------------------------------------------------
# Phase 2 - Classification
# ---------------------------------------------------------------------------


class AstrodyneBodyKind(StrEnum):
    """Source-supported body classes in the natal Astrodyne system."""

    PLANET = "planet"
    ANGLE = "angle"


class AstrodyneDignityCondition(StrEnum):
    """The eight scored conditions in the Church of Light dignity table."""

    DEGREE_OF_EXALTATION = "degree_of_exaltation"
    EXALTATION = "exaltation"
    HOME = "home"
    HARMONY = "harmony"
    DEGREE_OF_FALL = "degree_of_fall"
    FALL = "fall"
    DETRIMENT = "detriment"
    INHARMONY = "inharmony"


class AstrodyneAspectFamily(StrEnum):
    """Harmony family assigned by the manual to a scored aspect."""

    HARMONIOUS = "harmonious"
    DISCORDANT = "discordant"
    NEUTRAL = "neutral"


class AstrodyneRelationKind(StrEnum):
    """Relation families admitted by the bounded natal subsystem."""

    ZODIACAL_ASPECT = "zodiacal_aspect"
    PARALLEL = "parallel"
    MUTUAL_RECEPTION = "mutual_reception"


class AstrodyneContributionSource(StrEnum):
    """Named computational sources preserved in integrated profiles."""

    HOUSE_POSITION = "house_position"
    ZODIACAL_ASPECT = "zodiacal_aspect"
    PARALLEL = "parallel"
    ESSENTIAL_DIGNITY = "essential_dignity"
    MUTUAL_RECEPTION = "mutual_reception"


class AstrodyneSummaryFamily(StrEnum):
    """Official Church of Light natal summary families."""

    SOCIETY = "society"
    TRINITY = "trinity"
    ELEMENT = "element"
    QUALITY = "quality"


class AstrodyneParallelGeometry(StrEnum):
    """Admitted declination geometry, fixed by the manual's worked examples."""

    MAGNITUDE_DIFFERENCE = "magnitude_difference"


class AstrodyneMercuryOrbRule(StrEnum):
    """Admitted Mercury orb doctrine."""

    PLANET_PRESENCE_LUMINARY_SCORE = "planet_presence_luminary_score"


# ---------------------------------------------------------------------------
# Phase 4 - Doctrine / Policy Surface
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AstrodynePolicy:
    """
    Explicit fixed doctrine for Church of Light natal Astrodynes.

    Phase 4 does not invent alternatives.  Each field is visible so consumers
    can inspect the governing choices, and construction rejects any value not
    supported by the confirmed source.
    """

    degree_emphasis_orb_deg: float = 1.0
    parallel_orb_arcmin: float = ASTRODYNE_PARALLEL_ORB_ARCMIN
    parallel_geometry: AstrodyneParallelGeometry = (
        AstrodyneParallelGeometry.MAGNITUDE_DIFFERENCE
    )
    mercury_orb_rule: AstrodyneMercuryOrbRule = (
        AstrodyneMercuryOrbRule.PLANET_PRESENCE_LUMINARY_SCORE
    )
    mutual_reception_bonus: float = 5.0

    def __post_init__(self) -> None:
        if self.degree_emphasis_orb_deg != 1.0:
            raise ValueError("the admitted degree-emphasis orb is exactly 1 degree")
        if self.parallel_orb_arcmin != ASTRODYNE_PARALLEL_ORB_ARCMIN:
            raise ValueError("the admitted parallel orb is exactly 60 arcminutes")
        if self.parallel_geometry is not AstrodyneParallelGeometry.MAGNITUDE_DIFFERENCE:
            raise ValueError("only magnitude-difference parallel geometry is admitted")
        if self.mercury_orb_rule is not AstrodyneMercuryOrbRule.PLANET_PRESENCE_LUMINARY_SCORE:
            raise ValueError("only the manual's two-stage Mercury orb rule is admitted")
        if self.mutual_reception_bonus != 5.0:
            raise ValueError("the admitted mutual-reception bonus is exactly 5")


DEFAULT_ASTRODYNE_POLICY = AstrodynePolicy()


ASTRODYNE_SOCIETY_GROUPS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("Personal", (12, 1, 2, 3)),
    ("Companionship", (4, 5, 6, 7)),
    ("Public", (8, 9, 10, 11)),
)

ASTRODYNE_TRINITY_GROUPS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("Life", (1, 5, 9)),
    ("Wealth", (2, 6, 10)),
    ("Association", (3, 7, 11)),
    ("Psychism", (4, 8, 12)),
)

ASTRODYNE_ELEMENT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Fire", ("Aries", "Leo", "Sagittarius")),
    ("Earth", ("Taurus", "Virgo", "Capricorn")),
    ("Air", ("Gemini", "Libra", "Aquarius")),
    ("Water", ("Cancer", "Scorpio", "Pisces")),
)

ASTRODYNE_QUALITY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Movable", ("Aries", "Cancer", "Libra", "Capricorn")),
    ("Fixed", ("Taurus", "Leo", "Scorpio", "Aquarius")),
    ("Mutable", ("Gemini", "Virgo", "Sagittarius", "Pisces")),
)


@dataclass(frozen=True, slots=True)
class AstrodyneDignityRow:
    """One directly transcribed row of the Church of Light dignity table."""

    planet: str
    home_signs: tuple[str, ...]
    detriment_signs: tuple[str, ...]
    exaltation_sign: str
    exaltation_degree: float
    fall_sign: str
    fall_degree: float
    harmony_sign: str
    inharmony_sign: str

    def __post_init__(self) -> None:
        if self.planet not in ASTRODYNE_PLANETS:
            raise ValueError(f"unsupported Astrodyne planet: {self.planet!r}")
        signs = (
            *self.home_signs,
            *self.detriment_signs,
            self.exaltation_sign,
            self.fall_sign,
            self.harmony_sign,
            self.inharmony_sign,
        )
        invalid = [sign for sign in signs if sign not in ASTRODYNE_SIGNS]
        if invalid:
            raise ValueError(f"invalid Astrodyne dignity signs: {invalid!r}")
        for label, value in (
            ("exaltation_degree", self.exaltation_degree),
            ("fall_degree", self.fall_degree),
        ):
            if not isfinite(value) or not 0.0 <= value < 30.0:
                raise ValueError(f"{label} must be finite and in [0, 30)")


ASTRODYNE_DIGNITY_ROWS: tuple[AstrodyneDignityRow, ...] = (
    AstrodyneDignityRow(
        "Sun", ("Leo",), ("Aquarius",), "Aries", 19.0,
        "Libra", 19.0, "Sagittarius", "Gemini",
    ),
    AstrodyneDignityRow(
        "Moon", ("Cancer",), ("Capricorn",), "Taurus", 3.0,
        "Scorpio", 3.0, "Pisces", "Virgo",
    ),
    AstrodyneDignityRow(
        "Mercury", ("Gemini", "Virgo"), ("Sagittarius", "Pisces"),
        "Aquarius", 15.0, "Leo", 15.0, "Scorpio", "Taurus",
    ),
    AstrodyneDignityRow(
        "Venus", ("Taurus", "Libra"), ("Aries", "Scorpio"),
        "Pisces", 27.0, "Virgo", 27.0, "Aquarius", "Leo",
    ),
    AstrodyneDignityRow(
        "Mars", ("Aries", "Scorpio"), ("Taurus", "Libra"),
        "Capricorn", 28.0, "Cancer", 28.0, "Leo", "Aquarius",
    ),
    AstrodyneDignityRow(
        "Jupiter", ("Sagittarius", "Pisces"), ("Gemini", "Virgo"),
        "Cancer", 15.0, "Capricorn", 15.0, "Taurus", "Scorpio",
    ),
    AstrodyneDignityRow(
        "Saturn", ("Capricorn", "Aquarius"), ("Cancer", "Leo"),
        "Libra", 21.0, "Aries", 21.0, "Virgo", "Pisces",
    ),
    AstrodyneDignityRow(
        "Uranus", ("Aquarius",), ("Leo",), "Gemini", 7.0,
        "Sagittarius", 7.0, "Libra", "Aries",
    ),
    AstrodyneDignityRow(
        "Neptune", ("Pisces",), ("Virgo",), "Sagittarius", 18.0,
        "Gemini", 18.0, "Cancer", "Capricorn",
    ),
    AstrodyneDignityRow(
        "Pluto", ("Scorpio",), ("Taurus",), "Leo", 17.0,
        "Aquarius", 17.0, "Aries", "Libra",
    ),
)

_DIGNITY_BY_PLANET: dict[str, AstrodyneDignityRow] = {
    row.planet: row for row in ASTRODYNE_DIGNITY_ROWS
}


@dataclass(frozen=True, slots=True)
class AstrodyneHousePowerRow:
    """One directly transcribed house-position power interval."""

    house: int
    weaker_cusp_power: float
    stronger_cusp_power: float

    @property
    def variation(self) -> float:
        return self.stronger_cusp_power - self.weaker_cusp_power


ASTRODYNE_HOUSE_POWER_ROWS: tuple[AstrodyneHousePowerRow, ...] = (
    AstrodyneHousePowerRow(6, 6.50, 7.00),
    AstrodyneHousePowerRow(5, 7.00, 7.50),
    AstrodyneHousePowerRow(3, 7.50, 8.00),
    AstrodyneHousePowerRow(2, 8.00, 8.50),
    AstrodyneHousePowerRow(12, 8.60, 9.30),
    AstrodyneHousePowerRow(9, 9.30, 10.00),
    AstrodyneHousePowerRow(8, 10.00, 10.90),
    AstrodyneHousePowerRow(11, 10.90, 11.90),
    AstrodyneHousePowerRow(4, 12.00, 14.00),
    AstrodyneHousePowerRow(7, 12.50, 14.50),
    AstrodyneHousePowerRow(10, 13.00, 15.00),
    AstrodyneHousePowerRow(1, 13.00, 15.00),
)

_HOUSE_POWER_BY_NUMBER: dict[int, AstrodyneHousePowerRow] = {
    row.house: row for row in ASTRODYNE_HOUSE_POWER_ROWS
}


@dataclass(frozen=True, slots=True)
class AstrodyneAspectOrbRow:
    """One directly transcribed row of the natal aspect-orb table."""

    aspect: str
    exact_angle_deg: float
    succedent_planet_deg: float
    succedent_luminary_deg: float
    angular_planet_deg: float
    angular_luminary_deg: float
    cadent_planet_deg: float
    cadent_luminary_deg: float

    def as_tuple(self) -> tuple[float, float, float, float, float, float, float]:
        return (
            self.exact_angle_deg,
            self.succedent_planet_deg,
            self.succedent_luminary_deg,
            self.angular_planet_deg,
            self.angular_luminary_deg,
            self.cadent_planet_deg,
            self.cadent_luminary_deg,
        )


ASTRODYNE_ASPECT_ORB_ROWS: tuple[AstrodyneAspectOrbRow, ...] = (
    AstrodyneAspectOrbRow("conjunction", 0.0, 10.0, 13.0, 12.0, 15.0, 8.0, 11.0),
    AstrodyneAspectOrbRow("semi-sextile", 30.0, 2.0, 3.0, 3.0, 4.0, 1.0, 2.0),
    AstrodyneAspectOrbRow("sextile", 60.0, 6.0, 7.0, 7.0, 8.0, 5.0, 6.0),
    AstrodyneAspectOrbRow("square", 90.0, 8.0, 10.0, 10.0, 12.0, 6.0, 8.0),
    AstrodyneAspectOrbRow("trine", 120.0, 8.0, 10.0, 10.0, 12.0, 6.0, 8.0),
    AstrodyneAspectOrbRow("inconjunct", 150.0, 2.0, 3.0, 3.0, 4.0, 1.0, 2.0),
    AstrodyneAspectOrbRow("semi-square", 45.0, 4.0, 5.0, 5.0, 6.0, 3.0, 4.0),
    AstrodyneAspectOrbRow("sesqui-square", 135.0, 4.0, 5.0, 5.0, 6.0, 3.0, 4.0),
    AstrodyneAspectOrbRow("opposition", 180.0, 10.0, 13.0, 12.0, 15.0, 8.0, 11.0),
)

_ASPECT_ORB_ROWS: dict[str, tuple[float, float, float, float, float, float, float]] = {
    row.aspect: row.as_tuple() for row in ASTRODYNE_ASPECT_ORB_ROWS
}

ASTRODYNE_ASPECTS: tuple[str, ...] = (*_ASPECT_ORB_ROWS, "parallel")

_HARMONIOUS_ASPECTS: frozenset[str] = frozenset(
    {"trine", "sextile", "semi-sextile"}
)
_DISCORDANT_ASPECTS: frozenset[str] = frozenset(
    {"opposition", "square", "sesqui-square", "semi-square"}
)


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _policy(policy: AstrodynePolicy | None) -> AstrodynePolicy:
    if policy is None:
        return DEFAULT_ASTRODYNE_POLICY
    if not isinstance(policy, AstrodynePolicy):
        raise TypeError("policy must be an AstrodynePolicy")
    return policy


def _canonical_planet(planet: str) -> str:
    if not isinstance(planet, str):
        raise TypeError("planet must be a string")
    key = planet.strip().casefold()
    for candidate in ASTRODYNE_PLANETS:
        if candidate.casefold() == key:
            return candidate
    raise ValueError(f"unsupported Astrodyne planet: {planet!r}")


def _canonical_body(body: str) -> str:
    if not isinstance(body, str):
        raise TypeError("body must be a string")
    aliases = {
        "mc": "M.C.",
        "m.c.": "M.C.",
        "midheaven": "M.C.",
        "asc": "Asc.",
        "asc.": "Asc.",
        "ascendant": "Asc.",
    }
    key = body.strip().casefold()
    if key in aliases:
        return aliases[key]
    return _canonical_planet(body)


def _canonical_sign(sign: str) -> str:
    if not isinstance(sign, str):
        raise TypeError("sign must be a string")
    key = sign.strip().casefold()
    for candidate in ASTRODYNE_SIGNS:
        if candidate.casefold() == key:
            return candidate
    raise ValueError(f"unsupported zodiac sign: {sign!r}")


def _canonical_house_class(house_class: str) -> str:
    if not isinstance(house_class, str):
        raise TypeError("house_class must be a string")
    result = house_class.strip().casefold()
    if result not in ASTRODYNE_HOUSE_CLASSES:
        raise ValueError(
            "house_class must be 'angular', 'succedent', or 'cadent'"
        )
    return result


def _canonical_aspect(aspect: str, *, include_parallel: bool = False) -> str:
    if not isinstance(aspect, str):
        raise TypeError("aspect must be a string")
    result = aspect.strip().casefold().replace("_", " ").replace(" ", "-")
    allowed = ASTRODYNE_ASPECTS if include_parallel else tuple(_ASPECT_ORB_ROWS)
    if result not in allowed:
        raise ValueError(f"unsupported Astrodyne aspect: {aspect!r}")
    return result


def _uses_luminary_scoring(body: str) -> bool:
    return body in {"Sun", "Moon", "Mercury"}


def _uses_luminary_presence(body: str) -> bool:
    return body in {"Sun", "Moon"}


def _orb_for(
    aspect: str,
    house_class: str,
    *,
    luminary_column: bool,
) -> float:
    row = _ASPECT_ORB_ROWS[aspect]
    offset = {
        "succedent": 1,
        "angular": 3,
        "cadent": 5,
    }[house_class]
    return row[offset + int(luminary_column)]


def _validate_point_house_class(body: str, house_class: str) -> None:
    if body in ASTRODYNE_POINTS and house_class != "angular":
        raise ValueError(f"{body} must use the angular planet orb column")


@dataclass(frozen=True, slots=True)
class AstrodyneHousePositionTruth:
    """Preserved interpolation truth for one house-position power result."""

    house: int
    distance_from_weaker_cusp_deg: float
    house_size_deg: float
    weaker_cusp_power: float
    stronger_cusp_power: float
    variation: float
    interpolation_fraction: float
    astrodyne_power: float

    def __post_init__(self) -> None:
        if self.house not in range(1, 13):
            raise ValueError("house must be in [1, 12]")
        if not 0.0 <= self.interpolation_fraction <= 1.0:
            raise ValueError("interpolation_fraction must be in [0, 1]")

    @property
    def rounded_power(self) -> float:
        """Manual-facing value rounded to hundredths."""

        return round(self.astrodyne_power, 2)


def house_position_power(
    house: int,
    distance_from_weaker_cusp_deg: float,
    house_size_deg: float,
) -> AstrodyneHousePositionTruth:
    """Compute the manual's linear house-position power interpolation."""

    if isinstance(house, bool) or not isinstance(house, int):
        raise TypeError("house must be an integer")
    try:
        row = _HOUSE_POWER_BY_NUMBER[house]
    except KeyError as exc:
        raise ValueError("house must be in [1, 12]") from exc

    distance = _finite(
        "distance_from_weaker_cusp_deg", distance_from_weaker_cusp_deg
    )
    size = _finite("house_size_deg", house_size_deg)
    if size <= 0.0:
        raise ValueError("house_size_deg must be greater than zero")
    if not 0.0 <= distance <= size:
        raise ValueError(
            "distance_from_weaker_cusp_deg must be within the house"
        )

    fraction = distance / size
    power = row.weaker_cusp_power + row.variation * fraction
    return AstrodyneHousePositionTruth(
        house=house,
        distance_from_weaker_cusp_deg=distance,
        house_size_deg=size,
        weaker_cusp_power=row.weaker_cusp_power,
        stronger_cusp_power=row.stronger_cusp_power,
        variation=row.variation,
        interpolation_fraction=fraction,
        astrodyne_power=power,
    )


@dataclass(frozen=True, slots=True)
class AstrodyneZodiacalAspectTruth:
    """Preserved orb admission and scoring truth for one zodiacal aspect."""

    body_a: str
    body_b: str
    longitude_a_deg: float
    longitude_b_deg: float
    house_class_a: str
    house_class_b: str
    aspect: str
    exact_angle_deg: float
    separation_deg: float
    distance_from_perfect_deg: float
    presence_orb_a_deg: float
    presence_orb_b_deg: float
    admitted_presence_orb_deg: float
    scoring_orb_a_deg: float
    scoring_orb_b_deg: float
    admitted_scoring_orb_deg: float
    within_orb: bool
    astrodyne_power: float

    def __post_init__(self) -> None:
        if self.within_orb != (
            self.distance_from_perfect_deg <= self.admitted_presence_orb_deg
        ):
            raise ValueError("within_orb disagrees with the preserved orb truth")
        if self.astrodyne_power < 0.0:
            raise ValueError("astrodyne_power cannot be negative")

    @property
    def orb_margin_deg(self) -> float:
        """Signed ordinary-orb margin; negative means outside admission."""

        return self.admitted_presence_orb_deg - self.distance_from_perfect_deg

    @property
    def rounded_power(self) -> float:
        return round(self.astrodyne_power, 2)


def zodiacal_aspect_power(
    body_a: str,
    longitude_a_deg: float,
    house_class_a: str,
    body_b: str,
    longitude_b_deg: float,
    house_class_b: str,
    aspect: str,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneZodiacalAspectTruth:
    """
    Compute one natal zodiacal aspect's Astrodyne power.

    Presence uses the wider ordinary orb of the two bodies.  Mercury retains a
    planet's ordinary orb for presence, but after admission its score uses the
    Sun-Moon column for Mercury's house class, exactly as the manual directs.
    """

    active_policy = _policy(policy)
    if active_policy.mercury_orb_rule is not AstrodyneMercuryOrbRule.PLANET_PRESENCE_LUMINARY_SCORE:
        raise ValueError("unsupported Mercury orb rule")
    first = _canonical_body(body_a)
    second = _canonical_body(body_b)
    first_class = _canonical_house_class(house_class_a)
    second_class = _canonical_house_class(house_class_b)
    _validate_point_house_class(first, first_class)
    _validate_point_house_class(second, second_class)
    kind = _canonical_aspect(aspect)

    longitude_a = _finite("longitude_a_deg", longitude_a_deg) % 360.0
    longitude_b = _finite("longitude_b_deg", longitude_b_deg) % 360.0
    separation = abs(longitude_a - longitude_b)
    separation = min(separation, 360.0 - separation)
    exact_angle = _ASPECT_ORB_ROWS[kind][0]
    distance = abs(separation - exact_angle)

    presence_a = _orb_for(
        kind,
        first_class,
        luminary_column=_uses_luminary_presence(first),
    )
    presence_b = _orb_for(
        kind,
        second_class,
        luminary_column=_uses_luminary_presence(second),
    )
    scoring_a = _orb_for(
        kind,
        first_class,
        luminary_column=_uses_luminary_scoring(first),
    )
    scoring_b = _orb_for(
        kind,
        second_class,
        luminary_column=_uses_luminary_scoring(second),
    )
    presence_orb = max(presence_a, presence_b)
    scoring_orb = max(scoring_a, scoring_b)
    admitted = distance <= presence_orb
    power = max(0.0, scoring_orb - distance) if admitted else 0.0

    return AstrodyneZodiacalAspectTruth(
        body_a=first,
        body_b=second,
        longitude_a_deg=longitude_a,
        longitude_b_deg=longitude_b,
        house_class_a=first_class,
        house_class_b=second_class,
        aspect=kind,
        exact_angle_deg=exact_angle,
        separation_deg=separation,
        distance_from_perfect_deg=distance,
        presence_orb_a_deg=presence_a,
        presence_orb_b_deg=presence_b,
        admitted_presence_orb_deg=presence_orb,
        scoring_orb_a_deg=scoring_a,
        scoring_orb_b_deg=scoring_b,
        admitted_scoring_orb_deg=scoring_orb,
        within_orb=admitted,
        astrodyne_power=power,
    )


@dataclass(frozen=True, slots=True)
class AstrodyneParallelAspectTruth:
    """Preserved magnitude-parallel geometry and linear power derivation."""

    body_a: str
    body_b: str
    declination_a_deg: float
    declination_b_deg: float
    house_class_a: str
    house_class_b: str
    magnitude_separation_arcmin: float
    orb_limit_arcmin: float
    perfect_conjunction_power_a: float
    perfect_conjunction_power_b: float
    scale_fraction: float
    scaled_power_a: float
    scaled_power_b: float
    within_orb: bool
    astrodyne_power: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.scale_fraction <= 1.0:
            raise ValueError("scale_fraction must be in [0, 1]")
        if self.astrodyne_power < 0.0:
            raise ValueError("astrodyne_power cannot be negative")

    @property
    def rounded_power(self) -> float:
        return round(self.astrodyne_power, 2)


def parallel_aspect_power(
    body_a: str,
    declination_a_deg: float,
    house_class_a: str,
    body_b: str,
    declination_b_deg: float,
    house_class_b: str,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneParallelAspectTruth:
    """
    Compute the manual's 60-arcminute magnitude-parallel power.

    The source examples compare absolute declination magnitudes even when the
    bodies occupy opposite hemispheres.  The signed inputs are preserved, while
    the admitted geometry is explicitly their magnitude difference.
    """

    active_policy = _policy(policy)
    if active_policy.parallel_geometry is not AstrodyneParallelGeometry.MAGNITUDE_DIFFERENCE:
        raise ValueError("unsupported parallel geometry")
    first = _canonical_body(body_a)
    second = _canonical_body(body_b)
    first_class = _canonical_house_class(house_class_a)
    second_class = _canonical_house_class(house_class_b)
    _validate_point_house_class(first, first_class)
    _validate_point_house_class(second, second_class)

    declination_a = _finite("declination_a_deg", declination_a_deg)
    declination_b = _finite("declination_b_deg", declination_b_deg)
    if not -90.0 <= declination_a <= 90.0:
        raise ValueError("declination_a_deg must be in [-90, 90]")
    if not -90.0 <= declination_b <= 90.0:
        raise ValueError("declination_b_deg must be in [-90, 90]")

    separation_arcmin = abs(abs(declination_a) - abs(declination_b)) * 60.0
    orb_limit = active_policy.parallel_orb_arcmin
    admitted = separation_arcmin <= orb_limit
    scale = max(0.0, 1.0 - separation_arcmin / orb_limit)
    perfect_a = _orb_for(
        "conjunction",
        first_class,
        luminary_column=_uses_luminary_scoring(first),
    )
    perfect_b = _orb_for(
        "conjunction",
        second_class,
        luminary_column=_uses_luminary_scoring(second),
    )
    scaled_a = perfect_a * scale
    scaled_b = perfect_b * scale
    power = max(scaled_a, scaled_b) if admitted else 0.0

    return AstrodyneParallelAspectTruth(
        body_a=first,
        body_b=second,
        declination_a_deg=declination_a,
        declination_b_deg=declination_b,
        house_class_a=first_class,
        house_class_b=second_class,
        magnitude_separation_arcmin=separation_arcmin,
        orb_limit_arcmin=orb_limit,
        perfect_conjunction_power_a=perfect_a,
        perfect_conjunction_power_b=perfect_b,
        scale_fraction=scale,
        scaled_power_a=scaled_a,
        scaled_power_b=scaled_b,
        within_orb=admitted,
        astrodyne_power=power,
    )


@dataclass(frozen=True, slots=True)
class AstrodyneEssentialDignityTruth:
    """Preserved source-row match and harmony/discord contribution."""

    planet: str
    sign: str
    sign_degree: float
    source_row: AstrodyneDignityRow
    condition: AstrodyneDignityCondition | None
    exact_degree: float | None
    distance_from_exact_degree: float | None
    degree_emphasis_applied: bool
    harmony_delta: float

    def __post_init__(self) -> None:
        if self.source_row.planet != self.planet:
            raise ValueError("source_row does not belong to planet")
        if self.condition is None and self.harmony_delta != 0.0:
            raise ValueError("an unmatched dignity must contribute zero")
        if self.degree_emphasis_applied and self.condition not in {
            "degree_of_exaltation",
            "degree_of_fall",
        }:
            raise ValueError("degree emphasis requires a degree condition")

    @property
    def harmony(self) -> float:
        return max(0.0, self.harmony_delta)

    @property
    def discord(self) -> float:
        return max(0.0, -self.harmony_delta)

    @property
    def is_dignified(self) -> bool:
        return self.harmony_delta > 0.0

    @property
    def is_debilitated(self) -> bool:
        return self.harmony_delta < 0.0


def essential_dignity(
    planet: str,
    sign: str,
    sign_degree: float,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneEssentialDignityTruth:
    """Evaluate one position against the exact Church of Light dignity row."""

    active_policy = _policy(policy)
    body = _canonical_planet(planet)
    zodiac_sign = _canonical_sign(sign)
    degree = _finite("sign_degree", sign_degree)
    if not 0.0 <= degree < 30.0:
        raise ValueError("sign_degree must be in [0, 30)")

    row = _DIGNITY_BY_PLANET[body]
    condition: AstrodyneDignityCondition | None = None
    exact_degree: float | None = None
    distance: float | None = None
    emphasized = False
    delta = 0.0

    if zodiac_sign == row.exaltation_sign:
        exact_degree = row.exaltation_degree
        distance = abs(degree - exact_degree)
        if distance <= active_policy.degree_emphasis_orb_deg:
            condition = AstrodyneDignityCondition.DEGREE_OF_EXALTATION
            emphasized = True
            delta = 4.0
        else:
            condition = AstrodyneDignityCondition.EXALTATION
            delta = 3.0
    elif zodiac_sign == row.fall_sign:
        exact_degree = row.fall_degree
        distance = abs(degree - exact_degree)
        if distance <= active_policy.degree_emphasis_orb_deg:
            condition = AstrodyneDignityCondition.DEGREE_OF_FALL
            emphasized = True
            delta = -4.0
        else:
            condition = AstrodyneDignityCondition.FALL
            delta = -3.0
    elif zodiac_sign in row.home_signs:
        condition = AstrodyneDignityCondition.HOME
        delta = 2.0
    elif zodiac_sign in row.detriment_signs:
        condition = AstrodyneDignityCondition.DETRIMENT
        delta = -2.0
    elif zodiac_sign == row.harmony_sign:
        condition = AstrodyneDignityCondition.HARMONY
        delta = 1.0
    elif zodiac_sign == row.inharmony_sign:
        condition = AstrodyneDignityCondition.INHARMONY
        delta = -1.0

    return AstrodyneEssentialDignityTruth(
        planet=body,
        sign=zodiac_sign,
        sign_degree=degree,
        source_row=row,
        condition=condition,
        exact_degree=exact_degree,
        distance_from_exact_degree=distance,
        degree_emphasis_applied=emphasized,
        harmony_delta=delta,
    )


@dataclass(frozen=True, slots=True)
class AstrodyneNatureContribution:
    """One preserved benefic or malefic contribution to an aspect."""

    body: str
    fraction: float
    harmony: float
    discord: float


@dataclass(frozen=True, slots=True)
class AstrodyneAspectHarmonyTruth:
    """Preserved translation from aspect power to harmony and discord."""

    body_a: str
    body_b: str
    aspect: str
    family: AstrodyneAspectFamily
    astrodyne_power: float
    base_harmony: float
    base_discord: float
    nature_contributions: tuple[AstrodyneNatureContribution, ...]
    total_harmony: float
    total_discord: float
    net_harmony: float

    def __post_init__(self) -> None:
        if self.astrodyne_power < 0.0:
            raise ValueError("astrodyne_power cannot be negative")
        if abs(self.net_harmony - (self.total_harmony - self.total_discord)) > 1e-12:
            raise ValueError("net_harmony disagrees with harmony and discord")

    @property
    def is_harmonious(self) -> bool:
        return self.net_harmony > 0.0

    @property
    def is_discordant(self) -> bool:
        return self.net_harmony < 0.0


def aspect_harmony(
    body_a: str,
    body_b: str,
    aspect: str,
    astrodyne_power: float,
) -> AstrodyneAspectHarmonyTruth:
    """Translate aspect power through the manual's aspect and planet natures."""

    first = _canonical_body(body_a)
    second = _canonical_body(body_b)
    kind = _canonical_aspect(aspect, include_parallel=True)
    power = _finite("astrodyne_power", astrodyne_power)
    if power < 0.0:
        raise ValueError("astrodyne_power cannot be negative")

    if kind in _HARMONIOUS_ASPECTS:
        family = AstrodyneAspectFamily.HARMONIOUS
    elif kind in _DISCORDANT_ASPECTS:
        family = AstrodyneAspectFamily.DISCORDANT
    else:
        family = AstrodyneAspectFamily.NEUTRAL
    base_harmony = power if family is AstrodyneAspectFamily.HARMONIOUS else 0.0
    base_discord = power if family is AstrodyneAspectFamily.DISCORDANT else 0.0
    contributions: list[AstrodyneNatureContribution] = []

    for body in (first, second):
        if body == "Jupiter":
            contributions.append(
                AstrodyneNatureContribution(body, 0.5, power * 0.5, 0.0)
            )
        elif body == "Venus":
            contributions.append(
                AstrodyneNatureContribution(body, 0.25, power * 0.25, 0.0)
            )
        elif body == "Saturn":
            contributions.append(
                AstrodyneNatureContribution(body, 0.5, 0.0, power * 0.5)
            )
        elif body == "Mars":
            contributions.append(
                AstrodyneNatureContribution(body, 0.25, 0.0, power * 0.25)
            )

    total_harmony = base_harmony + sum(item.harmony for item in contributions)
    total_discord = base_discord + sum(item.discord for item in contributions)
    return AstrodyneAspectHarmonyTruth(
        body_a=first,
        body_b=second,
        aspect=kind,
        family=family,
        astrodyne_power=power,
        base_harmony=base_harmony,
        base_discord=base_discord,
        nature_contributions=tuple(contributions),
        total_harmony=total_harmony,
        total_discord=total_discord,
        net_harmony=total_harmony - total_discord,
    )


# ---------------------------------------------------------------------------
# Phases 5-6 - Relational Formalization and Hardening
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AstrodyneAspectRelation:
    """One evaluated zodiacal-aspect or declination-parallel relation."""

    kind: AstrodyneRelationKind
    body_a: str
    body_b: str
    aspect: str
    power_truth: AstrodyneZodiacalAspectTruth | AstrodyneParallelAspectTruth
    harmony_truth: AstrodyneAspectHarmonyTruth

    def __post_init__(self) -> None:
        if self.kind not in {
            AstrodyneRelationKind.ZODIACAL_ASPECT,
            AstrodyneRelationKind.PARALLEL,
        }:
            raise ValueError("AstrodyneAspectRelation requires an aspect kind")
        if self.kind is AstrodyneRelationKind.PARALLEL and self.aspect != "parallel":
            raise ValueError("parallel relation must use the parallel aspect label")
        if self.power_truth.body_a != self.body_a or self.power_truth.body_b != self.body_b:
            raise ValueError("power truth bodies disagree with relation bodies")
        if self.harmony_truth.body_a != self.body_a or self.harmony_truth.body_b != self.body_b:
            raise ValueError("harmony truth bodies disagree with relation bodies")
        if self.harmony_truth.aspect != self.aspect:
            raise ValueError("harmony truth aspect disagrees with relation aspect")
        if self.harmony_truth.astrodyne_power != self.power:
            raise ValueError("harmony truth power disagrees with relation power")

    @property
    def detected(self) -> bool:
        return True

    @property
    def admitted(self) -> bool:
        return self.power_truth.within_orb

    @property
    def scored(self) -> bool:
        return self.admitted and self.power > 0.0

    @property
    def power(self) -> float:
        return self.power_truth.astrodyne_power

    @property
    def harmony(self) -> float:
        return self.harmony_truth.total_harmony

    @property
    def discord(self) -> float:
        return self.harmony_truth.total_discord

    @property
    def net_harmony(self) -> float:
        return self.harmony_truth.net_harmony

    @property
    def bodies(self) -> tuple[str, str]:
        return (self.body_a, self.body_b)

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        first, second = sorted(self.bodies)
        return (first, second, self.kind.value, self.aspect)


def evaluate_zodiacal_relation(
    body_a: str,
    longitude_a_deg: float,
    house_class_a: str,
    body_b: str,
    longitude_b_deg: float,
    house_class_b: str,
    aspect: str,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneAspectRelation:
    """Evaluate one named zodiacal relation, whether admitted or not."""

    power = zodiacal_aspect_power(
        body_a,
        longitude_a_deg,
        house_class_a,
        body_b,
        longitude_b_deg,
        house_class_b,
        aspect,
        policy=policy,
    )
    harmony = aspect_harmony(power.body_a, power.body_b, power.aspect, power.astrodyne_power)
    return AstrodyneAspectRelation(
        kind=AstrodyneRelationKind.ZODIACAL_ASPECT,
        body_a=power.body_a,
        body_b=power.body_b,
        aspect=power.aspect,
        power_truth=power,
        harmony_truth=harmony,
    )


def evaluate_parallel_relation(
    body_a: str,
    declination_a_deg: float,
    house_class_a: str,
    body_b: str,
    declination_b_deg: float,
    house_class_b: str,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneAspectRelation:
    """Evaluate one magnitude-parallel relation, whether admitted or not."""

    power = parallel_aspect_power(
        body_a,
        declination_a_deg,
        house_class_a,
        body_b,
        declination_b_deg,
        house_class_b,
        policy=policy,
    )
    harmony = aspect_harmony(power.body_a, power.body_b, "parallel", power.astrodyne_power)
    return AstrodyneAspectRelation(
        kind=AstrodyneRelationKind.PARALLEL,
        body_a=power.body_a,
        body_b=power.body_b,
        aspect="parallel",
        power_truth=power,
        harmony_truth=harmony,
    )


def _reception_signs(planet: str) -> tuple[str, ...]:
    row = _DIGNITY_BY_PLANET[planet]
    return (*row.home_signs, row.exaltation_sign)


@dataclass(frozen=True, slots=True)
class AstrodyneMutualReceptionRelation:
    """Explicit home-or-exaltation mutual-reception truth for one planet pair."""

    kind: AstrodyneRelationKind
    planet_a: str
    sign_a: str
    qualifying_signs_a: tuple[str, ...]
    planet_b: str
    sign_b: str
    qualifying_signs_b: tuple[str, ...]
    a_occupies_b_dignity: bool
    b_occupies_a_dignity: bool
    bonus_each: float

    def __post_init__(self) -> None:
        if self.kind is not AstrodyneRelationKind.MUTUAL_RECEPTION:
            raise ValueError("mutual reception requires its relation kind")
        if self.qualifying_signs_a != _reception_signs(self.planet_a):
            raise ValueError("planet A qualifying signs disagree with the source table")
        if self.qualifying_signs_b != _reception_signs(self.planet_b):
            raise ValueError("planet B qualifying signs disagree with the source table")
        if self.a_occupies_b_dignity != (self.sign_a in self.qualifying_signs_b):
            raise ValueError("planet A reception flag is inconsistent")
        if self.b_occupies_a_dignity != (self.sign_b in self.qualifying_signs_a):
            raise ValueError("planet B reception flag is inconsistent")
        if self.admitted != (self.bonus_each > 0.0):
            raise ValueError("mutual-reception bonus is inconsistent")

    @property
    def body_a(self) -> str:
        return self.planet_a

    @property
    def body_b(self) -> str:
        return self.planet_b

    @property
    def bodies(self) -> tuple[str, str]:
        return (self.planet_a, self.planet_b)

    @property
    def detected(self) -> bool:
        return True

    @property
    def admitted(self) -> bool:
        return self.a_occupies_b_dignity and self.b_occupies_a_dignity

    @property
    def scored(self) -> bool:
        return self.admitted and self.bonus_each > 0.0

    @property
    def power(self) -> float:
        return 0.0

    @property
    def harmony(self) -> float:
        return self.bonus_each

    @property
    def discord(self) -> float:
        return 0.0

    @property
    def net_harmony(self) -> float:
        return self.bonus_each

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        first, second = sorted(self.bodies)
        return (first, second, self.kind.value, "mutual_reception")


AstrodyneRelation = AstrodyneAspectRelation | AstrodyneMutualReceptionRelation


def mutual_reception(
    planet_a: str,
    sign_a: str,
    planet_b: str,
    sign_b: str,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneMutualReceptionRelation:
    """Evaluate the manual's home-or-exaltation mutual-reception rule."""

    active_policy = _policy(policy)
    first = _canonical_planet(planet_a)
    second = _canonical_planet(planet_b)
    if first == second:
        raise ValueError("mutual reception requires two different planets")
    first_sign = _canonical_sign(sign_a)
    second_sign = _canonical_sign(sign_b)
    first_qualifying = _reception_signs(first)
    second_qualifying = _reception_signs(second)
    first_in_second = first_sign in second_qualifying
    second_in_first = second_sign in first_qualifying
    admitted = first_in_second and second_in_first
    return AstrodyneMutualReceptionRelation(
        kind=AstrodyneRelationKind.MUTUAL_RECEPTION,
        planet_a=first,
        sign_a=first_sign,
        qualifying_signs_a=first_qualifying,
        planet_b=second,
        sign_b=second_sign,
        qualifying_signs_b=second_qualifying,
        a_occupies_b_dignity=first_in_second,
        b_occupies_a_dignity=second_in_first,
        bonus_each=active_policy.mutual_reception_bonus if admitted else 0.0,
    )


@dataclass(frozen=True, slots=True)
class AstrodyneRelationSet:
    """Deterministic detected, admitted, and scored relation subsets."""

    detected: tuple[AstrodyneRelation, ...]

    def __post_init__(self) -> None:
        if tuple(sorted(self.detected, key=lambda item: item.sort_key)) != self.detected:
            raise ValueError("relations must be deterministically sorted")
        keys = [item.sort_key for item in self.detected]
        if len(keys) != len(set(keys)):
            raise ValueError("relation keys must be unique")

    @property
    def admitted(self) -> tuple[AstrodyneRelation, ...]:
        return tuple(item for item in self.detected if item.admitted)

    @property
    def scored(self) -> tuple[AstrodyneRelation, ...]:
        return tuple(item for item in self.detected if item.scored)

    def for_body(self, body: str, *, scored_only: bool = False) -> tuple[AstrodyneRelation, ...]:
        canonical = _canonical_body(body)
        source = self.scored if scored_only else self.admitted
        return tuple(item for item in source if canonical in item.bodies)


# ---------------------------------------------------------------------------
# Phase 7 - Integrated Local Condition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AstrodyneBodyInput:
    """Explicit chart geometry required by the kernel-free natal core."""

    body: str
    longitude_deg: float
    house: int
    house_class: str
    distance_from_weaker_cusp_deg: float | None = None
    house_size_deg: float | None = None
    declination_deg: float | None = None

    def __post_init__(self) -> None:
        body = _canonical_body(self.body)
        house_class = _canonical_house_class(self.house_class)
        _validate_point_house_class(body, house_class)
        if isinstance(self.house, bool) or not isinstance(self.house, int) or self.house not in range(1, 13):
            raise ValueError("house must be an integer in [1, 12]")
        expected_house_class = (
            "angular"
            if self.house in {1, 4, 7, 10}
            else "succedent"
            if self.house in {2, 5, 8, 11}
            else "cadent"
        )
        if house_class != expected_house_class:
            raise ValueError(
                f"house {self.house} requires house_class={expected_house_class!r}"
            )
        longitude = _finite("longitude_deg", self.longitude_deg) % 360.0
        declination = self.declination_deg
        if declination is not None:
            declination = _finite("declination_deg", declination)
            if not -90.0 <= declination <= 90.0:
                raise ValueError("declination_deg must be in [-90, 90]")
        if body in ASTRODYNE_PLANETS:
            if self.distance_from_weaker_cusp_deg is None or self.house_size_deg is None:
                raise ValueError("planet inputs require house interpolation geometry")
            distance = _finite(
                "distance_from_weaker_cusp_deg", self.distance_from_weaker_cusp_deg
            )
            size = _finite("house_size_deg", self.house_size_deg)
            if size <= 0.0 or not 0.0 <= distance <= size:
                raise ValueError("planet house interpolation geometry is invalid")
        else:
            if self.distance_from_weaker_cusp_deg is not None or self.house_size_deg is not None:
                raise ValueError("M.C. and Asc. use fixed power, not interpolation geometry")
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "longitude_deg", longitude)
        object.__setattr__(self, "house_class", house_class)
        object.__setattr__(self, "declination_deg", declination)

    @property
    def body_kind(self) -> AstrodyneBodyKind:
        return (
            AstrodyneBodyKind.PLANET
            if self.body in ASTRODYNE_PLANETS
            else AstrodyneBodyKind.ANGLE
        )

    @property
    def sign(self) -> str:
        return ASTRODYNE_SIGNS[int(self.longitude_deg // 30.0)]

    @property
    def sign_degree(self) -> float:
        return self.longitude_deg % 30.0


@dataclass(frozen=True, slots=True)
class AstrodyneContribution:
    """One named contribution retained by an integrated body profile."""

    source: AstrodyneContributionSource
    label: str
    power: float
    harmony: float
    discord: float

    def __post_init__(self) -> None:
        if min(self.power, self.harmony, self.discord) < 0.0:
            raise ValueError("contribution magnitudes cannot be negative")

    @property
    def net_harmony(self) -> float:
        return self.harmony - self.discord


@dataclass(frozen=True, slots=True)
class AstrodyneBodyConditionProfile:
    """Integrated power and harmony/discord truth for one planet or angle."""

    input: AstrodyneBodyInput
    house_position: AstrodyneHousePositionTruth | None
    dignity: AstrodyneEssentialDignityTruth | None
    relations: tuple[AstrodyneRelation, ...]
    contributions: tuple[AstrodyneContribution, ...]
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float

    def __post_init__(self) -> None:
        if self.input.body_kind is AstrodyneBodyKind.PLANET and self.house_position is None:
            raise ValueError("planet profile requires house-position truth")
        if self.input.body_kind is AstrodyneBodyKind.ANGLE and self.house_position is not None:
            raise ValueError("angle profile uses fixed power")
        if self.input.body_kind is AstrodyneBodyKind.PLANET and self.dignity is None:
            raise ValueError("planet profile requires dignity truth")
        expected_power = sum(item.power for item in self.contributions)
        expected_harmony = sum(item.harmony for item in self.contributions)
        expected_discord = sum(item.discord for item in self.contributions)
        if abs(self.total_power - expected_power) > 1e-12:
            raise ValueError("total_power disagrees with contributions")
        if abs(self.total_harmony - expected_harmony) > 1e-12:
            raise ValueError("total_harmony disagrees with contributions")
        if abs(self.total_discord - expected_discord) > 1e-12:
            raise ValueError("total_discord disagrees with contributions")
        if abs(self.net_harmony - (self.total_harmony - self.total_discord)) > 1e-12:
            raise ValueError("net_harmony disagrees with totals")

    @property
    def body(self) -> str:
        return self.input.body

    @property
    def sign(self) -> str:
        return self.input.sign

    @property
    def house(self) -> int:
        return self.input.house

    def contributions_from(
        self, source: AstrodyneContributionSource
    ) -> tuple[AstrodyneContribution, ...]:
        return tuple(item for item in self.contributions if item.source is source)


def _build_body_profile(
    body_input: AstrodyneBodyInput,
    relations: AstrodyneRelationSet,
    *,
    policy: AstrodynePolicy,
) -> AstrodyneBodyConditionProfile:
    body = body_input.body
    local_relations = relations.for_body(body, scored_only=True)
    contributions: list[AstrodyneContribution] = []

    if body_input.body_kind is AstrodyneBodyKind.ANGLE:
        house_truth = None
        dignity_truth = None
        contributions.append(
            AstrodyneContribution(
                AstrodyneContributionSource.HOUSE_POSITION,
                "fixed angle power",
                ASTRODYNE_ANGLE_POINT_POWER,
                0.0,
                0.0,
            )
        )
    else:
        assert body_input.distance_from_weaker_cusp_deg is not None
        assert body_input.house_size_deg is not None
        house_truth = house_position_power(
            body_input.house,
            body_input.distance_from_weaker_cusp_deg,
            body_input.house_size_deg,
        )
        dignity_truth = essential_dignity(
            body,
            body_input.sign,
            body_input.sign_degree,
            policy=policy,
        )
        contributions.append(
            AstrodyneContribution(
                AstrodyneContributionSource.HOUSE_POSITION,
                f"house {body_input.house}",
                house_truth.astrodyne_power,
                0.0,
                0.0,
            )
        )
        if dignity_truth.condition is not None:
            contributions.append(
                AstrodyneContribution(
                    AstrodyneContributionSource.ESSENTIAL_DIGNITY,
                    dignity_truth.condition.value,
                    0.0,
                    dignity_truth.harmony,
                    dignity_truth.discord,
                )
            )

    for relation in local_relations:
        if isinstance(relation, AstrodyneAspectRelation):
            source = (
                AstrodyneContributionSource.PARALLEL
                if relation.kind is AstrodyneRelationKind.PARALLEL
                else AstrodyneContributionSource.ZODIACAL_ASPECT
            )
            contributions.append(
                AstrodyneContribution(
                    source,
                    f"{relation.aspect} with {relation.body_b if body == relation.body_a else relation.body_a}",
                    relation.power,
                    relation.harmony,
                    relation.discord,
                )
            )
        else:
            contributions.append(
                AstrodyneContribution(
                    AstrodyneContributionSource.MUTUAL_RECEPTION,
                    f"mutual reception with {relation.body_b if body == relation.body_a else relation.body_a}",
                    0.0,
                    relation.bonus_each,
                    0.0,
                )
            )

    contribution_tuple = tuple(contributions)
    total_power = sum(item.power for item in contribution_tuple)
    total_harmony = sum(item.harmony for item in contribution_tuple)
    total_discord = sum(item.discord for item in contribution_tuple)
    return AstrodyneBodyConditionProfile(
        input=body_input,
        house_position=house_truth,
        dignity=dignity_truth,
        relations=local_relations,
        contributions=contribution_tuple,
        total_power=total_power,
        total_harmony=total_harmony,
        total_discord=total_discord,
        net_harmony=total_harmony - total_discord,
    )


# ---------------------------------------------------------------------------
# Phase 8 - Aggregate Intelligence
# ---------------------------------------------------------------------------


def _rulers_for_sign(sign: str) -> tuple[str, ...]:
    return tuple(row.planet for row in ASTRODYNE_DIGNITY_ROWS if sign in row.home_signs)


@dataclass(frozen=True, slots=True)
class AstrodyneRulerShareTruth:
    """Preserved average-ruler fraction used by sign and house rollups."""

    rulers: tuple[str, ...]
    ruler_powers: tuple[float, ...]
    average_ruler_power: float
    cusp_count: int
    intercepted_count: int
    fraction: float
    contribution: float

    def __post_init__(self) -> None:
        if len(self.rulers) != len(self.ruler_powers) or not self.rulers:
            raise ValueError("rulers and ruler_powers must be non-empty and aligned")
        expected_fraction = self.cusp_count * 0.5 + self.intercepted_count * 0.25
        if abs(self.fraction - expected_fraction) > 1e-12:
            raise ValueError("ruler-share fraction is inconsistent")
        if abs(self.contribution - self.average_ruler_power * self.fraction) > 1e-12:
            raise ValueError("ruler-share contribution is inconsistent")


def ruler_power_share(
    rulers: Sequence[str],
    ruler_powers: Sequence[float],
    *,
    cusp_count: int = 0,
    intercepted_count: int = 0,
) -> AstrodyneRulerShareTruth:
    """Compute the manual's averaged half-cusp and quarter-interception share."""

    canonical_rulers = tuple(_canonical_planet(ruler) for ruler in rulers)
    powers = tuple(_finite("ruler_power", value) for value in ruler_powers)
    if len(canonical_rulers) != len(powers) or not canonical_rulers:
        raise ValueError("rulers and ruler_powers must be non-empty and aligned")
    if cusp_count not in {0, 1, 2}:
        raise ValueError("cusp_count must be 0, 1, or 2")
    if isinstance(intercepted_count, bool) or not isinstance(intercepted_count, int) or intercepted_count < 0:
        raise ValueError("intercepted_count must be a non-negative integer")
    if any(power < 0.0 for power in powers):
        raise ValueError("ruler powers cannot be negative")
    average = sum(powers) / len(powers)
    fraction = cusp_count * 0.5 + intercepted_count * 0.25
    return AstrodyneRulerShareTruth(
        rulers=canonical_rulers,
        ruler_powers=powers,
        average_ruler_power=average,
        cusp_count=cusp_count,
        intercepted_count=intercepted_count,
        fraction=fraction,
        contribution=average * fraction,
    )


@dataclass(frozen=True, slots=True)
class AstrodyneSignAggregate:
    """Source-supported ruler plus occupant rollup for one zodiac sign."""

    sign: str
    rulers: tuple[str, ...]
    cusp_count: int
    intercepted_houses: tuple[int, ...]
    ruler_fraction: float
    occupants: tuple[str, ...]
    ruler_power: float
    occupant_power: float
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float

    def __post_init__(self) -> None:
        if self.sign not in ASTRODYNE_SIGNS:
            raise ValueError("invalid sign aggregate")
        if not self.rulers:
            raise ValueError("every Astrodyne sign must have at least one ruler")
        if self.cusp_count not in {0, 1, 2}:
            raise ValueError("cusp_count must be 0, 1, or 2")
        expected_fraction = self.cusp_count * 0.5 + len(self.intercepted_houses) * 0.25
        if abs(self.ruler_fraction - expected_fraction) > 1e-12:
            raise ValueError("ruler_fraction disagrees with cusp/interception truth")
        if abs(self.total_power - (self.ruler_power + self.occupant_power)) > 1e-12:
            raise ValueError("sign power rollup is inconsistent")
        if abs(self.net_harmony - (self.total_harmony - self.total_discord)) > 1e-12:
            raise ValueError("sign harmony rollup is inconsistent")


@dataclass(frozen=True, slots=True)
class AstrodyneHouseAggregate:
    """Source-supported cusp/interception plus occupant rollup for one house."""

    house: int
    cusp_sign: str
    intercepted_signs: tuple[str, ...]
    occupants: tuple[str, ...]
    ruler_power: float
    occupant_power: float
    total_power: float
    total_harmony: float
    total_discord: float
    net_harmony: float

    def __post_init__(self) -> None:
        if self.house not in range(1, 13):
            raise ValueError("house aggregate number must be in [1, 12]")
        if self.cusp_sign not in ASTRODYNE_SIGNS:
            raise ValueError("invalid cusp sign")
        if abs(self.total_power - (self.ruler_power + self.occupant_power)) > 1e-12:
            raise ValueError("house power rollup is inconsistent")
        if abs(self.net_harmony - (self.total_harmony - self.total_discord)) > 1e-12:
            raise ValueError("house harmony rollup is inconsistent")


@dataclass(frozen=True, slots=True)
class AstrodyneChartAggregate:
    """The twelve sign and twelve house rollups with manual checksum truth."""

    signs: tuple[AstrodyneSignAggregate, ...]
    houses: tuple[AstrodyneHouseAggregate, ...]
    total_body_power: float
    total_sign_power: float
    total_house_power: float
    total_sign_harmony: float
    total_house_harmony: float

    def __post_init__(self) -> None:
        if tuple(item.sign for item in self.signs) != ASTRODYNE_SIGNS:
            raise ValueError("sign aggregates must follow zodiacal order")
        if tuple(item.house for item in self.houses) != tuple(range(1, 13)):
            raise ValueError("house aggregates must follow numerical order")
        if abs(self.total_sign_power - sum(item.total_power for item in self.signs)) > 1e-9:
            raise ValueError("total_sign_power is inconsistent")
        if abs(self.total_house_power - sum(item.total_power for item in self.houses)) > 1e-9:
            raise ValueError("total_house_power is inconsistent")
        if abs(self.total_sign_harmony - sum(item.net_harmony for item in self.signs)) > 1e-9:
            raise ValueError("total_sign_harmony is inconsistent")
        if abs(self.total_house_harmony - sum(item.net_harmony for item in self.houses)) > 1e-9:
            raise ValueError("total_house_harmony is inconsistent")

    @property
    def power_checksum_delta(self) -> float:
        return self.total_sign_power - self.total_house_power

    @property
    def harmony_checksum_delta(self) -> float:
        return self.total_sign_harmony - self.total_house_harmony

    @property
    def checksums_pass(self) -> bool:
        return (
            abs(self.power_checksum_delta) <= 1e-9
            and abs(self.harmony_checksum_delta) <= 1e-9
        )


@dataclass(frozen=True, slots=True)
class AstrodyneSummaryEntry:
    """One official society, trinity, element, or quality summary row."""

    family: AstrodyneSummaryFamily
    name: str
    houses: tuple[int, ...]
    signs: tuple[str, ...]
    power: float
    percentage: float
    total_harmony: float
    total_discord: float
    net_harmony: float

    def __post_init__(self) -> None:
        if not isinstance(self.family, AstrodyneSummaryFamily):
            raise TypeError("summary family must be AstrodyneSummaryFamily")
        if not self.name:
            raise ValueError("summary entry name cannot be empty")
        if bool(self.houses) == bool(self.signs):
            raise ValueError("summary entry must own either houses or signs")
        if self.family in {
            AstrodyneSummaryFamily.SOCIETY,
            AstrodyneSummaryFamily.TRINITY,
        } and not self.houses:
            raise ValueError("society and trinity entries require houses")
        if self.family in {
            AstrodyneSummaryFamily.ELEMENT,
            AstrodyneSummaryFamily.QUALITY,
        } and not self.signs:
            raise ValueError("element and quality entries require signs")
        numeric = (
            self.power,
            self.percentage,
            self.total_harmony,
            self.total_discord,
            self.net_harmony,
        )
        if not all(isfinite(value) for value in numeric):
            raise ValueError("summary values must be finite")
        if self.power < 0.0 or not 0.0 <= self.percentage <= 100.0:
            raise ValueError("summary power/percentage is invalid")
        if min(self.total_harmony, self.total_discord) < 0.0:
            raise ValueError("summary harmony/discord magnitudes cannot be negative")
        if abs(self.net_harmony - (self.total_harmony - self.total_discord)) > 1e-12:
            raise ValueError("summary net harmony is inconsistent")

    @property
    def rounded_power(self) -> float:
        return round(self.power, 2)

    @property
    def rounded_percentage(self) -> float:
        return round(self.percentage, 1)

    @property
    def rounded_net_harmony(self) -> float:
        return round(self.net_harmony, 2)


@dataclass(frozen=True, slots=True)
class AstrodyneSummaryProfile:
    """All four official summary families over one chart aggregate."""

    societies: tuple[AstrodyneSummaryEntry, ...]
    trinities: tuple[AstrodyneSummaryEntry, ...]
    elements: tuple[AstrodyneSummaryEntry, ...]
    qualities: tuple[AstrodyneSummaryEntry, ...]
    total_power: float

    def __post_init__(self) -> None:
        if not isfinite(self.total_power) or self.total_power <= 0.0:
            raise ValueError("summary total power must be finite and positive")
        expected = (
            (self.societies, AstrodyneSummaryFamily.SOCIETY, ASTRODYNE_SOCIETY_GROUPS),
            (self.trinities, AstrodyneSummaryFamily.TRINITY, ASTRODYNE_TRINITY_GROUPS),
            (self.elements, AstrodyneSummaryFamily.ELEMENT, ASTRODYNE_ELEMENT_GROUPS),
            (self.qualities, AstrodyneSummaryFamily.QUALITY, ASTRODYNE_QUALITY_GROUPS),
        )
        for entries, family, groups in expected:
            if tuple(item.family for item in entries) != (family,) * len(groups):
                raise ValueError(f"{family.value} entries have the wrong family")
            if tuple(item.name for item in entries) != tuple(name for name, _ in groups):
                raise ValueError(f"{family.value} entries are not in source order")
            members = tuple(
                item.houses if item.houses else item.signs for item in entries
            )
            if members != tuple(group_members for _, group_members in groups):
                raise ValueError(f"{family.value} entries have the wrong members")
            if abs(sum(item.power for item in entries) - self.total_power) > 1e-9:
                raise ValueError(f"{family.value} power does not partition the chart")
            if self.total_power > 0.0 and abs(sum(item.percentage for item in entries) - 100.0) > 1e-9:
                raise ValueError(f"{family.value} percentages do not sum to 100")

    def family(
        self, family: AstrodyneSummaryFamily
    ) -> tuple[AstrodyneSummaryEntry, ...]:
        if family is AstrodyneSummaryFamily.SOCIETY:
            return self.societies
        if family is AstrodyneSummaryFamily.TRINITY:
            return self.trinities
        if family is AstrodyneSummaryFamily.ELEMENT:
            return self.elements
        if family is AstrodyneSummaryFamily.QUALITY:
            return self.qualities
        raise ValueError(f"unsupported summary family: {family!r}")

    def dominant(self, family: AstrodyneSummaryFamily) -> AstrodyneSummaryEntry:
        """Return the first source-ordered maximum for one family."""

        return max(self.family(family), key=lambda item: item.power)


def _summary_entry_from_houses(
    family: AstrodyneSummaryFamily,
    name: str,
    houses: tuple[int, ...],
    aggregate: AstrodyneChartAggregate,
) -> AstrodyneSummaryEntry:
    members = tuple(aggregate.houses[house - 1] for house in houses)
    power = sum(item.total_power for item in members)
    harmony = sum(item.total_harmony for item in members)
    discord = sum(item.total_discord for item in members)
    percentage = power / aggregate.total_house_power * 100.0
    return AstrodyneSummaryEntry(
        family=family,
        name=name,
        houses=houses,
        signs=(),
        power=power,
        percentage=percentage,
        total_harmony=harmony,
        total_discord=discord,
        net_harmony=harmony - discord,
    )


def _summary_entry_from_signs(
    family: AstrodyneSummaryFamily,
    name: str,
    signs: tuple[str, ...],
    aggregate: AstrodyneChartAggregate,
) -> AstrodyneSummaryEntry:
    members = tuple(aggregate.signs[ASTRODYNE_SIGNS.index(sign)] for sign in signs)
    power = sum(item.total_power for item in members)
    harmony = sum(item.total_harmony for item in members)
    discord = sum(item.total_discord for item in members)
    percentage = power / aggregate.total_sign_power * 100.0
    return AstrodyneSummaryEntry(
        family=family,
        name=name,
        houses=(),
        signs=signs,
        power=power,
        percentage=percentage,
        total_harmony=harmony,
        total_discord=discord,
        net_harmony=harmony - discord,
    )


def astrodynes_summary(
    aggregate: AstrodyneChartAggregate,
) -> AstrodyneSummaryProfile:
    """Derive the four official Class 5 summary families."""

    if not isinstance(aggregate, AstrodyneChartAggregate):
        raise TypeError("aggregate must be an AstrodyneChartAggregate")
    if (
        not isfinite(aggregate.total_house_power)
        or not isfinite(aggregate.total_sign_power)
        or aggregate.total_house_power <= 0.0
        or aggregate.total_sign_power <= 0.0
    ):
        raise ValueError("summary aggregation requires positive chart power")
    societies = tuple(
        _summary_entry_from_houses(
            AstrodyneSummaryFamily.SOCIETY, name, houses, aggregate
        )
        for name, houses in ASTRODYNE_SOCIETY_GROUPS
    )
    trinities = tuple(
        _summary_entry_from_houses(
            AstrodyneSummaryFamily.TRINITY, name, houses, aggregate
        )
        for name, houses in ASTRODYNE_TRINITY_GROUPS
    )
    elements = tuple(
        _summary_entry_from_signs(
            AstrodyneSummaryFamily.ELEMENT, name, signs, aggregate
        )
        for name, signs in ASTRODYNE_ELEMENT_GROUPS
    )
    qualities = tuple(
        _summary_entry_from_signs(
            AstrodyneSummaryFamily.QUALITY, name, signs, aggregate
        )
        for name, signs in ASTRODYNE_QUALITY_GROUPS
    )
    return AstrodyneSummaryProfile(
        societies=societies,
        trinities=trinities,
        elements=elements,
        qualities=qualities,
        total_power=aggregate.total_house_power,
    )


def _average_ruler_values(
    sign: str,
    profiles: Mapping[str, AstrodyneBodyConditionProfile],
) -> tuple[float, float, float]:
    rulers = _rulers_for_sign(sign)
    ruler_profiles = [profiles[ruler] for ruler in rulers]
    count = len(ruler_profiles)
    return (
        sum(item.total_power for item in ruler_profiles) / count,
        sum(item.total_harmony for item in ruler_profiles) / count,
        sum(item.total_discord for item in ruler_profiles) / count,
    )


def _build_chart_aggregate(
    profiles: tuple[AstrodyneBodyConditionProfile, ...],
    cusp_signs: tuple[str, ...],
    intercepted_signs_by_house: Mapping[int, tuple[str, ...]],
) -> AstrodyneChartAggregate:
    by_body = {profile.body: profile for profile in profiles}
    sign_aggregates: list[AstrodyneSignAggregate] = []

    for sign in ASTRODYNE_SIGNS:
        rulers = _rulers_for_sign(sign)
        cusp_count = cusp_signs.count(sign)
        intercepted_houses = tuple(
            house
            for house in range(1, 13)
            if sign in intercepted_signs_by_house.get(house, ())
        )
        fraction = cusp_count * 0.5 + len(intercepted_houses) * 0.25
        average_power, average_harmony, average_discord = _average_ruler_values(sign, by_body)
        ruler_power = average_power * fraction
        ruler_harmony = average_harmony * fraction
        ruler_discord = average_discord * fraction
        occupants = tuple(profile.body for profile in profiles if profile.sign == sign)
        occupant_profiles = [by_body[body] for body in occupants]
        occupant_power = sum(item.total_power for item in occupant_profiles)
        total_harmony = ruler_harmony + sum(item.total_harmony for item in occupant_profiles)
        total_discord = ruler_discord + sum(item.total_discord for item in occupant_profiles)
        sign_aggregates.append(
            AstrodyneSignAggregate(
                sign=sign,
                rulers=rulers,
                cusp_count=cusp_count,
                intercepted_houses=intercepted_houses,
                ruler_fraction=fraction,
                occupants=occupants,
                ruler_power=ruler_power,
                occupant_power=occupant_power,
                total_power=ruler_power + occupant_power,
                total_harmony=total_harmony,
                total_discord=total_discord,
                net_harmony=total_harmony - total_discord,
            )
        )

    house_aggregates: list[AstrodyneHouseAggregate] = []
    for house, cusp_sign in enumerate(cusp_signs, 1):
        intercepted = intercepted_signs_by_house.get(house, ())
        average_power, average_harmony, average_discord = _average_ruler_values(
            cusp_sign, by_body
        )
        ruler_power = average_power * 0.5
        ruler_harmony = average_harmony * 0.5
        ruler_discord = average_discord * 0.5
        for sign in intercepted:
            power, harmony, discord = _average_ruler_values(sign, by_body)
            ruler_power += power * 0.25
            ruler_harmony += harmony * 0.25
            ruler_discord += discord * 0.25
        occupants = tuple(profile.body for profile in profiles if profile.house == house)
        occupant_profiles = [by_body[body] for body in occupants]
        occupant_power = sum(item.total_power for item in occupant_profiles)
        total_harmony = ruler_harmony + sum(item.total_harmony for item in occupant_profiles)
        total_discord = ruler_discord + sum(item.total_discord for item in occupant_profiles)
        house_aggregates.append(
            AstrodyneHouseAggregate(
                house=house,
                cusp_sign=cusp_sign,
                intercepted_signs=intercepted,
                occupants=occupants,
                ruler_power=ruler_power,
                occupant_power=occupant_power,
                total_power=ruler_power + occupant_power,
                total_harmony=total_harmony,
                total_discord=total_discord,
                net_harmony=total_harmony - total_discord,
            )
        )

    sign_tuple = tuple(sign_aggregates)
    house_tuple = tuple(house_aggregates)
    return AstrodyneChartAggregate(
        signs=sign_tuple,
        houses=house_tuple,
        total_body_power=sum(item.total_power for item in profiles),
        total_sign_power=sum(item.total_power for item in sign_tuple),
        total_house_power=sum(item.total_power for item in house_tuple),
        total_sign_harmony=sum(item.net_harmony for item in sign_tuple),
        total_house_harmony=sum(item.net_harmony for item in house_tuple),
    )


# ---------------------------------------------------------------------------
# Phase 9 - Network Intelligence
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AstrodyneNetworkNode:
    """Vessel: Structured astrodyne network node data."""
    body: str
    sign: str
    house: int
    power: float
    net_harmony: float


@dataclass(frozen=True, slots=True)
class AstrodyneNetworkEdge:
    """Vessel: Structured astrodyne network edge data."""
    kind: AstrodyneRelationKind
    body_a: str
    body_b: str
    label: str
    power: float
    net_harmony: float
    scored: bool

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        first, second = sorted((self.body_a, self.body_b))
        return (first, second, self.kind.value, self.label)


@dataclass(frozen=True, slots=True)
class AstrodyneNetwork:
    """Vessel: Structured astrodyne network data."""
    nodes: tuple[AstrodyneNetworkNode, ...]
    edges: tuple[AstrodyneNetworkEdge, ...]

    def __post_init__(self) -> None:
        if len({node.body for node in self.nodes}) != len(self.nodes):
            raise ValueError("network node bodies must be unique")
        if tuple(sorted(self.edges, key=lambda item: item.sort_key)) != self.edges:
            raise ValueError("network edges must be deterministically sorted")

    def neighbors(self, body: str) -> tuple[str, ...]:
        canonical = _canonical_body(body)
        result: set[str] = set()
        for edge in self.edges:
            if edge.body_a == canonical:
                result.add(edge.body_b)
            elif edge.body_b == canonical:
                result.add(edge.body_a)
        return tuple(sorted(result))


def _build_network(
    profiles: tuple[AstrodyneBodyConditionProfile, ...],
    relations: AstrodyneRelationSet,
) -> AstrodyneNetwork:
    nodes = tuple(
        AstrodyneNetworkNode(
            body=profile.body,
            sign=profile.sign,
            house=profile.house,
            power=profile.total_power,
            net_harmony=profile.net_harmony,
        )
        for profile in profiles
    )
    edges = tuple(
        sorted(
            (
                AstrodyneNetworkEdge(
                    kind=relation.kind,
                    body_a=relation.body_a,
                    body_b=relation.body_b,
                    label=(
                        relation.aspect
                        if isinstance(relation, AstrodyneAspectRelation)
                        else "mutual_reception"
                    ),
                    power=relation.power,
                    net_harmony=relation.net_harmony,
                    scored=relation.scored,
                )
                for relation in relations.admitted
            ),
            key=lambda item: item.sort_key,
        )
    )
    return AstrodyneNetwork(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# Phase 10 - Full-Subsystem Hardening
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AstrodyneChartResult:
    """Complete bounded natal result through summary and network layers."""

    policy: AstrodynePolicy
    inputs: tuple[AstrodyneBodyInput, ...]
    relations: AstrodyneRelationSet
    profiles: tuple[AstrodyneBodyConditionProfile, ...]
    aggregate: AstrodyneChartAggregate
    summary: AstrodyneSummaryProfile
    network: AstrodyneNetwork

    def __post_init__(self) -> None:
        failures = validate_astrodynes_output(self)
        if failures:
            raise ValueError("invalid AstrodyneChartResult: " + "; ".join(failures))

    def profile(self, body: str) -> AstrodyneBodyConditionProfile:
        canonical = _canonical_body(body)
        for profile in self.profiles:
            if profile.body == canonical:
                return profile
        raise KeyError(canonical)

    def sign(self, sign: str) -> AstrodyneSignAggregate:
        canonical = _canonical_sign(sign)
        return self.aggregate.signs[ASTRODYNE_SIGNS.index(canonical)]

    def house(self, house: int) -> AstrodyneHouseAggregate:
        if house not in range(1, 13):
            raise KeyError(house)
        return self.aggregate.houses[house - 1]


def _closest_zodiacal_relation(
    first: AstrodyneBodyInput,
    second: AstrodyneBodyInput,
    policy: AstrodynePolicy,
) -> AstrodyneAspectRelation:
    candidates = tuple(
        evaluate_zodiacal_relation(
            first.body,
            first.longitude_deg,
            first.house_class,
            second.body,
            second.longitude_deg,
            second.house_class,
            aspect,
            policy=policy,
        )
        for aspect in _ASPECT_ORB_ROWS
    )
    return min(
        candidates,
        key=lambda relation: (
            relation.power_truth.distance_from_perfect_deg,
            relation.power_truth.exact_angle_deg,
        ),
    )


def _build_relation_set(
    inputs: tuple[AstrodyneBodyInput, ...],
    policy: AstrodynePolicy,
) -> AstrodyneRelationSet:
    detected: list[AstrodyneRelation] = []
    for index, first in enumerate(inputs):
        for second in inputs[index + 1 :]:
            detected.append(_closest_zodiacal_relation(first, second, policy))
            if first.declination_deg is not None and second.declination_deg is not None:
                detected.append(
                    evaluate_parallel_relation(
                        first.body,
                        first.declination_deg,
                        first.house_class,
                        second.body,
                        second.declination_deg,
                        second.house_class,
                        policy=policy,
                    )
                )
            if first.body_kind is AstrodyneBodyKind.PLANET and second.body_kind is AstrodyneBodyKind.PLANET:
                detected.append(
                    mutual_reception(
                        first.body,
                        first.sign,
                        second.body,
                        second.sign,
                        policy=policy,
                    )
                )
    return AstrodyneRelationSet(tuple(sorted(detected, key=lambda item: item.sort_key)))


def _canonical_interceptions(
    value: Mapping[int, Sequence[str]] | None,
    cusp_signs: tuple[str, ...],
) -> dict[int, tuple[str, ...]]:
    result: dict[int, tuple[str, ...]] = {}
    if value is None:
        return result
    for house, signs in value.items():
        if isinstance(house, bool) or not isinstance(house, int) or house not in range(1, 13):
            raise ValueError("intercepted-sign house keys must be integers in [1, 12]")
        canonical = tuple(_canonical_sign(sign) for sign in signs)
        if len(canonical) != len(set(canonical)):
            raise ValueError("intercepted signs within a house must be unique")
        if cusp_signs[house - 1] in canonical:
            raise ValueError("a house cusp sign cannot also be intercepted in that house")
        result[house] = canonical
    occurrences = [sign for signs in result.values() for sign in signs]
    if len(occurrences) != len(set(occurrences)):
        raise ValueError("an intercepted sign may occur in only one house")
    return result


def _geometry_house(
    longitude_deg: float,
    cusp_longitudes: tuple[float, ...],
) -> tuple[int, float, float]:
    """Return house, zodiacal size, and distance from its weaker cusp."""

    longitude = longitude_deg % 360.0
    for index, opening in enumerate(cusp_longitudes):
        closing = cusp_longitudes[(index + 1) % 12]
        house_size = (closing - opening) % 360.0
        distance_from_opening = (longitude - opening) % 360.0
        if distance_from_opening < house_size or distance_from_opening <= 1e-12:
            # The manual's worked house-position calculations identify the
            # closing boundary as the weaker cusp. The opening boundary is
            # therefore the stronger cusp for this within-house interpolation.
            return (
                index + 1,
                house_size,
                house_size - distance_from_opening,
            )
    raise ValueError("longitude does not fall within the ordered cusp figure")


def _geometry_interceptions(
    cusp_longitudes: tuple[float, ...],
    cusp_signs: tuple[str, ...],
) -> dict[int, tuple[str, ...]]:
    """Derive signs wholly enclosed by a house and absent from all cusps."""

    result: dict[int, list[str]] = {}
    cusp_sign_set = set(cusp_signs)
    for sign_index, sign in enumerate(ASTRODYNE_SIGNS):
        if sign in cusp_sign_set:
            continue
        sign_midpoint = sign_index * 30.0 + 15.0
        house, _, _ = _geometry_house(sign_midpoint, cusp_longitudes)
        result.setdefault(house, []).append(sign)
    return {house: tuple(signs) for house, signs in result.items()}


def natal_astrodynes_from_geometry(
    planet_longitudes: Mapping[str, float],
    declinations: Mapping[str, float],
    cusp_longitudes: Sequence[float],
    mc_longitude: float,
    asc_longitude: float,
    *,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneChartResult:
    """Build natal Astrodynes from a complete explicit tropical chart figure.

    This adapter owns only the conversion from already-computed chart geometry
    into :class:`AstrodyneBodyInput`. It does not acquire an ephemeris, choose a
    house system, infer a time zone, or alter the fixed Astrodyne doctrine.
    Declinations must include the ten planets plus ``M.C.`` and ``Asc.`` because
    the Church of Light relation grid admits parallels involving the angles.
    """

    if not isinstance(planet_longitudes, Mapping):
        raise TypeError("planet_longitudes must be a mapping")
    if not isinstance(declinations, Mapping):
        raise TypeError("declinations must be a mapping")

    longitudes_by_planet: dict[str, float] = {}
    for body, value in planet_longitudes.items():
        canonical = _canonical_planet(body)
        if canonical in longitudes_by_planet:
            raise ValueError(f"duplicate planet longitude: {canonical}")
        longitudes_by_planet[canonical] = _finite(
            f"planet_longitudes[{canonical!r}]", value
        ) % 360.0
    if set(longitudes_by_planet) != set(ASTRODYNE_PLANETS):
        missing = sorted(set(ASTRODYNE_PLANETS) - set(longitudes_by_planet))
        extra = sorted(set(longitudes_by_planet) - set(ASTRODYNE_PLANETS))
        raise ValueError(
            "planet_longitudes requires all ten Astrodyne planets; "
            f"missing={missing}, extra={extra}"
        )

    declinations_by_body: dict[str, float] = {}
    for body, value in declinations.items():
        canonical = _canonical_body(body)
        if canonical in declinations_by_body:
            raise ValueError(f"duplicate declination: {canonical}")
        declination = _finite(f"declinations[{canonical!r}]", value)
        if not -90.0 <= declination <= 90.0:
            raise ValueError(f"declination for {canonical} must be in [-90, 90]")
        declinations_by_body[canonical] = declination
    expected_bodies = (*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS)
    if set(declinations_by_body) != set(expected_bodies):
        missing = sorted(set(expected_bodies) - set(declinations_by_body))
        extra = sorted(set(declinations_by_body) - set(expected_bodies))
        raise ValueError(
            "declinations requires ten planets plus M.C. and Asc.; "
            f"missing={missing}, extra={extra}"
        )

    cusps = tuple(
        _finite(f"cusp_longitudes[{index}]", value) % 360.0
        for index, value in enumerate(cusp_longitudes)
    )
    if len(cusps) != 12:
        raise ValueError("cusp_longitudes must contain exactly twelve cusps")
    spans = tuple(
        (cusps[(index + 1) % 12] - cusp) % 360.0
        for index, cusp in enumerate(cusps)
    )
    if any(span <= 1e-12 for span in spans) or abs(sum(spans) - 360.0) > 1e-9:
        raise ValueError("cusp_longitudes must form one ordered zodiacal circuit")

    mc = _finite("mc_longitude", mc_longitude) % 360.0
    asc = _finite("asc_longitude", asc_longitude) % 360.0
    def angular_delta(first: float, second: float) -> float:
        return abs((first - second + 180.0) % 360.0 - 180.0)
    if angular_delta(asc, cusps[0]) > 1e-9:
        raise ValueError("asc_longitude must equal the first-house cusp")
    if angular_delta(mc, cusps[9]) > 1e-9:
        raise ValueError("mc_longitude must equal the tenth-house cusp")

    body_inputs: list[AstrodyneBodyInput] = []
    for body in ASTRODYNE_PLANETS:
        longitude = longitudes_by_planet[body]
        house, house_size, distance_from_weaker = _geometry_house(longitude, cusps)
        house_class = (
            "angular"
            if house in {1, 4, 7, 10}
            else "succedent"
            if house in {2, 5, 8, 11}
            else "cadent"
        )
        body_inputs.append(
            AstrodyneBodyInput(
                body=body,
                longitude_deg=longitude,
                house=house,
                house_class=house_class,
                distance_from_weaker_cusp_deg=distance_from_weaker,
                house_size_deg=house_size,
                declination_deg=declinations_by_body[body],
            )
        )
    body_inputs.extend(
        (
            AstrodyneBodyInput(
                "M.C.",
                mc,
                10,
                "angular",
                declination_deg=declinations_by_body["M.C."],
            ),
            AstrodyneBodyInput(
                "Asc.",
                asc,
                1,
                "angular",
                declination_deg=declinations_by_body["Asc."],
            ),
        )
    )
    cusp_signs = tuple(ASTRODYNE_SIGNS[int(cusp // 30.0)] for cusp in cusps)
    interceptions = _geometry_interceptions(cusps, cusp_signs)
    return natal_astrodynes(
        body_inputs,
        cusp_signs,
        intercepted_signs_by_house=interceptions,
        policy=policy,
    )


def natal_astrodynes(
    body_inputs: Sequence[AstrodyneBodyInput],
    cusp_signs: Sequence[str],
    *,
    intercepted_signs_by_house: Mapping[int, Sequence[str]] | None = None,
    policy: AstrodynePolicy | None = None,
) -> AstrodyneChartResult:
    """Build the complete bounded natal Astrodyne result from explicit geometry."""

    active_policy = _policy(policy)
    inputs_by_body: dict[str, AstrodyneBodyInput] = {}
    for item in body_inputs:
        if not isinstance(item, AstrodyneBodyInput):
            raise TypeError("body_inputs must contain AstrodyneBodyInput values")
        if item.body in inputs_by_body:
            raise ValueError(f"duplicate Astrodyne body input: {item.body}")
        inputs_by_body[item.body] = item
    expected_order = (*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS)
    if set(inputs_by_body) != set(expected_order):
        missing = sorted(set(expected_order) - set(inputs_by_body))
        extra = sorted(set(inputs_by_body) - set(expected_order))
        raise ValueError(f"full natal input requires all ten planets plus M.C./Asc.; missing={missing}, extra={extra}")
    inputs = tuple(inputs_by_body[body] for body in expected_order)

    canonical_cusps = tuple(_canonical_sign(sign) for sign in cusp_signs)
    if len(canonical_cusps) != 12:
        raise ValueError("cusp_signs must contain exactly twelve signs")
    interceptions = _canonical_interceptions(
        intercepted_signs_by_house, canonical_cusps
    )

    relations = _build_relation_set(inputs, active_policy)
    profiles = tuple(
        _build_body_profile(item, relations, policy=active_policy) for item in inputs
    )
    aggregate = _build_chart_aggregate(profiles, canonical_cusps, interceptions)
    summary = astrodynes_summary(aggregate)
    network = _build_network(profiles, relations)
    return AstrodyneChartResult(
        policy=active_policy,
        inputs=inputs,
        relations=relations,
        profiles=profiles,
        aggregate=aggregate,
        summary=summary,
        network=network,
    )


def validate_astrodynes_output(result: AstrodyneChartResult) -> tuple[str, ...]:
    """Return deterministic cross-layer invariant failures for one chart result."""

    failures: list[str] = []
    expected_order = (*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS)
    input_bodies = tuple(item.body for item in result.inputs)
    profile_bodies = tuple(item.body for item in result.profiles)
    if input_bodies != expected_order:
        failures.append("inputs are not in canonical body order")
    if profile_bodies != expected_order:
        failures.append("profiles are not in canonical body order")
    if len(set(input_bodies)) != len(expected_order):
        failures.append("input bodies are not unique")
    if not result.aggregate.checksums_pass:
        failures.append("sign/house checksum does not pass")
    if abs(result.summary.total_power - result.aggregate.total_house_power) > 1e-9:
        failures.append("summary power disagrees with chart aggregate")
    for entries, expected_harmony, label in (
        (result.summary.societies, result.aggregate.total_house_harmony, "society"),
        (result.summary.trinities, result.aggregate.total_house_harmony, "trinity"),
        (result.summary.elements, result.aggregate.total_sign_harmony, "element"),
        (result.summary.qualities, result.aggregate.total_sign_harmony, "quality"),
    ):
        if abs(sum(item.net_harmony for item in entries) - expected_harmony) > 1e-9:
            failures.append(f"{label} harmony does not partition the chart")
    if tuple(node.body for node in result.network.nodes) != profile_bodies:
        failures.append("network nodes do not align with profiles")
    profile_by_body = {profile.body: profile for profile in result.profiles}
    for node in result.network.nodes:
        profile = profile_by_body.get(node.body)
        if profile is None or abs(node.power - profile.total_power) > 1e-12:
            failures.append(f"network node power disagrees for {node.body}")
    admitted_keys = {item.sort_key for item in result.relations.admitted}
    edge_keys = {
        (
            *sorted((edge.body_a, edge.body_b)),
            edge.kind.value,
            edge.label,
        )
        for edge in result.network.edges
    }
    if admitted_keys != edge_keys:
        failures.append("network edges do not align with admitted relations")
    for profile in result.profiles:
        relation_keys = {item.sort_key for item in profile.relations}
        expected_keys = {
            item.sort_key for item in result.relations.scored if profile.body in item.bodies
        }
        if relation_keys != expected_keys:
            failures.append(f"profile relations disagree for {profile.body}")
    return tuple(failures)


# ---------------------------------------------------------------------------
# Phase 12 - Public API Curation
# ---------------------------------------------------------------------------


__all__ = [
    # Source constants and rows
    "ASTRODYNE_PLANETS",
    "ASTRODYNE_POINTS",
    "ASTRODYNE_SIGNS",
    "ASTRODYNE_HOUSE_CLASSES",
    "ASTRODYNE_ANGLE_POINT_POWER",
    "ASTRODYNE_PARALLEL_ORB_ARCMIN",
    "ASTRODYNE_ASPECTS",
    "ASTRODYNE_DIGNITY_ROWS",
    "ASTRODYNE_HOUSE_POWER_ROWS",
    "ASTRODYNE_ASPECT_ORB_ROWS",
    "ASTRODYNE_SOCIETY_GROUPS",
    "ASTRODYNE_TRINITY_GROUPS",
    "ASTRODYNE_ELEMENT_GROUPS",
    "ASTRODYNE_QUALITY_GROUPS",
    # Classification and policy
    "AstrodyneBodyKind",
    "AstrodyneDignityCondition",
    "AstrodyneAspectFamily",
    "AstrodyneRelationKind",
    "AstrodyneContributionSource",
    "AstrodyneParallelGeometry",
    "AstrodyneMercuryOrbRule",
    "AstrodyneSummaryFamily",
    "AstrodynePolicy",
    "DEFAULT_ASTRODYNE_POLICY",
    # Source and truth vessels
    "AstrodyneDignityRow",
    "AstrodyneHousePowerRow",
    "AstrodyneAspectOrbRow",
    "AstrodyneHousePositionTruth",
    "AstrodyneZodiacalAspectTruth",
    "AstrodyneParallelAspectTruth",
    "AstrodyneEssentialDignityTruth",
    "AstrodyneNatureContribution",
    "AstrodyneAspectHarmonyTruth",
    # Relations and integrated profiles
    "AstrodyneAspectRelation",
    "AstrodyneMutualReceptionRelation",
    "AstrodyneRelationSet",
    "AstrodyneBodyInput",
    "AstrodyneContribution",
    "AstrodyneBodyConditionProfile",
    # Aggregates and network
    "AstrodyneRulerShareTruth",
    "AstrodyneSignAggregate",
    "AstrodyneHouseAggregate",
    "AstrodyneChartAggregate",
    "AstrodyneSummaryEntry",
    "AstrodyneSummaryProfile",
    "AstrodyneNetworkNode",
    "AstrodyneNetworkEdge",
    "AstrodyneNetwork",
    "AstrodyneChartResult",
    # Computation
    "house_position_power",
    "zodiacal_aspect_power",
    "parallel_aspect_power",
    "essential_dignity",
    "aspect_harmony",
    "evaluate_zodiacal_relation",
    "evaluate_parallel_relation",
    "mutual_reception",
    "ruler_power_share",
    "astrodynes_summary",
    "natal_astrodynes_from_geometry",
    "natal_astrodynes",
    "validate_astrodynes_output",
]
