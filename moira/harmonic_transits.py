"""Sampled mixed-origin harmonic transit configurations.

This module implements one deliberately bounded, VA-informed computational
object: complete three-member configurations made from either one transiting
and two natal bodies, or two transiting and one natal body.  It consumes
caller-supplied longitudes and timestamped transit samples.  It does not build
charts, open an ephemeris, interpolate contacts, or claim numerical parity
with Sirius.

The public result calls its intervals *observed windows*: their boundaries are
the first and last supplied samples at which the complete triple is admitted.
They are not inferred ingress or egress instants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
import math
from numbers import Real
from types import MappingProxyType
from typing import Mapping, Sequence

from .harmonics import HarmonicOrbPolicy

__all__ = [
    "HarmonicTransitMemberOrigin",
    "MixedOriginHarmonicTransitMode",
    "HarmonicTransitSample",
    "HarmonicTransitMember",
    "HarmonicTransitPatternSample",
    "HarmonicTransitWindow",
    "HarmonicTransitForecast",
    "MixedOriginHarmonicTransitForecastPolicy",
    "mixed_origin_harmonic_transit_forecast",
]


_SIRIUS_VA_FORECAST_SOURCE = (
    "https://www.astrosoftware.com/cpnew/m/software/sirius/"
    "methods_vibrational_astrology.html"
)
_UAC_2018_VA_HANDOUT_SOURCE = (
    "https://hosted-files.sched.co/uac2018/f2/"
    "handout%20for%20Forecasting%20with%20Vibrational%20Astrology.pdf"
)
_VA_INFORMED_SOURCE_LOCATORS = (
    _SIRIUS_VA_FORECAST_SOURCE,
    _UAC_2018_VA_HANDOUT_SOURCE,
)
_PROJECTED_ARC_ABS_TOL_DEG = 1e-12


class HarmonicTransitMemberOrigin(str, Enum):
    """Identity domain for one member of a mixed-origin configuration."""

    NATAL = "natal"
    TRANSIT = "transit"


class MixedOriginHarmonicTransitMode(str, Enum):
    """The two admitted natal/transit cardinalities."""

    ONE_TRANSIT_TWO_NATAL = "one_transit_two_natal"
    TWO_TRANSITS_ONE_NATAL = "two_transits_one_natal"


_DEFAULT_MODES = (
    MixedOriginHarmonicTransitMode.ONE_TRANSIT_TWO_NATAL,
    MixedOriginHarmonicTransitMode.TWO_TRANSITS_ONE_NATAL,
)


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number")
    return parsed


def _normalized_longitude(value: object, *, context: str) -> float:
    return _finite_number(context, value) % 360.0


def _normalized_longitude_mapping(
    values: Mapping[str, float],
    *,
    context: str,
) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise ValueError(f"{context} must be a mapping of body names to longitudes")
    if not values:
        raise ValueError(f"{context} must contain at least one body")

    normalized: dict[str, float] = {}
    for raw_name, raw_longitude in values.items():
        if not isinstance(raw_name, str):
            raise ValueError(f"{context} body names must be strings")
        name = raw_name.strip()
        if not name:
            raise ValueError(f"{context} body names must be non-empty")
        if name in normalized:
            raise ValueError(
                f"{context} body names must be unique after trimming"
            )
        normalized[name] = _normalized_longitude(
            raw_longitude,
            context=f"{context} longitude for {name!r}",
        )

    return MappingProxyType(dict(sorted(normalized.items())))


def _positive_integer(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _minimum_circular_covering_arc(longitudes: Sequence[float]) -> float:
    """Return the shortest arc containing every normalized longitude."""

    if not longitudes:
        raise ValueError("at least one longitude is required")
    ordered = sorted(longitudes)
    gaps = [
        ordered[index + 1] - ordered[index]
        for index in range(len(ordered) - 1)
    ]
    gaps.append(ordered[0] + 360.0 - ordered[-1])
    spread = 360.0 - max(gaps)
    # Suppress harmless binary noise at the coincident limit.
    return 0.0 if abs(spread) <= 1e-14 else spread


def _member_sort_key(
    member: "HarmonicTransitMember",
) -> tuple[int, str]:
    origin_rank = 0 if member.origin is HarmonicTransitMemberOrigin.NATAL else 1
    return origin_rank, member.body


def _pattern_identity(
    sample: "HarmonicTransitPatternSample",
) -> tuple[
    int,
    MixedOriginHarmonicTransitMode,
    tuple[tuple[HarmonicTransitMemberOrigin, str], ...],
]:
    return (
        sample.harmonic,
        sample.mode,
        tuple((member.origin, member.body) for member in sample.members),
    )


@dataclass(frozen=True, slots=True)
class HarmonicTransitSample:
    """One caller-owned transit-longitude sample at a finite UT Julian Day."""

    jd_ut: float
    longitudes: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "jd_ut", _finite_number("jd_ut", self.jd_ut))
        object.__setattr__(
            self,
            "longitudes",
            _normalized_longitude_mapping(
                self.longitudes,
                context="transit longitudes",
            ),
        )


@dataclass(frozen=True, slots=True)
class HarmonicTransitMember:
    """One natal or transiting body in a projected harmonic configuration."""

    body: str
    origin: HarmonicTransitMemberOrigin
    source_longitude_deg: float
    projected_longitude_deg: float

    def __post_init__(self) -> None:
        if not isinstance(self.body, str) or not self.body or self.body != self.body.strip():
            raise ValueError("body must be a non-empty trimmed string")
        if not isinstance(self.origin, HarmonicTransitMemberOrigin):
            raise ValueError("origin must be a HarmonicTransitMemberOrigin")
        source = _normalized_longitude(
            self.source_longitude_deg,
            context="source_longitude_deg",
        )
        projected = _normalized_longitude(
            self.projected_longitude_deg,
            context="projected_longitude_deg",
        )
        object.__setattr__(self, "source_longitude_deg", source)
        object.__setattr__(self, "projected_longitude_deg", projected)


@dataclass(frozen=True, slots=True)
class HarmonicTransitPatternSample:
    """One complete mixed-origin triple admitted at one supplied sample."""

    sample_index: int
    jd_ut: float
    harmonic: int
    mode: MixedOriginHarmonicTransitMode
    members: tuple[HarmonicTransitMember, ...]
    projected_spread_deg: float
    source_residual_spread_deg: float
    projected_orb_limit_deg: float
    source_orb_limit_deg: float

    def __post_init__(self) -> None:
        if type(self.sample_index) is not int or self.sample_index < 0:
            raise ValueError("sample_index must be a non-negative integer")
        object.__setattr__(self, "jd_ut", _finite_number("jd_ut", self.jd_ut))
        harmonic = _positive_integer("harmonic", self.harmonic)
        if not isinstance(self.mode, MixedOriginHarmonicTransitMode):
            raise ValueError("mode must be a MixedOriginHarmonicTransitMode")

        members = tuple(self.members)
        if len(members) != 3 or not all(
            isinstance(member, HarmonicTransitMember) for member in members
        ):
            raise ValueError("members must contain exactly three HarmonicTransitMember values")
        members = tuple(sorted(members, key=_member_sort_key))
        identities = {(member.origin, member.body) for member in members}
        if len(identities) != 3:
            raise ValueError("member origin/body identities must be unique")
        natal_count = sum(
            member.origin is HarmonicTransitMemberOrigin.NATAL for member in members
        )
        transit_count = len(members) - natal_count
        expected = (
            (2, 1)
            if self.mode
            is MixedOriginHarmonicTransitMode.ONE_TRANSIT_TWO_NATAL
            else (1, 2)
        )
        if (natal_count, transit_count) != expected:
            raise ValueError("member origins do not match the declared mode")

        for member in members:
            expected_projected = (member.source_longitude_deg * harmonic) % 360.0
            if not math.isclose(
                member.projected_longitude_deg,
                expected_projected,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    "member projected longitude must equal source longitude "
                    "multiplied by the declared harmonic"
                )

        projected_spread = _finite_number(
            "projected_spread_deg", self.projected_spread_deg
        )
        source_spread = _finite_number(
            "source_residual_spread_deg", self.source_residual_spread_deg
        )
        projected_limit = _finite_number(
            "projected_orb_limit_deg", self.projected_orb_limit_deg
        )
        source_limit = _finite_number(
            "source_orb_limit_deg", self.source_orb_limit_deg
        )
        for name, value in (
            ("projected_spread_deg", projected_spread),
            ("source_residual_spread_deg", source_spread),
            ("projected_orb_limit_deg", projected_limit),
            ("source_orb_limit_deg", source_limit),
        ):
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative")
        if projected_spread > projected_limit and not math.isclose(
            projected_spread,
            projected_limit,
            rel_tol=0.0,
            abs_tol=_PROJECTED_ARC_ABS_TOL_DEG,
        ):
            raise ValueError("projected spread exceeds the admitted orb limit")
        expected_projected_spread = _minimum_circular_covering_arc(
            tuple(member.projected_longitude_deg for member in members)
        )
        if not math.isclose(
            projected_spread,
            expected_projected_spread,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "projected spread must be the complete minimum circular "
                "covering arc of all members"
            )
        if not math.isclose(
            source_spread,
            projected_spread / harmonic,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "source residual spread must equal projected spread / harmonic"
            )
        if not math.isclose(
            source_limit,
            projected_limit / harmonic,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "source orb limit must equal projected orb limit / harmonic"
            )

        object.__setattr__(self, "harmonic", harmonic)
        object.__setattr__(self, "members", members)
        object.__setattr__(self, "projected_spread_deg", projected_spread)
        object.__setattr__(self, "source_residual_spread_deg", source_spread)
        object.__setattr__(self, "projected_orb_limit_deg", projected_limit)
        object.__setattr__(self, "source_orb_limit_deg", source_limit)


@dataclass(frozen=True, slots=True)
class HarmonicTransitWindow:
    """A consecutive observed run of one admitted sampled configuration."""

    samples: tuple[HarmonicTransitPatternSample, ...]
    maximum_sample_gap_days: float
    harmonic: int = field(init=False)
    mode: MixedOriginHarmonicTransitMode = field(init=False)
    member_identities: tuple[
        tuple[HarmonicTransitMemberOrigin, str], ...
    ] = field(init=False)
    first_sampled_jd_ut: float = field(init=False)
    peak_sampled_jd_ut: float = field(init=False)
    last_sampled_jd_ut: float = field(init=False)
    observed_duration_days: float = field(init=False)
    sample_count: int = field(init=False)

    def __post_init__(self) -> None:
        samples = tuple(self.samples)
        if not samples or not all(
            isinstance(sample, HarmonicTransitPatternSample) for sample in samples
        ):
            raise ValueError("samples must contain at least one pattern sample")
        maximum_gap = _finite_number(
            "maximum_sample_gap_days", self.maximum_sample_gap_days
        )
        if maximum_gap <= 0.0:
            raise ValueError("maximum_sample_gap_days must be positive")

        identity = _pattern_identity(samples[0])
        for previous, current in zip(samples, samples[1:]):
            if _pattern_identity(current) != identity:
                raise ValueError("all window samples must describe the same pattern")
            if current.sample_index != previous.sample_index + 1:
                raise ValueError("window samples must use consecutive sample indices")
            gap = current.jd_ut - previous.jd_ut
            if gap <= 0.0 or gap > maximum_gap:
                raise ValueError(
                    "window sample timestamps must advance within the maximum gap"
                )

        peak = min(
            samples,
            key=lambda sample: (
                sample.projected_spread_deg,
                sample.jd_ut,
                sample.sample_index,
            ),
        )
        harmonic, mode, member_identities = identity
        first_jd = samples[0].jd_ut
        last_jd = samples[-1].jd_ut
        observed_duration = last_jd - first_jd
        if not math.isfinite(observed_duration):
            raise ValueError("observed window duration must be finite")

        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "maximum_sample_gap_days", maximum_gap)
        object.__setattr__(self, "harmonic", harmonic)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "member_identities", member_identities)
        object.__setattr__(self, "first_sampled_jd_ut", first_jd)
        object.__setattr__(self, "peak_sampled_jd_ut", peak.jd_ut)
        object.__setattr__(self, "last_sampled_jd_ut", last_jd)
        object.__setattr__(self, "observed_duration_days", observed_duration)
        object.__setattr__(self, "sample_count", len(samples))


@dataclass(frozen=True, slots=True)
class MixedOriginHarmonicTransitForecastPolicy:
    """Admission policy for a bounded sampled mixed-origin forecast."""

    harmonics: tuple[int, ...]
    modes: tuple[MixedOriginHarmonicTransitMode, ...] = _DEFAULT_MODES
    orb_policy: HarmonicOrbPolicy = field(default_factory=HarmonicOrbPolicy)
    minimum_observed_duration_days: float = 0.0
    maximum_sample_gap_days: float = 1.0

    def __post_init__(self) -> None:
        harmonics = tuple(self.harmonics)
        if not harmonics:
            raise ValueError("harmonics must contain at least one positive integer")
        for harmonic in harmonics:
            _positive_integer("each harmonic", harmonic)
        if len(set(harmonics)) != len(harmonics):
            raise ValueError("harmonics must be unique")

        modes = tuple(self.modes)
        if not modes:
            raise ValueError("modes must contain at least one mode")
        if not all(isinstance(mode, MixedOriginHarmonicTransitMode) for mode in modes):
            raise ValueError("modes must contain MixedOriginHarmonicTransitMode values")
        if len(set(modes)) != len(modes):
            raise ValueError("modes must be unique")
        if not isinstance(self.orb_policy, HarmonicOrbPolicy):
            raise ValueError("orb_policy must be a HarmonicOrbPolicy")

        minimum_duration = _finite_number(
            "minimum_observed_duration_days",
            self.minimum_observed_duration_days,
        )
        maximum_gap = _finite_number(
            "maximum_sample_gap_days", self.maximum_sample_gap_days
        )
        if minimum_duration < 0.0:
            raise ValueError("minimum_observed_duration_days must be non-negative")
        if maximum_gap <= 0.0:
            raise ValueError("maximum_sample_gap_days must be positive")

        object.__setattr__(self, "harmonics", tuple(sorted(harmonics)))
        object.__setattr__(
            self,
            "modes",
            tuple(sorted(modes, key=lambda mode: mode.value)),
        )
        object.__setattr__(self, "minimum_observed_duration_days", minimum_duration)
        object.__setattr__(self, "maximum_sample_gap_days", maximum_gap)


@dataclass(frozen=True, slots=True)
class HarmonicTransitForecast:
    """Immutable sampled forecast and its complete input provenance."""

    policy: MixedOriginHarmonicTransitForecastPolicy
    natal_longitudes: Mapping[str, float]
    transit_samples: tuple[HarmonicTransitSample, ...]
    windows: tuple[HarmonicTransitWindow, ...]
    natal_bodies: tuple[str, ...] = field(init=False)
    transit_bodies: tuple[str, ...] = field(init=False)
    transit_sample_count: int = field(init=False)
    window_count: int = field(init=False)
    source_locators: tuple[str, str] = field(
        init=False,
        default=_VA_INFORMED_SOURCE_LOCATORS,
    )
    input_provenance: str = field(
        init=False,
        default="caller_supplied_natal_longitudes_and_timestamped_transit_samples",
    )
    evaluation_scope: str = field(
        init=False,
        default="sampled_complete_mixed_origin_triples_without_interpolation",
    )
    claim_boundary: str = field(
        init=False,
        default="VA-informed; no Sirius parity and no exact ingress or egress claim",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.policy, MixedOriginHarmonicTransitForecastPolicy):
            raise ValueError("policy must be a MixedOriginHarmonicTransitForecastPolicy")
        natal_longitudes = _normalized_longitude_mapping(
            self.natal_longitudes,
            context="natal longitudes",
        )
        transit_samples = tuple(self.transit_samples)
        _validate_transit_sample_sequence(transit_samples)
        windows = tuple(self.windows)
        if not all(isinstance(window, HarmonicTransitWindow) for window in windows):
            raise ValueError("windows must contain HarmonicTransitWindow values")
        for window in windows:
            if window.harmonic not in self.policy.harmonics:
                raise ValueError("window harmonic is not admitted by policy")
            if window.mode not in self.policy.modes:
                raise ValueError("window mode is not admitted by policy")
            if not math.isclose(
                window.maximum_sample_gap_days,
                self.policy.maximum_sample_gap_days,
                rel_tol=0.0,
                abs_tol=0.0,
            ):
                raise ValueError("window maximum gap does not match forecast policy")
            if (
                window.observed_duration_days
                < self.policy.minimum_observed_duration_days
            ):
                raise ValueError("window is shorter than the forecast duration policy")
            orb_truth = self.policy.orb_policy.resolve(window.harmonic)
            for pattern_sample in window.samples:
                if pattern_sample.sample_index >= len(transit_samples):
                    raise ValueError("window sample index is outside forecast inputs")
                input_sample = transit_samples[pattern_sample.sample_index]
                if pattern_sample.jd_ut != input_sample.jd_ut:
                    raise ValueError("window timestamp does not match forecast inputs")
                if not math.isclose(
                    pattern_sample.projected_orb_limit_deg,
                    orb_truth.projected_orb_limit_deg,
                    rel_tol=0.0,
                    abs_tol=0.0,
                ) or not math.isclose(
                    pattern_sample.source_orb_limit_deg,
                    orb_truth.source_orb_limit_deg,
                    rel_tol=0.0,
                    abs_tol=0.0,
                ):
                    raise ValueError("window orb limits do not match forecast policy")
                for member in pattern_sample.members:
                    if member.origin is HarmonicTransitMemberOrigin.NATAL:
                        source = natal_longitudes.get(member.body)
                    else:
                        source = input_sample.longitudes.get(member.body)
                    if source is None or not math.isclose(
                        member.source_longitude_deg,
                        source,
                        rel_tol=0.0,
                        abs_tol=0.0,
                    ):
                        raise ValueError(
                            "window member does not match its forecast input source"
                        )

        transit_bodies = tuple(transit_samples[0].longitudes)
        object.__setattr__(self, "natal_longitudes", natal_longitudes)
        object.__setattr__(self, "transit_samples", transit_samples)
        object.__setattr__(self, "windows", windows)
        object.__setattr__(self, "natal_bodies", tuple(natal_longitudes))
        object.__setattr__(self, "transit_bodies", transit_bodies)
        object.__setattr__(self, "transit_sample_count", len(transit_samples))
        object.__setattr__(self, "window_count", len(windows))


def _validate_transit_sample_sequence(
    samples: tuple[HarmonicTransitSample, ...],
) -> None:
    if not samples:
        raise ValueError("transit_samples must contain at least one sample")
    if not all(isinstance(sample, HarmonicTransitSample) for sample in samples):
        raise ValueError("transit_samples must contain HarmonicTransitSample values")

    body_identity = tuple(samples[0].longitudes)
    for index, sample in enumerate(samples):
        if tuple(sample.longitudes) != body_identity:
            raise ValueError("transit body identity must be consistent across samples")
        if index:
            previous_jd = samples[index - 1].jd_ut
            if sample.jd_ut <= previous_jd:
                raise ValueError("transit sample timestamps must be strictly increasing")
            if not math.isfinite(sample.jd_ut - previous_jd):
                raise ValueError("transit sample timestamp gaps must be finite")
    if not math.isfinite(samples[-1].jd_ut - samples[0].jd_ut):
        raise ValueError("transit sample timestamp span must be finite")


def _projected_members(
    natal_names: tuple[str, ...],
    transit_names: tuple[str, ...],
    natal_longitudes: Mapping[str, float],
    transit_longitudes: Mapping[str, float],
    harmonic: int,
) -> tuple[HarmonicTransitMember, ...]:
    members = [
        HarmonicTransitMember(
            body=name,
            origin=HarmonicTransitMemberOrigin.NATAL,
            source_longitude_deg=natal_longitudes[name],
            projected_longitude_deg=(natal_longitudes[name] * harmonic) % 360.0,
        )
        for name in natal_names
    ]
    members.extend(
        HarmonicTransitMember(
            body=name,
            origin=HarmonicTransitMemberOrigin.TRANSIT,
            source_longitude_deg=transit_longitudes[name],
            projected_longitude_deg=(transit_longitudes[name] * harmonic) % 360.0,
        )
        for name in transit_names
    )
    return tuple(sorted(members, key=_member_sort_key))


def _candidate_member_names(
    mode: MixedOriginHarmonicTransitMode,
    natal_names: tuple[str, ...],
    transit_names: tuple[str, ...],
) -> tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]:
    if mode is MixedOriginHarmonicTransitMode.ONE_TRANSIT_TWO_NATAL:
        return tuple(
            (natal_pair, (transit_name,))
            for natal_pair in combinations(natal_names, 2)
            for transit_name in transit_names
        )
    return tuple(
        ((natal_name,), transit_pair)
        for natal_name in natal_names
        for transit_pair in combinations(transit_names, 2)
    )


def _patterns_at_sample(
    *,
    sample_index: int,
    sample: HarmonicTransitSample,
    natal_longitudes: Mapping[str, float],
    policy: MixedOriginHarmonicTransitForecastPolicy,
) -> tuple[HarmonicTransitPatternSample, ...]:
    natal_names = tuple(natal_longitudes)
    transit_names = tuple(sample.longitudes)
    patterns: list[HarmonicTransitPatternSample] = []

    for harmonic in policy.harmonics:
        orb_truth = policy.orb_policy.resolve(harmonic)
        projected_limit = orb_truth.projected_orb_limit_deg
        source_limit = orb_truth.source_orb_limit_deg
        for mode in policy.modes:
            for selected_natal, selected_transit in _candidate_member_names(
                mode,
                natal_names,
                transit_names,
            ):
                members = _projected_members(
                    selected_natal,
                    selected_transit,
                    natal_longitudes,
                    sample.longitudes,
                    harmonic,
                )
                spread = _minimum_circular_covering_arc(
                    tuple(member.projected_longitude_deg for member in members)
                )
                if spread <= projected_limit or math.isclose(
                    spread,
                    projected_limit,
                    rel_tol=0.0,
                    abs_tol=_PROJECTED_ARC_ABS_TOL_DEG,
                ):
                    patterns.append(
                        HarmonicTransitPatternSample(
                            sample_index=sample_index,
                            jd_ut=sample.jd_ut,
                            harmonic=harmonic,
                            mode=mode,
                            members=members,
                            projected_spread_deg=spread,
                            source_residual_spread_deg=spread / harmonic,
                            projected_orb_limit_deg=projected_limit,
                            source_orb_limit_deg=source_limit,
                        )
                    )

    patterns.sort(
        key=lambda pattern: (
            pattern.harmonic,
            pattern.mode.value,
            tuple((member.origin.value, member.body) for member in pattern.members),
        )
    )
    return tuple(patterns)


def _observed_windows(
    patterns_by_index: tuple[tuple[HarmonicTransitPatternSample, ...], ...],
    policy: MixedOriginHarmonicTransitForecastPolicy,
) -> tuple[HarmonicTransitWindow, ...]:
    occurrences: dict[
        tuple[
            int,
            MixedOriginHarmonicTransitMode,
            tuple[tuple[HarmonicTransitMemberOrigin, str], ...],
        ],
        list[HarmonicTransitPatternSample],
    ] = {}
    for patterns in patterns_by_index:
        for pattern in patterns:
            occurrences.setdefault(_pattern_identity(pattern), []).append(pattern)

    windows: list[HarmonicTransitWindow] = []
    for identity in sorted(
        occurrences,
        key=lambda value: (
            value[0],
            value[1].value,
            tuple((origin.value, body) for origin, body in value[2]),
        ),
    ):
        group: list[HarmonicTransitPatternSample] = []
        for pattern in occurrences[identity]:
            if group:
                previous = group[-1]
                is_consecutive = pattern.sample_index == previous.sample_index + 1
                gap_is_lawful = (
                    pattern.jd_ut - previous.jd_ut
                    <= policy.maximum_sample_gap_days
                )
                if not is_consecutive or not gap_is_lawful:
                    window = HarmonicTransitWindow(
                        samples=tuple(group),
                        maximum_sample_gap_days=policy.maximum_sample_gap_days,
                    )
                    if (
                        window.observed_duration_days
                        >= policy.minimum_observed_duration_days
                    ):
                        windows.append(window)
                    group = []
            group.append(pattern)

        if group:
            window = HarmonicTransitWindow(
                samples=tuple(group),
                maximum_sample_gap_days=policy.maximum_sample_gap_days,
            )
            if (
                window.observed_duration_days
                >= policy.minimum_observed_duration_days
            ):
                windows.append(window)

    windows.sort(
        key=lambda window: (
            window.first_sampled_jd_ut,
            window.harmonic,
            window.mode.value,
            tuple(
                (origin.value, body) for origin, body in window.member_identities
            ),
        )
    )
    return tuple(windows)


def mixed_origin_harmonic_transit_forecast(
    natal_longitudes: Mapping[str, float],
    transit_samples: Sequence[HarmonicTransitSample],
    policy: MixedOriginHarmonicTransitForecastPolicy,
) -> HarmonicTransitForecast:
    """Find complete mixed-origin triples in caller-supplied transit samples.

    Admission uses the minimum circular covering arc of all three projected
    positions.  Pairwise connected components are intentionally insufficient:
    every member must belong to the same complete three-member arc.
    """

    if not isinstance(policy, MixedOriginHarmonicTransitForecastPolicy):
        raise ValueError("policy must be a MixedOriginHarmonicTransitForecastPolicy")
    normalized_natal = _normalized_longitude_mapping(
        natal_longitudes,
        context="natal longitudes",
    )
    samples = tuple(transit_samples)
    _validate_transit_sample_sequence(samples)

    patterns_by_index = tuple(
        _patterns_at_sample(
            sample_index=index,
            sample=sample,
            natal_longitudes=normalized_natal,
            policy=policy,
        )
        for index, sample in enumerate(samples)
    )
    windows = _observed_windows(patterns_by_index, policy)
    return HarmonicTransitForecast(
        policy=policy,
        natal_longitudes=normalized_natal,
        transit_samples=samples,
        windows=windows,
    )
