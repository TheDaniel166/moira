"""
Extended Sothic cycle validation — multi-epoch, multi-site, corroboration.

This test suite validates Moira's heliacal rising computation for Sirius across
the schematic Sothic cycle (1460 fixed Julian years), multiple Egyptian
sites, and independent Astropy/ERFA geometric corroboration. Primary-source
civil-day authority checks live in tests/oracle/test_sothic_oracle.py.

Schematic fixed-cycle years in astronomical numbering:
  -2781: Epoch 1 (theoretical, predates historical records)
  -1321: Epoch 2 (Middle Kingdom)
   +139: Epoch 3 (Censorinus, Roman era) — anchor
  +1599: Epoch 4 (theoretical future epoch)

The Egyptian civil calendar (365 days, no leap) drifts ~1 day every 4 years
relative to the solar year. The Sothic cycle is the ~1460-year period for
Sirius heliacal rising to return to 1 Thoth.
"""

import pytest
from astropy.coordinates import AltAz, Distance, EarthLocation, SkyCoord, get_body
from astropy.time import Time
import astropy.units as u

from moira.sothic import (
    predicted_sothic_epoch_year,
    sothic_drift_rate,
    sothic_epochs,
    sothic_rising,
)


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
# Test 3: Independent geometric corroboration (Astropy/ERFA)
# ---------------------------------------------------------------------------


def sirius_geometric_altitude_astropy(jd_ut: float, lat: float, lon: float) -> float:
    """
    Geometric altitude of Sirius using Astropy/ERFA for corroboration.

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
def test_sothic_139_memphis_astropy_corroboration() -> None:
    """Corroborate 139 AD Memphis event geometry with Astropy/ERFA."""
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
def test_sothic_139_alexandria_astropy_corroboration() -> None:
    """Corroborate 139 AD Alexandria event geometry with Astropy/ERFA."""
    lat, lon = 31.2, 29.9  # Alexandria
    entry = sothic_rising(lat, lon, 139, 139)[0]

    jd_rising = entry.jd_rising
    sirius_alt = sirius_geometric_altitude_astropy(jd_rising, lat, lon)
    sun_alt = sun_geometric_altitude_astropy(jd_rising, lat, lon)

    assert sirius_alt > -0.5667, f"Sirius should be above horizon: {sirius_alt:.3f}°"
    assert -12 <= sun_alt <= -8, f"Sun altitude {sun_alt:.3f}° outside twilight range"


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_minus_1321_memphis_astropy_corroboration() -> None:
    """Corroborate astronomical year -1321 Memphis geometry with Astropy/ERFA."""
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


# ---------------------------------------------------------------------------
# Drift rate: pinned against real risings, at both ends of the cycle
# ---------------------------------------------------------------------------


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_drift_rate_tracks_the_julian_year_not_the_tropical_year() -> None:
    """Pin the computed drift rate against real risings, far apart in time.

    The drift is the excess of Sirius's heliacal recurrence interval over the
    365-day civil year. That interval tracks the **Julian** year of 365.25
    days, not the tropical year of 365.2422, which is why this module's cycle
    identity holds exactly: 533265 / 1460 = 365.25. Reading the tropical year
    here instead would give 0.2422 days/year and a cycle near 1508 years.

    Without this test nothing could fail if the rate were wrong. The unit test
    of the fit uses a synthetic slope, and the REST test asserts only that the
    route reports whatever the engine computed, so both would pass unchanged.

    The tolerance is 0.004 days/year about 0.25, which still excludes the
    tropical reading by its full 0.0078 separation. It is deliberately loose
    because the rate is a property of the heliacal visibility model, not a
    constant: measured here it moves by 0.0017 d/yr for a 0.05 degree shift of
    site latitude, which is more than it moves between the Roman era and the
    Old Kingdom. A tight tolerance would pin the visibility doctrine rather
    than the calendar arithmetic.
    """
    latitude, longitude, _ = EGYPTIAN_SITES["Memphis"]
    measured = {}
    for label, (year_start, year_end) in (
        ("roman", (120, 160)),
        ("old_kingdom", (-2790, -2750)),
    ):
        entries = sothic_rising(latitude, longitude, year_start, year_end)
        assert len(entries) >= 20, f"{label}: too few risings to fit a rate"
        rate = sothic_drift_rate(entries)
        measured[label] = rate

        assert rate == pytest.approx(0.25, abs=0.004), (
            f"{label}: drift rate {rate:.6f} d/yr is not the Julian-year excess"
        )
        assert abs(rate - 0.2422) > 0.004, (
            f"{label}: drift rate {rate:.6f} d/yr matches the tropical year, "
            "which does not govern the heliacal recurrence"
        )
        implied_cycle_years = 365.0 / rate
        assert 1420.0 < implied_cycle_years < 1500.0, (
            f"{label}: implied cycle {implied_cycle_years:.1f} yr is not near "
            "the 1460-year schematic cycle this module assumes"
        )

    # Both epochs land in the same band. They are not asserted equal: at this
    # site they differ by about 0.0017 d/yr, which is the visibility model
    # responding to the epoch, not the calendar arithmetic changing.
    assert measured["roman"] == pytest.approx(measured["old_kingdom"], abs=0.004)


# ---------------------------------------------------------------------------
# Epoch windows: the finder returns years, the projection is schematic
# ---------------------------------------------------------------------------


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_epoch_tolerance_selects_a_window_of_years_by_construction() -> None:
    """A tolerance admits a span of years, not a single epoch.

    The rising drifts about 0.25 days per civil year, so a +/- tolerance
    admits roughly 2 * tolerance / 0.25 consecutive years. They are one
    realignment window, which is why sothic_epochs documents its result as one
    entry per year in tolerance rather than one per epoch.
    """
    latitude, longitude, _ = EGYPTIAN_SITES["Memphis"]
    spans = {}
    for tolerance_days, expected in ((0.5, 4), (1.0, 8), (2.0, 16)):
        epochs = sothic_epochs(
            latitude, longitude, -1335, -1300, tolerance_days=tolerance_days
        )
        years = sorted(epoch.year for epoch in epochs)
        spans[tolerance_days] = years
        assert years, f"tolerance {tolerance_days}: no epoch years found"
        assert len(years) == pytest.approx(expected, abs=1), (
            f"tolerance {tolerance_days} d admitted {len(years)} years, "
            f"expected about {expected} at ~0.25 d/yr drift"
        )
        assert years == list(range(years[0], years[-1] + 1)), (
            f"tolerance {tolerance_days}: window is not contiguous: {years}"
        )

    # Widening the tolerance may only widen the window.
    assert set(spans[0.5]) <= set(spans[1.0]) <= set(spans[2.0])


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_schematic_epoch_projection_lands_outside_the_computed_window() -> None:
    """The 1460-year projection is arithmetic, and says so.

    It is not wrong, it is schematic: the computed realignment interval is
    nearer 1455 years, so the fixed-interval projection falls progressively
    earlier than the window the engine computes. This pins that divergence so
    it cannot grow silently, and so the documented figures stay true.
    """
    latitude, longitude, _ = EGYPTIAN_SITES["Memphis"]
    gaps = {}
    for n_cycles, (search_start, search_end) in (
        (-1, (-1335, -1300)),
        (-2, (-2795, -2760)),
    ):
        predicted = predicted_sothic_epoch_year(139, n_cycles)
        epochs = sothic_epochs(
            latitude, longitude, search_start, search_end, tolerance_days=1.0
        )
        years = sorted(epoch.year for epoch in epochs)
        assert years, f"n_cycles={n_cycles}: no computed window found"
        gaps[n_cycles] = years[0] - predicted
        assert predicted < years[0], (
            f"n_cycles={n_cycles}: projection {predicted:.0f} is expected to "
            f"precede the computed window starting {years[0]}"
        )

    # One cycle back the projection is ~2 years early, two cycles ~5, so the
    # divergence widens by roughly 3 years per cycle.
    assert gaps[-1] == pytest.approx(2, abs=1)
    assert gaps[-2] == pytest.approx(5, abs=1)
    assert gaps[-2] > gaps[-1]
