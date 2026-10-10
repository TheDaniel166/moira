"""Source-bound Gochara snapshot requests and typed engine views."""
from typing import Literal
from pydantic import ConfigDict, Field, model_validator
from moira.gochara import (
    GOCHARA_PLANETS, GocharaSourceProfile, GocharaVedhaMode,
    GocharaCompleteness, GocharaBavMode, GocharaAdmissionStatus,
    GocharaBaselineClass, GocharaBavAvailability, GocharaVedhaStatus,
    GocharaVedhaRelationClass, GocharaLocalCondition,
)
from .common import _StrictModel
from ._vedic_inputs import ClassicalPlanet, FiniteNumber, RekhaTable

GocharaTopic = Literal[
    "activation", "ashtakavarga", "astronomy", "completeness", "counter_vedha",
    "forecast", "murthi", "nakshatra", "nodes", "participants", "reference",
    "remedies", "source_discrepancies", "source_profile", "strength_context", "vedha",
]


class GocharaPolicyRequest(_StrictModel):
    source_profile: GocharaSourceProfile = GocharaSourceProfile.PHALADEEPICA_26
    vedha_mode: GocharaVedhaMode = GocharaVedhaMode.ORDINARY
    completeness: GocharaCompleteness = GocharaCompleteness.RETAIN_PARTIAL
    bav_mode: GocharaBavMode = GocharaBavMode.RAW_IF_SUPPLIED


class GocharaSnapshotRequest(_StrictModel):
    """Positions share a caller-owned sidereal frame; BAV is raw and same-birth."""
    natal_moon_sidereal_longitude: FiniteNumber
    transit_sidereal_longitudes: dict[ClassicalPlanet, FiniteNumber] = Field(min_length=1, max_length=7)
    raw_bav: dict[ClassicalPlanet, RekhaTable] | None = None
    policy: GocharaPolicyRequest = Field(default_factory=GocharaPolicyRequest)

    @model_validator(mode="after")
    def _input_scope(self) -> "GocharaSnapshotRequest":
        positions = self.transit_sidereal_longitudes
        if self.policy.completeness is GocharaCompleteness.REQUIRE_COMPLETE:
            missing = set(GOCHARA_PLANETS) - positions.keys()
            if missing:
                raise ValueError(f"complete snapshot required; missing: {sorted(missing)}")
        if self.raw_bav and set(self.raw_bav) - positions.keys():
            raise ValueError("raw_bav subjects must have supplied transit positions")
        if self.raw_bav and self.policy.bav_mode is GocharaBavMode.OMIT:
            raise ValueError("raw_bav was supplied but BAV is omitted by policy")
        if self.policy.bav_mode is GocharaBavMode.REQUIRE_ALL_RAW:
            missing = positions.keys() - (self.raw_bav or {}).keys()
            if missing:
                raise ValueError(f"raw BAV required for observed subjects: {sorted(missing)}")
        return self


class _GocharaView(_StrictModel):
    """Explicit fields read named attributes of frozen engine vessels."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class GocharaDoctrineOptionResponse(_GocharaView):
    id: str
    topic: GocharaTopic
    status: GocharaAdmissionStatus
    authority_kind: str
    sources: tuple[str, ...]
    statement: str
    limitation: str


class GocharaDoctrineOptionsResponse(_StrictModel):
    options: tuple[GocharaDoctrineOptionResponse, ...]


class GocharaPolicyResponse(GocharaPolicyRequest):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    reference: str
    subjects: tuple[ClassicalPlanet, ...]
    blockers: tuple[ClassicalPlanet, ...]
    selected_options: tuple[GocharaDoctrineOptionResponse, ...]


class GocharaPositionResponse(_GocharaView):
    planet: ClassicalPlanet
    sidereal_longitude: float
    rashi_index: int
    degrees_in_sign: float


class GocharaVedhaWitnessResponse(_GocharaView):
    subject: GocharaPositionResponse
    blocker: GocharaPositionResponse
    janma_rashi_index: int
    subject_house: int
    blocker_house: int
    exempt: bool
    source: str
    relation_class: GocharaVedhaRelationClass
    directed_pair: tuple[int, int]


class GocharaBavResponse(_GocharaView):
    planet: ClassicalPlanet
    rekhas: tuple[int, ...]
    total_rekhas: int


class GocharaPlanetResponse(_GocharaView):
    position: GocharaPositionResponse
    janma_rashi_index: int
    policy: GocharaPolicyResponse
    house_from_moon: int
    baseline_favorable: bool
    baseline_source: str
    indication: str
    indication_source: str
    vedha_house: int | None
    vedha_source: str
    vedha_witnesses: tuple[GocharaVedhaWitnessResponse, ...]
    active_vedha_witnesses: tuple[GocharaVedhaWitnessResponse, ...]
    exempt_vedha_witnesses: tuple[GocharaVedhaWitnessResponse, ...]
    eligible_blockers: tuple[ClassicalPlanet, ...]
    missing_blockers: tuple[ClassicalPlanet, ...]
    vedha_status: GocharaVedhaStatus
    vedha_observation_complete: bool | None
    ashtakavarga_rekhas: int | None
    ashtakavarga_source: str | None
    evaluated_layers: tuple[str, ...]
    baseline_class: GocharaBaselineClass
    ashtakavarga_availability: GocharaBavAvailability


class GocharaResultResponse(_GocharaView):
    natal_moon_sidereal_longitude: float
    positions: tuple[GocharaPositionResponse, ...]
    bhinna: tuple[GocharaBavResponse, ...]
    policy: GocharaPolicyResponse
    profile: str
    source_edition: str
    source_url: str
    reference_source: str
    position_origin: str
    blocker_participants: tuple[ClassicalPlanet, ...]
    outside_profile_layers: tuple[str, ...]
    janma_rashi_index: int
    missing_planets: tuple[ClassicalPlanet, ...]
    planets: tuple[GocharaPlanetResponse, ...]


class GocharaLocalProfileResponse(_GocharaView):
    assessment: GocharaPlanetResponse
    planet: ClassicalPlanet
    condition: GocharaLocalCondition
    ashtakavarga_rekhas: int | None


class GocharaChartSummaryResponse(_GocharaView):
    favorable_planets: tuple[ClassicalPlanet, ...]
    outside_favorable_planets: tuple[ClassicalPlanet, ...]
    blocked_planets: tuple[ClassicalPlanet, ...]
    unobstructed_planets: tuple[ClassicalPlanet, ...]
    incomplete_verdict_planets: tuple[ClassicalPlanet, ...]
    omitted_vedha_planets: tuple[ClassicalPlanet, ...]
    incomplete_observation_planets: tuple[ClassicalPlanet, ...]
    raw_bav_planets: tuple[ClassicalPlanet, ...]
    missing_planets: tuple[ClassicalPlanet, ...]
    condition_counts: tuple[tuple[GocharaLocalCondition, int], ...]


class GocharaNetworkNodeResponse(_GocharaView):
    planet: ClassicalPlanet
    blocking: tuple[GocharaVedhaWitnessResponse, ...]
    blocked_by: tuple[GocharaVedhaWitnessResponse, ...]
    exempt_blocking: tuple[GocharaVedhaWitnessResponse, ...]
    exempt_from: tuple[GocharaVedhaWitnessResponse, ...]
    observed_out_degree: int
    observed_in_degree: int


class GocharaVedhaNetworkResponse(_GocharaView):
    nodes: tuple[GocharaNetworkNodeResponse, ...]
    active_edges: tuple[GocharaVedhaWitnessResponse, ...]
    exempt_edges: tuple[GocharaVedhaWitnessResponse, ...]
    vedha_evaluated: bool
    observed_unconnected_planets: tuple[ClassicalPlanet, ...]
    incomplete_observation_planets: tuple[ClassicalPlanet, ...]
    missing_planets: tuple[ClassicalPlanet, ...]


class GocharaSubsystemProfileResponse(_GocharaView):
    snapshot: GocharaResultResponse
    local_profiles: tuple[GocharaLocalProfileResponse, ...]
    chart_summary: GocharaChartSummaryResponse
    vedha_network: GocharaVedhaNetworkResponse


__all__ = [
    "GocharaPolicyRequest", "GocharaSnapshotRequest", "GocharaDoctrineOptionResponse",
    "GocharaDoctrineOptionsResponse", "GocharaPolicyResponse", "GocharaPositionResponse",
    "GocharaVedhaWitnessResponse", "GocharaBavResponse", "GocharaPlanetResponse",
    "GocharaResultResponse", "GocharaLocalProfileResponse", "GocharaChartSummaryResponse",
    "GocharaNetworkNodeResponse", "GocharaVedhaNetworkResponse", "GocharaSubsystemProfileResponse",
]
