"""Church of Light progressed Astrodynes doctrine and derivation truth."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from math import isfinite

from .astrodynes import (
    ASTRODYNE_ASPECT_ORB_ROWS,
    ASTRODYNE_DIGNITY_ROWS,
    ASTRODYNE_HOUSE_CLASSES,
    ASTRODYNE_PLANETS,
    ASTRODYNE_POINTS,
    ASTRODYNE_SIGNS,
    AstrodyneAspectHarmonyTruth,
    aspect_harmony,
    essential_dignity,
)


class ProgressedAstrodyneTier(StrEnum):
    """Church of Light progression scale governing carried and aspect power."""

    MAJOR = "major"
    MAJOR_MOON = "major_moon"
    MINOR = "minor"
    TRANSIT = "transit"


class ProgressedInfluenceUnit(StrEnum):
    """Unit retained by one constant-rate total-influence product."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class ProgressedTerminalKind(StrEnum):
    """Identity of a radical or major-progressed aspect terminal."""

    RADICAL = "radical"
    MAJOR_PROGRESSED = "major_progressed"
    MINOR_PROGRESSED = "minor_progressed"
    TRANSIT = "transit"


PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES: tuple[str, ...] = (
    "Saturn-Sun dated subtraction prints 11.13 although staged arithmetic gives 11.14.",
    "Sun-Pluto prints 15.72 discord although its rule and house arithmetic use 18.72.",
    "M.C.-Moon prints 19.94 although its peak and distance give 19.91.",
    "Mercury-Uranus p prints 13.58 although staged arithmetic gives 13.59.",
    "Jupiter-Saturn prints 4.58 harmony although its nature terms cancel to 4.88.",
    "Jupiter-Uranus square is signed harmonious although later arithmetic treats it as discordant.",
    "The printed seventh-house Jupiter products sum to 339.86, not 339.76.",
    "The printed Moon terminal rows do not reproduce the stated 61.87 total.",
    "The ninth-house prose once prints 51.32 although its baseline and total require 51.82.",
)


@dataclass(frozen=True, slots=True)
class ProgressedAstrodynePolicy:
    """Fixed source doctrine for the admitted progressed scalar core."""

    major_carry_factor: float = 0.5
    major_moon_carry_divisor: float = 14.0
    minor_carry_divisor: float = 54.6
    transit_carry_divisor: float = 730.50
    aspect_percentage_per_orb_degree: float = 0.05
    major_moon_aspect_divisor: float = 7.0
    minor_aspect_divisor: float = 27.3
    transit_aspect_divisor: float = 365.25
    effective_orb_arcmin: float = 60.0
    orb_limit_fraction: float = 0.5
    major_mutual_reception_bonus_each: float = 2.5
    total_influence_average_factor: float = 0.75
    manual_rounding_digits: int = 2

    def __post_init__(self) -> None:
        expected = ProgressedAstrodynePolicy.__dataclass_fields__
        defaults = {
            name: field.default
            for name, field in expected.items()
        }
        for name, default in defaults.items():
            if getattr(self, name) != default:
                raise ValueError(
                    f"unsupported progressed Astrodyne policy value for {name}"
                )


DEFAULT_PROGRESSED_ASTRODYNE_POLICY = ProgressedAstrodynePolicy()


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _non_negative(name: str, value: float) -> float:
    result = _finite(name, value)
    if result < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _manual_round(value: float, digits: int = 2) -> float:
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def _tier(value: ProgressedAstrodyneTier | str) -> ProgressedAstrodyneTier:
    try:
        return ProgressedAstrodyneTier(value)
    except ValueError as exc:
        supported = ", ".join(item.value for item in ProgressedAstrodyneTier)
        raise ValueError(f"unsupported progressed tier {value!r}; use {supported}") from exc


def _policy(
    policy: ProgressedAstrodynePolicy | None,
) -> ProgressedAstrodynePolicy:
    if policy is None:
        return DEFAULT_PROGRESSED_ASTRODYNE_POLICY
    if not isinstance(policy, ProgressedAstrodynePolicy):
        raise TypeError("policy must be ProgressedAstrodynePolicy")
    return policy


def _carry_factor(
    tier: ProgressedAstrodyneTier,
    policy: ProgressedAstrodynePolicy,
) -> float:
    if tier is ProgressedAstrodyneTier.MAJOR:
        return policy.major_carry_factor
    if tier is ProgressedAstrodyneTier.MAJOR_MOON:
        return 1.0 / policy.major_moon_carry_divisor
    if tier is ProgressedAstrodyneTier.MINOR:
        return 1.0 / policy.minor_carry_divisor
    return 1.0 / policy.transit_carry_divisor


def _aspect_divisor(
    tier: ProgressedAstrodyneTier,
    policy: ProgressedAstrodynePolicy,
) -> float:
    if tier is ProgressedAstrodyneTier.MAJOR:
        return 1.0
    if tier is ProgressedAstrodyneTier.MAJOR_MOON:
        return policy.major_moon_aspect_divisor
    if tier is ProgressedAstrodyneTier.MINOR:
        return policy.minor_aspect_divisor
    return policy.transit_aspect_divisor


@dataclass(frozen=True, slots=True)
class ProgressedCarryTruth:
    """Normal progressed power and harmony/discord carried by one body."""

    tier: ProgressedAstrodyneTier
    birth_power: float
    birth_harmony: float
    birth_discord: float
    progressed_dignity_delta: float
    carry_factor: float
    carried_power: float
    carried_harmony: float
    carried_discord: float
    dignity_harmony: float
    dignity_discord: float
    total_harmony: float
    total_discord: float

    @property
    def manual_carried_power(self) -> float:
        return _manual_round(self.carried_power)

    @property
    def manual_carried_harmony(self) -> float:
        return _manual_round(self.carried_harmony)

    @property
    def manual_carried_discord(self) -> float:
        return _manual_round(self.carried_discord)

    @property
    def manual_dignity_harmony(self) -> float:
        return _manual_round(self.dignity_harmony)

    @property
    def manual_dignity_discord(self) -> float:
        return _manual_round(self.dignity_discord)

    @property
    def manual_total_harmony(self) -> float:
        return _manual_round(
            self.manual_carried_harmony + self.manual_dignity_harmony
        )

    @property
    def manual_total_discord(self) -> float:
        return _manual_round(
            self.manual_carried_discord + self.manual_dignity_discord
        )


def progressed_carry(
    birth_power: float,
    birth_harmony: float,
    birth_discord: float,
    progressed_dignity_delta: float,
    tier: ProgressedAstrodyneTier | str,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedCarryTruth:
    """Compute the manual's normal carried influence for one progressed body."""

    active_policy = _policy(policy)
    resolved_tier = _tier(tier)
    power = _non_negative("birth_power", birth_power)
    harmony = _non_negative("birth_harmony", birth_harmony)
    discord = _non_negative("birth_discord", birth_discord)
    dignity = _finite("progressed_dignity_delta", progressed_dignity_delta)
    factor = _carry_factor(resolved_tier, active_policy)
    carried_harmony = harmony * factor
    carried_discord = discord * factor
    dignity_harmony = max(0.0, dignity) * factor
    dignity_discord = max(0.0, -dignity) * factor
    return ProgressedCarryTruth(
        tier=resolved_tier,
        birth_power=power,
        birth_harmony=harmony,
        birth_discord=discord,
        progressed_dignity_delta=dignity,
        carry_factor=factor,
        carried_power=power * factor,
        carried_harmony=carried_harmony,
        carried_discord=carried_discord,
        dignity_harmony=dignity_harmony,
        dignity_discord=dignity_discord,
        total_harmony=carried_harmony + dignity_harmony,
        total_discord=carried_discord + dignity_discord,
    )


_ORB_ROWS = {row.aspect: row for row in ASTRODYNE_ASPECT_ORB_ROWS}
def _canonical_house_class(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("house class must be a string")
    result = value.strip().lower()
    if result not in ASTRODYNE_HOUSE_CLASSES:
        raise ValueError(f"unsupported house class: {value!r}")
    return result


def _canonical_aspect(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("aspect must be a string")
    result = value.strip().lower().replace("_", "-")
    if result == "parallel":
        return result
    if result not in _ORB_ROWS:
        raise ValueError(f"unsupported progressed Astrodyne aspect: {value!r}")
    return result


def _progressed_orb(
    house_class: str,
    aspect: str,
    uses_luminary_column: bool,
) -> float:
    row = _ORB_ROWS["conjunction" if aspect == "parallel" else aspect]
    field = (
        f"{house_class}_"
        f"{'luminary' if uses_luminary_column else 'planet'}_deg"
    )
    return float(getattr(row, field))


@dataclass(frozen=True, slots=True)
class ProgressedAspectPercentageTruth:
    """Source-row selection for one progressed aspect percentage."""

    aspect: str
    source_aspect: str
    governing_house_class: str
    uses_luminary_column: bool
    source_column: str
    selected_orb_degrees: float
    percentage_factor: float
    progressed_percentage: float


def progressed_aspect_percentage(
    aspect: str,
    governing_house_class: str,
    *,
    uses_luminary_column: bool,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedAspectPercentageTruth:
    """Derive one progressed percentage from its explicit source column.

    Terminal assembly owns which radical/major terminal supplies the most
    powerful house class.  Keeping that choice explicit here prevents a minor
    or transit angle from being mistaken for a governing natal/major house.
    Mercury uses the luminary column under the manual's progressed rule.
    """

    active_policy = _policy(policy)
    house_class = _canonical_house_class(governing_house_class)
    if not isinstance(uses_luminary_column, bool):
        raise TypeError("uses_luminary_column must be bool")
    kind = _canonical_aspect(aspect)
    source_aspect = "conjunction" if kind == "parallel" else kind
    selected_orb = _progressed_orb(
        house_class,
        kind,
        uses_luminary_column,
    )
    return ProgressedAspectPercentageTruth(
        aspect=kind,
        source_aspect=source_aspect,
        governing_house_class=house_class,
        uses_luminary_column=uses_luminary_column,
        source_column="luminary" if uses_luminary_column else "planet",
        selected_orb_degrees=selected_orb,
        percentage_factor=active_policy.aspect_percentage_per_orb_degree,
        progressed_percentage=(
            selected_orb * active_policy.aspect_percentage_per_orb_degree
        ),
    )


@dataclass(frozen=True, slots=True)
class ProgressedAspectPeakTruth:
    """Exact and manual-staged peak power for one progressed aspect."""

    tier: ProgressedAstrodyneTier
    birth_power_a: float
    birth_power_b: float
    progressed_percentage: float
    tier_divisor: float
    average_birth_power: float
    major_peak_power: float
    peak_power: float
    manual_average_birth_power: float
    manual_major_peak_power: float
    manual_peak_power: float


def progressed_aspect_peak_power(
    birth_power_a: float,
    birth_power_b: float,
    progressed_percentage: float,
    tier: ProgressedAstrodyneTier | str,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedAspectPeakTruth:
    """Compute peak power while retaining the manual's staged rounding path."""

    active_policy = _policy(policy)
    resolved_tier = _tier(tier)
    first = _non_negative("birth_power_a", birth_power_a)
    second = _non_negative("birth_power_b", birth_power_b)
    percentage = _non_negative("progressed_percentage", progressed_percentage)
    divisor = _aspect_divisor(resolved_tier, active_policy)
    average = (first + second) / 2.0
    major_peak = average * percentage
    peak = major_peak / divisor
    manual_average = _manual_round(average)
    manual_major_peak = _manual_round(manual_average * percentage)
    manual_peak = _manual_round(manual_major_peak / divisor)
    return ProgressedAspectPeakTruth(
        tier=resolved_tier,
        birth_power_a=first,
        birth_power_b=second,
        progressed_percentage=percentage,
        tier_divisor=divisor,
        average_birth_power=average,
        major_peak_power=major_peak,
        peak_power=peak,
        manual_average_birth_power=manual_average,
        manual_major_peak_power=manual_major_peak,
        manual_peak_power=manual_peak,
    )


@dataclass(frozen=True, slots=True)
class ProgressedAspectMomentTruth:
    """Power of one progressed aspect on a date."""

    distance_arcmin: float
    orb_limit_arcmin: float
    within_orb: bool
    scale_fraction: float
    peak_power: float
    power: float
    manual_peak_power: float
    manual_decrement_power: float
    manual_power: float


def progressed_aspect_at_distance(
    peak_power: float,
    distance_arcmin: float,
    *,
    manual_peak_power: float | None = None,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedAspectMomentTruth:
    """Apply the manual's half-at-60-minutes linear progressed power curve.

    Manual-facing harmony/discord is derived from the staged, rounded current
    power afterward; scaling an already-rounded peak harmony can differ by a
    hundredth from the printed examples.
    """

    active_policy = _policy(policy)
    power = _non_negative("peak_power", peak_power)
    distance = _non_negative("distance_arcmin", distance_arcmin)
    limit = active_policy.effective_orb_arcmin
    admitted = distance <= limit
    fraction = 0.0 if not admitted else 1.0 - distance / (2.0 * limit)

    manual_peak = (
        _manual_round(power)
        if manual_peak_power is None
        else _non_negative("manual_peak_power", manual_peak_power)
    )
    if admitted:
        decrement_power = _manual_round(
            manual_peak * distance / (2.0 * limit)
        )
        manual_power = _manual_round(manual_peak - decrement_power)
    else:
        decrement_power = 0.0
        manual_power = 0.0
    return ProgressedAspectMomentTruth(
        distance_arcmin=distance,
        orb_limit_arcmin=limit,
        within_orb=admitted,
        scale_fraction=fraction,
        peak_power=power,
        power=power * fraction,
        manual_peak_power=manual_peak,
        manual_decrement_power=decrement_power,
        manual_power=manual_power,
    )


@dataclass(frozen=True, slots=True)
class ProgressedMutualReceptionTruth:
    """Vessel: Structured progressed mutual reception truth data."""
    tier: ProgressedAstrodyneTier
    major_bonus_each: float
    tier_divisor: float
    bonus_each: float

    @property
    def manual_bonus_each(self) -> float:
        return _manual_round(self.bonus_each)


def progressed_mutual_reception_bonus(
    tier: ProgressedAstrodyneTier | str,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedMutualReceptionTruth:
    """Return the in-orb mutual-reception bonus granted to each planet."""

    active_policy = _policy(policy)
    resolved_tier = _tier(tier)
    divisor = _aspect_divisor(resolved_tier, active_policy)
    return ProgressedMutualReceptionTruth(
        tier=resolved_tier,
        major_bonus_each=active_policy.major_mutual_reception_bonus_each,
        tier_divisor=divisor,
        bonus_each=active_policy.major_mutual_reception_bonus_each / divisor,
    )


def progressed_aspect_harmony(
    body_a: str,
    body_b: str,
    aspect: str,
    astrodyne_power: float,
) -> AstrodyneAspectHarmonyTruth:
    """Apply the shared Church of Light aspect/nature translation."""

    return aspect_harmony(body_a, body_b, aspect, astrodyne_power)


@dataclass(frozen=True, slots=True)
class ProgressedTotalInfluenceTruth:
    """Vessel: Structured progressed total influence truth data."""
    unit: ProgressedInfluenceUnit
    duration: float
    average_factor: float
    peak_power: float
    peak_harmony: float
    peak_discord: float
    average_power: float
    average_harmony: float
    average_discord: float
    total_power: float
    total_harmony: float
    total_discord: float
    manual_average_power: float
    manual_average_harmony: float
    manual_average_discord: float
    manual_total_power: float
    manual_total_harmony: float
    manual_total_discord: float


@dataclass(frozen=True, slots=True)
class ProgressedCompoundDuration:
    """Calendar-style duration used by the manual's compound influence example."""

    years: int = 0
    months: int = 0
    days: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.years, bool) or not isinstance(self.years, int):
            raise TypeError("years must be an integer")
        if isinstance(self.months, bool) or not isinstance(self.months, int):
            raise TypeError("months must be an integer")
        if self.years < 0 or self.months < 0:
            raise ValueError("duration years and months must be non-negative")
        object.__setattr__(self, "days", _non_negative("days", self.days))


@dataclass(frozen=True, slots=True)
class ProgressedCompoundQuantity:
    """Normalized manual-facing astrodyne/harmodyne/discordyne duration."""

    years: int
    months: int
    days: float


@dataclass(frozen=True, slots=True)
class ProgressedCompoundInfluenceTruth:
    """Vessel: Structured progressed compound influence truth data."""
    duration: ProgressedCompoundDuration
    average_factor: float
    manual_average_power: float
    manual_average_harmony: float
    manual_average_discord: float
    power: ProgressedCompoundQuantity
    harmony: ProgressedCompoundQuantity
    discord: ProgressedCompoundQuantity


def progressed_total_influence(
    peak_power: float,
    peak_harmony: float,
    peak_discord: float,
    duration: float,
    unit: ProgressedInfluenceUnit | str,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedTotalInfluenceTruth:
    """Compute the manual's constant-rate 0.75-peak interval product."""

    active_policy = _policy(policy)
    power = _non_negative("peak_power", peak_power)
    harmony = _non_negative("peak_harmony", peak_harmony)
    discord = _non_negative("peak_discord", peak_discord)
    span = _non_negative("duration", duration)
    try:
        resolved_unit = ProgressedInfluenceUnit(unit)
    except ValueError as exc:
        raise ValueError(f"unsupported influence unit: {unit!r}") from exc
    factor = active_policy.total_influence_average_factor
    average_power = power * factor
    average_harmony = harmony * factor
    average_discord = discord * factor
    manual_average_power = _manual_round(average_power)
    manual_average_harmony = _manual_round(average_harmony)
    manual_average_discord = _manual_round(average_discord)
    return ProgressedTotalInfluenceTruth(
        unit=resolved_unit,
        duration=span,
        average_factor=factor,
        peak_power=power,
        peak_harmony=harmony,
        peak_discord=discord,
        average_power=average_power,
        average_harmony=average_harmony,
        average_discord=average_discord,
        total_power=average_power * span,
        total_harmony=average_harmony * span,
        total_discord=average_discord * span,
        manual_average_power=manual_average_power,
        manual_average_harmony=manual_average_harmony,
        manual_average_discord=manual_average_discord,
        manual_total_power=_manual_round(manual_average_power * span),
        manual_total_harmony=_manual_round(manual_average_harmony * span),
        manual_total_discord=_manual_round(manual_average_discord * span),
    )


def _compound_quantity(
    manual_average: float,
    duration: ProgressedCompoundDuration,
) -> ProgressedCompoundQuantity:
    year_value = _manual_round(manual_average * duration.years)
    whole_years = int(year_value)
    days = (year_value - whole_years) * 365.25

    month_value = _manual_round(manual_average * duration.months)
    whole_months = int(month_value)
    days += (month_value - whole_months) * 30.0
    days += manual_average * duration.days

    extra_months = int(days // 30.0)
    days -= extra_months * 30.0
    whole_months += extra_months
    whole_years += whole_months // 12
    whole_months %= 12
    return ProgressedCompoundQuantity(
        years=whole_years,
        months=whole_months,
        days=_manual_round(days),
    )


def progressed_compound_total_influence(
    peak_power: float,
    peak_harmony: float,
    peak_discord: float,
    duration: ProgressedCompoundDuration,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedCompoundInfluenceTruth:
    """Reproduce the manual's 365.25-day year / 30-day month normalization."""

    if not isinstance(duration, ProgressedCompoundDuration):
        raise TypeError("duration must be ProgressedCompoundDuration")
    active_policy = _policy(policy)
    power = _non_negative("peak_power", peak_power)
    harmony = _non_negative("peak_harmony", peak_harmony)
    discord = _non_negative("peak_discord", peak_discord)
    factor = active_policy.total_influence_average_factor
    average_power = _manual_round(power * factor)
    average_harmony = _manual_round(harmony * factor)
    average_discord = _manual_round(discord * factor)
    return ProgressedCompoundInfluenceTruth(
        duration=duration,
        average_factor=factor,
        manual_average_power=average_power,
        manual_average_harmony=average_harmony,
        manual_average_discord=average_discord,
        power=_compound_quantity(average_power, duration),
        harmony=_compound_quantity(average_harmony, duration),
        discord=_compound_quantity(average_discord, duration),
    )


_CANONICAL_BODY_ORDER = (*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS)


def _canonical_body(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("body must be a string")
    stripped = value.strip()
    for body in _CANONICAL_BODY_ORDER:
        if stripped.casefold() == body.casefold():
            return body
    raise ValueError(f"unsupported Astrodyne body: {value!r}")


@dataclass(frozen=True, slots=True)
class ProgressedNatalBodyValue:
    """Natal body totals used as the source of progressed carried influence."""

    body: str
    power: float
    harmony: float
    discord: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", _canonical_body(self.body))
        object.__setattr__(self, "power", _non_negative("power", self.power))
        object.__setattr__(
            self, "harmony", _non_negative("harmony", self.harmony)
        )
        object.__setattr__(
            self, "discord", _non_negative("discord", self.discord)
        )


@dataclass(frozen=True, slots=True)
class ProgressedBaselineValue:
    """Power and separate harmony/discord magnitudes for a sign or house."""

    power: float
    harmony: float
    discord: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "power", _non_negative("power", self.power))
        object.__setattr__(
            self, "harmony", _non_negative("harmony", self.harmony)
        )
        object.__setattr__(
            self, "discord", _non_negative("discord", self.discord)
        )

    @property
    def net_harmony(self) -> float:
        return self.harmony - self.discord


@dataclass(frozen=True, slots=True)
class ProgressedBodyPlacement:
    """Explicit major-progressed location of one natal body or angle."""

    body: str
    longitude_deg: float
    house: int

    def __post_init__(self) -> None:
        body = _canonical_body(self.body)
        longitude = _finite("longitude_deg", self.longitude_deg) % 360.0
        if isinstance(self.house, bool) or not isinstance(self.house, int):
            raise TypeError("house must be an integer")
        if self.house not in range(1, 13):
            raise ValueError("house must be in [1, 12]")
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "longitude_deg", longitude)

    @property
    def sign(self) -> str:
        return ASTRODYNE_SIGNS[int(self.longitude_deg // 30.0)]

    @property
    def sign_degree(self) -> float:
        return self.longitude_deg % 30.0


@dataclass(frozen=True, slots=True)
class ProgressedNormalBodyProfile:
    """Vessel: Structured progressed normal body profile data."""
    body: str
    placement: ProgressedBodyPlacement
    natal: ProgressedNatalBodyValue
    dignity_delta: float
    carry: ProgressedCarryTruth

    def __post_init__(self) -> None:
        if self.body != self.placement.body or self.body != self.natal.body:
            raise ValueError("normal progressed body identity is inconsistent")


@dataclass(frozen=True, slots=True)
class ProgressedNormalAggregateEntry:
    """One normal progressed sign or house total with visible baseline/addition."""

    name: str
    baseline: ProgressedBaselineValue
    occupants: tuple[str, ...]
    added_power: float
    added_harmony: float
    added_discord: float
    manual_added_power: float
    manual_added_harmony: float
    manual_added_discord: float
    total_power: float
    total_harmony: float
    total_discord: float

    def __post_init__(self) -> None:
        numeric = (
            self.added_power,
            self.added_harmony,
            self.added_discord,
            self.manual_added_power,
            self.manual_added_harmony,
            self.manual_added_discord,
            self.total_power,
            self.total_harmony,
            self.total_discord,
        )
        if any(not isfinite(value) or value < 0.0 for value in numeric):
            raise ValueError("normal progressed aggregate values must be finite and non-negative")
        if abs(self.total_power - (self.baseline.power + self.added_power)) > 1e-12:
            raise ValueError("normal progressed aggregate power is inconsistent")
        if abs(
            self.total_harmony - (self.baseline.harmony + self.added_harmony)
        ) > 1e-12:
            raise ValueError("normal progressed aggregate harmony is inconsistent")
        if abs(
            self.total_discord - (self.baseline.discord + self.added_discord)
        ) > 1e-12:
            raise ValueError("normal progressed aggregate discord is inconsistent")

    @property
    def net_harmony(self) -> float:
        return self.total_harmony - self.total_discord

    @property
    def manual_total_power(self) -> float:
        return _manual_round(self.baseline.power + self.manual_added_power)

    @property
    def manual_total_harmony(self) -> float:
        return _manual_round(self.baseline.harmony + self.manual_added_harmony)

    @property
    def manual_total_discord(self) -> float:
        return _manual_round(self.baseline.discord + self.manual_added_discord)

    @property
    def manual_net_harmony(self) -> float:
        return _manual_round(
            self.manual_total_harmony - self.manual_total_discord
        )


@dataclass(frozen=True, slots=True)
class ProgressedNormalHoroscope:
    """Normal major-progressed baseline before accessory progressed aspects."""

    profiles: tuple[ProgressedNormalBodyProfile, ...]
    signs: tuple[ProgressedNormalAggregateEntry, ...]
    houses: tuple[ProgressedNormalAggregateEntry, ...]
    total_sign_power: float
    total_house_power: float
    total_sign_harmony: float
    total_house_harmony: float

    def __post_init__(self) -> None:
        if tuple(profile.body for profile in self.profiles) != _CANONICAL_BODY_ORDER:
            raise ValueError("normal progressed profiles are not in canonical order")
        if tuple(entry.name for entry in self.signs) != ASTRODYNE_SIGNS:
            raise ValueError("normal progressed signs are not in zodiacal order")
        if tuple(entry.name for entry in self.houses) != tuple(
            str(house) for house in range(1, 13)
        ):
            raise ValueError("normal progressed houses are not in numerical order")
        if not self.checksums_pass:
            raise ValueError("normal progressed sign/house checksums do not pass")

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

    def sign(self, name: str) -> ProgressedNormalAggregateEntry:
        try:
            index = ASTRODYNE_SIGNS.index(name)
        except ValueError as exc:
            raise KeyError(name) from exc
        return self.signs[index]

    def house(self, number: int) -> ProgressedNormalAggregateEntry:
        if number not in range(1, 13):
            raise KeyError(number)
        return self.houses[number - 1]


def _complete_body_map(
    values: Sequence[ProgressedNatalBodyValue | ProgressedBodyPlacement],
    label: str,
    expected_type: type,
) -> dict[str, ProgressedNatalBodyValue | ProgressedBodyPlacement]:
    result: dict[str, ProgressedNatalBodyValue | ProgressedBodyPlacement] = {}
    for item in values:
        if not isinstance(item, expected_type):
            raise TypeError(f"{label} must contain {expected_type.__name__} values")
        if item.body in result:
            raise ValueError(f"duplicate {label} body: {item.body}")
        result[item.body] = item
    missing = sorted(set(_CANONICAL_BODY_ORDER) - set(result))
    extra = sorted(set(result) - set(_CANONICAL_BODY_ORDER))
    if missing or extra:
        raise ValueError(
            f"{label} requires ten planets plus M.C./Asc.; "
            f"missing={missing}, extra={extra}"
        )
    return result


def _baseline_signs(
    values: Mapping[str, ProgressedBaselineValue],
) -> dict[str, ProgressedBaselineValue]:
    if set(values) != set(ASTRODYNE_SIGNS):
        missing = sorted(set(ASTRODYNE_SIGNS) - set(values))
        extra = sorted(set(values) - set(ASTRODYNE_SIGNS))
        raise ValueError(
            f"birth_sign_values requires all twelve signs; "
            f"missing={missing}, extra={extra}"
        )
    return {sign: values[sign] for sign in ASTRODYNE_SIGNS}


def _baseline_houses(
    values: Mapping[int, ProgressedBaselineValue],
) -> dict[int, ProgressedBaselineValue]:
    expected = set(range(1, 13))
    if set(values) != expected:
        missing = sorted(expected - set(values))
        extra = sorted(set(values) - expected)
        raise ValueError(
            f"birth_house_values requires houses 1-12; "
            f"missing={missing}, extra={extra}"
        )
    return {house: values[house] for house in range(1, 13)}


def normal_progressed_horoscope(
    birth_body_values: Sequence[ProgressedNatalBodyValue],
    birth_sign_values: Mapping[str, ProgressedBaselineValue],
    birth_house_values: Mapping[int, ProgressedBaselineValue],
    placements: Sequence[ProgressedBodyPlacement],
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedNormalHoroscope:
    """Build the normal major-progressed horoscope from explicit placements."""

    active_policy = _policy(policy)
    natal_map = _complete_body_map(
        birth_body_values,
        "birth_body_values",
        ProgressedNatalBodyValue,
    )
    placement_map = _complete_body_map(
        placements,
        "placements",
        ProgressedBodyPlacement,
    )
    sign_baselines = _baseline_signs(birth_sign_values)
    house_baselines = _baseline_houses(birth_house_values)
    if abs(
        sum(item.power for item in sign_baselines.values())
        - sum(item.power for item in house_baselines.values())
    ) > 1e-9:
        raise ValueError("birth sign/house power baselines do not reconcile")
    if abs(
        sum(item.net_harmony for item in sign_baselines.values())
        - sum(item.net_harmony for item in house_baselines.values())
    ) > 1e-9:
        raise ValueError("birth sign/house harmony baselines do not reconcile")

    profiles: list[ProgressedNormalBodyProfile] = []
    for body in _CANONICAL_BODY_ORDER:
        natal = natal_map[body]
        placement = placement_map[body]
        assert isinstance(natal, ProgressedNatalBodyValue)
        assert isinstance(placement, ProgressedBodyPlacement)
        dignity_delta = (
            essential_dignity(body, placement.sign, placement.sign_degree).harmony_delta
            if body in ASTRODYNE_PLANETS
            else 0.0
        )
        tier = (
            ProgressedAstrodyneTier.MAJOR_MOON
            if body == "Moon"
            else ProgressedAstrodyneTier.MAJOR
        )
        carry = progressed_carry(
            natal.power,
            natal.harmony,
            natal.discord,
            dignity_delta,
            tier,
            policy=active_policy,
        )
        profiles.append(
            ProgressedNormalBodyProfile(
                body=body,
                placement=placement,
                natal=natal,
                dignity_delta=dignity_delta,
                carry=carry,
            )
        )

    def aggregate(
        names: Sequence[str],
        baselines: Mapping[str, ProgressedBaselineValue],
        key,
    ) -> tuple[ProgressedNormalAggregateEntry, ...]:
        entries = []
        for name in names:
            occupants = tuple(profile for profile in profiles if key(profile) == name)
            baseline = baselines[name]
            added_power = sum(item.carry.carried_power for item in occupants)
            added_harmony = sum(item.carry.total_harmony for item in occupants)
            added_discord = sum(item.carry.total_discord for item in occupants)
            manual_added_power = sum(
                item.carry.manual_carried_power for item in occupants
            )
            manual_added_harmony = sum(
                item.carry.manual_total_harmony for item in occupants
            )
            manual_added_discord = sum(
                item.carry.manual_total_discord for item in occupants
            )
            entries.append(
                ProgressedNormalAggregateEntry(
                    name=name,
                    baseline=baseline,
                    occupants=tuple(item.body for item in occupants),
                    added_power=added_power,
                    added_harmony=added_harmony,
                    added_discord=added_discord,
                    manual_added_power=manual_added_power,
                    manual_added_harmony=manual_added_harmony,
                    manual_added_discord=manual_added_discord,
                    total_power=baseline.power + added_power,
                    total_harmony=baseline.harmony + added_harmony,
                    total_discord=baseline.discord + added_discord,
                )
            )
        return tuple(entries)

    signs = aggregate(
        ASTRODYNE_SIGNS,
        sign_baselines,
        lambda profile: profile.placement.sign,
    )
    house_baselines_by_name = {
        str(house): value for house, value in house_baselines.items()
    }
    houses = aggregate(
        tuple(str(house) for house in range(1, 13)),
        house_baselines_by_name,
        lambda profile: str(profile.placement.house),
    )
    total_sign_power = sum(item.total_power for item in signs)
    total_house_power = sum(item.total_power for item in houses)
    total_sign_harmony = sum(item.net_harmony for item in signs)
    total_house_harmony = sum(item.net_harmony for item in houses)
    return ProgressedNormalHoroscope(
        profiles=tuple(profiles),
        signs=signs,
        houses=houses,
        total_sign_power=total_sign_power,
        total_house_power=total_house_power,
        total_sign_harmony=total_sign_harmony,
        total_house_harmony=total_house_harmony,
    )


@dataclass(frozen=True, slots=True)
class ProgressedAstrodyneTerminal:
    """One explicit radical or major-progressed geometric terminal."""

    body: str
    kind: ProgressedTerminalKind
    longitude_deg: float
    house_class: str
    declination_deg: float | None = None

    def __post_init__(self) -> None:
        body = _canonical_body(self.body)
        try:
            kind = ProgressedTerminalKind(self.kind)
        except ValueError as exc:
            raise ValueError(f"unsupported terminal kind: {self.kind!r}") from exc
        longitude = _finite("longitude_deg", self.longitude_deg) % 360.0
        house_class = _canonical_house_class(self.house_class)
        declination = self.declination_deg
        if declination is not None:
            declination = _finite("declination_deg", declination)
            if not -90.0 <= declination <= 90.0:
                raise ValueError("declination_deg must be in [-90, 90]")
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "longitude_deg", longitude)
        object.__setattr__(self, "house_class", house_class)
        object.__setattr__(self, "declination_deg", declination)

    @property
    def terminal_id(self) -> str:
        suffix = {
            ProgressedTerminalKind.RADICAL: "r",
            ProgressedTerminalKind.MAJOR_PROGRESSED: "p",
            ProgressedTerminalKind.MINOR_PROGRESSED: "m",
            ProgressedTerminalKind.TRANSIT: "t",
        }[self.kind]
        return f"{self.body}:{suffix}"


@dataclass(frozen=True, slots=True)
class ProgressedMajorAspectRelation:
    """One evaluated major progressed relation with terminal and scoring truth."""

    aspect: str
    tier: ProgressedAstrodyneTier
    direct_terminals: tuple[ProgressedAstrodyneTerminal, ...]
    indirect_terminals: tuple[ProgressedAstrodyneTerminal, ...]
    distance_arcmin: float
    percentage_truth: ProgressedAspectPercentageTruth
    peak_truth: ProgressedAspectPeakTruth
    peak_harmony_truth: AstrodyneAspectHarmonyTruth
    manual_peak_harmony_truth: AstrodyneAspectHarmonyTruth
    moment_truth: ProgressedAspectMomentTruth
    moment_harmony_truth: AstrodyneAspectHarmonyTruth
    manual_moment_harmony_truth: AstrodyneAspectHarmonyTruth

    @property
    def detected(self) -> bool:
        return True

    @property
    def admitted(self) -> bool:
        return self.moment_truth.within_orb

    @property
    def scored(self) -> bool:
        return self.admitted and self.moment_truth.power > 0.0

    @property
    def relation_id(self) -> str:
        terminals = "|".join(item.terminal_id for item in self.direct_terminals)
        return f"{terminals}|{self.aspect}|{self.tier.value}"


def _counterpart(
    direct: ProgressedAstrodyneTerminal,
    counterpart: ProgressedAstrodyneTerminal,
) -> None:
    admitted = {
        ProgressedTerminalKind.RADICAL,
        ProgressedTerminalKind.MAJOR_PROGRESSED,
    }
    if direct.kind not in admitted or counterpart.kind not in admitted:
        raise ValueError("counterparts must be radical/major-progressed terminals")
    if direct.body != counterpart.body:
        raise ValueError("counterpart must belong to the same body as its direct terminal")
    if direct.kind is counterpart.kind:
        raise ValueError("counterpart must use the opposite radical/progressed kind")


def _zodiacal_distance_arcmin(
    first: ProgressedAstrodyneTerminal,
    second: ProgressedAstrodyneTerminal,
    aspect: str,
) -> float:
    row = _ORB_ROWS[aspect]
    separation = abs(first.longitude_deg - second.longitude_deg)
    separation = min(separation, 360.0 - separation)
    return abs(separation - row.exact_angle_deg) * 60.0


def _parallel_distance_arcmin(
    first: ProgressedAstrodyneTerminal,
    second: ProgressedAstrodyneTerminal,
) -> float:
    if first.declination_deg is None or second.declination_deg is None:
        raise ValueError("parallel relations require both terminal declinations")
    return abs(abs(first.declination_deg) - abs(second.declination_deg)) * 60.0


def evaluate_major_progressed_relation(
    direct_a: ProgressedAstrodyneTerminal,
    direct_b: ProgressedAstrodyneTerminal,
    counterpart_a: ProgressedAstrodyneTerminal | None,
    counterpart_b: ProgressedAstrodyneTerminal | None,
    natal_a: ProgressedNatalBodyValue,
    natal_b: ProgressedNatalBodyValue,
    aspect: str,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedMajorAspectRelation:
    """Evaluate one explicit major relation and assemble its lawful terminals."""

    active_policy = _policy(policy)
    kind_order = {
        ProgressedTerminalKind.RADICAL: 0,
        ProgressedTerminalKind.MAJOR_PROGRESSED: 1,
        ProgressedTerminalKind.MINOR_PROGRESSED: 2,
        ProgressedTerminalKind.TRANSIT: 3,
    }
    terminal_key = lambda item: (
        _CANONICAL_BODY_ORDER.index(item.body),
        kind_order[item.kind],
    )
    if terminal_key(direct_b) < terminal_key(direct_a):
        direct_a, direct_b = direct_b, direct_a
        counterpart_a, counterpart_b = counterpart_b, counterpart_a
        natal_a, natal_b = natal_b, natal_a
    if direct_a.body != natal_a.body or direct_b.body != natal_b.body:
        raise ValueError("natal body values must align with the direct terminals")
    if not (
        direct_a.kind is ProgressedTerminalKind.MAJOR_PROGRESSED
        or direct_b.kind is ProgressedTerminalKind.MAJOR_PROGRESSED
    ):
        raise ValueError("a major progressed relation requires a progressed terminal")
    if direct_a.kind not in {
        ProgressedTerminalKind.RADICAL,
        ProgressedTerminalKind.MAJOR_PROGRESSED,
    } or direct_b.kind not in {
        ProgressedTerminalKind.RADICAL,
        ProgressedTerminalKind.MAJOR_PROGRESSED,
    }:
        raise ValueError("major relation direct terminals must be radical/major-progressed")

    same_body = direct_a.body == direct_b.body
    if same_body:
        if direct_a.kind is direct_b.kind:
            raise ValueError("a same-body relation requires radical and progressed terminals")
        if counterpart_a is not None or counterpart_b is not None:
            raise ValueError("a same-body relation has only its two direct terminals")
        if natal_a != natal_b:
            raise ValueError("same-body relation natal values must agree")
        indirect: tuple[ProgressedAstrodyneTerminal, ...] = ()
    else:
        if counterpart_a is None or counterpart_b is None:
            raise ValueError("a two-body major relation requires both indirect counterparts")
        _counterpart(direct_a, counterpart_a)
        _counterpart(direct_b, counterpart_b)
        ids = {
            direct_a.terminal_id,
            direct_b.terminal_id,
            counterpart_a.terminal_id,
            counterpart_b.terminal_id,
        }
        if len(ids) != 4:
            raise ValueError("major relation terminals must be unique")
        indirect = (counterpart_a, counterpart_b)

    kind = _canonical_aspect(aspect)
    terminals = (direct_a, direct_b, *indirect)
    governing = max(
        terminals,
        key=lambda item: (
            {"cadent": 0, "succedent": 1, "angular": 2}[item.house_class],
            -_CANONICAL_BODY_ORDER.index(item.body),
            0 if item.kind is ProgressedTerminalKind.RADICAL else -1,
        ),
    )
    uses_luminary = governing.body in {"Sun", "Moon", "Mercury"}
    if governing.body in ASTRODYNE_POINTS:
        uses_luminary = direct_a.body in {"Sun", "Moon", "Mercury"} or (
            direct_b.body in {"Sun", "Moon", "Mercury"}
        )
    percentage = progressed_aspect_percentage(
        kind,
        governing.house_class,
        uses_luminary_column=uses_luminary,
        policy=active_policy,
    )
    moving_moon = any(
        item.kind is ProgressedTerminalKind.MAJOR_PROGRESSED and item.body == "Moon"
        for item in (direct_a, direct_b)
    )
    tier = (
        ProgressedAstrodyneTier.MAJOR_MOON
        if moving_moon
        else ProgressedAstrodyneTier.MAJOR
    )
    peak = progressed_aspect_peak_power(
        natal_a.power,
        natal_b.power,
        percentage.progressed_percentage,
        tier,
        policy=active_policy,
    )
    distance = (
        _parallel_distance_arcmin(direct_a, direct_b)
        if kind == "parallel"
        else _zodiacal_distance_arcmin(direct_a, direct_b, kind)
    )
    moment = progressed_aspect_at_distance(
        peak.peak_power,
        distance,
        manual_peak_power=peak.manual_peak_power,
        policy=active_policy,
    )
    return ProgressedMajorAspectRelation(
        aspect=kind,
        tier=tier,
        direct_terminals=(direct_a, direct_b),
        indirect_terminals=indirect,
        distance_arcmin=distance,
        percentage_truth=percentage,
        peak_truth=peak,
        peak_harmony_truth=progressed_aspect_harmony(
            direct_a.body,
            direct_b.body,
            kind,
            peak.peak_power,
        ),
        manual_peak_harmony_truth=progressed_aspect_harmony(
            direct_a.body,
            direct_b.body,
            kind,
            peak.manual_peak_power,
        ),
        moment_truth=moment,
        moment_harmony_truth=progressed_aspect_harmony(
            direct_a.body,
            direct_b.body,
            kind,
            moment.power,
        ),
        manual_moment_harmony_truth=progressed_aspect_harmony(
            direct_a.body,
            direct_b.body,
            kind,
            moment.manual_power,
        ),
    )


@dataclass(frozen=True, slots=True)
class ProgressedAccessoryAspectRelation:
    """Independent minor or transit aspect to a radical/major terminal."""

    tier: ProgressedAstrodyneTier
    aspect: str
    moving_terminal: ProgressedAstrodyneTerminal
    target_terminal: ProgressedAstrodyneTerminal
    indirect_target_terminal: ProgressedAstrodyneTerminal
    distance_arcmin: float
    percentage_truth: ProgressedAspectPercentageTruth
    peak_truth: ProgressedAspectPeakTruth
    manual_peak_harmony_truth: AstrodyneAspectHarmonyTruth
    moment_truth: ProgressedAspectMomentTruth
    manual_moment_harmony_truth: AstrodyneAspectHarmonyTruth

    @property
    def detected(self) -> bool:
        return True

    @property
    def admitted(self) -> bool:
        return self.moment_truth.within_orb

    @property
    def scored(self) -> bool:
        return self.admitted and self.moment_truth.power > 0.0

    @property
    def relation_id(self) -> str:
        return (
            f"{self.moving_terminal.terminal_id}|"
            f"{self.target_terminal.terminal_id}|{self.aspect}|{self.tier.value}"
        )


def evaluate_accessory_progressed_relation(
    moving_terminal: ProgressedAstrodyneTerminal,
    target_terminal: ProgressedAstrodyneTerminal,
    target_counterpart: ProgressedAstrodyneTerminal,
    natal_moving: ProgressedNatalBodyValue,
    natal_target: ProgressedNatalBodyValue,
    aspect: str,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedAccessoryAspectRelation:
    """Evaluate one independent minor or transit progressed aspect."""

    active_policy = _policy(policy)
    tier_by_kind = {
        ProgressedTerminalKind.MINOR_PROGRESSED: ProgressedAstrodyneTier.MINOR,
        ProgressedTerminalKind.TRANSIT: ProgressedAstrodyneTier.TRANSIT,
    }
    try:
        tier = tier_by_kind[moving_terminal.kind]
    except KeyError as exc:
        raise ValueError("moving terminal must be minor-progressed or transit") from exc
    if target_terminal.kind not in {
        ProgressedTerminalKind.RADICAL,
        ProgressedTerminalKind.MAJOR_PROGRESSED,
    }:
        raise ValueError("accessory target must be radical or major-progressed")
    _counterpart(target_terminal, target_counterpart)
    if moving_terminal.body != natal_moving.body:
        raise ValueError("moving natal value must align with the moving terminal")
    if target_terminal.body != natal_target.body:
        raise ValueError("target natal value must align with the target terminal")
    kind = _canonical_aspect(aspect)
    governing_candidates = [target_terminal, target_counterpart]
    if moving_terminal.body in ASTRODYNE_PLANETS:
        governing_candidates.append(moving_terminal)
    governing = max(
        governing_candidates,
        key=lambda item: {"cadent": 0, "succedent": 1, "angular": 2}[
            item.house_class
        ],
    )
    uses_luminary = governing.body in {"Sun", "Moon", "Mercury"}
    if governing.body in ASTRODYNE_POINTS:
        uses_luminary = moving_terminal.body in {"Sun", "Moon", "Mercury"} or (
            target_terminal.body in {"Sun", "Moon", "Mercury"}
        )
    percentage = progressed_aspect_percentage(
        kind,
        governing.house_class,
        uses_luminary_column=uses_luminary,
        policy=active_policy,
    )
    peak = progressed_aspect_peak_power(
        natal_moving.power,
        natal_target.power,
        percentage.progressed_percentage,
        tier,
        policy=active_policy,
    )
    distance = (
        _parallel_distance_arcmin(moving_terminal, target_terminal)
        if kind == "parallel"
        else _zodiacal_distance_arcmin(moving_terminal, target_terminal, kind)
    )
    moment = progressed_aspect_at_distance(
        peak.peak_power,
        distance,
        manual_peak_power=peak.manual_peak_power,
        policy=active_policy,
    )
    return ProgressedAccessoryAspectRelation(
        tier=tier,
        aspect=kind,
        moving_terminal=moving_terminal,
        target_terminal=target_terminal,
        indirect_target_terminal=target_counterpart,
        distance_arcmin=distance,
        percentage_truth=percentage,
        peak_truth=peak,
        manual_peak_harmony_truth=progressed_aspect_harmony(
            moving_terminal.body,
            target_terminal.body,
            kind,
            peak.manual_peak_power,
        ),
        moment_truth=moment,
        manual_moment_harmony_truth=progressed_aspect_harmony(
            moving_terminal.body,
            target_terminal.body,
            kind,
            moment.manual_power,
        ),
    )


@dataclass(frozen=True, slots=True)
class ProgressedReenforcementTruth:
    """Power-only reenforcement of one major relation by a minor relation."""

    major_relation_id: str
    minor_relation_id: str
    target_terminal_id: str
    target_is_direct: bool
    terminal_factor: float
    progressed_percentage: float
    peak_power: float
    manual_peak_power: float
    moment_truth: ProgressedAspectMomentTruth
    unreenforced_power: float
    reenforced_power: float
    manual_unreenforced_power: float
    manual_reenforced_power: float
    harmony_unchanged: float
    discord_unchanged: float


@dataclass(frozen=True, slots=True)
class ProgressedRelativeTerminalTruth:
    """Normal plus dated accessory harmony/discord for one major terminal."""

    terminal: ProgressedAstrodyneTerminal
    direct: bool
    terminal_factor: float
    normal_harmony: float
    normal_discord: float
    added_harmony: float
    added_discord: float
    total_harmony: float
    total_discord: float

    @property
    def net_harmony(self) -> float:
        return self.total_harmony - self.total_discord

    @property
    def manual_net_harmony(self) -> float:
        return _manual_round(self.net_harmony)


def reenforce_major_progressed_relation(
    major: ProgressedMajorAspectRelation,
    minor: ProgressedAccessoryAspectRelation,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedReenforcementTruth:
    """Apply one minor aspect's dated power-only reenforcement to a major aspect."""

    active_policy = _policy(policy)
    if minor.tier is not ProgressedAstrodyneTier.MINOR:
        raise ValueError("only a minor progressed aspect can reenforce a major aspect")
    target_id = minor.target_terminal.terminal_id
    direct_by_id = {item.terminal_id: item for item in major.direct_terminals}
    indirect_by_id = {item.terminal_id: item for item in major.indirect_terminals}
    if target_id in direct_by_id:
        if minor.target_terminal != direct_by_id[target_id]:
            raise ValueError("minor target geometry disagrees with the major terminal")
        direct = True
        terminal_factor = 1.0
    elif target_id in indirect_by_id:
        if minor.target_terminal != indirect_by_id[target_id]:
            raise ValueError("minor target geometry disagrees with the major terminal")
        direct = False
        terminal_factor = 0.5
    else:
        raise ValueError("minor target is not a terminal of the major relation")

    percentage = minor.percentage_truth.progressed_percentage
    exact_peak = major.moment_truth.power * percentage * terminal_factor
    manual_peak = _manual_round(
        major.moment_truth.manual_power * percentage * terminal_factor
    )
    moment = progressed_aspect_at_distance(
        exact_peak,
        minor.distance_arcmin,
        manual_peak_power=manual_peak,
        policy=active_policy,
    )
    return ProgressedReenforcementTruth(
        major_relation_id=major.relation_id,
        minor_relation_id=minor.relation_id,
        target_terminal_id=target_id,
        target_is_direct=direct,
        terminal_factor=terminal_factor,
        progressed_percentage=percentage,
        peak_power=exact_peak,
        manual_peak_power=manual_peak,
        moment_truth=moment,
        unreenforced_power=major.moment_truth.power,
        reenforced_power=major.moment_truth.power + moment.power,
        manual_unreenforced_power=major.moment_truth.manual_power,
        manual_reenforced_power=_manual_round(
            major.moment_truth.manual_power + moment.manual_power
        ),
        harmony_unchanged=major.manual_moment_harmony_truth.total_harmony,
        discord_unchanged=major.manual_moment_harmony_truth.total_discord,
    )


def relative_major_terminal_truth(
    relation: ProgressedMajorAspectRelation,
    normal: ProgressedNormalHoroscope,
) -> tuple[ProgressedRelativeTerminalTruth, ...]:
    """Combine normal and dated aspect harmony/discord for every major terminal."""

    profile_by_body = {profile.body: profile for profile in normal.profiles}
    direct_ids = {terminal.terminal_id for terminal in relation.direct_terminals}
    aspect_harmony = relation.manual_moment_harmony_truth.total_harmony
    aspect_discord = relation.manual_moment_harmony_truth.total_discord
    result = []
    for terminal in (*relation.direct_terminals, *relation.indirect_terminals):
        direct = terminal.terminal_id in direct_ids
        factor = 1.0 if direct else 0.5
        profile = profile_by_body[terminal.body]
        if terminal.kind is ProgressedTerminalKind.RADICAL:
            normal_harmony = profile.natal.harmony
            normal_discord = profile.natal.discord
        elif terminal.kind is ProgressedTerminalKind.MAJOR_PROGRESSED:
            normal_harmony = profile.carry.manual_total_harmony
            normal_discord = profile.carry.manual_total_discord
        else:  # pragma: no cover - major relation construction excludes this
            raise ValueError("relative major terminals must be radical/major-progressed")
        added_harmony = _manual_round(aspect_harmony * factor)
        added_discord = _manual_round(aspect_discord * factor)
        result.append(
            ProgressedRelativeTerminalTruth(
                terminal=terminal,
                direct=direct,
                terminal_factor=factor,
                normal_harmony=normal_harmony,
                normal_discord=normal_discord,
                added_harmony=added_harmony,
                added_discord=added_discord,
                total_harmony=_manual_round(normal_harmony + added_harmony),
                total_discord=_manual_round(normal_discord + added_discord),
            )
        )
    return tuple(
        sorted(
            result,
            key=lambda item: (
                _CANONICAL_BODY_ORDER.index(item.terminal.body),
                0
                if item.terminal.kind is ProgressedTerminalKind.RADICAL
                else 1,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class ProgressedDatedAspectTruth:
    """One dated major aspect normalized for practical distribution."""

    relation_id: str
    body_a: str
    body_b: str
    aspect: str
    direct_terminal_ids: tuple[str, ...]
    indirect_terminal_ids: tuple[str, ...]
    peak_power: float
    distance_arcmin: float
    power: float
    harmony: float
    discord: float

    def __post_init__(self) -> None:
        if not self.relation_id.strip():
            raise ValueError("relation_id must be non-empty")
        body_a = _canonical_body(self.body_a)
        body_b = _canonical_body(self.body_b)
        aspect = _canonical_aspect(self.aspect)
        direct = tuple(self.direct_terminal_ids)
        indirect = tuple(self.indirect_terminal_ids)
        if not direct:
            raise ValueError("a dated aspect requires at least one direct terminal")
        terminal_ids = (*direct, *indirect)
        if len(terminal_ids) != len(set(terminal_ids)):
            raise ValueError("dated aspect terminal ids must be unique")
        lawful = {
            f"{body_a}:r",
            f"{body_a}:p",
            f"{body_b}:r",
            f"{body_b}:p",
        }
        if not set(terminal_ids) <= lawful:
            raise ValueError("dated aspect terminal ids disagree with its bodies")
        numeric = (
            self.peak_power,
            self.distance_arcmin,
            self.power,
            self.harmony,
            self.discord,
        )
        if any(not isfinite(value) or value < 0.0 for value in numeric):
            raise ValueError("dated aspect values must be finite and non-negative")
        if self.distance_arcmin > 60.0:
            raise ValueError("a practical dated aspect must be within one degree")
        if self.power - self.peak_power > 1e-12:
            raise ValueError("dated aspect power cannot exceed peak power")
        object.__setattr__(self, "body_a", body_a)
        object.__setattr__(self, "body_b", body_b)
        object.__setattr__(self, "aspect", aspect)
        object.__setattr__(self, "direct_terminal_ids", direct)
        object.__setattr__(self, "indirect_terminal_ids", indirect)

    @property
    def net_harmony(self) -> float:
        return self.harmony - self.discord


def progressed_dated_aspect(
    relation_id: str,
    body_a: str,
    body_b: str,
    aspect: str,
    direct_terminal_ids: Sequence[str],
    indirect_terminal_ids: Sequence[str],
    peak_power: float,
    distance_arcmin: float,
    *,
    policy: ProgressedAstrodynePolicy | None = None,
) -> ProgressedDatedAspectTruth:
    """Evaluate a printed or computed peak at one date using manual staging."""

    moment = progressed_aspect_at_distance(
        peak_power,
        distance_arcmin,
        manual_peak_power=peak_power,
        policy=policy,
    )
    harmony = progressed_aspect_harmony(
        body_a,
        body_b,
        aspect,
        moment.manual_power,
    )
    manual_net = _manual_round(harmony.total_harmony - harmony.total_discord)
    return ProgressedDatedAspectTruth(
        relation_id=relation_id,
        body_a=body_a,
        body_b=body_b,
        aspect=aspect,
        direct_terminal_ids=tuple(direct_terminal_ids),
        indirect_terminal_ids=tuple(indirect_terminal_ids),
        peak_power=_manual_round(peak_power),
        distance_arcmin=distance_arcmin,
        power=moment.manual_power,
        harmony=max(manual_net, 0.0),
        discord=max(-manual_net, 0.0),
    )


def dated_aspect_from_major_relation(
    relation: ProgressedMajorAspectRelation,
) -> ProgressedDatedAspectTruth:
    """Project an evaluated major relation into practical-distribution truth."""

    manual_net = _manual_round(
        relation.manual_moment_harmony_truth.total_harmony
        - relation.manual_moment_harmony_truth.total_discord
    )
    return ProgressedDatedAspectTruth(
        relation_id=relation.relation_id,
        body_a=relation.direct_terminals[0].body,
        body_b=relation.direct_terminals[1].body,
        aspect=relation.aspect,
        direct_terminal_ids=tuple(
            terminal.terminal_id for terminal in relation.direct_terminals
        ),
        indirect_terminal_ids=tuple(
            terminal.terminal_id for terminal in relation.indirect_terminals
        ),
        peak_power=relation.peak_truth.manual_peak_power,
        distance_arcmin=relation.distance_arcmin,
        power=relation.moment_truth.manual_power,
        harmony=max(manual_net, 0.0),
        discord=max(-manual_net, 0.0),
    )


@dataclass(frozen=True, slots=True)
class ProgressedMutualReceptionAllocation:
    """One in-orb mutual-reception bonus attached to a major relation."""

    allocation_id: str
    body: str
    direct_terminal_ids: tuple[str, ...]
    indirect_terminal_ids: tuple[str, ...]
    harmony: float = 2.5

    def __post_init__(self) -> None:
        if not self.allocation_id.strip():
            raise ValueError("allocation_id must be non-empty")
        body = _canonical_body(self.body)
        if body not in ASTRODYNE_PLANETS:
            raise ValueError("mutual reception allocations require a planet")
        direct = tuple(self.direct_terminal_ids)
        indirect = tuple(self.indirect_terminal_ids)
        terminal_ids = (*direct, *indirect)
        if not terminal_ids or len(terminal_ids) != len(set(terminal_ids)):
            raise ValueError("mutual reception terminal ids must be non-empty and unique")
        if any(item not in {f"{body}:r", f"{body}:p"} for item in terminal_ids):
            raise ValueError("mutual reception terminal ids disagree with body")
        harmony = _non_negative("harmony", self.harmony)
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "direct_terminal_ids", direct)
        object.__setattr__(self, "indirect_terminal_ids", indirect)
        object.__setattr__(self, "harmony", harmony)


@dataclass(frozen=True, slots=True)
class ProgressedTerminalLocation:
    """Sign and house occupied by one radical or major-progressed terminal."""

    terminal_id: str
    sign: str
    house: int

    def __post_init__(self) -> None:
        parts = self.terminal_id.split(":")
        if len(parts) != 2 or parts[1] not in {"r", "p"}:
            raise ValueError("terminal_id must end in :r or :p")
        body = _canonical_body(parts[0])
        if self.sign not in ASTRODYNE_SIGNS:
            raise ValueError(f"unsupported terminal sign: {self.sign!r}")
        if self.house not in range(1, 13):
            raise ValueError("terminal house must be in [1, 12]")
        object.__setattr__(self, "terminal_id", f"{body}:{parts[1]}")


@dataclass(frozen=True, slots=True)
class ProgressedPracticalContribution:
    """Auditable influence added to one practical sign or house."""

    source_id: str
    body: str
    channel: str
    factor: float
    power: float
    harmony: float
    discord: float

    @property
    def net_harmony(self) -> float:
        return self.harmony - self.discord


@dataclass(frozen=True, slots=True)
class ProgressedPracticalAggregate:
    """One dated sign or house with normal and accessory truth separated."""

    name: str
    normal_power: float
    normal_harmony: float
    normal_discord: float
    contributions: tuple[ProgressedPracticalContribution, ...]
    added_power: float
    added_harmony: float
    added_discord: float
    total_power: float
    total_harmony: float
    total_discord: float

    def __post_init__(self) -> None:
        expected_power = _manual_round(
            sum(item.power for item in self.contributions)
        )
        net_by_body: dict[str, float] = {}
        for item in self.contributions:
            net_by_body[item.body] = net_by_body.get(item.body, 0.0) + item.net_harmony
        expected_harmony = _manual_round(
            sum(max(value, 0.0) for value in net_by_body.values())
        )
        expected_discord = _manual_round(
            sum(max(-value, 0.0) for value in net_by_body.values())
        )
        if (self.added_power, self.added_harmony, self.added_discord) != (
            expected_power,
            expected_harmony,
            expected_discord,
        ):
            raise ValueError("practical contribution totals are inconsistent")
        if self.total_power != _manual_round(self.normal_power + self.added_power):
            raise ValueError("practical total power is inconsistent")
        if self.total_harmony != _manual_round(
            self.normal_harmony + self.added_harmony
        ):
            raise ValueError("practical total harmony is inconsistent")
        if self.total_discord != _manual_round(
            self.normal_discord + self.added_discord
        ):
            raise ValueError("practical total discord is inconsistent")

    @property
    def net_harmony(self) -> float:
        return _manual_round(self.total_harmony - self.total_discord)


@dataclass(frozen=True, slots=True)
class ProgressedPracticalHoroscope:
    """Complete dated practical sign and house distribution."""

    signs: tuple[ProgressedPracticalAggregate, ...]
    houses: tuple[ProgressedPracticalAggregate, ...]

    def __post_init__(self) -> None:
        if tuple(item.name for item in self.signs) != ASTRODYNE_SIGNS:
            raise ValueError("practical signs are not in zodiacal order")
        if tuple(item.name for item in self.houses) != tuple(
            str(number) for number in range(1, 13)
        ):
            raise ValueError("practical houses are not in numerical order")

    def sign(self, name: str) -> ProgressedPracticalAggregate:
        try:
            return self.signs[ASTRODYNE_SIGNS.index(name)]
        except ValueError as exc:
            raise KeyError(name) from exc

    def house(self, number: int) -> ProgressedPracticalAggregate:
        if number not in range(1, 13):
            raise KeyError(number)
        return self.houses[number - 1]


def _rulers(sign: str) -> tuple[str, ...]:
    return tuple(
        row.planet for row in ASTRODYNE_DIGNITY_ROWS if sign in row.home_signs
    )


def _practical_factor(
    body: str,
    direct_terminal_ids: Sequence[str],
    indirect_terminal_ids: Sequence[str],
    occupied_terminal_ids: frozenset[str],
    cusp_rulers: Sequence[str],
    intercepted_rulers: Sequence[str],
) -> tuple[float, str]:
    ruler_factor = 0.5 * cusp_rulers.count(body) + 0.25 * intercepted_rulers.count(
        body
    )
    direct_occupied = sum(
        item in occupied_terminal_ids for item in direct_terminal_ids
    )
    indirect_occupied = sum(
        item in occupied_terminal_ids for item in indirect_terminal_ids
    )
    occupied_factor = direct_occupied + 0.5 * indirect_occupied

    # The manual's Moon-to-own-radical-place example assigns 1.5 shares to
    # the occupied progressed body even though the relation has only its two
    # direct terminals. This is the two-terminal form of full direct plus
    # half corresponding-terminal influence.
    same_body_two_terminal = (
        len(direct_terminal_ids) == 2
        and not indirect_terminal_ids
        and {item.split(":", 1)[0] for item in direct_terminal_ids} == {body}
        and direct_occupied > 0
    )
    if same_body_two_terminal:
        occupied_factor = 1.5
    channels = []
    if ruler_factor:
        channels.append("ruler")
    if occupied_factor:
        channels.append("occupied_terminal")
    return ruler_factor + occupied_factor, "+".join(channels) or "none"


def practical_progressed_horoscope(
    normal: ProgressedNormalHoroscope,
    aspects: Sequence[ProgressedDatedAspectTruth],
    terminal_locations: Sequence[ProgressedTerminalLocation],
    house_cusp_signs: Mapping[int, str],
    intercepted_signs: Mapping[int, Sequence[str]] | None = None,
    mutual_receptions: Sequence[ProgressedMutualReceptionAllocation] = (),
) -> ProgressedPracticalHoroscope:
    """Distribute dated major influence into every practical sign and house."""

    aspects = tuple(aspects)
    if len({item.relation_id for item in aspects}) != len(aspects):
        raise ValueError("dated aspect relation ids must be unique")
    receptions = tuple(mutual_receptions)
    if len({item.allocation_id for item in receptions}) != len(receptions):
        raise ValueError("mutual reception allocation ids must be unique")
    locations: dict[str, ProgressedTerminalLocation] = {}
    for item in terminal_locations:
        if item.terminal_id in locations:
            raise ValueError(f"duplicate terminal location: {item.terminal_id}")
        locations[item.terminal_id] = item
    referenced = {
        terminal_id
        for aspect in aspects
        for terminal_id in (
            *aspect.direct_terminal_ids,
            *aspect.indirect_terminal_ids,
        )
    } | {
        terminal_id
        for reception in receptions
        for terminal_id in (
            *reception.direct_terminal_ids,
            *reception.indirect_terminal_ids,
        )
    }
    missing = sorted(referenced - set(locations))
    if missing:
        raise ValueError(f"missing practical terminal locations: {missing}")
    expected_houses = set(range(1, 13))
    if set(house_cusp_signs) != expected_houses:
        raise ValueError("house_cusp_signs must contain houses 1-12")
    if any(sign not in ASTRODYNE_SIGNS for sign in house_cusp_signs.values()):
        raise ValueError("house_cusp_signs contains an unsupported sign")
    interceptions = {
        house: tuple(signs)
        for house, signs in (intercepted_signs or {}).items()
    }
    if not set(interceptions) <= expected_houses or any(
        sign not in ASTRODYNE_SIGNS
        for signs in interceptions.values()
        for sign in signs
    ):
        raise ValueError("intercepted_signs contains an unsupported house or sign")

    def aggregate(
        name: str,
        normal_entry: ProgressedNormalAggregateEntry,
        occupied: frozenset[str],
        cusp_rulers: tuple[str, ...],
        intercepted_rulers: tuple[str, ...],
    ) -> ProgressedPracticalAggregate:
        normal_net = _manual_round(
            normal_entry.manual_total_harmony
            - normal_entry.manual_total_discord
        )
        normal_harmony = max(normal_net, 0.0)
        normal_discord = max(-normal_net, 0.0)
        contributions: list[ProgressedPracticalContribution] = []
        for aspect in aspects:
            for body in dict.fromkeys((aspect.body_a, aspect.body_b)):
                direct = tuple(
                    item
                    for item in aspect.direct_terminal_ids
                    if item.startswith(f"{body}:")
                )
                indirect = tuple(
                    item
                    for item in aspect.indirect_terminal_ids
                    if item.startswith(f"{body}:")
                )
                factor, channel = _practical_factor(
                    body,
                    direct,
                    indirect,
                    occupied,
                    cusp_rulers,
                    intercepted_rulers,
                )
                if not factor:
                    continue
                contributions.append(
                    ProgressedPracticalContribution(
                        source_id=aspect.relation_id,
                        body=body,
                        channel=channel,
                        factor=factor,
                        power=aspect.power * factor,
                        harmony=aspect.harmony * factor,
                        discord=aspect.discord * factor,
                    )
                )
        for reception in receptions:
            factor, channel = _practical_factor(
                reception.body,
                reception.direct_terminal_ids,
                reception.indirect_terminal_ids,
                occupied,
                cusp_rulers,
                intercepted_rulers,
            )
            if factor:
                contributions.append(
                    ProgressedPracticalContribution(
                        source_id=reception.allocation_id,
                        body=reception.body,
                        channel=f"mutual_reception+{channel}",
                        factor=factor,
                        power=0.0,
                        harmony=reception.harmony * factor,
                        discord=0.0,
                    )
                )
        contributions.sort(key=lambda item: (item.body, item.source_id, item.channel))
        added_power = _manual_round(sum(item.power for item in contributions))
        net_by_body: dict[str, float] = {}
        for item in contributions:
            net_by_body[item.body] = net_by_body.get(item.body, 0.0) + item.net_harmony
        added_harmony = _manual_round(
            sum(max(value, 0.0) for value in net_by_body.values())
        )
        added_discord = _manual_round(
            sum(max(-value, 0.0) for value in net_by_body.values())
        )
        return ProgressedPracticalAggregate(
            name=name,
            normal_power=normal_entry.manual_total_power,
            normal_harmony=normal_harmony,
            normal_discord=normal_discord,
            contributions=tuple(contributions),
            added_power=added_power,
            added_harmony=added_harmony,
            added_discord=added_discord,
            total_power=_manual_round(normal_entry.manual_total_power + added_power),
            total_harmony=_manual_round(
                normal_harmony + added_harmony
            ),
            total_discord=_manual_round(
                normal_discord + added_discord
            ),
        )

    signs = []
    for sign in ASTRODYNE_SIGNS:
        cusp_count = sum(value == sign for value in house_cusp_signs.values())
        intercepted_count = sum(
            sign in values for values in interceptions.values()
        )
        rulers = _rulers(sign)
        signs.append(
            aggregate(
                sign,
                normal.sign(sign),
                frozenset(
                    terminal_id
                    for terminal_id, location in locations.items()
                    if location.sign == sign
                ),
                tuple(ruler for ruler in rulers for _ in range(cusp_count)),
                tuple(ruler for ruler in rulers for _ in range(intercepted_count)),
            )
        )
    houses = []
    for house in range(1, 13):
        houses.append(
            aggregate(
                str(house),
                normal.house(house),
                frozenset(
                    terminal_id
                    for terminal_id, location in locations.items()
                    if location.house == house
                ),
                _rulers(house_cusp_signs[house]),
                tuple(
                    ruler
                    for sign in interceptions.get(house, ())
                    for ruler in _rulers(sign)
                ),
            )
        )
    return ProgressedPracticalHoroscope(signs=tuple(signs), houses=tuple(houses))


__all__ = [
    "DEFAULT_PROGRESSED_ASTRODYNE_POLICY",
    "PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES",
    "ProgressedAspectMomentTruth",
    "ProgressedAccessoryAspectRelation",
    "ProgressedAspectPeakTruth",
    "ProgressedAspectPercentageTruth",
    "ProgressedAstrodynePolicy",
    "ProgressedAstrodyneTier",
    "ProgressedAstrodyneTerminal",
    "ProgressedCarryTruth",
    "ProgressedCompoundDuration",
    "ProgressedCompoundInfluenceTruth",
    "ProgressedCompoundQuantity",
    "ProgressedInfluenceUnit",
    "ProgressedMutualReceptionTruth",
    "ProgressedBaselineValue",
    "ProgressedBodyPlacement",
    "ProgressedNatalBodyValue",
    "ProgressedNormalAggregateEntry",
    "ProgressedNormalBodyProfile",
    "ProgressedNormalHoroscope",
    "ProgressedMajorAspectRelation",
    "ProgressedReenforcementTruth",
    "ProgressedRelativeTerminalTruth",
    "ProgressedDatedAspectTruth",
    "ProgressedMutualReceptionAllocation",
    "ProgressedPracticalAggregate",
    "ProgressedPracticalContribution",
    "ProgressedPracticalHoroscope",
    "ProgressedTerminalLocation",
    "ProgressedTerminalKind",
    "ProgressedTotalInfluenceTruth",
    "progressed_aspect_at_distance",
    "progressed_aspect_harmony",
    "progressed_aspect_peak_power",
    "progressed_aspect_percentage",
    "progressed_carry",
    "progressed_mutual_reception_bonus",
    "progressed_total_influence",
    "progressed_compound_total_influence",
    "normal_progressed_horoscope",
    "evaluate_major_progressed_relation",
    "evaluate_accessory_progressed_relation",
    "reenforce_major_progressed_relation",
    "relative_major_terminal_truth",
    "dated_aspect_from_major_relation",
    "practical_progressed_horoscope",
    "progressed_dated_aspect",
]
