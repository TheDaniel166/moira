"""DE441 parity evidence for optimized Western profile scanning."""

from __future__ import annotations

import pytest

from moira.constants import HouseSystem
from moira.western_electional import (
    WesternElectionalProfileId,
    WesternElectionalProfileScanPolicy,
    WesternElectionalQualificationStatus,
)


pytestmark = pytest.mark.requires_ephemeris


_ALL_STATUSES = tuple(WesternElectionalQualificationStatus)


def _rule_ids(evaluation, state: str) -> tuple[str, ...]:
    return tuple(
        rule.rule_id for rule in evaluation.rules if rule.state.value == state
    )


@pytest.mark.parametrize(
    ("profile_id", "single_method"),
    [
        (WesternElectionalProfileId.RAMESEY_MOON_CONDITION_V1, "ramesey_moon_condition_at"),
        (WesternElectionalProfileId.SAHL_MOON_CONDITION_V1, "sahl_moon_condition_at"),
    ],
)
def test_range_voc_scan_matches_independent_single_moment_evaluations(
    moira_engine,
    profile_id,
    single_method,
) -> None:
    start = 2451545.0
    policy = WesternElectionalProfileScanPolicy(
        qualifying_statuses=_ALL_STATUSES,
        step_days=1.0 / 24.0,
        max_scan_points=4,
    )
    result = moira_engine.western_electional_profile_windows(
        start,
        start + 3.0 / 24.0,
        51.5074,
        -0.1278,
        house_system=HouseSystem.REGIOMONTANUS,
        profile_id=profile_id,
        scan_policy=policy,
    )

    method = getattr(moira_engine, single_method)
    assert len(result.samples) == 4
    for sample in result.samples:
        expected = method(
            sample.jd_ut,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
        )
        assert sample.status.value == expected.status.value
        assert sample.triggered_rule_ids == _rule_ids(expected, "triggered")
        assert sample.not_evaluable_rule_ids == _rule_ids(
            expected, "not_evaluable"
        )
        assert sample.qualifies is True


def test_dorotheus_scan_sample_evidence_matches_single_moment(moira_engine) -> None:
    start = 2451545.0
    result = moira_engine.western_electional_profile_windows(
        start,
        start + 1.0 / 24.0,
        51.5074,
        -0.1278,
        house_system=HouseSystem.REGIOMONTANUS,
        profile_id=WesternElectionalProfileId.DOROTHEUS_MOON_CONDITION_V1,
        scan_policy=WesternElectionalProfileScanPolicy(
            qualifying_statuses=_ALL_STATUSES,
            step_days=1.0 / 24.0,
            max_scan_points=2,
        ),
    )
    for sample in result.samples:
        expected = moira_engine.dorotheus_moon_condition_at(
            sample.jd_ut,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
        )
        assert sample.status.value == expected.status.value
        assert sample.triggered_rule_ids == _rule_ids(expected, "triggered")
        assert sample.not_evaluable_rule_ids == _rule_ids(
            expected, "not_evaluable"
        )
