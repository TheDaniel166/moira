from __future__ import annotations

import pytest

from moira.sothic import sothic_epochs, sothic_rising


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_rising_supports_bce_year_without_python_datetime() -> None:
    entries = sothic_rising(29.8, 31.3, -1321, -1321)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.year == -1321
    assert entry.calendar_year == -1321
    assert 1 <= entry.calendar_month <= 12
    assert 1 <= entry.calendar_day <= 31
    assert entry.date_utc is None


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_rising_anchor_year_is_near_censorinus_epoch() -> None:
    entries = sothic_rising(31.2, 29.9, 139, 139)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.year == 139
    assert entry.egyptian_date.month_name == "Thoth"
    assert 1 <= entry.egyptian_date.day <= 3
    assert abs(entry.drift_days) <= 2.0


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_epochs_finds_anchor_epoch_near_139_ad() -> None:
    epochs = sothic_epochs(31.2, 29.9, 138, 140, tolerance_days=2.0)

    assert epochs
    assert any(epoch.year == 139 for epoch in epochs)
    anchor = next(epoch for epoch in epochs if epoch.year == 139)
    assert abs(anchor.drift_days) <= 2.0


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_ad_site_order_matches_published_latitude_trend() -> None:
    """
    Historical benchmark: for the Censorinus-era epoch window, southern
    Egyptian sites should see Sirius heliacally earlier than northern ones.
    """
    elephantine = sothic_rising(24.1, 32.9, 139, 139, arcus_visionis=10.0)[0]
    thebes = sothic_rising(25.7, 32.6, 139, 139, arcus_visionis=10.0)[0]
    memphis = sothic_rising(29.8, 31.3, 139, 139, arcus_visionis=10.0)[0]
    alexandria = sothic_rising(31.2, 29.9, 139, 139, arcus_visionis=10.0)[0]

    assert elephantine.jd_rising < thebes.jd_rising < memphis.jd_rising < alexandria.jd_rising
    assert elephantine.drift_days < thebes.drift_days < memphis.drift_days
    assert alexandria.drift_days < 1.0


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_ad_alexandria_matches_censorinus_window_at_arcus_10() -> None:
    """
    Alexandria with arcus visionis ~10° is the benchmark case where the Sirius
    rising falls on or extremely near 1 Thoth in 139 AD.
    """
    entry = sothic_rising(31.2, 29.9, 139, 139, arcus_visionis=10.0)[0]

    assert entry.egyptian_date.month_name == "Thoth"
    assert entry.egyptian_date.day == 1
    assert abs(entry.drift_days) <= 1.0


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_139_ad_memphis_remains_just_before_1_thoth_at_arcus_10() -> None:
    """
    Memphis is slightly south of Alexandria and should therefore place the
    heliacal rising a bit earlier in the civil calendar for the same epoch.
    """
    entry = sothic_rising(29.8, 31.3, 139, 139, arcus_visionis=10.0)[0]

    assert entry.egyptian_date.month_name == "Epagomenal"
    assert entry.egyptian_date.day == 4
    assert 362.0 <= entry.drift_days <= 364.5


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_rising_moves_later_with_higher_latitude() -> None:
    memphis = sothic_rising(29.8, 31.3, 139, 139)[0]
    london = sothic_rising(51.5, -0.1, 139, 139)[0]

    assert london.jd_rising > memphis.jd_rising


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_rising_absent_where_sirius_never_rises() -> None:
    entries = sothic_rising(80.0, 0.0, 139, 140)
    assert entries == []


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_sothic_rising_respects_arcus_visionis_direction() -> None:
    easier_visibility = sothic_rising(29.8, 31.3, 139, 139, arcus_visionis=8.0)[0]
    harder_visibility = sothic_rising(29.8, 31.3, 139, 139, arcus_visionis=12.0)[0]

    assert harder_visibility.jd_rising >= easier_visibility.jd_rising
    assert harder_visibility.day_of_year >= easier_visibility.day_of_year
