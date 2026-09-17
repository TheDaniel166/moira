#!/usr/bin/env python3
"""Build an exact-TDB JPL Horizons apsidal-passage candidate fixture.

Network access is intentional and belongs outside pytest.  The builder locates
chronological radial-velocity sign crossings in official geometric Horizons
VECTORS output, refines each crossing without consulting Moira's event solver,
and writes only to an operator-selected candidate directory.  Acceptance into
``tests/fixtures`` remains a separate reviewed source-data change.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "tests"))

from tools.horizons import (  # noqa: E402
    _parse_vector_state,
    _parse_vector_series_km_s,
    _vector_series_tdb_parameters,
    _vector_state_tdb_parameters,
    orbital_elements_tdb,
    vector_series_response_tdb,
    vector_state_response_tdb,
)


GENERATOR_VERSION = "moira-horizons-apsidal-passages-builder-v1"
SCHEMA_VERSION = "moira.horizons-apsidal-passages.v1"
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
KM_PER_AU = 149_597_870.700
REFINEMENT_TOLERANCE_DAYS = 2.0e-8
REFINEMENT_MAX_ITERATIONS = 24
WITNESS_OFFSET_DAYS = 0.005


@dataclass(frozen=True, slots=True)
class Case:
    role: str
    body: str
    body_naif_id: int
    command: str
    center: str
    center_naif_id: int
    start_jd_tdb: float
    event_kinds: tuple[str, ...] = ("PERICENTER", "APOCENTER")
    search_days: float | None = None

    @property
    def key(self) -> str:
        return (
            f"{self.body_naif_id}:{self.center_naif_id}:"
            f"{self.start_jd_tdb:.12f}"
        )


CASES = (
    Case("calibration", "Mercury", 199, "199", "500@10", 10, 2_451_545.0),
    Case("holdout", "Venus", 299, "299", "500@10", 10, 2_451_545.0),
    Case("calibration", "Earth", 399, "399", "500@10", 10, 2_451_545.0),
    Case("holdout", "Earth-Moon Barycenter", 3, "3", "500@10", 10, 2_451_545.0),
    Case("holdout", "Mars", 4, "4", "500@10", 10, 2_451_545.0),
    Case("calibration", "Jupiter", 5, "5", "500@10", 10, 2_451_545.0),
    Case("holdout", "Saturn", 6, "6", "500@10", 10, 2_451_545.0),
    Case("holdout", "Uranus", 7, "7", "500@10", 10, 2_451_545.0),
    Case("calibration", "Neptune", 8, "8", "500@10", 10, 2_451_545.0),
    Case("holdout", "Pluto", 9, "9", "500@10", 10, 2_451_545.0),
    Case("holdout", "Eros", 2_000_433, "433;", "500@10", 10, 2_460_676.5),
    Case("calibration", "Chiron", 2_002_060, "2060;", "500@10", 10, 2_460_676.5),
    Case(
        "calibration",
        "1P/Halley",
        1_000_001,
        "DES=1P;NOFRAG;CAP",
        "500@10",
        10,
        2_473_459.5,
        ("PERICENTER",),
        5.0 * 365.25,
    ),
    Case(
        "holdout",
        "2P/Encke",
        1_000_002,
        "DES=2P;NOFRAG;CAP",
        "500@10",
        10,
        2_460_676.5,
    ),
    Case(
        "holdout",
        "Sedna",
        2_090_377,
        "90377;",
        "500@10",
        10,
        2_477_112.5,
        ("PERICENTER",),
        20.0 * 365.25,
    ),
    Case(
        "holdout",
        "Eris",
        2_136_199,
        "136199;",
        "500@10",
        10,
        2_542_855.5,
        ("PERICENTER",),
        20.0 * 365.25,
    ),
)


def _response_receipt(text: str) -> dict[str, Any]:
    encoded = text.encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "byte_count": len(encoded)}


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return None if match is None else match.group(1).strip()


def _authority_metadata(text: str) -> dict[str, str | None]:
    return {
        "api_version": _first_match(r"^API VERSION:\s*(.+)$", text),
        "api_source": _first_match(r"^API SOURCE:\s*(.+)$", text),
        "target_body_line": _first_match(r"^(Target body name:.+)$", text),
        "center_body_line": _first_match(r"^(Center body name:.+)$", text),
        "target_solution": _first_match(
            r"^Target body name:.*?\{source:\s*([^}]+)\}", text
        ),
    }


def _distance_au(state) -> float:
    return math.sqrt(state.x * state.x + state.y * state.y + state.z * state.z) / KM_PER_AU


def _radial_velocity_km_s(state) -> float:
    radius = math.sqrt(state.x * state.x + state.y * state.y + state.z * state.z)
    return (state.x * state.vx + state.y * state.vy + state.z * state.vz) / radius


def _step_string(step_days: float) -> str:
    return f"{max(1, math.floor(step_days * 1440.0))} m"


def _crosses(kind: str, left_g: float, right_g: float) -> bool:
    if kind == "PERICENTER":
        return left_g <= 0.0 <= right_g
    if kind == "APOCENTER":
        return left_g >= 0.0 >= right_g
    raise ValueError(kind)


def _request_state(case: Case, epoch_tdb: float) -> tuple[Any, str]:
    text = vector_state_response_tdb(case.command, epoch_tdb, case.center)
    return _parse_vector_state(case.command, text), text


def _coarse_search(case: Case) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    elements = orbital_elements_tdb(case.command, case.start_jd_tdb, case.center)
    if not math.isfinite(elements.orbital_period_days) or elements.orbital_period_days <= 0.0:
        raise SystemExit(f"{case.body}: no finite positive search period")
    step_days = max(0.05, min(32.0, elements.orbital_period_days / 256.0))
    search_days = (
        1.5 * elements.orbital_period_days
        if case.search_days is None
        else case.search_days
    )
    stop_tdb = case.start_jd_tdb + search_days + step_days
    step_size = _step_string(step_days)
    request = _vector_series_tdb_parameters(
        case.command,
        case.start_jd_tdb - step_days,
        stop_tdb,
        step_size,
        case.center,
    )
    text = vector_series_response_tdb(
        case.command,
        case.start_jd_tdb - step_days,
        stop_tdb,
        step_size,
        case.center,
    )
    samples = _parse_vector_series_km_s(case.command, text)
    brackets: dict[str, tuple[float, float]] = {}
    for left, right in zip(samples, samples[1:]):
        if right.jd_tdb < case.start_jd_tdb:
            continue
        left_g = _radial_velocity_km_s(left.state)
        right_g = _radial_velocity_km_s(right.state)
        for kind in case.event_kinds:
            if kind not in brackets and _crosses(kind, left_g, right_g):
                brackets[kind] = (left.jd_tdb, right.jd_tdb)
        if len(brackets) == len(case.event_kinds):
            break
    missing = tuple(kind for kind in case.event_kinds if kind not in brackets)
    if missing:
        raise SystemExit(f"{case.body}: no coarse bracket for {missing}")
    return brackets, {
        "request": request,
        "response": _response_receipt(text),
        "period_days": elements.orbital_period_days,
        "sampling_step_days": step_days,
        "sampling_step_size": step_size,
        "search_days": search_days,
    }


def _refine_event(
    case: Case,
    kind: str,
    coarse_bracket: tuple[float, float],
) -> dict[str, Any]:
    left, right = coarse_bracket
    fine_step = "1 m" if right - left <= 2.0 else "5 m"
    fine_request = _vector_series_tdb_parameters(
        case.command, left, right, fine_step, case.center
    )
    fine_text = vector_series_response_tdb(
        case.command, left, right, fine_step, case.center
    )
    samples = _parse_vector_series_km_s(case.command, fine_text)
    fine_left = fine_right = None
    for before, after in zip(samples, samples[1:]):
        before_g = _radial_velocity_km_s(before.state)
        after_g = _radial_velocity_km_s(after.state)
        if _crosses(kind, before_g, after_g):
            fine_left, fine_right = before, after
            break
    if fine_left is None or fine_right is None:
        raise SystemExit(f"{case.body} {kind}: no fine bracket")

    left_tdb = fine_left.jd_tdb
    right_tdb = fine_right.jd_tdb
    left_g = _radial_velocity_km_s(fine_left.state)
    right_g = _radial_velocity_km_s(fine_right.state)
    refinement_responses: list[dict[str, Any]] = []
    iterations = 0
    for iterations in range(1, REFINEMENT_MAX_ITERATIONS + 1):
        if right_tdb - left_tdb <= REFINEMENT_TOLERANCE_DAYS:
            break
        if right_g == left_g:
            candidate_tdb = (left_tdb + right_tdb) / 2.0
        else:
            candidate_tdb = left_tdb - left_g * (right_tdb - left_tdb) / (right_g - left_g)
        width = right_tdb - left_tdb
        if not (
            left_tdb + 0.25 * width
            <= candidate_tdb
            <= right_tdb - 0.25 * width
        ):
            candidate_tdb = (left_tdb + right_tdb) / 2.0
        candidate, candidate_text = _request_state(case, candidate_tdb)
        candidate_g = _radial_velocity_km_s(candidate)
        refinement_responses.append(
            {
                "epoch_tdb": candidate_tdb,
                "request": _vector_state_tdb_parameters(
                    case.command, candidate_tdb, case.center
                ),
                "response": _response_receipt(candidate_text),
                "radial_velocity_km_s": candidate_g,
            }
        )
        if _crosses(kind, left_g, candidate_g):
            right_tdb = candidate_tdb
            right_g = candidate_g
        else:
            left_tdb = candidate_tdb
            left_g = candidate_g

    if right_tdb - left_tdb > REFINEMENT_TOLERANCE_DAYS:
        raise SystemExit(
            f"{case.body} {kind}: refinement did not close; "
            f"width={right_tdb - left_tdb:.12g} day"
        )
    epoch_tdb = (left_tdb + right_tdb) / 2.0
    exact, exact_text = _request_state(case, epoch_tdb)
    before_tdb = epoch_tdb - WITNESS_OFFSET_DAYS
    after_tdb = epoch_tdb + WITNESS_OFFSET_DAYS
    before, before_text = _request_state(case, before_tdb)
    after, after_text = _request_state(case, after_tdb)
    before_g = _radial_velocity_km_s(before)
    after_g = _radial_velocity_km_s(after)
    if not _crosses(kind, before_g, after_g):
        raise SystemExit(f"{case.body} {kind}: final witness has wrong sign")
    exact_distance = _distance_au(exact)
    before_distance = _distance_au(before)
    after_distance = _distance_au(after)
    if kind == "PERICENTER":
        witnessed = exact_distance <= min(before_distance, after_distance)
    else:
        witnessed = exact_distance >= max(before_distance, after_distance)
    if not witnessed:
        raise SystemExit(f"{case.body} {kind}: distance witness failed")

    return {
        "kind": kind,
        "epoch_tdb": epoch_tdb,
        "distance_au": exact_distance,
        "radial_velocity_km_s": _radial_velocity_km_s(exact),
        "coarse_bracket_tdb": list(coarse_bracket),
        "final_bracket_tdb": [left_tdb, right_tdb],
        "refinement": {
            "method": "safeguarded_secant_on_horizons_radial_velocity",
            "tolerance_days": REFINEMENT_TOLERANCE_DAYS,
            "maximum_iterations": REFINEMENT_MAX_ITERATIONS,
            "iterations": iterations,
            "fine_step_size": fine_step,
        },
        "fine_series": {
            "request": fine_request,
            "response": _response_receipt(fine_text),
        },
        "refinement_samples": refinement_responses,
        "event_state": {
            "request": _vector_state_tdb_parameters(
                case.command, epoch_tdb, case.center
            ),
            "response": _response_receipt(exact_text),
            "vector_icrf_km_km_s": asdict(exact),
        },
        "two_sided_witness": {
            "offset_days": WITNESS_OFFSET_DAYS,
            "before": {
                "epoch_tdb": before_tdb,
                "distance_au": before_distance,
                "radial_velocity_km_s": before_g,
                "response": _response_receipt(before_text),
            },
            "after": {
                "epoch_tdb": after_tdb,
                "distance_au": after_distance,
                "radial_velocity_km_s": after_g,
                "response": _response_receipt(after_text),
            },
        },
        "authority": _authority_metadata(exact_text),
    }


def _record(case: Case, retrieved_utc: str) -> dict[str, Any]:
    brackets, coarse = _coarse_search(case)
    return {
        "case_key": case.key,
        "fixture_role": case.role,
        "body": case.body,
        "body_naif_id": case.body_naif_id,
        "center_naif_id": case.center_naif_id,
        "start_jd_tdb": case.start_jd_tdb,
        "source": {
            "owner": "NASA/JPL Solar System Dynamics",
            "source_url": HORIZONS_URL,
            "retrieved_utc": retrieved_utc,
            "generator_version": GENERATOR_VERSION,
        },
        "semantics": (
            "first chronological isolated two-sided local extremum of "
            "center-relative geometric distance at or after start_jd_tdb"
        ),
        "coordinate_contract": {
            "time_scale": "TDB",
            "reference_system": "ICRF",
            "reference_plane": "FRAME",
            "vector_correction": "NONE",
            "distance_unit": "AU",
            "velocity_unit": "km/s",
        },
        "coarse_search": coarse,
        "events": [
            _refine_event(case, kind, brackets[kind])
            for kind in case.event_kinds
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="optional body name; repeat to generate a subset",
    )
    parser.add_argument(
        "--merge-input",
        action="append",
        type=Path,
        default=[],
        help="merge already generated candidate fixtures without network access",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    tracked_fixture_dir = (REPOSITORY_ROOT / "tests" / "fixtures").resolve()
    if output_dir == tracked_fixture_dir or tracked_fixture_dir in output_dir.parents:
        raise SystemExit("candidate output must not be inside tests/fixtures")
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = CASES
    if args.case and args.merge_input:
        raise SystemExit("--case and --merge-input are mutually exclusive")
    if args.case:
        names = set(args.case)
        selected = tuple(case for case in CASES if case.body in names)
        missing = names - {case.body for case in selected}
        if missing:
            raise SystemExit(f"unknown case name(s): {sorted(missing)}")
    if args.merge_input:
        by_key: dict[str, dict[str, Any]] = {}
        for raw_path in args.merge_input:
            candidate = json.loads(raw_path.resolve().read_text(encoding="utf-8"))
            if candidate.get("schema_version") != SCHEMA_VERSION:
                raise SystemExit(f"wrong candidate schema: {raw_path}")
            for record in candidate["records"]:
                key = record["case_key"]
                if key in by_key:
                    raise SystemExit(f"duplicate candidate case key: {key}")
                by_key[key] = record
        expected = {case.key for case in CASES}
        if set(by_key) != expected:
            raise SystemExit(
                "merged candidates must contain the complete frozen case set; "
                f"missing={sorted(expected - set(by_key))}, "
                f"extra={sorted(set(by_key) - expected)}"
            )
        records = [by_key[case.key] for case in CASES]
    else:
        retrieved_utc = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        records = []
        for index, case in enumerate(selected, start=1):
            print(f"[{index}/{len(selected)}] {case.body}", flush=True)
            records.append(_record(case, retrieved_utc))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "fixture_role": "disjoint_calibration_and_holdout",
        "source_url": HORIZONS_URL,
        "refinement_policy": {
            "algorithm": "coarse_sign_scan_then_fine_scan_then_safeguarded_secant",
            "radial_function": "dot(position_km, velocity_km_s) / norm(position_km)",
            "root_tolerance_days": REFINEMENT_TOLERANCE_DAYS,
            "maximum_iterations": REFINEMENT_MAX_ITERATIONS,
            "witness_offset_days": WITNESS_OFFSET_DAYS,
        },
        "acceptance_gates": {
            "event_time_absolute_days": 1.0e-4,
            "distance_absolute_au": 1.0e-9,
        },
        "records": records,
    }
    output = output_dir / "horizons_apsidal_passages_reference.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(records)} Horizons apsidal cases to {output}")
    print(f"sha256={hashlib.sha256(output.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
