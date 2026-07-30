from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_SCRIPT = (
    REPO_ROOT / "scripts" / "diagnose_visibility_spectral_reference.py"
)
DIAGNOSTIC_SPEC = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_spectral_reference_training_diagnostic_spec.json"
)
RADIANCE_SPEC = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_radiance_response_probe_spec.json"
)
CHECKPOINT = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_spectral_reference_training_diagnostic_checkpoint_2026-07-30.json"
)


def test_diagnostic_inventory_is_training_only_and_frozen() -> None:
    diagnostic = json.loads(DIAGNOSTIC_SPEC.read_text(encoding="utf-8"))
    radiance = json.loads(RADIANCE_SPEC.read_text(encoding="utf-8"))
    point = diagnostic["training_point"]
    coordinates = (
        point["solar_center_altitude_deg"],
        point["target_true_altitude_deg"],
        point["relative_solar_azimuth_deg"],
    )
    grid = radiance["radiance_grid"]
    assert coordinates[0] in grid["solar_center_altitude_deg"][
        "training_nodes"
    ]
    assert coordinates[1] in grid["target_true_altitude_deg"][
        "training_nodes"
    ]
    assert coordinates[2] in grid["relative_solar_azimuth_deg"][
        "training_nodes"
    ]
    assert list(coordinates) not in grid["response_holdouts"]
    assert diagnostic["candidate_reference_wavelengths_nm"] == [
        507.0,
        519.0,
        531.0,
        543.0,
        550.0,
        555.0,
    ]
    assert diagnostic["monte_carlo"]["fixed_seed_count"] == 8
    assert (
        diagnostic["monte_carlo"]["random_seeds"]
        == radiance["adaptive_monte_carlo"][
            "spectral_shape_training_random_seeds"
        ]
    )


def test_diagnostic_inspection_reports_no_holdout_execution() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(DIAGNOSTIC_SCRIPT),
            "--inspect-spec",
            "--radiance-spec",
            str(RADIANCE_SPEC),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert payload["run_count"] == 48
    assert payload["response_holdouts_executed"] is False
    assert payload["direct_extinction_holdouts_executed"] is False


def test_checkpoint_selection_recomputes_from_frozen_scores() -> None:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    eligible = [
        row
        for row in checkpoint["candidate_results"]
        if row["passes_frozen_training_threshold"]
    ]
    selected = min(
        eligible,
        key=lambda row: (
            row["primary_score"],
            (
                row["photopic_relative_standard_error"]
                + row["scotopic_relative_standard_error"]
            ),
            row["candidate_reference_wavelength_nm"],
        ),
    )
    assert selected["candidate_reference_wavelength_nm"] == 531.0
    assert checkpoint["selection"]["threshold_relaxed"] is False
    assert checkpoint["holdout_boundary"]["response_holdouts_executed"] is False


def test_diagnostic_has_no_network_imports() -> None:
    tree = ast.parse(DIAGNOSTIC_SCRIPT.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {"httpx", "requests", "socket", "urllib", "urllib3"}
    )
