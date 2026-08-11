"""Live engine replay for the Phase 7 broad physical-event oracle."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from moira._visibility_lut import VisibilityDataPackConfig
from moira.heliacal import (
    PhysicalBackgroundScope,
    PhysicalDirectionalBackground,
    PhysicalVisibilityEvidenceState,
    PhysicalVisibilityPhase,
    PhysicalVisibilityPolicy,
    PhysicalVisibilitySearchPolicy,
    PhysicalVisibilityStatus,
    physical_visibility_event,
)
from moira.julian import jd_from_datetime


pytestmark = [
    pytest.mark.requires_ephemeris,
    pytest.mark.slow,
    pytest.mark.parallel,
]

_GOLDEN_PATH = (
    Path(__file__).resolve().parents[1]
    / "golden"
    / "physical_visibility_phase7_broad_oracle.json"
)
_GOLDEN = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
_MANIFEST_SHA256 = _GOLDEN["exact_data_pack"]["manifest_sha256"]
_ENGINE_CONTRACT = _GOLDEN["required_engine_contract"]


def _configured_pack() -> VisibilityDataPackConfig:
    raw = os.environ.get("MOIRA_PHASE7_VISIBILITY_PACK") or os.environ.get(
        "MOIRA_PHASE3_VISIBILITY_PACK"
    )
    if not raw:
        pytest.skip(
            "set MOIRA_PHASE7_VISIBILITY_PACK to the exact external "
            "Phase 7 data-pack directory"
        )
    path = Path(raw)
    if not path.is_dir():
        pytest.fail(
            "MOIRA_PHASE7_VISIBILITY_PACK is not an existing directory"
        )
    return VisibilityDataPackConfig(
        path,
        expected_manifest_sha256=_MANIFEST_SHA256,
    )


def _policy() -> PhysicalVisibilityPolicy:
    background = _GOLDEN["policy"]["background"]
    return PhysicalVisibilityPolicy(
        background=PhysicalDirectionalBackground(
            photopic_luminance_cd_m2=background[
                "photopic_luminance_cd_m2"
            ],
            scotopic_luminance_cd_m2=background[
                "scotopic_luminance_cd_m2"
            ],
            scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR,
            component_ids=("phase7_broad_oracle_dark_sky",),
            source_id="phase7_broad_oracle_dark_sky_v1",
            source_receipt_sha256="a" * 64,
            method_id="source_locked_reference_anchor_v1",
        ),
        expected_manifest_sha256=_MANIFEST_SHA256,
    )


@pytest.mark.parametrize(
    "case",
    _GOLDEN["cases"],
    ids=lambda case: case["case_id"],
)
def test_physical_event_replays_the_broad_oracle_matrix(
    case: dict[str, object],
) -> None:
    search = _GOLDEN["policy"]["public_search_policy"]
    result = physical_visibility_event(
        str(case["target"]),
        PhysicalVisibilityPhase(str(case["phase"])),
        jd_from_datetime(
            datetime.fromisoformat(
                str(case["search_start_utc"]).replace("Z", "+00:00")
            )
        ),
        float(case["latitude_deg"]),
        float(case["longitude_deg"]),
        data_pack_config=_configured_pack(),
        policy=_policy(),
        search_policy=PhysicalVisibilitySearchPolicy(
            search_window_days=int(case["search_window_days"]),
            scan_step_days=float(search["scan_step_minutes"]) / 1440.0,
            adaptive_minimum_step_days=(
                float(search["adaptive_minimum_step_minutes"]) / 1440.0
            ),
            root_time_tolerance_days=(
                float(search["root_time_tolerance_seconds"]) / 86400.0
            ),
        ),
    )
    captured = case["captured_engine_result"]
    assert isinstance(captured, dict)

    if case["independent_event_time_claimed"]:
        oracle = case["independent_oracle"]
        assert isinstance(oracle, dict)
        assert result.status is PhysicalVisibilityStatus.EVALUATED
        assert result.reason is None
        assert result.event_jd_ut == pytest.approx(
            oracle["event_jd_ut"],
            abs=float(case["maximum_engine_oracle_difference_seconds"])
            / 86400.0,
        )
        assert result.event_jd_ut == pytest.approx(
            captured["event_jd_ut"],
            abs=0.5 / 86400.0,
        )
        assert result.observation_day_key == captured["observation_day_key"]
        assert result.comparison_observation_day_key == (
            captured["comparison_observation_day_key"]
        )
        assert result.comparison_day_status == (
            captured["comparison_day_status"]
        )
        assert result.event_time_semantics is not None
        assert result.event_time_semantics.value == (
            _ENGINE_CONTRACT["event_time_semantics"]
        )
        assert result.boundary_source is not None
        assert result.boundary_source.value == (
            _ENGINE_CONTRACT["boundary_source"]
        )
        assert result.crossing_direction is not None
        assert result.crossing_direction.value == (
            "not_visible_to_visible"
            if str(case["phase"]).endswith("_rising")
            else "visible_to_not_visible"
        )
        assert result.solver_receipt.crossing_completeness_state == (
            _ENGINE_CONTRACT["crossing_completeness_state"]
        )
        assert result.solver_receipt.crossing_certificate_source_sha256 == (
            _ENGINE_CONTRACT["crossing_certificate_source_sha256"]
        )
        assert result.solver_receipt.unresolved_certificate_interval_count == (
            _ENGINE_CONTRACT["unresolved_certificate_interval_count"]
        )
        return

    expected_status = PhysicalVisibilityStatus(str(captured["status"]))
    assert result.status is expected_status
    assert result.reason == captured["reason"]
    assert result.event_jd_ut is None
    assert result.event_time_semantics is None
    assert result.boundary_source is None
    assert result.comparison_day_status is None
    if result.status is PhysicalVisibilityStatus.NOT_FOUND:
        assert result.evidence_state is (
            PhysicalVisibilityEvidenceState.EVALUATED_NO_EVENT
        )
    else:
        assert result.evidence_state is PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
