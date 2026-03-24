"""
Unit tests for moira/gaia.py against the real kernels/gaia_g10.bin catalog.

All tests marked @pytest.mark.requires_ephemeris (gaia_g10.bin required).

Gaia DR3 brightness caveat
--------------------------
Gaia cannot reliably observe stars brighter than roughly G ~ 3.  Very bright
stars (Sirius, Canopus, Arcturus …) saturate the instrument and are absent or
have null photometry in the source catalog.  The G < 10 download therefore
starts around G ~ 2, not G ~ -1.5.  Tests do not assume any star brighter
than G = 2.5.

Catalog totals (G < 10, parallax NOT NULL, downloaded from ESA TAP):
  147,996 stars
"""
from __future__ import annotations

import math
import pytest

import moira.gaia as gaia
from moira.gaia import (
    GaiaStarPosition,
    StellarQuality,
    catalog_size,
    gaia_catalog_info,
    gaia_star_at,
    gaia_stars_by_magnitude,
    gaia_stars_near,
    load_gaia_catalog,
)

_J2000 = 2451545.0   # JD TT for J2000.0


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_load_catalog_succeeds():
    load_gaia_catalog()   # must not raise


@pytest.mark.requires_ephemeris
def test_catalog_size_matches_download():
    assert catalog_size() == 147_996


@pytest.mark.requires_ephemeris
def test_catalog_info_keys():
    info = gaia_catalog_info()
    for key in ("path", "n_stars", "mag_min", "mag_max", "n_with_color", "n_with_teff"):
        assert key in info


@pytest.mark.requires_ephemeris
def test_catalog_info_n_stars():
    assert gaia_catalog_info()["n_stars"] == 147_996


@pytest.mark.requires_ephemeris
def test_catalog_info_mag_max_below_limit():
    """All stars in a G < 10 catalog must have mag_max < 10."""
    assert gaia_catalog_info()["mag_max"] < 10.0


@pytest.mark.requires_ephemeris
def test_catalog_info_mag_min_reasonable():
    """Gaia saturates for very bright stars; the faintest 'bright' limit in
    the catalog is around G ~ 2 (not negative).  Just verify it is under 3."""
    assert gaia_catalog_info()["mag_min"] < 3.0


@pytest.mark.requires_ephemeris
def test_catalog_info_n_with_color_positive():
    assert gaia_catalog_info()["n_with_color"] > 0


@pytest.mark.requires_ephemeris
def test_catalog_info_path_contains_kernels():
    assert "kernels" in gaia_catalog_info()["path"]


# ---------------------------------------------------------------------------
# gaia_star_at — return type and structure
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_gaia_star_at_returns_gaia_star_position():
    assert isinstance(gaia_star_at(0, _J2000), GaiaStarPosition)


@pytest.mark.requires_ephemeris
def test_gaia_star_at_longitude_in_range():
    pos = gaia_star_at(0, _J2000)
    assert 0.0 <= pos.longitude < 360.0


@pytest.mark.requires_ephemeris
def test_gaia_star_at_latitude_in_range():
    pos = gaia_star_at(0, _J2000)
    assert -90.0 <= pos.latitude <= 90.0


@pytest.mark.requires_ephemeris
def test_gaia_star_at_magnitude_below_limit():
    pos = gaia_star_at(0, _J2000)
    assert pos.magnitude < 10.0


@pytest.mark.requires_ephemeris
def test_gaia_star_at_source_index_preserved():
    pos = gaia_star_at(42, _J2000)
    assert pos.source_index == 42


@pytest.mark.requires_ephemeris
def test_gaia_star_at_quality_is_stellar_quality():
    pos = gaia_star_at(0, _J2000)
    assert isinstance(pos.quality, StellarQuality)


@pytest.mark.requires_ephemeris
def test_gaia_star_at_not_topocentric_by_default():
    pos = gaia_star_at(0, _J2000)
    assert pos.is_topocentric is False


@pytest.mark.requires_ephemeris
def test_gaia_star_at_distance_positive_when_parallax_available():
    pos = gaia_star_at(0, _J2000)
    if pos.parallax_mas > 0.0:
        assert pos.distance_ly > 0.0


@pytest.mark.requires_ephemeris
def test_gaia_star_at_invalid_index_raises():
    with pytest.raises((IndexError, ValueError)):
        gaia_star_at(999_999_999, _J2000)


# ---------------------------------------------------------------------------
# gaia_stars_by_magnitude — bright subset (max_magnitude=2.5 for speed)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_returns_list():
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=2.5)
    assert isinstance(result, list)


@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_non_empty():
    """There must be at least one star brighter than G=2.5."""
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=2.5)
    assert len(result) >= 1


@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_sorted_brightest_first():
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=2.5)
    mags = [p.magnitude for p in result]
    assert mags == sorted(mags)


@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_all_below_limit():
    limit = 2.5
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=limit)
    assert all(p.magnitude <= limit for p in result)


@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_brightest_is_reasonable():
    """The brightest available star should have magnitude < 3 and valid coords."""
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=2.5)
    assert len(result) >= 1
    brightest = result[0]
    assert brightest.magnitude < 3.0
    assert 0.0 <= brightest.longitude < 360.0
    assert -90.0 <= brightest.latitude <= 90.0


@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_all_longitudes_in_range():
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=2.5)
    for p in result:
        assert 0.0 <= p.longitude < 360.0, (
            f"source_index={p.source_index} longitude={p.longitude:.4f} out of [0,360)"
        )


@pytest.mark.requires_ephemeris
def test_gaia_stars_by_magnitude_all_latitudes_in_range():
    result = gaia_stars_by_magnitude(_J2000, max_magnitude=2.5)
    assert all(-90.0 <= p.latitude <= 90.0 for p in result)


# ---------------------------------------------------------------------------
# gaia_stars_near — always pass max_magnitude to limit compute cost
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_gaia_stars_near_returns_list():
    result = gaia_stars_near(180.0, _J2000, orb=5.0, max_magnitude=6.0)
    assert isinstance(result, list)


@pytest.mark.requires_ephemeris
def test_gaia_stars_near_non_empty_broad_search():
    """A 10° window anywhere on the ecliptic should contain G<6 stars."""
    result = gaia_stars_near(0.0, _J2000, orb=10.0, max_magnitude=6.0)
    assert len(result) >= 1


@pytest.mark.requires_ephemeris
def test_gaia_stars_near_all_within_orb():
    lon, orb = 90.0, 3.0
    result = gaia_stars_near(lon, _J2000, orb=orb, max_magnitude=6.0)
    for p in result:
        diff = abs((p.longitude - lon + 180.0) % 360.0 - 180.0)
        assert diff <= orb + 0.6, (   # +0.6° for the guard band
            f"source_index={p.source_index} lon={p.longitude:.2f} outside orb={orb} of {lon}"
        )


@pytest.mark.requires_ephemeris
def test_gaia_stars_near_magnitude_filter_reduces_results():
    all_near  = gaia_stars_near(0.0, _J2000, orb=10.0, max_magnitude=7.0)
    bright    = gaia_stars_near(0.0, _J2000, orb=10.0, max_magnitude=5.0)
    assert len(bright) <= len(all_near)
    assert all(p.magnitude <= 5.0 for p in bright)


@pytest.mark.requires_ephemeris
def test_gaia_stars_near_empty_patch_returns_list():
    result = gaia_stars_near(180.0, _J2000, orb=0.001, max_magnitude=2.0)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Top-level moira import
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_importable_from_moira():
    import moira as _m
    assert hasattr(_m, "gaia_star_at")
    assert hasattr(_m, "gaia_stars_near")
    assert hasattr(_m, "gaia_stars_by_magnitude")
    assert hasattr(_m, "gaia_catalog_info")
    assert hasattr(_m, "load_gaia_catalog")
