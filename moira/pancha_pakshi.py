"""First-class, source-scoped Pancha Pakshi public surface.

Pancha Pakshi is represented as a registry of named computational profiles,
not as one ambient canon.  Every computation therefore requires an explicit
``profile_id``.  The first admitted profile is the 1879 Madras
aksara/query-or-name-initial fixed-clock operating schedule; it is not a
natal-Moon identity, an astronomical paksha router, a seasonally scaled clock,
or a scoring doctrine.

The private :mod:`moira._pancha_pakshi` module owns hash-verified source-data
ingestion and exact table materialization.  This module owns the stable public
vessels and delegates to that private layer without exposing its raw profile
object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


class PanchaPakshiCapability(str, Enum):
    """Independently admitted computation available from a profile."""

    AKSARA_IDENTITY = "aksara_identity"
    NOMINAL_SCHEDULE = "nominal_schedule"
    DIRECTED_RELATIONSHIPS = "directed_relationships"
    ASTRONOMICAL_CONTEXT = "astronomical_context"
    NATAL_IDENTITY = "natal_identity"
    FIXED_CLOCK_MATERIALIZATION = "fixed_clock_materialization"
    SOLAR_PROPORTIONAL_MATERIALIZATION = "solar_proportional_materialization"
    AUTHORITY_BIRDS = "authority_birds"
    SUBDIVISIONS = "subdivisions"
    CONDITION = "condition"
    SCORING = "scoring"
    WINDOW_SEARCH = "window_search"


class PanchaPakshiBird(str, Enum):
    VULTURE = "vulture"
    OWL = "owl"
    CROW = "crow"
    COCK = "cock"
    PEACOCK = "peacock"


class PanchaPakshiActivity(str, Enum):
    EAT = "eat"
    WALK = "walk"
    RULE = "rule"
    SLEEP = "sleep"
    DIE = "die"


class PanchaPakshiPaksha(str, Enum):
    """Source labels only; no astronomical phase mapping is implied."""

    PURVA = "purva"
    AMARA = "amara"


class PanchaPakshiHalf(str, Enum):
    DAY = "day"
    NIGHT = "night"


class PanchaPakshiWeekday(str, Enum):
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"


class PanchaPakshiRelation(str, Enum):
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


@dataclass(frozen=True, slots=True)
class PanchaPakshiSourceLocator:
    locator_id: str
    witness_id: str
    label: str
    url: str
    evidence_role: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiSource:
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
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiOmission:
    feature: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class PanchaPakshiConflictWitness:
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
class PanchaPakshiInitialVowelIdentity:
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
_FIXED_CLOCK_MATERIALIZATION_STATUS = (
    "fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell"
)
_SI_SECONDS_PER_DAY = 86_400


def available_pancha_pakshi_profiles() -> tuple[PanchaPakshiProfileDescriptor, ...]:
    """Return explicitly registered profiles; no default is selected."""

    from ._pancha_pakshi import available_pancha_pakshi_profiles as _available

    return _available()


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
            "astronomical paksha inference is not admitted"
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


__all__ = [
    "PanchaPakshiActivity",
    "PanchaPakshiAdmissionStatus",
    "PanchaPakshiBird",
    "PanchaPakshiCapability",
    "PanchaPakshiConflictWitness",
    "PanchaPakshiDataError",
    "PanchaPakshiDirectedRelationship",
    "PanchaPakshiError",
    "PanchaPakshiFixedClockCell",
    "PanchaPakshiFixedClockMaterialization",
    "PanchaPakshiFixedClockMaterializationPolicy",
    "PanchaPakshiHalf",
    "PanchaPakshiInitialVowelIdentity",
    "PanchaPakshiLocalSolarContext",
    "PanchaPakshiLocalSolarContextPolicy",
    "PanchaPakshiMaterializedCellRelation",
    "PanchaPakshiOmission",
    "PanchaPakshiPaksha",
    "PanchaPakshiProfileDescriptor",
    "PanchaPakshiProfileInfo",
    "PanchaPakshiProvenance",
    "PanchaPakshiRelation",
    "PanchaPakshiSchedule",
    "PanchaPakshiScheduleCell",
    "PanchaPakshiSolarBoundaryRelation",
    "PanchaPakshiSource",
    "PanchaPakshiSourceLocator",
    "PanchaPakshiWeekday",
    "available_pancha_pakshi_profiles",
    "pancha_pakshi_directed_relationship",
    "pancha_pakshi_fixed_clock_materialization_at",
    "pancha_pakshi_identity_from_initial_vowel",
    "pancha_pakshi_local_solar_context_at",
    "pancha_pakshi_profile_info",
    "pancha_pakshi_schedule",
]
