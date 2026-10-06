"""Offline, reader-bound PAC 1948 SE ingress comparison; JSON to stdout.

Run with the project runtime and MOIRA_NO_DOWNLOAD=1. The source transcription
and its precision/acceptance policy are versioned in tests/fixtures. This tool
does not download kernels, fit ayanamsa constants, or change runtime policy.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import moira
from moira import moira_native
from moira._kernel_paths import find_planetary_kernel
from moira.julian import delta_t_from_jd, jd_from_datetime, utc_to_ut1
from moira.lunar_month import lunar_month_at
from moira.panchanga import sankranti_at
from moira.spk_reader import SpkReader, use_reader_override


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    fixture = root / "tests/fixtures/pac_1948_solar_ingresses.json"
    reference = json.loads(fixture.read_text(encoding="utf-8"))
    kernel = find_planetary_kernel()
    if kernel is None:
        raise RuntimeError("An installed planetary kernel is required; downloads are disabled")
    reader = SpkReader(kernel)
    ist = timezone(timedelta(hours=5, minutes=30))
    rows = []
    for case in reference["cases"]:
        published = datetime.fromisoformat(case["ist"]).replace(tzinfo=ist)
        jd = utc_to_ut1(jd_from_datetime(published))
        result = lunar_month_at(jd, reader=reader)
        event, = [event for context in (result.previous_lunation,
            result.amanta_lunation, result.next_lunation)
            for event in context.ingresses
            if event.target_degrees == case["target_degrees"]
            and abs(event.jd_ut1-jd) < 0.5]
        with use_reader_override(reader):
            sankranti, = sankranti_at(jd-0.5, jd+0.5)
        rows.append({
            **case,
            "published_jd_ut1": jd,
            "delta_t_seconds": delta_t_from_jd(jd),
            "boundary": asdict(event),
            "lunar_month_residual_seconds": (event.jd_ut1-jd)*86400,
            "sankranti_residual_seconds": (sankranti.jd-jd)*86400,
            "solver_difference_seconds": (event.jd_ut1-sankranti.jd)*86400,
        })
    limit = reference["source"]["acceptance_seconds"]
    accepted = all(abs(row[key]) <= limit for row in rows for key in (
        "lunar_month_residual_seconds", "sankranti_residual_seconds"))
    consistent = all(abs(row["solver_difference_seconds"]) <= 0.2 for row in rows)
    print(json.dumps({
        "evidence_class": "bounded_institutional_authority_comparison",
        "source": reference["source"],
        "planetary_kernel": str(kernel.resolve()),
        "moira_version": moira.__version__,
        "native_backend": moira_native.__backend_file__,
        "reader_binding": "explicit_installed_reader",
        "longitude": "apparent_geocentric_ecliptic_of_date",
        "ayanamsa_system": "Lahiri",
        "sidereal_mode": "true",
        "solver_tolerance_seconds": 0.1,
        "sample_count": len(rows),
        "maximum_absolute_residual_seconds": max(abs(row[key]) for row in rows
            for key in ("lunar_month_residual_seconds", "sankranti_residual_seconds")),
        "authority_comparison_passed": accepted,
        "solver_consistency_passed": consistent,
        "cases": rows,
    }, indent=2))
    return 0 if accepted and consistent else 1


if __name__ == "__main__":
    raise SystemExit(main())
