#!/usr/bin/env python3
"""Compare ALIS reference wavelengths at one governing training geometry.

This offline research diagnostic is deliberately separate from the admitted
radiance builder.  It may inspect only the predeclared training point and
fixed training seeds; it never executes a response or direct holdout.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from build_visibility_radiance_response_probe import (
    DATA_LINK_NAME,
    REPO_ROOT,
    VisibilityRadianceResponseError,
    _kept_run_files,
    _parse_radiance_file,
    _point_id,
    _shape_run,
    _trapezoid_response,
    _verify_source_inputs,
    canonical_json_bytes,
    file_receipt,
    load_spec,
    radiance_points,
    render_input,
    sha256_bytes,
    sha256_file,
)


DEFAULT_DIAGNOSTIC_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_spectral_reference_training_diagnostic_spec.json"
)
DEFAULT_RADIANCE_SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_radiance_response_probe_spec.json"
)
DIAGNOSTIC_SPEC_SCHEMA = (
    "moira.visibility-spectral-reference-training-diagnostic-spec/v1"
)
ARTIFACT_SCHEMA = (
    "moira.visibility-spectral-reference-training-diagnostic/v1"
)
RUN_SCHEMA = (
    "moira.visibility-spectral-reference-training-diagnostic-run/v1"
)
MANIFEST_NAME = "artifact-manifest.json"
SUMMARY_NAME = "summary.json"


class SpectralReferenceDiagnosticError(ValueError):
    """Raised when the training-only diagnostic contract is violated."""


class DiagnosticBudgetReached(RuntimeError):
    """Raised after the caller-supplied new-run budget is exhausted."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpectralReferenceDiagnosticError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SpectralReferenceDiagnosticError(f"{label} must be an array")
    return value


def _verify_file_receipt(declaration: dict[str, Any]) -> Path:
    relative = declaration.get("path")
    if (
        not isinstance(relative, str)
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic file receipt path is unsafe"
        )
    path = REPO_ROOT / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != declaration.get("bytes")
        or sha256_file(path) != declaration.get("sha256")
    ):
        raise SpectralReferenceDiagnosticError(
            f"diagnostic file receipt differs: {relative}"
        )
    return path


def load_diagnostic_spec(
    path: Path = DEFAULT_DIAGNOSTIC_SPEC_PATH,
    *,
    radiance_spec_path: Path = DEFAULT_RADIANCE_SPEC_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        diagnostic = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpectralReferenceDiagnosticError(
            f"invalid diagnostic specification: {path}"
        ) from exc
    diagnostic = _require_dict(diagnostic, "diagnostic specification")
    if (
        diagnostic.get("schema") != DIAGNOSTIC_SPEC_SCHEMA
        or diagnostic.get("status")
        != "training_only_research_diagnostic_not_runtime_data_pack"
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic specification identity differs"
        )
    radiance_declaration = _require_dict(
        diagnostic.get("radiance_spec"),
        "radiance spec receipt",
    )
    declared_radiance_path = _verify_file_receipt(radiance_declaration)
    if declared_radiance_path.resolve() != radiance_spec_path.resolve():
        raise SpectralReferenceDiagnosticError(
            "caller-supplied radiance specification differs"
        )
    _verify_file_receipt(
        _require_dict(
            diagnostic.get("governing_failed_checkpoint"),
            "failed checkpoint receipt",
        )
    )
    radiance = load_spec(radiance_spec_path)
    if radiance.get("spec_id") != radiance_declaration.get("spec_id"):
        raise SpectralReferenceDiagnosticError(
            "radiance specification ID differs"
        )
    training, holdouts, response_holdouts = radiance_points(radiance)
    point_declaration = _require_dict(
        diagnostic.get("training_point"),
        "training point",
    )
    point = (
        float(point_declaration.get("solar_center_altitude_deg")),
        float(point_declaration.get("target_true_altitude_deg")),
        float(point_declaration.get("relative_solar_azimuth_deg")),
    )
    if (
        _point_id(point) != point_declaration.get("point_id")
        or point not in training
        or point in holdouts
        or point in response_holdouts
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic point is not an exclusive training point"
        )
    candidates = [
        float(value)
        for value in _require_list(
            diagnostic.get("candidate_reference_wavelengths_nm"),
            "candidate reference wavelengths",
        )
    ]
    if (
        candidates != [507.0, 519.0, 531.0, 543.0, 550.0, 555.0]
        or candidates != sorted(set(candidates))
    ):
        raise SpectralReferenceDiagnosticError(
            "candidate reference inventory differs"
        )
    monte_carlo = _require_dict(
        diagnostic.get("monte_carlo"),
        "diagnostic Monte Carlo",
    )
    seeds = _require_list(monte_carlo.get("random_seeds"), "random seeds")
    if (
        int(monte_carlo.get("photons_per_seed", 0)) != 100000
        or seeds
        != radiance["adaptive_monte_carlo"][
            "spectral_shape_training_random_seeds"
        ]
        or monte_carlo.get("fixed_seed_count") != len(seeds)
        or monte_carlo.get("adaptive_stopping_allowed") is not False
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic Monte Carlo contract differs"
        )
    selection = _require_dict(
        diagnostic.get("selection"),
        "selection contract",
    )
    if (
        selection.get("maximum_response_shape_relative_standard_error")
        != radiance["adaptive_monte_carlo"][
            "maximum_response_shape_relative_standard_error"
        ]
        or selection.get("thresholds_may_not_change") is not True
        or selection.get("candidate_inventory_may_not_change_after_execution")
        is not True
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic selection contract differs"
        )
    holdout = _require_dict(
        diagnostic.get("holdout_boundary"),
        "holdout boundary",
    )
    if (
        holdout.get("training_point_only") is not True
        or holdout.get("response_holdouts_must_not_execute") is not True
        or holdout.get("direct_extinction_holdouts_must_not_execute")
        is not True
        or holdout.get("grid_nodes_may_not_change") is not True
        or holdout.get("acceptance_thresholds_may_not_change") is not True
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic holdout boundary differs"
        )
    runtime = _require_dict(
        diagnostic.get("runtime_boundary"),
        "runtime boundary",
    )
    if (
        runtime.get("network_allowed") is not False
        or runtime.get("automatic_download_allowed") is not False
        or runtime.get("engine_dependency_allowed") is not False
        or runtime.get("engine_runtime_invocation_allowed") is not False
        or runtime.get("engine_changes_authorized") is not False
    ):
        raise SpectralReferenceDiagnosticError(
            "diagnostic runtime boundary differs"
        )
    return diagnostic, radiance


def inspect_spec(
    path: Path = DEFAULT_DIAGNOSTIC_SPEC_PATH,
    *,
    radiance_spec_path: Path = DEFAULT_RADIANCE_SPEC_PATH,
) -> dict[str, Any]:
    diagnostic, _ = load_diagnostic_spec(
        path,
        radiance_spec_path=radiance_spec_path,
    )
    monte_carlo = diagnostic["monte_carlo"]
    candidates = diagnostic["candidate_reference_wavelengths_nm"]
    return {
        "diagnostic_id": diagnostic["diagnostic_id"],
        "training_point": diagnostic["training_point"],
        "candidate_reference_wavelengths_nm": candidates,
        "seed_count_per_candidate": monte_carlo["fixed_seed_count"],
        "run_count": len(candidates) * monte_carlo["fixed_seed_count"],
        "response_holdouts_executed": False,
        "direct_extinction_holdouts_executed": False,
        "runtime_boundary": diagnostic["runtime_boundary"],
    }


def _candidate_run(
    diagnostic: dict[str, Any],
    radiance: dict[str, Any],
    *,
    candidate_wavelength_nm: float,
    seed_index: int,
    seed: int,
) -> tuple[dict[str, Any], str]:
    point_declaration = diagnostic["training_point"]
    point = (
        float(point_declaration["solar_center_altitude_deg"]),
        float(point_declaration["target_true_altitude_deg"]),
        float(point_declaration["relative_solar_azimuth_deg"]),
    )
    run = _shape_run(
        point,
        partition="training",
        seed_index=seed_index,
        seed=seed,
        spec=radiance,
    )
    run["run_id"] = (
        f"training__{point_declaration['point_id']}"
        f"__ref{int(candidate_wavelength_nm):04d}"
        f"__r{seed_index + 1:02d}"
    )
    run["candidate_reference_wavelength_nm"] = candidate_wavelength_nm
    candidate_spec = copy.deepcopy(radiance)
    candidate_spec["radiance_solver"][
        "spectral_importance_reference_wavelength_nm"
    ] = candidate_wavelength_nm
    return run, render_input(run, candidate_spec)


def _candidate_index(
    wavelengths: list[float],
    candidate_wavelength_nm: float,
) -> int:
    index = round((candidate_wavelength_nm - 380.0) / 0.05)
    if (
        index < 0
        or index >= len(wavelengths)
        or not math.isclose(
            wavelengths[index],
            candidate_wavelength_nm,
            abs_tol=1e-6,
        )
    ):
        raise SpectralReferenceDiagnosticError(
            "candidate wavelength is not on the spectral output grid"
        )
    return index


def _parse_candidate_result(
    directory: Path,
    *,
    candidate_wavelength_nm: float,
    cie_tables: dict[str, dict[int, float]],
) -> dict[str, Any]:
    wavelengths, radiances = _parse_radiance_file(
        directory / "mc.rad.spc",
        expected_rows=8001,
    )
    index = _candidate_index(wavelengths, candidate_wavelength_nm)
    normalizer = radiances[index]
    if not math.isfinite(normalizer) or normalizer <= 0:
        raise SpectralReferenceDiagnosticError(
            "candidate-reference normalization sample is zero or invalid"
        )
    result: dict[str, Any] = {
        "candidate_reference_radiance_mw_m2_nm_sr": normalizer,
    }
    for response, table in cie_tables.items():
        integral = _trapezoid_response(wavelengths, radiances, table)
        if not math.isfinite(integral) or integral <= 0:
            raise SpectralReferenceDiagnosticError(
                f"{response} response integral is invalid"
            )
        result[f"{response}_shape_nm"] = integral / normalizer
    return result


def _completed_run(
    directory: Path,
    *,
    run: dict[str, Any],
    expected_input: str,
) -> dict[str, Any] | None:
    result_path = directory / "result.json"
    if (
        not result_path.is_file()
        or result_path.is_symlink()
        or (directory / "input.inp").read_bytes()
        != expected_input.encode("utf-8")
    ):
        return None
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        payload.get("schema") != RUN_SCHEMA
        or payload.get("run") != run
        or result_path.read_bytes() != canonical_json_bytes(payload)
    ):
        return None
    receipts = payload.get("files")
    if not isinstance(receipts, list):
        return None
    expected_names = _kept_run_files("shape")
    received: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            return None
        name = receipt.get("path")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in received
            or name not in expected_names
        ):
            return None
        path = directory / name
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != receipt.get("bytes")
            or sha256_file(path) != receipt.get("sha256")
        ):
            return None
        received.add(name)
    actual = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if (
        received != expected_names
        or actual != expected_names | {"result.json"}
        or any(path.is_symlink() for path in directory.iterdir())
    ):
        return None
    return payload


def _execute_run(
    *,
    uvspec: Path,
    data_root: Path,
    output_root: Path,
    run: dict[str, Any],
    input_text: str,
    cie_tables: dict[str, dict[int, float]],
) -> dict[str, Any]:
    runs_root = output_root / "runs"
    runs_root.mkdir(exist_ok=True)
    final_dir = runs_root / run["run_id"]
    if final_dir.exists():
        completed = _completed_run(
            final_dir,
            run=run,
            expected_input=input_text,
        )
        if completed is None:
            raise SpectralReferenceDiagnosticError(
                f"partial or stale diagnostic run exists: {final_dir}"
            )
        return completed
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f".{run['run_id']}.", dir=runs_root)
    )
    try:
        (temp_dir / DATA_LINK_NAME).symlink_to(
            data_root,
            target_is_directory=True,
        )
        (temp_dir / "input.inp").write_text(
            input_text,
            encoding="utf-8",
            newline="\n",
        )
        syntax = subprocess.run(
            [str(uvspec), "-c"],
            cwd=temp_dir,
            input=input_text,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (temp_dir / "syntax.stdout.txt").write_text(
            syntax.stdout,
            encoding="utf-8",
            newline="\n",
        )
        (temp_dir / "syntax.stderr.txt").write_text(
            syntax.stderr,
            encoding="utf-8",
            newline="\n",
        )
        if (
            syntax.returncode != 0
            or "Error" in syntax.stderr
            or "Exiting" in syntax.stderr
        ):
            raise SpectralReferenceDiagnosticError(
                f"uvspec syntax check failed: {temp_dir}"
            )
        completed = subprocess.run(
            [str(uvspec)],
            cwd=temp_dir,
            input=input_text,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (temp_dir / "stdout.txt").write_text(
            completed.stdout,
            encoding="utf-8",
            newline="\n",
        )
        (temp_dir / "stderr.txt").write_text(
            completed.stderr,
            encoding="utf-8",
            newline="\n",
        )
        if (
            completed.returncode != 0
            or "Error" in completed.stderr
            or "Exiting" in completed.stderr
        ):
            raise SpectralReferenceDiagnosticError(
                f"uvspec run failed: {temp_dir}"
            )
        result = _parse_candidate_result(
            temp_dir,
            candidate_wavelength_nm=float(
                run["candidate_reference_wavelength_nm"]
            ),
            cie_tables=cie_tables,
        )
        data_link = temp_dir / DATA_LINK_NAME
        if data_link.is_symlink():
            data_link.unlink()
        kept = _kept_run_files("shape")
        for path in list(temp_dir.iterdir()):
            if path.name not in kept:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        receipts = [
            {
                "path": name,
                "bytes": (temp_dir / name).stat().st_size,
                "sha256": sha256_file(temp_dir / name),
            }
            for name in sorted(kept)
        ]
        payload = {
            "schema": RUN_SCHEMA,
            "run": run,
            "result": result,
            "files": receipts,
        }
        (temp_dir / "result.json").write_bytes(
            canonical_json_bytes(payload)
        )
        temp_dir.replace(final_dir)
        return payload
    except Exception:
        raise


def _relative_standard_error(values: list[float]) -> tuple[float, float]:
    mean = statistics.fmean(values)
    if not math.isfinite(mean) or mean <= 0:
        raise SpectralReferenceDiagnosticError(
            "diagnostic aggregate mean is invalid"
        )
    return (
        mean,
        statistics.stdev(values) / math.sqrt(len(values)) / mean,
    )


def _summarize(
    diagnostic: dict[str, Any],
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    threshold = float(
        diagnostic["selection"][
            "maximum_response_shape_relative_standard_error"
        ]
    )
    rows: list[dict[str, Any]] = []
    for candidate in diagnostic["candidate_reference_wavelengths_nm"]:
        candidate_payloads = [
            payload
            for payload in payloads
            if payload["run"]["candidate_reference_wavelength_nm"]
            == candidate
        ]
        response_metrics: dict[str, dict[str, float]] = {}
        for response in ("photopic", "scotopic"):
            mean, relative_standard_error = _relative_standard_error(
                [
                    payload["result"][f"{response}_shape_nm"]
                    for payload in candidate_payloads
                ]
            )
            response_metrics[response] = {
                "mean_shape_nm": mean,
                "relative_standard_error": relative_standard_error,
            }
        primary = max(
            metrics["relative_standard_error"]
            for metrics in response_metrics.values()
        )
        secondary = sum(
            metrics["relative_standard_error"]
            for metrics in response_metrics.values()
        )
        rows.append(
            {
                "candidate_reference_wavelength_nm": candidate,
                "seed_count": len(candidate_payloads),
                "total_photon_count": sum(
                    int(payload["run"]["photon_count"])
                    for payload in candidate_payloads
                ),
                "photopic": response_metrics["photopic"],
                "scotopic": response_metrics["scotopic"],
                "primary_score": primary,
                "secondary_score": secondary,
                "passes_frozen_training_threshold": primary <= threshold,
            }
        )
    eligible = [
        row for row in rows if row["passes_frozen_training_threshold"]
    ]
    selected = (
        min(
            eligible,
            key=lambda row: (
                row["primary_score"],
                row["secondary_score"],
                row["candidate_reference_wavelength_nm"],
            ),
        )
        if eligible
        else None
    )
    return {
        "schema": (
            "moira.visibility-spectral-reference-training-diagnostic-summary/v1"
        ),
        "status": "complete_training_only_research_diagnostic",
        "diagnostic_id": diagnostic["diagnostic_id"],
        "training_point": diagnostic["training_point"],
        "threshold": threshold,
        "candidate_results": rows,
        "selected_candidate_reference_wavelength_nm": (
            selected["candidate_reference_wavelength_nm"]
            if selected is not None
            else None
        ),
        "selection_succeeded": selected is not None,
        "holdout_boundary": {
            "response_holdouts_executed": False,
            "direct_extinction_holdouts_executed": False,
            "grid_nodes_changed": False,
            "acceptance_thresholds_changed": False,
        },
    }


def _tooling_receipts(
    diagnostic_spec_path: Path,
    radiance_spec_path: Path,
) -> dict[str, Any]:
    paths = {
        "diagnostic_spec": diagnostic_spec_path,
        "radiance_spec": radiance_spec_path,
        "diagnostic_runner": Path(__file__).resolve(),
        "radiance_builder_dependency": (
            REPO_ROOT / "scripts" / "build_visibility_radiance_response_probe.py"
        ),
    }
    return {
        role: file_receipt(path, relative_to=REPO_ROOT)
        for role, path in paths.items()
    }


def build_diagnostic(
    *,
    diagnostic_spec_path: Path,
    radiance_spec_path: Path,
    source_archive: Path,
    reptran_archive: Path,
    libradtran_root: Path,
    data_root: Path,
    cie_root: Path,
    named_direct_artifact: Path,
    output_root: Path,
    max_new_runs: int | None,
) -> dict[str, Any]:
    if max_new_runs is not None and max_new_runs < 0:
        raise SpectralReferenceDiagnosticError(
            "max-new-runs must be non-negative"
        )
    if output_root.is_symlink():
        raise SpectralReferenceDiagnosticError(
            "output root must not be a symlink"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    if (output_root / MANIFEST_NAME).exists():
        raise SpectralReferenceDiagnosticError(
            "completed diagnostic is immutable; choose a new output"
        )
    diagnostic, radiance = load_diagnostic_spec(
        diagnostic_spec_path,
        radiance_spec_path=radiance_spec_path,
    )
    try:
        uvspec, source_receipt, cie_tables = _verify_source_inputs(
            radiance,
            source_archive=source_archive.resolve(),
            reptran_archive=reptran_archive.resolve(),
            libradtran_root=libradtran_root.resolve(),
            data_root=data_root.resolve(),
            cie_root=cie_root.resolve(),
            named_direct_artifact=named_direct_artifact.resolve(),
        )
    except VisibilityRadianceResponseError as exc:
        raise SpectralReferenceDiagnosticError(str(exc)) from exc
    payloads: list[dict[str, Any]] = []
    new_run_count = 0
    for candidate in diagnostic["candidate_reference_wavelengths_nm"]:
        for seed_index, seed in enumerate(
            diagnostic["monte_carlo"]["random_seeds"]
        ):
            run, input_text = _candidate_run(
                diagnostic,
                radiance,
                candidate_wavelength_nm=float(candidate),
                seed_index=seed_index,
                seed=int(seed),
            )
            run_dir = output_root / "runs" / run["run_id"]
            if not run_dir.exists():
                if (
                    max_new_runs is not None
                    and new_run_count >= max_new_runs
                ):
                    raise DiagnosticBudgetReached
                new_run_count += 1
            payloads.append(
                _execute_run(
                    uvspec=uvspec,
                    data_root=data_root.resolve(),
                    output_root=output_root,
                    run=run,
                    input_text=input_text,
                    cie_tables=cie_tables,
                )
            )
    summary = _summarize(diagnostic, payloads)
    summary_path = output_root / SUMMARY_NAME
    summary_path.write_bytes(canonical_json_bytes(summary))
    tooling = _tooling_receipts(
        diagnostic_spec_path,
        radiance_spec_path,
    )
    generation_identity = {
        "diagnostic_id": diagnostic["diagnostic_id"],
        "tooling": tooling,
        "source": source_receipt,
        "training_point": diagnostic["training_point"],
        "candidates": diagnostic["candidate_reference_wavelengths_nm"],
        "monte_carlo": diagnostic["monte_carlo"],
        "holdout_boundary": diagnostic["holdout_boundary"],
        "runtime_boundary": diagnostic["runtime_boundary"],
    }
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "status": "complete_training_only_research_diagnostic",
        "diagnostic_id": diagnostic["diagnostic_id"],
        "generation_fingerprint": sha256_bytes(
            canonical_json_bytes(generation_identity)
        ),
        "tooling": tooling,
        "source": source_receipt,
        "training_point": diagnostic["training_point"],
        "candidate_reference_wavelengths_nm": diagnostic[
            "candidate_reference_wavelengths_nm"
        ],
        "monte_carlo": diagnostic["monte_carlo"],
        "holdout_boundary": diagnostic["holdout_boundary"],
        "runtime_boundary": diagnostic["runtime_boundary"],
        "run_count": len(payloads),
        "runs": [
            {
                "run_id": payload["run"]["run_id"],
                **file_receipt(
                    output_root
                    / "runs"
                    / payload["run"]["run_id"]
                    / "result.json",
                    relative_to=output_root,
                ),
            }
            for payload in sorted(
                payloads,
                key=lambda payload: payload["run"]["run_id"],
            )
        ],
        "summary": file_receipt(
            summary_path,
            relative_to=output_root,
        ),
    }
    manifest_path = output_root / MANIFEST_NAME
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return {
        "status": "complete_training_only_research_diagnostic",
        "output": str(output_root),
        "new_run_count": new_run_count,
        "run_count": len(payloads),
        "generation_fingerprint": manifest["generation_fingerprint"],
        "manifest_sha256": sha256_file(manifest_path),
        "selected_candidate_reference_wavelength_nm": summary[
            "selected_candidate_reference_wavelength_nm"
        ],
        "candidate_results": summary["candidate_results"],
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Phase 1 training-only ALIS reference diagnostic."
        )
    )
    parser.add_argument(
        "--diagnostic-spec",
        type=Path,
        default=DEFAULT_DIAGNOSTIC_SPEC_PATH,
    )
    parser.add_argument(
        "--radiance-spec",
        type=Path,
        default=DEFAULT_RADIANCE_SPEC_PATH,
    )
    parser.add_argument("--inspect-spec", action="store_true")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--reptran-archive", type=Path)
    parser.add_argument("--libradtran-root", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--cie-root", type=Path)
    parser.add_argument("--named-direct-artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-new-runs", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.inspect_spec:
            print(
                json.dumps(
                    inspect_spec(
                        args.diagnostic_spec,
                        radiance_spec_path=args.radiance_spec,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        required = {
            "--source-archive": args.source_archive,
            "--reptran-archive": args.reptran_archive,
            "--libradtran-root": args.libradtran_root,
            "--data-root": args.data_root,
            "--cie-root": args.cie_root,
            "--named-direct-artifact": args.named_direct_artifact,
            "--output": args.output,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise SpectralReferenceDiagnosticError(
                "missing required arguments: " + ", ".join(missing)
            )
        try:
            result = build_diagnostic(
                diagnostic_spec_path=args.diagnostic_spec.resolve(),
                radiance_spec_path=args.radiance_spec.resolve(),
                source_archive=args.source_archive.resolve(),
                reptran_archive=args.reptran_archive.resolve(),
                libradtran_root=args.libradtran_root.resolve(),
                data_root=args.data_root.resolve(),
                cie_root=args.cie_root.resolve(),
                named_direct_artifact=args.named_direct_artifact.resolve(),
                output_root=args.output.resolve(),
                max_new_runs=args.max_new_runs,
            )
        except DiagnosticBudgetReached:
            result = {
                "status": "incomplete_resumable",
                "output": str(args.output.resolve()),
                "manifest_emitted": False,
            }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, SpectralReferenceDiagnosticError) as exc:
        print(f"spectral-reference diagnostic failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
