"""Lossless marriage projection; decisions are computed only by the engine."""
from dataclasses import asdict
from ..models.muhurta_marriage import (MarriageAssessmentResponse,MarriageSnapshotResponse,
                                       MarriageCatalogueResponse,MarriageWindowsResponse)


def serialize_marriage_assessment(result):
    values=asdict(result)
    for name in ('astronomical_findings','personal_findings','composition_findings'):
        values[name]=tuple(dict(asdict(f),effective_restriction=f.effective_restriction,
                               coverage_complete=f.coverage_complete) for f in getattr(result,name))
    return MarriageAssessmentResponse(**values)


def serialize_marriage_snapshot(result):
    values=asdict(result)
    values['assessment']=serialize_marriage_assessment(result.assessment)
    return MarriageSnapshotResponse(**values)


def serialize_marriage_catalogue(result):
    return MarriageCatalogueResponse(**dict(result,rules=tuple(asdict(r) for r in result['rules']),
        rule_contracts=tuple(asdict(r) for r in result['rule_contracts']),
        remedy_contracts=tuple(asdict(r) for r in result['remedy_contracts']),
        default_limits=asdict(result['default_limits']),hard_maxima=asdict(result['hard_maxima'])))


def serialize_marriage_windows(result):
    values=asdict(result)
    values['eligible_intervals']=tuple(asdict(i) for i in result.eligible_intervals)
    values['indeterminate_cell_indices']=result.indeterminate_cell_indices
    values['findings']=tuple(dict(asdict(f),effective_restriction=f.effective_restriction,
                                 coverage_complete=f.coverage_complete) for f in result.findings)
    return MarriageWindowsResponse(**values)
