"""
Benchmark a fixed Swiss planetary reference slice.

This is the Swiss-side timing baseline corresponding to the same canonical
10-body, 24-date planetary workload we use for Moira's public benchmarks.
"""

from __future__ import annotations

import importlib
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ARTIFACT = Path("tests/artifacts/benchmarks/swiss_planetary_reference_benchmark.json")
REPEATS = 7
SAMPLE_DATES = 24
SWISS_SITE_PACKAGES = ROOT / ".venv-swiss-314" / "Lib" / "site-packages"
SWISS_EPHE_CANDIDATES = (
    Path(r"C:\Users\nilad\OneDrive\Desktop\Astrolog\ephem"),
    ROOT.parent / "Astrolog" / "ephem",
)
BODIES = [
    ("Sun", 0),
    ("Moon", 1),
    ("Mercury", 2),
    ("Venus", 3),
    ("Mars", 4),
    ("Jupiter", 5),
    ("Saturn", 6),
    ("Uranus", 7),
    ("Neptune", 8),
    ("Pluto", 9),
]
JD_START = 2415020.5  # 1900-01-01 UT
JD_END = 2488069.5    # 2100-01-01 UT


def _import_swisseph():
    if not SWISS_SITE_PACKAGES.exists():
        raise RuntimeError(f"Swiss site-packages not found: {SWISS_SITE_PACKAGES}")
    if str(SWISS_SITE_PACKAGES) not in sys.path:
        sys.path.insert(0, str(SWISS_SITE_PACKAGES))
    return importlib.import_module("swisseph")


def _swiss_ephe_path() -> Path:
    for candidate in SWISS_EPHE_CANDIDATES:
        if candidate.exists() and any(candidate.glob("se*.se1")):
            return candidate
    raise RuntimeError("Swiss ephemeris data path not found")


def _sample_jds() -> list[float]:
    step = (JD_END - JD_START) / (SAMPLE_DATES - 1)
    return [JD_START + i * step for i in range(SAMPLE_DATES)]


def _call_cases(swe, jds: list[float], flags: int) -> None:
    for jd_ut in jds:
        for _body_name, body_id in BODIES:
            swe.calc_ut(jd_ut, body_id, flags)


def _measure(swe, jds: list[float], flags: int) -> float:
    start = time.perf_counter()
    _call_cases(swe, jds, flags)
    return time.perf_counter() - start


def main() -> None:
    swe = _import_swisseph()
    ephe_path = _swiss_ephe_path()
    swe.set_ephe_path(str(ephe_path))
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    jds = _sample_jds()

    runs: list[float] = []
    for _ in range(REPEATS):
        runs.append(_measure(swe, jds, flags))

    payload = {
        "phase": "swiss_planetary_reference_benchmark",
        "engine": "Swiss Ephemeris",
        "module_file": str(Path(swe.__file__).resolve()),
        "module_version": getattr(swe, "__version__", "unknown"),
        "ephe_path": str(ephe_path),
        "flags": ["FLG_SWIEPH", "FLG_SPEED"],
        "repeat_count": REPEATS,
        "body_count": len(BODIES),
        "jd_count": SAMPLE_DATES,
        "calls_per_run": len(BODIES) * SAMPLE_DATES,
        "best_seconds": min(runs),
        "median_seconds": statistics.median(runs),
        "runs_seconds": runs,
        "jds": jds,
        "bodies": [body_name for body_name, _body_id in BODIES],
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
