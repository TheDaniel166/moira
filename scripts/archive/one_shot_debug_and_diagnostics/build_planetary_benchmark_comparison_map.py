"""
Build a unified comparison map for the current planetary benchmark surfaces.

This reads the existing Swiss benchmark artifact plus the current Moira
`planet_at(...)` and `all_planets_at(...)` benchmark artifacts and emits one
comparison ledger for direct judgement.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SWISS_ARTIFACT = ROOT / "tests" / "artifacts" / "benchmarks" / "swiss_planetary_reference_benchmark.json"
PLANET_AT_ARTIFACT = ROOT / "tests" / "artifacts" / "benchmarks" / "native_phase2_planet_at.json"
ALL_PLANETS_ARTIFACT = ROOT / "tests" / "artifacts" / "benchmarks" / "native_phase2_all_planets.json"
OUTPUT_ARTIFACT = ROOT / "tests" / "artifacts" / "benchmarks" / "planetary_benchmark_comparison_map.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ratio(lhs: float, rhs: float) -> float:
    return lhs / rhs


def _surface_row(
    *,
    surface: str,
    mode: str,
    calls_per_run: int,
    bodies_per_call: int,
    swiss_best: float,
    swiss_median: float,
    moira_python_best: float,
    moira_python_median: float,
    moira_native_best: float,
    moira_native_median: float,
) -> dict[str, float | int | str]:
    return {
        "surface": surface,
        "mode": mode,
        "calls_per_run": calls_per_run,
        "bodies_per_call": bodies_per_call,
        "moira_python_best_seconds": moira_python_best,
        "moira_python_median_seconds": moira_python_median,
        "moira_native_best_seconds": moira_native_best,
        "moira_native_median_seconds": moira_native_median,
        "swiss_best_seconds": swiss_best,
        "swiss_median_seconds": swiss_median,
        "moira_native_vs_swiss_best_ratio": _ratio(moira_native_best, swiss_best),
        "moira_native_vs_swiss_median_ratio": _ratio(moira_native_median, swiss_median),
        "moira_python_vs_swiss_best_ratio": _ratio(moira_python_best, swiss_best),
        "moira_python_vs_swiss_median_ratio": _ratio(moira_python_median, swiss_median),
        "moira_native_vs_python_best_ratio": _ratio(moira_native_best, moira_python_best),
        "moira_native_vs_python_median_ratio": _ratio(moira_native_median, moira_python_median),
        "moira_native_speedup_over_python_best": _ratio(moira_python_best, moira_native_best),
        "moira_native_speedup_over_python_median": _ratio(moira_python_median, moira_native_median),
    }


def main() -> None:
    swiss = _load(SWISS_ARTIFACT)
    planet_at = _load(PLANET_AT_ARTIFACT)
    all_planets = _load(ALL_PLANETS_ARTIFACT)

    swiss_best = float(swiss["best_seconds"])
    swiss_median = float(swiss["median_seconds"])

    planet_at_rows = []
    for fn in planet_at["functions"]:
        planet_at_rows.append(
            _surface_row(
                surface="planet_at",
                mode=str(fn["name"]).removeprefix("planet_at_"),
                calls_per_run=int(fn["calls_per_run"]),
                bodies_per_call=1,
                swiss_best=swiss_best,
                swiss_median=swiss_median,
                moira_python_best=float(fn["python_best_seconds"]),
                moira_python_median=float(fn["python_median_seconds"]),
                moira_native_best=float(fn["native_best_seconds"]),
                moira_native_median=float(fn["native_median_seconds"]),
            )
        )

    all_planets_rows = []
    for fn in all_planets["functions"]:
        all_planets_rows.append(
            _surface_row(
                surface="all_planets_at",
                mode=str(fn["name"]).removeprefix("all_planets_at_"),
                calls_per_run=int(fn["calls_per_run"]),
                bodies_per_call=int(fn["bodies_per_call"]),
                swiss_best=swiss_best,
                swiss_median=swiss_median,
                moira_python_best=float(fn["python_best_seconds"]),
                moira_python_median=float(fn["python_median_seconds"]),
                moira_native_best=float(fn["native_best_seconds"]),
                moira_native_median=float(fn["native_median_seconds"]),
            )
        )

    payload = {
        "phase": "planetary_benchmark_comparison_map",
        "source_artifacts": {
            "swiss": str(SWISS_ARTIFACT.relative_to(ROOT)),
            "planet_at": str(PLANET_AT_ARTIFACT.relative_to(ROOT)),
            "all_planets_at": str(ALL_PLANETS_ARTIFACT.relative_to(ROOT)),
        },
        "workload_alignment": {
            "body_count": int(swiss["body_count"]),
            "jd_count": int(swiss["jd_count"]),
            "swiss_calls_per_run": int(swiss["calls_per_run"]),
            "body_set": swiss["bodies"],
        },
        "swiss_reference": {
            "engine": swiss["engine"],
            "best_seconds": swiss_best,
            "median_seconds": swiss_median,
            "flags": swiss["flags"],
        },
        "surfaces": planet_at_rows + all_planets_rows,
    }

    OUTPUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
