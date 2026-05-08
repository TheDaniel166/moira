from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from moira.constants import Body

_ROOT = Path(__file__).resolve().parents[2]
_SWISS_SITE_PACKAGES = _ROOT / ".venv-swiss-314" / "Lib" / "site-packages"
_SWISS_EPHE_CANDIDATES = (
    Path(r"C:\Users\nilad\OneDrive\Desktop\Astrolog\ephem"),
    _ROOT.parent / "Astrolog" / "ephem",
)

_BODIES = [
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
]

_SWISS_BODY_IDS = {
    Body.SUN: 0,
    Body.MOON: 1,
    Body.MERCURY: 2,
    Body.VENUS: 3,
    Body.MARS: 4,
    Body.JUPITER: 5,
    Body.SATURN: 6,
    Body.URANUS: 7,
    Body.NEPTUNE: 8,
    Body.PLUTO: 9,
}

_JD_START = 2415020.5  # 1900-01-01 UT
_JD_END = 2488069.5    # 2100-01-01 UT
_JD_COUNT = 24


def _import_swisseph():
    if not _SWISS_SITE_PACKAGES.exists():
        pytest.skip(f"Swiss site-packages not found: {_SWISS_SITE_PACKAGES}")

    if str(_SWISS_SITE_PACKAGES) not in sys.path:
        sys.path.insert(0, str(_SWISS_SITE_PACKAGES))

    try:
        return importlib.import_module("swisseph")
    except ImportError as exc:
        pytest.skip(f"Swiss import unavailable: {exc}")


def _swiss_ephe_path() -> Path:
    for candidate in _SWISS_EPHE_CANDIDATES:
        if candidate.exists() and any(candidate.glob("se*.se1")):
            return candidate
    pytest.skip("Swiss ephemeris data path not found")


def _sample_jds() -> list[float]:
    step = (_JD_END - _JD_START) / (_JD_COUNT - 1)
    return [_JD_START + i * step for i in range(_JD_COUNT)]


@pytest.mark.requires_ephemeris
def test_swiss_planetary_reference_snapshot(snapshot) -> None:
    swe = _import_swisseph()
    ephe_path = _swiss_ephe_path()
    swe.set_ephe_path(str(ephe_path))
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    cases: list[dict[str, object]] = []
    for jd_ut in _sample_jds():
        for body in _BODIES:
            xx, retflag = swe.calc_ut(jd_ut, _SWISS_BODY_IDS[body], flags)
            cases.append(
                {
                    "jd_ut": round(jd_ut, 9),
                    "body": body,
                    "longitude": round(float(xx[0]), 12),
                    "latitude": round(float(xx[1]), 12),
                    "distance_au": round(float(xx[2]), 12),
                    "speed_longitude": round(float(xx[3]), 12),
                    "retflag": int(retflag),
                }
            )

    value = {
        "engine": "Swiss Ephemeris",
        "module_file": str(Path(swe.__file__).resolve()),
        "module_version": getattr(swe, "__version__", "unknown"),
        "ephe_path": str(ephe_path),
        "flags": ["FLG_SWIEPH", "FLG_SPEED"],
        "jd_start_ut": _JD_START,
        "jd_end_ut": _JD_END,
        "jd_count": _JD_COUNT,
        "body_count": len(_BODIES),
        "cases": cases,
    }

    snapshot("swiss_planetary_reference_state", value)
