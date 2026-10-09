"""Lossless projection of canonical Shuddhi vessels; no doctrine here."""
from dataclasses import asdict
from ..models.panchanga_shuddhi import ShuddhiAssessmentResponse, ShuddhiCatalogueResponse, ShuddhiDayResponse


def serialize_shuddhi_assessment(result):
    return ShuddhiAssessmentResponse(**asdict(result))


def serialize_shuddhi_catalogue(result):
    return ShuddhiCatalogueResponse(**asdict(result))


def serialize_shuddhi_day(result):
    return ShuddhiDayResponse(**asdict(result))
