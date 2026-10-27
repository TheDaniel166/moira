"""Candidate generation cannot silently widen protected scientific policy."""

from copy import deepcopy
import sys

import pytest

from tests.tools import generate_iota_spica_candidate as candidate_tool


@pytest.mark.parametrize("field", ("solver", "topology", "asset", "total_gate"))
def test_candidate_rejects_changed_scientific_contract(field):
    original = candidate_tool.checks._load(candidate_tool.checks._MODEL_FIXTURE)
    candidate = deepcopy(original)
    if field == "solver":
        candidate["contact_search_policy"]["time_tolerance_seconds"] *= 2.0
    elif field == "topology":
        candidate["sites"][0]["topology_characterization"]["required_model_contact_count"] -= 1
    elif field == "asset":
        candidate["lola_stac_cells"][0]["asset"]["sha256"] = "0" * 64
    else:
        candidate["sites"][0]["regression_envelope"]["maximum_absolute_observed_residual_s"] = 1.0
    with pytest.raises(ValueError, match="changed an observation, resource identity, topology rule, or gate"):
        candidate_tool.assert_unchanged_contracts(original, candidate)


def test_reporting_reallocation_keeps_total_gate_and_fails_closed_beyond_budget():
    original = candidate_tool.checks._load(candidate_tool.checks._MODEL_FIXTURE)
    candidate = deepcopy(original)
    site = candidate["sites"][1]
    site["contact_regression"]["matched_maximum_absolute_residual_s"] = 0.350792706
    candidate_tool.refresh_reporting_characterizations(site)
    budget = site["regression_envelope"]["budget_components_s"]
    assert budget["frozen_baseline_characterization"] == 0.351
    assert budget["reserved_reporting_and_model_drift_margin"] == 0.1089
    assert sum(budget.values()) == pytest.approx(0.5, abs=1e-12)
    candidate_tool.assert_unchanged_contracts(original, candidate)
    site["contact_regression"]["matched_maximum_absolute_residual_s"] = 0.6
    candidate_tool.refresh_reporting_characterizations(site)
    assert budget["reserved_reporting_and_model_drift_margin"] < 0.0
    assert site["regression_envelope"]["maximum_absolute_observed_residual_s"] == 0.5


def test_candidate_cli_refuses_existing_output_before_loading_resources(monkeypatch, tmp_path):
    witness = tmp_path / "existing-evidence.txt"
    witness.write_bytes(b"preserve existing evidence")
    monkeypatch.setattr(sys, "argv", ["generate-candidate", "--output", str(tmp_path)])

    def unexpected_load(*args):
        pytest.fail("existing-output refusal must precede resource loading")

    monkeypatch.setattr(candidate_tool.checks, "_load", unexpected_load)
    with pytest.raises(SystemExit) as error:
        candidate_tool.main()
    assert error.value.code == 2
    assert witness.read_bytes() == b"preserve existing evidence"
    assert list(tmp_path.iterdir()) == [witness]
