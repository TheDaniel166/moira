"""First-class, source-scoped Pancha Pakshi public surface.

Pancha Pakshi is represented as a registry of named computational profiles,
not as one ambient canon.  Every computation therefore requires an explicit
``profile_id``.  The 1879 Madras profile remains an aksara/query-or-name-
initial operating schedule.  A separate Bogamuni 2024 profile preserves a
source-attested Paksha-and-nakshatra bird table and admits an explicit modern
Moira composition that applies that table to the apparent Lahiri sidereal
natal Moon.  The source table itself is not relabelled as a birth-Moon rule.

The private :mod:`moira._pancha_pakshi` module owns hash-verified source-data
ingestion and exact table materialization.  This module owns the stable public
vessels and delegates to that private layer without exposing its raw profile
object.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._local_solar_day import LocalSolarDay
    from ._pancha_pakshi import PanchaPakshiProfile
    from .spk_reader import SpkReader


class PanchaPakshiError(RuntimeError):
    """Base error for public Pancha Pakshi computation."""


class PanchaPakshiDataError(PanchaPakshiError):
    """Raised when bundled Pancha Pakshi data fails closed."""


class PanchaPakshiAdmissionStatus(str, Enum):
    """Admission state of one explicitly named profile."""

    RESEARCH_ONLY = "research_only"
    SOURCE_SCOPED_PUBLIC = "source_scoped_public"
    CORROBORATED_PUBLIC = "corroborated_public"


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiConstitutionStatus:
    """Public governance status without exposing private research data."""

    process: str = field(default="SCP", init=False)
    completed_phases: tuple[int, ...] = field(
        default=tuple(range(1, 13)), init=False
    )
    admission_status: PanchaPakshiAdmissionStatus = field(
        default=PanchaPakshiAdmissionStatus.RESEARCH_ONLY, init=False
    )
    public_product: str = field(
        default="constitutional_status_only", init=False
    )
    historical_data_status: str = field(default="private_not_exposed", init=False)
    network_status: str = field(
        default="private_structural_no_admitted_edges", init=False
    )
    relation_semantics_status: str = field(default="not_admitted", init=False)
    graph_metric_status: str = field(
        default="not_evaluable_no_admitted_relation_edges", init=False
    )
    condition_evaluation_status: str = field(
        default="not_evaluable_no_admitted_condition_doctrine", init=False
    )
    prognosis_status: str = field(default="not_performed", init=False)
    medical_use_status: str = field(default="forbidden", init=False)
    manifest_profile_status: str = field(default="not_admitted", init=False)
    rest_route_status: str = field(
        default="admitted_governance_status_only", init=False
    )


class PanchaPakshiCapability(str, Enum):
    """Independently admitted computation available from a profile."""

    AKSARA_IDENTITY = "aksara_identity"
    NOMINAL_SCHEDULE = "nominal_schedule"
    DIRECTED_RELATIONSHIPS = "directed_relationships"
    ASTRONOMICAL_CONTEXT = "astronomical_context"
    ASTRONOMICAL_PAKSHA_INFERENCE = "astronomical_paksha_inference"
    NAKSHATRA_BIRD_MAPPING = "nakshatra_bird_mapping"
    NATAL_IDENTITY = "natal_identity"
    PADU_BIRD_MAPPING = "padu_bird_mapping"
    FIRST_EAT_BIRD_MAPPING = "first_eat_bird_mapping"
    SOOKSHMA_TEMPORAL_SELECTION = "sookshma_temporal_selection"
    FIXED_CLOCK_MATERIALIZATION = "fixed_clock_materialization"
    FIXED_CLOCK_CURRENT_CELL_SELECTION = "fixed_clock_current_cell_selection"
    SOLAR_PROPORTIONAL_MATERIALIZATION = "solar_proportional_materialization"
    SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION = (
        "solar_proportional_current_cell_selection"
    )
    AUTHORITY_BIRDS = "authority_birds"
    SUBDIVISIONS = "subdivisions"
    CONDITION = "condition"
    SCORING = "scoring"
    WINDOW_SEARCH = "window_search"


class PanchaPakshiBird(str, Enum):
    """Vessel: Registry of Pancha Pakshi bird values."""
    VULTURE = "vulture"
    OWL = "owl"
    CROW = "crow"
    COCK = "cock"
    PEACOCK = "peacock"


class PanchaPakshiActivity(str, Enum):
    """Vessel: Registry of Pancha Pakshi activity values."""
    EAT = "eat"
    WALK = "walk"
    RULE = "rule"
    SLEEP = "sleep"
    DIE = "die"


class PanchaPakshiSookshmaSelectorPolicyId(str, Enum):
    """Explicitly selectable, source-scoped Sookshma partition doctrines."""

    WEIGHTED_SOOKSHMA = "bogamuni_2024_weighted_sookshma_samam_v1"
    EKA_SOOKSHMA_EQUAL_FIFTHS = (
        "bogamuni_2024_eka_sookshma_equal_fifths_v1"
    )


class PanchaPakshiSookshmaTimingPolicyId(str, Enum):
    """Explicit existing materialization used for civil-time routing."""

    FIXED_CLOCK = "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    SOLAR_PROPORTIONAL = (
        "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
    )


class PanchaPakshiPaksha(str, Enum):
    """Profile-owned source labels, distinct from astronomical phase halves."""

    PURVA = "purva"
    AMARA = "amara"


class PanchaPakshiAstronomicalPaksha(str, Enum):
    """Geocentric lunar phase halves used by the explicit inference product."""

    SHUKLA = "shukla"
    KRISHNA = "krishna"


class PanchaPakshiHalf(str, Enum):
    """Vessel: Registry of Pancha Pakshi half values."""
    DAY = "day"
    NIGHT = "night"


class PanchaPakshiWeekday(str, Enum):
    """Vessel: Registry of Pancha Pakshi weekday values."""
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"


class PanchaPakshiRelation(str, Enum):
    """Vessel: Registry of Pancha Pakshi relation values."""
    FRIEND = "friend"
    ENEMY = "enemy"


class PanchaPakshiSolarBoundaryRelation(str, Enum):
    """Relation of the fixed 30-nazhigai end to the solar-half end."""

    ENDS_BEFORE_SOLAR_BOUNDARY = "ends_before_solar_boundary"
    ENDS_AT_SOLAR_BOUNDARY = "ends_at_solar_boundary"
    ENDS_AFTER_SOLAR_BOUNDARY = "ends_after_solar_boundary"


class PanchaPakshiMaterializedCellRelation(str, Enum):
    """Relation of one fixed-clock cell to the governing solar-half end."""

    WITHIN_GOVERNING_SOLAR_HALF = "within_governing_solar_half"
    CROSSES_GOVERNING_SOLAR_HALF_END = "crosses_governing_solar_half_end"
    AFTER_GOVERNING_SOLAR_HALF = "after_governing_solar_half"


class PanchaPakshiCurrentCellSelectionStatus(str, Enum):
    """Outcome of one explicitly governed current-cell selection."""

    SELECTED = "selected"
    UNMATERIALIZED_SOLAR_HALF_TAIL = "unmaterialized_solar_half_tail"


@dataclass(frozen=True, slots=True)
class PanchaPakshiSourceLocator:
    """Vessel: Structured Pancha Pakshi source locator data."""
    locator_id: str
    witness_id: str
    label: str
    url: str
    evidence_role: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiSource:
    """Vessel: Structured Pancha Pakshi source data."""
    witness_id: str
    title: str
    traditional_attribution: str
    authorship_status: str
    publication_place: str
    publisher: str
    publication_year: int
    language: str
    archive_item_url: str
    archive_original_image_zip_name: str
    archive_original_image_zip_source_status: str
    archive_original_image_zip_md5: str
    archive_original_image_zip_sha1: str
    archive_pdf_name: str
    archive_pdf_source_status: str
    archive_pdf_md5: str
    archive_pdf_sha1: str
    locally_verified_pdf_sha256: str
    catalogued_contributor_note: str
    artifact_distribution_status: str
    redistribution_policy: str
    license_scope: str
    artifact_distribution_note: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiProfileDescriptor:
    """Vessel: Structured Pancha Pakshi profile descriptor data."""
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiOmission:
    """Vessel: Structured Pancha Pakshi omission data."""
    feature: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiConflictWitness:
    """Vessel: Structured Pancha Pakshi conflict witness data."""
    witness_id: str
    bibliographic_label: str
    record_url: str
    record_identity: str
    conflict_locators: tuple[str, ...]
    evidence_status: str
    runtime_status: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiProvenance:
    """Profile-owned provenance carried by every public computation."""

    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str
    derivation_status: str
    assembly_policy: str
    astronomical_routing_status: str
    source: PanchaPakshiSource
    declared_omissions: tuple[PanchaPakshiOmission, ...]


@dataclass(frozen=True, slots=True)
class PanchaPakshiProfileInfo:
    """Complete public description of one admitted profile."""

    title: str
    provenance: PanchaPakshiProvenance
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    known_conflict_witnesses: tuple[PanchaPakshiConflictWitness, ...]


@dataclass(frozen=True, slots=True)
class PanchaPakshiAstronomicalPakshaInferencePolicy:
    """The fixed astronomical and source-mapping doctrine for Stage 2F.

    The astronomical object is the apparent geocentric Moon-minus-Sun
    longitude in the true ecliptic of date.  Its two half-open semicircles
    define Shukla and Krishna; a profile-owned, source-attested mapping then
    translates those astronomical halves to Purva and Amara.  This vessel is
    immutable and has no caller-configurable switches.
    """

    policy_id: str = field(
        default="apparent_geocentric_moon_sun_longitude_paksha_half_open_v1",
        init=False,
    )
    input_time_scale: str = field(default="ut1", init=False)
    ephemeris_time_scale: str = field(default="reader_bound_tt", init=False)
    position_origin: str = field(default="geocentric", init=False)
    position_frame: str = field(default="true_ecliptic_of_date", init=False)
    apparent: bool = field(default=True, init=False)
    aberration: bool = field(default=True, init=False)
    grav_deflection: bool = field(default=True, init=False)
    nutation: bool = field(default=True, init=False)
    elongation_definition: str = field(
        default="normalized_moon_longitude_minus_sun_longitude",
        init=False,
    )
    elongation_domain: str = field(
        default="degrees_half_open_0_360",
        init=False,
    )
    shukla_interval: str = field(
        default="0_inclusive_180_exclusive",
        init=False,
    )
    krishna_interval: str = field(
        default="180_inclusive_360_exclusive",
        init=False,
    )
    boundary_tolerance_degrees: float = field(default=0.0, init=False)
    ayanamsa_status: str = field(
        default="not_applied_common_longitude_offset_cancels",
        init=False,
    )
    profile_mapping_basis: str = field(
        default="direct_source_attested_waxing_waning",
        init=False,
    )
    purva_source_locator_id: str = field(default="ia_n16", init=False)
    amara_source_locator_id: str = field(default="ia_n26", init=False)
    schedule_selection_status: str = field(default="not_performed", init=False)
    materialization_status: str = field(default="not_performed", init=False)
    natal_identity_status: str = field(default="not_performed", init=False)


@dataclass(frozen=True, slots=True)
class PanchaPakshiAstronomicalPakshaInference:
    """One instantaneous astronomical phase-half to profile-label inference."""

    profile_id: str
    requested_jd_ut1: float
    requested_jd_tt: float
    policy: PanchaPakshiAstronomicalPakshaInferencePolicy
    sun_longitude_deg: float
    moon_longitude_deg: float
    moon_minus_sun_elongation_deg: float
    astronomical_paksha: PanchaPakshiAstronomicalPaksha
    profile_paksha: PanchaPakshiPaksha
    mapping_status: str
    mapping_source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str):
            raise TypeError("profile_id must be a string")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        for name, value in (
            ("requested_jd_ut1", self.requested_jd_ut1),
            ("requested_jd_tt", self.requested_jd_tt),
            ("sun_longitude_deg", self.sun_longitude_deg),
            ("moon_longitude_deg", self.moon_longitude_deg),
            (
                "moon_minus_sun_elongation_deg",
                self.moon_minus_sun_elongation_deg,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        for name, value in (
            ("sun_longitude_deg", self.sun_longitude_deg),
            ("moon_longitude_deg", self.moon_longitude_deg),
            (
                "moon_minus_sun_elongation_deg",
                self.moon_minus_sun_elongation_deg,
            ),
        ):
            if not 0.0 <= value < 360.0:
                raise ValueError(f"{name} must lie in [0, 360)")
        if not isinstance(
            self.policy,
            PanchaPakshiAstronomicalPakshaInferencePolicy,
        ):
            raise TypeError(
                "policy must be a "
                "PanchaPakshiAstronomicalPakshaInferencePolicy"
            )
        if not isinstance(
            self.astronomical_paksha,
            PanchaPakshiAstronomicalPaksha,
        ):
            raise TypeError(
                "astronomical_paksha must be a PanchaPakshiAstronomicalPaksha"
            )
        if not isinstance(self.profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if self.mapping_status != "direct_source_attested":
            raise ValueError("mapping_status must be direct_source_attested")
        if (
            not isinstance(self.mapping_source_locators, tuple)
            or len(self.mapping_source_locators) != 1
            or not isinstance(
                self.mapping_source_locators[0],
                PanchaPakshiSourceLocator,
            )
        ):
            raise TypeError(
                "mapping_source_locators must contain one source locator"
            )
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        if self.provenance.profile_id != self.profile_id:
            raise ValueError("provenance profile disagrees with profile_id")
        if (
            PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE
            not in self.provenance.capabilities
        ):
            raise ValueError(
                "provenance does not admit astronomical paksha inference"
            )

        expected_elongation = (
            self.moon_longitude_deg - self.sun_longitude_deg
        ) % 360.0
        if self.moon_minus_sun_elongation_deg != expected_elongation:
            raise ValueError(
                "moon_minus_sun_elongation_deg disagrees with the longitudes"
            )

        if self.moon_minus_sun_elongation_deg < 180.0:
            expected_astronomical = PanchaPakshiAstronomicalPaksha.SHUKLA
            expected_profile = PanchaPakshiPaksha.PURVA
            expected_locator_id = self.policy.purva_source_locator_id
        else:
            expected_astronomical = PanchaPakshiAstronomicalPaksha.KRISHNA
            expected_profile = PanchaPakshiPaksha.AMARA
            expected_locator_id = self.policy.amara_source_locator_id
        if self.astronomical_paksha is not expected_astronomical:
            raise ValueError(
                "astronomical_paksha disagrees with half-open elongation policy"
            )
        if self.profile_paksha is not expected_profile:
            raise ValueError(
                "profile_paksha disagrees with the source-attested mapping"
            )
        if self.mapping_source_locators[0].locator_id != expected_locator_id:
            raise ValueError(
                "mapping source locator disagrees with the inferred paksha"
            )
        canonical_profile = _profile_for_public_capability(
            self.profile_id,
            PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE,
        )
        if (
            self.mapping_source_locators[0]
            != canonical_profile.locator(expected_locator_id)
        ):
            raise ValueError(
                "mapping source locator disagrees with the canonical "
                "profile locator"
            )
        if (
            self.mapping_source_locators[0].witness_id
            != self.provenance.source.witness_id
        ):
            raise ValueError(
                "mapping source locator disagrees with the provenance witness"
            )
        if self.provenance.astronomical_routing_status != (
            "astronomical_paksha_inference_performed_source_mapped_no_"
            "schedule_materialization_or_natal_identity"
        ):
            raise ValueError(
                "provenance does not describe the astronomical paksha route"
            )


@dataclass(frozen=True, slots=True)
class PanchaPakshiNakshatraBirdMapping:
    """One pure source-table mapping, without a natal-Moon claim.

    The Bogamuni witness associates each named nakshatra with one bird in each
    of its Purva and Amara partitions.  This immutable vessel represents only
    that source statement.  It does not select an epoch, compute a Moon, or
    assert that the table itself is explicitly natal.
    """

    profile_id: str
    profile_paksha: PanchaPakshiPaksha
    nakshatra_index: int
    nakshatra: str
    bird: PanchaPakshiBird
    mapping_status: str
    source_table_semantics: str
    assembly_policy: str
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        from .sidereal import NAKSHATRA_NAMES

        if not isinstance(self.profile_id, str):
            raise TypeError("profile_id must be a string")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        if not isinstance(self.profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if isinstance(self.nakshatra_index, bool) or not isinstance(
            self.nakshatra_index,
            int,
        ):
            raise TypeError("nakshatra_index must be an integer")
        if not 0 <= self.nakshatra_index < len(NAKSHATRA_NAMES):
            raise ValueError("nakshatra_index must lie in [0, 26]")
        if self.nakshatra != NAKSHATRA_NAMES[self.nakshatra_index]:
            raise ValueError("nakshatra disagrees with nakshatra_index")
        if not isinstance(self.bird, PanchaPakshiBird):
            raise TypeError("bird must be a PanchaPakshiBird")
        if self.mapping_status != "direct_source_attested":
            raise ValueError("mapping_status must be direct_source_attested")
        if self.source_table_semantics != (
            "nakshatra_bird_table_not_explicitly_natal_moon"
        ):
            raise ValueError("source_table_semantics is unknown")
        if self.assembly_policy != "verse_precedence_for_nakshatra_partition":
            raise ValueError("assembly_policy is unknown")
        if (
            not isinstance(self.source_locators, tuple)
            or len(self.source_locators) != 1
            or not isinstance(self.source_locators[0], PanchaPakshiSourceLocator)
        ):
            raise TypeError("source_locators must contain one source locator")
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        if self.provenance.profile_id != self.profile_id:
            raise ValueError("provenance profile disagrees with profile_id")
        if (
            PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING
            not in self.provenance.capabilities
        ):
            raise ValueError("provenance does not admit nakshatra-bird mapping")
        if self.provenance.assembly_policy != self.assembly_policy:
            raise ValueError("provenance assembly policy disagrees with mapping")

        profile = _profile_for_public_capability(
            self.profile_id,
            PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
        )
        rule = profile.nakshatra_bird_rule(
            self.profile_paksha,
            self.nakshatra_index,
        )
        if rule.nakshatra != self.nakshatra or rule.bird is not self.bird:
            raise ValueError("mapping disagrees with the canonical source table")
        if rule.source_locator_ids != (self.source_locators[0].locator_id,):
            raise ValueError("mapping source locator disagrees with source table")
        if self.source_locators[0] != profile.locator(rule.source_locator_ids[0]):
            raise ValueError("mapping source locator is not canonical")


@dataclass(frozen=True, slots=True)
class PanchaPakshiFirstEatBirdMapping:
    """One source generator's weekday first-samam EAT seed.

    This pure lookup exposes the bird from which the named source schedule
    begins.  It does not materialize that schedule or reinterpret the seed as
    Padu, an authority bird, condition, score, or forecast.
    """

    profile_id: str
    generator_id: str
    profile_paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    first_eat_bird: PanchaPakshiBird
    mapping_status: str
    source_table_semantics: str
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str):
            raise TypeError("profile_id must be a string")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        if not isinstance(self.generator_id, str):
            raise TypeError("generator_id must be a string")
        if not self.generator_id:
            raise ValueError("generator_id must not be empty")
        if not isinstance(self.profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if not isinstance(self.half, PanchaPakshiHalf):
            raise TypeError("half must be a PanchaPakshiHalf")
        if not isinstance(self.weekday, PanchaPakshiWeekday):
            raise TypeError("weekday must be a PanchaPakshiWeekday")
        if not isinstance(self.first_eat_bird, PanchaPakshiBird):
            raise TypeError("first_eat_bird must be a PanchaPakshiBird")
        if self.mapping_status != "direct_source_attested":
            raise ValueError("mapping_status must be direct_source_attested")
        if self.source_table_semantics != (
            "profile_paksha_half_weekday_first_samam_eat_seed_not_padu_"
            "authority_condition_or_score"
        ):
            raise ValueError("source_table_semantics is unknown")
        if (
            not isinstance(self.source_locators, tuple)
            or not self.source_locators
            or any(
                not isinstance(locator, PanchaPakshiSourceLocator)
                for locator in self.source_locators
            )
        ):
            raise TypeError(
                "source_locators must contain canonical generator locators"
            )
        if len(
            {locator.locator_id for locator in self.source_locators}
        ) != len(self.source_locators):
            raise ValueError("source_locators must be unique")
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        if self.provenance.profile_id != self.profile_id:
            raise ValueError("provenance profile disagrees with profile_id")
        if (
            PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING
            not in self.provenance.capabilities
        ):
            raise ValueError(
                "provenance does not admit first-EAT-bird mapping"
            )
        if self.provenance.astronomical_routing_status != "not_performed":
            raise ValueError(
                "first-EAT-bird lookup must not perform astronomical routing"
            )

        from ._pancha_pakshi import _profile_provenance

        profile = _profile_for_public_capability(
            self.profile_id,
            PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING,
        )
        if self.provenance != _profile_provenance(profile):
            raise ValueError("provenance is not canonical")
        generator = profile.generator(self.profile_paksha, self.half)
        if self.generator_id != generator.generator_id:
            raise ValueError(
                "generator_id disagrees with profile_paksha and half"
            )
        expected_bird = generator.first_eat_bird_for(self.weekday)
        if self.first_eat_bird is not expected_bird:
            raise ValueError("mapping disagrees with the canonical source table")
        canonical_locators = tuple(
            profile.locator(locator_id)
            for locator_id in generator.source_locator_ids
        )
        if self.source_locators != canonical_locators:
            raise ValueError(
                "mapping source locators are not canonical generator locators"
            )
        if any(
            locator.witness_id != self.provenance.source.witness_id
            for locator in self.source_locators
        ):
            raise ValueError("mapping source locators disagree with provenance")


@dataclass(frozen=True, slots=True)
class PanchaPakshiPaduBirdMapping:
    """One source-attested Paksha-and-weekday Padu bird.

    The source describes the Padu bird as the weekday's death or inoperative
    bird.  This pure lookup does not select a day/night half, inspect a
    schedule, or reinterpret the bird as an instantaneous ``RULE`` activity.
    """

    profile_id: str
    profile_paksha: PanchaPakshiPaksha
    weekday: PanchaPakshiWeekday
    bird: PanchaPakshiBird
    mapping_status: str
    source_table_semantics: str
    assembly_policy: str
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str):
            raise TypeError("profile_id must be a string")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        if not isinstance(self.profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if not isinstance(self.weekday, PanchaPakshiWeekday):
            raise TypeError("weekday must be a PanchaPakshiWeekday")
        if not isinstance(self.bird, PanchaPakshiBird):
            raise TypeError("bird must be a PanchaPakshiBird")
        if self.mapping_status != "direct_source_attested":
            raise ValueError("mapping_status must be direct_source_attested")
        if self.source_table_semantics != (
            "profile_paksha_weekday_death_or_inoperative_bird_not_schedule_"
            "rule_activity"
        ):
            raise ValueError("source_table_semantics is unknown")
        if self.assembly_policy != (
            "paksha_stanzas_govern_repeated_combined_table_confirms"
        ):
            raise ValueError("assembly_policy is unknown")
        if (
            not isinstance(self.source_locators, tuple)
            or len(self.source_locators) != 3
            or any(
                not isinstance(locator, PanchaPakshiSourceLocator)
                for locator in self.source_locators
            )
        ):
            raise TypeError("source_locators must contain three source locators")
        if len({locator.locator_id for locator in self.source_locators}) != 3:
            raise ValueError("source_locators must be unique")
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        if self.provenance.profile_id != self.profile_id:
            raise ValueError("provenance profile disagrees with profile_id")
        if (
            PanchaPakshiCapability.PADU_BIRD_MAPPING
            not in self.provenance.capabilities
        ):
            raise ValueError("provenance does not admit Padu-bird mapping")
        if self.provenance.assembly_policy != self.assembly_policy:
            raise ValueError("provenance assembly policy disagrees with mapping")
        if self.provenance.astronomical_routing_status != "not_performed":
            raise ValueError("Padu-bird lookup must not perform astronomical routing")

        from ._pancha_pakshi import _profile_provenance

        profile = _profile_for_public_capability(
            self.profile_id,
            PanchaPakshiCapability.PADU_BIRD_MAPPING,
        )
        if self.provenance != _profile_provenance(profile):
            raise ValueError("provenance is not canonical")
        rule = profile.padu_bird_rule(self.profile_paksha, self.weekday)
        if rule.bird is not self.bird:
            raise ValueError("mapping disagrees with the canonical source table")
        canonical_locators = tuple(
            profile.locator(locator_id) for locator_id in rule.source_locator_ids
        )
        if self.source_locators != canonical_locators:
            raise ValueError("mapping source locators are not canonical")
        if any(
            locator.witness_id != self.provenance.source.witness_id
            for locator in self.source_locators
        ):
            raise ValueError("mapping source locators disagree with provenance")


@dataclass(frozen=True, slots=True)
class PanchaPakshiSookshmaSelectorPolicy:
    """One explicitly selected source-attested Sookshma partition doctrine."""

    policy_id: PanchaPakshiSookshmaSelectorPolicyId
    source_layer: str
    partition_kind: str
    container_span_nazhigai: Fraction
    interval_count: int
    interval_ownership: str
    sequence_policy: str
    activity_assignment_status: str
    activity_durations_nazhigai: tuple[
        tuple[PanchaPakshiActivity, Fraction], ...
    ]
    automatic_policy_selection: str
    uromarisi_composition_status: str
    outcome_interpretation_status: str
    source_locator_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.policy_id,
            PanchaPakshiSookshmaSelectorPolicyId,
        ):
            raise TypeError(
                "policy_id must be a PanchaPakshiSookshmaSelectorPolicyId"
            )
        if self.container_span_nazhigai != Fraction(6):
            raise ValueError("Sookshma policy container must span six nazhigai")
        if self.interval_count != 5:
            raise ValueError("Sookshma policy must define five intervals")
        if self.interval_ownership != "half_open":
            raise ValueError("Sookshma interval ownership must be half_open")
        if self.automatic_policy_selection != "forbidden":
            raise ValueError("automatic Sookshma policy selection is forbidden")
        if self.uromarisi_composition_status != (
            "not_performed_requires_separate_explicit_cross_witness_decision"
        ):
            raise ValueError("Uromarisi composition status is not canonical")
        if self.outcome_interpretation_status != "not_performed":
            raise ValueError("outcome interpretation must remain not_performed")
        if (
            not isinstance(self.source_locator_ids, tuple)
            or len(self.source_locator_ids) != 2
            or any(
                not isinstance(locator_id, str) or not locator_id
                for locator_id in self.source_locator_ids
            )
        ):
            raise TypeError("source_locator_ids must contain two locator ids")

        weighted_durations = (
            (PanchaPakshiActivity.EAT, Fraction(3, 2)),
            (PanchaPakshiActivity.WALK, Fraction(5, 4)),
            (PanchaPakshiActivity.RULE, Fraction(2)),
            (PanchaPakshiActivity.SLEEP, Fraction(3, 4)),
            (PanchaPakshiActivity.DIE, Fraction(1, 2)),
        )
        if (
            self.policy_id
            is PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
        ):
            if self.source_layer != "sookshma_pakshi_editorial_section":
                raise ValueError("weighted Sookshma source layer is unknown")
            if self.partition_kind != "weighted_activity_durations":
                raise ValueError("weighted Sookshma partition kind is unknown")
            if self.sequence_policy != (
                "cyclic_activity_order_with_each_row_beginning_at_its_named_"
                "activity"
            ):
                raise ValueError("weighted Sookshma sequence policy is unknown")
            if self.activity_assignment_status != (
                "source_attested_cyclic_activity_rows"
            ):
                raise ValueError(
                    "weighted Sookshma activity assignment is unknown"
                )
            if self.activity_durations_nazhigai != weighted_durations:
                raise ValueError(
                    "weighted Sookshma activity durations are not canonical"
                )
            if sum(
                (duration for _, duration in self.activity_durations_nazhigai),
                Fraction(),
            ) != self.container_span_nazhigai:
                raise ValueError("weighted Sookshma durations do not close")
        else:
            if self.source_layer != "eka_sookshma_chakra_editorial_section":
                raise ValueError("Eka Sookshma source layer is unknown")
            if self.partition_kind != "five_equal_parts":
                raise ValueError("Eka Sookshma partition kind is unknown")
            if self.sequence_policy != (
                "ordinal_only_no_subactivity_assignment_attested"
            ):
                raise ValueError("Eka Sookshma sequence policy is unknown")
            if self.activity_assignment_status != "not_attested":
                raise ValueError(
                    "Eka Sookshma must not invent activity assignments"
                )
            if self.activity_durations_nazhigai:
                raise ValueError(
                    "Eka Sookshma must not carry weighted activity durations"
                )


@dataclass(frozen=True, slots=True)
class PanchaPakshiSookshmaInterval:
    """One exact half-open position inside a selected Sookshma policy."""

    ordinal: int
    activity: PanchaPakshiActivity | None
    start_nazhigai: Fraction
    end_nazhigai: Fraction
    duration_nazhigai: Fraction

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int):
            raise TypeError("ordinal must be an integer")
        if not 1 <= self.ordinal <= 5:
            raise ValueError("ordinal must lie in [1, 5]")
        if self.activity is not None and not isinstance(
            self.activity,
            PanchaPakshiActivity,
        ):
            raise TypeError("activity must be a PanchaPakshiActivity or None")
        for name, value in (
            ("start_nazhigai", self.start_nazhigai),
            ("end_nazhigai", self.end_nazhigai),
            ("duration_nazhigai", self.duration_nazhigai),
        ):
            if not isinstance(value, Fraction):
                raise TypeError(f"{name} must be a Fraction")
        if not (
            Fraction() <= self.start_nazhigai < self.end_nazhigai <= Fraction(6)
        ):
            raise ValueError("Sookshma interval bounds must lie within [0, 6]")
        if self.end_nazhigai - self.start_nazhigai != self.duration_nazhigai:
            raise ValueError("Sookshma interval duration disagrees with bounds")


def _sookshma_intervals_for_policy(
    policy: PanchaPakshiSookshmaSelectorPolicy,
    parent_activity: PanchaPakshiActivity,
) -> tuple[PanchaPakshiSookshmaInterval, ...]:
    if not isinstance(policy, PanchaPakshiSookshmaSelectorPolicy):
        raise TypeError("policy must be a PanchaPakshiSookshmaSelectorPolicy")
    if not isinstance(parent_activity, PanchaPakshiActivity):
        raise TypeError("parent_activity must be a PanchaPakshiActivity")

    if (
        policy.policy_id
        is PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
    ):
        activity_order = tuple(PanchaPakshiActivity)
        start_index = activity_order.index(parent_activity)
        ordered_activities = (
            activity_order[start_index:] + activity_order[:start_index]
        )
        durations = dict(policy.activity_durations_nazhigai)
        cells = tuple(
            (activity, durations[activity]) for activity in ordered_activities
        )
    else:
        cells = tuple(
            (None, policy.container_span_nazhigai / policy.interval_count)
            for _ in range(policy.interval_count)
        )

    intervals: list[PanchaPakshiSookshmaInterval] = []
    cursor = Fraction()
    for ordinal, (activity, duration) in enumerate(cells, start=1):
        end = cursor + duration
        intervals.append(
            PanchaPakshiSookshmaInterval(
                ordinal=ordinal,
                activity=activity,
                start_nazhigai=cursor,
                end_nazhigai=end,
                duration_nazhigai=duration,
            )
        )
        cursor = end
    if cursor != policy.container_span_nazhigai:
        raise PanchaPakshiDataError("Sookshma intervals do not close exactly")
    return tuple(intervals)


@dataclass(frozen=True, slots=True)
class PanchaPakshiSookshmaSelection:
    """One exact policy-selected Sookshma ordinal without outcome semantics."""

    profile_id: str
    parent_activity: PanchaPakshiActivity
    elapsed_nazhigai: Fraction
    policy: PanchaPakshiSookshmaSelectorPolicy
    intervals: tuple[PanchaPakshiSookshmaInterval, ...]
    selected_ordinal: int
    selected_interval: PanchaPakshiSookshmaInterval
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str):
            raise TypeError("profile_id must be a string")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        if not isinstance(self.parent_activity, PanchaPakshiActivity):
            raise TypeError("parent_activity must be a PanchaPakshiActivity")
        if not isinstance(self.elapsed_nazhigai, Fraction):
            raise TypeError("elapsed_nazhigai must be a Fraction")
        if not Fraction() <= self.elapsed_nazhigai < Fraction(6):
            raise ValueError("elapsed_nazhigai must lie in the half-open [0, 6)")
        if not isinstance(self.policy, PanchaPakshiSookshmaSelectorPolicy):
            raise TypeError(
                "policy must be a PanchaPakshiSookshmaSelectorPolicy"
            )
        expected_intervals = _sookshma_intervals_for_policy(
            self.policy,
            self.parent_activity,
        )
        if self.intervals != expected_intervals:
            raise ValueError("Sookshma intervals are not canonical")
        matches = tuple(
            interval
            for interval in self.intervals
            if interval.start_nazhigai
            <= self.elapsed_nazhigai
            < interval.end_nazhigai
        )
        if len(matches) != 1:
            raise ValueError("Sookshma selection must have exactly one match")
        if self.selected_interval != matches[0]:
            raise ValueError("selected_interval is not the exact half-open match")
        if self.selected_ordinal != self.selected_interval.ordinal:
            raise ValueError("selected_ordinal disagrees with selected_interval")
        if (
            not isinstance(self.source_locators, tuple)
            or len(self.source_locators) != 2
            or any(
                not isinstance(locator, PanchaPakshiSourceLocator)
                for locator in self.source_locators
            )
        ):
            raise TypeError("source_locators must contain two canonical locators")
        if tuple(
            locator.locator_id for locator in self.source_locators
        ) != self.policy.source_locator_ids:
            raise ValueError("source locators disagree with selected policy")
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        if self.provenance.profile_id != self.profile_id:
            raise ValueError("provenance profile disagrees with profile_id")
        if (
            PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION
            not in self.provenance.capabilities
        ):
            raise ValueError(
                "provenance does not admit Sookshma temporal selection"
            )
        if self.provenance.astronomical_routing_status != "not_performed":
            raise ValueError(
                "Sookshma temporal selection must not route astronomy"
            )

        from ._pancha_pakshi import _profile_provenance, _resolve_locators

        profile = _profile_for_public_capability(
            self.profile_id,
            PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION,
        )
        rule = profile.sookshma_policy_rule(self.policy.policy_id)
        if self.policy != _sookshma_public_policy(profile, rule):
            raise ValueError("selected Sookshma policy is not canonical")
        if self.source_locators != _resolve_locators(
            profile,
            rule.source_locator_ids,
        ):
            raise ValueError("source locators are not canonical")
        if self.provenance != _profile_provenance(profile):
            raise ValueError("provenance is not canonical")


@dataclass(frozen=True, slots=True)
class PanchaPakshiScheduleSookshmaCompositionPolicy:
    """Explicit modern policy joining one schedule samam to one selector.

    The caller continues to own every doctrinal choice: both profiles, the
    schedule axes, the subject bird, the Sookshma selector, and the exact
    elapsed offset.  This policy derives only the subject bird's parent
    activity in the named samam.  It performs no clock routing or outcome
    interpretation.
    """

    policy_id: str = field(
        default="explicit_schedule_samam_subject_bird_sookshma_v1",
        init=False,
    )
    composition_status: str = field(
        default="modern_moira_policy_not_source_claim",
        init=False,
    )
    schedule_selection_basis: str = field(
        default="caller_named_profile_paksha_half_weekday_and_samam",
        init=False,
    )
    parent_activity_basis: str = field(
        default="unique_subject_bird_cell_in_selected_schedule_samam",
        init=False,
    )
    selector_policy_basis: str = field(
        default="caller_named_no_default",
        init=False,
    )
    elapsed_offset_basis: str = field(
        default="caller_supplied_exact_nazhigai_within_samam",
        init=False,
    )
    clock_or_civil_time_routing_status: str = field(
        default="not_performed",
        init=False,
    )
    uromarisi_outcome_binding_status: str = field(
        default="not_performed",
        init=False,
    )
    outcome_interpretation_status: str = field(
        default="not_performed",
        init=False,
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiScheduleSookshmaSelection:
    """One explicit cross-profile schedule-to-Sookshma composition."""

    schedule_profile_id: str
    selector_profile_id: str
    schedule: PanchaPakshiSchedule
    samam_index: int
    subject_bird: PanchaPakshiBird
    parent_schedule_cell: PanchaPakshiScheduleCell
    elapsed_nazhigai: Fraction
    composition_policy: PanchaPakshiScheduleSookshmaCompositionPolicy
    sookshma_selection: PanchaPakshiSookshmaSelection

    def __post_init__(self) -> None:
        for name, value in (
            ("schedule_profile_id", self.schedule_profile_id),
            ("selector_profile_id", self.selector_profile_id),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            if not value:
                raise ValueError(f"{name} must not be empty")
        if not isinstance(self.schedule, PanchaPakshiSchedule):
            raise TypeError("schedule must be a PanchaPakshiSchedule")
        if self.schedule.profile_id != self.schedule_profile_id:
            raise ValueError("schedule profile disagrees with schedule_profile_id")
        if isinstance(self.samam_index, bool) or not isinstance(
            self.samam_index,
            int,
        ):
            raise TypeError("samam_index must be an integer")
        if not 1 <= self.samam_index <= 5:
            raise ValueError("samam_index must lie in [1, 5]")
        if not isinstance(self.subject_bird, PanchaPakshiBird):
            raise TypeError("subject_bird must be a PanchaPakshiBird")
        if not isinstance(self.parent_schedule_cell, PanchaPakshiScheduleCell):
            raise TypeError(
                "parent_schedule_cell must be a PanchaPakshiScheduleCell"
            )
        matches = tuple(
            cell
            for cell in self.schedule.cells
            if cell.samam_index == self.samam_index
            and cell.bird is self.subject_bird
        )
        if len(matches) != 1 or self.parent_schedule_cell != matches[0]:
            raise ValueError(
                "parent_schedule_cell must be the unique subject-bird cell "
                "in the selected samam"
            )
        if not isinstance(self.elapsed_nazhigai, Fraction):
            raise TypeError("elapsed_nazhigai must be a Fraction")
        if not Fraction() <= self.elapsed_nazhigai < Fraction(6):
            raise ValueError("elapsed_nazhigai must lie in the half-open [0, 6)")
        if not isinstance(
            self.composition_policy,
            PanchaPakshiScheduleSookshmaCompositionPolicy,
        ):
            raise TypeError(
                "composition_policy must be a "
                "PanchaPakshiScheduleSookshmaCompositionPolicy"
            )
        if not isinstance(
            self.sookshma_selection,
            PanchaPakshiSookshmaSelection,
        ):
            raise TypeError(
                "sookshma_selection must be a PanchaPakshiSookshmaSelection"
            )
        if self.sookshma_selection.profile_id != self.selector_profile_id:
            raise ValueError(
                "Sookshma selection profile disagrees with selector_profile_id"
            )
        if (
            self.sookshma_selection.parent_activity
            is not self.parent_schedule_cell.activity
        ):
            raise ValueError(
                "Sookshma parent activity disagrees with the schedule cell"
            )
        if self.sookshma_selection.elapsed_nazhigai != self.elapsed_nazhigai:
            raise ValueError(
                "Sookshma elapsed offset disagrees with the composition"
            )

        canonical_schedule = pancha_pakshi_schedule(
            self.schedule_profile_id,
            paksha=self.schedule.paksha,
            half=self.schedule.half,
            weekday=self.schedule.weekday,
        )
        if self.schedule != canonical_schedule:
            raise ValueError("schedule is not canonical")
        canonical_selection = pancha_pakshi_sookshma_temporal_selection(
            self.selector_profile_id,
            policy_id=self.sookshma_selection.policy.policy_id,
            parent_activity=self.parent_schedule_cell.activity,
            elapsed_nazhigai=self.elapsed_nazhigai,
        )
        if self.sookshma_selection != canonical_selection:
            raise ValueError("Sookshma selection is not canonical")


@dataclass(frozen=True, slots=True)
class PanchaPakshiCivilTimeSookshmaRoutingPolicy:
    """Modern Stage 2O clock route into the exact Stage 2N composition."""

    policy_id: str = field(
        default="civil_time_materialized_samam_to_stage2n_v1",
        init=False,
    )
    composition_status: str = field(
        default="modern_moira_policy_not_source_claim",
        init=False,
    )
    timing_policy_selection: str = field(
        default="caller_named_no_default",
        init=False,
    )
    selector_policy_selection: str = field(
        default="caller_named_no_default",
        init=False,
    )
    selection_time_scale: str = field(
        default="reader_bound_tt",
        init=False,
    )
    samam_derivation: str = field(
        default="current_materialized_cell_nominal_samam_index",
        init=False,
    )
    elapsed_derivation: str = field(
        default=(
            "binary64_tt_values_lifted_exactly_to_fraction_then_normalized_"
            "over_materialized_samam_span_times_six"
        ),
        init=False,
    )
    interval_ownership: str = field(default="half_open", init=False)
    fixed_tail_policy: str = field(
        default="preserve_explicit_unmaterialized_solar_half_tail",
        init=False,
    )
    automatic_timing_fallback: str = field(default="forbidden", init=False)
    astronomical_paksha_inference_status: str = field(
        default="not_performed",
        init=False,
    )
    uromarisi_outcome_binding_status: str = field(
        default="not_performed",
        init=False,
    )
    outcome_interpretation_status: str = field(
        default="not_performed",
        init=False,
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiCivilTimeSookshmaSelection:
    """One civil instant routed through explicit timing and selector policies."""

    schedule_profile_id: str
    selector_profile_id: str
    timing_policy_id: PanchaPakshiSookshmaTimingPolicyId
    selector_policy_id: PanchaPakshiSookshmaSelectorPolicyId
    subject_bird: PanchaPakshiBird
    routing_policy: PanchaPakshiCivilTimeSookshmaRoutingPolicy
    current_cell_selection: (
        PanchaPakshiFixedClockCurrentCellSelection
        | PanchaPakshiSolarProportionalCurrentCellSelection
    )
    selection_status: PanchaPakshiCurrentCellSelectionStatus
    samam_index: int | None
    samam_start_jd_tt: float | None
    samam_end_jd_tt: float | None
    elapsed_nazhigai: Fraction | None
    composition: PanchaPakshiScheduleSookshmaSelection | None

    def __post_init__(self) -> None:
        for name, value in (
            ("schedule_profile_id", self.schedule_profile_id),
            ("selector_profile_id", self.selector_profile_id),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            if not value:
                raise ValueError(f"{name} must not be empty")
        if not isinstance(
            self.timing_policy_id,
            PanchaPakshiSookshmaTimingPolicyId,
        ):
            raise TypeError(
                "timing_policy_id must be a PanchaPakshiSookshmaTimingPolicyId"
            )
        if not isinstance(
            self.selector_policy_id,
            PanchaPakshiSookshmaSelectorPolicyId,
        ):
            raise TypeError(
                "selector_policy_id must be a "
                "PanchaPakshiSookshmaSelectorPolicyId"
            )
        if not isinstance(self.subject_bird, PanchaPakshiBird):
            raise TypeError("subject_bird must be a PanchaPakshiBird")
        if not isinstance(
            self.routing_policy,
            PanchaPakshiCivilTimeSookshmaRoutingPolicy,
        ):
            raise TypeError(
                "routing_policy must be a "
                "PanchaPakshiCivilTimeSookshmaRoutingPolicy"
            )
        fixed = isinstance(
            self.current_cell_selection,
            PanchaPakshiFixedClockCurrentCellSelection,
        )
        proportional = isinstance(
            self.current_cell_selection,
            PanchaPakshiSolarProportionalCurrentCellSelection,
        )
        if fixed == proportional:
            raise TypeError(
                "current_cell_selection must be exactly one admitted timing "
                "selection vessel"
            )
        expected_timing_policy_id = (
            PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK
            if fixed
            else PanchaPakshiSookshmaTimingPolicyId.SOLAR_PROPORTIONAL
        )
        if self.timing_policy_id is not expected_timing_policy_id:
            raise ValueError(
                "timing_policy_id disagrees with current_cell_selection"
            )
        materialization = self.current_cell_selection.materialization
        context = materialization.context
        if context.profile_id != self.schedule_profile_id:
            raise ValueError(
                "timing selection profile disagrees with schedule_profile_id"
            )
        if materialization.policy.policy_id != self.timing_policy_id.value:
            raise ValueError(
                "timing policy does not match the materialization policy"
            )
        if not isinstance(
            self.selection_status,
            PanchaPakshiCurrentCellSelectionStatus,
        ):
            raise TypeError(
                "selection_status must be a "
                "PanchaPakshiCurrentCellSelectionStatus"
            )
        if (
            self.selection_status
            is not self.current_cell_selection.selection_status
        ):
            raise ValueError(
                "selection_status disagrees with current_cell_selection"
            )

        if self.selection_status is (
            PanchaPakshiCurrentCellSelectionStatus
            .UNMATERIALIZED_SOLAR_HALF_TAIL
        ):
            if not fixed:
                raise ValueError(
                    "only fixed-clock routing can produce an unmaterialized tail"
                )
            if any(
                value is not None
                for value in (
                    self.samam_index,
                    self.samam_start_jd_tt,
                    self.samam_end_jd_tt,
                    self.elapsed_nazhigai,
                    self.composition,
                )
            ):
                raise ValueError(
                    "unmaterialized tail must not contain a derived composition"
                )
            return

        if self.selection_status is not (
            PanchaPakshiCurrentCellSelectionStatus.SELECTED
        ):
            raise ValueError("unsupported Stage 2O selection status")
        if self.current_cell_selection.current_cell is None:
            raise ValueError("selected timing route requires a current cell")
        if (
            isinstance(self.samam_index, bool)
            or not isinstance(self.samam_index, int)
            or not 1 <= self.samam_index <= 5
        ):
            raise ValueError("selected route requires samam_index in [1, 5]")
        for name, value in (
            ("samam_start_jd_tt", self.samam_start_jd_tt),
            ("samam_end_jd_tt", self.samam_end_jd_tt),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not self.samam_start_jd_tt < self.samam_end_jd_tt:
            raise ValueError("materialized samam endpoints must increase")
        if not isinstance(self.elapsed_nazhigai, Fraction):
            raise TypeError("elapsed_nazhigai must be a Fraction")
        if not Fraction() <= self.elapsed_nazhigai < Fraction(6):
            raise ValueError("elapsed_nazhigai must lie in [0, 6)")
        if not isinstance(
            self.composition,
            PanchaPakshiScheduleSookshmaSelection,
        ):
            raise TypeError(
                "composition must be a PanchaPakshiScheduleSookshmaSelection"
            )

        current_cell = self.current_cell_selection.current_cell
        if current_cell.nominal_cell.samam_index != self.samam_index:
            raise ValueError("samam_index disagrees with current materialized cell")
        (
            expected_start,
            expected_end,
            expected_elapsed,
        ) = _stage2o_materialized_samam_coordinates(
            self.current_cell_selection,
            self.samam_index,
        )
        if self.samam_start_jd_tt != expected_start:
            raise ValueError("samam_start_jd_tt is not canonical")
        if self.samam_end_jd_tt != expected_end:
            raise ValueError("samam_end_jd_tt is not canonical")
        if self.elapsed_nazhigai != expected_elapsed:
            raise ValueError("elapsed_nazhigai is not canonical")
        if self.composition.schedule_profile_id != self.schedule_profile_id:
            raise ValueError("composition schedule profile is not canonical")
        if self.composition.selector_profile_id != self.selector_profile_id:
            raise ValueError("composition selector profile is not canonical")
        if self.composition.samam_index != self.samam_index:
            raise ValueError("composition samam is not canonical")
        if self.composition.subject_bird is not self.subject_bird:
            raise ValueError("composition subject bird is not canonical")
        if self.composition.elapsed_nazhigai != self.elapsed_nazhigai:
            raise ValueError("composition elapsed offset is not canonical")
        if (
            self.composition.sookshma_selection.policy.policy_id
            is not self.selector_policy_id
        ):
            raise ValueError("composition selector policy is not canonical")


@dataclass(frozen=True, slots=True)
class PanchaPakshiNatalMoonIdentityPolicy:
    """Fixed Stage 2G doctrine for the Bogamuni natal-Moon composition."""

    policy_id: str = field(
        default="bogamuni_2024_apparent_lahiri_natal_moon_identity_v1",
        init=False,
    )
    composition_status: str = field(
        default="modern_moira_policy_not_source_claim",
        init=False,
    )
    source_table_semantics: str = field(
        default="nakshatra_bird_table_not_explicitly_natal_moon",
        init=False,
    )
    input_time_scale: str = field(default="ut1", init=False)
    ephemeris_time_scale: str = field(default="reader_bound_tt", init=False)
    position_origin: str = field(default="geocentric", init=False)
    position_frame: str = field(default="true_ecliptic_of_date", init=False)
    apparent: bool = field(default=True, init=False)
    aberration: bool = field(default=True, init=False)
    grav_deflection: bool = field(default=True, init=False)
    nutation: bool = field(default=True, init=False)
    elongation_definition: str = field(
        default="normalized_moon_longitude_minus_sun_longitude",
        init=False,
    )
    shukla_interval: str = field(
        default="0_inclusive_180_exclusive",
        init=False,
    )
    krishna_interval: str = field(
        default="180_inclusive_360_exclusive",
        init=False,
    )
    phase_boundary_tolerance_degrees: float = field(default=0.0, init=False)
    phase_to_profile_mapping: str = field(
        default="direct_source_attested_new_moon_purva_full_moon_amara",
        init=False,
    )
    phase_mapping_source_locator_id: str = field(
        default="bogar_n167_phase",
        init=False,
    )
    ayanamsa_system: str = field(default="Lahiri", init=False)
    ayanamsa_mode: str = field(default="true", init=False)
    ayanamsa_status: str = field(
        default="fixed_modern_moira_policy_not_source_attested",
        init=False,
    )
    nakshatra_partition: str = field(
        default="27_equal_half_open_40_over_3_degree_sectors",
        init=False,
    )
    exact_internal_boundary_ownership: str = field(
        default="following_nakshatra",
        init=False,
    )
    binary_boundary_recovery: str = field(
        default="maximum_one_ulp_below_internal_boundary",
        init=False,
    )
    mapping_assembly_policy: str = field(
        default="verse_precedence_for_nakshatra_partition",
        init=False,
    )
    schedule_selection_status: str = field(default="not_performed", init=False)
    materialization_status: str = field(default="not_performed", init=False)
    current_cell_status: str = field(default="not_performed", init=False)
    scoring_status: str = field(default="not_performed", init=False)
    forecast_status: str = field(default="not_performed", init=False)


@dataclass(frozen=True, slots=True)
class PanchaPakshiNatalMoonIdentity:
    """One modern natal-Moon composition over a source-owned bird table."""

    profile_id: str
    requested_jd_ut1: float
    requested_jd_tt: float
    policy: PanchaPakshiNatalMoonIdentityPolicy
    sun_longitude_deg: float
    moon_tropical_longitude_deg: float
    moon_minus_sun_elongation_deg: float
    astronomical_paksha: PanchaPakshiAstronomicalPaksha
    profile_paksha: PanchaPakshiPaksha
    phase_mapping_source_locators: tuple[PanchaPakshiSourceLocator, ...]
    ayanamsa_deg: float
    moon_sidereal_longitude_deg: float
    nakshatra_index: int
    nakshatra: str
    degrees_in_nakshatra: float
    bird: PanchaPakshiBird
    bird_mapping: PanchaPakshiNakshatraBirdMapping
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        from .sidereal import (
            NAKSHATRA_NAMES,
            NAKSHATRA_SPAN,
            _nakshatra_position_from_sidereal,
        )

        if not isinstance(self.profile_id, str):
            raise TypeError("profile_id must be a string")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        for name, value in (
            ("requested_jd_ut1", self.requested_jd_ut1),
            ("requested_jd_tt", self.requested_jd_tt),
            ("sun_longitude_deg", self.sun_longitude_deg),
            ("moon_tropical_longitude_deg", self.moon_tropical_longitude_deg),
            (
                "moon_minus_sun_elongation_deg",
                self.moon_minus_sun_elongation_deg,
            ),
            ("ayanamsa_deg", self.ayanamsa_deg),
            ("moon_sidereal_longitude_deg", self.moon_sidereal_longitude_deg),
            ("degrees_in_nakshatra", self.degrees_in_nakshatra),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        for name, value in (
            ("sun_longitude_deg", self.sun_longitude_deg),
            ("moon_tropical_longitude_deg", self.moon_tropical_longitude_deg),
            (
                "moon_minus_sun_elongation_deg",
                self.moon_minus_sun_elongation_deg,
            ),
            ("moon_sidereal_longitude_deg", self.moon_sidereal_longitude_deg),
        ):
            if not 0.0 <= value < 360.0:
                raise ValueError(f"{name} must lie in [0, 360)")
        if not isinstance(self.policy, PanchaPakshiNatalMoonIdentityPolicy):
            raise TypeError("policy must be a PanchaPakshiNatalMoonIdentityPolicy")
        if not isinstance(self.astronomical_paksha, PanchaPakshiAstronomicalPaksha):
            raise TypeError(
                "astronomical_paksha must be a PanchaPakshiAstronomicalPaksha"
            )
        if not isinstance(self.profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if (
            not isinstance(self.phase_mapping_source_locators, tuple)
            or len(self.phase_mapping_source_locators) != 1
            or not isinstance(
                self.phase_mapping_source_locators[0],
                PanchaPakshiSourceLocator,
            )
        ):
            raise TypeError(
                "phase_mapping_source_locators must contain one source locator"
            )
        if isinstance(self.nakshatra_index, bool) or not isinstance(
            self.nakshatra_index,
            int,
        ):
            raise TypeError("nakshatra_index must be an integer")
        if not 0 <= self.nakshatra_index < len(NAKSHATRA_NAMES):
            raise ValueError("nakshatra_index must lie in [0, 26]")
        if self.nakshatra != NAKSHATRA_NAMES[self.nakshatra_index]:
            raise ValueError("nakshatra disagrees with nakshatra_index")
        if not 0.0 <= self.degrees_in_nakshatra < NAKSHATRA_SPAN:
            raise ValueError("degrees_in_nakshatra lies outside its sector")
        canonical_nakshatra = _nakshatra_position_from_sidereal(
            self.moon_sidereal_longitude_deg
        )
        if (
            self.nakshatra_index != canonical_nakshatra.nakshatra_index
            or self.nakshatra != canonical_nakshatra.nakshatra
            or self.degrees_in_nakshatra != canonical_nakshatra.degrees_in
        ):
            raise ValueError(
                "nakshatra index, name, and degrees must equal the shared "
                "sidereal classification of moon_sidereal_longitude_deg"
            )
        if not isinstance(self.bird, PanchaPakshiBird):
            raise TypeError("bird must be a PanchaPakshiBird")
        if not isinstance(self.bird_mapping, PanchaPakshiNakshatraBirdMapping):
            raise TypeError(
                "bird_mapping must be a PanchaPakshiNakshatraBirdMapping"
            )
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        if self.provenance.profile_id != self.profile_id:
            raise ValueError("provenance profile disagrees with profile_id")
        if PanchaPakshiCapability.NATAL_IDENTITY not in self.provenance.capabilities:
            raise ValueError("provenance does not admit natal identity")
        if self.provenance.astronomical_routing_status != (
            "natal_moon_identity_performed_modern_lahiri_composition_no_"
            "schedule_materialization_current_cell_scoring_or_forecast"
        ):
            raise ValueError("provenance does not describe the natal-Moon route")

        expected_elongation = (
            self.moon_tropical_longitude_deg - self.sun_longitude_deg
        ) % 360.0
        if self.moon_minus_sun_elongation_deg != expected_elongation:
            raise ValueError("elongation disagrees with the tropical longitudes")
        expected_astronomical = (
            PanchaPakshiAstronomicalPaksha.SHUKLA
            if expected_elongation < 180.0
            else PanchaPakshiAstronomicalPaksha.KRISHNA
        )
        if self.astronomical_paksha is not expected_astronomical:
            raise ValueError("astronomical_paksha disagrees with elongation")
        if not math.isclose(
            (self.moon_tropical_longitude_deg - self.ayanamsa_deg) % 360.0,
            self.moon_sidereal_longitude_deg,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("sidereal longitude disagrees with the ayanamsa")
        if (
            self.bird_mapping.profile_id != self.profile_id
            or self.bird_mapping.profile_paksha is not self.profile_paksha
            or self.bird_mapping.nakshatra_index != self.nakshatra_index
            or self.bird_mapping.nakshatra != self.nakshatra
            or self.bird_mapping.bird is not self.bird
            or self.bird_mapping.provenance != self.provenance
        ):
            raise ValueError("bird mapping disagrees with the natal identity")

        profile = _profile_for_public_capability(
            self.profile_id,
            PanchaPakshiCapability.NATAL_IDENTITY,
        )
        phase_rule = profile.lunar_paksha_mapping_rule(self.astronomical_paksha)
        if phase_rule.profile_paksha is not self.profile_paksha:
            raise ValueError("profile Paksha disagrees with the source phase mapping")
        if phase_rule.source_locator_ids != (
            self.phase_mapping_source_locators[0].locator_id,
        ):
            raise ValueError("phase locator disagrees with the source phase mapping")
        if self.phase_mapping_source_locators[0] != profile.locator(
            phase_rule.source_locator_ids[0]
        ):
            raise ValueError("phase mapping source locator is not canonical")


@dataclass(frozen=True, slots=True)
class PanchaPakshiInitialVowelIdentity:
    """Vessel: Structured Pancha Pakshi initial vowel identity data."""
    profile_id: str
    identity_kind: str
    input_symbol: str
    normalized_symbol: str
    bird: PanchaPakshiBird
    is_natal_moon_identity: bool
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance


@dataclass(frozen=True, slots=True)
class PanchaPakshiDirectedRelationship:
    """Vessel: Structured Pancha Pakshi directed relationship data."""
    profile_id: str
    model_kind: str
    subject: PanchaPakshiBird
    target: PanchaPakshiBird
    relation: PanchaPakshiRelation
    is_reciprocal_inference: bool
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    provenance: PanchaPakshiProvenance


@dataclass(frozen=True, slots=True)
class PanchaPakshiScheduleCell:
    """Vessel: Structured Pancha Pakshi schedule cell data."""
    samam_index: int
    sequence_index: int
    bird: PanchaPakshiBird
    activity: PanchaPakshiActivity
    start_nazhigai: Fraction
    end_nazhigai: Fraction
    duration_nazhigai: Fraction
    derivation_status: str
    assembly_policy: str
    source_locators: tuple[PanchaPakshiSourceLocator, ...]


@dataclass(frozen=True, slots=True)
class PanchaPakshiSchedule:
    """Vessel: Structured Pancha Pakshi schedule data."""
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    generator_id: str
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    first_eat_bird: PanchaPakshiBird
    temporal_model_kind: str
    span_nazhigai: Fraction
    samam_span_nazhigai: Fraction
    cells: tuple[PanchaPakshiScheduleCell, ...]
    provenance: PanchaPakshiProvenance

    def cell_at_nazhigai(
        self, offset_nazhigai: Fraction | int
    ) -> PanchaPakshiScheduleCell:
        """Return the half-open cell containing an exact nominal offset."""

        if isinstance(offset_nazhigai, bool) or not isinstance(
            offset_nazhigai, (Fraction, int)
        ):
            raise TypeError("offset_nazhigai must be an int or Fraction")
        offset = Fraction(offset_nazhigai)
        if offset < 0 or offset >= self.span_nazhigai:
            raise ValueError(
                "offset_nazhigai must lie in the half-open interval "
                f"[0, {self.span_nazhigai})"
            )
        for cell in self.cells:
            if cell.start_nazhigai <= offset < cell.end_nazhigai:
                return cell
        raise PanchaPakshiDataError(
            "validated schedule contains an uncovered nominal offset"
        )


@dataclass(frozen=True, slots=True)
class PanchaPakshiLocalSolarContextPolicy:
    """The one admitted local-solar routing policy for Stage 2A.

    All fields are fixed rather than caller-configurable.  The policy derives
    only the enclosing solar half and its local-mean-solar weekday.  Paksha
    remains an explicit source label supplied by the caller, and nominal
    nazhigai offsets are not projected onto clock time.
    """

    policy_id: str = field(
        default="local_solar_day_explicit_paksha_v1", init=False
    )
    paksha_basis: str = field(
        default="caller_supplied_source_label", init=False
    )
    solar_day_basis: str = field(
        default="topocentric_sunrise_to_next_sunrise", init=False
    )
    solar_event_altitude_deg: float = field(default=-0.833, init=False)
    observer_elevation_m: float = field(default=0.0, init=False)
    solar_altitude_refraction_mode: str = field(
        default="unrefracted_signal_standard_refraction_and_semidiameter_in_threshold",
        init=False,
    )
    half_basis: str = field(
        default="topocentric_sunrise_sunset", init=False
    )
    weekday_basis: str = field(
        default="local_mean_solar_time_at_governing_sunrise", init=False
    )
    offset_materialization_status: str = field(
        default="not_performed", init=False
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiLocalSolarContext:
    """One nominal schedule selected by a bounded local-solar context.

    The three event epochs and the requested epoch are UT1 Julian Days.  This
    vessel intentionally contains no current cell or materialized cell clock
    intervals because Stage 2A admits neither fixed-clock anchoring nor solar-
    proportional scaling.
    """

    profile_id: str
    requested_jd_ut1: float
    latitude: float
    longitude: float
    sunrise_jd_ut1: float
    sunset_jd_ut1: float
    next_sunrise_jd_ut1: float
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    policy: PanchaPakshiLocalSolarContextPolicy
    nominal_schedule: PanchaPakshiSchedule
    provenance: PanchaPakshiProvenance


@dataclass(frozen=True, slots=True)
class PanchaPakshiFixedClockMaterializationPolicy:
    """The bounded modern composition admitted for Phase 2B.

    Source-owned nominal offsets remain exact.  The modern policy anchors the
    selected half at its topocentric solar start, advances those offsets on a
    uniform TT elapsed-time coordinate, and reports rather than repairs any
    mismatch with the governing solar-half end.
    """

    policy_id: str = field(
        default="fixed_24_minute_nazhigai_from_local_solar_half_start_v1",
        init=False,
    )
    paksha_basis: str = field(
        default="caller_supplied_source_label",
        init=False,
    )
    solar_context_basis: str = field(
        default="topocentric_sunrise_to_next_sunrise",
        init=False,
    )
    day_anchor: str = field(
        default="governing_topocentric_sunrise",
        init=False,
    )
    night_anchor: str = field(
        default="governing_topocentric_sunset",
        init=False,
    )
    nazhigai_seconds: int = field(default=1440, init=False)
    half_span_nazhigai: int = field(default=30, init=False)
    half_span_seconds: int = field(default=43_200, init=False)
    offset_arithmetic_time_scale: str = field(
        default="reader_bound_tt",
        init=False,
    )
    published_endpoint_time_scale: str = field(default="ut1", init=False)
    interval_ownership: str = field(default="half_open", init=False)
    solar_end_clipping: str = field(default="none", init=False)
    topology_metric: str = field(
        default="fixed_end_jd_tt_minus_solar_end_jd_tt",
        init=False,
    )
    topology_coalescence_seconds: float = field(default=0.0001, init=False)
    current_cell_status: str = field(
        default="not_performed",
        init=False,
    )
    solar_proportional_scaling_status: str = field(
        default="not_performed",
        init=False,
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiFixedClockCell:
    """One nominal cell materialized on paired TT and UT1 coordinates."""

    schedule_cell_index: int
    nominal_cell: PanchaPakshiScheduleCell
    start_jd_tt: float
    end_jd_tt: float
    start_jd_ut1: float
    end_jd_ut1: float
    duration_seconds: Fraction
    solar_half_relation: PanchaPakshiMaterializedCellRelation


@dataclass(frozen=True, slots=True)
class PanchaPakshiFixedClockMaterialization:
    """Fixed-clock projection of one selected nominal half.

    No current-cell judgment is present.  Long and short solar halves remain
    visible through the signed boundary residual and the cell relations.
    """

    context: PanchaPakshiLocalSolarContext
    policy: PanchaPakshiFixedClockMaterializationPolicy
    anchor_jd_tt: float
    anchor_jd_ut1: float
    governing_solar_half_end_jd_tt: float
    governing_solar_half_end_jd_ut1: float
    fixed_end_jd_tt: float
    fixed_end_jd_ut1: float
    signed_fixed_end_minus_solar_end_seconds_tt: float
    solar_boundary_relation: PanchaPakshiSolarBoundaryRelation
    cells: tuple[PanchaPakshiFixedClockCell, ...]
    provenance: PanchaPakshiProvenance


@dataclass(frozen=True, slots=True)
class PanchaPakshiFixedClockCurrentCellSelectionPolicy:
    """The bounded modern current-cell doctrine admitted for Stage 2C.

    The governing astronomical half is resolved before fixed-clock membership.
    Membership then uses the materializer's reader-bound TT endpoints with
    exact half-open ownership.  No tolerance, clipping, wrap, repetition,
    scaling, or astronomical paksha inference is permitted.
    """

    policy_id: str = field(
        default="fixed_clock_current_cell_half_open_solar_precedence_v1",
        init=False,
    )
    materialization_policy_id: str = field(
        default="fixed_24_minute_nazhigai_from_local_solar_half_start_v1",
        init=False,
    )
    paksha_basis: str = field(
        default="caller_supplied_source_label",
        init=False,
    )
    selection_time_scale: str = field(default="reader_bound_tt", init=False)
    interval_ownership: str = field(default="half_open", init=False)
    solar_half_precedence: str = field(
        default="resolve_governing_solar_half_before_selection",
        init=False,
    )
    membership_tolerance_seconds: float = field(default=0.0, init=False)
    unmaterialized_solar_half_tail: str = field(
        default="explicit_no_current_cell",
        init=False,
    )
    solar_end_clipping: str = field(default="none", init=False)
    fixed_span_wrap: str = field(default="none", init=False)
    fixed_span_repeat: str = field(default="none", init=False)
    solar_proportional_scaling_status: str = field(
        default="not_performed",
        init=False,
    )
    astronomical_paksha_inference_status: str = field(
        default="not_performed",
        init=False,
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiFixedClockCurrentCellSelection:
    """Current fixed-clock cell under governing-solar-half precedence."""

    materialization: PanchaPakshiFixedClockMaterialization
    policy: PanchaPakshiFixedClockCurrentCellSelectionPolicy
    requested_jd_tt: float
    selection_status: PanchaPakshiCurrentCellSelectionStatus
    current_cell: PanchaPakshiFixedClockCell | None
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(
            self.materialization,
            PanchaPakshiFixedClockMaterialization,
        ):
            raise TypeError(
                "materialization must be a PanchaPakshiFixedClockMaterialization"
            )
        if not isinstance(
            self.policy,
            PanchaPakshiFixedClockCurrentCellSelectionPolicy,
        ):
            raise TypeError(
                "policy must be a PanchaPakshiFixedClockCurrentCellSelectionPolicy"
            )
        if isinstance(self.requested_jd_tt, bool) or not isinstance(
            self.requested_jd_tt,
            (int, float),
        ):
            raise TypeError("requested_jd_tt must be a real number")
        if not math.isfinite(self.requested_jd_tt):
            raise ValueError("requested_jd_tt must be finite")
        if not isinstance(
            self.selection_status,
            PanchaPakshiCurrentCellSelectionStatus,
        ):
            raise TypeError(
                "selection_status must be a PanchaPakshiCurrentCellSelectionStatus"
            )
        if self.current_cell is not None and not isinstance(
            self.current_cell,
            PanchaPakshiFixedClockCell,
        ):
            raise TypeError(
                "current_cell must be a PanchaPakshiFixedClockCell or None"
            )
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")

        materialization = self.materialization
        if (
            self.policy.materialization_policy_id
            != materialization.policy.policy_id
        ):
            raise ValueError(
                "selection policy does not bind the supplied materialization policy"
            )
        if self.provenance.profile_id != materialization.context.profile_id:
            raise ValueError(
                "selection provenance profile disagrees with the materialization"
            )
        if (
            PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION
            not in self.provenance.capabilities
        ):
            raise ValueError(
                "selection provenance does not admit fixed-clock current-cell selection"
            )
        if not (
            materialization.anchor_jd_tt
            <= self.requested_jd_tt
            < materialization.governing_solar_half_end_jd_tt
        ):
            raise ValueError(
                "requested_jd_tt must lie in the governing half-open solar half"
            )

        matches = tuple(
            cell
            for cell in materialization.cells
            if cell.start_jd_tt <= self.requested_jd_tt < cell.end_jd_tt
        )
        if self.selection_status is PanchaPakshiCurrentCellSelectionStatus.SELECTED:
            if self.current_cell is None:
                raise ValueError("selected status requires a current cell")
            if len(matches) != 1 or matches[0] is not self.current_cell:
                raise ValueError(
                    "selected current cell must be the unique half-open TT match"
                )
            return

        if self.selection_status is not (
            PanchaPakshiCurrentCellSelectionStatus.UNMATERIALIZED_SOLAR_HALF_TAIL
        ):
            raise ValueError("unsupported current-cell selection status")
        if self.current_cell is not None:
            raise ValueError(
                "unmaterialized solar-half tail status requires current_cell=None"
            )
        if matches:
            raise ValueError(
                "unmaterialized solar-half tail cannot contain a materialized cell"
            )
        if not (
            materialization.fixed_end_jd_tt
            < materialization.governing_solar_half_end_jd_tt
            and materialization.fixed_end_jd_tt
            <= self.requested_jd_tt
            < materialization.governing_solar_half_end_jd_tt
        ):
            raise ValueError(
                "unmaterialized solar-half tail requires fixed_end <= requested "
                "< solar_end with fixed_end < solar_end"
            )


@dataclass(frozen=True, slots=True)
class PanchaPakshiSolarProportionalMaterializationPolicy:
    """The bounded modern solar-proportional doctrine admitted for Stage 2D.

    Exact source-owned nominal offsets become rational fractions of the
    schedule's full 30-nazhigai span.  Each endpoint is then mapped
    independently over the governing local-solar half on reader-bound TT.
    The policy neither interprets one nazhigai as 1,440 seconds nor performs
    current-cell selection or astronomical Paksha inference.
    """

    policy_id: str = field(
        default="solar_proportional_nominal_offsets_over_governing_half_tt_v1",
        init=False,
    )
    paksha_basis: str = field(
        default="caller_supplied_source_label",
        init=False,
    )
    solar_context_basis: str = field(
        default="topocentric_sunrise_to_next_sunrise",
        init=False,
    )
    day_anchor: str = field(
        default="governing_topocentric_sunrise",
        init=False,
    )
    night_anchor: str = field(
        default="governing_topocentric_sunset",
        init=False,
    )
    nominal_offset_basis: str = field(
        default="exact_fraction_of_nominal_schedule_span",
        init=False,
    )
    mapping_time_scale: str = field(default="reader_bound_tt", init=False)
    published_endpoint_time_scale: str = field(default="ut1", init=False)
    endpoint_mapping: str = field(
        default="independent_anchor_plus_fraction_of_governing_solar_half",
        init=False,
    )
    endpoint_closure: str = field(
        default="exact_anchor_and_governing_solar_half_end",
        init=False,
    )
    interval_ownership: str = field(default="half_open", init=False)
    solar_end_clipping: str = field(default="none", init=False)
    solar_half_wrap: str = field(default="none", init=False)
    solar_half_repeat: str = field(default="none", init=False)
    fixed_nazhigai_seconds_status: str = field(
        default="not_used",
        init=False,
    )
    current_cell_status: str = field(default="not_performed", init=False)
    astronomical_paksha_inference_status: str = field(
        default="not_performed",
        init=False,
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiSolarProportionalCell:
    """One nominal cell mapped over the governing solar half.

    The three fractional fields retain the exact rational mapping doctrine.
    TT and UT1 endpoints are floating astronomical coordinates and therefore
    remain distinct from those source-owned fractions.
    """

    schedule_cell_index: int
    nominal_cell: PanchaPakshiScheduleCell
    start_offset_fraction: Fraction
    end_offset_fraction: Fraction
    span_fraction: Fraction
    start_jd_tt: float
    end_jd_tt: float
    start_jd_ut1: float
    end_jd_ut1: float
    duration_seconds_tt: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.schedule_cell_index, bool)
            or not isinstance(self.schedule_cell_index, int)
        ):
            raise TypeError("schedule_cell_index must be an integer")
        if self.schedule_cell_index < 0:
            raise ValueError("schedule_cell_index must be non-negative")
        if not isinstance(self.nominal_cell, PanchaPakshiScheduleCell):
            raise TypeError("nominal_cell must be a PanchaPakshiScheduleCell")

        for name, value in (
            ("start_offset_fraction", self.start_offset_fraction),
            ("end_offset_fraction", self.end_offset_fraction),
            ("span_fraction", self.span_fraction),
        ):
            if not isinstance(value, Fraction):
                raise TypeError(f"{name} must be a Fraction")
        if not (
            Fraction(0) <= self.start_offset_fraction
            < self.end_offset_fraction <= Fraction(1)
        ):
            raise ValueError(
                "solar-proportional offset fractions must satisfy "
                "0 <= start < end <= 1"
            )
        if self.span_fraction != (
            self.end_offset_fraction - self.start_offset_fraction
        ):
            raise ValueError("span_fraction must equal end minus start")

        nominal_span = Fraction(30)
        if self.start_offset_fraction != (
            self.nominal_cell.start_nazhigai / nominal_span
        ):
            raise ValueError(
                "start_offset_fraction disagrees with the nominal cell"
            )
        if self.end_offset_fraction != (
            self.nominal_cell.end_nazhigai / nominal_span
        ):
            raise ValueError(
                "end_offset_fraction disagrees with the nominal cell"
            )
        if self.span_fraction != (
            self.nominal_cell.duration_nazhigai / nominal_span
        ):
            raise ValueError("span_fraction disagrees with the nominal cell")

        for name, value in (
            ("start_jd_tt", self.start_jd_tt),
            ("end_jd_tt", self.end_jd_tt),
            ("start_jd_ut1", self.start_jd_ut1),
            ("end_jd_ut1", self.end_jd_ut1),
            ("duration_seconds_tt", self.duration_seconds_tt),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not self.start_jd_tt < self.end_jd_tt:
            raise ValueError("cell TT endpoints must be strictly increasing")
        if not self.start_jd_ut1 < self.end_jd_ut1:
            raise ValueError("cell UT1 endpoints must be strictly increasing")
        if self.duration_seconds_tt <= 0.0:
            raise ValueError("duration_seconds_tt must be positive")
        endpoint_duration_seconds = (
            self.end_jd_tt - self.start_jd_tt
        ) * 86_400.0
        if not math.isclose(
            self.duration_seconds_tt,
            endpoint_duration_seconds,
            rel_tol=1e-12,
            abs_tol=1e-7,
        ):
            raise ValueError(
                "duration_seconds_tt disagrees with the mapped TT endpoints"
            )


@dataclass(frozen=True, slots=True)
class PanchaPakshiSolarProportionalMaterialization:
    """Solar-proportional projection of one selected nominal half.

    The detached vessel proves its exact fraction-to-TT mapping, outer UT1
    closure, and UT1 ordering/contiguity.  Interior TT-to-UT1 inverse truth is
    reader-dependent and is therefore established by the governing factory,
    not replayed without a reader inside ``__post_init__``.
    """

    context: PanchaPakshiLocalSolarContext
    policy: PanchaPakshiSolarProportionalMaterializationPolicy
    anchor_jd_tt: float
    anchor_jd_ut1: float
    governing_solar_half_end_jd_tt: float
    governing_solar_half_end_jd_ut1: float
    solar_half_duration_seconds_tt: float
    cells: tuple[PanchaPakshiSolarProportionalCell, ...]
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.context, PanchaPakshiLocalSolarContext):
            raise TypeError("context must be a PanchaPakshiLocalSolarContext")
        if not isinstance(
            self.policy,
            PanchaPakshiSolarProportionalMaterializationPolicy,
        ):
            raise TypeError(
                "policy must be a "
                "PanchaPakshiSolarProportionalMaterializationPolicy"
            )
        for name, value in (
            ("anchor_jd_tt", self.anchor_jd_tt),
            ("anchor_jd_ut1", self.anchor_jd_ut1),
            (
                "governing_solar_half_end_jd_tt",
                self.governing_solar_half_end_jd_tt,
            ),
            (
                "governing_solar_half_end_jd_ut1",
                self.governing_solar_half_end_jd_ut1,
            ),
            (
                "solar_half_duration_seconds_tt",
                self.solar_half_duration_seconds_tt,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not self.anchor_jd_tt < self.governing_solar_half_end_jd_tt:
            raise ValueError("governing solar-half TT bounds must be ordered")
        if not self.anchor_jd_ut1 < self.governing_solar_half_end_jd_ut1:
            raise ValueError("governing solar-half UT1 bounds must be ordered")

        expected_anchor_ut1 = (
            self.context.sunrise_jd_ut1
            if self.context.half is PanchaPakshiHalf.DAY
            else self.context.sunset_jd_ut1
        )
        expected_end_ut1 = (
            self.context.sunset_jd_ut1
            if self.context.half is PanchaPakshiHalf.DAY
            else self.context.next_sunrise_jd_ut1
        )
        if self.anchor_jd_ut1 != expected_anchor_ut1:
            raise ValueError("anchor_jd_ut1 disagrees with the governing half")
        if self.governing_solar_half_end_jd_ut1 != expected_end_ut1:
            raise ValueError(
                "governing_solar_half_end_jd_ut1 disagrees with the context"
            )

        endpoint_duration_seconds = (
            self.governing_solar_half_end_jd_tt - self.anchor_jd_tt
        ) * 86_400.0
        if self.solar_half_duration_seconds_tt != endpoint_duration_seconds:
            raise ValueError(
                "solar_half_duration_seconds_tt disagrees with the TT bounds"
            )
        if self.solar_half_duration_seconds_tt <= 0.0:
            raise ValueError("solar_half_duration_seconds_tt must be positive")

        schedule = self.context.nominal_schedule
        if schedule.span_nazhigai != Fraction(30):
            raise ValueError(
                "solar-proportional policy requires a 30-nazhigai schedule"
            )
        if not isinstance(self.cells, tuple):
            raise TypeError("cells must be a tuple")
        if len(self.cells) != len(schedule.cells) or not self.cells:
            raise ValueError(
                "cells must map every nominal schedule cell exactly once"
            )
        governing_span_days_tt = (
            self.governing_solar_half_end_jd_tt - self.anchor_jd_tt
        )
        for schedule_cell_index, (nominal_cell, cell) in enumerate(
            zip(schedule.cells, self.cells, strict=True)
        ):
            if not isinstance(cell, PanchaPakshiSolarProportionalCell):
                raise TypeError(
                    "cells must contain PanchaPakshiSolarProportionalCell values"
                )
            if cell.schedule_cell_index != schedule_cell_index:
                raise ValueError("solar-proportional cell indices are not ordered")
            if cell.nominal_cell != nominal_cell:
                raise ValueError(
                    "solar-proportional cell disagrees with the nominal schedule"
                )
            expected_start_jd_tt = (
                self.anchor_jd_tt
                if cell.start_offset_fraction == 0
                else self.anchor_jd_tt
                + float(cell.start_offset_fraction) * governing_span_days_tt
            )
            expected_end_jd_tt = (
                self.governing_solar_half_end_jd_tt
                if cell.end_offset_fraction == 1
                else self.anchor_jd_tt
                + float(cell.end_offset_fraction) * governing_span_days_tt
            )
            if cell.start_jd_tt != expected_start_jd_tt:
                raise ValueError(
                    "cell start_jd_tt does not match its exact nominal fraction"
                )
            if cell.end_jd_tt != expected_end_jd_tt:
                raise ValueError(
                    "cell end_jd_tt does not match its exact nominal fraction"
                )

        if self.cells[0].start_offset_fraction != Fraction(0):
            raise ValueError("first cell must begin at exact fraction zero")
        if self.cells[-1].end_offset_fraction != Fraction(1):
            raise ValueError("last cell must end at exact fraction one")
        if self.cells[0].start_jd_tt != self.anchor_jd_tt:
            raise ValueError("first cell must close exactly on the TT anchor")
        if self.cells[0].start_jd_ut1 != self.anchor_jd_ut1:
            raise ValueError("first cell must close exactly on the UT1 anchor")
        if (
            self.cells[-1].end_jd_tt
            != self.governing_solar_half_end_jd_tt
        ):
            raise ValueError("last cell must close exactly on the TT solar end")
        if (
            self.cells[-1].end_jd_ut1
            != self.governing_solar_half_end_jd_ut1
        ):
            raise ValueError("last cell must close exactly on the UT1 solar end")
        for left, right in zip(self.cells, self.cells[1:]):
            if left.end_offset_fraction != right.start_offset_fraction:
                raise ValueError("cell fractions must be contiguous")
            if left.end_jd_tt != right.start_jd_tt:
                raise ValueError("cell TT endpoints must be contiguous")
            if left.end_jd_ut1 != right.start_jd_ut1:
                raise ValueError("cell UT1 endpoints must be contiguous")

        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")
        expected_provenance = _solar_proportional_provenance(self.context)
        if self.provenance != expected_provenance:
            raise ValueError(
                "materialization provenance must equal the exact Stage 2D "
                "transformation of its local-solar context provenance"
            )


@dataclass(frozen=True, slots=True)
class PanchaPakshiSolarProportionalCurrentCellSelectionPolicy:
    """The bounded modern proportional current-cell doctrine for Stage 2E.

    The governing Stage 2D materialization is a complete half-open partition
    of its local-solar half.  Selection therefore requires exactly one TT
    match and admits neither a null/tail state nor any repair or inference.
    """

    policy_id: str = field(
        default="solar_proportional_current_cell_half_open_solar_precedence_v1",
        init=False,
    )
    materialization_policy_id: str = field(
        default="solar_proportional_nominal_offsets_over_governing_half_tt_v1",
        init=False,
    )
    paksha_basis: str = field(
        default="caller_supplied_source_label",
        init=False,
    )
    selection_time_scale: str = field(default="reader_bound_tt", init=False)
    interval_ownership: str = field(default="half_open", init=False)
    solar_half_precedence: str = field(
        default="resolve_governing_solar_half_before_selection",
        init=False,
    )
    membership_tolerance_seconds: float = field(default=0.0, init=False)
    coverage_requirement: str = field(
        default="complete_governing_solar_half",
        init=False,
    )
    required_match_count: int = field(default=1, init=False)
    unmaterialized_solar_half_tail_status: str = field(
        default="not_applicable",
        init=False,
    )
    invalid_match_policy: str = field(default="fail_closed", init=False)
    fixed_clock_mixing_status: str = field(
        default="not_performed",
        init=False,
    )
    astronomical_paksha_inference_status: str = field(
        default="not_performed",
        init=False,
    )


@dataclass(frozen=True, slots=True)
class PanchaPakshiSolarProportionalCurrentCellSelection:
    """Unique current cell in one complete Stage 2D materialization."""

    materialization: PanchaPakshiSolarProportionalMaterialization
    policy: PanchaPakshiSolarProportionalCurrentCellSelectionPolicy
    requested_jd_tt: float
    selection_status: PanchaPakshiCurrentCellSelectionStatus
    current_cell: PanchaPakshiSolarProportionalCell
    provenance: PanchaPakshiProvenance

    def __post_init__(self) -> None:
        if not isinstance(
            self.materialization,
            PanchaPakshiSolarProportionalMaterialization,
        ):
            raise TypeError(
                "materialization must be a "
                "PanchaPakshiSolarProportionalMaterialization"
            )
        if not isinstance(
            self.policy,
            PanchaPakshiSolarProportionalCurrentCellSelectionPolicy,
        ):
            raise TypeError(
                "policy must be a "
                "PanchaPakshiSolarProportionalCurrentCellSelectionPolicy"
            )
        if isinstance(self.requested_jd_tt, bool) or not isinstance(
            self.requested_jd_tt,
            (int, float),
        ):
            raise TypeError("requested_jd_tt must be a real number")
        if not math.isfinite(self.requested_jd_tt):
            raise ValueError("requested_jd_tt must be finite")
        if not isinstance(
            self.selection_status,
            PanchaPakshiCurrentCellSelectionStatus,
        ):
            raise TypeError(
                "selection_status must be a PanchaPakshiCurrentCellSelectionStatus"
            )
        if self.selection_status is not PanchaPakshiCurrentCellSelectionStatus.SELECTED:
            raise ValueError(
                "solar-proportional current-cell selection requires selected status"
            )
        if not isinstance(
            self.current_cell,
            PanchaPakshiSolarProportionalCell,
        ):
            raise TypeError(
                "current_cell must be a PanchaPakshiSolarProportionalCell"
            )
        if not isinstance(self.provenance, PanchaPakshiProvenance):
            raise TypeError("provenance must be a PanchaPakshiProvenance")

        materialization = self.materialization
        if (
            self.policy.materialization_policy_id
            != materialization.policy.policy_id
        ):
            raise ValueError(
                "selection policy does not bind the supplied materialization policy"
            )
        if (
            PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION
            not in self.provenance.capabilities
        ):
            raise ValueError(
                "selection provenance does not admit solar-proportional "
                "current-cell selection"
            )
        expected_provenance = _solar_proportional_current_cell_provenance(
            materialization
        )
        if self.provenance != expected_provenance:
            raise ValueError(
                "selection provenance must equal the exact Stage 2E "
                "transformation of its Stage 2D materialization provenance"
            )
        if not (
            materialization.anchor_jd_tt
            <= self.requested_jd_tt
            < materialization.governing_solar_half_end_jd_tt
        ):
            raise ValueError(
                "requested_jd_tt must lie in the governing half-open solar half"
            )

        matches = tuple(
            cell
            for cell in materialization.cells
            if cell.start_jd_tt <= self.requested_jd_tt < cell.end_jd_tt
        )
        if len(matches) != self.policy.required_match_count:
            raise ValueError(
                "solar-proportional materialization must provide exactly one "
                "half-open TT match"
            )
        if matches[0] is not self.current_cell:
            raise ValueError(
                "current_cell must be the unique materialization tuple member"
            )


_WEEKDAY_FROM_LOCAL_SOLAR_INDEX = (
    PanchaPakshiWeekday.SUNDAY,
    PanchaPakshiWeekday.MONDAY,
    PanchaPakshiWeekday.TUESDAY,
    PanchaPakshiWeekday.WEDNESDAY,
    PanchaPakshiWeekday.THURSDAY,
    PanchaPakshiWeekday.FRIDAY,
    PanchaPakshiWeekday.SATURDAY,
)
_LOCAL_SOLAR_ROUTING_STATUS = (
    "local_solar_half_and_weekday_performed_paksha_caller_supplied"
)
_ASTRONOMICAL_PAKSHA_INFERENCE_STATUS = (
    "astronomical_paksha_inference_performed_source_mapped_no_schedule_"
    "materialization_or_natal_identity"
)
_NATAL_MOON_IDENTITY_STATUS = (
    "natal_moon_identity_performed_modern_lahiri_composition_no_schedule_"
    "materialization_current_cell_scoring_or_forecast"
)
_FIXED_CLOCK_MATERIALIZATION_STATUS = (
    "fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell"
)
_FIXED_CLOCK_CURRENT_CELL_SELECTION_STATUS = (
    "fixed_clock_current_cell_selection_performed_paksha_caller_supplied_"
    "no_scaling_or_inference"
)
_SOLAR_PROPORTIONAL_MATERIALIZATION_STATUS = (
    "solar_proportional_materialization_performed_paksha_caller_supplied_"
    "no_current_cell_or_inference"
)
_SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION_STATUS = (
    "solar_proportional_current_cell_selection_performed_paksha_caller_"
    "supplied_no_fixed_clock_mixing_or_inference"
)
_SOLAR_PROPORTIONAL_SOURCE_NONATTESTATION = PanchaPakshiOmission(
    feature="source_attested_solar_proportional_materialization",
    status="omitted",
    reason=(
        "The 1879 witness does not attest solar-proportional scaling; "
        "Moira Stage 2D performs a separately admitted modern proportional "
        "composition under its explicit policy."
    ),
)
_SI_SECONDS_PER_DAY = 86_400


def available_pancha_pakshi_profiles() -> tuple[PanchaPakshiProfileDescriptor, ...]:
    """Return explicitly registered profiles; no default is selected."""

    from ._pancha_pakshi import available_pancha_pakshi_profiles as _available

    return _available()


def pancha_pakshi_uromarisi_constitution_status(
) -> PanchaPakshiUromarisiConstitutionStatus:
    """Return stable SCP closure metadata, never the private research corpus."""

    return PanchaPakshiUromarisiConstitutionStatus()


def _profile_for_public_capability(
    profile_id: str,
    capability: PanchaPakshiCapability | None = None,
):
    from ._pancha_pakshi import load_pancha_pakshi_profile

    profile = load_pancha_pakshi_profile(profile_id)
    if profile.admission_status not in {
        PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
        PanchaPakshiAdmissionStatus.CORROBORATED_PUBLIC,
    }:
        raise ValueError(
            f"Pancha Pakshi profile {profile_id!r} is not publicly admitted"
        )
    if capability is not None and capability not in profile.capabilities:
        raise ValueError(
            f"Pancha Pakshi profile {profile_id!r} does not admit "
            f"{capability.value!r}"
        )
    return profile


def pancha_pakshi_profile_info(profile_id: str) -> PanchaPakshiProfileInfo:
    """Return the public description of one explicitly named profile."""

    from ._pancha_pakshi import (
        pancha_pakshi_profile_info as _profile_info,
    )

    return _profile_info(_profile_for_public_capability(profile_id))


def pancha_pakshi_identity_from_initial_vowel(
    profile_id: str,
    initial_vowel: str,
) -> PanchaPakshiInitialVowelIdentity:
    """Resolve the named profile's aksara/query-or-name initial identity."""

    from ._pancha_pakshi import (
        pancha_pakshi_identity_from_initial_vowel as _identity,
    )

    return _identity(
        _profile_for_public_capability(
            profile_id, PanchaPakshiCapability.AKSARA_IDENTITY
        ),
        initial_vowel,
    )


def pancha_pakshi_directed_relationship(
    profile_id: str,
    subject: PanchaPakshiBird,
    target: PanchaPakshiBird,
) -> PanchaPakshiDirectedRelationship:
    """Return one source-stored directed relationship without inference."""

    from ._pancha_pakshi import (
        pancha_pakshi_directed_relationship as _relationship,
    )

    return _relationship(
        _profile_for_public_capability(
            profile_id, PanchaPakshiCapability.DIRECTED_RELATIONSHIPS
        ),
        subject,
        target,
    )


def _pancha_pakshi_apparent_moon_sun_geometry(
    jd_ut1: float,
    *,
    reader: SpkReader | None,
    policy: (
        PanchaPakshiAstronomicalPakshaInferencePolicy
        | PanchaPakshiNatalMoonIdentityPolicy
    ),
) -> tuple[float, float, float, float]:
    """Return shared reader-bound TT and apparent Sun/Moon phase geometry."""

    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from .constants import Body
    from .planets import planet_at
    from .spk_reader import get_reader

    if isinstance(jd_ut1, bool) or not isinstance(jd_ut1, (int, float)):
        raise TypeError("jd_ut1 must be a real number")
    if not math.isfinite(jd_ut1):
        raise ValueError("jd_ut1 must be finite")
    if not isinstance(
        policy,
        (
            PanchaPakshiAstronomicalPakshaInferencePolicy,
            PanchaPakshiNatalMoonIdentityPolicy,
        ),
    ):
        raise TypeError("policy must govern Pancha Pakshi lunar geometry")
    if policy.position_frame != "true_ecliptic_of_date":
        raise PanchaPakshiDataError("lunar geometry policy frame is unknown")

    selected_reader = get_reader() if reader is None else reader
    requested_jd_tt = _ut1_to_ephemeris_tt(jd_ut1, selected_reader)
    positions = {
        body: planet_at(
            body,
            jd_ut1,
            reader=selected_reader,
            apparent=policy.apparent,
            aberration=policy.aberration,
            grav_deflection=policy.grav_deflection,
            nutation=policy.nutation,
            center=policy.position_origin,
            frame="ecliptic",
            observer_lat=None,
            observer_lon=None,
            observer_elev_m=0.0,
            lst_deg=None,
            jd_tt=requested_jd_tt,
        )
        for body in (Body.SUN, Body.MOON)
    }
    try:
        sun_longitude = float(positions[Body.SUN].longitude) % 360.0
        moon_longitude = float(positions[Body.MOON].longitude) % 360.0
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise PanchaPakshiDataError(
            "planetary substrate did not return finite Sun and Moon longitudes"
        ) from exc
    if not math.isfinite(sun_longitude) or not math.isfinite(moon_longitude):
        raise PanchaPakshiDataError(
            "planetary substrate did not return finite Sun and Moon longitudes"
        )
    return (
        requested_jd_tt,
        sun_longitude,
        moon_longitude,
        (moon_longitude - sun_longitude) % 360.0,
    )


def pancha_pakshi_astronomical_paksha_at(
    profile_id: str,
    jd_ut1: float,
    *,
    reader: SpkReader | None = None,
) -> PanchaPakshiAstronomicalPakshaInference:
    """Infer the named profile's Paksha label from lunar phase geometry.

    ``jd_ut1`` is an explicit UT1 Julian Day.  The governing astronomical
    coordinate is the apparent geocentric Moon-minus-Sun longitude in the
    true ecliptic of date.  Exact half-open ownership assigns ``0`` degrees to
    Shukla and ``180`` degrees to Krishna.  The result performs no schedule
    selection, clock materialization, or natal identity inference.
    """

    from ._pancha_pakshi import _profile_provenance, _resolve_locators

    if isinstance(jd_ut1, bool) or not isinstance(jd_ut1, (int, float)):
        raise TypeError("jd_ut1 must be a real number")
    if not math.isfinite(jd_ut1):
        raise ValueError("jd_ut1 must be finite")

    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE,
    )
    policy = PanchaPakshiAstronomicalPakshaInferencePolicy()
    (
        requested_jd_tt,
        sun_longitude,
        moon_longitude,
        elongation,
    ) = _pancha_pakshi_apparent_moon_sun_geometry(
        jd_ut1,
        reader=reader,
        policy=policy,
    )
    astronomical_paksha = (
        PanchaPakshiAstronomicalPaksha.SHUKLA
        if elongation < 180.0
        else PanchaPakshiAstronomicalPaksha.KRISHNA
    )
    mapping_rule = profile.lunar_paksha_mapping_rule(astronomical_paksha)
    expected_phase_half = (
        "waxing"
        if astronomical_paksha is PanchaPakshiAstronomicalPaksha.SHUKLA
        else "waning"
    )
    if mapping_rule.lunar_phase_half != expected_phase_half:
        raise PanchaPakshiDataError(
            "profile lunar-phase mapping disagrees with astronomical paksha"
        )

    return PanchaPakshiAstronomicalPakshaInference(
        profile_id=profile.profile_id,
        requested_jd_ut1=float(jd_ut1),
        requested_jd_tt=requested_jd_tt,
        policy=policy,
        sun_longitude_deg=sun_longitude,
        moon_longitude_deg=moon_longitude,
        moon_minus_sun_elongation_deg=elongation,
        astronomical_paksha=astronomical_paksha,
        profile_paksha=mapping_rule.profile_paksha,
        mapping_status="direct_source_attested",
        mapping_source_locators=_resolve_locators(
            profile,
            mapping_rule.source_locator_ids,
        ),
        provenance=_profile_provenance(
            profile,
            astronomical_routing_status=_ASTRONOMICAL_PAKSHA_INFERENCE_STATUS,
        ),
    )


def _pancha_pakshi_nakshatra_bird_mapping_for_profile(
    profile,
    *,
    profile_paksha: PanchaPakshiPaksha,
    nakshatra_index: int,
) -> PanchaPakshiNakshatraBirdMapping:
    from ._pancha_pakshi import _profile_provenance, _resolve_locators

    if not isinstance(profile_paksha, PanchaPakshiPaksha):
        raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
    if isinstance(nakshatra_index, bool) or not isinstance(nakshatra_index, int):
        raise TypeError("nakshatra_index must be an integer")
    if not 0 <= nakshatra_index < 27:
        raise ValueError("nakshatra_index must lie in [0, 26]")
    rule = profile.nakshatra_bird_rule(profile_paksha, nakshatra_index)
    provenance = _profile_provenance(profile)
    return PanchaPakshiNakshatraBirdMapping(
        profile_id=profile.profile_id,
        profile_paksha=profile_paksha,
        nakshatra_index=nakshatra_index,
        nakshatra=rule.nakshatra,
        bird=rule.bird,
        mapping_status="direct_source_attested",
        source_table_semantics=(
            "nakshatra_bird_table_not_explicitly_natal_moon"
        ),
        assembly_policy=profile.assembly_policy,
        source_locators=_resolve_locators(profile, rule.source_locator_ids),
        provenance=provenance,
    )


def pancha_pakshi_nakshatra_bird_mapping(
    profile_id: str,
    *,
    profile_paksha: PanchaPakshiPaksha,
    nakshatra_index: int,
) -> PanchaPakshiNakshatraBirdMapping:
    """Return one source-table mapping without applying a natal-Moon policy."""

    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
    )
    return _pancha_pakshi_nakshatra_bird_mapping_for_profile(
        profile,
        profile_paksha=profile_paksha,
        nakshatra_index=nakshatra_index,
    )


def pancha_pakshi_first_eat_bird_mapping(
    profile_id: str,
    *,
    profile_paksha: PanchaPakshiPaksha,
    half: PanchaPakshiHalf,
    weekday: PanchaPakshiWeekday,
) -> PanchaPakshiFirstEatBirdMapping:
    """Return one source generator's weekday first-samam EAT seed.

    This is a pure lookup over an explicitly named, source-scoped profile.  It
    does not infer Paksha or civil context, materialize a schedule, or derive
    Padu, authority, condition, score, or forecast semantics.
    """

    from ._pancha_pakshi import (
        PanchaPakshiProfile,
        _profile_provenance,
        _resolve_locators,
    )

    if not isinstance(profile_paksha, PanchaPakshiPaksha):
        raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
    if not isinstance(half, PanchaPakshiHalf):
        raise TypeError("half must be a PanchaPakshiHalf")
    if not isinstance(weekday, PanchaPakshiWeekday):
        raise TypeError("weekday must be a PanchaPakshiWeekday")
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING,
    )
    if not isinstance(profile, PanchaPakshiProfile):
        raise PanchaPakshiDataError(
            "first-EAT-bird mapping requires an operating-schedule profile"
        )
    generator = profile.generator(profile_paksha, half)
    first_eat_bird = generator.first_eat_bird_for(weekday)
    return PanchaPakshiFirstEatBirdMapping(
        profile_id=profile.profile_id,
        generator_id=generator.generator_id,
        profile_paksha=profile_paksha,
        half=half,
        weekday=weekday,
        first_eat_bird=first_eat_bird,
        mapping_status="direct_source_attested",
        source_table_semantics=(
            "profile_paksha_half_weekday_first_samam_eat_seed_not_padu_"
            "authority_condition_or_score"
        ),
        source_locators=_resolve_locators(
            profile,
            generator.source_locator_ids,
        ),
        provenance=_profile_provenance(profile),
    )


def pancha_pakshi_padu_bird_mapping(
    profile_id: str,
    *,
    profile_paksha: PanchaPakshiPaksha,
    weekday: PanchaPakshiWeekday,
) -> PanchaPakshiPaduBirdMapping:
    """Return one source-attested Paksha-and-weekday Padu bird.

    This is an immutable table lookup.  It performs no astronomical routing,
    day/night selection, schedule lookup, activity conversion, scoring, or
    forecast computation.
    """

    from ._pancha_pakshi import _profile_provenance, _resolve_locators

    if not isinstance(profile_paksha, PanchaPakshiPaksha):
        raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
    if not isinstance(weekday, PanchaPakshiWeekday):
        raise TypeError("weekday must be a PanchaPakshiWeekday")
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.PADU_BIRD_MAPPING,
    )
    rule = profile.padu_bird_rule(profile_paksha, weekday)
    return PanchaPakshiPaduBirdMapping(
        profile_id=profile.profile_id,
        profile_paksha=profile_paksha,
        weekday=weekday,
        bird=rule.bird,
        mapping_status="direct_source_attested",
        source_table_semantics=profile.source_table_semantics,
        assembly_policy=profile.assembly_policy,
        source_locators=_resolve_locators(profile, rule.source_locator_ids),
        provenance=_profile_provenance(profile),
    )


def _sookshma_public_policy(profile, rule) -> PanchaPakshiSookshmaSelectorPolicy:
    """Materialize one validated internal selector rule as a public policy."""

    return PanchaPakshiSookshmaSelectorPolicy(
        policy_id=rule.policy_id,
        source_layer=rule.source_layer,
        partition_kind=rule.partition_kind,
        container_span_nazhigai=rule.container_span_nazhigai,
        interval_count=rule.interval_count,
        interval_ownership=rule.interval_ownership,
        sequence_policy=rule.sequence_policy,
        activity_assignment_status=rule.activity_assignment_status,
        activity_durations_nazhigai=rule.activity_durations_nazhigai,
        automatic_policy_selection=profile.automatic_policy_selection,
        uromarisi_composition_status=profile.uromarisi_composition_status,
        outcome_interpretation_status=profile.outcome_interpretation_status,
        source_locator_ids=rule.source_locator_ids,
    )


def pancha_pakshi_sookshma_temporal_selection(
    profile_id: str,
    *,
    policy_id: PanchaPakshiSookshmaSelectorPolicyId,
    parent_activity: PanchaPakshiActivity,
    elapsed_nazhigai: Fraction,
) -> PanchaPakshiSookshmaSelection:
    """Select one exact Sookshma ordinal under a caller-named policy.

    The input is an exact offset within one six-nazhigai samam.  The function
    performs no clock, civil-time, astronomical, schedule, Uromarisi-outcome,
    condition, scoring, electional, or forecasting composition.
    """

    from ._pancha_pakshi import (
        PanchaPakshiSookshmaSelectorProfile,
        _profile_provenance,
        _resolve_locators,
    )

    if not isinstance(
        policy_id,
        PanchaPakshiSookshmaSelectorPolicyId,
    ):
        raise TypeError(
            "policy_id must be a PanchaPakshiSookshmaSelectorPolicyId; "
            "there is no default"
        )
    if not isinstance(parent_activity, PanchaPakshiActivity):
        raise TypeError("parent_activity must be a PanchaPakshiActivity")
    if not isinstance(elapsed_nazhigai, Fraction):
        raise TypeError("elapsed_nazhigai must be an exact Fraction")
    if not Fraction() <= elapsed_nazhigai < Fraction(6):
        raise ValueError("elapsed_nazhigai must lie in the half-open [0, 6)")

    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION,
    )
    if not isinstance(profile, PanchaPakshiSookshmaSelectorProfile):
        raise PanchaPakshiDataError(
            "Sookshma temporal selection requires a selector profile"
        )
    rule = profile.sookshma_policy_rule(policy_id)
    policy = _sookshma_public_policy(profile, rule)
    intervals = _sookshma_intervals_for_policy(policy, parent_activity)
    matches = tuple(
        interval
        for interval in intervals
        if interval.start_nazhigai
        <= elapsed_nazhigai
        < interval.end_nazhigai
    )
    if len(matches) != 1:
        raise PanchaPakshiDataError(
            "Sookshma half-open selection did not yield exactly one interval"
        )
    selected = matches[0]
    return PanchaPakshiSookshmaSelection(
        profile_id=profile.profile_id,
        parent_activity=parent_activity,
        elapsed_nazhigai=elapsed_nazhigai,
        policy=policy,
        intervals=intervals,
        selected_ordinal=selected.ordinal,
        selected_interval=selected,
        source_locators=_resolve_locators(profile, rule.source_locator_ids),
        provenance=_profile_provenance(profile),
    )


def pancha_pakshi_schedule_sookshma_temporal_selection(
    schedule_profile_id: str,
    selector_profile_id: str,
    *,
    profile_paksha: PanchaPakshiPaksha,
    half: PanchaPakshiHalf,
    weekday: PanchaPakshiWeekday,
    samam_index: int,
    subject_bird: PanchaPakshiBird,
    selector_policy_id: PanchaPakshiSookshmaSelectorPolicyId,
    elapsed_nazhigai: Fraction,
) -> PanchaPakshiScheduleSookshmaSelection:
    """Compose one named schedule samam with one explicit Sookshma policy.

    Source evidence owns each input profile independently.  Their composition
    is a declared modern Moira policy: it locates the subject bird's unique
    cell in the selected samam and uses that cell's activity as the Sookshma
    parent.  The exact elapsed offset remains caller supplied.  No civil time,
    Uromarisi outcome, condition, score, election, or forecast is inferred.
    """

    if isinstance(samam_index, bool) or not isinstance(samam_index, int):
        raise TypeError("samam_index must be an integer")
    if not 1 <= samam_index <= 5:
        raise ValueError("samam_index must lie in [1, 5]")
    if not isinstance(subject_bird, PanchaPakshiBird):
        raise TypeError("subject_bird must be a PanchaPakshiBird")

    schedule = pancha_pakshi_schedule(
        schedule_profile_id,
        paksha=profile_paksha,
        half=half,
        weekday=weekday,
    )
    matches = tuple(
        cell
        for cell in schedule.cells
        if cell.samam_index == samam_index and cell.bird is subject_bird
    )
    if len(matches) != 1:
        raise PanchaPakshiDataError(
            "selected schedule samam did not yield exactly one subject-bird cell"
        )
    parent_cell = matches[0]
    selection = pancha_pakshi_sookshma_temporal_selection(
        selector_profile_id,
        policy_id=selector_policy_id,
        parent_activity=parent_cell.activity,
        elapsed_nazhigai=elapsed_nazhigai,
    )
    return PanchaPakshiScheduleSookshmaSelection(
        schedule_profile_id=schedule.profile_id,
        selector_profile_id=selection.profile_id,
        schedule=schedule,
        samam_index=samam_index,
        subject_bird=subject_bird,
        parent_schedule_cell=parent_cell,
        elapsed_nazhigai=elapsed_nazhigai,
        composition_policy=PanchaPakshiScheduleSookshmaCompositionPolicy(),
        sookshma_selection=selection,
    )


def pancha_pakshi_natal_moon_identity_at(
    profile_id: str,
    jd_ut1: float,
    *,
    reader: SpkReader | None = None,
) -> PanchaPakshiNatalMoonIdentity:
    """Compose a natal Moon with one named source-scoped bird table.

    ``jd_ut1`` is converted to reader-bound TT exactly once.  Apparent
    geocentric Sun and Moon positions determine the lunar half; the same TT
    epoch governs the fixed Lahiri-true sidereal Moon.  Source evidence owns
    only the phase-label and nakshatra-bird mappings.  Their application to a
    natal Moon is the explicit modern policy carried by the result.
    """

    from ._pancha_pakshi import _profile_provenance, _resolve_locators
    from .sidereal import (
        _ayanamsa_at_tt,
        _nakshatra_position_from_sidereal,
    )

    if isinstance(jd_ut1, bool) or not isinstance(jd_ut1, (int, float)):
        raise TypeError("jd_ut1 must be a real number")
    if not math.isfinite(jd_ut1):
        raise ValueError("jd_ut1 must be finite")

    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.NATAL_IDENTITY,
    )
    policy = PanchaPakshiNatalMoonIdentityPolicy()
    (
        requested_jd_tt,
        sun_longitude,
        moon_longitude,
        elongation,
    ) = _pancha_pakshi_apparent_moon_sun_geometry(
        jd_ut1,
        reader=reader,
        policy=policy,
    )
    astronomical_paksha = (
        PanchaPakshiAstronomicalPaksha.SHUKLA
        if elongation < 180.0
        else PanchaPakshiAstronomicalPaksha.KRISHNA
    )
    phase_rule = profile.lunar_paksha_mapping_rule(astronomical_paksha)
    expected_phase_half = (
        "waxing"
        if astronomical_paksha is PanchaPakshiAstronomicalPaksha.SHUKLA
        else "waning"
    )
    if phase_rule.lunar_phase_half != expected_phase_half:
        raise PanchaPakshiDataError(
            "profile lunar-phase mapping disagrees with astronomical paksha"
        )

    ayanamsa_deg = float(
        _ayanamsa_at_tt(
            requested_jd_tt,
            policy.ayanamsa_system,
            policy.ayanamsa_mode,
        )
    )
    if not math.isfinite(ayanamsa_deg):
        raise PanchaPakshiDataError("sidereal substrate returned non-finite ayanamsa")
    moon_sidereal_longitude = (moon_longitude - ayanamsa_deg) % 360.0
    nakshatra_position = _nakshatra_position_from_sidereal(
        moon_sidereal_longitude
    )
    provenance = _profile_provenance(
        profile,
        astronomical_routing_status=_NATAL_MOON_IDENTITY_STATUS,
    )
    mapping = _pancha_pakshi_nakshatra_bird_mapping_for_profile(
        profile,
        profile_paksha=phase_rule.profile_paksha,
        nakshatra_index=nakshatra_position.nakshatra_index,
    )
    mapping = replace(mapping, provenance=provenance)
    return PanchaPakshiNatalMoonIdentity(
        profile_id=profile.profile_id,
        requested_jd_ut1=float(jd_ut1),
        requested_jd_tt=requested_jd_tt,
        policy=policy,
        sun_longitude_deg=sun_longitude,
        moon_tropical_longitude_deg=moon_longitude,
        moon_minus_sun_elongation_deg=elongation,
        astronomical_paksha=astronomical_paksha,
        profile_paksha=phase_rule.profile_paksha,
        phase_mapping_source_locators=_resolve_locators(
            profile,
            phase_rule.source_locator_ids,
        ),
        ayanamsa_deg=ayanamsa_deg,
        moon_sidereal_longitude_deg=nakshatra_position.sidereal_lon,
        nakshatra_index=nakshatra_position.nakshatra_index,
        nakshatra=nakshatra_position.nakshatra,
        degrees_in_nakshatra=nakshatra_position.degrees_in,
        bird=mapping.bird,
        bird_mapping=mapping,
        provenance=provenance,
    )


def _pancha_pakshi_natal_moon_identity_from_utc(
    profile_id: str,
    jd_utc: float,
    *,
    reader: SpkReader | None = None,
) -> PanchaPakshiNatalMoonIdentity:
    """Facade adapter converting one UTC Julian Day to the UT1 product."""

    from .julian import utc_to_ut1

    return pancha_pakshi_natal_moon_identity_at(
        profile_id,
        utc_to_ut1(jd_utc),
        reader=reader,
    )


def _pancha_pakshi_astronomical_paksha_from_utc(
    profile_id: str,
    jd_utc: float,
    *,
    reader: SpkReader | None = None,
) -> PanchaPakshiAstronomicalPakshaInference:
    """Facade adapter converting one UTC Julian Day to the public UT1 route."""

    from .julian import utc_to_ut1

    return pancha_pakshi_astronomical_paksha_at(
        profile_id,
        utc_to_ut1(jd_utc),
        reader=reader,
    )


def pancha_pakshi_schedule(
    profile_id: str,
    *,
    paksha: PanchaPakshiPaksha,
    half: PanchaPakshiHalf,
    weekday: PanchaPakshiWeekday,
) -> PanchaPakshiSchedule:
    """Generate one exact nominal source schedule; no clock routing occurs."""

    from ._pancha_pakshi import (
        generate_pancha_pakshi_schedule,
    )

    return generate_pancha_pakshi_schedule(
        _profile_for_public_capability(
            profile_id, PanchaPakshiCapability.NOMINAL_SCHEDULE
        ),
        paksha=paksha,
        half=half,
        weekday=weekday,
    )


def _require_context_paksha(
    paksha: PanchaPakshiPaksha,
) -> PanchaPakshiPaksha:
    if not isinstance(paksha, PanchaPakshiPaksha):
        raise TypeError(
            "paksha must be an explicit PanchaPakshiPaksha source label; "
            "schedule, context, and materialization routes do not perform "
            "ambient astronomical paksha inference"
        )
    return paksha


def _pancha_pakshi_context_for_solar_day(
    profile: PanchaPakshiProfile,
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha,
) -> PanchaPakshiLocalSolarContext:
    """Select a nominal schedule from one already resolved solar day."""

    from ._pancha_pakshi import (
        _profile_provenance,
        generate_pancha_pakshi_schedule,
    )

    solar_weekday = solar_day.weekday
    if (
        isinstance(solar_weekday, bool)
        or not isinstance(solar_weekday, int)
        or not 0 <= solar_weekday < len(_WEEKDAY_FROM_LOCAL_SOLAR_INDEX)
    ):
        raise PanchaPakshiDataError(
            "local-solar resolver returned an invalid Sunday-zero weekday"
        )
    weekday = _WEEKDAY_FROM_LOCAL_SOLAR_INDEX[solar_weekday]
    half = (
        PanchaPakshiHalf.DAY
        if solar_day.is_daytime
        else PanchaPakshiHalf.NIGHT
    )
    schedule = generate_pancha_pakshi_schedule(
        profile,
        paksha=paksha,
        half=half,
        weekday=weekday,
    )
    return PanchaPakshiLocalSolarContext(
        profile_id=profile.profile_id,
        requested_jd_ut1=solar_day.jd,
        latitude=solar_day.latitude,
        longitude=solar_day.longitude,
        sunrise_jd_ut1=solar_day.sunrise_jd,
        sunset_jd_ut1=solar_day.sunset_jd,
        next_sunrise_jd_ut1=solar_day.next_sunrise_jd,
        paksha=paksha,
        half=half,
        weekday=weekday,
        policy=PanchaPakshiLocalSolarContextPolicy(),
        nominal_schedule=schedule,
        provenance=_profile_provenance(
            profile,
            astronomical_routing_status=_LOCAL_SOLAR_ROUTING_STATUS,
        ),
    )


def pancha_pakshi_local_solar_context_at(
    profile_id: str,
    jd_ut1: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiLocalSolarContext:
    """Select a nominal schedule from an explicit Paksha and local solar day.

    ``jd_ut1`` and the returned event epochs are UT1 Julian Days.  Sunrise and
    sunset derive only the half and weekday context.  No lunar-phase mapping,
    nazhigai-to-clock projection, or current-cell lookup occurs.
    """

    from ._local_solar_day import _local_solar_day_from_ut1

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id, PanchaPakshiCapability.ASTRONOMICAL_CONTEXT
    )
    solar_day = _local_solar_day_from_ut1(
        jd_ut1,
        latitude,
        longitude,
        reader,
        bounds_owner="pancha-pakshi-local-solar-context",
    )
    return _pancha_pakshi_context_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
    )


def _pancha_pakshi_local_solar_context_from_utc(
    profile_id: str,
    jd_utc: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiLocalSolarContext:
    """Facade adapter preserving UTC civil-noon selection before UT1."""

    from ._local_solar_day import _local_solar_day_from_utc

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id, PanchaPakshiCapability.ASTRONOMICAL_CONTEXT
    )
    solar_day = _local_solar_day_from_utc(
        jd_utc,
        latitude,
        longitude,
        reader,
        bounds_owner="pancha-pakshi-local-solar-context",
    )
    return _pancha_pakshi_context_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
    )


def _fixed_clock_solar_boundary_relation(
    residual_seconds_tt: float,
    tolerance_seconds: float,
) -> PanchaPakshiSolarBoundaryRelation:
    if abs(residual_seconds_tt) <= tolerance_seconds:
        return PanchaPakshiSolarBoundaryRelation.ENDS_AT_SOLAR_BOUNDARY
    if residual_seconds_tt < 0.0:
        return PanchaPakshiSolarBoundaryRelation.ENDS_BEFORE_SOLAR_BOUNDARY
    return PanchaPakshiSolarBoundaryRelation.ENDS_AFTER_SOLAR_BOUNDARY


def _fixed_clock_cell_relation(
    start_jd_tt: float,
    end_jd_tt: float,
    governing_end_jd_tt: float,
) -> PanchaPakshiMaterializedCellRelation:
    """Classify one half-open cell against the exact solar-half endpoint."""

    if start_jd_tt >= governing_end_jd_tt:
        return PanchaPakshiMaterializedCellRelation.AFTER_GOVERNING_SOLAR_HALF
    if end_jd_tt <= governing_end_jd_tt:
        return PanchaPakshiMaterializedCellRelation.WITHIN_GOVERNING_SOLAR_HALF
    return (
        PanchaPakshiMaterializedCellRelation.CROSSES_GOVERNING_SOLAR_HALF_END
    )


def _pancha_pakshi_fixed_clock_for_solar_day(
    profile: PanchaPakshiProfile,
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader,
) -> PanchaPakshiFixedClockMaterialization:
    """Materialize one already resolved local-solar half on uniform TT."""

    from ._ephemeris_time import (
        _ephemeris_tt_to_ut1,
        _ut1_to_ephemeris_tt,
    )
    from ._pancha_pakshi import _profile_provenance

    context = _pancha_pakshi_context_for_solar_day(
        profile,
        solar_day,
        paksha=paksha,
    )
    policy = PanchaPakshiFixedClockMaterializationPolicy()
    schedule = context.nominal_schedule
    if schedule.span_nazhigai != policy.half_span_nazhigai:
        raise PanchaPakshiDataError(
            "nominal schedule span disagrees with fixed-clock policy"
        )

    if context.half is PanchaPakshiHalf.DAY:
        anchor_jd_ut1 = context.sunrise_jd_ut1
        governing_end_jd_ut1 = context.sunset_jd_ut1
    else:
        anchor_jd_ut1 = context.sunset_jd_ut1
        governing_end_jd_ut1 = context.next_sunrise_jd_ut1

    anchor_jd_tt = _ut1_to_ephemeris_tt(anchor_jd_ut1, reader)
    governing_end_jd_tt = _ut1_to_ephemeris_tt(
        governing_end_jd_ut1,
        reader,
    )

    offsets = {
        offset
        for nominal_cell in schedule.cells
        for offset in (
            nominal_cell.start_nazhigai,
            nominal_cell.end_nazhigai,
        )
    }
    endpoints_tt: dict[Fraction, float] = {}
    endpoints_ut1: dict[Fraction, float] = {}
    for offset_nazhigai in sorted(offsets):
        offset_seconds = offset_nazhigai * policy.nazhigai_seconds
        offset_days_tt = offset_seconds / _SI_SECONDS_PER_DAY
        endpoint_jd_tt = anchor_jd_tt + float(offset_days_tt)
        endpoints_tt[offset_nazhigai] = endpoint_jd_tt
        endpoints_ut1[offset_nazhigai] = (
            anchor_jd_ut1
            if offset_nazhigai == 0
            else _ephemeris_tt_to_ut1(endpoint_jd_tt, reader)
        )

    tolerance = policy.topology_coalescence_seconds
    materialized_cells = tuple(
        PanchaPakshiFixedClockCell(
            schedule_cell_index=schedule_cell_index,
            nominal_cell=nominal_cell,
            start_jd_tt=endpoints_tt[nominal_cell.start_nazhigai],
            end_jd_tt=endpoints_tt[nominal_cell.end_nazhigai],
            start_jd_ut1=endpoints_ut1[nominal_cell.start_nazhigai],
            end_jd_ut1=endpoints_ut1[nominal_cell.end_nazhigai],
            duration_seconds=(
                nominal_cell.duration_nazhigai * policy.nazhigai_seconds
            ),
            solar_half_relation=_fixed_clock_cell_relation(
                endpoints_tt[nominal_cell.start_nazhigai],
                endpoints_tt[nominal_cell.end_nazhigai],
                governing_end_jd_tt,
            ),
        )
        for schedule_cell_index, nominal_cell in enumerate(schedule.cells)
    )
    fixed_end_jd_tt = endpoints_tt[Fraction(policy.half_span_nazhigai)]
    fixed_end_jd_ut1 = endpoints_ut1[Fraction(policy.half_span_nazhigai)]
    residual_seconds_tt = (
        fixed_end_jd_tt - governing_end_jd_tt
    ) * _SI_SECONDS_PER_DAY
    return PanchaPakshiFixedClockMaterialization(
        context=context,
        policy=policy,
        anchor_jd_tt=anchor_jd_tt,
        anchor_jd_ut1=anchor_jd_ut1,
        governing_solar_half_end_jd_tt=governing_end_jd_tt,
        governing_solar_half_end_jd_ut1=governing_end_jd_ut1,
        fixed_end_jd_tt=fixed_end_jd_tt,
        fixed_end_jd_ut1=fixed_end_jd_ut1,
        signed_fixed_end_minus_solar_end_seconds_tt=residual_seconds_tt,
        solar_boundary_relation=_fixed_clock_solar_boundary_relation(
            residual_seconds_tt,
            tolerance,
        ),
        cells=materialized_cells,
        provenance=_profile_provenance(
            profile,
            astronomical_routing_status=_FIXED_CLOCK_MATERIALIZATION_STATUS,
        ),
    )


def pancha_pakshi_fixed_clock_materialization_at(
    profile_id: str,
    jd_ut1: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiFixedClockMaterialization:
    """Materialize fixed nominal offsets from the governing solar-half start.

    Offsets are elapsed on TT and projected back to UT1 through the same
    reader-bound clock policy.  The result reports solar-boundary divergence
    and intentionally performs neither current-cell selection nor seasonal
    scaling.
    """

    from ._local_solar_day import _local_solar_day_from_ut1
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_ut1(
        jd_ut1,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-fixed-clock-materialization",
    )
    return _pancha_pakshi_fixed_clock_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _pancha_pakshi_fixed_clock_materialization_from_utc(
    profile_id: str,
    jd_utc: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiFixedClockMaterialization:
    """Facade adapter preserving UTC civil-noon selection before UT1."""

    from ._local_solar_day import _local_solar_day_from_utc
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_utc(
        jd_utc,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-fixed-clock-materialization",
    )
    return _pancha_pakshi_fixed_clock_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _pancha_pakshi_fixed_clock_current_cell_for_solar_day(
    profile: PanchaPakshiProfile,
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader,
) -> PanchaPakshiFixedClockCurrentCellSelection:
    """Select exact TT membership after resolving the governing solar half."""

    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from ._pancha_pakshi import _profile_provenance

    materialization = _pancha_pakshi_fixed_clock_for_solar_day(
        profile,
        solar_day,
        paksha=paksha,
        reader=reader,
    )
    policy = PanchaPakshiFixedClockCurrentCellSelectionPolicy()
    requested_jd_tt = _ut1_to_ephemeris_tt(solar_day.jd, reader)
    if not (
        materialization.anchor_jd_tt
        <= requested_jd_tt
        < materialization.governing_solar_half_end_jd_tt
    ):
        raise PanchaPakshiDataError(
            "requested TT instant escaped the governing half-open solar half"
        )

    matches = tuple(
        cell
        for cell in materialization.cells
        if cell.start_jd_tt <= requested_jd_tt < cell.end_jd_tt
    )
    if len(matches) == 1:
        selection_status = PanchaPakshiCurrentCellSelectionStatus.SELECTED
        current_cell = matches[0]
    elif len(matches) > 1:
        raise PanchaPakshiDataError(
            "materialized fixed-clock cells overlap at the requested TT instant"
        )
    elif (
        materialization.fixed_end_jd_tt
        < materialization.governing_solar_half_end_jd_tt
        and materialization.fixed_end_jd_tt
        <= requested_jd_tt
        < materialization.governing_solar_half_end_jd_tt
    ):
        selection_status = (
            PanchaPakshiCurrentCellSelectionStatus.UNMATERIALIZED_SOLAR_HALF_TAIL
        )
        current_cell = None
    else:
        raise PanchaPakshiDataError(
            "requested TT instant has no lawful fixed-clock cell membership"
        )

    return PanchaPakshiFixedClockCurrentCellSelection(
        materialization=materialization,
        policy=policy,
        requested_jd_tt=requested_jd_tt,
        selection_status=selection_status,
        current_cell=current_cell,
        provenance=_profile_provenance(
            profile,
            astronomical_routing_status=(
                _FIXED_CLOCK_CURRENT_CELL_SELECTION_STATUS
            ),
        ),
    )


def pancha_pakshi_fixed_clock_current_cell_at(
    profile_id: str,
    jd_ut1: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiFixedClockCurrentCellSelection:
    """Select the fixed-clock cell current under governing-half precedence.

    The local solar half is resolved from ``jd_ut1`` before materialization.
    Membership is exact and half-open on reader-bound TT.  A long solar half
    may lawfully return an explicit unmaterialized-tail result; cells extending
    past a short solar half never remain eligible after its boundary.
    """

    from ._local_solar_day import _local_solar_day_from_ut1
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_ut1(
        jd_ut1,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-fixed-clock-current-cell",
    )
    return _pancha_pakshi_fixed_clock_current_cell_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _pancha_pakshi_fixed_clock_current_cell_from_utc(
    profile_id: str,
    jd_utc: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiFixedClockCurrentCellSelection:
    """Facade adapter preserving UTC civil-noon selection before UT1."""

    from ._local_solar_day import _local_solar_day_from_utc
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_utc(
        jd_utc,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-fixed-clock-current-cell",
    )
    return _pancha_pakshi_fixed_clock_current_cell_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _solar_proportional_provenance(
    context: PanchaPakshiLocalSolarContext,
) -> PanchaPakshiProvenance:
    """Return Stage 2D provenance without conflating source and policy truth."""

    provenance = context.provenance
    seasonal_scaling_omissions = tuple(
        omission
        for omission in provenance.declared_omissions
        if omission.feature == "seasonal_scaling"
    )
    if len(seasonal_scaling_omissions) != 1:
        raise PanchaPakshiDataError(
            "Stage 2D context provenance must contain exactly one "
            "seasonal_scaling source omission"
        )
    declared_omissions = tuple(
        _SOLAR_PROPORTIONAL_SOURCE_NONATTESTATION
        if omission.feature == "seasonal_scaling"
        else omission
        for omission in provenance.declared_omissions
    )
    return replace(
        provenance,
        declared_omissions=declared_omissions,
        astronomical_routing_status=(
            _SOLAR_PROPORTIONAL_MATERIALIZATION_STATUS
        ),
    )


def _solar_proportional_current_cell_provenance(
    materialization: PanchaPakshiSolarProportionalMaterialization,
) -> PanchaPakshiProvenance:
    """Name Stage 2E while preserving Stage 2D source-policy separation."""

    return replace(
        materialization.provenance,
        astronomical_routing_status=(
            _SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION_STATUS
        ),
    )


def _pancha_pakshi_solar_proportional_for_solar_day(
    profile: PanchaPakshiProfile,
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader,
) -> PanchaPakshiSolarProportionalMaterialization:
    """Map one nominal half independently over its governing solar half."""

    from ._ephemeris_time import (
        _ephemeris_tt_to_ut1,
        _ut1_to_ephemeris_tt,
    )

    context = _pancha_pakshi_context_for_solar_day(
        profile,
        solar_day,
        paksha=paksha,
    )
    policy = PanchaPakshiSolarProportionalMaterializationPolicy()
    schedule = context.nominal_schedule
    if schedule.span_nazhigai != Fraction(30):
        raise PanchaPakshiDataError(
            "solar-proportional policy requires a 30-nazhigai schedule"
        )

    if context.half is PanchaPakshiHalf.DAY:
        anchor_jd_ut1 = context.sunrise_jd_ut1
        governing_end_jd_ut1 = context.sunset_jd_ut1
    else:
        anchor_jd_ut1 = context.sunset_jd_ut1
        governing_end_jd_ut1 = context.next_sunrise_jd_ut1

    anchor_jd_tt = _ut1_to_ephemeris_tt(anchor_jd_ut1, reader)
    governing_end_jd_tt = _ut1_to_ephemeris_tt(
        governing_end_jd_ut1,
        reader,
    )
    if not (
        math.isfinite(anchor_jd_tt)
        and math.isfinite(governing_end_jd_tt)
        and anchor_jd_tt < governing_end_jd_tt
    ):
        raise PanchaPakshiDataError(
            "reader-bound TT solar-half bounds must be finite and ordered"
        )

    solar_half_span_days_tt = governing_end_jd_tt - anchor_jd_tt
    solar_half_duration_seconds_tt = (
        solar_half_span_days_tt * _SI_SECONDS_PER_DAY
    )
    offsets = {
        offset
        for nominal_cell in schedule.cells
        for offset in (
            nominal_cell.start_nazhigai,
            nominal_cell.end_nazhigai,
        )
    }
    if Fraction(0) not in offsets or schedule.span_nazhigai not in offsets:
        raise PanchaPakshiDataError(
            "nominal schedule does not expose both outer half endpoints"
        )

    endpoint_fractions: dict[Fraction, Fraction] = {}
    endpoints_tt: dict[Fraction, float] = {}
    endpoints_ut1: dict[Fraction, float] = {}
    for offset_nazhigai in sorted(offsets):
        offset_fraction = offset_nazhigai / schedule.span_nazhigai
        endpoint_fractions[offset_nazhigai] = offset_fraction
        if offset_nazhigai == 0:
            endpoint_jd_tt = anchor_jd_tt
            endpoint_jd_ut1 = anchor_jd_ut1
        elif offset_nazhigai == schedule.span_nazhigai:
            endpoint_jd_tt = governing_end_jd_tt
            endpoint_jd_ut1 = governing_end_jd_ut1
        else:
            endpoint_jd_tt = anchor_jd_tt + (
                float(offset_fraction) * solar_half_span_days_tt
            )
            endpoint_jd_ut1 = _ephemeris_tt_to_ut1(endpoint_jd_tt, reader)
        if not math.isfinite(endpoint_jd_ut1):
            raise PanchaPakshiDataError(
                "solar-proportional UT1 projection returned a non-finite JD"
            )
        endpoints_tt[offset_nazhigai] = endpoint_jd_tt
        endpoints_ut1[offset_nazhigai] = endpoint_jd_ut1

    materialized_cells = tuple(
        PanchaPakshiSolarProportionalCell(
            schedule_cell_index=schedule_cell_index,
            nominal_cell=nominal_cell,
            start_offset_fraction=(
                endpoint_fractions[nominal_cell.start_nazhigai]
            ),
            end_offset_fraction=(
                endpoint_fractions[nominal_cell.end_nazhigai]
            ),
            span_fraction=(
                nominal_cell.duration_nazhigai / schedule.span_nazhigai
            ),
            start_jd_tt=endpoints_tt[nominal_cell.start_nazhigai],
            end_jd_tt=endpoints_tt[nominal_cell.end_nazhigai],
            start_jd_ut1=endpoints_ut1[nominal_cell.start_nazhigai],
            end_jd_ut1=endpoints_ut1[nominal_cell.end_nazhigai],
            duration_seconds_tt=(
                endpoints_tt[nominal_cell.end_nazhigai]
                - endpoints_tt[nominal_cell.start_nazhigai]
            )
            * _SI_SECONDS_PER_DAY,
        )
        for schedule_cell_index, nominal_cell in enumerate(schedule.cells)
    )
    return PanchaPakshiSolarProportionalMaterialization(
        context=context,
        policy=policy,
        anchor_jd_tt=anchor_jd_tt,
        anchor_jd_ut1=anchor_jd_ut1,
        governing_solar_half_end_jd_tt=governing_end_jd_tt,
        governing_solar_half_end_jd_ut1=governing_end_jd_ut1,
        solar_half_duration_seconds_tt=solar_half_duration_seconds_tt,
        cells=materialized_cells,
        provenance=_solar_proportional_provenance(context),
    )


def pancha_pakshi_solar_proportional_materialization_at(
    profile_id: str,
    jd_ut1: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiSolarProportionalMaterialization:
    """Scale exact nominal offsets over the governing local-solar half.

    The local solar half is resolved before mapping.  Its UT1 outer bounds are
    converted to reader-bound TT exactly once, every source-owned nominal
    offset is independently mapped as a rational fraction of that TT span,
    and only interior endpoints are projected back to UT1.  Paksha remains a
    caller-supplied source label; no current-cell selection occurs.
    """

    from ._local_solar_day import _local_solar_day_from_ut1
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_ut1(
        jd_ut1,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-solar-proportional-materialization",
    )
    return _pancha_pakshi_solar_proportional_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _pancha_pakshi_solar_proportional_materialization_from_utc(
    profile_id: str,
    jd_utc: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiSolarProportionalMaterialization:
    """Facade adapter preserving UTC civil-noon selection before UT1."""

    from ._local_solar_day import _local_solar_day_from_utc
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_utc(
        jd_utc,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-solar-proportional-materialization",
    )
    return _pancha_pakshi_solar_proportional_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _pancha_pakshi_solar_proportional_current_cell_for_solar_day(
    profile: PanchaPakshiProfile,
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader,
) -> PanchaPakshiSolarProportionalCurrentCellSelection:
    """Select the unique half-open TT cell from one Stage 2D partition."""

    from ._ephemeris_time import _ut1_to_ephemeris_tt

    materialization = _pancha_pakshi_solar_proportional_for_solar_day(
        profile,
        solar_day,
        paksha=paksha,
        reader=reader,
    )
    policy = PanchaPakshiSolarProportionalCurrentCellSelectionPolicy()
    requested_jd_tt = _ut1_to_ephemeris_tt(solar_day.jd, reader)
    if not (
        materialization.anchor_jd_tt
        <= requested_jd_tt
        < materialization.governing_solar_half_end_jd_tt
    ):
        raise PanchaPakshiDataError(
            "requested TT instant escaped the governing half-open solar half"
        )

    matches = tuple(
        cell
        for cell in materialization.cells
        if cell.start_jd_tt <= requested_jd_tt < cell.end_jd_tt
    )
    if len(matches) != policy.required_match_count:
        raise PanchaPakshiDataError(
            "solar-proportional current-cell selection requires exactly one "
            "half-open TT match"
        )

    return PanchaPakshiSolarProportionalCurrentCellSelection(
        materialization=materialization,
        policy=policy,
        requested_jd_tt=requested_jd_tt,
        selection_status=PanchaPakshiCurrentCellSelectionStatus.SELECTED,
        current_cell=matches[0],
        provenance=_solar_proportional_current_cell_provenance(
            materialization
        ),
    )


def pancha_pakshi_solar_proportional_current_cell_at(
    profile_id: str,
    jd_ut1: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiSolarProportionalCurrentCellSelection:
    """Select the proportional cell current in the governing solar half.

    The governing half is resolved before the unchanged Stage 2D
    materialization is constructed.  Membership is exact and half-open on
    reader-bound TT; the complete proportional partition must yield one cell.
    """

    from ._local_solar_day import _local_solar_day_from_ut1
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_ut1(
        jd_ut1,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-solar-proportional-current-cell",
    )
    return _pancha_pakshi_solar_proportional_current_cell_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _pancha_pakshi_solar_proportional_current_cell_from_utc(
    profile_id: str,
    jd_utc: float,
    latitude: float,
    longitude: float,
    *,
    paksha: PanchaPakshiPaksha,
    reader: SpkReader | None = None,
) -> PanchaPakshiSolarProportionalCurrentCellSelection:
    """Facade adapter preserving UTC civil-noon selection before UT1."""

    from ._local_solar_day import _local_solar_day_from_utc
    from .spk_reader import get_reader

    selected_paksha = _require_context_paksha(paksha)
    profile = _profile_for_public_capability(
        profile_id,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION,
    )
    selected_reader = get_reader() if reader is None else reader
    solar_day = _local_solar_day_from_utc(
        jd_utc,
        latitude,
        longitude,
        selected_reader,
        bounds_owner="pancha-pakshi-solar-proportional-current-cell",
    )
    return _pancha_pakshi_solar_proportional_current_cell_for_solar_day(
        profile,
        solar_day,
        paksha=selected_paksha,
        reader=selected_reader,
    )


def _stage2o_materialized_samam_coordinates(
    current_cell_selection: (
        PanchaPakshiFixedClockCurrentCellSelection
        | PanchaPakshiSolarProportionalCurrentCellSelection
    ),
    samam_index: int,
) -> tuple[float, float, Fraction]:
    """Derive exact normalized samam offset from stored binary64 TT values."""

    if not isinstance(
        current_cell_selection,
        (
            PanchaPakshiFixedClockCurrentCellSelection,
            PanchaPakshiSolarProportionalCurrentCellSelection,
        ),
    ):
        raise TypeError("current_cell_selection is not an admitted timing vessel")
    if (
        current_cell_selection.selection_status
        is not PanchaPakshiCurrentCellSelectionStatus.SELECTED
        or current_cell_selection.current_cell is None
    ):
        raise ValueError("materialized samam coordinates require selected status")
    if isinstance(samam_index, bool) or not isinstance(samam_index, int):
        raise TypeError("samam_index must be an integer")
    if not 1 <= samam_index <= 5:
        raise ValueError("samam_index must lie in [1, 5]")

    cells = tuple(
        cell
        for cell in current_cell_selection.materialization.cells
        if cell.nominal_cell.samam_index == samam_index
    )
    if len(cells) != 5:
        raise PanchaPakshiDataError(
            "materialization must contain five cells in the selected samam"
        )
    if tuple(cell.nominal_cell.sequence_index for cell in cells) != (
        1,
        2,
        3,
        4,
        5,
    ):
        raise PanchaPakshiDataError(
            "selected materialized samam cells are not canonically ordered"
        )
    samam_start_jd_tt = cells[0].start_jd_tt
    samam_end_jd_tt = cells[-1].end_jd_tt
    requested_jd_tt = current_cell_selection.requested_jd_tt
    if not samam_start_jd_tt <= requested_jd_tt < samam_end_jd_tt:
        raise PanchaPakshiDataError(
            "requested TT instant does not belong to the selected samam"
        )

    exact_start = Fraction.from_float(samam_start_jd_tt)
    exact_end = Fraction.from_float(samam_end_jd_tt)
    exact_requested = Fraction.from_float(requested_jd_tt)
    exact_span = exact_end - exact_start
    if exact_span <= 0:
        raise PanchaPakshiDataError(
            "selected materialized samam has no positive exact TT span"
        )
    elapsed_nazhigai = (
        (exact_requested - exact_start) * Fraction(6) / exact_span
    )
    if not Fraction() <= elapsed_nazhigai < Fraction(6):
        raise PanchaPakshiDataError(
            "normalized Stage 2O elapsed offset escaped [0, 6)"
        )
    return samam_start_jd_tt, samam_end_jd_tt, elapsed_nazhigai


def _stage2o_selection_from_current_cell(
    selector_profile_id: str,
    current_cell_selection: (
        PanchaPakshiFixedClockCurrentCellSelection
        | PanchaPakshiSolarProportionalCurrentCellSelection
    ),
    *,
    timing_policy_id: PanchaPakshiSookshmaTimingPolicyId,
    subject_bird: PanchaPakshiBird,
    selector_policy_id: PanchaPakshiSookshmaSelectorPolicyId,
) -> PanchaPakshiCivilTimeSookshmaSelection:
    """Assemble Stage 2O from one already selected materialization policy."""

    context = current_cell_selection.materialization.context
    if current_cell_selection.selection_status is (
        PanchaPakshiCurrentCellSelectionStatus
        .UNMATERIALIZED_SOLAR_HALF_TAIL
    ):
        return PanchaPakshiCivilTimeSookshmaSelection(
            schedule_profile_id=context.profile_id,
            selector_profile_id=selector_profile_id,
            timing_policy_id=timing_policy_id,
            selector_policy_id=selector_policy_id,
            subject_bird=subject_bird,
            routing_policy=PanchaPakshiCivilTimeSookshmaRoutingPolicy(),
            current_cell_selection=current_cell_selection,
            selection_status=current_cell_selection.selection_status,
            samam_index=None,
            samam_start_jd_tt=None,
            samam_end_jd_tt=None,
            elapsed_nazhigai=None,
            composition=None,
        )

    current_cell = current_cell_selection.current_cell
    if current_cell is None:
        raise PanchaPakshiDataError(
            "selected Stage 2O timing route returned no current cell"
        )
    samam_index = current_cell.nominal_cell.samam_index
    (
        samam_start_jd_tt,
        samam_end_jd_tt,
        elapsed_nazhigai,
    ) = _stage2o_materialized_samam_coordinates(
        current_cell_selection,
        samam_index,
    )
    composition = pancha_pakshi_schedule_sookshma_temporal_selection(
        context.profile_id,
        selector_profile_id,
        profile_paksha=context.paksha,
        half=context.half,
        weekday=context.weekday,
        samam_index=samam_index,
        subject_bird=subject_bird,
        selector_policy_id=selector_policy_id,
        elapsed_nazhigai=elapsed_nazhigai,
    )
    return PanchaPakshiCivilTimeSookshmaSelection(
        schedule_profile_id=context.profile_id,
        selector_profile_id=selector_profile_id,
        timing_policy_id=timing_policy_id,
        selector_policy_id=selector_policy_id,
        subject_bird=subject_bird,
        routing_policy=PanchaPakshiCivilTimeSookshmaRoutingPolicy(),
        current_cell_selection=current_cell_selection,
        selection_status=current_cell_selection.selection_status,
        samam_index=samam_index,
        samam_start_jd_tt=samam_start_jd_tt,
        samam_end_jd_tt=samam_end_jd_tt,
        elapsed_nazhigai=elapsed_nazhigai,
        composition=composition,
    )


def _require_stage2o_inputs(
    selector_profile_id: str,
    *,
    timing_policy_id: PanchaPakshiSookshmaTimingPolicyId,
    subject_bird: PanchaPakshiBird,
    selector_policy_id: PanchaPakshiSookshmaSelectorPolicyId,
) -> None:
    if not isinstance(
        timing_policy_id,
        PanchaPakshiSookshmaTimingPolicyId,
    ):
        raise TypeError(
            "timing_policy_id must be a PanchaPakshiSookshmaTimingPolicyId; "
            "there is no default"
        )
    if not isinstance(subject_bird, PanchaPakshiBird):
        raise TypeError("subject_bird must be a PanchaPakshiBird")
    if not isinstance(
        selector_policy_id,
        PanchaPakshiSookshmaSelectorPolicyId,
    ):
        raise TypeError(
            "selector_policy_id must be a "
            "PanchaPakshiSookshmaSelectorPolicyId; there is no default"
        )
    _profile_for_public_capability(
        selector_profile_id,
        PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION,
    )


def pancha_pakshi_civil_time_sookshma_selection_at(
    schedule_profile_id: str,
    selector_profile_id: str,
    jd_ut1: float,
    latitude: float,
    longitude: float,
    *,
    profile_paksha: PanchaPakshiPaksha,
    subject_bird: PanchaPakshiBird,
    timing_policy_id: PanchaPakshiSookshmaTimingPolicyId,
    selector_policy_id: PanchaPakshiSookshmaSelectorPolicyId,
    reader: SpkReader | None = None,
) -> PanchaPakshiCivilTimeSookshmaSelection:
    """Route one UT1 civil instant into Stage 2N under explicit policies."""

    _require_stage2o_inputs(
        selector_profile_id,
        timing_policy_id=timing_policy_id,
        subject_bird=subject_bird,
        selector_policy_id=selector_policy_id,
    )
    if timing_policy_id is PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK:
        current_cell_selection = pancha_pakshi_fixed_clock_current_cell_at(
            schedule_profile_id,
            jd_ut1,
            latitude,
            longitude,
            paksha=profile_paksha,
            reader=reader,
        )
    else:
        current_cell_selection = (
            pancha_pakshi_solar_proportional_current_cell_at(
                schedule_profile_id,
                jd_ut1,
                latitude,
                longitude,
                paksha=profile_paksha,
                reader=reader,
            )
        )
    return _stage2o_selection_from_current_cell(
        selector_profile_id,
        current_cell_selection,
        timing_policy_id=timing_policy_id,
        subject_bird=subject_bird,
        selector_policy_id=selector_policy_id,
    )


def _pancha_pakshi_civil_time_sookshma_selection_from_utc(
    schedule_profile_id: str,
    selector_profile_id: str,
    jd_utc: float,
    latitude: float,
    longitude: float,
    *,
    profile_paksha: PanchaPakshiPaksha,
    subject_bird: PanchaPakshiBird,
    timing_policy_id: PanchaPakshiSookshmaTimingPolicyId,
    selector_policy_id: PanchaPakshiSookshmaSelectorPolicyId,
    reader: SpkReader | None = None,
) -> PanchaPakshiCivilTimeSookshmaSelection:
    """Facade adapter preserving UTC local-solar selection semantics."""

    _require_stage2o_inputs(
        selector_profile_id,
        timing_policy_id=timing_policy_id,
        subject_bird=subject_bird,
        selector_policy_id=selector_policy_id,
    )
    if timing_policy_id is PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK:
        current_cell_selection = (
            _pancha_pakshi_fixed_clock_current_cell_from_utc(
                schedule_profile_id,
                jd_utc,
                latitude,
                longitude,
                paksha=profile_paksha,
                reader=reader,
            )
        )
    else:
        current_cell_selection = (
            _pancha_pakshi_solar_proportional_current_cell_from_utc(
                schedule_profile_id,
                jd_utc,
                latitude,
                longitude,
                paksha=profile_paksha,
                reader=reader,
            )
        )
    return _stage2o_selection_from_current_cell(
        selector_profile_id,
        current_cell_selection,
        timing_policy_id=timing_policy_id,
        subject_bird=subject_bird,
        selector_policy_id=selector_policy_id,
    )


__all__ = [
    "PanchaPakshiActivity",
    "PanchaPakshiAdmissionStatus",
    "PanchaPakshiAstronomicalPaksha",
    "PanchaPakshiAstronomicalPakshaInference",
    "PanchaPakshiAstronomicalPakshaInferencePolicy",
    "PanchaPakshiBird",
    "PanchaPakshiCivilTimeSookshmaRoutingPolicy",
    "PanchaPakshiCivilTimeSookshmaSelection",
    "PanchaPakshiCapability",
    "PanchaPakshiConflictWitness",
    "PanchaPakshiCurrentCellSelectionStatus",
    "PanchaPakshiDataError",
    "PanchaPakshiDirectedRelationship",
    "PanchaPakshiError",
    "PanchaPakshiFixedClockCell",
    "PanchaPakshiFixedClockCurrentCellSelection",
    "PanchaPakshiFixedClockCurrentCellSelectionPolicy",
    "PanchaPakshiFixedClockMaterialization",
    "PanchaPakshiFixedClockMaterializationPolicy",
    "PanchaPakshiFirstEatBirdMapping",
    "PanchaPakshiHalf",
    "PanchaPakshiInitialVowelIdentity",
    "PanchaPakshiLocalSolarContext",
    "PanchaPakshiLocalSolarContextPolicy",
    "PanchaPakshiMaterializedCellRelation",
    "PanchaPakshiNakshatraBirdMapping",
    "PanchaPakshiNatalMoonIdentity",
    "PanchaPakshiNatalMoonIdentityPolicy",
    "PanchaPakshiOmission",
    "PanchaPakshiPaduBirdMapping",
    "PanchaPakshiPaksha",
    "PanchaPakshiProfileDescriptor",
    "PanchaPakshiProfileInfo",
    "PanchaPakshiProvenance",
    "PanchaPakshiRelation",
    "PanchaPakshiSchedule",
    "PanchaPakshiScheduleCell",
    "PanchaPakshiSolarProportionalCell",
    "PanchaPakshiSolarProportionalCurrentCellSelection",
    "PanchaPakshiSolarProportionalCurrentCellSelectionPolicy",
    "PanchaPakshiSolarProportionalMaterialization",
    "PanchaPakshiSolarProportionalMaterializationPolicy",
    "PanchaPakshiSolarBoundaryRelation",
    "PanchaPakshiSource",
    "PanchaPakshiSourceLocator",
    "PanchaPakshiSookshmaInterval",
    "PanchaPakshiScheduleSookshmaCompositionPolicy",
    "PanchaPakshiScheduleSookshmaSelection",
    "PanchaPakshiSookshmaSelection",
    "PanchaPakshiSookshmaSelectorPolicy",
    "PanchaPakshiSookshmaSelectorPolicyId",
    "PanchaPakshiSookshmaTimingPolicyId",
    "PanchaPakshiUromarisiConstitutionStatus",
    "PanchaPakshiWeekday",
    "available_pancha_pakshi_profiles",
    "pancha_pakshi_astronomical_paksha_at",
    "pancha_pakshi_civil_time_sookshma_selection_at",
    "pancha_pakshi_directed_relationship",
    "pancha_pakshi_fixed_clock_current_cell_at",
    "pancha_pakshi_fixed_clock_materialization_at",
    "pancha_pakshi_first_eat_bird_mapping",
    "pancha_pakshi_identity_from_initial_vowel",
    "pancha_pakshi_local_solar_context_at",
    "pancha_pakshi_nakshatra_bird_mapping",
    "pancha_pakshi_natal_moon_identity_at",
    "pancha_pakshi_padu_bird_mapping",
    "pancha_pakshi_profile_info",
    "pancha_pakshi_schedule",
    "pancha_pakshi_schedule_sookshma_temporal_selection",
    "pancha_pakshi_sookshma_temporal_selection",
    "pancha_pakshi_solar_proportional_current_cell_at",
    "pancha_pakshi_solar_proportional_materialization_at",
    "pancha_pakshi_uromarisi_constitution_status",
]
