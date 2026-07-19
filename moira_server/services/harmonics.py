"""Service layer for P12-02 harmonic projection routes."""

from __future__ import annotations

from moira.harmonics import (
    HARMONIC_PRESETS,
    HarmonicAspect,
    HarmonicConjunction,
    HarmonicOrbPolicy,
    HarmonicPosition,
    HarmonicSweepEntry,
    age_harmonic,
    calculate_harmonic,
    composite_harmonic,
    harmonic_aspects,
    harmonic_conjunctions,
    harmonic_pattern_score,
    harmonic_sweep,
    vibrational_fingerprint,
)
from moira.harmonic_transits import (
    HarmonicTransitMember,
    HarmonicTransitPatternSample,
    HarmonicTransitSample,
    HarmonicTransitWindow,
    MixedOriginHarmonicTransitForecastPolicy,
    MixedOriginHarmonicTransitMode,
    mixed_origin_harmonic_transit_forecast,
)

from ..models.harmonics import (
    HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN,
    HARMONICS_MAX_FORECAST_HARMONICS,
    HARMONICS_MAX_FORECAST_SAMPLES,
    HARMONICS_MAX_FORECAST_WORK_UNITS,
    HarmonicAgeChartRequest,
    HarmonicAspectResponse,
    HarmonicAspectsRequest,
    HarmonicAspectsResponse,
    HarmonicCatalogResponse,
    HarmonicChartRequest,
    HarmonicChartResponse,
    HarmonicCompositeRequest,
    HarmonicCompositeResponse,
    HarmonicConjunctionRequest,
    HarmonicConjunctionResponse,
    HarmonicConjunctionsResponse,
    HarmonicFingerprintResponse,
    HarmonicPatternScoreResponse,
    HarmonicPositionResponse,
    HarmonicPresetResponse,
    HarmonicProvenanceResponse,
    HarmonicOrbPolicyResponse,
    HarmonicSweepEntryResponse,
    HarmonicSweepRequest,
    HarmonicSweepResponse,
    HarmonicTransitForecastPolicyResponse,
    HarmonicTransitForecastProvenanceResponse,
    HarmonicTransitForecastRequest,
    HarmonicTransitForecastResponse,
    HarmonicTransitMemberIdentityResponse,
    HarmonicTransitMemberResponse,
    HarmonicTransitPatternSampleResponse,
    HarmonicTransitWindowResponse,
)


def _preset_for(harmonic: float) -> tuple[str | None, str | None]:
    value = float(harmonic)
    if not value.is_integer():
        return None, None
    return HARMONIC_PRESETS.get(int(value), (None, None))


def _harmonic_kind(harmonic: float) -> str:
    return "integer" if float(harmonic).is_integer() else "continuous_multiplier"


def _harmonic_validation_stage(harmonic: float) -> str:
    return (
        "integer_harmonic_validation"
        if float(harmonic).is_integer()
        else "continuous_multiplier_validation"
    )


def _orb_policy_for(reference_orb_deg: float) -> HarmonicOrbPolicy:
    return HarmonicOrbPolicy(reference_orb_deg=reference_orb_deg)


def _serialize_orb_policy(
    policy: HarmonicOrbPolicy,
    *,
    harmonic: float | None,
    request_mode: str,
) -> HarmonicOrbPolicyResponse:
    truth = None if harmonic is None else policy.resolve(harmonic)
    return HarmonicOrbPolicyResponse(
        scaling_mode=policy.scaling_mode.value,
        reference_harmonic=1.0,
        reference_orb_deg=policy.reference_orb_deg,
        projected_orb_limit_deg=(
            None if truth is None else truth.projected_orb_limit_deg
        ),
        source_orb_limit_deg=(
            None if truth is None else truth.source_orb_limit_deg
        ),
        resolved_harmonic=None if truth is None else truth.harmonic,
        authority=policy.authority,
        source_locator=policy.source_locator,
        formula=policy.formula,
        continuous_extension=(
            False if truth is None else truth.noninteger_extension
        ),
        request_mode=request_mode,
    )


def _orb_request_mode(request) -> str:
    return "explicit_policy" if request.orb_policy is not None else "legacy_orb_adapter"


def _serialize_position(position: HarmonicPosition) -> HarmonicPositionResponse:
    return HarmonicPositionResponse(
        body=position.planet,
        natal_longitude=position.natal_longitude,
        harmonic_longitude=position.harmonic_longitude,
        harmonic=position.harmonic,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
    )


def _serialize_conjunction(conjunction: HarmonicConjunction) -> HarmonicConjunctionResponse:
    return HarmonicConjunctionResponse(
        planet_a=conjunction.planet_a,
        planet_b=conjunction.planet_b,
        harmonic=conjunction.harmonic,
        orb=conjunction.orb,
        longitude=conjunction.longitude,
    )


def _serialize_aspect(aspect: HarmonicAspect) -> HarmonicAspectResponse:
    return HarmonicAspectResponse(
        planet_a=aspect.planet_a,
        planet_b=aspect.planet_b,
        harmonic=aspect.harmonic,
        orb=aspect.orb,
        separation=aspect.separation,
    )


def _serialize_sweep_entry(entry: HarmonicSweepEntry) -> HarmonicSweepEntryResponse:
    return HarmonicSweepEntryResponse(
        harmonic=entry.harmonic,
        score=entry.score,
        n_conjunctions=entry.n_conjunctions,
        largest_cluster=entry.largest_cluster,
    )


def _serialize_transit_member(
    member: HarmonicTransitMember,
) -> HarmonicTransitMemberResponse:
    return HarmonicTransitMemberResponse(
        body=member.body,
        origin=member.origin.value,
        source_longitude_deg=member.source_longitude_deg,
        projected_longitude_deg=member.projected_longitude_deg,
    )


def _serialize_transit_pattern_sample(
    sample: HarmonicTransitPatternSample,
) -> HarmonicTransitPatternSampleResponse:
    return HarmonicTransitPatternSampleResponse(
        sample_index=sample.sample_index,
        jd_ut=sample.jd_ut,
        harmonic=sample.harmonic,
        mode=sample.mode.value,
        members=[_serialize_transit_member(member) for member in sample.members],
        projected_spread_deg=sample.projected_spread_deg,
        source_residual_spread_deg=sample.source_residual_spread_deg,
        projected_orb_limit_deg=sample.projected_orb_limit_deg,
        source_orb_limit_deg=sample.source_orb_limit_deg,
    )


def _serialize_transit_window(
    window: HarmonicTransitWindow,
) -> HarmonicTransitWindowResponse:
    return HarmonicTransitWindowResponse(
        harmonic=window.harmonic,
        mode=window.mode.value,
        member_identities=[
            HarmonicTransitMemberIdentityResponse(
                origin=origin.value,
                body=body,
            )
            for origin, body in window.member_identities
        ],
        first_sampled_jd_ut=window.first_sampled_jd_ut,
        peak_sampled_jd_ut=window.peak_sampled_jd_ut,
        last_sampled_jd_ut=window.last_sampled_jd_ut,
        observed_duration_days=window.observed_duration_days,
        sample_count=window.sample_count,
        samples=[
            _serialize_transit_pattern_sample(sample) for sample in window.samples
        ],
    )


def list_harmonic_presets() -> HarmonicCatalogResponse:
    presets = [
        HarmonicPresetResponse(
            harmonic=harmonic,
            name=name,
            description=description,
        )
        for harmonic, (name, description) in sorted(HARMONIC_PRESETS.items())
    ]
    return HarmonicCatalogResponse(
        presets=presets,
        count=len(presets),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="HARMONIC_PRESETS",
            harmonic_kind="catalog",
            stage_sequence=[
                "preset_catalog_read",
                "harmonic_preset_serialization",
            ],
        ),
    )


def compute_harmonic_chart(request: HarmonicChartRequest) -> HarmonicChartResponse:
    positions = calculate_harmonic(request.longitudes, request.harmonic)
    preset_name, preset_description = _preset_for(request.harmonic)
    harmonic_kind = _harmonic_kind(request.harmonic)
    effective_harmonic = positions[0].harmonic if positions else float(request.harmonic)
    return HarmonicChartResponse(
        positions=[_serialize_position(position) for position in positions],
        requested_harmonic=float(request.harmonic),
        effective_harmonic=effective_harmonic,
        harmonic_kind=harmonic_kind,
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="calculate_harmonic",
            harmonic_kind=harmonic_kind,
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                _harmonic_validation_stage(request.harmonic),
                "harmonic_projection_computation",
                "harmonic_chart_response_serialization",
            ],
        ),
    )


def compute_age_harmonic_chart(request: HarmonicAgeChartRequest) -> HarmonicChartResponse:
    positions = age_harmonic(request.longitudes, request.jd_birth, request.jd_now)
    effective_harmonic = positions[0].harmonic if positions else 0.0
    return HarmonicChartResponse(
        positions=[_serialize_position(position) for position in positions],
        requested_harmonic=effective_harmonic,
        effective_harmonic=effective_harmonic,
        harmonic_kind="age_decimal",
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="age_harmonic",
            harmonic_kind="age_decimal",
            stage_sequence=[
                "caller_longitude_validation",
                "age_window_validation",
                "decimal_age_harmonic_derivation",
                "harmonic_projection_computation",
                "age_harmonic_response_serialization",
            ],
            jd_birth=request.jd_birth,
            jd_now=request.jd_now,
            age_harmonic_basis="(jd_now - jd_birth) / tropical_year",
        ),
    )


def compute_harmonic_conjunctions(
    request: HarmonicConjunctionRequest,
) -> HarmonicConjunctionsResponse:
    orb_policy = _orb_policy_for(request.orb)
    conjunctions = harmonic_conjunctions(
        request.longitudes,
        request.harmonic,
        orb_policy=orb_policy,
    )
    preset_name, preset_description = _preset_for(request.harmonic)
    harmonic_kind = _harmonic_kind(request.harmonic)
    return HarmonicConjunctionsResponse(
        conjunctions=[_serialize_conjunction(conjunction) for conjunction in conjunctions],
        requested_harmonic=float(request.harmonic),
        effective_harmonic=float(request.harmonic),
        orb=request.orb,
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="harmonic_conjunctions",
            harmonic_kind=harmonic_kind,
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                _harmonic_validation_stage(request.harmonic),
                "orb_validation",
                "harmonic_conjunction_computation",
                "harmonic_conjunction_response_serialization",
            ],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=request.harmonic,
                request_mode=_orb_request_mode(request),
            ),
        ),
    )


def compute_harmonic_pattern_score(
    request: HarmonicConjunctionRequest,
) -> HarmonicPatternScoreResponse:
    orb_policy = _orb_policy_for(request.orb)
    score = harmonic_pattern_score(
        request.longitudes,
        request.harmonic,
        orb_policy=orb_policy,
    )
    preset_name, preset_description = _preset_for(request.harmonic)
    harmonic_kind = _harmonic_kind(request.harmonic)
    conjunctions = [_serialize_conjunction(conjunction) for conjunction in score.conjunctions]
    return HarmonicPatternScoreResponse(
        pattern_score=score.score,
        conjunctions=conjunctions,
        cluster_sizes=list(score.cluster_sizes),
        score=score.score,
        requested_harmonic=float(request.harmonic),
        effective_harmonic=float(score.harmonic),
        orb=request.orb,
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="harmonic_pattern_score",
            harmonic_kind=harmonic_kind,
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                _harmonic_validation_stage(request.harmonic),
                "orb_validation",
                "harmonic_conjunction_computation",
                "cluster_score_computation",
                "harmonic_pattern_score_response_serialization",
            ],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=request.harmonic,
                request_mode=_orb_request_mode(request),
            ),
            note="Pattern score is a density measure over harmonic conjunction clusters, not interpretive judgment.",
        ),
    )


def compute_harmonic_aspects(request: HarmonicAspectsRequest) -> HarmonicAspectsResponse:
    orb_policy = _orb_policy_for(request.orb)
    aspects = harmonic_aspects(
        request.longitudes,
        max_harmonic=request.max_harmonic,
        orb_policy=orb_policy,
    )
    return HarmonicAspectsResponse(
        aspects=[_serialize_aspect(aspect) for aspect in aspects],
        max_harmonic=request.max_harmonic,
        orb=request.orb,
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="harmonic_aspects",
            harmonic_kind="range_sweep",
            stage_sequence=[
                "caller_longitude_validation",
                "max_harmonic_validation",
                "orb_validation",
                "harmonic_aspect_computation",
                "harmonic_aspect_response_serialization",
            ],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=None,
                request_mode=_orb_request_mode(request),
            ),
        ),
    )


def compute_harmonic_sweep(request: HarmonicSweepRequest) -> HarmonicSweepResponse:
    orb_policy = _orb_policy_for(request.orb)
    entries = harmonic_sweep(
        request.longitudes,
        request.max_harmonic,
        orb_policy=orb_policy,
    )
    return HarmonicSweepResponse(
        entries=[_serialize_sweep_entry(entry) for entry in entries],
        max_harmonic=request.max_harmonic,
        orb=request.orb,
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="harmonic_sweep",
            harmonic_kind="range_sweep",
            stage_sequence=[
                "caller_longitude_validation",
                "max_harmonic_validation",
                "orb_validation",
                "bounded_harmonic_sweep_computation",
                "harmonic_sweep_response_serialization",
            ],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=None,
                request_mode=_orb_request_mode(request),
            ),
            note="Sweep score is a pattern density measure, not interpretive judgment.",
        ),
    )


def compute_harmonic_fingerprint(request: HarmonicSweepRequest) -> HarmonicFingerprintResponse:
    orb_policy = _orb_policy_for(request.orb)
    fingerprint = vibrational_fingerprint(
        request.longitudes,
        request.max_harmonic,
        orb_policy=orb_policy,
    )
    return HarmonicFingerprintResponse(
        sweep=[_serialize_sweep_entry(entry) for entry in fingerprint.sweep],
        dominant=list(fingerprint.dominant),
        total_score=fingerprint.total_score,
        peak_harmonic=fingerprint.peak_harmonic,
        peak_score=fingerprint.peak_score,
        max_harmonic=request.max_harmonic,
        orb=request.orb,
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="vibrational_fingerprint",
            harmonic_kind="range_sweep",
            stage_sequence=[
                "caller_longitude_validation",
                "max_harmonic_validation",
                "orb_validation",
                "bounded_harmonic_sweep_computation",
                "vibrational_fingerprint_response_serialization",
            ],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=None,
                request_mode=_orb_request_mode(request),
            ),
            note="Fingerprint score is a pattern density summary, not interpretive judgment.",
        ),
    )


def compute_composite_harmonic(request: HarmonicCompositeRequest) -> HarmonicCompositeResponse:
    orb_policy = _orb_policy_for(request.orb)
    conjunctions = composite_harmonic(
        request.longitudes_a,
        request.longitudes_b,
        request.harmonic,
        None,
        request.label_a,
        request.label_b,
        orb_policy=orb_policy,
    )
    preset_name, preset_description = _preset_for(request.harmonic)
    return HarmonicCompositeResponse(
        conjunctions=[_serialize_conjunction(conjunction) for conjunction in conjunctions],
        requested_harmonic=float(request.harmonic),
        effective_harmonic=float(request.harmonic),
        orb=request.orb,
        label_a=request.label_a,
        label_b=request.label_b,
        input_count_a=len(request.longitudes_a),
        input_count_b=len(request.longitudes_b),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="composite_harmonic",
            harmonic_kind="composite",
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                "composite_label_validation",
                _harmonic_validation_stage(request.harmonic),
                "orb_validation",
                "cross_chart_harmonic_conjunction_computation",
                "composite_harmonic_response_serialization",
            ],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=request.harmonic,
                request_mode=_orb_request_mode(request),
            ),
        ),
    )


def compute_harmonic_transit_forecast(
    request: HarmonicTransitForecastRequest,
) -> HarmonicTransitForecastResponse:
    """Evaluate bounded VA-informed complete triples over supplied samples."""

    orb_policy = _orb_policy_for(request.orb)
    policy = MixedOriginHarmonicTransitForecastPolicy(
        harmonics=tuple(request.harmonics),
        modes=tuple(MixedOriginHarmonicTransitMode(mode) for mode in request.modes),
        orb_policy=orb_policy,
        minimum_observed_duration_days=request.minimum_observed_duration_days,
        maximum_sample_gap_days=request.maximum_sample_gap_days,
    )
    forecast = mixed_origin_harmonic_transit_forecast(
        request.natal_longitudes,
        tuple(
            HarmonicTransitSample(
                jd_ut=sample.jd_ut,
                longitudes=sample.longitudes,
            )
            for sample in request.transit_samples
        ),
        policy,
    )
    return HarmonicTransitForecastResponse(
        windows=[_serialize_transit_window(window) for window in forecast.windows],
        window_count=forecast.window_count,
        natal_bodies=list(forecast.natal_bodies),
        transit_bodies=list(forecast.transit_bodies),
        transit_sample_count=forecast.transit_sample_count,
        policy=HarmonicTransitForecastPolicyResponse(
            harmonics=list(policy.harmonics),
            modes=[mode.value for mode in policy.modes],
            orb_policy=_serialize_orb_policy(
                orb_policy,
                harmonic=None,
                request_mode=_orb_request_mode(request),
            ),
            minimum_observed_duration_days=policy.minimum_observed_duration_days,
            maximum_sample_gap_days=policy.maximum_sample_gap_days,
        ),
        provenance=HarmonicTransitForecastProvenanceResponse(
            evaluation_scope=forecast.evaluation_scope,
            claim_boundary=forecast.claim_boundary,
            source_locators=list(forecast.source_locators),
            bounds={
                "max_bodies_per_origin": HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN,
                "max_samples": HARMONICS_MAX_FORECAST_SAMPLES,
                "max_harmonics": HARMONICS_MAX_FORECAST_HARMONICS,
                "max_candidate_evaluations": HARMONICS_MAX_FORECAST_WORK_UNITS,
            },
        ),
    )
