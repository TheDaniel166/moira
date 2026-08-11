"""Transport-to-engine adapter for bounded Horary evidence composition."""

from __future__ import annotations

from datetime import timezone

from moira import Moira
from moira.horary import (
    HoraryEvidenceProfile,
    HoraryEvidenceState,
    HoraryHousePolicy,
    HoraryQuestionReceipt,
    HoraryQuestionTimeBasis,
    HoraryQuestionTimeReceipt,
    HorarySourceCalendar,
)
from moira.julian import jd_from_datetime, utc_to_ut1

from ..models.horary import HoraryEvidenceProfileRequest


def compute_horary_evidence_profile(
    engine: Moira,
    request: HoraryEvidenceProfileRequest,
) -> HoraryEvidenceProfile:
    """Normalize caller time, construct source receipts, and delegate once."""

    normalized_instant = request.question_instant.astimezone(timezone.utc)
    normalized_jd_ut1 = utc_to_ut1(jd_from_datetime(normalized_instant))
    question = HoraryQuestionReceipt(
        question_id=request.question_id,
        latitude_deg=request.latitude_deg,
        longitude_deg=request.longitude_deg,
        time=HoraryQuestionTimeReceipt(
            state=HoraryEvidenceState.EVALUATED,
            stated_basis=HoraryQuestionTimeBasis(request.stated_basis),
            stated_basis_source=request.stated_basis_source,
            source_calendar=HorarySourceCalendar(request.source_calendar),
            source_instant_label=request.source_instant_label,
            normalized_instant=normalized_instant,
            normalized_jd_ut1=normalized_jd_ut1,
            conversion_policy_id=request.conversion_policy_id,
            reason=None,
        ),
        perspective_path=request.perspective_path,
        terminal_topic_house=request.terminal_topic_house,
    )
    perfection_jd_end = None
    if request.perfection_end is not None:
        perfection_jd_end = utc_to_ut1(
            jd_from_datetime(request.perfection_end.astimezone(timezone.utc))
        )
    return engine.horary_evidence_at(
        question,
        house_policy=HoraryHousePolicy(request.house_system),
        perfection_jd_end=perfection_jd_end,
    )


__all__ = ["compute_horary_evidence_profile"]
