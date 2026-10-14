"""Validation tests for replayable Light Box evidence contracts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

import pytest


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "replay_lightbox_receipts.py"
R1B_RELATIONSHIP_SURFACES = {
    "rest:POST:/v1/aspects/from-longitudes",
    "rest:POST:/v1/aspects/motion-witness",
    "rest:POST:/v1/composite/chart",
    "rest:POST:/v1/composite/transits",
    "rest:POST:/v1/davison/chart",
    "rest:POST:/v1/davison/transits",
    "rest:POST:/v1/synastry/overlay",
    "rest:POST:/v1/synastry/overlays",
}
R1C_RELATIONSHIP_SURFACES = {
    "rest:POST:/v1/midpoints/calculate",
    "rest:POST:/v1/midpoints/pictures",
    "rest:POST:/v1/midpoints/weighting",
    "rest:POST:/v1/patterns/find",
    "rest:POST:/v1/synastry/aspects",
    "rest:POST:/v1/synastry/contacts",
}
R2A_CHART_WHEEL_SURFACES = {
    "rest:POST:/v1/website/chart-wheel/packet",
}
R2B_TIME_SURFACES = {
    f"python:moira.facade:{name}"
    for name in (
        "jd_from_datetime",
        "jd_from_datetime_with_truth",
        "datetime_from_jd",
        "datetime_from_jd_with_truth",
        "delta_t_from_jd",
        "delta_t_from_jd_with_truth",
        "utc_to_ut1",
        "utc_to_ut1_with_truth",
        "utc_to_tt",
        "utc_to_tt_with_truth",
        "local_sidereal_time",
        "local_sidereal_time_with_truth",
    )
}
R2B_FRAME_SURFACES = {
    f"python:moira.facade:{name}"
    for name in (
        "ecliptic_to_equatorial",
        "ecliptic_to_equatorial_with_truth",
        "equatorial_to_horizontal",
        "equatorial_to_horizontal_with_truth",
        "true_obliquity",
        "true_obliquity_with_truth",
    )
}
R2B_KERNEL_SURFACES = {
    f"python:moira.facade:{name}"
    for name in (
        "planet_relative_to",
        "planet_relative_to_with_truth",
        "true_lilith",
        "true_lilith_with_truth",
    )
}
R3B_SOLAR_CONDITION_SURFACES = {
    "rest:POST:/v1/solar-condition/instant",
    "rest:POST:/v1/solar-condition/events",
}
R3C_STATION_SURFACES = {
    "rest:POST:/v1/stations/search",
    "rest:POST:/v1/stations/next",
    "rest:POST:/v1/stations/is-retrograde",
}
R3D_VOID_OF_COURSE_SURFACES = {
    "rest:POST:/v1/void-of-course/window",
    "rest:POST:/v1/void-of-course/next",
    "rest:POST:/v1/void-of-course/is-active",
    "rest:POST:/v1/void-of-course/range",
}
R2A_CORE_REST_SURFACES = {
    "rest:POST:/v1/chart",
    "rest:POST:/v1/houses",
    "rest:POST:/v1/positions/planet",
    "rest:POST:/v1/positions/sky",
}
R2C_SIDEREAL_PYTHON_SURFACES = {
    f"python:moira.facade:{name}"
    for name in (
        "all_nakshatras_at",
        "all_nakshatras_at_with_truth",
        "ayanamsa",
        "ayanamsa_with_truth",
        "nakshatra_of",
        "nakshatra_of_with_truth",
        "sidereal_to_tropical",
        "sidereal_to_tropical_with_truth",
        "tropical_to_sidereal",
        "tropical_to_sidereal_with_truth",
    )
}
R2C_SIDEREAL_REST_SURFACES = {
    "rest:POST:/v1/nakshatra/bulk",
    "rest:POST:/v1/nakshatra/position",
    "rest:POST:/v1/sidereal/ayanamsa",
    "rest:POST:/v1/sidereal/convert",
}
R3A_CHART_SHAPE_SURFACES = {
    "python:moira.facade:classify_chart_shape",
    "python:moira.facade:classify_chart_shape_with_truth",
    "rest:POST:/v1/chart-shape/classify",
}


def _module():
    spec = importlib.util.spec_from_file_location("replay_lightbox_receipts", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_contracts_are_unique_and_cover_every_structural_admission() -> None:
    replay = _module()
    contracts, inventory = replay.load_contracts()
    contract_surfaces = {
        surface_id
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }
    admissions = replay._load(
        REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CONFORMANCE_ADMISSIONS.json"
    )
    admitted = {row["surface_id"] for row in admissions["entries"]}
    assert contract_surfaces == admitted
    assert inventory["surface_fingerprint_sha256"]


def test_passed_count_uses_terminal_pytest_summary() -> None:
    replay = _module()
    assert replay._passed_count(".... 4 passed in 1.00s") == 4
    assert replay._passed_count("1 passed\nthen 7 passed in 2.00s") == 7
    assert replay._passed_count("............... [100%]\npolicy receipt") == 15
    assert replay._passed_count("2 failed") == 0


def test_r2b_foundation_truth_contracts_are_bounded() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_id = {contract["claim_id"]: contract for contract in contracts["contracts"]}

    time = by_id["LB-FOUNDATION-TIME-TRUTH"]
    assert set(time["surface_ids"]) == R2B_TIME_SURFACES
    assert set(time["evidence_classes"]) == {
        "authority",
        "invariant",
        "regression",
        "release",
    }
    assert time["minimum_tests"] == 17
    assert "future Delta-T scenario" in time["exclusions"][0]

    frame = by_id["LB-FOUNDATION-FRAME-SINGULARITY-TRUTH"]
    assert set(frame["surface_ids"]) == R2B_FRAME_SURFACES
    assert set(frame["evidence_classes"]) == {
        "authority",
        "invariant",
        "regression",
        "release",
    }
    assert frame["minimum_tests"] == 14
    assert "refraction" in frame["exclusions"][0]

    kernel = by_id["LB-FOUNDATION-KERNEL-RELATIVE-TRUTH"]
    assert set(kernel["surface_ids"]) == R2B_KERNEL_SURFACES
    assert set(kernel["evidence_classes"]) == {
        "invariant",
        "regression",
        "release",
    }
    assert kernel["minimum_tests"] == 6
    assert "not an independent JPL Horizons residual" in kernel["exclusions"][0]


def test_r1b_relationship_surfaces_have_bounded_replay_contracts() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_surface = {
        surface_id: contract
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }

    assert R1B_RELATIONSHIP_SURFACES <= set(by_surface)
    for surface_id in R1B_RELATIONSHIP_SURFACES:
        contract = by_surface[surface_id]
        assert {"invariant", "regression", "release"} <= set(
            contract["evidence_classes"]
        )
        assert contract["pytest_targets"]
        assert contract["minimum_tests"] >= 1
        assert contract["claim_scope"]
        assert contract["exclusions"]


def test_r1c_relationship_surfaces_have_bounded_replay_contracts() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_surface = {
        surface_id: contract
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }

    assert R1C_RELATIONSHIP_SURFACES <= set(by_surface)
    for surface_id in R1C_RELATIONSHIP_SURFACES:
        contract = by_surface[surface_id]
        assert {"invariant", "regression", "release"} <= set(
            contract["evidence_classes"]
        )
        assert contract["pytest_targets"]
        assert contract["minimum_tests"] >= 1
        assert contract["claim_scope"]
        assert contract["exclusions"]


def test_r2a_chart_wheel_surface_has_a_bounded_replay_contract() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_surface = {
        surface_id: contract
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }

    assert R2A_CHART_WHEEL_SURFACES <= set(by_surface)
    for surface_id in R2A_CHART_WHEEL_SURFACES:
        contract = by_surface[surface_id]
        assert {"invariant", "regression", "release"} <= set(
            contract["evidence_classes"]
        )
        assert len(contract["pytest_targets"]) == 7
        assert contract["minimum_tests"] == 7
        assert contract["claim_scope"]
        assert contract["exclusions"]


def test_r3b_solar_condition_surfaces_have_a_bounded_replay_contract() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_surface = {
        surface_id: contract
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }

    assert R3B_SOLAR_CONDITION_SURFACES <= set(by_surface)
    for surface_id in R3B_SOLAR_CONDITION_SURFACES:
        contract = by_surface[surface_id]
        assert set(contract["evidence_classes"]) == {
            "doctrine_source",
            "invariant",
            "regression",
            "release",
        }
        assert len(contract["pytest_targets"]) == 5
        assert contract["minimum_tests"] == 5
        assert "8.5 degrees" in contract["claim_scope"]
        assert (
            "not an independent astronomical authority residual"
            in contract["exclusions"][0]
        )


def test_r3c_station_surfaces_have_a_bounded_replay_contract() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_surface = {
        surface_id: contract
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }

    assert R3C_STATION_SURFACES <= set(by_surface)
    for surface_id in R3C_STATION_SURFACES:
        contract = by_surface[surface_id]
        assert set(contract["evidence_classes"]) == {
            "invariant",
            "regression",
            "release",
        }
        assert len(contract["pytest_targets"]) == 3
        assert contract["minimum_tests"] == 12
        assert "null next-station bodies remain null" in contract["claim_scope"]
        assert "/v1/stations/retrograde-periods route is not admitted" in (
            contract["exclusions"][0]
        )


def test_r3d_void_of_course_surfaces_have_a_bounded_replay_contract() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_surface = {
        surface_id: contract
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }

    assert R3D_VOID_OF_COURSE_SURFACES <= set(by_surface)
    for surface_id in R3D_VOID_OF_COURSE_SURFACES:
        contract = by_surface[surface_id]
        assert set(contract["evidence_classes"]) == {
            "invariant",
            "regression",
            "release",
        }
        assert len(contract["pytest_targets"]) == 3
        assert contract["minimum_tests"] == 13
        assert "controlled geometry" in contract["claim_scope"]
        assert "not an independent void-of-course almanac residual" in (
            contract["exclusions"][0]
        )


def test_r2a_core_rest_and_r2c_sidereal_and_r3a_chart_shape_contracts_are_bounded() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_id = {contract["claim_id"]: contract for contract in contracts["contracts"]}

    core_rest = by_id["LB-CORE-POSITIONS-HOUSES-CHART-TRUTH"]
    assert set(core_rest["surface_ids"]) == R2A_CORE_REST_SURFACES
    assert set(core_rest["evidence_classes"]) == {
        "invariant",
        "regression",
        "release",
    }
    assert core_rest["minimum_tests"] == 8
    assert "paired /reduction routes" in core_rest["claim_scope"]

    sidereal_py = by_id["LB-SIDEREAL-PYTHON-TRUTH"]
    assert set(sidereal_py["surface_ids"]) == R2C_SIDEREAL_PYTHON_SURFACES
    assert set(sidereal_py["evidence_classes"]) == {
        "invariant",
        "regression",
        "release",
    }
    assert sidereal_py["minimum_tests"] == 11
    assert "single-evaluation bulk ayanamsa reuse" in sidereal_py["claim_scope"]

    sidereal_rest = by_id["LB-SIDEREAL-REST-TRUTH"]
    assert set(sidereal_rest["surface_ids"]) == R2C_SIDEREAL_REST_SURFACES
    assert set(sidereal_rest["evidence_classes"]) == {
        "invariant",
        "regression",
        "release",
    }
    assert sidereal_rest["minimum_tests"] == 7
    assert "shared-ayanamsa bulk Nakshatra placement" in sidereal_rest["claim_scope"]

    chart_shape = by_id["LB-CHART-SHAPE-TRUTH"]
    assert set(chart_shape["surface_ids"]) == R3A_CHART_SHAPE_SURFACES
    assert set(chart_shape["evidence_classes"]) == {
        "doctrine_source",
        "invariant",
        "regression",
        "release",
    }
    assert chart_shape["minimum_tests"] == 16
    assert "ten-planet canonical body set" in chart_shape["claim_scope"]


def test_r4_phenomena_horizon_visibility_and_locational_contracts_are_bounded() -> None:
    replay = _module()
    contracts, _ = replay.load_contracts()
    by_id = {contract["claim_id"]: contract for contract in contracts["contracts"]}

    expected_claims = {
        "LB-PLANETARY-HOURS-TRUTH": (4, 5),
        "LB-PHENOMENA-CONJUNCTION-RESONANCE-TRUTH": (6, 5),
        "LB-VISIBILITY-ASSESSMENT-TRUTH": (1, 4),
        "LB-ASTROCARTOGRAPHY-REST-TRUTH": (6, 6),
        "LB-LOCATIONAL-PROJECTION-REST-TRUTH": (4, 5),
        "LB-PARAN-SEARCH-PACKET-REST-TRUTH": (2, 4),
        "LB-ECLIPSE-HELIACAL-TWILIGHT-REST-TRUTH": (6, 8),
    }
    for claim_id, (surface_count, min_tests) in expected_claims.items():
        contract = by_id[claim_id]
        assert len(contract["surface_ids"]) == surface_count
        assert {"invariant", "regression", "release"} <= set(
            contract["evidence_classes"]
        )
        assert contract["minimum_tests"] == min_tests
        assert contract["claim_scope"]
        assert contract["exclusions"]



def test_contract_hash_is_order_stable() -> None:
    replay = _module()
    assert replay._sha({"b": 2, "a": 1}) == replay._sha({"a": 1, "b": 2})


def _stub_build(
    replay: Any,
    monkeypatch: pytest.MonkeyPatch,
    snapshots: list[tuple[str, bool]],
) -> None:
    contract = {
        "claim_id": "LB-TEST",
        "surface_ids": ["python:moira.facade:test"],
        "evidence_classes": ["release"],
        "claim_scope": "test",
        "exclusions": ["none"],
        "pytest_targets": ["tests/unit/test_lightbox_evidence_contracts.py"],
        "minimum_tests": 1,
    }
    contracts = {"contracts": [contract]}
    inventory = {
        "engine_version": "test",
        "surface_fingerprint_sha256": "fingerprint",
    }
    snapshots_iter = iter(snapshots)
    monkeypatch.setattr(replay, "load_contracts", lambda: (contracts, inventory))
    monkeypatch.setattr(replay, "_source_snapshot", lambda: next(snapshots_iter))

    def fake_replay_contract(
        raw_contract: dict[str, Any],
        *,
        inventory: dict[str, Any],
        source_revision: str,
        working_tree_clean: bool,
    ) -> dict[str, Any]:
        return {
            "receipt_id": "old-id",
            "claim_id": raw_contract["claim_id"],
            "source_revision": source_revision,
            "working_tree_clean": working_tree_clean,
            "artifact_status": (
                "exact_source_revision"
                if working_tree_clean
                else "local_unreleased_worktree"
            ),
            "status": "passed",
            "passed_tests": 1,
        }

    monkeypatch.setattr(replay, "replay_contract", fake_replay_contract)


def test_exact_replay_requires_a_stable_clean_source_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay = _module()
    source = "1" * 40
    _stub_build(replay, monkeypatch, [(source, True), (source, True)])
    receipt_set = replay.build_receipt_set(require_exact_source=True)
    assert receipt_set["source_revision"] == source
    assert receipt_set["working_tree_clean"] is True
    assert receipt_set["artifact_status"] == "exact_source_revision"
    assert receipt_set["receipts"][0]["working_tree_clean"] is True
    assert receipt_set["receipts"][0]["artifact_status"] == "exact_source_revision"
    assert receipt_set["receipts"][0]["receipt_id"] != "old-id"


def test_exact_replay_refuses_a_dirty_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay = _module()
    _stub_build(replay, monkeypatch, [("1" * 40, False)])
    with pytest.raises(
        replay.ReceiptReplayError, match="clean worktree before execution"
    ):
        replay.build_receipt_set(require_exact_source=True)


@pytest.mark.parametrize(
    "final_snapshot",
    [("2" * 40, True), ("1" * 40, False)],
)
def test_exact_replay_refuses_revision_or_worktree_drift(
    monkeypatch: pytest.MonkeyPatch,
    final_snapshot: tuple[str, bool],
) -> None:
    replay = _module()
    _stub_build(replay, monkeypatch, [("1" * 40, True), final_snapshot])
    with pytest.raises(replay.ReceiptReplayError, match="lost its source boundary"):
        replay.build_receipt_set(require_exact_source=True)


def test_local_replay_downgrades_when_source_changes_during_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay = _module()
    source = "1" * 40
    _stub_build(replay, monkeypatch, [(source, True), ("2" * 40, True)])
    receipt_set = replay.build_receipt_set()
    assert receipt_set["source_revision"] == source
    assert receipt_set["working_tree_clean"] is False
    assert receipt_set["artifact_status"] == "local_unreleased_worktree"
    assert receipt_set["receipts"][0]["working_tree_clean"] is False
    assert receipt_set["receipts"][0]["artifact_status"] == (
        "local_unreleased_worktree"
    )
