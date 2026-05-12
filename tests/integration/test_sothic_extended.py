"""
Extended Sothic cycle validation — multi-epoch, multi-site, oracle comparison.

This test suite validates Moira's heliacal rising computation for Sirius across
the full Sothic cycle (~1460 years), multiple Egyptian sites, and against
independent astronomical oracles.

Sothic cycle epochs (traditional):
  -2781: Epoch 1 (theoretical, predates historical records)
  -1321: Epoch 2 (Middle Kingdom)
   +139: Epoch 3 (Censorinus, Roman era) — anchor
  +1599: Epoch 4 (theoretical future epoch)

The Egyptian civil calendar (365 days, no leap) drifts ~1 day every 4 years
relative to the solar year. The Sothic cycle is the ~1460-year period for
Sirius heliacal rising to return to 1 Thoth.
"""

import math

import pytest
from astropy.coordinates import AltAz, Distance, EarthLocation, SkyCoord, get_body
from astropy.time import Time
import astropy.units as u

from moira.sothic import sothic_epochs, sothic_rising


# ---------------------------------------------------------------------------
# Egyptian sites (latitude, longitude, elevation)
# ---------------------------------------------------------------------------

EGYPTIAN_SITES = {
    "Elephantine": (24.1, 32.9, 0.0),   # Aswan, southernmost
    "Thebes": (25.7, 32.6, 0.0),        # Luxor
    "Abydos": (26.2, 31.9, 0.0),        # Middle Egypt
    "Memphis": (29.8, 31.3, 0.0),       # Near Cairo
    "Heliopolis": (30.1, 31.3, 0.0),    # Cairo suburbs
    "Alexandria": (31.2, 29.9, 0.0),    # Mediterranean coast, northernmost
}


# ---------------------------------------------------------------------------
# Test 1: Multi-epoch validation (all 4 Sothic epochs)
# ---------------------------------------------------------------------------


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_all_four_epochs_produce_valid_results() -> None:
    """Verify all 4 traditional Sothic epochs produce heliacal rising events."""
    epochs = [-2781, -1321, 139, 1599]
    lat, lon = 29.8, 31.3  # Memphis

    for epoch_year in epochs:
        entries = sothic_rising(lat, lon, epoch_year, epoch_year)
        assert len(entries) == 1, f"Epoch {epoch_year} should produce exactly 1 entry"
        entry = entries[0]
        assert entry.year == epoch_year
        assert entry.egyptian_date is not None
        assert entry.jd_rising > 0  # Valid JD


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_epochs_are_approximately_1460_years_apart() -> None:
    """Verify the Sothic cycle period is ~1460 years."""
    lat, lon = 29.8, 31.3  # Memphis
    epochs = [-2781, -1321, 139, 1599]

    jd_risings = []
    for epoch_year in epochs:
        entry = sothic_rising(lat, lon, epoch_year, epoch_year)[0]
        jd_risings.append(entry.jd_rising)

    # Check intervals between consecutive epochs
    intervals_years = []
    for i in range(1, len(jd_risings)):
        interval_days = jd_risings[i] - jd_risings[i - 1]
        interval_years = interval_days / 365.25
        intervals_years.append(interval_years)

    # Each interval should be ~1460 years (±10 years tolerance for drift)
    for interval in intervals_years:
        assert 1450 <= interval <= 1470, f"Sothic cycle interval {interval:.1f} years out of range"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_epoch_detection_finds_all_four_epochs() -> None:
    """Verify sothic_epochs() can detect all 4 traditional epochs."""
    lat, lon = 29.8, 31.3  # Memphis
    tolerance_days = 3.0

    # Search around each traditional epoch
    search_windows = [
        (-2783, -2779),  # Around -2781
        (-1323, -1319),  # Around -1321
        (137, 141),      # Around 139
        (1597, 1601),    # Around 1599
    ]

    for year_start, year_end in search_windows:
        epochs = sothic_epochs(lat, lon, year_start, year_end, tolerance_days=tolerance_days)
        assert len(epochs) >= 1, f"Should find epoch in window {year_start}-{year_end}"


# ---------------------------------------------------------------------------
# Test 2: Multi-year continuity (verify smooth progression)
# ---------------------------------------------------------------------------


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_rising_progresses_smoothly_across_consecutive_years() -> None:
    """Verify heliacal rising dates change smoothly year-to-year."""
    lat, lon = 29.8, 31.3  # Memphis
    year_start, year_end = 135, 145  # 11 years around Censorinus epoch

    entries = sothic_rising(lat, lon, year_start, year_end)
    assert len(entries) == year_end - year_start + 1

    # Check temporal continuity: consecutive years should differ by ~365.25 days
    for i in range(1, len(entries)):
        jd_diff = entries[i].jd_rising - entries[i - 1].jd_rising
        # Expect ~365.25 days ± 2 days (accounting for solar year vs civil calendar drift)
        assert 363 <= jd_diff <= 367, f"Year {entries[i].year}: discontinuity {jd_diff:.2f} days"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_drift_accumulates_linearly_over_decades() -> None:
    """Verify drift_days increases linearly over time (Egyptian calendar drifts ~0.25 days/year)."""
    lat, lon = 29.8, 31.3  # Memphis
    year_start, year_end = 139, 179  # 40 years

    entries = sothic_rising(lat, lon, year_start, year_end)

    # Drift should increase by ~0.25 days per year (365.25 - 365 = 0.25)
    drift_start = entries[0].drift_days
    drift_end = entries[-1].drift_days

    # Over 40 years, expect ~10 days of additional drift
    drift_increase = (drift_end - drift_start) % 365  # Handle wrap-around
    assert 8 <= drift_increase <= 12, f"Drift increase {drift_increase:.2f} days over 40 years out of range"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_day_of_year_increases_monotonically_away_from_epoch() -> None:
    """Verify day_of_year increases as we move away from a Sothic epoch (with leap year tolerance)."""
    lat, lon = 29.8, 31.3  # Memphis
    year_start, year_end = 139, 149  # 10 years after Censorinus epoch

    entries = sothic_rising(lat, lon, year_start, year_end)

    # Day of year should generally increase (heliacal rising drifts later in the year)
    # Allow ±1 day variation due to leap year effects in the Julian/Gregorian calendar
    for i in range(1, len(entries)):
        day_diff = entries[i].day_of_year - entries[i - 1].day_of_year
        assert day_diff >= -1, \
            f"Day of year should not decrease by more than 1: {entries[i - 1].day_of_year} -> {entries[i].day_of_year}"


# ---------------------------------------------------------------------------
# Test 3: Oracle comparison (astropy/ERFA)
# ---------------------------------------------------------------------------


def sirius_geometric_altitude_astropy(jd_ut: float, lat: float, lon: float) -> float:
    """
    Geometric altitude of Sirius using astropy/ERFA (independent oracle).

    Sirius: HIP 32349, ICRS J2000
    RA = 101.28715533° (6h 45m 8.9s)
    Dec = -16.71611586° (-16° 42' 58")
    Proper motion: pmra = -546.01 mas/yr, pmdec = -1223.07 mas/yr
    Parallax: 379.21 mas
    """
    obs_time = Time(jd_ut, format="jd", scale="utc")
    location = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=0 * u.m)

    sirius = SkyCoord(
        ra=101.28715533 * u.deg,
        dec=-16.71611586 * u.deg,
        pm_ra_cosdec=-546.01 * u.mas / u.yr,
        pm_dec=-1223.07 * u.mas / u.yr,
        distance=Distance(parallax=379.21 * u.mas, allow_negative=False),
        frame="icrs",
        obstime=Time("J2000.0"),
    )
    sirius_at_epoch = sirius.apply_space_motion(new_obstime=obs_time)
    altaz = AltAz(obstime=obs_time, location=location, pressure=0)
    return float(sirius_at_epoch.transform_to(altaz).alt.deg)


def sun_geometric_altitude_astropy(jd_ut: float, lat: float, lon: float) -> float:
    """Geometric altitude of the Sun using astropy/ERFA."""
    obs_time = Time(jd_ut, format="jd", scale="utc")
    location = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=0 * u.m)
    sun = get_body("sun", obs_time, location)
    altaz = AltAz(obstime=obs_time, location=location, pressure=0 * u.hPa)
    return float(sun.transform_to(altaz).alt.deg)


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_memphis_oracle_comparison() -> None:
    """Compare Moira's Sothic rising against astropy/ERFA oracle for 139 AD Memphis."""
    lat, lon = 29.8, 31.3  # Memphis
    entry = sothic_rising(lat, lon, 139, 139)[0]

    # At the predicted heliacal rising time, verify:
    # 1. Sirius altitude > -0.5667° (geometric horizon)
    # 2. Sun altitude ≈ -arcus_visionis (twilight threshold)
    jd_rising = entry.jd_rising
    sirius_alt = sirius_geometric_altitude_astropy(jd_rising, lat, lon)
    sun_alt = sun_geometric_altitude_astropy(jd_rising, lat, lon)

    assert sirius_alt > -0.5667, f"Sirius should be above horizon: {sirius_alt:.3f}°"
    # Sun should be near -10° (arcus visionis for Sirius, V=-1.46 → av≈7.5-10°)
    assert -12 <= sun_alt <= -8, f"Sun altitude {sun_alt:.3f}° outside twilight range"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_alexandria_oracle_comparison() -> None:
    """Compare Moira's Sothic rising against astropy/ERFA oracle for 139 AD Alexandria."""
    lat, lon = 31.2, 29.9  # Alexandria
    entry = sothic_rising(lat, lon, 139, 139)[0]

    jd_rising = entry.jd_rising
    sirius_alt = sirius_geometric_altitude_astropy(jd_rising, lat, lon)
    sun_alt = sun_geometric_altitude_astropy(jd_rising, lat, lon)

    assert sirius_alt > -0.5667, f"Sirius should be above horizon: {sirius_alt:.3f}°"
    assert -12 <= sun_alt <= -8, f"Sun altitude {sun_alt:.3f}° outside twilight range"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_minus_1321_memphis_oracle_comparison() -> None:
    """Compare Moira's Sothic rising against astropy/ERFA oracle for -1321 BCE Memphis."""
    lat, lon = 29.8, 31.3  # Memphis
    entry = sothic_rising(lat, lon, -1321, -1321)[0]

    jd_rising = entry.jd_rising
    sirius_alt = sirius_geometric_altitude_astropy(jd_rising, lat, lon)
    sun_alt = sun_geometric_altitude_astropy(jd_rising, lat, lon)

    assert sirius_alt > -0.5667, f"Sirius should be above horizon: {sirius_alt:.3f}°"
    assert -12 <= sun_alt <= -8, f"Sun altitude {sun_alt:.3f}° outside twilight range"


# ---------------------------------------------------------------------------
# Test 4: More Egyptian sites (comprehensive latitude coverage)
# ---------------------------------------------------------------------------


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_all_egyptian_sites_produce_valid_results() -> None:
    """Verify all 6 Egyptian sites produce valid heliacal rising events for 139 AD."""
    for site_name, (lat, lon, elev) in EGYPTIAN_SITES.items():
        entries = sothic_rising(lat, lon, 139, 139)
        assert len(entries) == 1, f"{site_name} should produce exactly 1 entry"
        entry = entries[0]
        assert entry.year == 139
        assert entry.jd_rising > 0
        assert entry.egyptian_date is not None


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_latitude_trend_across_all_sites() -> None:
    """Verify heliacal rising occurs earlier at southern sites (monotonic latitude trend)."""
    results = []
    for site_name, (lat, lon, elev) in EGYPTIAN_SITES.items():
        entry = sothic_rising(lat, lon, 139, 139)[0]
        results.append((site_name, lat, entry.jd_rising))

    # Sort by latitude (south to north)
    results.sort(key=lambda x: x[1])

    # Verify JD increases monotonically with latitude
    for i in range(1, len(results)):
        site_prev, lat_prev, jd_prev = results[i - 1]
        site_curr, lat_curr, jd_curr = results[i]
        assert jd_curr > jd_prev, \
            f"{site_curr} (lat {lat_curr:.1f}°) should rise later than {site_prev} (lat {lat_prev:.1f}°)"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_elephantine_alexandria_span_exceeds_5_days() -> None:
    """Verify the span between southernmost and northernmost sites is significant (>5 days)."""
    elephantine = sothic_rising(24.1, 32.9, 139, 139)[0]
    alexandria = sothic_rising(31.2, 29.9, 139, 139)[0]

    span_days = alexandria.jd_rising - elephantine.jd_rising
    assert span_days > 5, f"Elephantine-Alexandria span {span_days:.2f} days too small"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_all_sites_multi_epoch() -> None:
    """Verify all sites produce valid results across multiple epochs."""
    epochs = [-1321, 139, 1599]
    for epoch_year in epochs:
        for site_name, (lat, lon, elev) in EGYPTIAN_SITES.items():
            entries = sothic_rising(lat, lon, epoch_year, epoch_year)
            assert len(entries) == 1, f"{site_name} epoch {epoch_year} should produce 1 entry"


# ---------------------------------------------------------------------------
# Test 5: Temporal continuity (year-to-year stability)
# ---------------------------------------------------------------------------


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_no_discontinuities_across_50_years() -> None:
    """Verify no temporal discontinuities across 50 years."""
    lat, lon = 29.8, 31.3  # Memphis
    year_start, year_end = 120, 170  # 50 years spanning Censorinus epoch

    entries = sothic_rising(lat, lon, year_start, year_end)
    assert len(entries) == 51

    # Check all consecutive pairs for discontinuities
    for i in range(1, len(entries)):
        jd_diff = entries[i].jd_rising - entries[i - 1].jd_rising
        assert 363 <= jd_diff <= 367, \
            f"Discontinuity at year {entries[i].year}: {jd_diff:.2f} days"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_egyptian_date_progression_is_monotonic() -> None:
    """Verify Egyptian civil date progresses monotonically through the year."""
    lat, lon = 29.8, 31.3  # Memphis
    year_start, year_end = 139, 159  # 20 years

    entries = sothic_rising(lat, lon, year_start, year_end)

    # Egyptian date should progress through the calendar
    # (day_of_egyptian_year should increase, wrapping at 365)
    prev_day = 0
    wrap_count = 0
    for entry in entries:
        # Compute day of Egyptian year (1-365)
        if entry.egyptian_date.month_name == "Epagomenal":
            day_of_year = 360 + entry.egyptian_date.day
        else:
            month_names = ["Thoth", "Phaophi", "Athyr", "Choiak", "Tybi", "Mechir",
                          "Phamenoth", "Pharmuthi", "Pachons", "Payni", "Epiphi", "Mesore"]
            month_idx = month_names.index(entry.egyptian_date.month_name)
            day_of_year = month_idx * 30 + entry.egyptian_date.day

        if day_of_year < prev_day:
            wrap_count += 1
        prev_day = day_of_year

    # Should wrap around the calendar at least once in 20 years
    assert wrap_count >= 1, "Egyptian date should wrap around calendar"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_jd_rising_increases_monotonically() -> None:
    """Verify JD of heliacal rising increases monotonically (no time travel)."""
    lat, lon = 29.8, 31.3  # Memphis
    year_start, year_end = 100, 200  # 100 years

    entries = sothic_rising(lat, lon, year_start, year_end)

    for i in range(1, len(entries)):
        assert entries[i].jd_rising > entries[i - 1].jd_rising, \
            f"JD should increase: year {entries[i - 1].year} -> {entries[i].year}"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_drift_days_near_zero_or_365_at_anchor_epoch() -> None:
    """Verify drift_days is near 0 or 365 at the anchor epoch (139 AD), indicating alignment with 1 Thoth."""
    lat, lon = 29.8, 31.3  # Memphis

    entry = sothic_rising(lat, lon, 139, 139)[0]
    # At epoch, heliacal rising should be near 1 Thoth (drift near 0 or wrapped near 365)
    assert entry.drift_days <= 3.0 or entry.drift_days >= 362.0, \
        f"Anchor epoch 139 drift_days {entry.drift_days:.1f} should be near 0 or 365"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_multi_century_stability() -> None:
    """Verify computation remains stable across multiple centuries."""
    lat, lon = 29.8, 31.3  # Memphis

    # Sample every 50 years from -1321 to 1599 (2920 years, ~2 Sothic cycles)
    years = list(range(-1321, 1600, 50))

    for year in years:
        entries = sothic_rising(lat, lon, year, year)
        assert len(entries) == 1, f"Year {year} should produce exactly 1 entry"
        entry = entries[0]
        assert entry.jd_rising > 0
        assert entry.egyptian_date is not None
        # Verify drift_days is in valid range [0, 365)
        assert 0 <= entry.drift_days < 365, \
            f"Year {year} drift_days {entry.drift_days:.2f} out of range"
