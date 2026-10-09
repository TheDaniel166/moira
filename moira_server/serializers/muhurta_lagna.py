"""Lossless projection of the canonical Lagna evidence vessels."""
from dataclasses import asdict
from ..models.muhurta_lagna import LagnaAssessmentResponse, LagnaSnapshotResponse


def serialize_lagna_assessment(result):
    return LagnaAssessmentResponse(**asdict(result))


def serialize_lagna_snapshot(result):
    return LagnaSnapshotResponse(**asdict(result))
