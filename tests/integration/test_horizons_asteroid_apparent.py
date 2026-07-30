"""
tests/integration/test_horizons_asteroid_apparent.py

Validate moira.asteroids.asteroid_at() against JPL Horizons reference
geocentric ecliptic positions.

Bodies covered
--------------
  Chiron  (2002060) — highest-priority centaur; widely used in astrology
  Pholus  (2005145) — second centaur
  Ceres   (2000001) — classical asteroid / dwarf planet
  Pallas  (2000002) — classical asteroid
  Juno    (2000003) — classical asteroid
  Vesta   (2000004) — classical asteroid
  Ixion   (2028978) — TNO
  Quaoar  (2050000) — TNO / dwarf planet
  Varuna  (2020000) — TNO
  Orcus   (2090482) — TNO / dwarf planet
  ... plus main-belt, centaurs, and minor bodies (see fixture)

Fixture
-------
  tests/fixtures/horizons_asteroid_reference.json
  Provenance and source semantics are recorded in the fixture metadata.

Thresholds
----------
  Asteroids route through the same apparent-place pipeline as planets
  (light-time → deflection → aberration → frame-bias → rotation).
  Thresholds mirror the planetary standard (0.75 arcsec) wherever
  kernel accuracy allows it, with explicit exceptions only for bodies
  whose orbital solutions are demonstrably kernel-accuracy limited.

  0.5 arcseconds  — default for observer-referenced bodies.
                    Matches the accuracy of the shared planetary pipeline;
                    all main-belt asteroids and centaurs are sub-0.20".

  1.5 arcseconds  — Varuna, Quaoar.
                    Mid-range TNOs in the manifest-backed Type-13 catalog;
                    sub-arcsecond near
                    J2000 but up to ~0.8" at the 1960 epoch due to orbit
                    solution uncertainty, not pipeline error.

  5.0 arcseconds  — Orcus, Ixion.
                    Distant TNOs whose manifest-backed solutions reach
                    ~3.5" error at the 1960 epoch. This is the kernel
                    accuracy floor, not a pipeline deficiency.

  New bodies added to the fixture without a named exception default to
  0.5 arcseconds — the same demand applied to planets.

Markers
-------
  integration, requires_ephemeris, slow
  No live network call is made — the fixture must be pre-generated with
  the recorded Horizons query semantics.
"""

import json
from pathlib import Path

import pytest

from moira.asteroids import asteroid_at

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "horizons_asteroid_reference.json"

# Default: same demand as planets — the shared pipeline should hold here.
_THRESHOLD_DEFAULT_ARCSEC = 0.5

# Explicit per-body exceptions, each annotated with the reason.
# Reason must be "kernel accuracy" (orbit solution), never "pipeline error".
_BODY_THRESHOLD_ARCSEC: dict[str, float] = {
    # Distant TNOs — manifest-backed solution reaches ~3.5" at 1960 epoch.
    "Orcus": 5.0,
    "Ixion": 5.0,
    # Mid-range TNOs — up to ~0.8" at 1960 epoch due to orbit uncertainty.
    "Varuna": 1.5,
    "Quaoar": 1.5,
}


def _load_cases() -> list[dict]:
    if not _FIXTURE.exists():
        return []
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return [c for c in data.get("cases", []) if "error" not in c]


def _angle_diff_arcsec(a: float, b: float) -> float:
    """Signed angular difference (a − b) in arcseconds, wrapped to (−180°, +180°)."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d * 3600.0


def _threshold_for(case: dict) -> float:
    """Return the per-body arcsecond threshold for this fixture case."""
    return _BODY_THRESHOLD_ARCSEC.get(case["body"], _THRESHOLD_DEFAULT_ARCSEC)


_CASES = _load_cases()
_CASE_IDS = [f"{c['body']}-{c['label']}" for c in _CASES]


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.skipif(not _FIXTURE.exists(), reason=(
    "tracked horizons_asteroid_reference.json fixture is missing"
))
@pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
def test_asteroid_at_matches_horizons_ecliptic(
    case: dict,
    small_body_reader_pool,
) -> None:
    """
    moira.asteroid_at() ecliptic longitude and latitude must agree with the
    Horizons reference to within the per-body threshold defined in
    _BODY_THRESHOLD_ARCSEC (default 0.5").

    The threshold is kernel-accuracy limited only for four distant TNOs
    (Orcus, Ixion, Varuna, Quaoar).  All other bodies — 55 of them — are
    held to 0.5", matching the planetary pipeline standard.
    """
    body      = case["body"]
    jd_ut     = case["jd_ut"]
    ref_lon   = case["ecl_lon_deg"]
    ref_lat   = case["ecl_lat_deg"]
    threshold = _threshold_for(case)

    result = asteroid_at(
        body,
        jd_ut,
        reader=small_body_reader_pool,
    )

    lon_err_arcsec = _angle_diff_arcsec(result.longitude, ref_lon)
    lat_err_arcsec = (result.latitude - ref_lat) * 3600.0

    src = case.get("ref_source", "observer")
    assert abs(lon_err_arcsec) <= threshold, (
        f"{body} @ {case['label']} [{src}]: longitude error {lon_err_arcsec:+.3f}\" "
        f"exceeds {threshold}\" threshold  "
        f"(moira={result.longitude:.6f}°, ref={ref_lon:.6f}°)"
    )
    assert abs(lat_err_arcsec) <= threshold, (
        f"{body} @ {case['label']} [{src}]: latitude error {lat_err_arcsec:+.3f}\" "
        f"exceeds {threshold}\" threshold  "
        f"(moira={result.latitude:.6f}°, ref={ref_lat:.6f}°)"
    )
