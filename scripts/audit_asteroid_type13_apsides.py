"""Audit the admitted asteroid catalog's Type-13 sampling at radial extrema.

The live audit partitions every admitted asteroid by current JPL SBDB
perihelion distance.  Bodies below the analytically admitted cutoff receive a
same-span authority comparison: a 10-day Horizons series is represented with
Moira's seven-node Type-13 evaluator and compared with a 5-day Horizons series
at every off-grid sample neighboring a radial-velocity sign crossing.  Bodies
at or beyond the cutoff are governed by a worst-case elliptic two-body sweep.

This is external-network validation tooling, not a runtime dependency.

Usage:
    python scripts/audit_asteroid_type13_apsides.py OUTPUT.json
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira import moira_native  # noqa: E402
from scripts import build_unified_asteroid_catalog as catalog_builder  # noqa: E402


IDENTITY_PATH = ROOT / "moira" / "data" / "asteroid_catalog_naif.json"
MANIFEST_PATH = ROOT / "moira" / "kernels" / "asteroids" / "manifest.json"
SBDB_QUERY_URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"

BASE_STEP_DAYS = 10
AUDIT_STEP_DAYS = 5
WINDOW_SIZE = 7
DIRECT_CUTOFF_AU = 1.3
DISTANCE_GATE_AU = 1.0e-9
AU_KM = 149_597_870.7
DISTANCE_GATE_KM = DISTANCE_GATE_AU * AU_KM
SHARED_NODE_GATE_KM = 1.0e-6
MU_SUN_KM3_S2 = 132_712_440_041.93938
SECONDS_PER_DAY = 86_400.0
ANALYTIC_E_STEP = 0.001
ANALYTIC_PHASE_STEP_DAYS = 0.1


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_url(params: dict[str, str]) -> tuple[dict, str]:
    url = f"{SBDB_QUERY_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Moira asteroid Type-13 apsidal audit"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _sbdb_rows(
    constraint: dict,
    *,
    fields: str,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    params = {
        "sb-kind": "a",
        "sb-ns": "n",
        "sb-cdata": json.dumps(constraint, separators=(",", ":")),
        "fields": fields,
        "full-prec": "true",
        "sort": "q",
    }
    payload, response_sha256 = _read_json_url(params)
    names = payload.get("fields", [])
    rows = [dict(zip(names, row)) for row in payload.get("data", [])]
    return rows, {
        "params": params,
        "response_sha256": response_sha256,
        "global_result_count": int(payload.get("count", 0)),
        "signature": payload.get("signature"),
    }


def _radial_velocity(states: list[list[float]], index: int) -> float:
    x, y, z, vx, vy, vz = (states[axis][index] for axis in range(6))
    radius = math.sqrt(x * x + y * y + z * z)
    return (x * vx + y * vy + z * vz) / radius


def _crosses_zero(left: float, right: float) -> bool:
    return (
        (left <= 0.0 <= right or left >= 0.0 >= right)
        and not (left == 0.0 and right == 0.0)
    )


def _radius(position: tuple[float, float, float] | list[float]) -> float:
    return math.sqrt(sum(value * value for value in position[:3]))


def _cartesian_delta(left: list[float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left[axis] - right[axis]) ** 2 for axis in range(3)))


def _extremum_witness_indices(
    audit_epochs: list[float],
    audit_states: list[list[float]],
    base_epochs: list[float],
) -> tuple[list[int], int]:
    """Return off-grid audit nodes adjacent to every detected radial extremum."""

    base_keys = {f"{epoch:.9f}" for epoch in base_epochs}
    witness_indices: set[int] = set()
    crossing_count = 0
    for index in range(len(audit_epochs) - 1):
        if not _crosses_zero(
            _radial_velocity(audit_states, index),
            _radial_velocity(audit_states, index + 1),
        ):
            continue
        crossing_count += 1
        for candidate in range(max(0, index - 1), min(len(audit_epochs), index + 3)):
            if f"{audit_epochs[candidate]:.9f}" not in base_keys:
                witness_indices.add(candidate)
    return sorted(witness_indices), crossing_count


def _evaluate_body_once(number: int) -> dict[str, object]:
    original_step = catalog_builder.STEP_DAYS
    try:
        catalog_builder.STEP_DAYS = BASE_STEP_DAYS
        base = catalog_builder._fetch_body(number)
        catalog_builder.STEP_DAYS = AUDIT_STEP_DAYS
        raw = catalog_builder._fetch_raw(f"{number};", base["start"], base["stop"])
        audit_epochs, audit_states = catalog_builder._parse_vectors(raw)
    finally:
        catalog_builder.STEP_DAYS = original_step

    witnesses, crossing_count = _extremum_witness_indices(
        audit_epochs,
        audit_states,
        base["epochs_jd"],
    )
    if crossing_count == 0 or not witnesses:
        raise RuntimeError(f"asteroid {number} has no auditable radial extremum")

    audit_index = {
        f"{epoch:.9f}": index for index, epoch in enumerate(audit_epochs)
    }
    shared_node_max_radial_error = 0.0
    shared_node_max_cartesian_error = 0.0
    for base_index, epoch in enumerate(base["epochs_jd"]):
        audit_position_index = audit_index[f"{epoch:.9f}"]
        base_position = tuple(base["states"][axis][base_index] for axis in range(3))
        audit_position = tuple(
            audit_states[axis][audit_position_index] for axis in range(3)
        )
        shared_node_max_radial_error = max(
            shared_node_max_radial_error,
            abs(_radius(base_position) - _radius(audit_position)),
        )
        shared_node_max_cartesian_error = max(
            shared_node_max_cartesian_error,
            math.sqrt(
                sum(
                    (base_position[axis] - audit_position[axis]) ** 2
                    for axis in range(3)
                )
            ),
        )

    worst_radial: dict[str, object] | None = None
    worst_cartesian: dict[str, object] | None = None
    for index in witnesses:
        epoch = audit_epochs[index]
        fitted = moira_native.spk_type13_record(
            base["epochs_jd"],
            base["states"],
            WINDOW_SIZE,
            epoch,
        )
        authority = tuple(audit_states[axis][index] for axis in range(3))
        radial_error = abs(_radius(fitted) - _radius(authority))
        cartesian_error = _cartesian_delta(fitted, authority)
        radial_row = {"epoch_jd_tdb": epoch, "error_km": radial_error}
        cartesian_row = {"epoch_jd_tdb": epoch, "error_km": cartesian_error}
        if worst_radial is None or radial_error > worst_radial["error_km"]:
            worst_radial = radial_row
        if worst_cartesian is None or cartesian_error > worst_cartesian["error_km"]:
            worst_cartesian = cartesian_row

    assert worst_radial is not None
    assert worst_cartesian is not None
    return {
        "number": number,
        "naif_id": int(base["naif_id"]),
        "name": str(base["name"]),
        "coverage_start": str(base["start"]),
        "coverage_stop": str(base["stop"]),
        "radial_extrema_detected": crossing_count,
        "off_grid_witness_count": len(witnesses),
        "shared_node_max_radial_error_km": shared_node_max_radial_error,
        "shared_node_max_cartesian_error_km": shared_node_max_cartesian_error,
        "authority_series_consistent": (
            shared_node_max_radial_error <= SHARED_NODE_GATE_KM
            and shared_node_max_cartesian_error <= SHARED_NODE_GATE_KM
        ),
        "worst_radial_error": worst_radial,
        "worst_cartesian_error": worst_cartesian,
        "passed": (
            worst_radial["error_km"] <= DISTANCE_GATE_KM
            and shared_node_max_radial_error <= SHARED_NODE_GATE_KM
            and shared_node_max_cartesian_error <= SHARED_NODE_GATE_KM
        ),
    }


def _evaluate_body(number: int) -> dict[str, object]:
    """Evaluate one body with bounded whole-body retries for live JPL outages."""

    for attempt in range(4):
        try:
            return _evaluate_body_once(number)
        except Exception as exc:  # noqa: BLE001 - external audit boundary
            if attempt == 3:
                raise RuntimeError(
                    f"asteroid {number} audit failed after four attempts: "
                    f"{type(exc).__name__}: {exc}"
                ) from None
            time.sleep(2 ** attempt)
    raise AssertionError("audit retry loop exhausted")


def _elliptic_state(q_au: float, eccentricity: float, days: float) -> tuple[float, ...]:
    semi_major_km = q_au * AU_KM / (1.0 - eccentricity)
    mean_motion = math.sqrt(MU_SUN_KM3_S2 / semi_major_km**3)
    mean_anomaly = mean_motion * days * SECONDS_PER_DAY
    if eccentricity < 0.8:
        eccentric_anomaly = mean_anomaly / (1.0 - eccentricity)
    else:
        eccentric_anomaly = math.copysign(
            (6.0 * abs(mean_anomaly)) ** (1.0 / 3.0),
            mean_anomaly,
        )
    for _ in range(60):
        residual = (
            eccentric_anomaly
            - eccentricity * math.sin(eccentric_anomaly)
            - mean_anomaly
        )
        derivative = 1.0 - eccentricity * math.cos(eccentric_anomaly)
        correction = residual / derivative
        eccentric_anomaly -= correction
        if abs(correction) < 1.0e-15:
            break
    cosine = math.cos(eccentric_anomaly)
    sine = math.sin(eccentric_anomaly)
    minor_factor = math.sqrt(1.0 - eccentricity * eccentricity)
    anomaly_rate = mean_motion / (1.0 - eccentricity * cosine)
    return (
        semi_major_km * (cosine - eccentricity),
        semi_major_km * minor_factor * sine,
        0.0,
        -semi_major_km * sine * anomaly_rate,
        semi_major_km * minor_factor * cosine * anomaly_rate,
        0.0,
    )


def _outer_domain_bound() -> dict[str, object]:
    """Numerically sweep the fastest bound ellipse admitted at the cutoff."""

    jd_anchor = 2_451_545.0
    worst_radial = {"error_km": -1.0}
    worst_cartesian = {"error_km": -1.0}
    eccentricities = [index * ANALYTIC_E_STEP for index in range(1000)] + [0.9999]
    phase_count = int(BASE_STEP_DAYS / ANALYTIC_PHASE_STEP_DAYS) + 1
    for eccentricity in eccentricities:
        for phase_index in range(phase_count):
            phase = phase_index * ANALYTIC_PHASE_STEP_DAYS
            node_days = [-50.0 + 10.0 * index + phase for index in range(11)]
            state_rows = [
                _elliptic_state(DIRECT_CUTOFF_AU, eccentricity, day)
                for day in node_days
            ]
            states = [[row[axis] for row in state_rows] for axis in range(6)]
            witness_day = phase + 5.0 if phase <= 5.0 else phase - 5.0
            exact = _elliptic_state(DIRECT_CUTOFF_AU, eccentricity, witness_day)
            fitted = moira_native.spk_type13_record(
                [jd_anchor + day for day in node_days],
                states,
                WINDOW_SIZE,
                jd_anchor + witness_day,
            )
            radial_error = abs(_radius(fitted) - _radius(exact))
            cartesian_error = _cartesian_delta(fitted, exact[:3])
            context = {
                "eccentricity": eccentricity,
                "grid_phase_days": phase,
                "witness_day_from_perihelion": witness_day,
            }
            if radial_error > worst_radial["error_km"]:
                worst_radial = {"error_km": radial_error, **context}
            if cartesian_error > worst_cartesian["error_km"]:
                worst_cartesian = {"error_km": cartesian_error, **context}
    return {
        "governing_model": "elliptic two-body Sun-centered state",
        "perihelion_distance_au": DIRECT_CUTOFF_AU,
        "eccentricity_domain": "0.0000 through 0.9990 by 0.001 plus 0.9999",
        "grid_phase_domain_days": (
            f"0.0 through 10.0 by {ANALYTIC_PHASE_STEP_DAYS}"
        ),
        "worst_radial_error": worst_radial,
        "worst_cartesian_error": worst_cartesian,
        "distance_gate_km": DISTANCE_GATE_KM,
        "radial_margin_factor": DISTANCE_GATE_KM / worst_radial["error_km"],
        "passed": worst_radial["error_km"] <= DISTANCE_GATE_KM,
    }


def _body_to_shard(manifest: dict) -> dict[int, int]:
    return {
        int(body): int(shard["index"])
        for shard in manifest["shards"]
        for body in shard["bodies"]
    }


def _checkpoint(
    path: Path,
    results: list[dict[str, object]],
    context: dict[str, object],
) -> None:
    payload = {
        "schema": "moira.asteroid-type13-apsidal-audit-checkpoint/v1",
        "context": context,
        "results": results,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--throttle-seconds", type=float, default=0.5)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")

    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    admitted_numbers = {int(naif_id) - 2_000_000 for naif_id in identity.values()}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    body_to_shard = _body_to_shard(manifest)
    checkpoint_context = {
        "identity_sha256": _sha256(IDENTITY_PATH),
        "manifest_sha256": _sha256(MANIFEST_PATH),
        "base_step_days": BASE_STEP_DAYS,
        "authority_step_days": AUDIT_STEP_DAYS,
        "window_size": WINDOW_SIZE,
        "direct_cutoff_au": DIRECT_CUTOFF_AU,
        "distance_gate_km": DISTANCE_GATE_KM,
        "shared_node_gate_km": SHARED_NODE_GATE_KM,
    }

    fields = "pdes,full_name,e,q,a,per,class,orbit_id"
    candidate_rows, candidate_query = _sbdb_rows(
        {"AND": [f"q|LT|{DIRECT_CUTOFF_AU}"]},
        fields=fields,
    )
    missing_rows, missing_query = _sbdb_rows({"AND": ["q|ND"]}, fields=fields)
    unbound_rows, unbound_query = _sbdb_rows({"AND": ["e|GE|1"]}, fields=fields)

    candidates = [
        row
        for row in candidate_rows
        if str(row["pdes"]).isdigit() and int(row["pdes"]) in admitted_numbers
    ]
    missing_admitted = [
        row for row in missing_rows
        if str(row["pdes"]).isdigit() and int(row["pdes"]) in admitted_numbers
    ]
    unbound_admitted = [
        row for row in unbound_rows
        if str(row["pdes"]).isdigit() and int(row["pdes"]) in admitted_numbers
    ]
    if missing_admitted or unbound_admitted:
        raise RuntimeError(
            "admitted asteroid universe includes missing-q or unbound bodies"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output.with_suffix(args.output.suffix + ".partial")
    results: list[dict[str, object]] = []
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("context") != checkpoint_context:
            raise RuntimeError("audit checkpoint does not match the current policy")
        results = list(checkpoint.get("results", []))
    completed = {int(result["number"]) for result in results}

    pending = [row for row in candidates if int(row["pdes"]) not in completed]
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        future_rows = {
            executor.submit(_evaluate_body, int(row["pdes"])): row
            for row in pending
        }
        for future in as_completed(future_rows):
            row = future_rows[future]
            number = int(row["pdes"])
            result = future.result()
            completed.add(number)
            ordinal = len(completed)
            result.update({
                "sbdb_full_name": str(row["full_name"]).strip(),
                "sbdb_eccentricity": float(row["e"]),
                "sbdb_perihelion_au": float(row["q"]),
                "sbdb_semi_major_axis_au": float(row["a"]),
                "sbdb_period_days": float(row["per"]),
                "sbdb_class": str(row["class"]),
                "sbdb_orbit_id": str(row["orbit_id"]),
                "shard_index": body_to_shard[int(result["naif_id"])],
            })
            results.append(result)
            _checkpoint(checkpoint_path, results, checkpoint_context)
            print(
                f"[{ordinal:03d}/{len(candidates):03d}] {number:>7} "
                f"extrema={result['radial_extrema_detected']:>4} "
                f"radial={result['worst_radial_error']['error_km']:.6g} km "
                f"{'PASS' if result['passed'] else 'FAIL'}",
                flush=True,
            )
            time.sleep(args.throttle_seconds)

    results.sort(key=lambda result: float(result["sbdb_perihelion_au"]))
    failures = [result for result in results if not result["passed"]]
    failure_shards = sorted({int(result["shard_index"]) for result in failures})
    outer_count = len(admitted_numbers) - len(candidates)
    outer_bound = _outer_domain_bound()
    payload = {
        "schema": "moira.asteroid-type13-apsidal-audit/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete_catalog_partition",
        "governing_object": (
            "Sun-centered geometric radial extrema represented by a 10-day, "
            "seven-node Type-13 Hermite series"
        ),
        "admitted_universe": {
            "identity_path": str(IDENTITY_PATH.relative_to(ROOT)).replace("\\", "/"),
            "identity_sha256": _sha256(IDENTITY_PATH),
            "body_count": len(admitted_numbers),
            "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": _sha256(MANIFEST_PATH),
            "missing_perihelion_count": len(missing_admitted),
            "unbound_orbit_count": len(unbound_admitted),
        },
        "authority": {
            "source": "NASA/JPL Horizons VECTORS and JPL SBDB Query API",
            "sbdb_query_url": SBDB_QUERY_URL,
            "horizons_url": catalog_builder.HORIZONS_URL,
            "queries": {
                "direct_candidates": candidate_query,
                "missing_perihelion": missing_query,
                "unbound_orbits": unbound_query,
            },
        },
        "sampling": {
            "base_step_days": BASE_STEP_DAYS,
            "authority_step_days": AUDIT_STEP_DAYS,
            "window_size": WINDOW_SIZE,
            "same_start_stop_interval": True,
            "direct_cutoff_au": DIRECT_CUTOFF_AU,
            "shared_node_consistency_gate_km": SHARED_NODE_GATE_KM,
        },
        "acceptance_gate": {
            "distance_absolute_au": DISTANCE_GATE_AU,
            "distance_absolute_km": DISTANCE_GATE_KM,
            "origin": "pre-existing Stage 2 apsidal-passage distance gate",
        },
        "catalog_partition": {
            "direct_authority_body_count": len(candidates),
            "outer_invariant_body_count": outer_count,
            "partition_total": len(candidates) + outer_count,
        },
        "outer_domain_invariant": outer_bound,
        "direct_results": results,
        "repair_scope": {
            "body_count": len(failures),
            "shard_count": len(failure_shards),
            "shard_indices": failure_shards,
            "bodies": [
                {
                    "number": result["number"],
                    "naif_id": result["naif_id"],
                    "name": result["sbdb_full_name"],
                    "shard_index": result["shard_index"],
                    "worst_radial_error": result["worst_radial_error"],
                }
                for result in failures
            ],
        },
        "limitations": [
            "The direct branch validates every 5-day off-grid witness neighboring a radial-velocity sign crossing returned by Horizons over the catalog build interval.",
            "The outer branch is an invariant bound for bound Sun-dominated elliptic motion, not a direct Horizons replay of all 11,097 outer-domain bodies.",
            "This audit governs apsidal sampling; it is not a general all-epoch close-encounter position audit.",
        ],
    }
    if payload["catalog_partition"]["partition_total"] != len(admitted_numbers):
        raise RuntimeError("catalog partition is incomplete")
    if not outer_bound["passed"]:
        raise RuntimeError("outer-domain invariant does not pass the distance gate")
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checkpoint_path.unlink(missing_ok=True)
    print(
        f"DONE: {len(admitted_numbers)} partitioned, {len(candidates)} direct, "
        f"{len(failures)} failures in {len(failure_shards)} shards",
        flush=True,
    )


if __name__ == "__main__":
    main()
