"""Service layer for P-GAP-06 bounded harmogram routes."""

from __future__ import annotations

from moira.harmograms import (
    GaussianWidthParameterMode,
    HarmogramChartDomain,
    HarmogramIntensityFamily,
    HarmogramIntensityPolicy,
    HarmogramOrbMode,
    HarmogramOutputMode,
    HarmogramPolicy,
    HarmogramProjection,
    HarmogramSamplingPolicy,
    HarmogramSymmetryMode,
    HarmogramTraceFamily,
    HarmonicDomain,
    HarmonicVectorNormalizationMode,
    PointSetHarmonicVector,
    PointSetHarmonicVectorPolicy,
    SelfPairMode,
    ZeroAriesPairConstructionMode,
    ZeroAriesPartsHarmonicVector,
    ZeroAriesPartsPolicy,
    harmogram_trace,
    intensity_function_spectrum,
    point_set_harmonic_vector,
    project_harmogram_strength,
    zero_aries_parts_harmonic_vector,
)

from ..models.harmograms import (
    HarmogramComponentResponse,
    HarmogramHarmonicDomainRequest,
    HarmogramHarmonicDomainResponse,
    HarmogramIntensityPolicyRequest,
    HarmogramIntensityPolicyResponse,
    HarmogramIntensitySpectrumEnvelopeResponse,
    HarmogramIntensitySpectrumRequest,
    HarmogramIntensitySpectrumResponse,
    HarmogramPartsPolicyRequest,
    HarmogramPartsPolicyResponse,
    HarmogramPositionRequest,
    HarmogramProjectionDetailResponse,
    HarmogramProjectionEnvelopeResponse,
    HarmogramProjectionRequest,
    HarmogramProjectionTermResponse,
    HarmogramProvenanceResponse,
    HarmogramSourceVectorResponse,
    HarmogramTraceEnvelopeResponse,
    HarmogramTracePolicyResponse,
    HarmogramTraceRequest,
    HarmogramTraceSampleResponse,
    HarmogramTraceSeriesResponse,
    HarmogramVectorEnvelopeResponse,
    HarmogramVectorPolicyRequest,
    HarmogramVectorPolicyResponse,
    HarmogramVectorRequest,
    HarmogramZeroAriesVectorRequest,
)


_ORB_MODE_BY_FAMILY = {
    HarmogramIntensityFamily.COSINE_BELL_HARMONIC_ASPECTS: HarmogramOrbMode.COSINE_BELL,
    HarmogramIntensityFamily.TOP_HAT_HARMONIC_ASPECTS: HarmogramOrbMode.TOP_HAT,
    HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS: HarmogramOrbMode.TRIANGULAR,
    HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS: HarmogramOrbMode.GAUSSIAN,
}

_CHART_DOMAIN_BY_TRACE_FAMILY = {
    HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS: HarmogramChartDomain.DYNAMIC_SKY_ONLY_TRACE,
    HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS: HarmogramChartDomain.TRANSIT_TO_NATAL_TRACE,
    HarmogramTraceFamily.DIRECTED_TO_NATAL_ZERO_ARIES_PARTS: HarmogramChartDomain.DIRECTED_OR_PROGRESSED_TRACE,
    HarmogramTraceFamily.PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS: HarmogramChartDomain.DIRECTED_OR_PROGRESSED_TRACE,
}


def _positions_payload(positions: list[HarmogramPositionRequest]) -> list[dict[str, float | str]]:
    return [{"name": position.name, "degree": position.degree} for position in positions]


def _domain(request: HarmogramHarmonicDomainRequest) -> HarmonicDomain:
    return HarmonicDomain(
        harmonic_start=request.harmonic_start,
        harmonic_stop=request.harmonic_stop,
    )


def _vector_policy(request: HarmogramVectorPolicyRequest) -> PointSetHarmonicVectorPolicy:
    return PointSetHarmonicVectorPolicy(
        normalization_mode=HarmonicVectorNormalizationMode(request.normalization_mode),
        harmonic_domain=_domain(request.harmonic_domain),
    )


def _parts_policy(request: HarmogramPartsPolicyRequest) -> ZeroAriesPartsPolicy:
    return ZeroAriesPartsPolicy(
        pair_construction_mode=ZeroAriesPairConstructionMode(request.pair_construction_mode),
        self_pair_mode=SelfPairMode(request.self_pair_mode),
    )


def _intensity_policy(request: HarmogramIntensityPolicyRequest) -> HarmogramIntensityPolicy:
    family = HarmogramIntensityFamily(request.family)
    return HarmogramIntensityPolicy(
        family=family,
        include_conjunction=request.include_conjunction,
        orb_mode=_ORB_MODE_BY_FAMILY[family],
        symmetry_mode=(
            HarmogramSymmetryMode.STAR_SYMMETRIC
            if request.include_conjunction
            else HarmogramSymmetryMode.CONJUNCTION_EXCLUDED
        ),
        harmonic_domain=_domain(request.harmonic_domain),
        orb_width_deg=request.orb_width_deg,
        gaussian_width_parameter_mode=GaussianWidthParameterMode(
            request.gaussian_width_parameter_mode
        ),
        gaussian_width_deg=request.gaussian_width_deg,
        sample_count=request.sample_count,
    )


def _default_intensity_request_for(
    vector_policy: HarmogramVectorPolicyRequest,
) -> HarmogramIntensityPolicyRequest:
    return HarmogramIntensityPolicyRequest(harmonic_domain=vector_policy.harmonic_domain)


def _same_domain(
    left: HarmogramHarmonicDomainRequest,
    right: HarmogramHarmonicDomainRequest,
) -> bool:
    return (
        left.harmonic_start == right.harmonic_start
        and left.harmonic_stop == right.harmonic_stop
    )


def _provenance(
    *,
    engine_entrypoint: str,
    stage_sequence: list[str],
) -> HarmogramProvenanceResponse:
    return HarmogramProvenanceResponse(
        engine_entrypoint=engine_entrypoint,
        stage_sequence=stage_sequence,
    )


def _serialize_domain(domain: HarmonicDomain) -> HarmogramHarmonicDomainResponse:
    return HarmogramHarmonicDomainResponse(
        harmonic_start=domain.harmonic_start,
        harmonic_stop=domain.harmonic_stop,
        harmonics=list(domain.harmonics),
    )


def _serialize_vector_policy(
    policy: PointSetHarmonicVectorPolicy,
) -> HarmogramVectorPolicyResponse:
    return HarmogramVectorPolicyResponse(
        normalization_mode=str(policy.normalization_mode),
        harmonic_domain=_serialize_domain(policy.harmonic_domain),
    )


def _serialize_parts_policy(policy: ZeroAriesPartsPolicy) -> HarmogramPartsPolicyResponse:
    return HarmogramPartsPolicyResponse(
        pair_construction_mode=str(policy.pair_construction_mode),
        self_pair_mode=str(policy.self_pair_mode),
    )


def _serialize_intensity_policy(
    policy: HarmogramIntensityPolicy,
) -> HarmogramIntensityPolicyResponse:
    return HarmogramIntensityPolicyResponse(
        family=str(policy.family),
        include_conjunction=policy.include_conjunction,
        orb_mode=str(policy.orb_mode),
        orb_scaling_mode=str(policy.orb_scaling_mode),
        symmetry_mode=str(policy.symmetry_mode),
        normalization_mode=str(policy.normalization_mode),
        harmonic_domain=_serialize_domain(policy.harmonic_domain),
        orb_width_deg=policy.orb_width_deg,
        gaussian_width_parameter_mode=str(policy.gaussian_width_parameter_mode),
        gaussian_width_deg=policy.gaussian_width_deg,
        sample_count=policy.sample_count,
    )


def _serialize_components(components) -> list[HarmogramComponentResponse]:
    return [
        HarmogramComponentResponse(
            harmonic=component.harmonic,
            amplitude=component.amplitude,
            phase_deg=component.phase_deg,
        )
        for component in components
    ]


def _serialize_source_vector(
    vector: PointSetHarmonicVector | ZeroAriesPartsHarmonicVector,
) -> HarmogramSourceVectorResponse:
    if isinstance(vector, PointSetHarmonicVector):
        return HarmogramSourceVectorResponse(
            source_kind="point_set",
            vector_policy=_serialize_vector_policy(vector.policy),
            body_names=list(vector.body_names),
            point_count=vector.point_count,
            harmonic_zero_amplitude=vector.harmonic_zero_amplitude,
            components=_serialize_components(vector.components),
        )
    return HarmogramSourceVectorResponse(
        source_kind="zero_aries_parts",
        vector_policy=_serialize_vector_policy(vector.vector_policy),
        parts_policy=_serialize_parts_policy(vector.parts_policy),
        source_body_names=list(vector.source_body_names),
        target_body_names=list(vector.target_body_names),
        parts_count=vector.parts_count,
        harmonic_zero_amplitude=vector.harmonic_zero_amplitude,
        components=_serialize_components(vector.components),
    )


def _serialize_intensity_spectrum(spectrum) -> HarmogramIntensitySpectrumResponse:
    return HarmogramIntensitySpectrumResponse(
        harmonic_number=spectrum.harmonic_number,
        policy=_serialize_intensity_policy(spectrum.policy),
        realization_mode=str(spectrum.realization_mode),
        harmonic_zero_amplitude=spectrum.harmonic_zero_amplitude,
        components=_serialize_components(spectrum.components),
    )


def _serialize_projection(projection: HarmogramProjection) -> HarmogramProjectionDetailResponse:
    return HarmogramProjectionDetailResponse(
        normalization_mode=str(projection.normalization_mode),
        realization_mode=str(projection.realization_mode),
        harmonic_zero_contribution=projection.harmonic_zero_contribution,
        total_strength=projection.total_strength,
        terms=[
            HarmogramProjectionTermResponse(
                harmonic=term.harmonic,
                source_amplitude=term.source_amplitude,
                source_phase_deg=term.source_phase_deg,
                intensity_amplitude=term.intensity_amplitude,
                intensity_phase_deg=term.intensity_phase_deg,
                signed_contribution=term.signed_contribution,
            )
            for term in projection.terms
        ],
    )


def compute_harmogram_vector(
    request: HarmogramVectorRequest,
) -> HarmogramVectorEnvelopeResponse:
    vector = point_set_harmonic_vector(
        _positions_payload(request.positions),
        policy=_vector_policy(request.policy),
    )
    return HarmogramVectorEnvelopeResponse(
        vector=_serialize_source_vector(vector),
        provenance=_provenance(
            engine_entrypoint="point_set_harmonic_vector",
            stage_sequence=[
                "input_validation",
                "point_set_policy_resolution",
                "harmonic_vector_computation",
                "transport_serialization",
            ],
        ),
    )


def compute_harmogram_zero_aries_vector(
    request: HarmogramZeroAriesVectorRequest,
) -> HarmogramVectorEnvelopeResponse:
    if request.positions is not None:
        vector = zero_aries_parts_harmonic_vector(
            positions=_positions_payload(request.positions),
            parts_policy=_parts_policy(request.parts_policy),
            vector_policy=_vector_policy(request.vector_policy),
        )
    else:
        if request.source_positions is None or request.target_positions is None:
            raise ValueError("source_positions and target_positions are required")
        vector = zero_aries_parts_harmonic_vector(
            source_positions=_positions_payload(request.source_positions),
            target_positions=_positions_payload(request.target_positions),
            parts_policy=_parts_policy(request.parts_policy),
            vector_policy=_vector_policy(request.vector_policy),
        )

    return HarmogramVectorEnvelopeResponse(
        vector=_serialize_source_vector(vector),
        provenance=_provenance(
            engine_entrypoint="zero_aries_parts_harmonic_vector",
            stage_sequence=[
                "input_validation",
                "zero_aries_policy_resolution",
                "zero_aries_parts_vector_computation",
                "transport_serialization",
            ],
        ),
    )


def compute_harmogram_intensity_spectrum(
    request: HarmogramIntensitySpectrumRequest,
) -> HarmogramIntensitySpectrumEnvelopeResponse:
    spectrum = intensity_function_spectrum(
        request.harmonic_number,
        policy=_intensity_policy(request.policy),
    )
    return HarmogramIntensitySpectrumEnvelopeResponse(
        spectrum=_serialize_intensity_spectrum(spectrum),
        provenance=_provenance(
            engine_entrypoint="intensity_function_spectrum",
            stage_sequence=[
                "input_validation",
                "intensity_policy_resolution",
                "intensity_spectrum_computation",
                "transport_serialization",
            ],
        ),
    )


def compute_harmogram_projection(
    request: HarmogramProjectionRequest,
) -> HarmogramProjectionEnvelopeResponse:
    intensity_request = request.intensity_policy or _default_intensity_request_for(
        request.vector_policy
    )
    if not _same_domain(request.vector_policy.harmonic_domain, intensity_request.harmonic_domain):
        raise ValueError("vector_policy and intensity_policy must share the same harmonic_domain")

    zero_vector_response = compute_harmogram_zero_aries_vector(request)
    if request.positions is not None:
        vector = zero_aries_parts_harmonic_vector(
            positions=_positions_payload(request.positions),
            parts_policy=_parts_policy(request.parts_policy),
            vector_policy=_vector_policy(request.vector_policy),
        )
    else:
        if request.source_positions is None or request.target_positions is None:
            raise ValueError("source_positions and target_positions are required")
        vector = zero_aries_parts_harmonic_vector(
            source_positions=_positions_payload(request.source_positions),
            target_positions=_positions_payload(request.target_positions),
            parts_policy=_parts_policy(request.parts_policy),
            vector_policy=_vector_policy(request.vector_policy),
        )
    spectrum = intensity_function_spectrum(
        request.harmonic_number,
        policy=_intensity_policy(intensity_request),
    )
    projection = project_harmogram_strength(vector, spectrum)
    return HarmogramProjectionEnvelopeResponse(
        source_vector=zero_vector_response.vector,
        intensity_spectrum=_serialize_intensity_spectrum(spectrum),
        projection=_serialize_projection(projection),
        provenance=_provenance(
            engine_entrypoint="project_harmogram_strength",
            stage_sequence=[
                "input_validation",
                "zero_aries_parts_vector_computation",
                "intensity_spectrum_computation",
                "harmogram_projection",
                "transport_serialization",
            ],
        ),
    )


def _trace_samples_payload(request: HarmogramTraceRequest) -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    for sample in request.samples:
        payload: dict[str, object] = {"time": sample.time}
        if request.trace_family == "dynamic_zero_aries_parts":
            if sample.positions is None:
                raise ValueError("dynamic traces require positions")
            payload["positions"] = _positions_payload(sample.positions)
        elif request.trace_family == "transit_to_natal_zero_aries_parts":
            if sample.transit_positions is None or sample.natal_positions is None:
                raise ValueError("transit-to-natal traces require transit_positions and natal_positions")
            payload["transit_positions"] = _positions_payload(sample.transit_positions)
            payload["natal_positions"] = _positions_payload(sample.natal_positions)
        elif request.trace_family == "directed_to_natal_zero_aries_parts":
            if sample.directed_positions is None or sample.natal_positions is None:
                raise ValueError("directed-to-natal traces require directed_positions and natal_positions")
            payload["directed_positions"] = _positions_payload(sample.directed_positions)
            payload["natal_positions"] = _positions_payload(sample.natal_positions)
        else:
            if sample.progressed_positions is None or sample.natal_positions is None:
                raise ValueError("progressed-to-natal traces require progressed_positions and natal_positions")
            payload["progressed_positions"] = _positions_payload(sample.progressed_positions)
            payload["natal_positions"] = _positions_payload(sample.natal_positions)
        samples.append(payload)
    return samples


def compute_harmogram_trace(
    request: HarmogramTraceRequest,
) -> HarmogramTraceEnvelopeResponse:
    trace_family = HarmogramTraceFamily(request.trace_family)
    policy = HarmogramPolicy(
        point_set_policy=_vector_policy(request.point_set_policy),
        parts_policy=_parts_policy(request.parts_policy),
        intensity_policy=_intensity_policy(request.intensity_policy),
        sampling_policy=HarmogramSamplingPolicy(sample_count=len(request.samples)),
        output_mode=HarmogramOutputMode(request.output_mode),
        chart_domain=_CHART_DOMAIN_BY_TRACE_FAMILY[trace_family],
        trace_family=trace_family,
    )
    trace = harmogram_trace(
        _trace_samples_payload(request),
        harmonic_numbers=tuple(request.harmonic_numbers),
        policy=policy,
    )
    return HarmogramTraceEnvelopeResponse(
        policy=HarmogramTracePolicyResponse(
            trace_family=str(trace.policy.trace_family),
            output_mode=str(trace.policy.output_mode),
            chart_domain=str(trace.policy.chart_domain),
            point_set_policy=_serialize_vector_policy(trace.policy.point_set_policy),
            parts_policy=_serialize_parts_policy(trace.policy.parts_policy),
            intensity_policy=_serialize_intensity_policy(trace.policy.intensity_policy),
            sample_count=len(trace.sample_times),
        ),
        interval_start=trace.interval_start,
        interval_stop=trace.interval_stop,
        sample_times=list(trace.sample_times),
        series=[
            HarmogramTraceSeriesResponse(
                harmonic_number=series.harmonic_number,
                intensity_spectrum=_serialize_intensity_spectrum(series.intensity_spectrum),
                strengths=list(series.strengths),
                samples=[
                    HarmogramTraceSampleResponse(
                        sample_index=sample.sample_index,
                        sample_time=sample.sample_time,
                        source_vector=_serialize_source_vector(sample.source_vector),
                        projection=_serialize_projection(sample.projection),
                        total_strength=sample.total_strength,
                    )
                    for sample in series.samples
                ],
            )
            for series in trace.series
        ],
        series_count=len(trace.series),
        provenance=_provenance(
            engine_entrypoint="harmogram_trace",
            stage_sequence=[
                "input_validation",
                "trace_policy_resolution",
                "caller_supplied_sample_normalization",
                "trace_series_computation",
                "transport_serialization",
            ],
        ),
    )
