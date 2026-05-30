"""
Full Eclipse Catalog Comparison — all NASA fixture entries.

Runs every solar maximum, lunar maximum, modern validation gamma,
and search case from eclipse_nasa_reference.json through Moira's engine,
and prints a comprehensive markdown report.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moira.eclipse import EclipseCalculator

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eclipse_nasa_reference.json"
REPORT = Path(__file__).resolve().parent / "eclipse_report.md"

KIND_MAP_SOLAR = {"H": "hybrid", "T": "total", "A": "annular", "P": "partial"}
KIND_MAP_LUNAR = {"T": "total", "P": "partial", "N": "penumbral"}


def jd_to_iso(jd: float) -> str:
    """Convert JD to a readable ISO-ish string via EclipseCalculator helper."""
    calc = EclipseCalculator()
    data = calc.calculate_jd(jd)
    return data.datetime_utc.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(data, "datetime_utc") else f"JD {jd:.6f}"


def main() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calc = EclipseCalculator()
    import builtins
    _print = builtins.print
    out = open(REPORT, "w", encoding="utf-8")

    def print(*args, **kwargs):
        kwargs.pop("flush", None)
        kwargs["file"] = out
        _print(*args, **kwargs)
        out.flush()

    # ── Solar Maxima ──────────────────────────────────────────────
    print("## Solar Eclipse Maxima — Classification at NASA Catalog Instant\n")
    print("| # | NASA Date | Year | NASA Type | Moira Type | Match |")
    print("|--:|---|---:|---|---|---|")

    solar_ok = solar_fail = 0
    attr_map_solar = {"H": "is_hybrid", "T": "is_total", "A": "is_annular", "P": "is_partial"}

    for i, row in enumerate(fixture["solar_maxima"], 1):
        data = calc.calculate_jd(float(row["ut_jd"]))
        nasa_type = str(row["type"])
        expected_attr = attr_map_solar[nasa_type]

        # determine Moira's classification
        et = data.eclipse_type
        if data.is_solar_eclipse:
            if et.is_hybrid:
                moira_type = "hybrid"
            elif et.is_total:
                moira_type = "total"
            elif et.is_annular:
                moira_type = "annular"
            elif et.is_partial:
                moira_type = "partial"
            else:
                moira_type = "unknown"
        else:
            moira_type = "no eclipse"

        match = data.is_solar_eclipse and getattr(et, expected_attr)
        mark = "YES" if match else "**NO**"
        if match:
            solar_ok += 1
        else:
            solar_fail += 1

        print(f"| {i} | {row['date']} | {row['year']} | {KIND_MAP_SOLAR[nasa_type]} | {moira_type} | {mark} |")

    print(f"\nSolar: {solar_ok}/{solar_ok + solar_fail} match\n")

    # ── Lunar Maxima ──────────────────────────────────────────────
    print("## Lunar Eclipse Maxima — Classification at NASA Catalog Instant\n")
    print("| # | NASA Date | Year | NASA Type | Moira Type | Pen Mag | Umb Mag | Match |")
    print("|--:|---|---:|---|---|---:|---:|---|")

    lunar_ok = lunar_fail = 0

    for i, row in enumerate(fixture["lunar_maxima"], 1):
        data = calc.calculate_jd(float(row["ut_jd"]))
        eclipse_type = str(row["type"])
        et = data.eclipse_type

        if data.is_lunar_eclipse:
            if et.is_total:
                moira_type = "total"
            elif et.is_partial:
                moira_type = "partial"
            else:
                moira_type = "lunar-other"
        elif et.magnitude_penumbra > 0.0:
            moira_type = "penumbral"
        else:
            moira_type = "no eclipse"

        if eclipse_type == "T":
            ok = data.is_lunar_eclipse and et.is_total
        elif eclipse_type == "P":
            ok = data.is_lunar_eclipse and et.is_partial
        elif eclipse_type == "N":
            ok = (not data.is_lunar_eclipse) and et.magnitude_penumbra > 0.0
        else:
            ok = False

        mark = "YES" if ok else "**NO**"
        if ok:
            lunar_ok += 1
        else:
            lunar_fail += 1

        print(
            f"| {i} | {row['date']} | {row['year']} | {KIND_MAP_LUNAR[eclipse_type]} "
            f"| {moira_type} | {et.magnitude_penumbra:.4f} | {et.magnitude_umbral:.4f} | {mark} |"
        )

    print(f"\nLunar: {lunar_ok}/{lunar_ok + lunar_fail} match\n")

    # ── Modern Validation (gamma) ─────────────────────────────────
    print("## Modern Lunar Validation — Gamma Comparison\n")
    print("| # | Label | NASA gamma | Moira gamma | Delta |")
    print("|--:|---|---:|---:|---:|")

    for i, row in enumerate(fixture["lunar_modern_validation"], 1):
        analysis = calc.analyze_lunar_eclipse(
            float(row["ut_jd"]) - 5,
            kind="total",
            backward=False,
            mode="nasa_compat",
        )
        moira_gamma = analysis.gamma_earth_radii if analysis.gamma_earth_radii is not None else float("nan")
        nasa_gamma = float(row["gamma"])
        delta = moira_gamma - nasa_gamma
        print(f"| {i} | {row['label']} | {nasa_gamma:.4f} | {moira_gamma:.4f} | {delta:+.4f} |")

    print()

    # ── Search Cases ──────────────────────────────────────────────
    print("## Search Cases — Timing Comparison\n")
    print("### Solar Search\n")
    print("| Label | Kind | NASA JD (UT) | Moira JD (UT) | Residual (s) |")
    print("|---|---|---:|---:|---:|")

    for row in fixture["search_cases"]["solar"]:
        event = calc.next_solar_eclipse(float(row["seed_jd"]), kind=str(row["kind"]))
        expected = float(row["expected_ut_jd"])
        err_s = (event.jd_ut - expected) * 86400.0
        print(
            f"| {row['label']} | {row['kind']} | {expected:.9f} | {event.jd_ut:.9f} | {err_s:+.2f} |"
        )

    print("\n### Lunar Search (Native vs NASA-compat)\n")
    print("| Label | Kind | NASA JD (UT) | Native JD | Native residual (s) | Canon JD | Canon residual (s) |")
    print("|---|---|---:|---:|---:|---:|---:|")

    for row in fixture["search_cases"]["lunar"]:
        expected = float(row["expected_ut_jd"])
        kind = str(row["kind"])
        seed = float(row["seed_jd"])

        native = calc.next_lunar_eclipse(seed, kind=kind)
        canon = calc.next_lunar_eclipse_canon(seed, kind=kind)

        native_err = (native.jd_ut - expected) * 86400.0
        canon_err = (canon.jd_ut - expected) * 86400.0

        print(
            f"| {row['label']} | {kind} | {expected:.9f} "
            f"| {native.jd_ut:.9f} | {native_err:+.2f} "
            f"| {canon.jd_ut:.9f} | {canon_err:+.2f} |"
        )

    # ── Extended Search: walk every fixture entry ─────────────────
    print("\n## Extended Search — All Fixture Entries as Search Targets\n", flush=True)
    print("For each NASA catalog entry, seed Moira 40 days earlier and search forward.\n", flush=True)
    total_searches = len(fixture["solar_maxima"]) + len(fixture["lunar_maxima"])
    print(f"*Running {total_searches} eclipse searches — this will take a few minutes...*\n", flush=True)

    print("### All Solar Maxima (searched)\n")
    print("| # | Year | Type | NASA JD | Moira JD | Residual (s) | Moira Type | Match |")
    print("|--:|---:|---|---:|---:|---:|---|---|", flush=True)

    for i, row in enumerate(fixture["solar_maxima"], 1):
        _print(f"  searching solar {i}/{len(fixture['solar_maxima'])}...", end="\r", file=sys.stderr, flush=True)
        nasa_jd = float(row["ut_jd"])
        nasa_type = str(row["type"])
        kind = KIND_MAP_SOLAR[nasa_type]
        seed = nasa_jd - 40.0

        event = calc.next_solar_eclipse(seed, kind=kind)
        err_s = (event.jd_ut - nasa_jd) * 86400.0

        et = event.data.eclipse_type
        if event.data.is_solar_eclipse:
            if et.is_hybrid:
                m_type = "hybrid"
            elif et.is_total:
                m_type = "total"
            elif et.is_annular:
                m_type = "annular"
            elif et.is_partial:
                m_type = "partial"
            else:
                m_type = "unknown"
        else:
            m_type = "none"

        type_match = "YES" if m_type == kind else "**NO**"
        print(
            f"| {i} | {row['year']} | {kind} | {nasa_jd:.6f} | {event.jd_ut:.6f} "
            f"| {err_s:+.2f} | {m_type} | {type_match} |"
        )

    print("\n### All Lunar Maxima (searched)\n")
    print("| # | Year | Type | NASA JD | Native JD | Native res (s) | Canon JD | Canon res (s) | Type OK |")
    print("|--:|---:|---|---:|---:|---:|---:|---:|---|", flush=True)

    for i, row in enumerate(fixture["lunar_maxima"], 1):
        _print(f"  searching lunar {i}/{len(fixture['lunar_maxima'])}...", end="\r", file=sys.stderr, flush=True)
        nasa_jd = float(row["ut_jd"])
        eclipse_type = str(row["type"])
        kind = KIND_MAP_LUNAR[eclipse_type]
        seed = nasa_jd - 40.0

        native = calc.next_lunar_eclipse(seed, kind=kind)
        canon = calc.next_lunar_eclipse_canon(seed, kind=kind)

        native_err = (native.jd_ut - nasa_jd) * 86400.0
        canon_err = (canon.jd_ut - nasa_jd) * 86400.0

        et = native.data.eclipse_type
        if native.data.is_lunar_eclipse:
            if et.is_total:
                m_type = "total"
            elif et.is_partial:
                m_type = "partial"
            else:
                m_type = "other"
        elif et.magnitude_penumbra > 0.0:
            m_type = "penumbral"
        else:
            m_type = "none"

        type_ok = "YES" if m_type == kind else "**NO**"
        print(
            f"| {i} | {row['year']} | {kind} | {nasa_jd:.6f} "
            f"| {native.jd_ut:.6f} | {native_err:+.2f} "
            f"| {canon.jd_ut:.6f} | {canon_err:+.2f} | {type_ok} |"
        )

    _print("\n", file=sys.stderr, flush=True)
    print("\n---\n*Generated by scripts/full_eclipse_comparison.py*")
    out.close()
    _print(f"Report written to {REPORT}", flush=True)


if __name__ == "__main__":
    main()
