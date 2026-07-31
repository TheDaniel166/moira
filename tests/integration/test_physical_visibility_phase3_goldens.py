"""Live engine replay for the external Phase 3 event goldens."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from moira._visibility_lut import VisibilityDataPackConfig
from moira.heliacal import (
    PhysicalBackgroundScope,
    PhysicalDirectionalBackground,
    PhysicalVisibilityPhase,
    PhysicalVisibilityPolicy,
    PhysicalVisibilitySearchPolicy,
    PhysicalVisibilityStatus,
    physical_visibility_event,
)


pytestmark = [
    pytest.mark.requires_ephemeris,
    pytest.mark.slow,
]

_GOLDEN_PATH = (
    Path(__file__).resolve().parents[1]
    / "golden"
    / "physical_visibility_phase3_events.json"
)
_GOLDEN = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
_MANIFEST_SHA256 = _GOLDEN["exact_data_pack"]["manifest_sha256"]
_CERTIFICATE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)


def _configured_pack() -> VisibilityDataPackConfig:
    raw = os.environ.get("MOIRA_PHASE3_VISIBILITY_PACK")
    if not raw:
        pytest.skip(
            "set MOIRA_PHASE3_VISIBILITY_PACK to the exact external "
            "Phase 3 data-pack directory"
        )
    path = Path(raw)
    if not path.is_dir():
        pytest.fail(
            "MOIRA_PHASE3_VISIBILITY_PACK is not an existing directory"
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
            component_ids=("phase3_reference_dark_sky",),
            source_id="phase3_reference_dark_sky_v1",
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
def test_physical_event_replays_the_independent_golden(
    case: dict[str, object],
) -> None:
    expected = case["engine_result"]
    assert isinstance(expected, dict)
    result = physical_visibility_event(
        str(case["target"]),
        PhysicalVisibilityPhase(str(case["phase"])),
        float(case["jd_start"]),
        float(case["latitude_deg"]),
        float(case["longitude_deg"]),
        data_pack_config=_configured_pack(),
        policy=_policy(),
        search_policy=PhysicalVisibilitySearchPolicy(
            search_window_days=int(case["search_window_days"])
        ),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.reason is None
    assert result.event_jd_ut == pytest.approx(
        expected["event_jd_ut"],
        abs=0.5 / 86400.0,
    )
    assert result.observation_day_key == expected["observation_day_key"]
    assert (
        result.comparison_observation_day_key
        == expected["comparison_observation_day_key"]
    )
    assert (
        result.comparison_day_status
        == expected["comparison_day_status"]
    )
    assert result.event_time_semantics is not None
    assert (
        result.event_time_semantics.value
        == expected["event_time_semantics"]
    )
    assert result.boundary_source is not None
    assert result.boundary_source.value == expected["boundary_source"]
    assert (
        result.solver_receipt.crossing_completeness_state
        == expected["crossing_completeness_state"]
    )
    assert (
        result.solver_receipt.crossing_certificate_source_sha256
        == _CERTIFICATE_SHA256
    )
    assert result.solver_receipt.unresolved_certificate_interval_count == 0
