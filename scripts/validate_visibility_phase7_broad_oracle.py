"""Reproduce the Phase 7 broad physical-event oracle without Moira.

The twelve timed-event cells use checksum-bound NASA/JPL Horizons geometry
and photometry, plus checksum-bound Hipparcos astrometry for Sirius, evaluated
through the independent visibility-pack equations.  Four additional matrix
cells bind typed engine no-event/domain behavior but make no independent event
time claim.  This module imports neither Moira nor its event solver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import validate_visibility_phase3_event_goldens as phase3


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_visibility_phase7_broad_oracle_matrix_v1.json"
)
DEFAULT_GOLDEN = (
    REPO_ROOT
    / "tests"
    / "golden"
    / "physical_visibility_phase7_broad_oracle.json"
)
DEFAULT_PHASE3_GOLDEN = (
    REPO_ROOT
    / "tests"
    / "golden"
    / "physical_visibility_phase3_events.json"
)
CERTIFICATE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)


class BroadOracleError(RuntimeError):
    """Raised when broad-oracle evidence is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class WindowGeometry:
    """Independent target-boundary ownership for one observation side."""

    status: str
    reason: str | None
    target_boundary_jd_ut: float
    solar_horizon_jd_ut: float
    target_minus_solar_boundary_minutes: float


def _object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BroadOracleError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise BroadOracleError(f"{label} must be an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_spec(spec: dict[str, Any]) -> None:
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-broad-oracle-matrix-spec/v1"
        or spec.get("status")
        != "predeclared_complete_admitted_target_phase_matrix"
    ):
        raise BroadOracleError("broad-oracle matrix identity differs")
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
        raise BroadOracleError("broad-oracle matrix is not a full product")
    release_gate = spec["release_gate"]
    if (
        release_gate["timed_event_oracle_case_count"] != 12
        or release_gate["typed_negative_regression_case_count"] != 4
        or release_gate["external_source_grid_step_seconds"] != 60.0
        or release_gate["maximum_engine_oracle_difference_seconds"]
        != 60.0
        or release_gate["negative_cells_are_not_event_time_oracles"]
        is not True
    ):
        raise BroadOracleError("broad-oracle release gate differs")


def _load_engine_results(
    paths: tuple[Path, ...],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for path in paths:
        receipt = _object(path, "exact engine receipt")
        if (
            receipt.get("schema")
            != "moira.physical-heliacal-visibility-oracle-window-discovery/v1"
            or receipt.get("exact_public_search_policy") is not True
            or receipt.get("role")
            != "source_query_bounds_only_not_oracle_truth"
        ):
            raise BroadOracleError(
                f"engine receipt is not exact-policy output: {path}"
            )
        for result in receipt.get("results", ()):
            if not isinstance(result, dict):
                raise BroadOracleError("engine receipt result differs")
            results[str(result["case_id"])] = dict(result)
    return results


def _validate_astrometry(
    phase3_golden: dict[str, Any],
    *,
    hipparcos_query: Path,
    hipparcos_readme: Path,
) -> dict[str, Any]:
    external = phase3_golden["external_sources"]
    declaration = external["hipparcos"]
    phase3._verify_file(
        hipparcos_query,
        declaration["query"],
        "Hipparcos Sirius query",
    )
    phase3._verify_file(
        hipparcos_readme,
        declaration["readme"],
        "Hipparcos ReadMe",
    )
    astrometry = phase3._hipparcos_sirius(hipparcos_query)
    admitted = dict(declaration["admitted_astrometry"])
    catalog_not_used = admitted.pop("catalog_v_magnitude_not_used")
    radial_velocity = admitted.pop("radial_velocity_assumption_km_per_s")
    source = dict(astrometry)
    catalog_magnitude = source.pop("catalog_v_magnitude")
    if (
        source != admitted
        or radial_velocity != 0.0
        or catalog_not_used is not True
        or catalog_magnitude != -1.44
    ):
        raise BroadOracleError("Hipparcos astrometry receipt differs")
    phase3._validate_toolchain(external["astropy_erfa"])
    return astrometry


def _bennett_apparent_altitude_deg(
    true_altitude_deg: float,
    *,
    pressure_hpa: float,
    temperature_c: float,
) -> float:
    altitude = max(float(true_altitude_deg), -5.0)
    theta = altitude + 7.31 / (altitude + 4.4)
    refraction_arcminutes = 1.0 / math.tan(math.radians(theta))
    scaled = (
        refraction_arcminutes
        * (pressure_hpa / 1010.0)
        * (283.0 / (273.0 + temperature_c))
    )
    return true_altitude_deg + scaled / 60.0


def _scalar_crossings(
    rows: tuple[phase3.ObserverRow, ...],
    value: Callable[[phase3.ObserverRow], float],
    *,
    direction: str,
) -> tuple[float, ...]:
    if direction not in {"negative_to_positive", "positive_to_negative"}:
        raise BroadOracleError("unsupported scalar crossing direction")
    roots: list[float] = []
    for left, right in zip(rows, rows[1:]):
        left_value = value(left)
        right_value = value(right)
        opening = left_value < 0.0 <= right_value
        closing = left_value >= 0.0 > right_value
        if (
            direction == "negative_to_positive"
            and opening
            or direction == "positive_to_negative"
            and closing
        ):
            fraction = -left_value / (right_value - left_value)
            roots.append(
                left.jd_ut + fraction * (right.jd_ut - left.jd_ut)
            )
    return tuple(roots)


def _window_geometry(
    target_rows: tuple[phase3.ObserverRow, ...],
    solar_rows: tuple[phase3.ObserverRow, ...],
    *,
    phase: str,
    policy: dict[str, Any],
) -> WindowGeometry:
    morning = phase.startswith("morning_")
    rising = phase.endswith("_rising")
    solar_direction = (
        "negative_to_positive" if morning else "positive_to_negative"
    )
    target_direction = (
        "negative_to_positive" if rising else "positive_to_negative"
    )
    pressure = float(policy["refraction_pressure_hpa"])
    temperature = float(policy["refraction_temperature_c"])
    solar_roots = _scalar_crossings(
        solar_rows,
        lambda row: _bennett_apparent_altitude_deg(
            row.altitude_deg,
            pressure_hpa=pressure,
            temperature_c=temperature,
        ),
        direction=solar_direction,
    )
    target_floor = float(policy["target_true_altitude_floor_deg"])
    target_roots = _scalar_crossings(
        target_rows,
        lambda row: row.altitude_deg - target_floor,
        direction=target_direction,
    )
    if len(solar_roots) != 1 or len(target_roots) != 1:
        raise BroadOracleError(
            "external source window does not contain exactly one requested "
            "solar and target boundary"
        )
    solar_root = solar_roots[0]
    target_root = target_roots[0]
    delta_minutes = (target_root - solar_root) * 1440.0
    qualifies = target_root < solar_root if morning else target_root > solar_root
    return WindowGeometry(
        status="qualifies" if qualifies else "does_not_qualify",
        reason=(
            None
            if qualifies
            else "target_boundary_outside_requested_solar_side"
        ),
        target_boundary_jd_ut=target_root,
        solar_horizon_jd_ut=solar_root,
        target_minus_solar_boundary_minutes=delta_minutes,
    )


def _crossing_in_window(
    rows: tuple[phase3.MarginRow, ...],
    *,
    phase: str,
    geometry: WindowGeometry,
) -> tuple[phase3.MarginRow, phase3.MarginRow, float] | None:
    direction = (
        "negative_to_positive"
        if phase.endswith("_rising")
        else "positive_to_negative"
    )
    try:
        left, right, root = phase3._crossing(
            rows,
            direction=direction,
        )
    except phase3.ValidationError:
        return None
    morning = phase.startswith("morning_")
    rising = phase.endswith("_rising")
    within_solar_side = (
        root <= geometry.solar_horizon_jd_ut
        if morning
        else root >= geometry.solar_horizon_jd_ut
    )
    within_target_visibility = (
        root >= geometry.target_boundary_jd_ut
        if rising
        else root <= geometry.target_boundary_jd_ut
    )
    if not within_solar_side or not within_target_visibility:
        return None
    return left, right, root


def _source_receipt_subset(receipt: dict[str, Any]) -> dict[str, Any]:
    parameters = receipt["request_parameters"]
    return {
        "filename": receipt["filename"],
        "bytes": receipt["bytes"],
        "sha256": receipt["sha256"],
        "row_count": receipt["row_count"],
        "api_version": receipt["api_version"],
        "authority": receipt["authority"],
        "COMMAND": parameters["COMMAND"].strip("'"),
        "QUANTITIES": parameters["QUANTITIES"].strip("'"),
        "SITE_COORD": parameters["SITE_COORD"].strip("'"),
        "START_TIME": parameters["START_TIME"].strip("'"),
        "STOP_TIME": parameters["STOP_TIME"].strip("'"),
        "STEP_SIZE": parameters["STEP_SIZE"].strip("'"),
        "APPARENT": parameters["APPARENT"].strip("'"),
        "REF_SYSTEM": parameters["REF_SYSTEM"].strip("'"),
        "TIME_TYPE": parameters["TIME_TYPE"].strip("'"),
    }


def _source_pairs(
    case: dict[str, Any],
    *,
    role: str,
    spec: dict[str, Any],
    source_manifest: dict[str, Any],
    source_root: Path,
    astrometry: dict[str, Any],
) -> tuple[
    tuple[tuple[phase3.ObserverRow, phase3.ObserverRow], ...],
    tuple[str, ...],
]:
    case_id = str(case["case_id"])
    files = source_manifest["files"]
    solar_id = f"{case_id}:{role}:sun"
    try:
        solar_receipt = files[solar_id]
    except KeyError as exc:
        raise BroadOracleError(f"missing source {solar_id}") from exc
    solar_path = source_root / solar_receipt["filename"]
    phase3._verify_file(solar_path, solar_receipt, solar_id)
    solar_rows = phase3._horizons_rows(
        solar_path,
        target_fields=False,
    )
    source_ids = [solar_id]
    if case["target"] == "Sirius":
        site = spec["sites"][case["site_id"]]
        target_rows = phase3._sirius_rows(
            solar_rows,
            astrometry=astrometry,
            latitude_deg=float(site["latitude_deg"]),
            longitude_deg=float(site["longitude_deg"]),
        )
    else:
        target_id = f"{case_id}:{role}:target"
        try:
            target_receipt = files[target_id]
        except KeyError as exc:
            raise BroadOracleError(f"missing source {target_id}") from exc
        target_path = source_root / target_receipt["filename"]
        phase3._verify_file(target_path, target_receipt, target_id)
        quantities = target_receipt["request_parameters"][
            "QUANTITIES"
        ].strip("'")
        target_rows = phase3._horizons_rows(
            target_path,
            target_fields=True,
            quantities=quantities,
        )
        source_ids.insert(0, target_id)
    return phase3._paired_rows(target_rows, solar_rows), tuple(source_ids)


def derive(
    *,
    spec_path: Path,
    phase3_golden_path: Path,
    pack_path: Path,
    source_manifest_path: Path,
    source_root: Path,
    hipparcos_query: Path,
    hipparcos_readme: Path,
    engine_receipt_paths: tuple[Path, ...],
) -> dict[str, Any]:
    """Derive the complete source-owned broad-oracle receipt."""

    spec = _object(spec_path, "broad-oracle specification")
    _validate_spec(spec)
    phase3_golden = _object(phase3_golden_path, "Phase 3 event golden")
    physical_policy = spec["physical_policy"]
    exact_pack = physical_policy["exact_data_pack"]
    if exact_pack != phase3_golden["exact_data_pack"]:
        raise BroadOracleError("broad and Phase 3 pack identities differ")
    pack = phase3.IndependentVisibilityPack(
        pack_path,
        exact_pack["manifest_sha256"],
    )
    astrometry = _validate_astrometry(
        phase3_golden,
        hipparcos_query=hipparcos_query,
        hipparcos_readme=hipparcos_readme,
    )
    source_manifest = _object(
        source_manifest_path,
        "broad-oracle source manifest",
    )
    release_gate = spec["release_gate"]
    if (
        source_manifest.get("schema")
        != "moira.physical-heliacal-visibility-broad-oracle-sources/v1"
        or source_manifest.get("status")
        != "complete_checksum_bound_external_sources"
        or source_manifest.get("evaluated_case_count")
        != release_gate["timed_event_oracle_case_count"]
        or source_manifest.get("spec_sha256")
        != release_gate["source_acquisition_spec_sha256"]
        or source_manifest.get("query_half_width_hours")
        != release_gate["source_query_half_width_hours"]
    ):
        raise BroadOracleError("broad-oracle source manifest differs")
    engine_results = _load_engine_results(engine_receipt_paths)
    cases = tuple(spec["cases"])
    case_ids = {str(case["case_id"]) for case in cases}
    if set(engine_results) != case_ids:
        raise BroadOracleError("exact engine results do not cover the matrix")

    background = physical_policy["background"]
    timed_count = 0
    negative_count = 0
    result_cases: list[dict[str, Any]] = []
    used_source_ids: set[str] = set()
    for case in cases:
        case_id = str(case["case_id"])
        engine = engine_results[case_id]
        for key in ("target", "phase", "site_id", "search_start_utc"):
            if engine.get(key) != case[key]:
                raise BroadOracleError(f"{case_id} engine metadata differs")
        if engine.get("search_window_days") != case["search_window_days"]:
            raise BroadOracleError(f"{case_id} engine window differs")
        base = {
            **case,
            "latitude_deg": spec["sites"][case["site_id"]][
                "latitude_deg"
            ],
            "longitude_deg": spec["sites"][case["site_id"]][
                "longitude_deg"
            ],
        }
        if engine.get("status") != "evaluated":
            negative_count += 1
            if (
                engine.get("status") not in {"not_found", "not_evaluable"}
                or not engine.get("reason")
                or engine.get("event_jd_ut") is not None
                or engine.get("comparison_day_status") is not None
            ):
                raise BroadOracleError(
                    f"{case_id} typed negative receipt differs"
                )
            result_cases.append(
                {
                    **base,
                    "validation_class": "typed_engine_negative_regression",
                    "independent_event_time_claimed": False,
                    "captured_engine_result": engine,
                }
            )
            continue

        timed_count += 1
        candidate_pairs, candidate_sources = _source_pairs(
            case,
            role="candidate",
            spec=spec,
            source_manifest=source_manifest,
            source_root=source_root,
            astrometry=astrometry,
        )
        guard_pairs, guard_sources = _source_pairs(
            case,
            role="guard",
            spec=spec,
            source_manifest=source_manifest,
            source_root=source_root,
            astrometry=astrometry,
        )
        used_source_ids.update(candidate_sources)
        used_source_ids.update(guard_sources)
        candidate_geometry = _window_geometry(
            tuple(pair[0] for pair in candidate_pairs),
            tuple(pair[1] for pair in candidate_pairs),
            phase=str(case["phase"]),
            policy=physical_policy,
        )
        guard_geometry = _window_geometry(
            tuple(pair[0] for pair in guard_pairs),
            tuple(pair[1] for pair in guard_pairs),
            phase=str(case["phase"]),
            policy=physical_policy,
        )
        if candidate_geometry.status != "qualifies":
            raise BroadOracleError(
                f"{case_id} candidate target boundary is not phase-owned"
            )
        candidate_margins = phase3._in_domain_margins(
            pack,
            target=str(case["target"]),
            pairs=candidate_pairs,
            background=background,
        )
        guard_margins = phase3._in_domain_margins(
            pack,
            target=str(case["target"]),
            pairs=guard_pairs,
            background=background,
        )
        crossing = _crossing_in_window(
            candidate_margins,
            phase=str(case["phase"]),
            geometry=candidate_geometry,
        )
        if crossing is None:
            raise BroadOracleError(
                f"{case_id} independent candidate crossing is missing"
            )
        left, right, root = crossing
        guard_crossing = (
            None
            if guard_geometry.status != "qualifies"
            else _crossing_in_window(
                guard_margins,
                phase=str(case["phase"]),
                geometry=guard_geometry,
            )
        )
        if guard_crossing is not None:
            raise BroadOracleError(
                f"{case_id} independent guard day still qualifies"
            )
        if engine.get("comparison_day_status") != "does_not_qualify":
            raise BroadOracleError(
                f"{case_id} engine guard-day status differs"
            )
        residual_seconds = abs(float(engine["event_jd_ut"]) - root) * 86400.0
        maximum_seconds = float(
            release_gate["maximum_engine_oracle_difference_seconds"]
        )
        if residual_seconds > maximum_seconds:
            raise BroadOracleError(
                f"{case_id} engine/oracle residual is {residual_seconds} seconds"
            )
        result_cases.append(
            {
                **base,
                "validation_class": "independent_timed_event_oracle",
                "independent_event_time_claimed": True,
                "candidate_sources": list(candidate_sources),
                "guard_sources": list(guard_sources),
                "independent_oracle": {
                    "algorithm_id": (
                        "external_airless_geometry_photometry_plus_"
                        "independent_pack_equations_and_phase_window_v1"
                    ),
                    "crossing_direction": (
                        "negative_to_positive"
                        if str(case["phase"]).endswith("_rising")
                        else "positive_to_negative"
                    ),
                    "candidate_window_geometry": {
                        "status": candidate_geometry.status,
                        "target_boundary_jd_ut": (
                            candidate_geometry.target_boundary_jd_ut
                        ),
                        "solar_horizon_jd_ut": (
                            candidate_geometry.solar_horizon_jd_ut
                        ),
                        "target_minus_solar_boundary_minutes": (
                            candidate_geometry
                            .target_minus_solar_boundary_minutes
                        ),
                    },
                    "guard_day_status": "does_not_qualify",
                    "guard_day_basis": (
                        guard_geometry.reason
                        or "visibility_margin_crossing_missing"
                    ),
                    "guard_window_geometry": {
                        "status": guard_geometry.status,
                        "target_boundary_jd_ut": (
                            guard_geometry.target_boundary_jd_ut
                        ),
                        "solar_horizon_jd_ut": (
                            guard_geometry.solar_horizon_jd_ut
                        ),
                        "target_minus_solar_boundary_minutes": (
                            guard_geometry
                            .target_minus_solar_boundary_minutes
                        ),
                    },
                    "crossing_bracket_jd_ut": [left.jd_ut, right.jd_ut],
                    "crossing_bracket_margin_magnitude": [
                        left.margin_magnitude,
                        right.margin_magnitude,
                    ],
                    "event_jd_ut": root,
                    "oracle_reproduction_tolerance_seconds": release_gate[
                        "oracle_reproduction_tolerance_seconds"
                    ],
                },
                "captured_engine_result": engine,
                "absolute_engine_oracle_difference_seconds": (
                    residual_seconds
                ),
                "maximum_engine_oracle_difference_seconds": maximum_seconds,
            }
        )

    if (
        timed_count != release_gate["timed_event_oracle_case_count"]
        or negative_count
        != release_gate["typed_negative_regression_case_count"]
    ):
        raise BroadOracleError("broad-oracle outcome counts differ")
    manifest_source_ids = set(source_manifest["files"])
    if used_source_ids != manifest_source_ids or len(used_source_ids) != 40:
        raise BroadOracleError("external source file coverage differs")
    source_files = {
        source_id: _source_receipt_subset(
            source_manifest["files"][source_id]
        )
        for source_id in sorted(used_source_ids)
    }
    external = phase3_golden["external_sources"]
    return {
        "schema": "moira.physical-heliacal-visibility-phase7-broad-oracle/v1",
        "status": "independent_broad_event_and_typed_negative_validation",
        "admission_date": spec["admission_date"],
        "matrix_spec": {
            "schema": spec["schema"],
            "sha256": _sha256(spec_path),
        },
        "exact_data_pack": exact_pack,
        "policy": physical_policy,
        "required_engine_contract": {
            "event_time_semantics": "visibility_margin_zero",
            "boundary_source": "visibility_margin",
            "crossing_completeness_state": (
                "certified_lipschitz_zero_enclosure"
            ),
            "crossing_certificate_source_sha256": CERTIFICATE_SHA256,
            "unresolved_certificate_interval_count": 0,
        },
        "external_sources": {
            "jpl_horizons": {
                "authority": source_manifest["authority"],
                "api_documentation": source_manifest["api_documentation"],
                "manual": source_manifest["manual"],
                "source_manifest_sha256": _sha256(source_manifest_path),
                "source_acquisition_spec_sha256": source_manifest[
                    "spec_sha256"
                ],
                "files": source_files,
            },
            "hipparcos": external["hipparcos"],
            "astropy_erfa": external["astropy_erfa"],
        },
        "coverage": {
            "required_targets": spec["selection_policy"][
                "required_targets"
            ],
            "required_phases": spec["selection_policy"]["required_phases"],
            "matrix_cell_count": len(cases),
            "independent_timed_event_oracle_count": timed_count,
            "typed_engine_negative_regression_count": negative_count,
            "external_source_file_count": len(used_source_ids),
            "normalized_captured_engine_results_sha256": (
                _canonical_sha256(engine_results)
            ),
        },
        "cases": result_cases,
        "limitations": [
            "one_minute_external_ephemeris_sampling_with_linear_margin_root_interpolation",
            "four_negative_matrix_cells_are_typed_engine_regressions_not_independent_event_time_oracles",
            "jpl_planetary_apparent_magnitudes_are_rounded_source_fields",
            "jpl_saturn_sub_latitudes_are_planetodetic_external_geometry",
            "sirius_radial_velocity_is_zero_for_the_astrometric_propagation",
            "subjective_observer_and_real_atmosphere_uncertainty_are_not_probabilistic_confidence",
            "validation_does_not_admit_mercury_or_venus_physical_events",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--phase3-golden",
        type=Path,
        default=DEFAULT_PHASE3_GOLDEN,
    )
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--hipparcos-query", type=Path, required=True)
    parser.add_argument("--hipparcos-readme", type=Path, required=True)
    parser.add_argument(
        "--engine-receipt",
        action="append",
        required=True,
        type=Path,
        dest="engine_receipts",
    )
    parser.add_argument(
        "--emit-derived",
        action="store_true",
        help="print the derived golden instead of comparing it",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        derived = derive(
            spec_path=arguments.spec.resolve(),
            phase3_golden_path=arguments.phase3_golden.resolve(),
            pack_path=arguments.pack.resolve(),
            source_manifest_path=arguments.source_manifest.resolve(),
            source_root=arguments.source_root.resolve(),
            hipparcos_query=arguments.hipparcos_query.resolve(),
            hipparcos_readme=arguments.hipparcos_readme.resolve(),
            engine_receipt_paths=tuple(
                path.resolve() for path in arguments.engine_receipts
            ),
        )
        if arguments.emit_derived:
            print(json.dumps(derived, indent=2, sort_keys=True))
            return 0
        expected = _object(arguments.golden.resolve(), "Phase 7 golden")
        if expected != derived:
            raise BroadOracleError("derived Phase 7 golden differs")
    except (
        BroadOracleError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        phase3.ValidationError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    residuals = [
        case["absolute_engine_oracle_difference_seconds"]
        for case in derived["cases"]
        if case["independent_event_time_claimed"]
    ]
    print(
        json.dumps(
            {
                "status": "accepted",
                "golden_sha256": _sha256(arguments.golden.resolve()),
                "timed_event_oracle_count": len(residuals),
                "typed_negative_regression_count": 4,
                "maximum_absolute_difference_seconds": max(residuals),
                "network_used": False,
                "moira_or_event_solver_imported": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
