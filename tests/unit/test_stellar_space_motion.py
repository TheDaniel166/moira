"""Stage 1 of the fixed-star pipeline: explicit catalog epoch and frame.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Sections
2-3. Authority for propagation from a non-J2000 epoch: ERFA ``pmsafe``
(rigorous straight-line space motion). The native ``FixedStarEvaluator`` is the
admitted counterpart; its parity here is a native/Python differential, not an
external authority.
"""

from __future__ import annotations

import csv
import math

import pytest

import moira.stars as stars
from moira._stellar_space_motion import astrometric_direction

J2000 = 2451545.0
J2016 = 2457389.0  # Gaia DR3 reference epoch, J2016.0 TDB
# Barnard's Star, Gaia-like values at J2016.0 (synthetic test inputs).
BARNARD = dict(ra_deg=269.448502, dec_deg=4.739420, pmra=-801.551, pmdec=10362.394,
               parallax=546.9759, rv=-110.6)


def _angle_arcsec(u, v):
    dot = sum(a * b for a, b in zip(u, v))
    cross = math.sqrt(sum(c * c for c in (
        u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])))
    return math.degrees(math.atan2(cross, dot)) * 3600.0


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


@pytest.mark.parametrize("jd_tt", [J2000 - 36525.0, J2000, J2016, J2000 + 36525.0])
def test_non_j2000_catalog_epoch_matches_erfa_pmsafe(jd_tt):
    erfa = pytest.importorskip("erfa")
    s = BARNARD
    # Zero radial velocity isolates the epoch handling. With a nonzero radial
    # velocity pmsafe also applies the Romer (light-time) correction, which is
    # Phase 2 of the fixed-star standard.
    rv = 0.0
    dec = math.radians(s["dec_deg"])
    ra2, dec2, *_ = erfa.pmsafe(
        math.radians(s["ra_deg"]), dec,
        math.radians(s["pmra"] / 3.6e6) / math.cos(dec), math.radians(s["pmdec"] / 3.6e6),
        s["parallax"] / 1000.0, rv, J2016, 0.0, jd_tt, 0.0,
    )
    expected = (math.cos(dec2) * math.cos(ra2), math.cos(dec2) * math.sin(ra2), math.sin(dec2))
    actual, distance_pc = astrometric_direction(
        s["ra_deg"], s["dec_deg"], s["pmra"], s["pmdec"], s["parallax"], rv, J2016, jd_tt,
    )
    assert _angle_arcsec(actual, expected) < 0.001
    assert distance_pc is not None and 1.0 < distance_pc < 2.5


def test_the_reference_epoch_is_honoured_not_assumed():
    s = BARNARD
    at_epoch, _ = astrometric_direction(
        s["ra_deg"], s["dec_deg"], s["pmra"], s["pmdec"], s["parallax"], s["rv"], J2016, J2016,
    )
    catalog = (math.cos(math.radians(s["dec_deg"])) * math.cos(math.radians(s["ra_deg"])),
               math.cos(math.radians(s["dec_deg"])) * math.sin(math.radians(s["ra_deg"])),
               math.sin(math.radians(s["dec_deg"])))
    assert at_epoch == pytest.approx(catalog, abs=1e-15)
    # Read as J2000 instead, the same row is 16 years of 10.4"/yr motion away.
    misread, _ = astrometric_direction(
        s["ra_deg"], s["dec_deg"], s["pmra"], s["pmdec"], s["parallax"], s["rv"], J2000, J2016,
    )
    assert _angle_arcsec(misread, at_epoch) > 150.0


@pytest.mark.parametrize("ref_epoch_jd", [J2000, J2016])
def test_native_evaluator_honours_the_reference_epoch(ref_epoch_jd):
    mn = pytest.importorskip("moira.moira_native")
    s = BARNARD
    native = mn.FixedStarEvaluator(s["ra_deg"], s["dec_deg"], s["pmra"], s["pmdec"],
                                   s["parallax"], s["rv"], ref_epoch_jd=ref_epoch_jd)
    for jd_tt in (J2000 - 36525.0, J2000 + 36525.0):
        python, _ = astrometric_direction(s["ra_deg"], s["dec_deg"], s["pmra"], s["pmdec"],
                                          s["parallax"], s["rv"], ref_epoch_jd, jd_tt)
        assert _angle_arcsec(_unit(native.evaluate(jd_tt)[:3]), python) < 1e-6


def _write_registry(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides):
    row = {"name": "Testar", "nomenclature": "HIP 0", "gaia_dr3_id": "0", "ra_deg": "10.0",
           "dec_deg": "20.0", "pmra_mas_yr": "1.0", "pmdec_mas_yr": "2.0", "parallax_mas": "3.0",
           "magnitude_v": "4.0", "color_index": "0.5", "ecl_lon_deg": "0", "ecl_lat_deg": "0",
           "arc_vis_deg": "10", "lat_limit_deg": "70", "ref_epoch_jd": "2451545.0", "frame": "ICRS"}
    row.update(overrides)
    return row


@pytest.mark.parametrize(("overrides", "message"), [
    ({"frame": "FK5"}, "unsupported astrometric frame"),
    ({"ref_epoch_jd": ""}, "missing reference epoch"),
    ({"ref_epoch_jd": "nan"}, "missing reference epoch"),
])
def test_loader_refuses_rows_without_an_admissible_epoch_or_frame(tmp_path, monkeypatch, overrides, message):
    path = tmp_path / "star_registry.csv"
    _write_registry(path, [_row(**overrides)])
    monkeypatch.setattr(stars, "_REGISTRY_PATH", path)
    stars._load_registry_records.cache_clear()
    try:
        with pytest.raises(ValueError, match=message):
            stars._load_registry_records()
    finally:
        stars._load_registry_records.cache_clear()


def test_every_registry_row_declares_its_epoch_and_frame():
    records = stars._load_registry_records()
    assert records
    assert {record.frame for record in records} == {"ICRS"}
    assert all(math.isfinite(record.ref_epoch_jd) for record in records)
