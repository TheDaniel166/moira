"""
Lunar cartography parity against the NASA Five Millennium Lunar Eclipse Catalog.

Oracle and Parity Law receipt
-----------------------------
- Comparison object  : moira.lunar_cartography.lunar_eclipse_cartography
                       (native shadow-axis minimum, default mode of the
                       underlying EclipseCalculator.analyze_lunar_eclipse)
- Authority          : NASA Five Millennium Catalog of Lunar Eclipses
                       (5MKLEcatalog.txt), curated into
                       tests/fixtures/eclipse_nasa_reference.json under
                       "lunar_modern_validation".
- Date range         : 2000-2022 (six total lunar eclipses in modern era)
- Tested event class : total lunar eclipses
- Tolerances:
    * Eclipse-type classification : exact ("T" -> "total")
    * Greatest-eclipse UT residual : <= 120.0 s
    * Sublunar bounds              : lat in [-90, 90], lon in [-180, 180]
    * Sublunar / Sun-side invariant: sublunar latitude opposite-hemisphere
                                     of approximate solar declination

Why 120 s and not 60 s
----------------------
The 60 s and 0.013 R_earth envelopes used in test_lunar_nasa_compat_reference.py
apply to the *canon* path (next_lunar_eclipse_canon /
analyze_lunar_eclipse(..., mode="nasa_compat")), which targets NASA's published
gamma-minimum greatest-eclipse instant directly.

lunar_eclipse_cartography uses the *native* shadow-axis-minimum path. Per
moira.wiki/ECLIPSE_CATALOG_COMPARISON.md and
test_native_path_remains_distinct_from_nasa_compat_for_problem_case, the native
and canon objectives are doctrinally distinct and disagree by >= 30 s on the
2003-11-09 problem case. The 120 s envelope was set after the empirical sweep
below recorded a native-mode worst-case residual of ~104 s on 2003-11-09, with
~16 s of margin on top.

Live measurements at the time this test was authored (2026-05-04, DE441,
native mode):
  2000-01-21 total :  +71.6 s
  2003-05-16 total :  +41.4 s
  2003-11-09 total : +104.0 s   (documented native/canon divergence)
  2004-05-04 total :  +61.3 s
  2011-06-15 total :  +74.1 s
  2022-05-16 total :  +74.2 s
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira.eclipse import EclipseCalculator
from moira.lunar_cartography import LunarCartographyResult, lunar_eclipse_cartography
from moira.planets import planet_at
from moira.constants import Body


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"
)
NATIVE_TIMING_ENVELOPE_S = 120.0


def _load_modern_total_cases() -> list[dict]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [row for row in fixture["lunar_modern_validation"] if row["type"] == "T"]


def _approx_solar_declination_deg(calc: EclipseCalculator, jd_ut: float) -> float:
    """Equatorial declination of the Sun, computed in the same frame the
    cartography uses for sublunar latitude (cartesian / equatorial xyz)."""
    sun = planet_at(Body.SUN, jd_ut, reader=calc._reader, frame="cartesian")
    r = math.sqrt(sun.x * sun.x + sun.y * sun.y + sun.z * sun.z)
    return math.degrees(math.asin(sun.z / r))


@pytest.mark.slow
@pytest.mark.parametrize("case", _load_modern_total_cases(), ids=lambda c: c["label"])
def test_lunar_cartography_matches_nasa_modern_total_eclipses(case: dict) -> None:
    calc = EclipseCalculator()
    nasa_ut = float(case["ut_jd"])

    result = lunar_eclipse_cartography(
        calc,
        nasa_ut - 5.0,
        kind="total",
        backend="cpu",
        time_samples=9,
    )

    assert isinstance(result, LunarCartographyResult)
    assert result.eclipse_type == "total", case["label"]

    err_seconds = abs(result.event_jd_ut - nasa_ut) * 86400.0
    assert err_seconds <= NATIVE_TIMING_ENVELOPE_S, (
        f"{case['label']}: native timing residual {err_seconds:.3f}s "
        f"exceeds {NATIVE_TIMING_ENVELOPE_S}s envelope"
    )

    assert len(result.besselian_samples) >= 1
    assert len(result.sample_jds_ut) >= 1
    assert result.window_start_jd_ut < result.event_jd_ut < result.window_end_jd_ut

    nearest = min(
        result.besselian_samples,
        key=lambda s: abs(s.jd_ut - result.event_jd_ut),
    )
    assert -90.0 <= nearest.sublunar_lat <= 90.0, case["label"]
    assert -180.0 <= nearest.sublunar_lon <= 180.0, case["label"]
    assert nearest.umbral_radius_earth_radii > 0.0
    assert nearest.penumbral_radius_earth_radii > nearest.umbral_radius_earth_radii

    sun_dec = _approx_solar_declination_deg(calc, result.event_jd_ut)
    assert nearest.sublunar_lat * sun_dec <= 0.0 or abs(sun_dec) < 1.0, (
        f"{case['label']}: sublunar lat {nearest.sublunar_lat:.2f} should oppose "
        f"solar declination {sun_dec:.2f} (anti-solar geometry at lunar eclipse)"
    )


@pytest.mark.slow
def test_lunar_cartography_total_band_present_for_canonical_2000_total() -> None:
    """For the 2000-01-21 total eclipse, totality structures must be populated.

    This anchors a single canonical case to a stronger structural contract than
    the parametrized parity sweep above: when the cartography classifies a
    result as "total", the totality band's polygon must be non-empty so a
    downstream consumer can render the totality footprint.
    """
    calc = EclipseCalculator()
    cases = _load_modern_total_cases()
    canonical = next(c for c in cases if c["label"].startswith("2000-01-21"))

    result = lunar_eclipse_cartography(
        calc,
        float(canonical["ut_jd"]) - 5.0,
        kind="total",
        backend="cpu",
        time_samples=9,
    )

    assert result.eclipse_type == "total"
    assert len(result.total_band.polygon) > 0, (
        "total eclipse classification implies a non-empty totality polygon"
    )
    assert len(result.partial_band.polygon) > 0, (
        "total eclipse implies a non-empty partial band as well"
    )
    assert len(result.penumbral_band.polygon) > 0, (
        "total eclipse implies a non-empty penumbral band"
    )
