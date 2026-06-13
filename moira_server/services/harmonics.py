"""Service layer for P12-02 harmonic projection routes."""

from __future__ import annotations

from moira.harmonics import (
    HARMONIC_PRESETS,
    HarmonicAspect,
    HarmonicConjunction,
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

from ..models.harmonics import (
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
    HarmonicSweepEntryResponse,
    HarmonicSweepRequest,
    HarmonicSweepResponse,
)


def _preset_for(harmonic: int) -> tuple[str | None, str | None]:
    return HARMONIC_PRESETS.get(harmonic, (None, None))


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
    return HarmonicChartResponse(
        positions=[_serialize_position(position) for position in positions],
        requested_harmonic=float(request.harmonic),
        effective_harmonic=float(request.harmonic),
        harmonic_kind="integer",
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="calculate_harmonic",
            harmonic_kind="integer",
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                "integer_harmonic_validation",
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
    conjunctions = harmonic_conjunctions(
        request.longitudes,
        request.harmonic,
        request.orb,
    )
    preset_name, preset_description = _preset_for(request.harmonic)
    return HarmonicConjunctionsResponse(
        conjunctions=[_serialize_conjunction(conjunction) for conjunction in conjunctions],
        requested_harmonic=float(request.harmonic),
        effective_harmonic=float(request.harmonic),
        orb=request.orb,
        input_count=len(request.longitudes),
        provenance=HarmonicProvenanceResponse(
            engine_entrypoint="harmonic_conjunctions",
            harmonic_kind="integer",
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                "integer_harmonic_validation",
                "orb_validation",
                "harmonic_conjunction_computation",
                "harmonic_conjunction_response_serialization",
            ],
        ),
    )


def compute_harmonic_pattern_score(
    request: HarmonicConjunctionRequest,
) -> HarmonicPatternScoreResponse:
    score = harmonic_pattern_score(
        request.longitudes,
        request.harmonic,
        request.orb,
    )
    preset_name, preset_description = _preset_for(request.harmonic)
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
            harmonic_kind="integer",
            preset_name=preset_name,
            preset_description=preset_description,
            stage_sequence=[
                "caller_longitude_validation",
                "integer_harmonic_validation",
                "orb_validation",
                "harmonic_conjunction_computation",
                "cluster_score_computation",
                "harmonic_pattern_score_response_serialization",
            ],
            note="Pattern score is a density measure over harmonic conjunction clusters, not interpretive judgment.",
        ),
    )


def compute_harmonic_aspects(request: HarmonicAspectsRequest) -> HarmonicAspectsResponse:
    aspects = harmonic_aspects(
        request.longitudes,
        request.orb,
        request.max_harmonic,
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
        ),
    )


def compute_harmonic_sweep(request: HarmonicSweepRequest) -> HarmonicSweepResponse:
    entries = harmonic_sweep(
        request.longitudes,
        request.max_harmonic,
        request.orb,
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
            note="Sweep score is a pattern density measure, not interpretive judgment.",
        ),
    )


def compute_harmonic_fingerprint(request: HarmonicSweepRequest) -> HarmonicFingerprintResponse:
    fingerprint = vibrational_fingerprint(
        request.longitudes,
        request.max_harmonic,
        request.orb,
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
            note="Fingerprint score is a pattern density summary, not interpretive judgment.",
        ),
    )


def compute_composite_harmonic(request: HarmonicCompositeRequest) -> HarmonicCompositeResponse:
    conjunctions = composite_harmonic(
        request.longitudes_a,
        request.longitudes_b,
        request.harmonic,
        request.orb,
        request.label_a,
        request.label_b,
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
                "integer_harmonic_validation",
                "orb_validation",
                "cross_chart_harmonic_conjunction_computation",
                "composite_harmonic_response_serialization",
            ],
        ),
    )
