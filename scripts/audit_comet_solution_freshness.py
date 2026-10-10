"""Fail-closed census of a comet catalog's JPL Horizons orbit solutions.

The Type-13 sampling certificate proves interpolation accuracy against the exact
Horizons replies used by the builder.  It cannot prove that JPL has not since
published a newer fitted orbit.  This audit queries the current object record
for every cataloged numbered comet and compares its ``JPL#...`` solution label
with the label retained in ``comet_master.json``.

The audit deliberately compares the ``source`` field from a one-epoch VECTORS
response with the same field retained by the catalog builder.  Horizons object
records expose a different ``soln ref.`` field for some legacy comets (for
example, ``DASTCOM`` versus ``SAO/1939``), so those fields are not interchangeable.

The output file is also an atomic checkpoint.  An interrupted run may resume
within ``--resume-max-age-hours``; use ``--restart`` to force a wholly fresh
census.  A completed report exits nonzero if any query failed or any solution
label differs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_comet_catalog  # noqa: E402


SCHEMA = "moira.comet-solution-freshness/v1"
DEFAULT_THROTTLE_SECONDS = 1.0
DEFAULT_RESUME_MAX_AGE_HOURS = 6.0
PROBE_EPOCH_JD_TDB = "2451545.0"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_current_solution(raw: str) -> str:
    """Parse the target-source identity retained by the catalog builder."""

    solution = build_comet_catalog._parse_solution(raw)
    if not solution:
        raise RuntimeError("Horizons VECTORS response did not declare a target source")
    return solution


def fetch_current_vector_header(number: int) -> str:
    """Fetch one current vector so Horizons returns its target-source field."""

    params = {
        "format": "text",
        "COMMAND": f"'DES={number}P;NOFRAG;CAP'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": "500@10",
        "TLIST": PROBE_EPOCH_JD_TDB,
        "OUT_UNITS": "KM-S",
        "VEC_TABLE": "2",
        "CSV_FORMAT": "YES",
        "TIME_TYPE": "TDB",
        "REF_SYSTEM": "ICRF",
        "REF_PLANE": "FRAME",
        "VEC_CORR": "NONE",
    }
    url = f"{build_comet_catalog.HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    return build_comet_catalog._read_request(url, timeout=60)


def _load_catalog_records(path: Path) -> tuple[str, list[dict[str, object]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("catalog master must contain a non-empty records list")
    numbers = [int(record["number"]) for record in records]
    if len(numbers) != len(set(numbers)):
        raise ValueError("catalog master contains duplicate comet numbers")
    missing = [number for number, record in zip(numbers, records) if not record.get("target_solution")]
    if missing:
        raise ValueError(f"catalog records lack target_solution: {missing[:10]}")
    return _sha256_file(path), sorted(records, key=lambda record: int(record["number"]))


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, indent=2)
            stream.write("\n")
        temporary.replace(path)
    except Exception:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        raise


def _new_report(
    *,
    catalog_path: Path,
    catalog_sha256: str,
    started: datetime,
    selected_numbers: list[int] | None,
) -> dict:
    return {
        "schema": SCHEMA,
        "authority": "NASA/JPL Horizons",
        "authority_url": build_comet_catalog.HORIZONS_URL,
        "query_policy": {
            "command_template": "DES={number}P;NOFRAG;CAP",
            "object_data": False,
            "make_ephemeris": True,
            "ephemeris_type": "VECTORS",
            "center": "500@10",
            "probe_epoch_jd_tdb": PROBE_EPOCH_JD_TDB,
            "comparison_field": "Target body name {source: ...}",
        },
        "catalog_master": str(catalog_path.resolve()),
        "catalog_master_sha256": catalog_sha256,
        "selected_numbers": selected_numbers,
        "audit_started_utc": _iso_utc(started),
        "audit_completed_utc": None,
        "completed": False,
        "records": [],
        "summary": None,
    }


def _load_resumable_report(
    output_path: Path,
    *,
    catalog_sha256: str,
    now: datetime,
    max_age: timedelta,
    selected_numbers: list[int] | None,
) -> dict | None:
    if not output_path.exists():
        return None
    try:
        report = json.loads(output_path.read_text(encoding="utf-8"))
        started = _parse_utc(report["audit_started_utc"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if report.get("schema") != SCHEMA:
        return None
    if report.get("catalog_master_sha256") != catalog_sha256:
        return None
    if report.get("selected_numbers") != selected_numbers:
        return None
    if now - started > max_age:
        return None
    return report


def audit_catalog(
    catalog_path: Path,
    output_path: Path,
    *,
    restart: bool = False,
    resume_max_age_hours: float = DEFAULT_RESUME_MAX_AGE_HOURS,
    throttle_seconds: float = DEFAULT_THROTTLE_SECONDS,
    fetch: Callable[[int], str] = fetch_current_vector_header,
    now: Callable[[], datetime] = _utc_now,
    sleep: Callable[[float], None] = time.sleep,
    numbers: set[int] | None = None,
) -> dict:
    """Run or resume a complete current-solution census."""

    if resume_max_age_hours <= 0:
        raise ValueError("resume_max_age_hours must be positive")
    if throttle_seconds < 0:
        raise ValueError("throttle_seconds must be non-negative")
    catalog_sha256, all_catalog_records = _load_catalog_records(catalog_path)
    selected_numbers = None if numbers is None else sorted(numbers)
    known_numbers = {int(record["number"]) for record in all_catalog_records}
    if numbers is not None:
        unknown = sorted(numbers - known_numbers)
        if unknown:
            raise ValueError(f"selected comet numbers are absent from catalog: {unknown}")
        if not numbers:
            raise ValueError("selected comet numbers must not be empty")
        catalog_records = [
            record
            for record in all_catalog_records
            if int(record["number"]) in numbers
        ]
    else:
        catalog_records = all_catalog_records
    started_now = now()
    report = None if restart else _load_resumable_report(
        output_path,
        catalog_sha256=catalog_sha256,
        now=started_now,
        max_age=timedelta(hours=resume_max_age_hours),
        selected_numbers=selected_numbers,
    )
    if report is None:
        report = _new_report(
            catalog_path=catalog_path,
            catalog_sha256=catalog_sha256,
            started=started_now,
            selected_numbers=selected_numbers,
        )
    prior = {
        int(record["number"]): record
        for record in report.get("records", [])
        if record.get("status") in {"match", "stale"}
    }
    results: list[dict[str, object]] = []
    total = len(catalog_records)
    for index, catalog_record in enumerate(catalog_records, start=1):
        number = int(catalog_record["number"])
        expected = str(catalog_record["target_solution"])
        if number in prior:
            result = prior[number]
            results.append(result)
            print(
                f"[{index:>3}/{total}] {number:>4}P {result['status'].upper()} (checkpoint)",
                flush=True,
            )
            continue
        try:
            raw = fetch(number)
            actual = parse_current_solution(raw)
            status = "match" if actual == expected else "stale"
            result = {
                "number": number,
                "name": catalog_record.get("name") or catalog_record.get("full_name"),
                "expected_target_solution": expected,
                "current_target_solution": actual,
                "status": status,
                "checked_utc": _iso_utc(now()),
                "response_sha256": _sha256_bytes(raw.encode("utf-8")),
                "response_byte_count": len(raw.encode("utf-8")),
            }
        except Exception as exc:  # noqa: BLE001
            result = {
                "number": number,
                "name": catalog_record.get("name") or catalog_record.get("full_name"),
                "expected_target_solution": expected,
                "current_target_solution": None,
                "status": "error",
                "checked_utc": _iso_utc(now()),
                "error": str(exc)[:500],
            }
        results.append(result)
        report["records"] = results
        report["completed"] = False
        report["audit_completed_utc"] = None
        report["summary"] = None
        _atomic_write_json(output_path, report)
        detail = ""
        if result["status"] == "stale":
            detail = f" {expected} -> {result['current_target_solution']}"
        elif result["status"] == "error":
            detail = f" {result['error']}"
        print(
            f"[{index:>3}/{total}] {number:>4}P {str(result['status']).upper()}{detail}",
            flush=True,
        )
        if index < total and throttle_seconds:
            sleep(throttle_seconds)

    status_counts = {
        status: sum(record["status"] == status for record in results)
        for status in ("match", "stale", "error")
    }
    report["records"] = results
    report["summary"] = {
        "catalog_records": len(all_catalog_records),
        "checked_records": total,
        **status_counts,
        "passed": status_counts["stale"] == 0 and status_counts["error"] == 0,
    }
    report["completed"] = True
    report["audit_completed_utc"] = _iso_utc(now())
    _atomic_write_json(output_path, report)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog_master", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--restart", action="store_true")
    parser.add_argument(
        "--number",
        action="append",
        type=int,
        dest="numbers",
        help="audit only this numbered periodic comet; repeatable",
    )
    parser.add_argument(
        "--resume-max-age-hours",
        type=float,
        default=DEFAULT_RESUME_MAX_AGE_HOURS,
    )
    parser.add_argument(
        "--throttle-seconds",
        type=float,
        default=DEFAULT_THROTTLE_SECONDS,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = audit_catalog(
        args.catalog_master,
        args.output,
        restart=args.restart,
        resume_max_age_hours=args.resume_max_age_hours,
        throttle_seconds=args.throttle_seconds,
        numbers=None if args.numbers is None else set(args.numbers),
    )
    summary = report["summary"]
    print(
        "DONE: "
        f"{summary['match']} match, {summary['stale']} stale, "
        f"{summary['error']} error",
        flush=True,
    )
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
