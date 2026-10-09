"""Lossless projection of canonical dosha vessels without transport-owned rules."""
from dataclasses import asdict
from ..models.muhurta_dosha import DoshaAssessmentResponse, DoshaCatalogueResponse, DoshaDayResponse


def serialize_dosha_assessment(result):
    return DoshaAssessmentResponse(**asdict(result))


def serialize_dosha_catalogue(result):
    return DoshaCatalogueResponse(**asdict(result))


def serialize_dosha_day(result):
    return DoshaDayResponse(**asdict(result))
