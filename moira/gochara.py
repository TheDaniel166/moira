"""
Moira — Gochara Phala
====================

Archetype: Engine

Purpose
-------
Evaluates seven classical planets in supplied sidereal transit snapshots,
counting whole signs from the natal Moon. Baseline indications, ordinary
Vedha, excluded blockers, and incomplete observations remain distinct.

Tradition and sources
---------------------
Mantreswara, Phaladeepika, V. Subrahmanya Sastri, second edition (1950):
26.1 reference; 26.2 favorable positions; 26.3–8 directed Vedha and
exceptions; 26.9–23 planet/sign indications; 26.41 Ashtakavarga context.
Printed pp. 286–295, 303 (PDF pp. 321–330, 338). The complete printed
26.6/8 sequences govern Mercury/Venus, including Venus 11→3 and 12→6.
Indications below are original concise paraphrases, not copied translations.

Boundary declaration
--------------------
Owns: the named Phaladeepika profile, sign-relative judgments, source
locators, immutable snapshots, obstruction witnesses and derived local,
aggregate and observed-network projections.
Delegates: raw own-BAV sign lookup to ``moira.ashtakavarga.transit_strength``.
Policy choices and source-admission metadata belong to ``moira.gochara_policy``.
Callers own astronomical positions and their epoch, ayanamsa and correction
regime. This module neither calculates nor certifies supplied ephemerides.

Ambiguity policy
----------------
The seven classical planets are the fixed subjects and blocker participants.
Nodes, counter-Vedha, strength overrides, sign-part activation, dated search,
remedies and composite scores are outside this profile. Longitudes must be
finite real numbers and are normalized modulo 360. Partial snapshots are
admitted: missing eligible blockers prevent an unobstructed verdict, while a
known non-exempt blocker still establishes obstruction. Missing exempt
planets do not prevent completion of that particular Vedha judgment.
Typed scope controls may require complete input, omit ordinary Vedha, or
omit/require raw BAV. Omission is recorded separately from incompleteness.
The doctrine catalogue distinguishes admitted choices, source attestation,
disputed editions and open research; catalogue records are not presets.

Public surface
--------------
The explicit 28-name __all__ curates source/policy metadata, snapshot and
relation vessels, derived local/aggregate/network profiles, and their
construction/inspection functions. Helpers and source tables remain private.

Import-time side effects: None
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from numbers import Real
from types import MappingProxyType

from .ashtakavarga import BhinnashtakavargaResult, transit_strength
from .gochara_policy import (
    GOCHARA_PROFILE, GOCHARA_PLANETS, DEFAULT_GOCHARA_POLICY,
    GocharaPolicy, GocharaVedhaMode, GocharaCompleteness, GocharaBavMode,
    GocharaSourceProfile, GocharaAdmissionStatus, GocharaDoctrineOption,
    gochara_doctrine_options,
)

__all__ = [
    "GOCHARA_PROFILE", "GOCHARA_PLANETS", "GocharaVedhaStatus",
    "GocharaPosition", "GocharaVedhaWitness", "GocharaPlanetResult",
    "GocharaResult", "gochara_from_positions",
    "DEFAULT_GOCHARA_POLICY", "GocharaSourceProfile", "GocharaVedhaMode",
    "GocharaCompleteness", "GocharaBavMode", "GocharaAdmissionStatus",
    "GocharaDoctrineOption", "GocharaPolicy", "gochara_doctrine_options",
    "GocharaBaselineClass", "GocharaBavAvailability", "GocharaVedhaRelationClass",
    "GocharaLocalCondition", "GocharaLocalProfile", "GocharaChartSummary",
    "GocharaNetworkNode", "GocharaVedhaNetwork", "GocharaSubsystemProfile",
    "gochara_local_profiles", "gochara_subsystem_profile",
]

_EDITION = "Phaladeepika; V. Subrahmanya Sastri; second edition, 1950"
_SOURCE_URL = (
    "https://www.wisdomlib.org/uploads/ocr/essays/phaladeepika/"
    "phaladeepika-2nd-ed-1950-by-v-subrahmanya-sastri-text.pdf"
)

# Each left-hand position is favorable under 26.2. Right-hand positions
# are the directed Vedha signs in 26.3–8; they are not an adverse-position set.
_VEDHA = MappingProxyType({
    "Sun": MappingProxyType({3: 9, 6: 12, 10: 4, 11: 5}),
    "Moon": MappingProxyType({1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8}),
    "Mars": MappingProxyType({3: 12, 6: 9, 11: 5}),
    "Mercury": MappingProxyType({2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12}),
    "Jupiter": MappingProxyType({2: 12, 5: 4, 7: 3, 9: 10, 11: 8}),
    "Venus": MappingProxyType({1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 3, 12: 6}),
    "Saturn": MappingProxyType({3: 12, 6: 9, 11: 5}),
})
_EXEMPT = MappingProxyType({"Sun": "Saturn", "Saturn": "Sun", "Moon": "Mercury", "Mercury": "Moon"})
_VEDHA_VERSE = MappingProxyType({
    "Sun": "26.3", "Moon": "26.4", "Mars": "26.5", "Saturn": "26.5",
    "Mercury": "26.6", "Jupiter": "26.7", "Venus": "26.8",
})

# Twelve entries per subject, in inclusive sign order from natal Moon.
# Each entry owns its indication and exact verse locator. These summarize
# the historical text; they are not unconditional event predictions.
_INDICATIONS = MappingProxyType({
    "Sun": (
        ("Fatigue, financial loss, irritability and taxing travel.", "26.9"),
        ("Financial loss, unhappiness and vulnerability to deception.", "26.9"),
        ("Improved standing, financial gains and relief from illness or opponents.", "26.9"),
        ("Illness and impediments to intimate enjoyment.", "26.9"),
        ("Mental distress, poor health and embarrassment.", "26.10"),
        ("Relief from illness, opponents and anxieties.", "26.10"),
        ("Taxing journeys, digestive complaints and humiliation.", "26.10"),
        ("Fear, illness, disputes and displeasure from authority.", "26.10"),
        ("Danger, humiliation, separation from kin and low spirits.", "26.11"),
        ("Completion of a significant undertaking.", "26.11"),
        ("Improved position, recognition, wealth and relief from illness.", "26.11"),
        ("Sorrow, financial loss, disputes with friends and fever.", "26.11"),
    ),
    "Moon": (
        ("An opening of favorable fortune.", "26.12"),
        ("Financial loss.", "26.12"),
        ("Success in undertakings.", "26.12"),
        ("Fear or apprehension.", "26.12"),
        ("Sorrow or distress.", "26.12"),
        ("Relief from illness.", "26.12"),
        ("Personal happiness.", "26.12"),
        ("Troublesome developments.", "26.12"),
        ("Illness or poor health.", "26.12"),
        ("Attainment of a desired aim.", "26.12"),
        ("Joy and satisfaction.", "26.12"),
        ("Expenses or outgoings.", "26.12"),
    ),
    "Mars": (
        ("Low spirits, separation from kin and blood or heat complaints.", "26.13"),
        ("Fear, heated exchanges and financial loss.", "26.13"),
        ("Success, acquisition of valuables and happiness.", "26.13"),
        ("Loss of standing, digestive trouble and distress involving kin.", "26.13"),
        ("Fever, troubling desires and distress involving children or relatives.", "26.14"),
        ("Resolution of conflict, relief from illness, gains and success.", "26.14"),
        ("Marital disagreement and eye or digestive complaints.", "26.15"),
        ("Fever, blood complaints and loss of wealth or honor.", "26.15"),
        ("Humiliation through losses, bodily weakness and difficulty walking.", "26.15"),
        ("Improper conduct, unsuccessful efforts and exhaustion.", "26.16"),
        ("Financial gains, relief from illness and acquisition of land.", "26.16"),
        ("Financial loss and illness associated with excessive heat.", "26.16"),
    ),
    "Mercury": (
        ("Financial loss.", "26.17"),
        ("Financial acquisition.", "26.17"),
        ("Apprehension concerning opponents.", "26.17"),
        ("An inflow of money.", "26.17"),
        ("Disputes involving spouse or children.", "26.17"),
        ("Success in undertakings.", "26.17"),
        ("Disagreements or misunderstandings.", "26.17"),
        ("Gains involving wealth or children.", "26.17"),
        ("Impediments to undertakings.", "26.17"),
        ("Happiness across affairs.", "26.17"),
        ("Increasing prosperity.", "26.17"),
        ("Apprehension of humiliation.", "26.17"),
    ),
    "Jupiter": (
        ("Departure from home, heavy expenses and ill will.", "26.18"),
        ("Financial gain, domestic happiness and influence in speech.", "26.18"),
        ("Loss of standing, separation from friends and obstacles or illness.", "26.18"),
        ("Distress involving kin, humiliation and danger from cattle.", "26.18"),
        ("Gains involving children, worthy company and favor from authority.", "26.19"),
        ("Trouble involving opponents or cousins, and illness.", "26.19"),
        ("Travel for an auspicious undertaking and happiness involving family.", "26.19"),
        ("Taxing journeys, misfortune, financial loss and distress.", "26.19"),
        ("Prosperity and its enjoyment.", "26.20"),
        ("Threats to property, position or children.", "26.20"),
        ("Gains involving children, position and recognition.", "26.20"),
        ("Grief or apprehension concerning property.", "26.20"),
    ),
    "Venus": (
        ("Enjoyment and personal pleasures.", "26.21"),
        ("Financial gain.", "26.21"),
        ("An increase in prosperity.", "26.21"),
        ("Happiness and an increase in friendships.", "26.21"),
        ("Gains involving children.", "26.21"),
        ("Mishaps or adversity.", "26.21"),
        ("Trouble involving the spouse.", "26.21"),
        ("Acquisition of wealth.", "26.21"),
        ("Personal contentment.", "26.21"),
        ("Disputes or quarrels.", "26.21"),
        ("Safety and security.", "26.21"),
        ("Acquisition of money.", "26.21"),
    ),
    "Saturn": (
        ("Illness and involvement in funeral observances.", "26.22"),
        ("Difficulties involving wealth or children.", "26.22"),
        ("Improved position, financial gains and assistance.", "26.22"),
        ("Losses involving spouse, relations or wealth.", "26.22"),
        ("Declining wealth, losses involving children and mental confusion.", "26.22"),
        ("Happiness across affairs.", "26.22"),
        ("Trouble involving the spouse, travel and apprehension.", "26.22"),
        ("Losses involving family, livestock, friends or wealth, and illness.", "26.22"),
        ("Financial loss, obstacles to good deeds and grief involving an elder.", "26.23"),
        ("Improper actions, loss of honor and illness.", "26.23"),
        ("Happiness, financial gains and notable recognition.", "26.23"),
        ("Unprofitable work, losses through opponents and family illness.", "26.23"),
    ),
})


def _longitude(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be a real longitude in degrees")
    try:
        longitude = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be finite") from exc
    if not math.isfinite(longitude):
        raise ValueError(f"{label} must be finite")
    normalized = longitude % 360.0
    # IEEE remainder can round a tiny negative angle up to exactly 360.
    # Retain its final-sign ownership with the nearest value below 360.
    return math.nextafter(360.0, 0.0) if normalized == 360.0 else normalized


def _planet(planet: str) -> None:
    if not isinstance(planet, str) or planet not in GOCHARA_PLANETS:
        raise ValueError(f"planet must be one of {GOCHARA_PLANETS}, got {planet!r}")


def _reference_sign(sign: int) -> None:
    if isinstance(sign, bool) or not isinstance(sign, int) or not 0 <= sign < 12:
        raise ValueError("janma_rashi_index must be an integer in [0, 11]")


class GocharaVedhaStatus(str, Enum):
    """Ordinary Vedha state; incomplete is never an unobstructed verdict."""

    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"
    UNOBSTRUCTED = "unobstructed"
    INCOMPLETE = "incomplete"
    OMITTED = "omitted_by_policy"


class GocharaBaselineClass(str, Enum):
    """Favorable membership; unlisted positions retain their individual indications."""

    FAVORABLE = "favorable"
    OUTSIDE_FAVORABLE_SET = "outside_favorable_set"


class GocharaBavAvailability(str, Enum):
    """Raw testimony availability, independent of strength interpretation."""

    SUPPLIED = "raw_supplied"
    NOT_SUPPLIED = "not_supplied"
    OMITTED = "omitted_by_policy"


class GocharaVedhaRelationClass(str, Enum):
    """Detected occupancy classified by the named subject's exemption rule."""

    OBSTRUCTION = "non_exempt_obstruction"
    EXEMPT_OCCUPANCY = "exempt_occupancy"


@dataclass(frozen=True, slots=True)
class GocharaPosition:
    """One caller-supplied sidereal position, normalized with derived sign."""

    planet: str
    sidereal_longitude: float
    rashi_index: int = field(init=False)
    degrees_in_sign: float = field(init=False)

    def __post_init__(self) -> None:
        _planet(self.planet)
        lon = _longitude(self.sidereal_longitude, f"{self.planet} longitude")
        object.__setattr__(self, "sidereal_longitude", lon)
        object.__setattr__(self, "rashi_index", int(lon // 30.0))
        object.__setattr__(self, "degrees_in_sign", lon % 30.0)


def _ordered_positions(positions: tuple[GocharaPosition, ...]) -> tuple[GocharaPosition, ...]:
    by_planet = {}
    for position in positions:
        if not isinstance(position, GocharaPosition):
            raise TypeError("positions must contain GocharaPosition values")
        if position.planet in by_planet:
            raise ValueError(f"duplicate position for {position.planet}")
        by_planet[position.planet] = position
    if not by_planet:
        raise ValueError("at least one transit position is required")
    return tuple(by_planet[p] for p in GOCHARA_PLANETS if p in by_planet)


def _copy_bhinna(bhinna: BhinnashtakavargaResult) -> BhinnashtakavargaResult:
    if not isinstance(bhinna, BhinnashtakavargaResult):
        raise TypeError("bhinna values must be BhinnashtakavargaResult vessels")
    counts = tuple(bhinna.rekhas)
    if any(isinstance(n, bool) or not isinstance(n, int) for n in counts):
        raise ValueError("BAV rekhas must be integers in [0, 8]")
    if isinstance(bhinna.total_rekhas, bool) or not isinstance(bhinna.total_rekhas, int):
        raise ValueError("BAV total_rekhas must be an integer")
    # Detach even from an existing vessel initialized with a mutable list.
    return BhinnashtakavargaResult(bhinna.planet, counts, bhinna.total_rekhas)


def _validate_snapshot_policy(positions: tuple[GocharaPosition, ...], policy: GocharaPolicy) -> None:
    if not isinstance(policy, GocharaPolicy):
        raise TypeError("policy must be a GocharaPolicy")
    missing = tuple(p for p in policy.subjects if p not in {item.planet for item in positions})
    if policy.completeness is GocharaCompleteness.REQUIRE_COMPLETE and missing:
        raise ValueError(f"complete snapshot required; missing transit positions: {missing}")


@dataclass(frozen=True, slots=True)
class GocharaVedhaWitness:
    """One occupied directed Vedha pair with its subject-specific exemption."""

    subject: GocharaPosition
    blocker: GocharaPosition
    janma_rashi_index: int
    subject_house: int = field(init=False)
    blocker_house: int = field(init=False)
    exempt: bool = field(init=False)
    source: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.subject, GocharaPosition) or not isinstance(self.blocker, GocharaPosition):
            raise TypeError("subject and blocker must be GocharaPosition vessels")
        _reference_sign(self.janma_rashi_index)
        house = (self.subject.rashi_index - self.janma_rashi_index) % 12 + 1
        blocker_house = (self.blocker.rashi_index - self.janma_rashi_index) % 12 + 1
        if self.subject.planet == self.blocker.planet or _VEDHA[self.subject.planet].get(house) != blocker_house:
            raise ValueError("witness positions must occupy a directed Vedha pair")
        object.__setattr__(self, "subject_house", house)
        object.__setattr__(self, "blocker_house", blocker_house)
        object.__setattr__(self, "exempt", _EXEMPT.get(self.subject.planet) == self.blocker.planet)
        object.__setattr__(self, "source", f"Phaladeepika {_VEDHA_VERSE[self.subject.planet]}")

    @property
    def relation_class(self) -> GocharaVedhaRelationClass:
        """Classify an observed relation without losing an exempt occupant."""
        return GocharaVedhaRelationClass.EXEMPT_OCCUPANCY if self.exempt else GocharaVedhaRelationClass.OBSTRUCTION

    @property
    def directed_pair(self) -> tuple[int, int]:
        """The subject's favorable position and its directed blocking position."""
        return self.subject_house, self.blocker_house


@dataclass(frozen=True, slots=True)
class GocharaPlanetResult:
    """
    One source-bound judgment retaining baseline, Vedha and raw BAV context.

    Computed fields cannot be supplied independently of their snapshot.
    ``indication`` is the baseline historical indication even when blocked;
    ``missing_blockers`` concerns only eligible absent Vedha participants.
    Raw BAV does not override either the baseline or the Vedha state.
    """

    position: GocharaPosition
    janma_rashi_index: int
    transit_positions: tuple[GocharaPosition, ...]
    bhinna: BhinnashtakavargaResult | None = None
    policy: GocharaPolicy = DEFAULT_GOCHARA_POLICY
    house_from_moon: int = field(init=False)
    baseline_favorable: bool = field(init=False)
    baseline_source: str = field(init=False, default="Phaladeepika 26.2")
    indication: str = field(init=False)
    indication_source: str = field(init=False)
    vedha_house: int | None = field(init=False)
    vedha_source: str = field(init=False)
    vedha_witnesses: tuple[GocharaVedhaWitness, ...] = field(init=False)
    missing_blockers: tuple[str, ...] = field(init=False)
    vedha_status: GocharaVedhaStatus = field(init=False)
    ashtakavarga_rekhas: int | None = field(init=False)
    ashtakavarga_source: str | None = field(init=False)
    evaluated_layers: tuple[str, ...] = field(init=False)
    baseline_class: GocharaBaselineClass = field(init=False)
    ashtakavarga_availability: GocharaBavAvailability = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.position, GocharaPosition):
            raise TypeError("position must be a GocharaPosition")
        _reference_sign(self.janma_rashi_index)
        positions = _ordered_positions(self.transit_positions)
        _validate_snapshot_policy(positions, self.policy)
        if self.position not in positions:
            raise ValueError("subject position must match the transit snapshot")
        planet = self.position.planet
        house = (self.position.rashi_index - self.janma_rashi_index) % 12 + 1
        vedha_house = _VEDHA[planet].get(house)
        indication, verse = _INDICATIONS[planet][house - 1]
        witnesses = ()
        missing = ()
        status = GocharaVedhaStatus.NOT_APPLICABLE
        if vedha_house is not None and self.policy.vedha_mode is GocharaVedhaMode.BASELINE_ONLY:
            status = GocharaVedhaStatus.OMITTED
        elif vedha_house is not None:
            witnesses = tuple(
                GocharaVedhaWitness(self.position, p, self.janma_rashi_index)
                for p in positions
                if p.planet != planet and (p.rashi_index - self.janma_rashi_index) % 12 + 1 == vedha_house
            )
            present = {p.planet for p in positions}
            missing = tuple(
                p for p in GOCHARA_PLANETS
                if p != planet and p != _EXEMPT.get(planet) and p not in present
            )
            if any(not witness.exempt for witness in witnesses):
                status = GocharaVedhaStatus.BLOCKED
            elif missing:
                status = GocharaVedhaStatus.INCOMPLETE
            else:
                status = GocharaVedhaStatus.UNOBSTRUCTED
        bhinna = self.bhinna
        count = None
        if self.policy.bav_mode is GocharaBavMode.OMIT and bhinna is not None:
            raise ValueError("bhinna was supplied but raw BAV is omitted by policy")
        if self.policy.bav_mode is GocharaBavMode.REQUIRE_ALL_RAW and bhinna is None:
            raise ValueError(f"raw BAV required for {planet}")
        if bhinna is not None:
            bhinna = _copy_bhinna(bhinna)
            count = transit_strength(planet, self.position.rashi_index, bhinna)
        for name, value in (
            ("transit_positions", positions), ("bhinna", bhinna),
            ("house_from_moon", house), ("baseline_favorable", vedha_house is not None),
            ("indication", indication), ("indication_source", f"Phaladeepika {verse}"),
            ("vedha_house", vedha_house), ("vedha_source", f"Phaladeepika {_VEDHA_VERSE[planet]}"),
            ("vedha_witnesses", witnesses), ("missing_blockers", missing),
            ("vedha_status", status), ("ashtakavarga_rekhas", count),
            ("ashtakavarga_source", "Phaladeepika 26.41; own unreduced BAV, raw count" if count is not None else None),
            ("evaluated_layers", ("moon_relative_baseline",)
             + (("ordinary_vedha",) if self.policy.vedha_mode is GocharaVedhaMode.ORDINARY else ())
             + ("historical_indications",)
             + (("raw_own_bav",) if count is not None else ())),
            ("baseline_class", GocharaBaselineClass.FAVORABLE if vedha_house is not None
             else GocharaBaselineClass.OUTSIDE_FAVORABLE_SET),
            ("ashtakavarga_availability", GocharaBavAvailability.SUPPLIED if count is not None
             else GocharaBavAvailability.OMITTED if self.policy.bav_mode is GocharaBavMode.OMIT
             else GocharaBavAvailability.NOT_SUPPLIED),
        ):
            object.__setattr__(self, name, value)

    @property
    def active_vedha_witnesses(self) -> tuple[GocharaVedhaWitness, ...]:
        """Observed non-exempt occupants, retaining the original typed witnesses."""
        return tuple(w for w in self.vedha_witnesses if not w.exempt)

    @property
    def exempt_vedha_witnesses(self) -> tuple[GocharaVedhaWitness, ...]:
        """Observed occupants excluded by the selected source's directed exception."""
        return tuple(w for w in self.vedha_witnesses if w.exempt)

    @property
    def eligible_blockers(self) -> tuple[str, ...]:
        """Potential classical blockers, independent of observed occupancy or omissions."""
        return tuple(p for p in self.policy.blockers if p != self.position.planet
                     and p != _EXEMPT.get(self.position.planet))

    @property
    def vedha_observation_complete(self) -> bool | None:
        """Whether eligible positions are complete; omitted/inapplicable layers return None."""
        if self.vedha_status in (GocharaVedhaStatus.NOT_APPLICABLE, GocharaVedhaStatus.OMITTED):
            return None
        return not self.missing_blockers


@dataclass(frozen=True, slots=True)
class GocharaResult:
    """
    Immutable natal-Moon judgment over a possibly partial sidereal snapshot.

    The profile fixes seven subjects/blockers. ``missing_planets`` records
    snapshot completeness; each judgment separately records missing eligible
    blockers. The source frame is a caller assertion, not certified astronomy.
    Optional BAV vessels must be the subjects' own unreduced natal BAVs.
    """

    natal_moon_sidereal_longitude: float
    positions: tuple[GocharaPosition, ...]
    bhinna: tuple[BhinnashtakavargaResult, ...] = ()
    policy: GocharaPolicy = DEFAULT_GOCHARA_POLICY
    profile: str = field(init=False, default=GOCHARA_PROFILE)
    source_edition: str = field(init=False, default=_EDITION)
    source_url: str = field(init=False, default=_SOURCE_URL)
    reference_source: str = field(init=False, default="Phaladeepika 26.1")
    position_origin: str = field(init=False, default="caller_supplied_sidereal")
    blocker_participants: tuple[str, ...] = field(init=False, default=GOCHARA_PLANETS)
    outside_profile_layers: tuple[str, ...] = field(init=False, default=(
        "nodes", "counter_vedha", "tara", "kakshya", "sign_part_activation",
        "dasha", "strength_overrides", "dated_forecast", "remedies", "composite_score",
    ))
    janma_rashi_index: int = field(init=False)
    missing_planets: tuple[str, ...] = field(init=False)
    planets: tuple[GocharaPlanetResult, ...] = field(init=False)

    def __post_init__(self) -> None:
        natal = _longitude(self.natal_moon_sidereal_longitude, "natal Moon longitude")
        positions = _ordered_positions(self.positions)
        _validate_snapshot_policy(positions, self.policy)
        present = {p.planet for p in positions}
        bav = {}
        for item in self.bhinna:
            item = _copy_bhinna(item)
            if item.planet not in present:
                raise ValueError(f"BAV supplied for absent transit subject {item.planet}")
            if item.planet in bav:
                raise ValueError(f"duplicate BAV for {item.planet}")
            bav[item.planet] = item
        if self.policy.bav_mode is GocharaBavMode.OMIT and bav:
            raise ValueError("bhinna was supplied but raw BAV is omitted by policy")
        if self.policy.bav_mode is GocharaBavMode.REQUIRE_ALL_RAW:
            missing_bav = tuple(p for p in GOCHARA_PLANETS if p in present and p not in bav)
            if missing_bav:
                raise ValueError(f"raw BAV required for supplied subjects: {missing_bav}")
        reference = int(natal // 30.0)
        object.__setattr__(self, "natal_moon_sidereal_longitude", natal)
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "bhinna", tuple(bav[p] for p in GOCHARA_PLANETS if p in bav))
        object.__setattr__(self, "janma_rashi_index", reference)
        object.__setattr__(self, "missing_planets", tuple(p for p in GOCHARA_PLANETS if p not in present))
        object.__setattr__(self, "planets", tuple(
            GocharaPlanetResult(p, reference, positions, bav.get(p.planet), self.policy) for p in positions
        ))

    def for_planet(self, planet: str) -> GocharaPlanetResult:
        """Return an assessed classical planet; an absent subject raises KeyError."""
        _planet(planet)
        for result in self.planets:
            if result.position.planet == planet:
                return result
        raise KeyError(f"no transit position supplied for {planet}")


def gochara_from_positions(
    natal_moon_sidereal_longitude: float,
    transit_sidereal_longitudes: Mapping[str, float],
    *,
    bhinna: Mapping[str, BhinnashtakavargaResult] | None = None,
    policy: GocharaPolicy = DEFAULT_GOCHARA_POLICY,
) -> GocharaResult:
    """
    Evaluate supplied sidereal longitudes under the Phaladeepika profile.

    No kernel, time, location or ayanamsa is inferred. Callers convert natal
    and transit longitudes at their respective epochs using the same frame
    policy. Only seven classical keys are admitted; partial mappings retain
    missing-data receipts. An empty mapping is rejected.

    ``bhinna`` optionally supplies each subject's own unreduced natal BAV.
    Its sign indices are absolute sidereal signs, not Moon-relative houses.
    The caller binds it to the same natal chart; the legacy BAV vessel does
    not contain natal identity metadata. No threshold or polarity override
    is applied to the raw count.

    ``policy`` selects admitted evaluation/completeness/raw-context scopes.
    The default preserves ordinary Vedha with partial-input receipts.
    A baseline-only scope explicitly omits Vedha; the doctrine catalogue
    records unadmitted source alternatives separately from executable modes.
    """
    if not isinstance(transit_sidereal_longitudes, Mapping):
        raise TypeError("transit_sidereal_longitudes must be a mapping")
    natal = _longitude(natal_moon_sidereal_longitude, "natal Moon longitude")
    positions = tuple(GocharaPosition(p, lon) for p, lon in transit_sidereal_longitudes.items())
    tables = ()
    if bhinna is not None:
        if not isinstance(bhinna, Mapping):
            raise TypeError("bhinna must be a mapping")
        for planet, value in bhinna.items():
            _planet(planet)
            if not isinstance(value, BhinnashtakavargaResult):
                raise TypeError("bhinna values must be BhinnashtakavargaResult vessels")
            if value.planet != planet:
                raise ValueError(f"BAV key {planet} does not match table planet {value.planet}")
        tables = tuple(bhinna.values())
    return GocharaResult(natal, positions, tables, policy)


class GocharaLocalCondition(str, Enum):
    """Integrated baseline/ordinary-Vedha state, without a life-outcome score."""

    FAVORABLE_UNOBSTRUCTED = "favorable_unobstructed"
    FAVORABLE_BLOCKED = "favorable_blocked"
    FAVORABLE_INCOMPLETE = "favorable_incomplete"
    FAVORABLE_VEDHA_OMITTED = "favorable_vedha_omitted"
    OUTSIDE_FAVORABLE_SET = "outside_favorable_set"


@dataclass(frozen=True, slots=True)
class GocharaLocalProfile:
    """Integrated local testimony whose raw BAV remains independent of condition."""

    assessment: GocharaPlanetResult
    planet: str = field(init=False)
    condition: GocharaLocalCondition = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.assessment, GocharaPlanetResult):
            raise TypeError("assessment must be a GocharaPlanetResult")
        status = self.assessment.vedha_status
        condition = {
            GocharaVedhaStatus.NOT_APPLICABLE: GocharaLocalCondition.OUTSIDE_FAVORABLE_SET,
            GocharaVedhaStatus.BLOCKED: GocharaLocalCondition.FAVORABLE_BLOCKED,
            GocharaVedhaStatus.INCOMPLETE: GocharaLocalCondition.FAVORABLE_INCOMPLETE,
            GocharaVedhaStatus.UNOBSTRUCTED: GocharaLocalCondition.FAVORABLE_UNOBSTRUCTED,
            GocharaVedhaStatus.OMITTED: GocharaLocalCondition.FAVORABLE_VEDHA_OMITTED,
        }[status]
        object.__setattr__(self, "planet", self.assessment.position.planet)
        object.__setattr__(self, "condition", condition)

    @property
    def ashtakavarga_rekhas(self) -> int | None:
        """The uncombined raw count retained by the authoritative assessment."""
        return self.assessment.ashtakavarga_rekhas


def gochara_local_profiles(snapshot: GocharaResult) -> tuple[GocharaLocalProfile, ...]:
    """Derive local profiles in the observed snapshot's canonical planet order."""
    if not isinstance(snapshot, GocharaResult):
        raise TypeError("snapshot must be a GocharaResult")
    return tuple(GocharaLocalProfile(p) for p in snapshot.planets)


@dataclass(frozen=True, slots=True)
class GocharaChartSummary:
    """Observed state partitions from local profiles; missing bodies remain separate."""

    snapshot: GocharaResult
    local_profiles: tuple[GocharaLocalProfile, ...] = field(init=False)
    favorable_planets: tuple[str, ...] = field(init=False)
    outside_favorable_planets: tuple[str, ...] = field(init=False)
    blocked_planets: tuple[str, ...] = field(init=False)
    unobstructed_planets: tuple[str, ...] = field(init=False)
    incomplete_verdict_planets: tuple[str, ...] = field(init=False)
    omitted_vedha_planets: tuple[str, ...] = field(init=False)
    incomplete_observation_planets: tuple[str, ...] = field(init=False)
    raw_bav_planets: tuple[str, ...] = field(init=False)
    missing_planets: tuple[str, ...] = field(init=False)
    condition_counts: tuple[tuple[GocharaLocalCondition, int], ...] = field(init=False)

    def __post_init__(self) -> None:
        profiles = gochara_local_profiles(self.snapshot)
        groups = {
            "favorable_planets": tuple(p.planet for p in profiles if p.assessment.baseline_favorable),
            "outside_favorable_planets": tuple(p.planet for p in profiles if p.condition is GocharaLocalCondition.OUTSIDE_FAVORABLE_SET),
            "blocked_planets": tuple(p.planet for p in profiles if p.condition is GocharaLocalCondition.FAVORABLE_BLOCKED),
            "unobstructed_planets": tuple(p.planet for p in profiles if p.condition is GocharaLocalCondition.FAVORABLE_UNOBSTRUCTED),
            "incomplete_verdict_planets": tuple(p.planet for p in profiles if p.condition is GocharaLocalCondition.FAVORABLE_INCOMPLETE),
            "omitted_vedha_planets": tuple(p.planet for p in profiles if p.condition is GocharaLocalCondition.FAVORABLE_VEDHA_OMITTED),
            "incomplete_observation_planets": tuple(p.planet for p in profiles if p.assessment.vedha_observation_complete is False),
            "raw_bav_planets": tuple(p.planet for p in profiles if p.ashtakavarga_rekhas is not None),
        }
        object.__setattr__(self, "local_profiles", profiles)
        for name, value in groups.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "missing_planets", self.snapshot.missing_planets)
        object.__setattr__(self, "condition_counts", tuple(
            (condition, sum(p.condition is condition for p in profiles)) for condition in GocharaLocalCondition
        ))


def _observed_vedha_witnesses(snapshot: GocharaResult) -> tuple[GocharaVedhaWitness, ...]:
    if not isinstance(snapshot, GocharaResult):
        raise TypeError("snapshot must be a GocharaResult")
    # Ordering is the assessed subject, then its blocker, in canonical planet order.
    return tuple(w for p in snapshot.planets for w in p.vedha_witnesses)


@dataclass(frozen=True, slots=True)
class GocharaNetworkNode:
    """One observed body; degrees describe known non-exempt blocker-to-subject edges."""

    snapshot: GocharaResult
    planet: str
    blocking: tuple[GocharaVedhaWitness, ...] = field(init=False)
    blocked_by: tuple[GocharaVedhaWitness, ...] = field(init=False)
    exempt_blocking: tuple[GocharaVedhaWitness, ...] = field(init=False)
    exempt_from: tuple[GocharaVedhaWitness, ...] = field(init=False)

    def __post_init__(self) -> None:
        witnesses = _observed_vedha_witnesses(self.snapshot)
        self.snapshot.for_planet(self.planet)
        for name, values in (
            ("blocking", tuple(w for w in witnesses if w.blocker.planet == self.planet and not w.exempt)),
            ("blocked_by", tuple(w for w in witnesses if w.subject.planet == self.planet and not w.exempt)),
            ("exempt_blocking", tuple(w for w in witnesses if w.blocker.planet == self.planet and w.exempt)),
            ("exempt_from", tuple(w for w in witnesses if w.subject.planet == self.planet and w.exempt)),
        ):
            object.__setattr__(self, name, values)

    @property
    def observed_out_degree(self) -> int:
        """Number of known subjects obstructed by this body; no importance weighting."""
        return len(self.blocking)

    @property
    def observed_in_degree(self) -> int:
        """Number of known blockers of this body; absent participants are not counted."""
        return len(self.blocked_by)


@dataclass(frozen=True, slots=True)
class GocharaVedhaNetwork:
    """Observed directed occupancy projection with separate active and exempt edges.

    Edges point from blocker to subject. Missing bodies are not fabricated as
    zero-degree nodes. An omitted layer is explicit and supplies no assertion
    of unconnectedness. This is source-rule structure, not a causal or scored
    planetary influence model.
    """

    snapshot: GocharaResult
    nodes: tuple[GocharaNetworkNode, ...] = field(init=False)
    active_edges: tuple[GocharaVedhaWitness, ...] = field(init=False)
    exempt_edges: tuple[GocharaVedhaWitness, ...] = field(init=False)
    vedha_evaluated: bool = field(init=False)
    observed_unconnected_planets: tuple[str, ...] = field(init=False)
    incomplete_observation_planets: tuple[str, ...] = field(init=False)
    missing_planets: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        profiles = gochara_local_profiles(self.snapshot)
        witnesses = tuple(w for p in profiles for w in p.assessment.vedha_witnesses)
        nodes = tuple(GocharaNetworkNode(self.snapshot, p.planet) for p in profiles)
        evaluated = self.snapshot.policy.vedha_mode is GocharaVedhaMode.ORDINARY
        for name, values in (
            ("nodes", nodes), ("active_edges", tuple(w for w in witnesses if not w.exempt)),
            ("exempt_edges", tuple(w for w in witnesses if w.exempt)), ("vedha_evaluated", evaluated),
            ("observed_unconnected_planets", tuple(n.planet for n in nodes
             if not n.observed_in_degree and not n.observed_out_degree) if evaluated else ()),
            ("incomplete_observation_planets", tuple(p.planet for p in profiles
             if p.assessment.vedha_observation_complete is False)),
            ("missing_planets", self.snapshot.missing_planets),
        ):
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class GocharaSubsystemProfile:
    """One snapshot's local, aggregate and network projections, derived together."""

    snapshot: GocharaResult
    local_profiles: tuple[GocharaLocalProfile, ...] = field(init=False)
    chart_summary: GocharaChartSummary = field(init=False)
    vedha_network: GocharaVedhaNetwork = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_profiles", gochara_local_profiles(self.snapshot))
        object.__setattr__(self, "chart_summary", GocharaChartSummary(self.snapshot))
        object.__setattr__(self, "vedha_network", GocharaVedhaNetwork(self.snapshot))


def gochara_subsystem_profile(snapshot: GocharaResult) -> GocharaSubsystemProfile:
    """Derive the bounded subsystem layers from one policy-stamped snapshot."""
    return GocharaSubsystemProfile(snapshot)
