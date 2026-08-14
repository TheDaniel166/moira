"""Build the pre-release 25-body wheel asteroid catalog from JPL Horizons.

Reuses the unified catalog Horizons fetch, sampling window, and Type-13
writer. Refuses to emit a shard unless every frozen roster body fetches
and the Horizons name contains the frozen name as a whole token.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._spk_body_kernel import SmallBodyKernel  # noqa: E402
from moira._wheel_asteroid_catalog import (  # noqa: E402
    CATALOG_ID,
    TARGETS_PATH,
    load_targets,
)
from moira.daf_writer import write_spk_type13  # noqa: E402

_UNIFIED_PATH = Path(__file__).resolve().parent / "build_unified_asteroid_catalog.py"
_unified_spec = importlib.util.spec_from_file_location(
    "build_unified_asteroid_catalog",
    _UNIFIED_PATH,
)
if _unified_spec is None or _unified_spec.loader is None:
    raise RuntimeError(f"cannot load unified builder: {_UNIFIED_PATH}")
unified = importlib.util.module_from_spec(_unified_spec)
_unified_spec.loader.exec_module(unified)

_fetch_body = unified._fetch_body
_verify = unified._verify
WINDOW = unified.WINDOW
STEP_DAYS = unified.STEP_DAYS
WINDOW_SIZE = unified.WINDOW_SIZE
CENTER = unified.CENTER
FRAME = unified.FRAME
THROTTLE_S = unified.THROTTLE_S
HORIZONS_URL = unified.HORIZONS_URL

_KERNEL_NAME = "asteroid_shard_000.bsp"
_METADATA_NAME = "asteroid_shard_000.metadata.json"
_LOCIFN = "MOIRA WHEEL ASTEROID CATALOG"
_SOURCE = "MOIRA WHEEL ASTEROID CATALOG (JPL Horizons)"
_WRITABLE_KEYS = (
    "naif_id",
    "name",
    "center",
    "frame",
    "states",
    "epochs_jd",
    "window_size",
)


def _horizons_name_contains_frozen(horizons_name: str, frozen_name: str) -> bool:
    # Token match: "NotCeres" must not satisfy frozen "Ceres".
    needle = frozen_name.casefold()
    if not needle:
        return False
    tokens = horizons_name.casefold().replace("/", " ").replace(",", " ").split()
    return needle in tokens


def _coverage_exceptions(records: list[dict]) -> list[dict]:
    exceptions: list[dict] = []
    for record in records:
        if "coverage_policy" in record:
            provenance = record["coverage_provenance"]
            exceptions.append(
                {
                    "naif_id": record["naif_id"],
                    "name": record["name"],
                    "start_date": record["start"],
                    "end_date": record["stop"],
                    "policy": record["coverage_policy"],
                    "authority": provenance["authority"],
                    "orbit_id": provenance["orbit_id"],
                    "solution_date": provenance["solution_date"],
                }
            )
        elif record.get("clamped"):
            exceptions.append(
                {
                    "naif_id": record["naif_id"],
                    "name": record["name"],
                    "start_date": record["start"],
                    "end_date": record["stop"],
                    "policy": "jpl_horizons_ephemeris_availability",
                    "authority": "JPL Horizons API",
                    "note": (
                        "conservative full-year bounds parsed from the Horizons "
                        "ephemeris-availability response"
                    ),
                }
            )
    return exceptions


def build_pre_release(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    targets = load_targets()
    fetched: list[dict] = []
    records: list[dict] = []
    failures: list[dict] = []
    mismatches: list[str] = []

    for index, target in enumerate(targets):
        number = int(target["number"])
        frozen_name = str(target["name"])
        started = time.perf_counter()
        try:
            body = _fetch_body(number)
        except Exception as exc:  # noqa: BLE001
            failures.append({"number": number, "error": str(exc)[:200]})
            print(f"  [FAIL] {number} {frozen_name}: {str(exc)[:70]}", flush=True)
        else:
            elapsed = time.perf_counter() - started
            horizons_name = str(body.get("name", ""))
            if not _horizons_name_contains_frozen(horizons_name, frozen_name):
                mismatches.append(frozen_name)
                print(
                    f"  [NAME] {number} {frozen_name}: Horizons {horizons_name!r}",
                    flush=True,
                )
            else:
                fetched.append(body)
                records.append(
                    {
                        "number": number,
                        "naif_id": body["naif_id"],
                        "name": body["name"],
                        "nodes": len(body["epochs_jd"]),
                        "clamped": body["clamped"],
                        "start": body["start"],
                        "stop": body["stop"],
                        "fetch_s": round(elapsed, 1),
                        **(
                            {
                                "coverage_policy": body["coverage_policy"],
                                "coverage_provenance": body["coverage_provenance"],
                            }
                            if "coverage_policy" in body
                            else {}
                        ),
                    }
                )
                tag = (
                    f"CLAMP {body['start'][:4]}-{body['stop'][:4]}"
                    if body["clamped"]
                    else "full"
                )
                print(
                    f"  [OK] {number:>7} {body['name']:<18} "
                    f"nodes={len(body['epochs_jd']):>6} {tag:>13} {elapsed:4.1f}s",
                    flush=True,
                )
        if index + 1 < len(targets) and THROTTLE_S > 0:
            time.sleep(THROTTLE_S)

    if failures:
        failed_numbers = ", ".join(str(item["number"]) for item in failures)
        raise RuntimeError(f"Horizons fetch failed for MPC numbers: {failed_numbers}")
    if mismatches:
        raise RuntimeError(
            "Horizons name does not contain frozen name: " + ", ".join(mismatches)
        )
    if len(fetched) != 25 or len(records) != 25:
        raise RuntimeError(
            f"refusing short catalog: fetched {len(fetched)} of 25 roster bodies"
        )

    kernel_path = output_dir / _KERNEL_NAME
    writable = [{key: body[key] for key in _WRITABLE_KEYS} for body in fetched]
    write_spk_type13(kernel_path, bodies=writable, locifn=_LOCIFN)

    kernel = SmallBodyKernel(kernel_path)
    try:
        for body, record in zip(fetched, records):
            record["max_node_error_km"] = _verify(
                kernel,
                body["naif_id"],
                body["epochs_jd"],
                body["states"],
            )
    finally:
        kernel.close()

    metadata = {
        "shard": 0,
        "kernel": kernel_path.name,
        "kernel_bytes": kernel_path.stat().st_size,
        "window": WINDOW,
        "step_days": STEP_DAYS,
        "window_size": WINDOW_SIZE,
        "records": records,
        "failures": failures,
        "naif_map": {record["name"]: record["naif_id"] for record in records},
    }
    (output_dir / _METADATA_NAME).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    naif_ids = [record["naif_id"] for record in records]
    manifest = {
        "manifest_schema": "moira.small-body-catalog/v1",
        "catalog_id": CATALOG_ID,
        "source": _SOURCE,
        "provenance": {
            "artifact_author": "Moira",
            "artifact_format": "DAF/SPK Type 13",
            "trajectory_source": "JPL Horizons VECTORS",
            "horizons_api": HORIZONS_URL,
            "center": "Sun (500@10)",
            "reference_plane": "FRAME",
            "units": "km and km/s",
            "timescale": "JDTDB",
        },
        "coverage": {
            "start_date": WINDOW[0],
            "end_date": WINDOW[1],
            "note": "default DE441 small-body span; see coverage_exceptions",
        },
        "coverage_exceptions": _coverage_exceptions(records),
        "sampling": {"step_days": STEP_DAYS, "window_size": WINDOW_SIZE},
        "body_count": 25,
        "shard_count": 1,
        "shards": [
            {
                "index": 0,
                "path": _KERNEL_NAME,
                "body_count": 25,
                "bodies": naif_ids,
            }
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    shutil.copy2(TARGETS_PATH, output_dir / "targets.json")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build" / "asteroids-wheel-src",
        help="pre-release output directory (default: build/asteroids-wheel-src)",
    )
    args = parser.parse_args()
    written = build_pre_release(args.out)
    print(f"pre-release catalog written to {written}", flush=True)


if __name__ == "__main__":
    main()
