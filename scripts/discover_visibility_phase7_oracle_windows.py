"""Bound source-query windows for the predeclared Phase 7 oracle matrix.

This is a discovery tool, not an oracle.  It uses Moira only to locate a
narrow event window for every predeclared target/phase matrix cell.  The
independent external validator owns expected event times and never imports
this module, Moira, or the production event solver.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
DEFAULT_SPEC = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_visibility_phase7_broad_oracle_matrix_v1.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c"
)


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """One engine-owned source-query bound, never oracle truth."""

    case_id: str
    target: str
    phase: str
    site_id: str
    status: str
    reason: str | None
    event_jd_ut: float | None
    observation_day_key: int | None
    comparison_observation_day_key: int | None
    comparison_day_status: str | None
    search_start_utc: str
    search_window_days: int


def _object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _validate_spec(spec: dict[str, Any]) -> None:
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-broad-oracle-matrix-spec/v1"
        or spec.get("status")
        != "predeclared_complete_admitted_target_phase_matrix"
    ):
        raise ValueError("oracle matrix specification identity differs")
    policy = spec["selection_policy"]
    targets = tuple(policy["required_targets"])
    phases = tuple(policy["required_phases"])
    cases = tuple(spec["cases"])
    cells = {(case["target"], case["phase"]) for case in cases}
    expected = {(target, phase) for target in targets for phase in phases}
    if (
        cells != expected
        or len(cases) != len(cells)
        or len(cases) != policy["required_matrix_cell_count"]
    ):
        raise ValueError("oracle matrix is not the complete declared product")


def _discover_one(
    case: dict[str, Any],
    site: dict[str, Any],
    *,
    kernel: str,
    pack: str,
    scan_step_minutes: float,
    adaptive_minimum_step_minutes: float,
    root_time_tolerance_seconds: float,
) -> DiscoveryResult:
    os.environ["MOIRA_NO_DOWNLOAD"] = "1"
    from moira._visibility_lut import VisibilityDataPackConfig
    from moira.heliacal import (
        PhysicalBackgroundScope,
        PhysicalDirectionalBackground,
        PhysicalVisibilityPhase,
        PhysicalVisibilityPolicy,
        PhysicalVisibilitySearchPolicy,
        physical_visibility_event,
    )
    from moira.julian import jd_from_datetime
    from moira.spk_reader import set_kernel_path

    set_kernel_path(kernel)
    background = PhysicalDirectionalBackground(
        photopic_luminance_cd_m2=0.0001,
        scotopic_luminance_cd_m2=0.00015,
        scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR,
        component_ids=("phase7_broad_oracle_dark_sky",),
        source_id="phase7_broad_oracle_dark_sky_v1",
        source_receipt_sha256="a" * 64,
        method_id="source_locked_reference_anchor_v1",
    )
    policy = PhysicalVisibilityPolicy(
        background=background,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    search_start = datetime.fromisoformat(
        case["search_start_utc"].replace("Z", "+00:00")
    )
    result = physical_visibility_event(
        case["target"],
        PhysicalVisibilityPhase(case["phase"]),
        jd_from_datetime(search_start),
        float(site["latitude_deg"]),
        float(site["longitude_deg"]),
        data_pack_config=VisibilityDataPackConfig(
            pack,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        ),
        policy=policy,
        search_policy=PhysicalVisibilitySearchPolicy(
            search_window_days=int(case["search_window_days"]),
            scan_step_days=scan_step_minutes / 1440.0,
            adaptive_minimum_step_days=(
                adaptive_minimum_step_minutes / 1440.0
            ),
            root_time_tolerance_days=(
                root_time_tolerance_seconds / 86400.0
            ),
        ),
    )
    return DiscoveryResult(
        case_id=case["case_id"],
        target=case["target"],
        phase=case["phase"],
        site_id=case["site_id"],
        status=result.status.value,
        reason=result.reason,
        event_jd_ut=result.event_jd_ut,
        observation_day_key=result.observation_day_key,
        comparison_observation_day_key=(
            result.comparison_observation_day_key
        ),
        comparison_day_status=result.comparison_day_status,
        search_start_utc=case["search_start_utc"],
        search_window_days=int(case["search_window_days"]),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--exact",
        action="store_true",
        help="use the public default scan and root-refinement policy",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="discover only the named predeclared cell; may be repeated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.workers <= 0:
        raise ValueError("workers must be positive")
    spec = _object(arguments.spec.resolve(), "oracle matrix specification")
    _validate_spec(spec)
    selection = spec["selection_policy"]
    sites = spec["sites"]
    all_cases = tuple(spec["cases"])
    if arguments.case_ids:
        requested = frozenset(arguments.case_ids)
        known = {case["case_id"] for case in all_cases}
        unknown = requested - known
        if unknown:
            raise ValueError(
                "unknown case ids: " + ", ".join(sorted(unknown))
            )
        cases = tuple(
            case for case in all_cases if case["case_id"] in requested
        )
    else:
        cases = all_cases
    scan_step_minutes = (
        5.0
        if arguments.exact
        else float(selection["discovery_scan_step_minutes"])
    )
    adaptive_minimum_step_minutes = (
        0.5
        if arguments.exact
        else float(
            selection["discovery_adaptive_minimum_step_minutes"]
        )
    )
    root_time_tolerance_seconds = 0.25 if arguments.exact else 2.0
    results: list[DiscoveryResult] = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=arguments.workers
    ) as executor:
        futures = {
            executor.submit(
                _discover_one,
                case,
                sites[case["site_id"]],
                kernel=str(arguments.kernel.resolve()),
                pack=str(arguments.pack.resolve()),
                scan_step_minutes=scan_step_minutes,
                adaptive_minimum_step_minutes=(
                    adaptive_minimum_step_minutes
                ),
                root_time_tolerance_seconds=(
                    root_time_tolerance_seconds
                ),
            ): case["case_id"]
            for case in cases
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"{result.case_id}: {result.status} "
                f"{result.event_jd_ut or result.reason}",
                flush=True,
            )
    order = {case["case_id"]: index for index, case in enumerate(cases)}
    results.sort(key=lambda result: order[result.case_id])
    receipt = {
        "schema": "moira.physical-heliacal-visibility-oracle-window-discovery/v1",
        "status": (
            "complete"
            if all(result.status == "evaluated" for result in results)
            else "incomplete"
        ),
        "role": "source_query_bounds_only_not_oracle_truth",
        "exact_public_search_policy": arguments.exact,
        "spec": str(arguments.spec.resolve()),
        "kernel": str(arguments.kernel.resolve()),
        "pack": str(arguments.pack.resolve()),
        "results": [asdict(result) for result in results],
    }
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0 if receipt["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
