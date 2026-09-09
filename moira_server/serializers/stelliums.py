"""Lossless evidence serialization; no geometry, counting, or presentation rounding."""

from dataclasses import asdict

from moira.stelliums import StelliumAnalysis
from ..models.stelliums import StelliumAnalysisResponse


def serialize_stellium_analysis(result: StelliumAnalysis) -> StelliumAnalysisResponse:
    payload = asdict(result)
    payload["policy"]["min_planets"] = result.policy.min_planets
    return StelliumAnalysisResponse.model_validate(payload)


__all__ = ["serialize_stellium_analysis"]
