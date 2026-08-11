"""Acquire checksum-bound JPL source tables for the broad event oracle.

The exact engine receipt is used only to center bounded source queries.  JPL
Horizons owns planetary and solar geometry and planetary apparent photometry;
the offline oracle independently derives event roots from the acquired rows.
This networked acquisition tool is never imported by Moira at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_visibility_phase7_source_acquisition_spec_v1.json"
)
ADMISSION_SPEC = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_visibility_phase7_broad_oracle_matrix_v1.json"
)
ACQUISITION_SPEC_SHA256 = (
    "ba061013c6e6258475baab4442b072c82c887aabc840cc19f5b0126542eb9323"
)
HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
TARGET_COMMANDS = {
    "Mars": "499",
    "Jupiter": "599",
    "Saturn": "699",
}
QUERY_HALF_WIDTH_DAYS = 4.0 / 24.0


class AcquisitionError(RuntimeError):
    """Raised when an external source response is incomplete or ambiguous."""


def _json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise AcquisitionError(f"{label} must be an object")
    return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_acquisition_spec(
    spec_path: Path,
    spec: dict[str, Any],
) -> None:
    if _sha256_bytes(spec_path.read_bytes()) != ACQUISITION_SPEC_SHA256:
        raise AcquisitionError("source acquisition specification differs")
    admitted = _json_object(ADMISSION_SPEC, "admitted oracle matrix")
    acquisition_keys = (
        "schema",
        "status",
        "selection_policy",
        "sites",
        "cases",
    )
    if tuple(spec) != acquisition_keys or any(
        spec[key] != admitted.get(key) for key in acquisition_keys
    ):
        raise AcquisitionError(
            "source acquisition specification and admitted matrix differ"
        )


def _quoted(value: str) -> str:
    return f"'{value}'"


def _request_parameters(
    *,
    command: str,
    site: dict[str, Any],
    start_jd: float,
    stop_jd: float,
    target_fields: bool,
) -> dict[str, str]:
    longitude = float(site["longitude_deg"])
    latitude = float(site["latitude_deg"])
    elevation_km = float(site["elevation_m"]) / 1000.0
    quantities = "4,9,14,15,43" if target_fields else "4"
    return {
        "format": "json",
        "COMMAND": _quoted(command),
        "OBJ_DATA": _quoted("NO"),
        "MAKE_EPHEM": _quoted("YES"),
        "EPHEM_TYPE": _quoted("OBSERVER"),
        "CENTER": _quoted("coord@399"),
        "COORD_TYPE": _quoted("GEODETIC"),
        "SITE_COORD": _quoted(
            f"{longitude:.8f},{latitude:.8f},{elevation_km:.6f}"
        ),
        "START_TIME": _quoted(f"JD{start_jd:.12f}"),
        "STOP_TIME": _quoted(f"JD{stop_jd:.12f}"),
        "STEP_SIZE": _quoted("1 min"),
        "QUANTITIES": _quoted(quantities),
        "REF_SYSTEM": _quoted("ICRF"),
        "APPARENT": _quoted("AIRLESS"),
        "TIME_TYPE": _quoted("UT"),
        "TIME_DIGITS": _quoted("SECONDS"),
        "CAL_FORMAT": _quoted("BOTH"),
        "CAL_TYPE": _quoted("GREGORIAN"),
        "CSV_FORMAT": _quoted("YES"),
        "ANG_FORMAT": _quoted("DEG"),
        "EXTRA_PREC": _quoted("YES"),
        "SKIP_DAYLT": _quoted("NO"),
    }


def _validate_response(
    payload: bytes,
    *,
    expected_command: str,
) -> tuple[int, str]:
    try:
        response = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError("Horizons response is not UTF-8 JSON") from exc
    if not isinstance(response, dict) or response.get("error"):
        raise AcquisitionError(
            f"Horizons returned an error: {response.get('error')!r}"
        )
    signature = response.get("signature")
    result = response.get("result")
    if (
        not isinstance(signature, dict)
        or signature.get("source") != "NASA/JPL Horizons API"
        or not isinstance(result, str)
        or "$$SOE" not in result
        or "$$EOE" not in result
        or "Atmos refraction: NO (AIRLESS)" not in result
        or "Center body name: Earth (399)" not in result
    ):
        raise AcquisitionError("Horizons response contract differs")
    target_id = f"({expected_command})"
    if expected_command != "10" and target_id not in result:
        raise AcquisitionError("Horizons target identity differs")
    lines = result.splitlines()
    start = lines.index("$$SOE") + 1
    stop = lines.index("$$EOE")
    row_count = sum(1 for line in lines[start:stop] if line.strip())
    if row_count < 470:
        raise AcquisitionError(
            f"Horizons response has only {row_count} source rows"
        )
    version = str(signature.get("version", ""))
    if not version:
        raise AcquisitionError("Horizons API version is missing")
    return row_count, version


def _fetch(
    *,
    parameters: dict[str, str],
    expected_command: str,
) -> tuple[bytes, int, str, str]:
    url = HORIZONS_API + "?" + urllib.parse.urlencode(parameters)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Moira-Phase7-Broad-Oracle/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
    except OSError as exc:
        raise AcquisitionError("Horizons request failed") from exc
    row_count, api_version = _validate_response(
        payload,
        expected_command=expected_command,
    )
    return payload, row_count, api_version, url


def _load_engine_results(paths: tuple[Path, ...]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for path in paths:
        receipt = _json_object(path, "exact engine receipt")
        if (
            receipt.get("schema")
            != "moira.physical-heliacal-visibility-oracle-window-discovery/v1"
            or receipt.get("exact_public_search_policy") is not True
        ):
            raise AcquisitionError(
                f"engine receipt is not exact-policy output: {path}"
            )
        for result in receipt.get("results", ()):  # later receipts override
            if not isinstance(result, dict):
                raise AcquisitionError("engine receipt result differs")
            results[str(result["case_id"])] = result
    return results


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--engine-receipt",
        action="append",
        required=True,
        type=Path,
        dest="engine_receipts",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    spec_path = arguments.spec.resolve()
    spec = _json_object(spec_path, "oracle matrix specification")
    if (
        spec.get("schema")
        != "moira.physical-heliacal-visibility-broad-oracle-matrix-spec/v1"
    ):
        raise AcquisitionError("oracle matrix specification identity differs")
    _validate_acquisition_spec(spec_path, spec)
    engine_results = _load_engine_results(
        tuple(path.resolve() for path in arguments.engine_receipts)
    )
    cases = {case["case_id"]: case for case in spec["cases"]}
    evaluated = {
        case_id: result
        for case_id, result in engine_results.items()
        if case_id in cases and result.get("status") == "evaluated"
    }
    if len(evaluated) != 12:
        raise AcquisitionError(
            f"expected 12 evaluated matrix cells, received {len(evaluated)}"
        )
    output_root = arguments.output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise AcquisitionError(
            f"output root must be absent or empty: {output_root}"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    acquired_at = datetime.now(timezone.utc).isoformat()
    files: dict[str, dict[str, Any]] = {}
    for case_id in sorted(evaluated):
        case = cases[case_id]
        result = evaluated[case_id]
        site = spec["sites"][case["site_id"]]
        event_jd = float(result["event_jd_ut"])
        day_delta = int(result["comparison_observation_day_key"]) - int(
            result["observation_day_key"]
        )
        if day_delta not in {-1, 1}:
            raise AcquisitionError(
                f"{case_id} comparison day is not adjacent"
            )
        centers = {
            "candidate": event_jd,
            "guard": event_jd + float(day_delta),
        }
        commands = {"sun": "10"}
        if case["target"] != "Sirius":
            commands["target"] = TARGET_COMMANDS[case["target"]]
        for day_role, center_jd in centers.items():
            for body_role, command in commands.items():
                source_id = f"{case_id}:{day_role}:{body_role}"
                filename = (
                    f"{case_id}--{day_role}--{body_role}--1min.json"
                )
                parameters = _request_parameters(
                    command=command,
                    site=site,
                    start_jd=center_jd - QUERY_HALF_WIDTH_DAYS,
                    stop_jd=center_jd + QUERY_HALF_WIDTH_DAYS,
                    target_fields=body_role == "target",
                )
                payload, row_count, api_version, url = _fetch(
                    parameters=parameters,
                    expected_command=command,
                )
                path = output_root / filename
                path.write_bytes(payload)
                files[source_id] = {
                    "filename": filename,
                    "bytes": len(payload),
                    "sha256": _sha256_bytes(payload),
                    "row_count": row_count,
                    "api_version": api_version,
                    "authority": "NASA/JPL Horizons",
                    "request_url": url,
                    "request_parameters": parameters,
                    "case_id": case_id,
                    "target": case["target"],
                    "phase": case["phase"],
                    "site_id": case["site_id"],
                    "day_role": day_role,
                    "body_role": body_role,
                    "center_jd_ut": center_jd,
                }
                print(
                    f"acquired {source_id}: {row_count} rows",
                    flush=True,
                )
                time.sleep(0.15)
    manifest = {
        "schema": "moira.physical-heliacal-visibility-broad-oracle-sources/v1",
        "status": "complete_checksum_bound_external_sources",
        "acquired_at_utc": acquired_at,
        "authority": "NASA/JPL Horizons",
        "api_documentation": (
            "https://ssd-api.jpl.nasa.gov/doc/horizons.html"
        ),
        "manual": "https://ssd.jpl.nasa.gov/horizons/manual.html",
        "spec_sha256": _sha256_bytes(spec_path.read_bytes()),
        "query_half_width_hours": QUERY_HALF_WIDTH_DAYS * 24.0,
        "evaluated_case_count": len(evaluated),
        "files": files,
    }
    manifest_path = output_root / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
