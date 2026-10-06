"""Transport preserves the canonical engine search; no scoring or ranking here."""
from dataclasses import asdict

from ..models.muhurta import TaraBalaResponse, ChandraBalaResponse
from ..models.muhurta_search import (
    MuhurtaSearchRequest, MuhurtaSearchResponse, MuhurtaSearchPolicyResponse,
    MuhurtaSearchMomentResponse, MuhurtaSearchWindowResponse, MuhurtaSearchProvenanceResponse,
)
from ..serializers.panchanga import serialize_panchanga_result
from .muhurta import _policy_response, _score_response


def _moment_response(moment):
    personal = moment.natal_mode == "tara_chandra"
    return MuhurtaSearchMomentResponse(
        jd_ut1=moment.jd_ut1, jd_tt=moment.jd_tt, jd_tdb=moment.jd_tdb,
        delta_t_source=moment.delta_t_source, clock_identity=moment.clock_identity,
        sun_tropical_longitude=moment.sun_tropical_longitude,
        moon_tropical_longitude=moment.moon_tropical_longitude,
        ayanamsa_degrees=moment.ayanamsa_degrees,
        panchanga=serialize_panchanga_result(moment.panchanga), score=_score_response(moment.score),
        tara=TaraBalaResponse(**asdict(moment.score.tara)) if personal else None,
        chandra=ChandraBalaResponse(**asdict(moment.score.chandra)) if personal else None,
    )


def compute_muhurta_search(engine, request: MuhurtaSearchRequest) -> MuhurtaSearchResponse:
    result = engine.find_muhurta_windows(
        request.start_jd_ut1, request.end_jd_ut1,
        janma_moon_sidereal_lon=request.janma_moon_sidereal_lon,
        policy=request.policy.to_engine(),
    )
    policy = result.policy
    personal = result.janma_moon_sidereal_lon is not None
    return MuhurtaSearchResponse(
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
            peak=_moment_response(w.peak), left_unqualified_jd=w.left_unqualified_jd,
            right_unqualified_jd=w.right_unqualified_jd,
        ) for w in result.windows],
        provenance=MuhurtaSearchProvenanceResponse(),
    )
