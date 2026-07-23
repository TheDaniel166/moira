"""Source-bounded Dorothean matter profiles from Carmen Book V.

The six profiles share one public computational vessel because each is a
single-moment, non-scored inspection of a named matter.  Profile identity is
explicit; no profile is treated as a complete election or recommendation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._western_electional_context import (
    DOROTHEUS_ROOTED_CONTEXT_V1,
    DorotheusMatter,
    DorotheusPlacementWitness,
    DorotheusRootedContextEvaluation,
    DorotheusStrengthState,
    WesternElectionClass,
    evaluate_dorotheus_rooted_context,
)
from ._western_electional_dorotheus import (
    DOROTHEUS_MOON_CONDITION_V1,
    DorotheusMeasurement,
    DorotheusMoonConditionEvaluation,
    evaluate_dorotheus_moon_condition,
)
from ._western_electional_construction import _iers_mean_lunar_longitude_degrees
from .aspects import AspectMotionState, _STATIONARY_THRESHOLDS, aspect_motion_witness
from .chart import ChartContext, create_chart
from .aspect_events import (
    MoonConnectionFlow,
    MoonConnectionFlowPolicy,
    moon_connection_flow_at,
)
from .constants import Body, SIGNS, sign_of
from .eclipse import EclipseCalculator
from .egyptian_bounds import EgyptianBoundsDoctrine, EgyptianBoundsPolicy, egyptian_bound_of
from .houses import HousePolicy, assign_house, describe_angularity
from .lunar_direction import lunar_ecliptic_direction_at
from .planets import planet_at
from .profections import DOMICILE_RULERS
from .spk_reader import SpkReader, get_reader
from .void_of_course import next_moon_connection


__all__ = [
    "DorotheusMatterProfileId",
    "DorotheusSignNatureVariant",
    "DorotheusMatterClauseRole",
    "DorotheusMatterClauseState",
    "DorotheusMatterProfileStatus",
    "DorotheusAngularPlaceWitness",
    "DorotheusMatterClauseWitness",
    "DorotheusMatterProfilePolicy",
    "DorotheusMatterProfileEvaluation",
    "DOROTHEUS_DEMOLITION_V1",
    "DOROTHEUS_LEASING_V1",
    "DOROTHEUS_BUYING_AND_SELLING_V1",
    "DOROTHEUS_LUNAR_PRICE_TIMING_V1",
    "DOROTHEUS_LAND_PURCHASE_V1",
    "DOROTHEUS_TRAVEL_V1",
    "DOROTHEUS_SHIP_ACQUISITION_V1",
    "DOROTHEUS_SHIP_CONSTRUCTION_V1",
    "DOROTHEUS_SHIP_LAUNCH_V1",
    "DOROTHEUS_LAND_TRAVEL_V1",
    "DOROTHEUS_SEA_TRAVEL_V1",
    "DOROTHEUS_PARTNERSHIP_V1",
    "DOROTHEUS_DEBT_AND_PAYMENT_V1",
    "DOROTHEUS_WRITING_A_WILL_V1",
    "evaluate_dorotheus_matter_profile",
    "dorotheus_matter_profile_at",
]


_AUTHORITY_V8 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.8.1-2, printed p. 238, including note 40"
)
_AUTHORITY_V9 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.9.1-8, printed pp. 239-241, with Dykes's party-role commentary"
)
_AUTHORITY_V10 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.10.1-7, printed pp. 241-242"
)
_AUTHORITY_V44 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.44.1-8, printed pp. 324-325, including notes 397-403"
)
_AUTHORITY_CALCULATION = (
    "Dykes edition glossary, Increasing/decreasing in calculation, printed p. 363"
)
_AUTHORITY_MEAN_LUNAR_LONGITUDE = (
    "IERS Conventions (2010), Chapter 5, section 5.7.2, equation 5.43: "
    "Delaunay F = L - Omega and mean lunar node Omega, evaluated in TT"
)
_AUTHORITY_V11 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.11.1-3, printed pp. 242-243"
)
_AUTHORITY_V22 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.22.1-10, printed pp. 259-260, including notes 110-119"
)
_AUTHORITY_V24 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.24.1-5, printed pp. 263-264, including note 136"
)
_AUTHORITY_V20 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.20.1-19, printed pp. 255-257"
)
_AUTHORITY_V21 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.21.1-8, printed pp. 257-259, including notes 105-109"
)
_AUTHORITY_V25 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.25.1-6, printed pp. 264-265, including notes 137-142"
)
_AUTHORITY_V26 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.26.1-38, printed pp. 265-269, including notes 143-174"
)
_AUTHORITY_V26_TRAVEL = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.26.39-43, printed pp. 269-270, including notes 175-179"
)
_AUTHORITY_LILLY_1647_SIGN_QUALITIES = (
    "William Lilly, Christian Astrology (1647), Book I, chapter XVI, "
    "printed pp. 94-99: the twelve signs' elemental hot/cold and wet/dry qualities"
)
_AUTHORITY_V43 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.43.1-6, printed pp. 323-324, including note 387"
)
_AUTHORITY_EGYPTIAN_BOUNDS = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "translator's introduction, printed p. 36: Egyptian bounds as Dorotheus's table"
)
_AUTHORITY_WATERY_SIGNS = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book I.21.3, printed p. 91: Cancer, Scorpio, and Pisces as water signs"
)
_AUTHORITY_CONNECTION = (
    "Dykes edition glossary, Applying and Connection, printed pp. 352 and 355: "
    "application moves toward exactness, while connection also requires an "
    "unspecified particular degree interval"
)
_TRADITIONAL_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
)
_FORTUNES = (Body.JUPITER, Body.VENUS)
_INFORTUNES = (Body.MARS, Body.SATURN)
_CONFIGURED_OFFSETS = frozenset((0, 2, 3, 4, 6, 8, 9, 10))
_WATERY_SIGNS = frozenset(("Cancer", "Scorpio", "Pisces"))
_LILLY_1647_DRY_SIGNS = frozenset(
    ("Aries", "Taurus", "Leo", "Virgo", "Sagittarius", "Capricorn")
)
_TWIN_SIGNS = frozenset(("Gemini", "Virgo", "Sagittarius", "Pisces"))
_RISING_REGION_SIGNS = frozenset(
    ("Aquarius", "Pisces", "Aries", "Taurus", "Gemini", "Cancer")
)
_PHASE_BOUNDARY_TOLERANCE_DEG = 1e-9


class DorotheusMatterProfileId(str, Enum):
    """Vessel: Registry of dorotheus matter profile id values."""
    DEMOLITION = "dorotheus_demolition_v1"
    LEASING = "dorotheus_leasing_v1"
    BUYING_AND_SELLING = "dorotheus_buying_and_selling_v1"
    LUNAR_PRICE_TIMING = "dorotheus_lunar_price_timing_v1"
    LAND_PURCHASE = "dorotheus_land_purchase_v1"
    TRAVEL = "dorotheus_travel_v1"
    SHIP_ACQUISITION = "dorotheus_ship_acquisition_v1"
    SHIP_CONSTRUCTION = "dorotheus_ship_construction_v1"
    SHIP_LAUNCH = "dorotheus_ship_launch_v1"
    LAND_TRAVEL = "dorotheus_land_travel_v1"
    SEA_TRAVEL = "dorotheus_sea_travel_v1"
    PARTNERSHIP = "dorotheus_partnership_v1"
    DEBT_AND_PAYMENT = "dorotheus_debt_and_payment_v1"
    WRITING_A_WILL = "dorotheus_writing_a_will_v1"


class DorotheusSignNatureVariant(str, Enum):
    """Explicit authority for V.26's otherwise unenumerated dry-sign class."""

    SOURCE_TEXT_UNRESOLVED = "source_text_unresolved_no_dry_sign_table"
    LILLY_1647_ELEMENTAL_QUALITIES = "lilly_1647_elemental_qualities"


_SIGN_NATURE_PROFILES = frozenset(
    (DorotheusMatterProfileId.LAND_TRAVEL, DorotheusMatterProfileId.SEA_TRAVEL)
)


class DorotheusMatterClauseRole(str, Enum):
    """Vessel: Registry of dorotheus matter clause role values."""
    FORTIFIER = "fortifier"
    GATE = "gate"
    WITNESS = "witness"


class DorotheusMatterClauseState(str, Enum):
    """Vessel: Registry of dorotheus matter clause state values."""
    SATISFIED = "satisfied"
    CLEAR = "clear"
    TRIGGERED = "triggered"
    OBSERVED = "observed"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusMatterProfileStatus(str, Enum):
    """Vessel: Registry of dorotheus matter profile status values."""
    CLEAR = "clear_of_explicit_profile_impediments"
    TRIGGERED = "one_or_more_explicit_profile_impediments"
    DESCRIPTIVE = "descriptive_witnesses_only"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DorotheusAngularPlaceWitness:
    """Vessel: Structured dorotheus angular place witness data."""
    whole_sign_place: int
    topic: str
    sign: str
    occupying_fortunes: tuple[str, ...]
    configured_fortunes: tuple[str, ...]
    occupying_infortunes: tuple[str, ...]
    configured_infortunes: tuple[str, ...]
    source_meaning: str

    def __post_init__(self) -> None:
        if self.whole_sign_place not in (1, 4, 7, 10):
            raise ValueError("angular witness must use whole-sign place 1, 4, 7, or 10")
        if self.sign not in SIGNS or not self.topic or not self.source_meaning:
            raise ValueError("angular topic identity and canonical sign must remain visible")


@dataclass(frozen=True, slots=True)
class DorotheusMatterClauseWitness:
    """Vessel: Structured dorotheus matter clause witness data."""
    clause_id: str
    source_order: int
    role: DorotheusMatterClauseRole
    state: DorotheusMatterClauseState
    measurements: tuple[DorotheusMeasurement, ...]
    explanation: str
    source_reference: str

    def __post_init__(self) -> None:
        if self.source_order < 1 or not self.clause_id or not self.measurements:
            raise ValueError("matter clause identity, order, and derivation must remain visible")
        if not self.explanation or not self.source_reference:
            raise ValueError("matter clause explanation and authority must remain visible")
        if self.role is DorotheusMatterClauseRole.GATE:
            if self.state not in (
                DorotheusMatterClauseState.CLEAR,
                DorotheusMatterClauseState.TRIGGERED,
                DorotheusMatterClauseState.NOT_EVALUABLE,
            ):
                raise ValueError("gate clauses require clear, triggered, or not-evaluable state")
        elif self.state is DorotheusMatterClauseState.TRIGGERED:
            raise ValueError("only gate clauses can be triggered")


@dataclass(frozen=True, slots=True)
class DorotheusMatterProfilePolicy:
    """Vessel: Structured dorotheus matter profile policy data."""
    profile_id: DorotheusMatterProfileId
    profile_version: str = "1.0.0"
    angular_place_policy: str = "whole_sign_places_from_tropical_ascendant"
    configuration_policy: str = "whole_sign_ptolemaic_configuration"
    strength_policy: str = "quadrant_house_angular_succedent_cadent"
    copresence_policy: str = "same_sign_copresence"
    under_rays_policy: str = "dykes_glossary_15_degree_solar_distance"
    calculation_policy: str = "iers_true_minus_mean_lunar_equation"
    station_policy: str = "moira_body_specific_instantaneous_speed_thresholds"
    connection_policy: str = "applying_to_exact_with_source_degree_interval_unresolved"
    sign_nature_variant: DorotheusSignNatureVariant = (
        DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
    )
    latitude_rate_sample_days: float = 0.01

    def __post_init__(self) -> None:
        if self.profile_version != "1.0.0":
            raise ValueError("profile_version is fixed for admitted v1 profiles")
        if self.angular_place_policy != "whole_sign_places_from_tropical_ascendant":
            raise ValueError("angular_place_policy is fixed")
        if self.configuration_policy != "whole_sign_ptolemaic_configuration":
            raise ValueError("configuration_policy is fixed")
        if self.strength_policy != "quadrant_house_angular_succedent_cadent":
            raise ValueError("strength_policy is fixed")
        if self.copresence_policy != "same_sign_copresence":
            raise ValueError("copresence_policy is fixed")
        if self.under_rays_policy != "dykes_glossary_15_degree_solar_distance":
            raise ValueError("under_rays_policy is fixed")
        if self.calculation_policy != "iers_true_minus_mean_lunar_equation":
            raise ValueError("calculation_policy is fixed")
        if self.station_policy != "moira_body_specific_instantaneous_speed_thresholds":
            raise ValueError("station_policy is fixed")
        if self.connection_policy != "applying_to_exact_with_source_degree_interval_unresolved":
            raise ValueError("connection_policy is fixed")
        if not isinstance(self.sign_nature_variant, DorotheusSignNatureVariant):
            raise TypeError("sign_nature_variant must be a DorotheusSignNatureVariant")
        if (
            self.profile_id not in _SIGN_NATURE_PROFILES
            and self.sign_nature_variant
            is not DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
        ):
            raise ValueError("sign_nature_variant belongs only to V.26.39-43 travel profiles")
        if self.latitude_rate_sample_days != 0.01:
            raise ValueError("latitude_rate_sample_days is fixed")


DOROTHEUS_DEMOLITION_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.DEMOLITION
)
DOROTHEUS_LEASING_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.LEASING
)
DOROTHEUS_BUYING_AND_SELLING_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.BUYING_AND_SELLING
)
DOROTHEUS_LUNAR_PRICE_TIMING_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.LUNAR_PRICE_TIMING
)
DOROTHEUS_LAND_PURCHASE_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.LAND_PURCHASE
)
DOROTHEUS_TRAVEL_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.TRAVEL
)
DOROTHEUS_SHIP_ACQUISITION_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.SHIP_ACQUISITION
)
DOROTHEUS_SHIP_CONSTRUCTION_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.SHIP_CONSTRUCTION
)
DOROTHEUS_SHIP_LAUNCH_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.SHIP_LAUNCH
)
DOROTHEUS_LAND_TRAVEL_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.LAND_TRAVEL
)
DOROTHEUS_SEA_TRAVEL_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.SEA_TRAVEL
)
DOROTHEUS_PARTNERSHIP_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.PARTNERSHIP
)
DOROTHEUS_DEBT_AND_PAYMENT_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.DEBT_AND_PAYMENT
)
DOROTHEUS_WRITING_A_WILL_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.WRITING_A_WILL
)
_POLICIES = {
    policy.profile_id: policy
    for policy in (
        DOROTHEUS_DEMOLITION_V1,
        DOROTHEUS_LEASING_V1,
        DOROTHEUS_BUYING_AND_SELLING_V1,
        DOROTHEUS_LUNAR_PRICE_TIMING_V1,
        DOROTHEUS_LAND_PURCHASE_V1,
        DOROTHEUS_TRAVEL_V1,
        DOROTHEUS_SHIP_ACQUISITION_V1,
        DOROTHEUS_SHIP_CONSTRUCTION_V1,
        DOROTHEUS_SHIP_LAUNCH_V1,
        DOROTHEUS_LAND_TRAVEL_V1,
        DOROTHEUS_SEA_TRAVEL_V1,
        DOROTHEUS_PARTNERSHIP_V1,
        DOROTHEUS_DEBT_AND_PAYMENT_V1,
        DOROTHEUS_WRITING_A_WILL_V1,
    )
}
_AUTHORITIES = {
    DorotheusMatterProfileId.DEMOLITION: _AUTHORITY_V8,
    DorotheusMatterProfileId.LEASING: _AUTHORITY_V9,
    DorotheusMatterProfileId.BUYING_AND_SELLING: _AUTHORITY_V10,
    DorotheusMatterProfileId.LUNAR_PRICE_TIMING: _AUTHORITY_V44,
    DorotheusMatterProfileId.LAND_PURCHASE: _AUTHORITY_V11,
    DorotheusMatterProfileId.TRAVEL: _AUTHORITY_V22,
    DorotheusMatterProfileId.SHIP_ACQUISITION: _AUTHORITY_V24,
    DorotheusMatterProfileId.SHIP_CONSTRUCTION: _AUTHORITY_V25,
    DorotheusMatterProfileId.SHIP_LAUNCH: _AUTHORITY_V26,
    DorotheusMatterProfileId.LAND_TRAVEL: _AUTHORITY_V26_TRAVEL,
    DorotheusMatterProfileId.SEA_TRAVEL: _AUTHORITY_V26_TRAVEL,
    DorotheusMatterProfileId.PARTNERSHIP: _AUTHORITY_V20,
    DorotheusMatterProfileId.DEBT_AND_PAYMENT: _AUTHORITY_V21,
    DorotheusMatterProfileId.WRITING_A_WILL: _AUTHORITY_V43,
}
_MATTERS = {
    DorotheusMatterProfileId.DEMOLITION: "building_demolition",
    DorotheusMatterProfileId.LEASING: "leasing",
    DorotheusMatterProfileId.BUYING_AND_SELLING: "buying_and_selling",
    DorotheusMatterProfileId.LUNAR_PRICE_TIMING: "lunar_price_timing",
    DorotheusMatterProfileId.LAND_PURCHASE: "land_purchase",
    DorotheusMatterProfileId.TRAVEL: "travel_and_departure",
    DorotheusMatterProfileId.SHIP_ACQUISITION: "ship_acquisition_or_commission",
    DorotheusMatterProfileId.SHIP_CONSTRUCTION: "ship_construction",
    DorotheusMatterProfileId.SHIP_LAUNCH: "ship_launch",
    DorotheusMatterProfileId.LAND_TRAVEL: "land_travel",
    DorotheusMatterProfileId.SEA_TRAVEL: "sea_travel",
    DorotheusMatterProfileId.PARTNERSHIP: "entering_a_partnership",
    DorotheusMatterProfileId.DEBT_AND_PAYMENT: "debt_and_payment",
    DorotheusMatterProfileId.WRITING_A_WILL: "writing_a_will",
}
_EXPECTED_CLAUSE_COUNTS = {
    DorotheusMatterProfileId.DEMOLITION: 2,
    DorotheusMatterProfileId.LEASING: 5,
    DorotheusMatterProfileId.BUYING_AND_SELLING: 2,
    DorotheusMatterProfileId.LUNAR_PRICE_TIMING: 3,
    DorotheusMatterProfileId.LAND_PURCHASE: 2,
    DorotheusMatterProfileId.TRAVEL: 10,
    DorotheusMatterProfileId.SHIP_ACQUISITION: 5,
    DorotheusMatterProfileId.SHIP_CONSTRUCTION: 6,
    DorotheusMatterProfileId.SHIP_LAUNCH: 38,
    DorotheusMatterProfileId.LAND_TRAVEL: 5,
    DorotheusMatterProfileId.SEA_TRAVEL: 3,
    DorotheusMatterProfileId.PARTNERSHIP: 19,
    DorotheusMatterProfileId.DEBT_AND_PAYMENT: 8,
    DorotheusMatterProfileId.WRITING_A_WILL: 6,
}
_ROOTED_MATTERS = {
    DorotheusMatterProfileId.DEMOLITION: DorotheusMatter.LAND_AND_MANAGEMENT,
    DorotheusMatterProfileId.LEASING: DorotheusMatter.LAND_AND_MANAGEMENT,
    DorotheusMatterProfileId.BUYING_AND_SELLING: DorotheusMatter.MERCURIAL_AFFAIRS,
    DorotheusMatterProfileId.LUNAR_PRICE_TIMING: DorotheusMatter.MERCURIAL_AFFAIRS,
    DorotheusMatterProfileId.LAND_PURCHASE: DorotheusMatter.LAND_AND_MANAGEMENT,
    DorotheusMatterProfileId.PARTNERSHIP: DorotheusMatter.MERCURIAL_AFFAIRS,
    DorotheusMatterProfileId.DEBT_AND_PAYMENT: DorotheusMatter.MERCURIAL_AFFAIRS,
}
_FLOW_PROFILES = frozenset(
    (
        DorotheusMatterProfileId.LEASING,
        DorotheusMatterProfileId.BUYING_AND_SELLING,
    )
)
_UNROOTED_EPHEMERAL_PROFILES = frozenset(
    (
        DorotheusMatterProfileId.TRAVEL,
        DorotheusMatterProfileId.SHIP_ACQUISITION,
        DorotheusMatterProfileId.SHIP_CONSTRUCTION,
        DorotheusMatterProfileId.SHIP_LAUNCH,
        DorotheusMatterProfileId.LAND_TRAVEL,
        DorotheusMatterProfileId.SEA_TRAVEL,
        DorotheusMatterProfileId.WRITING_A_WILL,
    )
)
_EPHEMERAL_ONLY_PROFILES = frozenset(
    (
        DorotheusMatterProfileId.TRAVEL,
        DorotheusMatterProfileId.SHIP_ACQUISITION,
        DorotheusMatterProfileId.SHIP_CONSTRUCTION,
        DorotheusMatterProfileId.LAND_TRAVEL,
        DorotheusMatterProfileId.SEA_TRAVEL,
        DorotheusMatterProfileId.WRITING_A_WILL,
    )
)


@dataclass(frozen=True, slots=True)
class DorotheusMatterProfileEvaluation:
    """Vessel: Structured dorotheus matter profile evaluation data."""
    jd_ut: float
    profile_id: DorotheusMatterProfileId
    profile_version: str
    policy: DorotheusMatterProfilePolicy
    matter: str
    status: DorotheusMatterProfileStatus
    moon_condition: DorotheusMoonConditionEvaluation
    rooted_context: DorotheusRootedContextEvaluation | None
    moon_connection_flow: MoonConnectionFlow | None
    clauses: tuple[DorotheusMatterClauseWitness, ...]
    angular_places: tuple[DorotheusAngularPlaceWitness, ...]
    planetary_strengths: tuple[DorotheusPlacementWitness, ...]
    triggered_clause_ids: tuple[str, ...]
    not_evaluable_clause_ids: tuple[str, ...]
    reader_provenance: str
    authorities: tuple[str, ...]
    source_complete: bool = True
    complete_matter_profile: bool = True
    numerically_complete: bool = True
    complete_electional_judgement: bool = False
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"
    scoring: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("jd_ut must be finite")
        if self.matter != _MATTERS[self.profile_id]:
            raise ValueError("matter must derive from profile identity")
        if self.policy.profile_id is not self.profile_id:
            raise ValueError("serialized policy must match profile identity")
        if self.profile_version != self.policy.profile_version:
            raise ValueError("profile version must derive from serialized policy")
        if self.profile_id in _UNROOTED_EPHEMERAL_PROFILES:
            if self.rooted_context is not None:
                raise ValueError(
                    "this source-unrooted profile must not invent a V.31 matter family"
                )
        elif self.rooted_context is None:
            raise ValueError("existing V.8-V.11 profiles require their rooted context")
        if (
            self.profile_id not in _FLOW_PROFILES
            and self.moon_connection_flow is not None
        ):
            raise ValueError("Moon connection flow belongs only to a flow-based profile")
        if len(self.clauses) != _EXPECTED_CLAUSE_COUNTS[self.profile_id]:
            raise ValueError("profile must preserve every admitted source clause")
        if tuple(item.source_order for item in self.clauses) != tuple(
            range(1, len(self.clauses) + 1)
        ):
            raise ValueError("matter clauses must remain in source-derived order")
        triggered = tuple(
            item.clause_id
            for item in self.clauses
            if item.state is DorotheusMatterClauseState.TRIGGERED
        )
        unknown = tuple(
            item.clause_id
            for item in self.clauses
            if item.state is DorotheusMatterClauseState.NOT_EVALUABLE
        )
        if triggered != self.triggered_clause_ids or unknown != self.not_evaluable_clause_ids:
            raise ValueError("clause summaries must derive from visible clauses")
        if self.numerically_complete != (not unknown):
            raise ValueError("numerical completeness must derive from evaluability")
        if not self.source_complete or not self.complete_matter_profile:
            raise ValueError("an admitted matter profile must preserve its full source layer")
        if self.complete_electional_judgement:
            raise ValueError("a matter profile is not a complete electional judgement")


def _measurement(
    name: str,
    value: float | str | bool | None,
    *,
    units: str | None = None,
    comparison: str | None = None,
    threshold: float | str | bool | None = None,
) -> DorotheusMeasurement:
    return DorotheusMeasurement(name, value, units, comparison, threshold)


def _whole_sign_offset(a_sign: str, b_sign: str) -> int:
    return (SIGNS.index(b_sign) - SIGNS.index(a_sign)) % 12


def _configured(a_sign: str, b_sign: str) -> bool:
    return _whole_sign_offset(a_sign, b_sign) in _CONFIGURED_OFFSETS


def _placement(
    chart: ChartContext,
    body: str,
    *,
    role: str = "V.8 fortune_or_infortune_strength",
) -> DorotheusPlacementWitness:
    planet = chart.planets[body]
    houses = chart.houses
    if houses is None or not houses.is_quadrant_system:
        return DorotheusPlacementWitness(
            body=body,
            role=role,
            longitude=planet.longitude,
            sign=planet.sign,
            house=None,
            strength=DorotheusStrengthState.NOT_EVALUABLE,
            house_system_is_quadrant=False,
            explanation="Dynamic strength requires a quadrant house figure.",
        )
    house = assign_house(planet.longitude, houses)
    strength = DorotheusStrengthState(describe_angularity(house).category.value)
    return DorotheusPlacementWitness(
        body=body,
        role=role,
        longitude=planet.longitude,
        sign=planet.sign,
        house=house.house,
        strength=strength,
        house_system_is_quadrant=True,
        explanation="Strength is the house's angular, succedent, or cadent relation.",
    )


def _angular_witness(
    chart: ChartContext,
    place: int,
    topic: str,
    source_meaning: str,
) -> DorotheusAngularPlaceWitness:
    if chart.houses is None:
        raise ValueError("matter profiles require houses")
    asc_sign, _, _ = sign_of(chart.houses.asc)
    target_sign = SIGNS[(SIGNS.index(asc_sign) + place - 1) % 12]

    def occupants(bodies: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(body for body in bodies if chart.planets[body].sign == target_sign)

    def aspecters(bodies: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            body
            for body in bodies
            if chart.planets[body].sign != target_sign
            and _configured(chart.planets[body].sign, target_sign)
        )

    return DorotheusAngularPlaceWitness(
        whole_sign_place=place,
        topic=topic,
        sign=target_sign,
        occupying_fortunes=occupants(_FORTUNES),
        configured_fortunes=aspecters(_FORTUNES),
        occupying_infortunes=occupants(_INFORTUNES),
        configured_infortunes=aspecters(_INFORTUNES),
        source_meaning=source_meaning,
    )


def _body_testimony(
    chart: ChartContext,
    body: str,
    witnesses: tuple[str, ...],
) -> tuple[str, ...]:
    """Return source-visible whole-sign testimony, excluding self-testimony."""

    sign = chart.planets[body].sign
    return tuple(
        witness
        for witness in witnesses
        if witness != body and _configured(chart.planets[witness].sign, sign)
    )


def _whole_sign_place(chart: ChartContext, body: str) -> int:
    if chart.houses is None:
        raise ValueError("whole-sign place requires houses")
    asc_sign, _, _ = sign_of(chart.houses.asc)
    return _whole_sign_offset(asc_sign, chart.planets[body].sign) + 1


def _solar_distance(chart: ChartContext, body: str) -> float | None:
    if body == Body.SUN:
        return None
    return abs(
        (
            chart.planets[body].longitude
            - chart.planets[Body.SUN].longitude
            + 180.0
        )
        % 360.0
        - 180.0
    )


def _lunar_calculation(
    chart: ChartContext,
    moon_true_longitude_mean_ecliptic_degrees: float,
) -> tuple[float, float, str]:
    mean_lunar_longitude = _iers_mean_lunar_longitude_degrees(chart.jd_tt)
    lunar_equation = (
        moon_true_longitude_mean_ecliptic_degrees
        - mean_lunar_longitude
        + 180.0
    ) % 360.0 - 180.0
    direction = (
        "increasing"
        if lunar_equation > 0.0
        else "decreasing"
        if lunar_equation < 0.0
        else "zero"
    )
    return mean_lunar_longitude, lunar_equation, direction


def _hard_aspect_name(a_sign: str, b_sign: str) -> str | None:
    offset = _whole_sign_offset(a_sign, b_sign)
    if offset in (3, 9):
        return "Square"
    if offset == 6:
        return "Opposition"
    return None


def _stationary_witness(chart: ChartContext, body: str) -> tuple[bool, float]:
    threshold = _STATIONARY_THRESHOLDS.get(body, 0.005)
    return abs(chart.planets[body].speed) < threshold, threshold


def _phase_quadrant(elongation: float) -> tuple[str, str, str | None]:
    """Classify V.44's four phase arcs without hiding exact boundaries."""

    boundaries = (
        (0.0, "exact_solar_conjunction"),
        (90.0, "exact_left_square"),
        (180.0, "exact_opposition"),
        (270.0, "exact_right_square"),
        (360.0, "exact_solar_conjunction"),
    )
    for boundary, label in boundaries:
        distance = abs(elongation - boundary)
        if boundary == 360.0:
            distance = min(distance, abs(elongation))
        if distance <= _PHASE_BOUNDARY_TOLERANCE_DEG:
            return (
                label,
                "boundary_between_adjacent_source_intervals",
                "The source says each phase moves until it reaches the boundary; "
                "the edition does not settle ownership of the exact boundary.",
            )
    if elongation < 90.0:
        return (
            "solar_conjunction_to_left_square",
            "fair_equivalent_price_for_buying_or_selling",
            None,
        )
    if elongation < 180.0:
        return (
            "left_square_to_opposition",
            "seller_benefit",
            "The source also associates this interval with lawsuit inceptions.",
        )
    if elongation < 270.0:
        return "opposition_to_right_square", "buyer_benefit", None
    return (
        "right_square_to_solar_conjunction",
        "benefit_for_truthful_and_just_intent",
        "Edition note 402 preserves the alternative reading that the price will be low.",
    )


def _clause(
    clause_id: str,
    order: int,
    role: DorotheusMatterClauseRole,
    state: DorotheusMatterClauseState,
    measurements: tuple[DorotheusMeasurement, ...],
    explanation: str,
    source_reference: str,
) -> DorotheusMatterClauseWitness:
    return DorotheusMatterClauseWitness(
        clause_id, order, role, state, measurements, explanation, source_reference
    )


def _sun_moon_elongation(chart: ChartContext) -> float:
    return (chart.planets[Body.MOON].longitude - chart.planets[Body.SUN].longitude) % 360.0


def _ship_construction_clauses(
    chart: ChartContext,
    *,
    moon_latitude_rate_degrees_per_day: float,
    moon_true_longitude_mean_ecliptic_degrees: float,
    authority: str,
) -> tuple[DorotheusMatterClauseWitness, ...]:
    """Preserve V.25's evaluable evidence without inventing its open terms."""

    moon = chart.planets[Body.MOON]
    sun = chart.planets[Body.SUN]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    bound = egyptian_bound_of(
        moon.longitude,
        policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN),
    )
    _, lunar_equation, calculation_direction = _lunar_calculation(
        chart, moon_true_longitude_mean_ecliptic_degrees
    )
    elongation = _sun_moon_elongation(chart)
    sun_trine_fortunes = tuple(
        body
        for body in _FORTUNES
        if _whole_sign_offset(sun.sign, chart.planets[body].sign) in (4, 8)
    )
    sun_mars_hard = _hard_aspect_name(sun.sign, moon.sign)
    mars_moon_hard = _hard_aspect_name(chart.planets[Body.MARS].sign, moon.sign)
    mars_asc_configuration = _configured(chart.planets[Body.MARS].sign, asc_sign)
    mars_moon_configuration = _configured(chart.planets[Body.MARS].sign, moon.sign)
    both_hard = sun_mars_hard is not None and mars_moon_hard is not None
    aquarius_same_sign_ambiguity = (
        moon.sign == "Aquarius"
        and not both_hard
        and (
            chart.planets[Body.SUN].sign == moon.sign
            or chart.planets[Body.MARS].sign == moon.sign
        )
    )
    return (
        _clause(
            "ship_construction_preferred_conditions",
            1,
            DorotheusMatterClauseRole.FORTIFIER,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("sun_sign", sun.sign),
                _measurement("sun_trine_fortunes", ",".join(sun_trine_fortunes) or "none"),
                _measurement("sun_trine_quantifier", "source_unresolved_one_or_both"),
                _measurement("moon_sun_elongation", elongation, units="degrees"),
                _measurement("moon_increasing_in_glow", 0.0 < elongation < 180.0),
                _measurement("lunar_equation", lunar_equation, units="degrees"),
                _measurement("calculation_direction", calculation_direction),
                _measurement("moon_latitude_rate", moon_latitude_rate_degrees_per_day, units="degrees/day"),
                _measurement("moon_longitude_rate", moon.speed, units="degrees/day"),
                _measurement("moon_bound_ruler", bound.ruler),
                _measurement("moon_in_fortune_bound", bound.ruler in _FORTUNES),
                _measurement("latitude_increase_interpretation", "source_unresolved"),
                _measurement("longitude_increase_interpretation", "source_unresolved"),
            ),
            "V.25.1 joins Sun/fortune trine, lunar glow and calculation, latitude and longitude increase, and a fortune bound. Glow, calculation, and the Egyptian-bound lookup are visible; the cited source leaves the trine quantifier and latitude/longitude increase criteria open.",
            f"{authority}; {_AUTHORITY_CALCULATION}; {_AUTHORITY_MEAN_LUNAR_LONGITUDE}; {_AUTHORITY_EGYPTIAN_BOUNDS}",
        ),
        _clause(
            "moon_and_ascendant_made_unfortunate_by_mars",
            2,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("ascendant_sign", asc_sign),
                _measurement("moon_sign", moon.sign),
                _measurement("mars_sign", chart.planets[Body.MARS].sign),
                _measurement("mars_configures_ascendant", mars_asc_configuration),
                _measurement("mars_configures_moon", mars_moon_configuration),
                _measurement("made_unfortunate_policy", "source_unresolved"),
            ),
            "V.25.2 names the Moon and Ascendant made unfortunate by Mars. The observable Mars configurations are preserved, but the chapter does not define a complete Mars-specific made-unfortunate predicate.",
            authority,
        ),
        _clause(
            "aquarius_sun_mars_ship_damage",
            3,
            DorotheusMatterClauseRole.GATE,
            (
                DorotheusMatterClauseState.TRIGGERED
                if moon.sign == "Aquarius" and both_hard
                else DorotheusMatterClauseState.NOT_EVALUABLE
                if aquarius_same_sign_ambiguity
                else DorotheusMatterClauseState.CLEAR
            ),
            (
                _measurement("moon_sign", moon.sign),
                _measurement("sun_moon_hard_aspect", sun_mars_hard or "none"),
                _measurement("mars_moon_hard_aspect", mars_moon_hard or "none"),
                _measurement("same_sign_grammar_ambiguity", aquarius_same_sign_ambiguity),
            ),
            "V.25.3's Aquarius damage testimony is triggered only by the unambiguous Sun-and-Mars hard-aspect branch. Its damaged same-sign grammar remains explicitly not evaluable.",
            authority,
        ),
        _clause(
            "marine_sign_submersion_damage",
            4,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_sign", moon.sign),
                _measurement("sun_moon_hard_aspect", sun_mars_hard or "none"),
                _measurement("mars_moon_hard_aspect", mars_moon_hard or "none"),
                _measurement("marine_sign_table", "source_not_admitted"),
            ),
            "V.25.4 names a marine-sign condition with Sun and Mars hard aspects. The edition does not enumerate the required marine-sign table, so the condition is not evaluated from an invented taxonomy.",
            authority,
        ),
        _clause(
            "dry_sign_shore_reef_damage",
            5,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_sign", moon.sign),
                _measurement("sun_moon_hard_aspect", sun_mars_hard or "none"),
                _measurement("mars_moon_hard_aspect", mars_moon_hard or "none"),
                _measurement("dry_sign_table", "source_not_admitted"),
            ),
            "V.25.5 names a dry-sign reef and shore damage condition. No source-bound dry-sign table is admitted for this chapter.",
            authority,
        ),
        _clause(
            "non_dry_sign_piracy_damage",
            6,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_sign", moon.sign),
                _measurement("dry_sign_table", "source_not_admitted"),
            ),
            "V.25.6 names the non-dry branch and piracy testimony. Its sign classification remains not evaluable until a governing dry-sign table is sourced.",
            authority,
        ),
    )


def _partnership_clauses(
    chart: ChartContext,
    *,
    authority: str,
) -> tuple[
    tuple[DorotheusMatterClauseWitness, ...],
    tuple[DorotheusAngularPlaceWitness, ...],
]:
    """Evaluate V.20 without turning its outcomes into a generic score."""

    moon = chart.planets[Body.MOON]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    shared_sign = asc_sign if asc_sign == moon.sign else None
    angular_places = (
        _angular_witness(chart, 1, "initiating_party", "the first contracting party"),
        _angular_witness(chart, 7, "other_partner", "the other contracting party"),
        _angular_witness(chart, 10, "partnership_work", "the partnership's work"),
        _angular_witness(chart, 4, "partnership_outcome", "the matter's conclusion"),
    )
    sign_rows = (
        ("Aries", DorotheusMatterClauseRole.GATE, "unsuitable; sudden separation"),
        ("Taurus", DorotheusMatterClauseRole.WITNESS, "rank and dissension outcome requires party-status evidence"),
        ("Gemini", DorotheusMatterClauseRole.FORTIFIER, "suitable; benefit and faithfulness"),
        ("Cancer", DorotheusMatterClauseRole.GATE, "betrayal and slander"),
        ("Leo", DorotheusMatterClauseRole.FORTIFIER, "benefit and praise"),
        ("Virgo", DorotheusMatterClauseRole.FORTIFIER, "benefit, praise, affection, and profit"),
        ("Libra", DorotheusMatterClauseRole.GATE, "no good"),
        ("Scorpio", DorotheusMatterClauseRole.GATE, "deceit and conflict"),
        ("Sagittarius", DorotheusMatterClauseRole.WITNESS, "suitable with arrogance"),
        ("Capricorn", DorotheusMatterClauseRole.FORTIFIER, "joy"),
        ("Aquarius", DorotheusMatterClauseRole.GATE, "harm"),
        ("Pisces", DorotheusMatterClauseRole.FORTIFIER, "excellent and suitable"),
    )
    clauses: list[DorotheusMatterClauseWitness] = [
        _clause(
            "moon_marriage_suitability_and_cleansing",
            1,
            DorotheusMatterClauseRole.FORTIFIER,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_sign", moon.sign),
                _measurement("marriage_suitable_sign_table", "V.17_dependency_not_admitted"),
                _measurement("cleansed_from_misfortunes", "source_predicate_not_closed"),
            ),
            "V.20.1 invokes the chapter's inherited marriage-suitable signs and a cleansing predicate. Neither is silently reconstructed here, so the opening condition remains visible but not evaluable.",
            authority,
        )
    ]
    for order, (sign, role, effect) in enumerate(sign_rows, start=2):
        matched = shared_sign == sign
        if sign == "Taurus" and matched:
            state = DorotheusMatterClauseState.NOT_EVALUABLE
        elif role is DorotheusMatterClauseRole.GATE:
            state = (
                DorotheusMatterClauseState.TRIGGERED
                if matched
                else DorotheusMatterClauseState.CLEAR
            )
        elif role is DorotheusMatterClauseRole.FORTIFIER:
            state = (
                DorotheusMatterClauseState.SATISFIED
                if matched
                else DorotheusMatterClauseState.CLEAR
            )
        else:
            state = (
                DorotheusMatterClauseState.OBSERVED
                if matched
                else DorotheusMatterClauseState.CLEAR
            )
        clauses.append(
            _clause(
                f"ascendant_and_moon_in_{sign.lower()}_partnership_testimony",
                order,
                role,
                state,
                (
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("shared_sign", shared_sign or "none"),
                    _measurement("source_effect", effect),
                ),
                f"V.20.{order} gives the paired Ascendant-and-Moon testimony for {sign}. It remains a named source witness, not a scored recommendation.",
                authority,
            )
        )
    configured_bodies = tuple(
        body
        for body in _FORTUNES + _INFORTUNES
        if (
            _configured(chart.planets[body].sign, asc_sign)
            or _configured(chart.planets[body].sign, moon.sign)
        )
    )
    clauses.extend(
        (
            _clause(
                "absence_of_fortune_and_infortune_testimony",
                14,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if not configured_bodies
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("configured_fortunes_or_infortunes", ",".join(configured_bodies) or "none"),
                ),
                "V.20.14 preserves the table's stated condition that no fortune or infortune is with or looking at the Ascendant and Moon.",
                authority,
            ),
            _clause(
                "saturn_partnership_delay_dissent_or_separation",
                15,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if (
                        _configured(chart.planets[Body.SATURN].sign, asc_sign)
                        or _configured(chart.planets[Body.SATURN].sign, moon.sign)
                    )
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("saturn_sign", chart.planets[Body.SATURN].sign),
                    _measurement("saturn_configures_ascendant", _configured(chart.planets[Body.SATURN].sign, asc_sign)),
                    _measurement("saturn_configures_moon", _configured(chart.planets[Body.SATURN].sign, moon.sign)),
                ),
                "V.20.15 names Saturn with or looking at either point as delay, dissent, or separation testimony under the profile's fixed whole-sign configuration policy.",
                authority,
            ),
            _clause(
                "mars_partnership_conflict",
                16,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if chart.planets[Body.MARS].sign in {asc_sign, moon.sign}
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if (
                        _configured(chart.planets[Body.MARS].sign, asc_sign)
                        or _configured(chart.planets[Body.MARS].sign, moon.sign)
                    )
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("mars_sign", chart.planets[Body.MARS].sign),
                    _measurement("mars_same_sign_with_ascendant_or_moon", chart.planets[Body.MARS].sign in {asc_sign, moon.sign}),
                    _measurement("mars_powerful_place_predicate", "source_not_closed"),
                ),
                "V.20.16's same-sign Mars branch is explicit. Its alternative powerful-place language has no admitted predicate and remains not evaluable when that branch alone is present.",
                authority,
            ),
            _clause(
                "jupiter_trine_or_copresent_benefit",
                17,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if _whole_sign_offset(chart.planets[Body.JUPITER].sign, moon.sign) in (0, 4, 8)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("jupiter_sign", chart.planets[Body.JUPITER].sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("jupiter_moon_offset", _whole_sign_offset(chart.planets[Body.JUPITER].sign, moon.sign)),
                ),
                "V.20.17 preserves Jupiter's trine or copresent benefit and esteem testimony.",
                authority,
            ),
            _clause(
                "venus_trine_best_fortune_testimony",
                18,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if _whole_sign_offset(chart.planets[Body.VENUS].sign, moon.sign) in (4, 8)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("venus_sign", chart.planets[Body.VENUS].sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("venus_moon_offset", _whole_sign_offset(chart.planets[Body.VENUS].sign, moon.sign)),
                ),
                "V.20.18 gives the other fortune's trine testimony without aggregating it into a score.",
                authority,
            ),
            _clause(
                "lesser_fortune_configurations",
                19,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if any(
                        _whole_sign_offset(chart.planets[body].sign, moon.sign) in (2, 3, 6, 9, 10)
                        for body in _FORTUNES
                    )
                    else DorotheusMatterClauseState.CLEAR
                ),
                tuple(
                    _measurement(f"{body.lower()}_moon_offset", _whole_sign_offset(chart.planets[body].sign, moon.sign))
                    for body in _FORTUNES
                ),
                "V.20.19 identifies sextile, square, and opposition fortune testimony as lesser benefit; it is retained as a non-scored witness.",
                authority,
            ),
        )
    )
    return tuple(clauses), angular_places


def _debt_and_payment_clauses(
    chart: ChartContext,
    *,
    authority: str,
) -> tuple[
    tuple[DorotheusMatterClauseWitness, ...],
    tuple[DorotheusAngularPlaceWitness, ...],
]:
    """Evaluate V.21's bounded debt and payment testimony."""

    moon = chart.planets[Body.MOON]
    mercury = chart.planets[Body.MERCURY]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    elongation = _sun_moon_elongation(chart)
    moon_under_rays = (_solar_distance(chart, Body.MOON) or 360.0) <= 15.0
    preferred_signs = frozenset(("Leo", "Pisces", "Aquarius", "Scorpio", "Sagittarius"))
    fortunes_to_moon_or_asc = tuple(
        body
        for body in _FORTUNES + (Body.MERCURY,)
        if _configured(chart.planets[body].sign, moon.sign)
        or _configured(chart.planets[body].sign, asc_sign)
    )
    angular_places = (
        _angular_witness(chart, 1, "creditor_or_lender", "the creditor or lender"),
        _angular_witness(chart, 7, "debtor", "the debtor"),
    )
    return (
        (
            _clause(
                "creditor_debtor_and_debtor_significators",
                1,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("first_place_role", "creditor_or_lender"),
                    _measurement("seventh_place_role", "debtor"),
                    _measurement("moon_sign", moon.sign),
                    _measurement("mercury_sign", mercury.sign),
                ),
                "V.21.1 names the first and seventh places and Moon and Mercury as debt-and-payment significators; their roles are exposed without inferring a creditor identity.",
                authority,
            ),
            _clause(
                "moon_fortune_testimony_and_recurrent_debt",
                2,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.NOT_EVALUABLE
                    if any(_configured(chart.planets[body].sign, moon.sign) for body in _FORTUNES)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("fortune_configuring_moon", ",".join(body for body in _FORTUNES if _configured(chart.planets[body].sign, moon.sign)) or "none"),
                    _measurement("made_unfortunate_predicate", "source_not_closed"),
                ),
                "V.21.2 combines fortune testimony with an undefined made-unfortunate condition and a recurrent-debt outcome. The incomplete compound is not turned into a fabricated gate.",
                authority,
            ),
            _clause(
                "mercury_saturn_confusion_or_deception",
                3,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if _configured(mercury.sign, chart.planets[Body.SATURN].sign)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("mercury_sign", mercury.sign),
                    _measurement("saturn_sign", chart.planets[Body.SATURN].sign),
                    _measurement("mercury_saturn_configured", _configured(mercury.sign, chart.planets[Body.SATURN].sign)),
                ),
                "V.21.3's Mercury-Saturn configuration is explicit confusion or deception testimony under the profile's whole-sign policy.",
                authority,
            ),
            _clause(
                "mercury_mars_conflict",
                4,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if mercury.sign == chart.planets[Body.MARS].sign
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if _configured(mercury.sign, chart.planets[Body.MARS].sign)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("mercury_sign", mercury.sign),
                    _measurement("mars_sign", chart.planets[Body.MARS].sign),
                    _measurement("mercury_mars_same_sign", mercury.sign == chart.planets[Body.MARS].sign),
                    _measurement("powerful_place_predicate", "source_not_closed"),
                ),
                "V.21.4's copresent Mercury-Mars branch is explicit. Its alternative powerful-place branch remains not evaluable.",
                authority,
            ),
            _clause(
                "moon_under_rays_solar_freedom_inquiry",
                5,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_under_rays
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_solar_distance", _solar_distance(chart, Body.MOON), units="degrees"),
                    _measurement("moon_under_rays", moon_under_rays),
                    _measurement("sun_freedom_predicate", "source_not_closed"),
                ),
                "V.21.5 directs the reader to inspect the Sun when the Moon is under rays, but does not supply a closed solar-freedom transfer rule.",
                authority,
            ),
            _clause(
                "burned_places_and_first_degrees",
                6,
                DorotheusMatterClauseRole.GATE,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("moon_degree_in_sign", moon.longitude % 30.0, units="degrees"),
                    _measurement("named_signs", "Leo,Gemini,Sagittarius"),
                    _measurement("burned_place_and_first_degree_intervals", "source_not_closed"),
                ),
                "V.21.6 names burned places and first degrees of three signs without admitting a complete burned-place or degree-interval definition.",
                authority,
            ),
            _clause(
                "waning_moon_in_preferred_debt_signs",
                7,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if moon.sign in preferred_signs and 180.0 < elongation < 360.0
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("preferred_sign", moon.sign in preferred_signs),
                    _measurement("moon_sun_elongation", elongation, units="degrees"),
                    _measurement("moon_waning", 180.0 < elongation < 360.0),
                ),
                "V.21.7 names Leo, Pisces, Aquarius, Scorpio, and Sagittarius with a waning Moon as preferred testimony.",
                authority,
            ),
            _clause(
                "jupiter_venus_mercury_testimony_to_moon_or_ascendant",
                8,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if fortunes_to_moon_or_asc
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("qualifying_bodies", ",".join(fortunes_to_moon_or_asc) or "none"),
                ),
                "V.21.8 preserves the stated Jupiter, Venus, or Mercury testimony as best for the matter without assigning a numeric rank.",
                authority,
            ),
        ),
        angular_places,
    )


def _writing_a_will_clauses(
    chart: ChartContext,
    *,
    moon_latitude_rate_degrees_per_day: float,
    moon_true_longitude_mean_ecliptic_degrees: float,
    authority: str,
) -> tuple[DorotheusMatterClauseWitness, ...]:
    """Preserve V.43's will-writing testimony and its unresolved connections."""

    moon = chart.planets[Body.MOON]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    elongation = _sun_moon_elongation(chart)
    _, lunar_equation, calculation_direction = _lunar_calculation(chart, moon_true_longitude_mean_ecliptic_degrees)
    moon_under_rays = (_solar_distance(chart, Body.MOON) or 360.0) <= 15.0
    return (
        _clause(
            "avoid_convertible_signs",
            1,
            DorotheusMatterClauseRole.GATE,
            (
                DorotheusMatterClauseState.TRIGGERED
                if asc_sign in _TWIN_SIGNS or moon.sign in _TWIN_SIGNS
                else DorotheusMatterClauseState.CLEAR
            ),
            (
                _measurement("ascendant_sign", asc_sign),
                _measurement("moon_sign", moon.sign),
                _measurement("convertible_signs", "Gemini,Virgo,Sagittarius,Pisces"),
            ),
            "V.43.1, with note 387's correction, directs avoidance of convertible signs; the named Dorothean twin-sign set is exposed directly.",
            authority,
        ),
        _clause(
            "lunar_growth_calculation_latitude_and_stationary_connection",
            2,
            DorotheusMatterClauseRole.FORTIFIER,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_sun_elongation", elongation, units="degrees"),
                _measurement("moon_increasing_in_glow", 0.0 < elongation < 180.0),
                _measurement("lunar_equation", lunar_equation, units="degrees"),
                _measurement("calculation_direction", calculation_direction),
                _measurement("moon_latitude_rate", moon_latitude_rate_degrees_per_day, units="degrees/day"),
                _measurement("moon_northward", moon_latitude_rate_degrees_per_day > 0.0),
                _measurement("moon_under_rays", moon_under_rays),
                _measurement("stationary_star_connection", "source_degree_interval_not_closed"),
            ),
            "V.43.2 combines computable lunar motion witnesses with an unspecified connection to a stationary star. The connection interval is not invented, so the compound remains not evaluable.",
            f"{authority}; {_AUTHORITY_CALCULATION}; {_AUTHORITY_MEAN_LUNAR_LONGITUDE}; {_AUTHORITY_CONNECTION}",
        ),
        _clause(
            "connected_star_under_rays",
            3,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_under_rays", moon_under_rays),
                _measurement("connected_star", "source_connection_not_closed"),
                _measurement("star_under_rays", "source_connection_not_closed"),
            ),
            "V.43.3 depends on the same unspecified connected star, so no under-rays result is fabricated.",
            authority,
        ),
        _clause(
            "mars_configuration_damage",
            4,
            DorotheusMatterClauseRole.GATE,
            (
                DorotheusMatterClauseState.TRIGGERED
                if _configured(chart.planets[Body.MARS].sign, asc_sign)
                or _configured(chart.planets[Body.MARS].sign, moon.sign)
                else DorotheusMatterClauseState.CLEAR
            ),
            (
                _measurement("mars_sign", chart.planets[Body.MARS].sign),
                _measurement("mars_configures_ascendant", _configured(chart.planets[Body.MARS].sign, asc_sign)),
                _measurement("mars_configures_moon", _configured(chart.planets[Body.MARS].sign, moon.sign)),
            ),
            "V.43.4's Mars testimony is preserved using the profile's explicit whole-sign configuration policy.",
            authority,
        ),
        _clause(
            "saturn_configuration_damage",
            5,
            DorotheusMatterClauseRole.GATE,
            (
                DorotheusMatterClauseState.TRIGGERED
                if _configured(chart.planets[Body.SATURN].sign, asc_sign)
                or _configured(chart.planets[Body.SATURN].sign, moon.sign)
                else DorotheusMatterClauseState.CLEAR
            ),
            (
                _measurement("saturn_sign", chart.planets[Body.SATURN].sign),
                _measurement("saturn_configures_ascendant", _configured(chart.planets[Body.SATURN].sign, asc_sign)),
                _measurement("saturn_configures_moon", _configured(chart.planets[Body.SATURN].sign, moon.sign)),
            ),
            "V.43.5's Saturn testimony is preserved using the same declared configuration policy.",
            authority,
        ),
        _clause(
            "jupiter_or_venus_configuration_benefit",
            6,
            DorotheusMatterClauseRole.FORTIFIER,
            (
                DorotheusMatterClauseState.SATISFIED
                if any(
                    _configured(chart.planets[body].sign, asc_sign)
                    or _configured(chart.planets[body].sign, moon.sign)
                    for body in _FORTUNES
                )
                else DorotheusMatterClauseState.CLEAR
            ),
            tuple(
                _measurement(
                    f"{body.lower()}_configures_ascendant_or_moon",
                    _configured(chart.planets[body].sign, asc_sign)
                    or _configured(chart.planets[body].sign, moon.sign),
                )
                for body in _FORTUNES
            ),
            "V.43.6's Jupiter or Venus testimony remains a source fortifier, not a recommendation score.",
            authority,
        ),
    )


def _horizon_hemisphere(
    chart: ChartContext,
    body: str,
) -> tuple[str | None, int | None, str]:
    """Classify a body against the local horizon only from a quadrant figure."""

    houses = chart.houses
    if houses is None or not houses.is_quadrant_system:
        return None, None, "quadrant_house_figure_required"
    longitude = chart.planets[body].longitude
    horizon_distance = min(
        abs((longitude - houses.asc + 180.0) % 360.0 - 180.0),
        abs((longitude - houses.dsc + 180.0) % 360.0 - 180.0),
    )
    if horizon_distance <= _PHASE_BOUNDARY_TOLERANCE_DEG:
        return None, None, "exact_horizon_not_evaluable"
    placement = assign_house(longitude, houses)
    return (
        "above_earth" if placement.house in (7, 8, 9, 10, 11, 12) else "under_earth",
        placement.house,
        "quadrant_house_horizon_classification",
    )


def _ship_launch_clauses(
    chart: ChartContext,
    *,
    natal_chart: ChartContext | None,
    authority: str,
) -> tuple[DorotheusMatterClauseWitness, ...]:
    """Preserve all V.26 launch paragraphs without collapsing open readings."""

    moon = chart.planets[Body.MOON]
    sun = chart.planets[Body.SUN]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    moon_hemisphere, moon_house, horizon_policy = _horizon_hemisphere(chart, Body.MOON)
    saturn_hemisphere, saturn_house, _ = _horizon_hemisphere(chart, Body.SATURN)
    mars_hemisphere, mars_house, _ = _horizon_hemisphere(chart, Body.MARS)
    saturn_stationary, saturn_station_threshold = _stationary_witness(chart, Body.SATURN)
    fortune_or_infortune_to_moon = tuple(
        body
        for body in _FORTUNES + _INFORTUNES
        if _configured(chart.planets[body].sign, moon.sign)
    )
    table_applicable = not fortune_or_infortune_to_moon
    malefic_to_moon = tuple(
        body
        for body in _INFORTUNES
        if _configured(chart.planets[body].sign, moon.sign)
    )
    moon_degree = moon.longitude % 30.0
    moon_under_rays = (_solar_distance(chart, Body.MOON) or 360.0) <= 15.0
    venus_under_rays = (_solar_distance(chart, Body.VENUS) or 360.0) <= 15.0

    table_rows = (
        ("Aries", "aries_first_ten_degrees_above_earth", DorotheusMatterClauseRole.FORTIFIER, "first_ten"),
        ("Taurus", "taurus_surge_and_malefic_destruction", DorotheusMatterClauseRole.WITNESS, "plain"),
        ("Gemini", "gemini_eight_degree_cargo_and_return", DorotheusMatterClauseRole.WITNESS, "eight_degree"),
        ("Cancer", "cancer_safe_benefit", DorotheusMatterClauseRole.FORTIFIER, "plain"),
        ("Leo", "leo_people_harm", DorotheusMatterClauseRole.WITNESS, "plain"),
        ("Virgo", "virgo_unplanned_or_fast_return", DorotheusMatterClauseRole.WITNESS, "plain"),
        ("Libra", "libra_first_ten_degrees_no_good", DorotheusMatterClauseRole.GATE, "first_ten"),
        ("Scorpio", "scorpio_safety_with_inward_fear", DorotheusMatterClauseRole.WITNESS, "plain"),
        ("Sagittarius", "sagittarius_surge_disaster", DorotheusMatterClauseRole.GATE, "plain"),
        ("Capricorn", "capricorn_after_nine_degrees_suitability", DorotheusMatterClauseRole.FORTIFIER, "after_nine"),
        ("Aquarius", "aquarius_dissent_slow_return_good_outcome", DorotheusMatterClauseRole.WITNESS, "plain"),
        ("Pisces", "pisces_calamity", DorotheusMatterClauseRole.GATE, "plain"),
    )
    clauses: list[DorotheusMatterClauseWitness] = []
    for order, (sign, clause_id, role, degree_rule) in enumerate(table_rows, start=1):
        matched = moon.sign == sign
        if sign == "Taurus" and matched and malefic_to_moon:
            state = DorotheusMatterClauseState.TRIGGERED
            role = DorotheusMatterClauseRole.GATE
        elif not table_applicable:
            state = DorotheusMatterClauseState.NOT_EVALUABLE
        elif not matched:
            state = DorotheusMatterClauseState.CLEAR
        elif degree_rule == "eight_degree":
            state = DorotheusMatterClauseState.NOT_EVALUABLE
        elif degree_rule == "first_ten":
            if abs(moon_degree - 10.0) <= _PHASE_BOUNDARY_TOLERANCE_DEG:
                state = DorotheusMatterClauseState.NOT_EVALUABLE
            elif sign == "Libra" and moon_degree < 10.0:
                state = DorotheusMatterClauseState.TRIGGERED
            elif sign == "Aries" and moon_degree < 10.0:
                state = DorotheusMatterClauseState.SATISFIED
            else:
                state = DorotheusMatterClauseState.CLEAR
        elif degree_rule == "after_nine":
            if abs(moon_degree - 9.0) <= _PHASE_BOUNDARY_TOLERANCE_DEG:
                state = DorotheusMatterClauseState.NOT_EVALUABLE
            else:
                state = (
                    DorotheusMatterClauseState.SATISFIED
                    if moon_degree > 9.0
                    else DorotheusMatterClauseState.CLEAR
                )
        elif role is DorotheusMatterClauseRole.GATE:
            state = DorotheusMatterClauseState.TRIGGERED
        elif role is DorotheusMatterClauseRole.FORTIFIER:
            state = DorotheusMatterClauseState.SATISFIED
        else:
            state = DorotheusMatterClauseState.OBSERVED
        clauses.append(
            _clause(
                clause_id,
                order,
                role,
                state,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("table_sign", sign),
                    _measurement("moon_degree_in_sign", moon_degree, units="degrees"),
                    _measurement("table_requires_no_fortune_or_infortune_testimony", table_applicable),
                    _measurement("fortune_or_infortune_configuring_moon", ",".join(fortune_or_infortune_to_moon) or "none"),
                    _measurement("malefic_configuring_moon", ",".join(malefic_to_moon) or "none"),
                    _measurement("degree_rule", degree_rule),
                ),
                "V.26.%d is one entry in the launch-sign table. Its stated no-fortune/no-infortune precondition and any unresolved degree wording remain explicit." % order,
                authority,
            )
        )
    clauses.extend(
        (
            _clause(
                "launch_sign_table_precondition",
                13,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if table_applicable
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                ),
                (
                    _measurement("configured_fortunes_or_infortunes", ",".join(fortune_or_infortune_to_moon) or "none"),
                    _measurement("table_applicable", table_applicable),
                ),
                "V.26.13 states the table's absence-of-fortune-and-infortune condition. A table result is not silently applied when that condition fails.",
                authority,
            ),
            _clause(
                "launch_transition_to_planetary_testimony",
                14,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("launch_context", "pushing_ship_into_water"),
                ),
                "V.26.14 begins the distinct planetary testimony following the launch-sign table.",
                authority,
            ),
            _clause(
                "moon_under_earth_configured_by_planets",
                15,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if moon_hemisphere == "under_earth" and fortune_or_infortune_to_moon
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("moon_house", moon_house),
                    _measurement("horizon_policy", horizon_policy),
                    _measurement("configuring_fortunes_or_infortunes", ",".join(fortune_or_infortune_to_moon) or "none"),
                ),
                "V.26.15's under-earth and planetary-configuration condition is evaluated only from an actual quadrant horizon figure.",
                authority,
            ),
            _clause(
                "under_earth_moon_stationary_saturn_copresence",
                16,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if moon_hemisphere == "under_earth" and saturn_stationary and chart.planets[Body.SATURN].sign == moon.sign
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("saturn_sign", chart.planets[Body.SATURN].sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("saturn_stationary", saturn_stationary),
                    _measurement("station_threshold", saturn_station_threshold, units="degrees/day"),
                ),
                "V.26.16's stationary Saturn and same-sign Moon testimony is retained with the declared instantaneous station policy.",
                authority,
            ),
            _clause(
                "above_earth_moon_stationary_saturn_trine",
                17,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("saturn_stationary", saturn_stationary),
                    _measurement("saturn_moon_offset", _whole_sign_offset(chart.planets[Body.SATURN].sign, moon.sign)),
                    _measurement("edition_reading", "source_internal_hemisphere_contradiction"),
                ),
                "V.26.17 contains an unresolved hemisphere contradiction in the translated wording; the evidence is exposed but no branch is chosen.",
                authority,
            ),
            _clause(
                "above_earth_moon_nonstationary_saturn_trine",
                18,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if moon_hemisphere == "above_earth" and not saturn_stationary and _whole_sign_offset(chart.planets[Body.SATURN].sign, moon.sign) in (4, 8)
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("saturn_stationary", saturn_stationary),
                    _measurement("saturn_moon_offset", _whole_sign_offset(chart.planets[Body.SATURN].sign, moon.sign)),
                ),
                "V.26.18's editorially corrected non-stationary Saturn trine is retained as an unscored injury witness.",
                authority,
            ),
            _clause(
                "saturn_mercury_association_and_planetary_help",
                19,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("saturn_mercury_configured", _configured(chart.planets[Body.SATURN].sign, chart.planets[Body.MERCURY].sign)),
                    _measurement("source_association_scope", "source_not_closed"),
                ),
                "V.26.19's association and planetary-help language has no closed configuration scope in the cited passage.",
                authority,
            ),
            _clause(
                "saturn_at_ascendant_and_moon_not_looking",
                20,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if chart.planets[Body.SATURN].sign == asc_sign and not _configured(chart.planets[Body.SATURN].sign, moon.sign)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("saturn_sign", chart.planets[Body.SATURN].sign),
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("saturn_configures_moon", _configured(chart.planets[Body.SATURN].sign, moon.sign)),
                ),
                "V.26.20's Ascendant-Saturn and Moon non-testimony is preserved as a source witness.",
                authority,
            ),
            _clause(
                "radical_saturn_sign_overlay",
                21,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.NOT_EVALUABLE
                    if natal_chart is None
                    else DorotheusMatterClauseState.TRIGGERED
                    if (
                        asc_sign == natal_chart.planets[Body.SATURN].sign
                        or _hard_aspect_name(chart.planets[Body.SATURN].sign, natal_chart.planets[Body.SATURN].sign) is not None
                    )
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("election_ascendant_sign", asc_sign),
                    _measurement("transiting_saturn_sign", chart.planets[Body.SATURN].sign),
                    _measurement("natal_saturn_sign", None if natal_chart is None else natal_chart.planets[Body.SATURN].sign),
                    _measurement("radical_chart_supplied", natal_chart is not None),
                ),
                "V.26.21 is profile-owned radical overlay testimony. It remains not evaluable for an ephemeral chart rather than manufacturing natal data.",
                authority,
            ),
            _clause(
                "mars_under_earth_moon_above_earth_water_or_fighting",
                22,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if mars_hemisphere == "under_earth" and moon_hemisphere == "above_earth" and _configured(chart.planets[Body.MARS].sign, moon.sign)
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if mars_hemisphere is None or moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("mars_hemisphere", mars_hemisphere),
                    _measurement("mars_house", mars_house),
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("moon_house", moon_house),
                    _measurement("mars_configures_moon", _configured(chart.planets[Body.MARS].sign, moon.sign)),
                ),
                "V.26.22 distinguishes the water and fighting outcomes without translating them into a unified risk score.",
                authority,
            ),
            _clause(
                "mars_condition_injury_consequence",
                23,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("dependent_clause", "mars_under_earth_moon_above_earth_water_or_fighting"),
                    _measurement("source_injury_scope", "continuation_not_separable"),
                ),
                "V.26.23 continues the preceding Mars condition but does not supply a separable independent predicate.",
                authority,
            ),
            _clause(
                "mercury_with_mars_increases_hardship",
                24,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if _configured(chart.planets[Body.MERCURY].sign, chart.planets[Body.MARS].sign)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("mercury_mars_configured", _configured(chart.planets[Body.MERCURY].sign, chart.planets[Body.MARS].sign)),
                ),
                "V.26.24's Mercury-Mars hardship increase is preserved as a qualitative witness.",
                authority,
            ),
            _clause(
                "saturn_mars_mercury_look_at_moon_above_earth",
                25,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if moon_hemisphere == "above_earth" and all(_configured(chart.planets[body].sign, moon.sign) for body in (Body.SATURN, Body.MARS, Body.MERCURY))
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                tuple(
                    _measurement(f"{body.lower()}_configures_moon", _configured(chart.planets[body].sign, moon.sign))
                    for body in (Body.SATURN, Body.MARS, Body.MERCURY)
                ) + (_measurement("moon_hemisphere", moon_hemisphere),),
                "V.26.25's no-escape testimony requires all three named planetary configurations and an above-earth Moon.",
                authority,
            ),
            _clause(
                "mars_mercury_association_analogy",
                26,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("mars_mercury_configured", _configured(chart.planets[Body.MARS].sign, chart.planets[Body.MERCURY].sign)),
                    _measurement("analogy_target", "preceding_mars_condition_scope_not_closed"),
                ),
                "V.26.26 says the Mars-Mercury association is analogous to an antecedent condition whose full scope is not separable in the passage.",
                authority,
            ),
            _clause(
                "mars_saturn_divided_solar_lunar_testimony",
                27,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if (
                        (_configured(chart.planets[Body.MARS].sign, sun.sign) and _configured(chart.planets[Body.SATURN].sign, moon.sign))
                        or (_configured(chart.planets[Body.SATURN].sign, sun.sign) and _configured(chart.planets[Body.MARS].sign, moon.sign))
                    )
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("mars_configures_sun", _configured(chart.planets[Body.MARS].sign, sun.sign)),
                    _measurement("mars_configures_moon", _configured(chart.planets[Body.MARS].sign, moon.sign)),
                    _measurement("saturn_configures_sun", _configured(chart.planets[Body.SATURN].sign, sun.sign)),
                    _measurement("saturn_configures_moon", _configured(chart.planets[Body.SATURN].sign, moon.sign)),
                ),
                "V.26.27's divided Mars-Saturn solar/lunar testimony is a source gate; opposition remains visible through the common configuration policy rather than receiving an invented extra weight.",
                authority,
            ),
            _clause(
                "jupiter_square_reading_and_moon_unafflicted",
                28,
                DorotheusMatterClauseRole.FORTIFIER,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("jupiter_moon_offset", _whole_sign_offset(chart.planets[Body.JUPITER].sign, moon.sign)),
                    _measurement("moon_made_unfortunate", "source_not_closed"),
                    _measurement("edition_note_161", "jupiter_square_epithet_not_predicate"),
                ),
                "V.26.28 cannot be narrowed to a Jupiter-square rule: note 161 rejects that apparent predicate and the Moon-unafflicted term is not closed.",
                authority,
            ),
            _clause(
                "venus_jupiter_and_moon_testimony",
                29,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("venus_jupiter_configured", _configured(chart.planets[Body.VENUS].sign, chart.planets[Body.JUPITER].sign)),
                    _measurement("depends_on_v26_28", True),
                ),
                "V.26.29 depends on the unresolved preceding reading and is therefore retained as not evaluable.",
                authority,
            ),
            _clause(
                "mercury_with_fortune_or_infortune_addition",
                30,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("mercury_configures_fortune", any(_configured(chart.planets[Body.MERCURY].sign, chart.planets[body].sign) for body in _FORTUNES)),
                    _measurement("mercury_configures_infortune", any(_configured(chart.planets[Body.MERCURY].sign, chart.planets[body].sign) for body in _INFORTUNES)),
                    _measurement("source_addition_outcome", "context_not_closed"),
                ),
                "V.26.30 says Mercury adds good or evil to the context but does not provide an independent outcome rule.",
                authority,
            ),
            _clause(
                "above_earth_moon_venus_alone_looks",
                31,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if moon_hemisphere == "above_earth" and _configured(chart.planets[Body.VENUS].sign, moon.sign) and not any(_configured(chart.planets[body].sign, moon.sign) for body in _INFORTUNES)
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("venus_configures_moon", _configured(chart.planets[Body.VENUS].sign, moon.sign)),
                    _measurement("infortune_configuring_moon", ",".join(malefic_to_moon) or "none"),
                ),
                "V.26.31 preserves Venus-alone testimony only when the quadrant horizon condition is actually available.",
                authority,
            ),
            _clause(
                "under_earth_moon_venus_copresence_under_rays",
                32,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if moon_hemisphere == "under_earth" and chart.planets[Body.VENUS].sign == moon.sign and venus_under_rays
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if moon_hemisphere is None
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_hemisphere", moon_hemisphere),
                    _measurement("venus_moon_same_sign", chart.planets[Body.VENUS].sign == moon.sign),
                    _measurement("venus_under_rays", venus_under_rays),
                ),
                "V.26.32's below-earth Venus condition is not approximated from a non-quadrant house system.",
                authority,
            ),
            _clause(
                "jupiter_venus_solar_lunar_and_mercury_testimony",
                33,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if all(_configured(chart.planets[body].sign, target.sign) for body in _FORTUNES for target in (sun, moon)) and _configured(moon.sign, chart.planets[Body.MERCURY].sign)
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("jupiter_configures_sun", _configured(chart.planets[Body.JUPITER].sign, sun.sign)),
                    _measurement("jupiter_configures_moon", _configured(chart.planets[Body.JUPITER].sign, moon.sign)),
                    _measurement("venus_configures_sun", _configured(chart.planets[Body.VENUS].sign, sun.sign)),
                    _measurement("venus_configures_moon", _configured(chart.planets[Body.VENUS].sign, moon.sign)),
                    _measurement("mercury_configures_moon", _configured(chart.planets[Body.MERCURY].sign, moon.sign)),
                ),
                "V.26.33 preserves the chapter's combined benefic and Mercury testimony without converting best into a numeric grade.",
                authority,
            ),
            _clause(
                "mixed_malefic_ascendant_and_fortune_moon_rescue",
                34,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("infortune_configures_ascendant", any(_configured(chart.planets[body].sign, asc_sign) for body in _INFORTUNES)),
                    _measurement("fortune_configures_moon", any(_configured(chart.planets[body].sign, moon.sign) for body in _FORTUNES)),
                    _measurement("source_rescue_relation", "mixed_outcome_not_closed"),
                ),
                "V.26.34 combines harm and rescue language without a source-provided precedence rule, so it remains a visible mixed witness.",
                authority,
            ),
            _clause(
                "reported_signs_testimony",
                35,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (_measurement("reported_signs", "antecedent_reference_not_identified"),),
                "V.26.35 refers to signs reported earlier without an unambiguous local table reference.",
                authority,
            ),
            _clause(
                "approved_signs_testimony",
                36,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (_measurement("approved_signs", "antecedent_reference_not_identified"),),
                "V.26.36 refers to approved signs without a closed antecedent set in the chapter.",
                authority,
            ),
            _clause(
                "launch_moment_distinguished_from_passenger_boarding",
                37,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (_measurement("elected_moment", "pushing_ship_into_water"), _measurement("passenger_boarding", "separate_unprofiled_moment")),
                "V.26.37 makes the launch moment distinct from passenger boarding. This profile evaluates only the stated ship-launch moment.",
                authority,
            ),
            _clause(
                "arrival_wording",
                38,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (_measurement("arrival_predicate", "source_wording_not_closed"),),
                "V.26.38's arrival wording does not close a separate arrival predicate, so no such product is implied.",
                authority,
            ),
        )
    )
    return tuple(clauses)


def _travel_sign_nature_authority(
    policy: DorotheusMatterProfilePolicy,
) -> str:
    if (
        policy.sign_nature_variant
        is DorotheusSignNatureVariant.LILLY_1647_ELEMENTAL_QUALITIES
    ):
        return _AUTHORITY_LILLY_1647_SIGN_QUALITIES
    return (
        "Dorotheus V.26.39-40 names dry and dry-earthy signs without "
        "enumerating their members; the source-faithful variant leaves that "
        "class indeterminate."
    )


def _configured_to_any_sign(body_sign: str, signs: frozenset[str]) -> bool:
    return any(_configured(body_sign, sign) for sign in signs)


def _land_travel_clauses(
    chart: ChartContext,
    *,
    authority: str,
    policy: DorotheusMatterProfilePolicy,
) -> tuple[DorotheusMatterClauseWitness, ...]:
    """Preserve V.26.39-43's land-travel branch without filling open doctrine."""

    moon = chart.planets[Body.MOON]
    moon_place = _whole_sign_place(chart, Body.MOON)
    dry_signs = (
        _LILLY_1647_DRY_SIGNS
        if policy.sign_nature_variant
        is DorotheusSignNatureVariant.LILLY_1647_ELEMENTAL_QUALITIES
        else None
    )
    policy_authority = _travel_sign_nature_authority(policy)
    clause_authority = f"{authority}; {policy_authority}"
    dry_infortunes = (
        tuple(
            body
            for body in _INFORTUNES
            if chart.planets[body].sign in dry_signs
            or _configured_to_any_sign(chart.planets[body].sign, dry_signs)
        )
        if dry_signs is not None
        else ()
    )
    fortunes_to_mars = tuple(
        body
        for body in _FORTUNES
        if _configured(chart.planets[body].sign, chart.planets[Body.MARS].sign)
    )
    moon_bound = egyptian_bound_of(
        moon.longitude,
        policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN),
    )
    malefic_hard_aspects = tuple(
        body
        for body in _INFORTUNES
        if _hard_aspect_name(chart.planets[body].sign, moon.sign) is not None
    )
    fortunes_to_moon = tuple(
        body
        for body in _FORTUNES
        if _configured(chart.planets[body].sign, moon.sign)
    )

    if moon_place != 7:
        land_impediment = DorotheusMatterClauseState.CLEAR
    elif dry_signs is None:
        land_impediment = DorotheusMatterClauseState.NOT_EVALUABLE
    elif moon.sign in dry_signs or not dry_infortunes:
        land_impediment = DorotheusMatterClauseState.CLEAR
    else:
        land_impediment = DorotheusMatterClauseState.TRIGGERED

    return (
        _clause(
            "land_travel_moon_seventh_non_dry_with_infortunes_dry",
            1,
            DorotheusMatterClauseRole.GATE,
            land_impediment,
            (
                _measurement("sign_nature_variant", policy.sign_nature_variant.value),
                _measurement("moon_whole_sign_place", moon_place),
                _measurement("moon_sign", moon.sign),
                _measurement(
                    "moon_in_lilly_dry_sign",
                    None if dry_signs is None else moon.sign in dry_signs,
                ),
                _measurement(
                    "infortunes_in_or_configuring_dry_signs",
                    None if dry_signs is None else ",".join(dry_infortunes) or "none",
                ),
            ),
            "V.26.39's land branch requires the Moon in the seventh, outside a dry sign, with an infortune in or configuring a dry sign. The dry-sign class is evaluated only under the named Lilly variant.",
            clause_authority,
        ),
        _clause(
            "land_travel_unafflicted_moon_and_fortunes_dry_earthy",
            2,
            DorotheusMatterClauseRole.FORTIFIER,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("sign_nature_variant", policy.sign_nature_variant.value),
                _measurement("dry_earthy_fortune_testimony", "source_not_evaluated"),
                _measurement("moon_not_made_unfortunate", "source_not_closed"),
            ),
            "V.26.40 preserves its land-travel fortification without converting the edition's non-exclusive made-unfortunate wording into a hidden test. The dry-earthy class remains source-faithful indeterminate unless the named Lilly variant is selected.",
            clause_authority,
        ),
        _clause(
            "land_travel_owner_death_years_unknown",
            3,
            DorotheusMatterClauseRole.WITNESS,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("travel_owners_nativities", "not_supplied"),
                _measurement("death_years_judgement", "source_requires_individual_nativities"),
            ),
            "V.26.41 refers to the travel owners' death judgement and years. A single election moment cannot invent those individual natal determinations.",
            authority,
        ),
        _clause(
            "land_travel_mars_harshness_and_fortune_absence",
            4,
            DorotheusMatterClauseRole.WITNESS,
            DorotheusMatterClauseState.OBSERVED,
            (
                _measurement("principal_infortune", Body.MARS),
                _measurement("fortunes_configuring_mars", ",".join(fortunes_to_mars) or "none"),
                _measurement("jupiter_or_venus_not_looking_at_mars", not fortunes_to_mars),
            ),
            "V.26.42 names Mars as the harshest infortune for land travel and intensifies that testimony when neither fortune looks at Mars. The passage does not supply a complete inverse safety rule, so this remains an unscored witness.",
            authority,
        ),
        _clause(
            "travel_moon_in_infortune_bound_and_face_hard_aspected_without_fortune",
            5,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_egyptian_bound_ruler", moon_bound.ruler),
                _measurement("moon_in_infortune_bound", moon_bound.ruler in _INFORTUNES),
                _measurement("moon_face_ruler", "source_not_admitted"),
                _measurement("infortunes_square_or_opposing_moon", ",".join(malefic_hard_aspects) or "none"),
                _measurement("fortunes_configuring_moon", ",".join(fortunes_to_moon) or "none"),
            ),
            "V.26.43 requires both infortune bound and face. Egyptian bounds are explicit, but no V.26-owned face table has been admitted; the full compound gate therefore remains not evaluable.",
            f"{authority}; {_AUTHORITY_EGYPTIAN_BOUNDS}",
        ),
    )


def _sea_travel_clauses(
    chart: ChartContext,
    *,
    authority: str,
    policy: DorotheusMatterProfilePolicy,
) -> tuple[DorotheusMatterClauseWitness, ...]:
    """Preserve V.26.39, 42, and 43's sea-travel branch."""

    moon = chart.planets[Body.MOON]
    water_infortunes = tuple(
        body
        for body in _INFORTUNES
        if chart.planets[body].sign in _WATERY_SIGNS
        or _configured_to_any_sign(chart.planets[body].sign, _WATERY_SIGNS)
    )
    sea_impediment = (
        DorotheusMatterClauseState.TRIGGERED
        if moon.sign not in _WATERY_SIGNS and water_infortunes
        else DorotheusMatterClauseState.CLEAR
    )
    fortunes_to_saturn = tuple(
        body
        for body in _FORTUNES
        if _configured(chart.planets[body].sign, chart.planets[Body.SATURN].sign)
    )
    moon_bound = egyptian_bound_of(
        moon.longitude,
        policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN),
    )
    malefic_hard_aspects = tuple(
        body
        for body in _INFORTUNES
        if _hard_aspect_name(chart.planets[body].sign, moon.sign) is not None
    )
    fortunes_to_moon = tuple(
        body
        for body in _FORTUNES
        if _configured(chart.planets[body].sign, moon.sign)
    )

    return (
        _clause(
            "sea_travel_moon_nonwatery_with_infortunes_water",
            1,
            DorotheusMatterClauseRole.GATE,
            sea_impediment,
            (
                _measurement("sign_nature_variant", policy.sign_nature_variant.value),
                _measurement("moon_sign", moon.sign),
                _measurement("moon_in_dorotheus_water_sign", moon.sign in _WATERY_SIGNS),
                _measurement("infortunes_in_or_configuring_water_signs", ",".join(water_infortunes) or "none"),
            ),
            "V.26.39's sea branch is evaluated from Dorotheus's named water-sign set: the Moon outside a water sign with an infortune in or configuring one is an impediment.",
            f"{authority}; {_AUTHORITY_WATERY_SIGNS}",
        ),
        _clause(
            "sea_travel_saturn_harshness_and_fortune_absence",
            2,
            DorotheusMatterClauseRole.WITNESS,
            DorotheusMatterClauseState.OBSERVED,
            (
                _measurement("principal_infortune", Body.SATURN),
                _measurement("fortunes_configuring_saturn", ",".join(fortunes_to_saturn) or "none"),
                _measurement("jupiter_or_venus_not_looking_at_saturn", not fortunes_to_saturn),
            ),
            "V.26.42 names Saturn as the harshest infortune for sea travel and intensifies the testimony when neither fortune looks at Saturn. It remains an unscored witness rather than an invented inverse safety rule.",
            authority,
        ),
        _clause(
            "travel_moon_in_infortune_bound_and_face_hard_aspected_without_fortune",
            3,
            DorotheusMatterClauseRole.GATE,
            DorotheusMatterClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_egyptian_bound_ruler", moon_bound.ruler),
                _measurement("moon_in_infortune_bound", moon_bound.ruler in _INFORTUNES),
                _measurement("moon_face_ruler", "source_not_admitted"),
                _measurement("infortunes_square_or_opposing_moon", ",".join(malefic_hard_aspects) or "none"),
                _measurement("fortunes_configuring_moon", ",".join(fortunes_to_moon) or "none"),
            ),
            "V.26.43 requires both infortune bound and face. The V.26 source does not close the face table, so this compound gate remains not evaluable.",
            f"{authority}; {_AUTHORITY_EGYPTIAN_BOUNDS}",
        ),
    )


def evaluate_dorotheus_matter_profile(
    chart: ChartContext,
    *,
    profile_id: DorotheusMatterProfileId,
    moon_condition: DorotheusMoonConditionEvaluation,
    rooted_context: DorotheusRootedContextEvaluation | None,
    moon_connection_flow: MoonConnectionFlow | None = None,
    moon_latitude_rate_degrees_per_day: float,
    moon_true_longitude_mean_ecliptic_degrees: float | None = None,
    natal_chart: ChartContext | None = None,
    reader_provenance: str,
    policy: DorotheusMatterProfilePolicy | None = None,
) -> DorotheusMatterProfileEvaluation:
    """Evaluate one source-closed Dorothean matter layer without scoring."""

    profile_id = DorotheusMatterProfileId(profile_id)
    resolved_policy = _POLICIES[profile_id] if policy is None else policy
    if resolved_policy.profile_id is not profile_id:
        raise ValueError("policy identity must match requested profile")
    if not math.isfinite(moon_latitude_rate_degrees_per_day):
        raise ValueError("Moon latitude rate must be finite")
    calculation_profiles = {
        DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
        DorotheusMatterProfileId.TRAVEL,
        DorotheusMatterProfileId.SHIP_CONSTRUCTION,
        DorotheusMatterProfileId.WRITING_A_WILL,
    }
    if profile_id in calculation_profiles:
        if (
            moon_true_longitude_mean_ecliptic_degrees is None
            or not math.isfinite(moon_true_longitude_mean_ecliptic_degrees)
            or not 0.0 <= moon_true_longitude_mean_ecliptic_degrees < 360.0
        ):
            raise ValueError(
                "this profile requires Moon true longitude in the mean ecliptic"
            )
    elif moon_true_longitude_mean_ecliptic_degrees is not None:
        raise ValueError(
            "Moon true longitude in the mean ecliptic belongs only to calculation-based profiles"
        )
    if chart.houses is None:
        raise ValueError("matter profiles require a house figure")
    if moon_condition.jd_ut != chart.jd_ut:
        raise ValueError("all inherited layers must describe the same instant")
    authority = _AUTHORITIES[profile_id]
    if profile_id is DorotheusMatterProfileId.SHIP_LAUNCH:
        if natal_chart is not None and natal_chart.houses is None:
            raise ValueError("V.26 natal overlay requires a complete natal chart")
    elif natal_chart is not None:
        raise ValueError("natal chart belongs only to the V.26 ship-launch overlay")
    if (
        profile_id in _UNROOTED_EPHEMERAL_PROFILES
        and rooted_context is not None
    ):
        raise ValueError(
            "this source-unrooted profile rejects an invented V.31 rooted matter family"
        )
    if profile_id is DorotheusMatterProfileId.TRAVEL:
        if moon_connection_flow is not None:
            raise ValueError("V.22 travel does not admit a lunar-flow window")
        if moon_true_longitude_mean_ecliptic_degrees is None:
            raise AssertionError("travel calculation input was validated above")
        moon = chart.planets[Body.MOON]
        asc_sign, _, _ = sign_of(chart.houses.asc)
        asc_lord = DOMICILE_RULERS[asc_sign]
        moon_lord = DOMICILE_RULERS[moon.sign]
        asc_lord_placement = _placement(
            chart,
            asc_lord,
            role="V.22 lord_of_ascendant_falling",
        )
        moon_lord_placement = _placement(
            chart,
            moon_lord,
            role="V.22 lord_of_moon_falling",
        )
        strengths = (asc_lord_placement, moon_lord_placement)
        angular_places = (
            _angular_witness(chart, 1, "traveler", "the traveler"),
            _angular_witness(chart, 7, "destination_land", "the land sought"),
            _angular_witness(chart, 10, "business_or_needed_thing", "the work or needed thing sought in travel"),
            _angular_witness(chart, 4, "outcome", "the outcome of the matter"),
        )
        mean_lunar_longitude, lunar_equation, calculation_direction = (
            _lunar_calculation(
                chart,
                float(moon_true_longitude_mean_ecliptic_degrees),
            )
        )
        moon_increasing = lunar_equation > 0.0
        mercury = chart.planets[Body.MERCURY]
        mercury_solar_distance = _solar_distance(chart, Body.MERCURY)
        mercury_under_rays = (
            mercury_solar_distance is not None and mercury_solar_distance <= 15.0
        )
        mercury_with_infortunes = tuple(
            body for body in _INFORTUNES if chart.planets[body].sign == mercury.sign
        )
        moon_place = _whole_sign_place(chart, Body.MOON)
        moon_in_bad_travel_place = moon_place in (6, 12)
        lord_data: list[tuple[str, str, DorotheusPlacementWitness, float | None, bool, bool | None]] = []
        for role, body, placement in (
            ("ascendant", asc_lord, asc_lord_placement),
            ("moon", moon_lord, moon_lord_placement),
        ):
            solar_distance = _solar_distance(chart, body)
            under_rays = solar_distance is not None and solar_distance <= 15.0
            cadent = (
                None
                if placement.strength is DorotheusStrengthState.NOT_EVALUABLE
                else placement.strength is DorotheusStrengthState.CADENT
            )
            lord_data.append((role, body, placement, solar_distance, under_rays, cadent))
        explicit_prerequisite_failures = (
            ("moon_not_increasing_in_calculation", not moon_increasing),
            ("mercury_under_rays", mercury_under_rays),
            ("mercury_with_infortunes", bool(mercury_with_infortunes)),
            ("moon_in_sixth_or_twelfth_place", moon_in_bad_travel_place),
            *tuple(
                (f"lord_of_{role}_under_rays", under_rays)
                for role, _, _, _, under_rays, _ in lord_data
            ),
            *tuple(
                (f"lord_of_{role}_falling", cadent is True)
                for role, _, _, _, _, cadent in lord_data
            ),
        )
        prerequisite_unknown = any(cadent is None for _, _, _, _, _, cadent in lord_data)
        prerequisite_state = (
            DorotheusMatterClauseState.TRIGGERED
            if any(failed for _, failed in explicit_prerequisite_failures)
            else DorotheusMatterClauseState.NOT_EVALUABLE
            if prerequisite_unknown
            else DorotheusMatterClauseState.CLEAR
        )
        first_place, seventh_place = angular_places[:2]
        moon_malefics_at_stakes = tuple(
            body
            for body in _INFORTUNES
            if moon_place in (1, 7) and chart.planets[body].sign == moon.sign
        )
        stationary_lords: list[str] = []
        stationary_measurements: list[DorotheusMeasurement] = []
        for role, body, _, _, _, _ in lord_data:
            stationary, threshold = _stationary_witness(chart, body)
            if stationary:
                stationary_lords.append(body)
            stationary_measurements.extend(
                (
                    _measurement(f"lord_of_{role}", body),
                    _measurement(
                        f"lord_of_{role}_longitude_rate",
                        chart.planets[body].speed,
                        units="degrees/day",
                    ),
                    _measurement(
                        f"lord_of_{role}_stationary_threshold",
                        threshold,
                        units="degrees/day",
                        comparison="abs(rate)<",
                    ),
                    _measurement(f"lord_of_{role}_stationary", stationary),
                )
            )
        benefic_connection_measurements: list[DorotheusMeasurement] = []
        exact_benefic_connections: list[str] = []
        unresolved_benefic_connections: list[str] = []
        for benefic in _FORTUNES:
            aspect_name = _hard_aspect_name(moon.sign, chart.planets[benefic].sign)
            benefic_connection_measurements.extend(
                (
                    _measurement(f"{benefic.lower()}_sign", chart.planets[benefic].sign),
                    _measurement(f"{benefic.lower()}_whole_sign_hard_aspect", aspect_name or "none"),
                )
            )
            if aspect_name is None:
                continue
            motion = aspect_motion_witness(
                Body.MOON,
                moon.longitude,
                benefic,
                chart.planets[benefic].longitude,
                aspect_name,
                speed1_deg_per_day=moon.speed,
                speed2_deg_per_day=chart.planets[benefic].speed,
                reference_frame="apparent_geocentric_ecliptic_longitude_of_date",
                timescale="UT1_input_with_internal_TT_ephemeris_evaluation",
            )
            benefic_connection_measurements.extend(
                (
                    _measurement(f"{benefic.lower()}_motion_state", motion.state.value),
                    _measurement(
                        f"{benefic.lower()}_directed_error",
                        motion.directed_error_deg,
                        units="degrees",
                    ),
                    _measurement(
                        f"{benefic.lower()}_canonical_orb",
                        motion.orb_deg,
                        units="degrees",
                    ),
                )
            )
            if motion.state is AspectMotionState.EXACT:
                exact_benefic_connections.append(benefic)
            elif motion.state is AspectMotionState.APPLYING:
                unresolved_benefic_connections.append(benefic)
        benefic_connection_state = (
            DorotheusMatterClauseState.SATISFIED
            if exact_benefic_connections
            else DorotheusMatterClauseState.NOT_EVALUABLE
            if unresolved_benefic_connections
            else DorotheusMatterClauseState.CLEAR
        )
        hard_malefic_aspects = tuple(
            body
            for body in _INFORTUNES
            if _hard_aspect_name(moon.sign, chart.planets[body].sign) is not None
        )
        clauses = (
            _clause(
                "travel_stake_assignments",
                1,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                tuple(
                    _measurement(f"place_{item.whole_sign_place}_topic", item.topic)
                    for item in angular_places
                ),
                "V.22.1 assigns the traveler, destination land, sought business or need, and outcome to places 1, 7, 10, and 4. The assignments are retained as separate witnesses, not a score.",
                authority,
            ),
            _clause(
                "departure_prerequisites",
                2,
                DorotheusMatterClauseRole.GATE,
                prerequisite_state,
                (
                    _measurement(
                        "moon_true_longitude_mean_ecliptic",
                        moon_true_longitude_mean_ecliptic_degrees,
                        units="degrees",
                    ),
                    _measurement(
                        "moon_mean_longitude_iers_2010",
                        mean_lunar_longitude,
                        units="degrees",
                    ),
                    _measurement("lunar_equation", lunar_equation, units="degrees"),
                    _measurement("calculation_direction", calculation_direction),
                    _measurement("mercury_solar_distance", mercury_solar_distance, units="degrees"),
                    _measurement("mercury_under_15_degree_rays", mercury_under_rays),
                    _measurement("mercury_same_sign_infortunes", ",".join(mercury_with_infortunes) or "none"),
                    _measurement("moon_whole_sign_place", moon_place),
                    _measurement("moon_in_sixth_or_twelfth", moon_in_bad_travel_place),
                )
                + tuple(
                    measurement
                    for role, body, placement, solar_distance, under_rays, cadent in lord_data
                    for measurement in (
                        _measurement(f"lord_of_{role}", body),
                        _measurement(f"lord_of_{role}_solar_distance", solar_distance, units="degrees"),
                        _measurement(f"lord_of_{role}_under_15_degree_rays", under_rays),
                        _measurement(f"lord_of_{role}_strength", placement.strength.value),
                        _measurement(f"lord_of_{role}_falling", cadent),
                    )
                )
                + (_measurement("failed_prerequisites", ",".join(name for name, failed in explicit_prerequisite_failures if failed) or "none"),),
                "V.22.2 makes these departure requirements conjunctive. Falling is evaluated only from a quadrant figure; when no explicit failure is present, a non-quadrant figure leaves that part of the sentence not evaluable.",
                authority,
            ),
            _clause(
                "moon_in_sixth_or_twelfth_travel_harm",
                3,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("moon_whole_sign_place", moon_place),
                    _measurement("travel_harm_testimony", moon_in_bad_travel_place),
                ),
                "V.22.3 attaches trouble, toil, and harm to the Moon in the sixth or twelfth. This preserves the named outcome testimony without inventing a severity score.",
                authority,
            ),
            _clause(
                "moon_increasing_in_calculation_comfort",
                4,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if moon_increasing
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("lunar_equation", lunar_equation, units="degrees", comparison=">", threshold=0.0),
                    _measurement("calculation_direction", calculation_direction),
                    _measurement("source_effect", "reaches_destination_in_comfort" if moon_increasing else "not_named"),
                ),
                "V.22.4 attributes comfortable arrival to the Moon increasing in calculation; zero is not silently treated as increasing.",
                authority,
            ),
            _clause(
                "fortunes_in_ascendant_journey_condition",
                5,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if first_place.occupying_fortunes
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("ascendant_sign", first_place.sign),
                    _measurement("occupying_fortunes", ",".join(first_place.occupying_fortunes) or "none"),
                ),
                "V.22.5 uses occupation of the Ascendant, not a generic configured benefit, for a journey whose condition turns good.",
                authority,
            ),
            _clause(
                "fortunes_in_seventh_destination_benefit",
                6,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if seventh_place.occupying_fortunes
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("seventh_sign", seventh_place.sign),
                    _measurement("occupying_fortunes", ",".join(seventh_place.occupying_fortunes) or "none"),
                ),
                "V.22.6 uses occupation of the seventh for benefit at the named destination land.",
                authority,
            ),
            _clause(
                "moon_with_infortune_in_travel_stakes",
                7,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if moon_malefics_at_stakes
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_whole_sign_place", moon_place),
                    _measurement("moon_sign", moon.sign),
                    _measurement("same_sign_infortunes", ",".join(moon_malefics_at_stakes) or "none"),
                ),
                "V.22.7, with edition note 117, requires the Moon with Saturn or Mars in the Ascendant or seventh. 'Together' is Dorothean same-sign co-presence, not an invented degree orb.",
                authority,
            ),
            _clause(
                "travel_lords_stationary",
                8,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if stationary_lords
                    else DorotheusMatterClauseState.CLEAR
                ),
                tuple(stationary_measurements) + (
                    _measurement("stationary_lords", ",".join(dict.fromkeys(stationary_lords)) or "none"),
                ),
                "V.22.8 names either lord's station as lengthening the time abroad. The visible numerical threshold is Moira's existing body-specific instantaneous station policy, not a historical station orb.",
                authority,
            ),
            _clause(
                "fortune_square_or_opposition_moon_connection",
                9,
                DorotheusMatterClauseRole.FORTIFIER,
                benefic_connection_state,
                tuple(benefic_connection_measurements)
                + (
                    _measurement("exactly_connecting_fortunes", ",".join(exact_benefic_connections) or "none"),
                    _measurement("applying_fortunes_with_unresolved_degree_interval", ",".join(unresolved_benefic_connections) or "none"),
                ),
                "V.22.9 requires a fortune in square or opposition and the Moon's connection. The edition glossary establishes motion toward exactness but leaves the particular degree interval unstated: exact connection is satisfied, while a merely applying configuration remains explicitly not evaluable.",
                f"{authority}; {_AUTHORITY_CONNECTION}",
            ),
            _clause(
                "infortune_square_or_opposition_moon",
                10,
                DorotheusMatterClauseRole.GATE,
                (
                    DorotheusMatterClauseState.TRIGGERED
                    if hard_malefic_aspects
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("whole_sign_hard_aspect_infortunes", ",".join(hard_malefic_aspects) or "none"),
                ),
                "V.22.10 names an infortune in the Moon's square or opposition as bad for the journey. Unlike V.22.9, this sentence does not add a connection requirement.",
                authority,
            ),
        )
        triggered = tuple(
            item.clause_id
            for item in clauses
            if item.state is DorotheusMatterClauseState.TRIGGERED
        )
        unknown = tuple(
            item.clause_id
            for item in clauses
            if item.state is DorotheusMatterClauseState.NOT_EVALUABLE
        )
        status = (
            DorotheusMatterProfileStatus.TRIGGERED
            if triggered
            else DorotheusMatterProfileStatus.INDETERMINATE
            if unknown
            else DorotheusMatterProfileStatus.CLEAR
        )
        return DorotheusMatterProfileEvaluation(
            jd_ut=chart.jd_ut,
            profile_id=profile_id,
            profile_version=resolved_policy.profile_version,
            policy=resolved_policy,
            matter=_MATTERS[profile_id],
            status=status,
            moon_condition=moon_condition,
            rooted_context=None,
            moon_connection_flow=None,
            clauses=clauses,
            angular_places=angular_places,
            planetary_strengths=strengths,
            triggered_clause_ids=triggered,
            not_evaluable_clause_ids=unknown,
            reader_provenance=reader_provenance,
            authorities=(
                authority,
                _AUTHORITY_CALCULATION,
                _AUTHORITY_MEAN_LUNAR_LONGITUDE,
                _AUTHORITY_CONNECTION,
            ),
            numerically_complete=not unknown,
        )
    if profile_id not in _UNROOTED_EPHEMERAL_PROFILES:
        if rooted_context is None or rooted_context.jd_ut != chart.jd_ut:
            raise ValueError("existing matter profiles require a same-instant rooted context")
        if rooted_context.matter is not _ROOTED_MATTERS[profile_id]:
            raise ValueError("rooted context matter must match the requested profile")
    if (
        moon_connection_flow is not None
        and moon_connection_flow.jd_query != chart.jd_ut
    ):
        raise ValueError("Moon connection flow must describe the same instant")
    if profile_id not in _FLOW_PROFILES and moon_connection_flow is not None:
        raise ValueError("Moon connection flow belongs only to a flow-based profile")

    authority = _AUTHORITIES[profile_id]
    angular_places: tuple[DorotheusAngularPlaceWitness, ...] = ()
    strengths: tuple[DorotheusPlacementWitness, ...] = ()

    if profile_id is DorotheusMatterProfileId.DEMOLITION:
        strengths = tuple(_placement(chart, body) for body in _FORTUNES + _INFORTUNES)
        strength_evaluable = all(
            item.strength is not DorotheusStrengthState.NOT_EVALUABLE
            for item in strengths
        )
        descending = moon_latitude_rate_degrees_per_day < 0.0
        clauses = (
            _clause(
                "moon_descending_south_in_latitude",
                1,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if descending
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement(
                        "moon_latitude_rate",
                        moon_latitude_rate_degrees_per_day,
                        units="degrees/day",
                        comparison="<",
                        threshold=0.0,
                    ),
                    _measurement("direction", "southward" if descending else "northward_or_stationary"),
                ),
                "V.8's descent is Hephaistion's southward lunar latitude motion.",
                authority,
            ),
            _clause(
                "fortune_and_infortune_strengths",
                2,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if strength_evaluable
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                ),
                tuple(
                    _measurement(f"{item.body.lower()}_strength", item.strength.value)
                    for item in strengths
                ),
                "V.8 preserves each fortune and infortune's dynamic strength: fortunes indicate ease and success, while infortunes indicate slowness, difficulty, and toil. No aggregate score is inferred.",
                authority,
            ),
        )
    elif profile_id is DorotheusMatterProfileId.LEASING:
        angular_places = (
            _angular_witness(chart, 1, "hiring_party", "party hiring labor or taking the fixed amount"),
            _angular_witness(chart, 7, "owner_or_provider", "owner or party providing labor, land, or tools"),
            _angular_witness(chart, 10, "amount_or_price", "amount, price, or contractual quantity"),
            _angular_witness(chart, 4, "outcome", "outcome of the work or agreement"),
        )
        leasing_clauses: list[DorotheusMatterClauseWitness] = []
        ids = (
            "infortune_in_hiring_party_place",
            "infortune_in_or_configured_to_owner_place",
            "infortune_in_or_configured_to_amount_place",
            "infortune_in_or_configured_to_outcome_place",
        )
        consequences = (
            "V.9.2-3: the hiring party may back out and take nothing; if the party participates, the text warns of deception, wickedness, and immorality.",
            "V.9.4-5: the owner or provider may back out and withhold the portion; participation carries warnings of immorality, obscenity, and betrayal.",
            "V.9.6: the amount or price will not be put in order and misfortune is attributed to it.",
            "V.9.7: the outcome is described as bad and harmful.",
        )
        for order, (clause_id, witness, consequence) in enumerate(
            zip(ids, angular_places, consequences), start=1
        ):
            malefics = witness.occupying_infortunes
            if witness.whole_sign_place != 1:
                malefics += witness.configured_infortunes
            leasing_clauses.append(
                _clause(
                    clause_id,
                    order,
                    DorotheusMatterClauseRole.GATE,
                    (
                        DorotheusMatterClauseState.TRIGGERED
                        if malefics
                        else DorotheusMatterClauseState.CLEAR
                    ),
                    (
                        _measurement("whole_sign_place", witness.whole_sign_place),
                        _measurement("topic", witness.topic),
                        _measurement("qualifying_infortunes", ",".join(malefics) or "none"),
                    ),
                    consequence + " The warning remains attached to the named party or stake and is not converted into a numeric score.",
                    authority,
                )
            )
        flow = moon_connection_flow
        previous = None if flow is None else flow.previous_separation
        previous_motion = None if flow is None else flow.previous_motion
        connection = None if flow is None else flow.next_connection
        leasing_clauses.append(
            _clause(
                "moon_separation_and_connection_flow",
                5,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("next_connection_body", None if connection is None else connection.body),
                    _measurement("next_connection_aspect", None if connection is None else connection.aspect_name),
                    _measurement("next_connection_jd_exact", None if connection is None else connection.jd_exact, units="JD UT1"),
                    _measurement("next_connection_signed_error_at_query", None if connection is None else connection.signed_error_at_query_deg, units="degrees"),
                    _measurement("previous_separation_body", None if previous is None else previous.body),
                    _measurement("previous_separation_aspect", None if previous is None else previous.aspect_name),
                    _measurement("previous_separation_jd_exact", None if previous is None else previous.jd_exact, units="JD UT1"),
                    _measurement("previous_separation_signed_error_at_query", None if previous is None else previous.signed_error_at_query_deg, units="degrees"),
                    _measurement("previous_motion_state", None if previous_motion is None else previous_motion.state.value),
                    _measurement("previous_window_policy", None if flow is None else flow.policy.previous_window.value),
                    _measurement("missing_semantics", "V.9-specific assignment of lunar flow-away and connection to the four leasing stakes"),
                ),
                "V.9.8 requires both what the Moon flows away from and connects to. The neutral geometry is preserved when an explicit previous-event window is supplied, but the surviving V.9 text does not assign those events to its four leasing stakes; the doctrinal clause therefore remains indeterminate.",
                authority,
            )
        )
        clauses = tuple(leasing_clauses)
    elif profile_id is DorotheusMatterProfileId.BUYING_AND_SELLING:
        angular_places = (
            _angular_witness(chart, 1, "buyer", "the one buying"),
            _angular_witness(chart, 7, "seller", "the one selling"),
            _angular_witness(chart, 10, "price", "the price"),
            _angular_witness(chart, 4, "commodity", "the commodity bought or sold"),
        )
        flow = moon_connection_flow
        previous = None if flow is None else flow.previous_separation
        connection = None if flow is None else flow.next_connection
        flow_complete = previous is not None and connection is not None
        lunar_measurements: list[DorotheusMeasurement] = [
            _measurement("commodity_significator", Body.MOON),
            _measurement(
                "seller_significator", None if previous is None else previous.body
            ),
            _measurement(
                "buyer_significator", None if connection is None else connection.body
            ),
            _measurement(
                "price_significator", None if connection is None else connection.body
            ),
            _measurement(
                "previous_window_policy",
                None if flow is None else flow.policy.previous_window.value,
            ),
            _measurement(
                "previous_separation_aspect",
                None if previous is None else previous.aspect_name,
            ),
            _measurement(
                "next_connection_aspect",
                None if connection is None else connection.aspect_name,
            ),
        ]
        for topic, body in (
            ("commodity", Body.MOON),
            ("seller", None if previous is None else previous.body),
            ("buyer_and_price", None if connection is None else connection.body),
        ):
            lunar_measurements.extend(
                (
                    _measurement(
                        f"{topic}_configured_fortunes",
                        None
                        if body is None
                        else ",".join(_body_testimony(chart, body, _FORTUNES))
                        or "none",
                    ),
                    _measurement(
                        f"{topic}_configured_infortunes",
                        None
                        if body is None
                        else ",".join(_body_testimony(chart, body, _INFORTUNES))
                        or "none",
                    ),
                )
            )
        clauses = (
            _clause(
                "moon_flow_role_assignments",
                1,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if flow_complete
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                ),
                tuple(lunar_measurements),
                "V.10.1-4 assigns the Moon to the commodity, the planet of the previous exact separation to the seller, and the planet of the next exact connection to both buyer and price. Fortune and infortune testimony remains attached to each named topic; no aggregate verdict is inferred.",
                authority,
            ),
            _clause(
                "four_stake_role_assignments",
                2,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                tuple(
                    _measurement(
                        f"{item.topic}_whole_sign_place", item.whole_sign_place
                    )
                    for item in angular_places
                )
                + tuple(
                    _measurement(
                        f"{item.topic}_fortunes",
                        ",".join(item.occupying_fortunes + item.configured_fortunes)
                        or "none",
                    )
                    for item in angular_places
                )
                + tuple(
                    _measurement(
                        f"{item.topic}_infortunes",
                        ",".join(item.occupying_infortunes + item.configured_infortunes)
                        or "none",
                    )
                    for item in angular_places
                ),
                "V.10.5-7 independently assigns buyer, seller, price, and commodity to whole-sign places 1, 7, 10, and 4. Fortune and infortune testimony remains separate for every stake.",
                authority,
            ),
        )
    elif profile_id is DorotheusMatterProfileId.LUNAR_PRICE_TIMING:
        moon = chart.planets[Body.MOON]
        sun = chart.planets[Body.SUN]
        rising_region = moon.sign in _RISING_REGION_SIGNS
        region = "rising_aquarius_through_cancer" if rising_region else (
            "falling_leo_through_capricorn"
        )
        mean_lunar_longitude, lunar_equation, calculation_direction = (
            _lunar_calculation(
                chart,
                float(moon_true_longitude_mean_ecliptic_degrees),
            )
        )
        price_relation = (
            "above_value"
            if rising_region and lunar_equation > 0.0
            else "below_value"
            if not rising_region and lunar_equation < 0.0
            else "no_compound_V44_price_testimony"
        )
        latitude_motion = (
            "rising_northward"
            if moon_latitude_rate_degrees_per_day > 0.0
            else "falling_southward"
            if moon_latitude_rate_degrees_per_day < 0.0
            else "stationary_in_latitude"
        )
        elongation = (moon.longitude - sun.longitude) % 360.0
        phase_interval, phase_effect, phase_note = _phase_quadrant(elongation)
        clauses = (
            _clause(
                "tabari_sign_region_and_calculation_price_relation",
                1,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("node_region", region),
                    _measurement(
                        "moon_true_longitude_mean_ecliptic",
                        moon_true_longitude_mean_ecliptic_degrees,
                        units="degrees",
                    ),
                    _measurement(
                        "moon_mean_longitude_iers_2010",
                        mean_lunar_longitude,
                        units="degrees",
                    ),
                    _measurement("lunar_equation", lunar_equation, units="degrees"),
                    _measurement("calculation_direction", calculation_direction),
                    _measurement("price_relation", price_relation),
                ),
                "V.44.1-3 in the al-Tabari recension combines the Moon's fixed sign region with the edition glossary's calculation direction. Only the two named conjunctions produce above-value or below-value testimony; other combinations remain unclassified.",
                authority,
            ),
            _clause(
                "hephaistion_parallel_latitude_and_speed_reading",
                2,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("moon_ecliptic_latitude", moon.latitude, units="degrees"),
                    _measurement(
                        "moon_latitude_rate",
                        moon_latitude_rate_degrees_per_day,
                        units="degrees/day",
                    ),
                    _measurement("latitude_motion", latitude_motion),
                    _measurement("moon_longitude_rate", moon.speed, units="degrees/day"),
                    _measurement("speed_threshold", None, units="degrees/day"),
                    _measurement("moon_waxing", 0.0 < elongation < 180.0),
                ),
                "Edition notes 397, 399, and 400 preserve the Hephaistion/Dorotheus-poem reading in latitude, faster/slower motion, and waning. The cited V.44 material supplies no speed threshold or complete combination law, so this parallel cannot overwrite the computable recension reading.",
                authority,
            ),
            _clause(
                "lunar_phase_commerce_interval",
                3,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("moon_sun_elongation", elongation, units="degrees"),
                    _measurement(
                        "boundary_tolerance",
                        _PHASE_BOUNDARY_TOLERANCE_DEG,
                        units="degrees",
                    ),
                    _measurement("phase_interval", phase_interval),
                    _measurement("source_effect", phase_effect),
                    _measurement("source_note_or_variant", phase_note),
                ),
                "V.44.4-8 classifies the four directed Moon-Sun phase arcs. Exact conjunction, squares, and opposition remain explicit boundaries rather than being silently assigned to an adjacent interval.",
                authority,
            ),
        )
    elif profile_id is DorotheusMatterProfileId.LAND_PURCHASE:
        angular_places = (
            _angular_witness(chart, 4, "land", "the land itself"),
            _angular_witness(chart, 10, "trees", "trees on the land"),
            _angular_witness(chart, 7, "vegetation", "grasses, hemp, and vegetation"),
            _angular_witness(chart, 1, "cultivation", "cultivation and management of the land"),
        )
        land = angular_places[0]
        watery = land.sign in _WATERY_SIGNS
        twin = land.sign in _TWIN_SIGNS
        clauses = (
            _clause(
                "fourth_place_terrain_testimony",
                1,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("fourth_place_sign", land.sign),
                    _measurement("watery_sign", watery),
                    _measurement("twin_sign", twin),
                    _measurement(
                        "terrain_testimony",
                        "+".join(
                            item
                            for item, present in (
                                ("near_water_or_much_water", watery),
                                ("mixed_mountains_and_plains", twin),
                            )
                            if present
                        ) or "no_V.11_named_terrain_testimony",
                    ),
                ),
                "V.11 permits both testimonies to coexist; Pisces is not forced into one category.",
                authority,
            ),
            _clause(
                "fortune_and_infortune_testimony_at_remaining_stakes",
                2,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                tuple(
                    _measurement(
                        f"{item.topic}_configured_fortunes",
                        ",".join(item.occupying_fortunes + item.configured_fortunes) or "none",
                    )
                    for item in angular_places
                )
                + tuple(
                    _measurement(
                        f"{item.topic}_configured_infortunes",
                        ",".join(item.occupying_infortunes + item.configured_infortunes) or "none",
                    )
                    for item in angular_places
                ),
                "The four topic stakes retain fortune and infortune testimony separately: fortune indicates benefit and infortune harm for the matter attributed to that stake. V.11 supplies no lawful aggregate score.",
                authority,
            ),
        )
    elif profile_id is DorotheusMatterProfileId.SHIP_ACQUISITION:
        moon = chart.planets[Body.MOON]
        asc_sign, _, _ = sign_of(chart.houses.asc)
        fourth = _angular_witness(
            chart,
            4,
            "ship_acquisition",
            "the ship to be bought or commissioned",
        )
        angular_places = (fourth,)
        qualifying_fortunes = tuple(
            body
            for body in _FORTUNES
            if (
                chart.planets[body].sign == fourth.sign
                and _configured(chart.planets[body].sign, asc_sign)
                and _configured(chart.planets[body].sign, moon.sign)
            )
        )
        known_preferred_places = tuple(
            body
            for body in qualifying_fortunes
            if (
                chart.planets[body].sign in _WATERY_SIGNS
                or DOMICILE_RULERS[chart.planets[body].sign] in _FORTUNES
            )
        )
        unresolved_sea_animal_candidates = tuple(
            body for body in qualifying_fortunes if body not in known_preferred_places
        )
        listed_pair_signs = frozenset(
            ("Taurus", "Gemini", "Cancer", "Virgo", "Sagittarius")
        )
        paired_sign = asc_sign if asc_sign == moon.sign else None
        preferred_rank = (
            1
            if paired_sign == "Taurus"
            else 2
            if paired_sign == "Pisces"
            else 3
            if paired_sign == "Gemini"
            else None
        )
        clauses = (
            _clause(
                "fortune_in_fourth_looking_at_ascendant_and_moon",
                1,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if qualifying_fortunes
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("fourth_place_sign", fourth.sign),
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement(
                        "jupiter_in_fourth",
                        chart.planets[Body.JUPITER].sign == fourth.sign,
                    ),
                    _measurement(
                        "jupiter_looks_at_ascendant",
                        _configured(chart.planets[Body.JUPITER].sign, asc_sign),
                    ),
                    _measurement(
                        "jupiter_looks_at_moon",
                        _configured(chart.planets[Body.JUPITER].sign, moon.sign),
                    ),
                    _measurement(
                        "venus_in_fourth",
                        chart.planets[Body.VENUS].sign == fourth.sign,
                    ),
                    _measurement(
                        "venus_looks_at_ascendant",
                        _configured(chart.planets[Body.VENUS].sign, asc_sign),
                    ),
                    _measurement(
                        "venus_looks_at_moon",
                        _configured(chart.planets[Body.VENUS].sign, moon.sign),
                    ),
                    _measurement(
                        "qualifying_fortunes",
                        ",".join(qualifying_fortunes) or "none",
                    ),
                ),
                "V.24.1 requires Jupiter or Venus in the fourth, looking at both the Ascendant and Moon. Each fortune is exposed separately under the fixed whole-sign configuration policy.",
                authority,
            ),
            _clause(
                "water_or_jupiter_venus_house_preference",
                2,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if known_preferred_places
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if unresolved_sea_animal_candidates
                    else DorotheusMatterClauseState.CLEAR
                ),
                tuple(
                    measurement
                    for body in qualifying_fortunes
                    for measurement in (
                        _measurement(f"{body}_sign", chart.planets[body].sign),
                        _measurement(
                            f"{body}_in_named_water_sign",
                            chart.planets[body].sign in _WATERY_SIGNS,
                        ),
                        _measurement(
                            f"{body}_domicile_ruler",
                            DOMICILE_RULERS[chart.planets[body].sign],
                        ),
                        _measurement(
                            f"{body}_in_jupiter_or_venus_house",
                            DOMICILE_RULERS[chart.planets[body].sign] in _FORTUNES,
                        ),
                    )
                )
                + (
                    _measurement(
                        "qualifying_fortunes",
                        ",".join(qualifying_fortunes) or "none",
                    ),
                    _measurement(
                        "known_preferred_fortunes",
                        ",".join(known_preferred_places) or "none",
                    ),
                    _measurement(
                        "unresolved_sea_animal_candidates",
                        ",".join(unresolved_sea_animal_candidates) or "none",
                    ),
                ),
                "V.24.2 names water signs and Jupiter/Venus houses, which are computed here. It also names an unenumerated sea-animal-sign class; a qualifying fortune outside the named categories therefore remains not evaluable rather than receiving an invented sign list.",
                f"{authority}; {_AUTHORITY_WATERY_SIGNS}",
            ),
            _clause(
                "ascendant_and_moon_in_named_ship_acquisition_signs",
                3,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if paired_sign in listed_pair_signs
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                    if paired_sign == "Capricorn"
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("shared_sign", paired_sign or "none"),
                    _measurement(
                        "listed_full_sign_pair",
                        paired_sign in listed_pair_signs,
                    ),
                    _measurement(
                        "capricorn_end_degree_interval", None, units="degrees"),
                    _measurement(
                        "edition_note_136_missing_predicate", True),
                ),
                "V.24.3 names the Ascendant and Moon together in Taurus, Gemini, Cancer, Virgo, or Sagittarius. The end-of-Capricorn wording has neither a degree interval nor a fully recovered predicate in note 136, so Capricorn is retained as not evaluable.",
                authority,
            ),
            _clause(
                "ascendant_and_moon_in_pisces",
                4,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if paired_sign == "Pisces"
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("both_in_pisces", paired_sign == "Pisces"),
                ),
                "V.24.4 separately calls the Ascendant and Moon together in Pisces suitable for the matter.",
                authority,
            ),
            _clause(
                "source_ranked_sign_preferences",
                5,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.NOT_EVALUABLE
                    if paired_sign == "Capricorn"
                    else DorotheusMatterClauseState.OBSERVED
                ),
                (
                    _measurement("ascendant_sign", asc_sign),
                    _measurement("moon_sign", moon.sign),
                    _measurement("shared_sign", paired_sign or "none"),
                    _measurement("source_rank", preferred_rank),
                    _measurement(
                        "ranked_order",
                        "Taurus> Pisces> Gemini> end_of_Capricorn",
                    ),
                    _measurement("capricorn_end_degree_interval", None, units="degrees"),
                ),
                "V.24.5 preserves Taurus, Pisces, Gemini, and end of Capricorn in the source's stated preference order. The order is a witness only: it does not create a score, and Capricorn remains not evaluable because its end interval is unspecified.",
                authority,
            ),
        )
    elif profile_id is DorotheusMatterProfileId.SHIP_CONSTRUCTION:
        if moon_true_longitude_mean_ecliptic_degrees is None:
            raise AssertionError("V.25 calculation input was validated above")
        angular_places = ()
        strengths = ()
        clauses = _ship_construction_clauses(
            chart,
            moon_latitude_rate_degrees_per_day=moon_latitude_rate_degrees_per_day,
            moon_true_longitude_mean_ecliptic_degrees=moon_true_longitude_mean_ecliptic_degrees,
            authority=authority,
        )
    elif profile_id is DorotheusMatterProfileId.SHIP_LAUNCH:
        angular_places = ()
        strengths = ()
        clauses = _ship_launch_clauses(
            chart,
            natal_chart=natal_chart,
            authority=authority,
        )
    elif profile_id is DorotheusMatterProfileId.LAND_TRAVEL:
        angular_places = ()
        strengths = ()
        clauses = _land_travel_clauses(
            chart,
            authority=authority,
            policy=resolved_policy,
        )
    elif profile_id is DorotheusMatterProfileId.SEA_TRAVEL:
        angular_places = ()
        strengths = ()
        clauses = _sea_travel_clauses(
            chart,
            authority=authority,
            policy=resolved_policy,
        )
    elif profile_id is DorotheusMatterProfileId.PARTNERSHIP:
        strengths = ()
        clauses, angular_places = _partnership_clauses(chart, authority=authority)
    elif profile_id is DorotheusMatterProfileId.DEBT_AND_PAYMENT:
        strengths = ()
        clauses, angular_places = _debt_and_payment_clauses(chart, authority=authority)
    elif profile_id is DorotheusMatterProfileId.WRITING_A_WILL:
        if moon_true_longitude_mean_ecliptic_degrees is None:
            raise AssertionError("V.43 calculation input was validated above")
        angular_places = ()
        strengths = ()
        clauses = _writing_a_will_clauses(
            chart,
            moon_latitude_rate_degrees_per_day=moon_latitude_rate_degrees_per_day,
            moon_true_longitude_mean_ecliptic_degrees=moon_true_longitude_mean_ecliptic_degrees,
            authority=authority,
        )
    else:
        raise AssertionError("unhandled Dorotheus matter profile")

    triggered = tuple(
        item.clause_id for item in clauses if item.state is DorotheusMatterClauseState.TRIGGERED
    )
    unknown = tuple(
        item.clause_id for item in clauses if item.state is DorotheusMatterClauseState.NOT_EVALUABLE
    )
    if triggered:
        status = DorotheusMatterProfileStatus.TRIGGERED
    elif unknown:
        status = DorotheusMatterProfileStatus.INDETERMINATE
    elif profile_id in {
        DorotheusMatterProfileId.LEASING,
        DorotheusMatterProfileId.TRAVEL,
    }:
        status = DorotheusMatterProfileStatus.CLEAR
    else:
        status = DorotheusMatterProfileStatus.DESCRIPTIVE

    return DorotheusMatterProfileEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=profile_id,
        profile_version=resolved_policy.profile_version,
        policy=resolved_policy,
        matter=_MATTERS[profile_id],
        status=status,
        moon_condition=moon_condition,
        rooted_context=rooted_context,
        moon_connection_flow=moon_connection_flow,
        clauses=clauses,
        angular_places=angular_places,
        planetary_strengths=strengths,
        triggered_clause_ids=triggered,
        not_evaluable_clause_ids=unknown,
        reader_provenance=reader_provenance,
        authorities=(
            (
                authority,
                _AUTHORITY_CALCULATION,
                _AUTHORITY_MEAN_LUNAR_LONGITUDE,
                _AUTHORITY_CONNECTION,
            )
            if profile_id is DorotheusMatterProfileId.TRAVEL
            else (
                authority,
                _AUTHORITY_CALCULATION,
                _AUTHORITY_MEAN_LUNAR_LONGITUDE,
                _AUTHORITY_EGYPTIAN_BOUNDS,
            )
            if profile_id is DorotheusMatterProfileId.SHIP_CONSTRUCTION
            else (authority, _AUTHORITY_CALCULATION, _AUTHORITY_MEAN_LUNAR_LONGITUDE, _AUTHORITY_CONNECTION)
            if profile_id is DorotheusMatterProfileId.WRITING_A_WILL
            else (authority, _AUTHORITY_CALCULATION, _AUTHORITY_MEAN_LUNAR_LONGITUDE)
            if profile_id is DorotheusMatterProfileId.LUNAR_PRICE_TIMING
            else (
                authority,
                _AUTHORITY_WATERY_SIGNS,
                _travel_sign_nature_authority(resolved_policy),
            )
            if profile_id in _SIGN_NATURE_PROFILES
            else (authority,)
        ),
        numerically_complete=not unknown,
    )


def _resolve_matter_profile_policy(
    profile_id: DorotheusMatterProfileId,
    *,
    policy: DorotheusMatterProfilePolicy | None,
    sign_nature_variant: DorotheusSignNatureVariant | None,
) -> DorotheusMatterProfilePolicy:
    if policy is not None:
        if policy.profile_id is not profile_id:
            raise ValueError("policy identity must match requested profile")
        if sign_nature_variant is not None:
            raise ValueError("provide either policy or sign_nature_variant, not both")
        return policy
    if profile_id not in _SIGN_NATURE_PROFILES:
        if sign_nature_variant is not None:
            raise ValueError("sign_nature_variant belongs only to V.26.39-43 travel profiles")
        return _POLICIES[profile_id]
    if sign_nature_variant is None:
        raise ValueError(
            "V.26.39-43 travel profiles require an explicit sign_nature_variant"
        )
    return DorotheusMatterProfilePolicy(
        profile_id=profile_id,
        sign_nature_variant=DorotheusSignNatureVariant(sign_nature_variant),
    )


def dorotheus_matter_profile_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    profile_id: DorotheusMatterProfileId,
    election_class: WesternElectionClass = WesternElectionClass.EPHEMERAL,
    natal_jd_ut: float | None = None,
    natal_latitude: float | None = None,
    natal_longitude: float | None = None,
    natal_house_system: str | None = None,
    unavoidable_time_urgency: bool | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: DorotheusMatterProfilePolicy | None = None,
    moon_flow_policy: MoonConnectionFlowPolicy | None = None,
    sign_nature_variant: DorotheusSignNatureVariant | None = None,
) -> DorotheusMatterProfileEvaluation:
    """Construct the shared astronomy and evaluate one named matter profile."""

    profile_id = DorotheusMatterProfileId(profile_id)
    resolved_policy = _resolve_matter_profile_policy(
        profile_id,
        policy=policy,
        sign_nature_variant=sign_nature_variant,
    )
    if profile_id in _FLOW_PROFILES and moon_flow_policy is None:
        raise ValueError(
            "flow-based profile requires an explicit moon_flow_policy because the "
            "previous-separation window is not source-settled"
        )
    if profile_id not in _FLOW_PROFILES and moon_flow_policy is not None:
        raise ValueError("moon_flow_policy is accepted only for flow-based profiles")
    election_class = WesternElectionClass(election_class)
    natal_values = (natal_jd_ut, natal_latitude, natal_longitude, natal_house_system)
    if profile_id in _EPHEMERAL_ONLY_PROFILES:
        if election_class is not WesternElectionClass.EPHEMERAL:
            raise ValueError(
                "source-unrooted Dorotheus matter profiles admit only ephemeral elections"
            )
        if any(value is not None for value in natal_values):
            raise ValueError("source-unrooted Dorotheus matter profiles reject natal input")
    if election_class is WesternElectionClass.EPHEMERAL and any(
        value is not None for value in natal_values
    ):
        raise ValueError("ephemeral matter profile rejects natal input")
    if election_class is WesternElectionClass.RADICAL and any(
        value is None for value in natal_values
    ):
        raise ValueError("radical matter profile requires complete natal input")

    resolved_reader = reader if reader is not None else get_reader()
    chart = create_chart(
        jd_ut,
        latitude,
        longitude,
        house_system=house_system,
        bodies=list(_TRADITIONAL_BODIES),
        reader=resolved_reader,
        policy=house_policy,
    )
    natal_chart = None
    if election_class is WesternElectionClass.RADICAL:
        natal_chart = create_chart(
            float(natal_jd_ut),
            float(natal_latitude),
            float(natal_longitude),
            house_system=str(natal_house_system),
            bodies=list(_TRADITIONAL_BODIES),
            reader=resolved_reader,
            policy=house_policy,
        )
    eclipse = EclipseCalculator(reader=resolved_reader).calculate_lunar_event_jd(
        jd_ut, kind="penumbral"
    )
    moon_eclipsed = eclipse.is_lunar_eclipse or eclipse.eclipse_type.magnitude_penumbra > 0.0
    reader_path = getattr(resolved_reader, "path", None)
    provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    moon_condition = evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=moon_eclipsed,
        lunar_direction=lunar_ecliptic_direction_at(jd_ut, reader=resolved_reader),
        unavoidable_time_urgency=unavoidable_time_urgency,
        position_product=DOROTHEUS_MOON_CONDITION_V1.position_product,
        reader_provenance=provenance,
    )
    rooted_context = (
        None
        if profile_id in _UNROOTED_EPHEMERAL_PROFILES
        else evaluate_dorotheus_rooted_context(
            chart,
            matter=_ROOTED_MATTERS[profile_id],
            election_class=election_class,
            next_connection=next_moon_connection(jd_ut, reader=resolved_reader),
            natal_chart=natal_chart,
            reader_provenance=provenance,
            policy=DOROTHEUS_ROOTED_CONTEXT_V1,
        )
    )
    dt = resolved_policy.latitude_rate_sample_days
    before = planet_at(Body.MOON, jd_ut - dt, reader=resolved_reader)
    after = planet_at(Body.MOON, jd_ut + dt, reader=resolved_reader)
    latitude_rate = (after.latitude - before.latitude) / (2.0 * dt)
    moon_flow = (
        moon_connection_flow_at(
            jd_ut,
            policy=moon_flow_policy,
            reader=resolved_reader,
        )
        if moon_flow_policy is not None
        else None
    )
    moon_mean_ecliptic = (
        planet_at(
            Body.MOON,
            jd_ut,
            reader=resolved_reader,
            nutation=False,
            jd_tt=chart.jd_tt,
        ).longitude
        if profile_id in {
            DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
            DorotheusMatterProfileId.TRAVEL,
            DorotheusMatterProfileId.SHIP_CONSTRUCTION,
            DorotheusMatterProfileId.WRITING_A_WILL,
        }
        else None
    )
    return evaluate_dorotheus_matter_profile(
        chart,
        profile_id=profile_id,
        moon_condition=moon_condition,
        rooted_context=rooted_context,
        moon_connection_flow=moon_flow,
        moon_latitude_rate_degrees_per_day=latitude_rate,
        moon_true_longitude_mean_ecliptic_degrees=moon_mean_ecliptic,
        natal_chart=natal_chart,
        reader_provenance=provenance,
        policy=resolved_policy,
    )
