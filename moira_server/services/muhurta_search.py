"""Transport preserves the canonical engine search; no scoring or ranking here."""
from dataclasses import asdict
from types import SimpleNamespace

from moira.muhurta import MuhurtaPolicy

from ..models.muhurta import TaraBalaResponse, ChandraBalaResponse
from ..models.muhurta_search import (
    MuhurtaSearchRequest, MuhurtaSearchResponse, MuhurtaSearchPolicyResponse,
    MuhurtaSearchMomentResponse, MuhurtaSearchWindowResponse, MuhurtaSearchProvenanceResponse,
    MuhurtaPrecomputedScoreRequest, MuhurtaPrecomputedScoreResponse,
    MuhurtaSearchSampleResponse, MuhurtaSearchWithSamplesResponse,
)
from ..serializers.panchanga import serialize_panchanga_result
from .muhurta import _policy_response, _score_response


def _moment_fields(moment):
    personal = moment.natal_mode == "tara_chandra"
    return dict(
        jd_ut1=moment.jd_ut1, jd_tt=moment.jd_tt, jd_tdb=moment.jd_tdb,
        delta_t_source=moment.delta_t_source, clock_identity=moment.clock_identity,
        sun_tropical_longitude=moment.sun_tropical_longitude,
        moon_tropical_longitude=moment.moon_tropical_longitude,
        ayanamsa_degrees=moment.ayanamsa_degrees,
        panchanga=serialize_panchanga_result(moment.panchanga), score=_score_response(moment.score),
        tara=TaraBalaResponse(**asdict(moment.score.tara)) if personal else None,
        chandra=ChandraBalaResponse(**asdict(moment.score.chandra)) if personal else None,
    )


def compute_muhurta_precomputed_score(
    engine, request: MuhurtaPrecomputedScoreRequest,
) -> MuhurtaPrecomputedScoreResponse:
    """Bind the explicit caller clock and longitudes to the canonical chart scorer."""
    chart = SimpleNamespace(
        jd_ut=request.jd_ut1, jd_tt=request.jd_tt,
        planets={
            "Sun": SimpleNamespace(longitude=request.sun_tropical_longitude),
            "Moon": SimpleNamespace(longitude=request.moon_tropical_longitude),
        },
    )
    moment = engine.muhurta_score_for_chart(
        chart, janma_moon_sidereal_lon=request.janma_moon_sidereal_lon,
        ayanamsa_system=request.ayanamsa_system, policy=MuhurtaPolicy(**request.muhurta_policy.model_dump()),
    )
    return MuhurtaPrecomputedScoreResponse(
        **_moment_fields(moment), input_time_basis=moment.input_time_basis,
        delta_t_seconds=(moment.jd_tt - moment.jd_ut1) * 86400,
        janma_moon_sidereal_lon=moment.janma_moon_sidereal_lon, natal_mode=moment.natal_mode,
        policy=_policy_response(moment.policy, personal=moment.natal_mode == "tara_chandra"),
    )


def compute_muhurta_search(
    engine, request: MuhurtaSearchRequest,
) -> MuhurtaSearchResponse | MuhurtaSearchWithSamplesResponse:
    result = engine.find_muhurta_windows(
        request.start_jd_ut1, request.end_jd_ut1,
        janma_moon_sidereal_lon=request.janma_moon_sidereal_lon,
        policy=request.policy.to_engine(),
    )
    policy = result.policy
    personal = result.janma_moon_sidereal_lon is not None
    summary = MuhurtaSearchResponse(
        start_jd_ut1=result.start_jd_ut1, end_jd_ut1=result.end_jd_ut1,
        janma_moon_sidereal_lon=result.janma_moon_sidereal_lon,
        natal_mode="tara_chandra" if personal else "omitted",
        policy=MuhurtaSearchPolicyResponse(
            ayanamsa_system=policy.ayanamsa_system, ayanamsa_mode=policy.ayanamsa_mode,
            muhurta_policy=_policy_response(policy.muhurta_policy, personal=personal),
            step_days=policy.step_days, min_score=policy.min_score, max_results=policy.max_results,
            max_samples=policy.max_samples, max_span_days=policy.max_span_days,
            vara_basis=policy.vara_basis, interval_semantics=policy.interval_semantics,
        ),
        sample_count=len(result.samples), qualifying_sample_count=result.qualifying_sample_count,
        observed_window_count=result.observed_window_count,
        returned_window_count=len(result.windows), truncated=result.truncated,
        windows=[MuhurtaSearchWindowResponse(
            jd_start=w.jd_start, jd_end=w.jd_end, qualifying_jds=list(w.qualifying_jds),
            peak=MuhurtaSearchMomentResponse(**_moment_fields(w.peak)), left_unqualified_jd=w.left_unqualified_jd,
            right_unqualified_jd=w.right_unqualified_jd,
        ) for w in result.windows],
        provenance=MuhurtaSearchProvenanceResponse(),
    )
    if not request.include_samples:
        return summary
    return MuhurtaSearchWithSamplesResponse(
        **summary.model_dump(),
        samples=[
            MuhurtaSearchSampleResponse(
                jd_ut1=sample.jd_ut1, jd_tt=sample.jd_tt, jd_tdb=sample.jd_tdb,
                clock_identity=sample.clock_identity, delta_t_source=sample.delta_t_source,
                sun_tropical_longitude=sample.sun_tropical_longitude,
                moon_tropical_longitude=sample.moon_tropical_longitude,
                ayanamsa_degrees=sample.ayanamsa_degrees, score_total=sample.score.total,
            )
            for sample in result.samples
        ],
    )
