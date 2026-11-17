"""Recomputed native 92-case snapshot survey, not a topology proof."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.eclipse import _solve_solar_umbral_contacts
from moira.solar_eclipse_clipped import inspect_instantaneous_clipped_central_boundary


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "moira_solar_one_limit_92_baseline.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: str(case["lunation_number"]))
def test_fresh_contacts_and_twelve_candidate_snapshots(eclipse_calculator, case):
    calc = eclipse_calculator
    event = calc.next_solar_eclipse(case["native_jd_ut1"] - 1.0)
    assert event.data.saros_lunation_number == case["lunation_number"]
    contacts = _solve_solar_umbral_contacts(calc, event.jd_ut)
    start, end = contacts.u1.epoch.jd_ut1, contacts.u4.epoch.jd_ut1
    assert start < end
    fractions = (.001, .01, .05, .10, .25, .50, .75, .90, .95, .99, .999)
    for epoch in [*(start + f * (end - start) for f in fractions), event.jd_ut]:
        result = inspect_instantaneous_clipped_central_boundary(calc, epoch, arc_samples=17)
        assert result.status == "candidate" and result.complete is False
        boundary = result.boundary
        assert boundary.topology == "NUMERICALLY_RESOLVED_BOUNDED_TWO_CROSSINGS"
        assert boundary.cone_arc[0] is boundary.horizon_arc[-1]
        assert boundary.cone_arc[-1] is boundary.horizon_arc[0]

    for epoch in (start + 1/86400, end - 1/86400):
        result = inspect_instantaneous_clipped_central_boundary(calc, epoch, arc_samples=17)
        assert result.status == "candidate" and result.complete is False
    for epoch in (start - 1/86400, start, end, end + 1/86400):
        result = inspect_instantaneous_clipped_central_boundary(calc, epoch, arc_samples=17)
        assert result.status == "unresolved" and result.complete is False
        assert result.boundary is None and result.reason
