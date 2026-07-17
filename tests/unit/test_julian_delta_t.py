from __future__ import annotations

from datetime import datetime, timezone
import math

import pytest

import moira.julian as julian_module
from moira.julian import (
    _DELTA_T_HPIERS_2016,
    _EOP_HANDOFF_WINDOW_DAYS,
    _TIDAL_NDOT_DE441,
    _TIDAL_NDOT_HPIERS,
    _TIDAL_NDOT_POLYNOMIAL,
    _load_delta_t_hpiers_2016,
    _continuous_decimal_year_from_jd,
    _tidacc_correction,
    _ut1_to_utc,
    calendar_datetime_from_jd,
    decimal_year,
    decimal_year_from_jd,
    delta_t,
    delta_t_from_jd,
    delta_t_nasa_canon,
    datetime_from_jd,
    DeltaTPolicy,
    EOPRegistry,
    jd_from_datetime,
    julian_day,
    safe_datetime_from_jd,
    tai_minus_utc,
    tai_to_tt,
    tt_to_ut,
    tt_to_ut_nasa_canon,
    tt_to_tdb,
    ut_to_tt,
    ut_to_tt_nasa_canon,
    utc_to_tai,
    utc_to_tt,
    utc_to_ut1,
)


def test_decimal_year_uses_mid_month_convention() -> None:
    assert decimal_year(2000, 1) == 2000.0416666666667
    assert decimal_year(2000, 7) == 2000.5416666666667


def test_decimal_year_from_jd_tracks_calendar_month() -> None:
    jd = julian_day(2000, 7, 1, 0.0)
    assert decimal_year_from_jd(jd) == 2000.5416666666667


def test_continuous_decimal_year_tracks_exact_leap_year_fraction() -> None:
    assert _continuous_decimal_year_from_jd(julian_day(2000, 1, 1)) == 2000.0
    assert _continuous_decimal_year_from_jd(julian_day(2000, 7, 2)) == pytest.approx(
        2000.5,
        abs=1.0e-12,
    )
    assert _continuous_decimal_year_from_jd(julian_day(2001, 1, 1)) == 2001.0


def test_default_jd_delta_t_has_no_nasa_month_midpoint_step() -> None:
    boundary = julian_day(1900, 2, 1)
    before = math.nextafter(boundary, -math.inf)
    assert abs(delta_t_from_jd(boundary) - delta_t_from_jd(before)) < 1.0e-4


@pytest.mark.parametrize("year", (-1000, 1000, 1900, 2150))
def test_default_tt_roundtrip_is_invertible_across_calendar_months(year: int) -> None:
    for month in range(1, 13):
        jd_ut1 = julian_day(year, month, 1, 12.0)
        recovered = tt_to_ut(ut_to_tt(jd_ut1))
        assert abs(recovered - jd_ut1) <= 2.0 * math.ulp(jd_ut1)


def test_delta_t_interpolates_hpiers_mean_in_the_atomic_era() -> None:
    assert delta_t(1962.5) == pytest.approx(33.78, abs=1e-12)


def test_delta_t_preserves_hpiers_source_basis_before_atomic_time() -> None:
    raw = dict(_DELTA_T_HPIERS_2016)
    for year in (-500.0, 1900.0, 1950.0):
        assert delta_t(year) == pytest.approx(raw[year], abs=1e-12)


def test_delta_t_interpolates_raw_hpiers_table() -> None:
    assert delta_t(1925.0) == pytest.approx(23.79, abs=1e-12)


def test_tidal_acceleration_correction_has_source_owned_sign_and_reference() -> None:
    year = -1000.0
    t = (year - 1955.0) / 100.0
    polynomial_expected = -0.91072 * (
        _TIDAL_NDOT_DE441 - _TIDAL_NDOT_POLYNOMIAL
    ) * t * t
    hpiers_expected = -0.91072 * (
        _TIDAL_NDOT_DE441 - _TIDAL_NDOT_HPIERS
    ) * t * t

    assert _tidacc_correction(
        year, _TIDAL_NDOT_POLYNOMIAL, _TIDAL_NDOT_DE441
    ) == pytest.approx(
        polynomial_expected, abs=1e-12
    )
    assert _tidacc_correction(
        year, _TIDAL_NDOT_HPIERS, _TIDAL_NDOT_DE441
    ) == pytest.approx(
        hpiers_expected, abs=1e-12
    )
    assert polynomial_expected < 0.0
    assert hpiers_expected > 0.0
    assert _tidacc_correction(
        1955.0, _TIDAL_NDOT_HPIERS, _TIDAL_NDOT_DE441
    ) == 0.0
    assert _tidacc_correction(
        2006.0, _TIDAL_NDOT_HPIERS, _TIDAL_NDOT_DE441
    ) > 0.0


def test_generic_delta_t_does_not_apply_an_ambient_ephemeris_correction() -> None:
    raw = dict(_DELTA_T_HPIERS_2016)
    correction = _tidacc_correction(
        -1000.0,
        _TIDAL_NDOT_HPIERS,
        _TIDAL_NDOT_DE441,
    )
    assert correction != 0.0
    assert delta_t(-1000.0) == raw[-1000.0]


def test_ancient_source_floor_has_an_explicit_century_c0_bridge() -> None:
    start = -2100.0
    end = -2000.0
    epsilon = 1.0e-7
    polynomial_start = -20.0 + 32.0 * ((start - 1820.0) / 100.0) ** 2

    assert delta_t(start) == pytest.approx(polynomial_start, abs=1.0e-12)
    assert delta_t(end) == pytest.approx(dict(_DELTA_T_HPIERS_2016)[end], abs=1.0e-12)
    assert delta_t(start - epsilon) == pytest.approx(delta_t(start + epsilon), abs=1.0e-3)
    assert delta_t(end - epsilon) == pytest.approx(delta_t(end + epsilon), abs=1.0e-3)


def test_hpiers_owns_the_mean_until_the_explicit_annual_bridge() -> None:
    raw = dict(_DELTA_T_HPIERS_2016)
    for year in (1955.5, 1962.0, 1962.5, 2000.0, 2010.0, 2014.0, 2014.5, 2015.0):
        assert delta_t(year) == pytest.approx(raw[year], abs=1e-12)


def test_hpiers_modern_block_preserves_source_declared_half_year_epochs() -> None:
    raw = dict(_DELTA_T_HPIERS_2016)
    assert raw[1971.5] == 41.49
    assert raw[1972.0] == 42.04
    assert raw[1972.5] == 42.59
    assert raw[1974.0] == 44.24


def test_modern_aggregate_means_use_representative_sample_epochs() -> None:
    aggregates = dict(julian_module._DELTA_T_ANNUAL)
    first_epoch = julian_module._monthly_mean_representative_epoch(2015, 12)
    final_epoch = julian_module._monthly_mean_representative_epoch(2026, 4)

    assert aggregates[first_epoch] == 67.84
    assert aggregates[final_epoch] == 69.12
    assert abs(delta_t(2015.0) - 67.6439) <= 0.06
    assert abs(delta_t(2015.5) - 67.8606) <= 0.06
    assert abs(delta_t(2026.0) - 69.1099) <= 0.06


def test_aggregate_surface_is_within_policy_scale_of_packaged_daily_eop() -> None:
    """Packaged-snapshot corroboration, not independent external validation."""

    first = julian_day(2015, 1, 1)
    stop = julian_day(2026, 5, 1)
    max_residual = 0.0
    for day in range(int(stop - first)):
        jd_utc = first + day
        year = _continuous_decimal_year_from_jd(jd_utc)
        eop_total = delta_t_from_jd(utc_to_ut1(jd_utc))
        max_residual = max(max_residual, abs(delta_t(year) - eop_total))
    assert max_residual <= 0.06


def test_canonical_and_physical_hpiers_loaders_admit_the_same_means() -> None:
    from moira.delta_t_physical import _load_smh2016_table

    assert _DELTA_T_HPIERS_2016 == _load_smh2016_table()


def test_canonical_hpiers_loader_keeps_declared_later_conflict_row(tmp_path) -> None:
    path = tmp_path / "delta_t.txt"
    path.write_text(
        "-2000 46800 2520\n1850 9.3 0.1\n1850 9.32 0.1\n2016 68.04 0.05\n",
        encoding="utf-8",
    )
    assert _load_delta_t_hpiers_2016(path) == (
        (-2000.0, 46800.0),
        (1850.0, 9.32),
        (2016.0, 68.04),
    )


@pytest.mark.parametrize(
    "contents, message",
    (
        ("-2000 46800\n2016 68 0.05\n", "quoted error"),
        ("-2000 46800 2520\n0 nan 90\n2016 68 0.05\n", "non-finite"),
        ("-2000 46800 2520\n0 10570 -1\n2016 68 0.05\n", "negative"),
        ("-2000 46800 2520\n10 100 1\n0 90 1\n2016 68 0.05\n", "non-decreasing"),
        ("-2000 46800 2520\n0 10570 90\n0 10571 90\n2016 68 0.05\n", "conflicting duplicate"),
        ("0 10570 90\n2016 68 0.05\n", "coverage"),
        ("# no data\n", "empty"),
    ),
)
def test_canonical_hpiers_loader_fails_closed_on_invalid_authority_data(
    tmp_path,
    contents: str,
    message: str,
) -> None:
    path = tmp_path / "delta_t.txt"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        _load_delta_t_hpiers_2016(path)


def test_canonical_hpiers_loader_fails_closed_when_authority_file_is_missing(
    tmp_path,
) -> None:
    with pytest.raises(FileNotFoundError, match="authority table is missing"):
        _load_delta_t_hpiers_2016(tmp_path / "missing.txt")


def test_observation_boundary_tracks_an_appended_annual_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_epoch = julian_module._monthly_mean_representative_epoch(2027, 12)
    extended = julian_module._DELTA_T_ANNUAL + ((new_epoch, 70.0),)
    monkeypatch.setattr(julian_module, "_DELTA_T_ANNUAL", extended)

    boundary = julian_module._delta_t_observation_boundary()
    previous_epoch, previous_total = julian_module._DELTA_T_ANNUAL[-2]
    expected_slope = (70.0 - previous_total) / (new_epoch - previous_epoch)
    assert (boundary.year, boundary.total, boundary.slope) == pytest.approx(
        (new_epoch, 70.0, expected_slope), abs=1e-12
    )
    epsilon = 1e-7
    left = delta_t(boundary.year - epsilon)
    at = delta_t(boundary.year)
    right = delta_t(boundary.year + epsilon)
    assert left == pytest.approx(at, abs=1e-6)
    assert right == pytest.approx(at, abs=1e-6)


def test_observation_boundary_can_move_earlier_without_recursion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shortened = julian_module._DELTA_T_ANNUAL[:-1]
    monkeypatch.setattr(julian_module, "_DELTA_T_ANNUAL", shortened)

    boundary = julian_module._delta_t_observation_boundary()
    assert boundary.year == julian_module._monthly_mean_representative_epoch(2025, 12)
    assert math.isfinite(delta_t(2026.0))
    assert delta_t(boundary.year + 1e-7) == pytest.approx(
        delta_t(boundary.year), abs=1e-6
    )


def test_ut_to_tt_uses_decimal_year_not_integer_year_only() -> None:
    jd = julian_day(2150, 7, 1, 0.0)
    tt_decimal = ut_to_tt(jd)
    tt_integer = ut_to_tt(jd, year=2150.0)
    assert abs((tt_decimal - tt_integer) * 86400.0) > 0.1


@pytest.mark.parametrize("year", (-1000, 1000, 2020, 2150, 5000))
@pytest.mark.parametrize(
    "policy",
    (
        None,
        DeltaTPolicy(model="physical"),
        DeltaTPolicy(model="nasa_canon"),
        DeltaTPolicy(model="fixed", fixed_delta_t=123.456),
    ),
    ids=("hybrid", "physical", "nasa_canon", "fixed"),
)
def test_explicit_year_coordinate_roundtrips_generic_tt_conversion(
    year: int,
    policy: DeltaTPolicy | None,
) -> None:
    jd_ut = julian_day(year, 7, 1)
    year_coordinate = year + 0.5
    jd_tt = ut_to_tt(
        jd_ut,
        year=year_coordinate,
        delta_t_policy=policy,
    )
    recovered = tt_to_ut(
        jd_tt,
        year=year_coordinate,
        delta_t_policy=policy,
    )
    assert recovered == pytest.approx(jd_ut, abs=math.ulp(jd_ut))


@pytest.mark.parametrize("year", (-1000, 1000, 2150, 5000))
def test_explicit_year_coordinate_roundtrips_nasa_canon_helpers(year: int) -> None:
    jd_ut = julian_day(year, 7, 1)
    year_coordinate = year + 0.5
    jd_tt = ut_to_tt_nasa_canon(jd_ut, year=year_coordinate)
    recovered = tt_to_ut_nasa_canon(jd_tt, year=year_coordinate)
    assert recovered == pytest.approx(jd_ut, abs=math.ulp(jd_ut))


@pytest.mark.parametrize(
    "forward,inverse",
    (
        (
            ut_to_tt_nasa_canon,
            tt_to_ut_nasa_canon,
        ),
        (
            lambda jd: ut_to_tt(
                jd,
                delta_t_policy=DeltaTPolicy(model="nasa_canon"),
            ),
            lambda jd: tt_to_ut(
                jd,
                delta_t_policy=DeltaTPolicy(model="nasa_canon"),
            ),
        ),
    ),
    ids=("standalone", "policy"),
)
def test_implicit_nasa_clock_coordinate_is_monotonic_at_ancient_year_seam(
    forward,
    inverse,
) -> None:
    boundary = julian_day(-2000, 1, 1)
    one_second = 1.0 / 86400.0
    samples_ut = (boundary - one_second, boundary, boundary + one_second)
    samples_tt = tuple(forward(jd) for jd in samples_ut)

    assert samples_tt[0] < samples_tt[1] < samples_tt[2]
    for jd_ut, jd_tt in zip(samples_ut, samples_tt):
        assert inverse(jd_tt) == pytest.approx(jd_ut, abs=math.ulp(jd_ut))


def test_implicit_nasa_inverse_rejects_raw_polynomial_overlap() -> None:
    boundary_ut = julian_day(1600, 1, 1)
    left_ut = math.nextafter(boundary_ut, -math.inf)
    left_tt = ut_to_tt_nasa_canon(left_ut)
    boundary_tt = ut_to_tt_nasa_canon(boundary_ut)
    assert boundary_tt < left_tt
    ambiguous_tt = (left_tt + boundary_tt) / 2.0

    with pytest.raises(ValueError, match="1600 model seam"):
        tt_to_ut_nasa_canon(ambiguous_tt)
    with pytest.raises(ValueError, match="1600 model seam"):
        tt_to_ut(
            ambiguous_tt,
            delta_t_policy=DeltaTPolicy(model="nasa_canon"),
        )


@pytest.mark.parametrize("month", range(1, 13))
def test_utc_ut1_tt_clock_is_coherent_through_civil_2026(month: int) -> None:
    jd_utc = jd_from_datetime(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
    jd_ut1 = utc_to_ut1(jd_utc)
    jd_tt = utc_to_tt(jd_utc)

    assert ut_to_tt(jd_ut1) == pytest.approx(jd_tt, abs=5.0e-10)
    assert tt_to_ut(jd_tt) == pytest.approx(jd_ut1, abs=5.0e-10)
    assert delta_t_from_jd(jd_ut1) == pytest.approx(
        (jd_tt - jd_ut1) * 86400.0,
        abs=5.0e-5,
    )


@pytest.mark.parametrize(
    "jd_civil",
    (
        julian_day(1900, 1, 1),
        julian_day(1000, 1, 1),
        julian_day(-1000, 1, 1),
    ),
)
def test_pre_1972_civil_clock_preserves_historical_ut1_proxy(jd_civil: float) -> None:
    """A placeholder atomic offset must not displace historical chart time."""

    jd_ut1 = utc_to_ut1(jd_civil)
    jd_tt = utc_to_tt(jd_civil)

    assert jd_ut1 == jd_civil
    assert jd_tt == pytest.approx(ut_to_tt(jd_ut1), abs=1.0e-12)
    assert (jd_tt - jd_ut1) * 86400.0 == pytest.approx(
        delta_t_from_jd(jd_ut1), abs=5.0e-5
    )


def test_1972_atomic_boundary_uses_admitted_utc_chain() -> None:
    boundary = julian_module.LEAP_SECONDS[0][0]

    assert utc_to_tt(boundary) == tai_to_tt(utc_to_tai(boundary))


@pytest.mark.parametrize(
    ("year", "month", "day", "expected_seconds"),
    (
        (1960, 1, 1, 0.9434820),
        (1961, 1, 1, 1.4228180),
        (1961, 8, 1, 1.6475700),
        (1965, 7, 1, 3.9747060),
        (1968, 2, 1, 6.1856820),
        (1971, 12, 31, 9.8896500),
        (1972, 1, 1, 10.0),
    ),
)
def test_tai_minus_utc_matches_sofa_pre_1972_history(
    year: int,
    month: int,
    day: int,
    expected_seconds: float,
) -> None:
    jd_utc = julian_day(year, month, day)
    assert tai_minus_utc(jd_utc) == pytest.approx(expected_seconds, abs=1.0e-12)
    assert (utc_to_tai(jd_utc) - jd_utc) * 86400.0 == pytest.approx(
        expected_seconds,
        abs=5.0e-5,
    )


def test_atomic_helpers_reject_epochs_before_utc_drift_authority() -> None:
    jd_utc = julian_day(1959, 12, 31)
    with pytest.raises(ValueError, match="only from 1960-01-01"):
        tai_minus_utc(jd_utc)
    with pytest.raises(ValueError, match="only from 1960-01-01"):
        utc_to_tai(jd_utc)


def test_1972_proxy_to_atomic_handoff_is_monotonic_and_invertible() -> None:
    boundary = julian_module.LEAP_SECONDS[0][0]
    samples_utc = tuple(boundary - 1.0 + index / 24.0 for index in range(25))
    samples_ut1 = tuple(utc_to_ut1(value) for value in samples_utc)

    assert all(left < right for left, right in zip(samples_ut1, samples_ut1[1:]))
    for jd_utc, jd_ut1 in zip(samples_utc, samples_ut1):
        recovered = _ut1_to_utc(jd_ut1)
        assert abs(recovered - jd_utc) <= math.ulp(jd_utc)


@pytest.mark.parametrize(
    "dt",
    (
        datetime(2025, 1, 1, 12, tzinfo=timezone.utc),
        datetime(2150, 7, 1, 12, tzinfo=timezone.utc),
        datetime(1900, 1, 1, 12, tzinfo=timezone.utc),
    ),
)
def test_ut1_to_utc_roundtrips_all_clock_policy_eras(dt: datetime) -> None:
    jd_utc = jd_from_datetime(dt)
    assert _ut1_to_utc(utc_to_ut1(jd_utc)) == pytest.approx(jd_utc, abs=1.0e-12)


@pytest.mark.parametrize("hour", (0, 6, 12, 18, 23))
def test_ut1_to_utc_does_not_smear_a_leap_second(hour: int) -> None:
    dt = datetime(2016, 12, 31, hour, 0, 0, tzinfo=timezone.utc)
    jd_utc = jd_from_datetime(dt)
    assert _ut1_to_utc(utc_to_ut1(jd_utc)) == pytest.approx(jd_utc, abs=1.0e-12)


def test_eop_interpolation_does_not_smear_utc_leap_second() -> None:
    before = jd_from_datetime(datetime(2016, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
    after = jd_from_datetime(datetime(2017, 1, 1, 0, 0, 0, tzinfo=timezone.utc))

    assert EOPRegistry.get_dut1(before) < 0.0
    assert EOPRegistry.get_dut1(after) > 0.0

    dt_before = delta_t_from_jd(utc_to_ut1(before))
    dt_after = delta_t_from_jd(utc_to_ut1(after))
    assert abs(dt_after - dt_before) < 0.01
    assert ut_to_tt(utc_to_ut1(before)) == pytest.approx(utc_to_tt(before), abs=5.0e-10)
    assert ut_to_tt(utc_to_ut1(after)) == pytest.approx(utc_to_tt(after), abs=5.0e-10)


def test_eop_zero_dut1_is_admitted_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EOPRegistry, "_data", {60000: 0.0, 60001: 0.0})
    jd_utc = 2400000.5 + 60000.25

    assert EOPRegistry.get_dut1(jd_utc) == 0.0
    assert utc_to_ut1(jd_utc) == jd_utc


def test_eop_lookup_does_not_bridge_internal_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EOPRegistry, "_data", {60000: 0.1, 60002: 0.2})

    covered_ut1 = 2400000.5 + 60000.5 + 0.1 / 86400.0
    gap_ut1 = 2400000.5 + 60001.5
    assert EOPRegistry._delta_t_from_ut1(covered_ut1) is not None
    assert EOPRegistry._delta_t_from_ut1(gap_ut1) is None


def test_eop_model_handoff_is_c0_across_an_internal_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(EOPRegistry, "_data", {60000: 0.1, 60002: 0.2})
    data = EOPRegistry._ensure_loaded()
    left = EOPRegistry._segment_bounds(60000, data)
    right = EOPRegistry._segment_bounds(60002, data)
    assert left is not None and right is not None
    left_edge = left[2]
    right_edge = right[0]
    epsilon = 1e-8

    assert delta_t_from_jd(left_edge - epsilon) == pytest.approx(
        delta_t_from_jd(left_edge), abs=1e-6
    )
    assert delta_t_from_jd(right_edge - epsilon) == pytest.approx(
        delta_t_from_jd(right_edge), abs=1e-6
    )
    assert math.isfinite(delta_t_from_jd((left_edge + right_edge) / 2.0))


def test_outer_eop_reconciliation_is_local_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(EOPRegistry, "_data", {60000: 0.1})
    data = EOPRegistry._ensure_loaded()
    segment = EOPRegistry._segment_bounds(60000, data)
    assert segment is not None
    first_ut1, first_delta_t, last_ut1, last_delta_t = segment

    def source_total(jd_ut1: float) -> float:
        return delta_t(_continuous_decimal_year_from_jd(jd_ut1))

    before_window = first_ut1 - _EOP_HANDOFF_WINDOW_DAYS
    after_window = last_ut1 + _EOP_HANDOFF_WINDOW_DAYS
    assert delta_t_from_jd(before_window) == pytest.approx(
        source_total(before_window), abs=1.0e-12
    )
    assert delta_t_from_jd(after_window) == pytest.approx(
        source_total(after_window), abs=1.0e-12
    )

    epsilon = 1.0e-8
    assert delta_t_from_jd(first_ut1 - epsilon) == pytest.approx(
        first_delta_t, abs=1.0e-6
    )
    assert delta_t_from_jd(last_ut1 + epsilon) == pytest.approx(
        last_delta_t, abs=1.0e-6
    )


def test_far_historical_jd_uses_unmodified_source_model() -> None:
    jd_ut1 = julian_day(-1000, 6, 30, 12.0)
    assert delta_t_from_jd(jd_ut1) == pytest.approx(
        delta_t(_continuous_decimal_year_from_jd(jd_ut1)),
        abs=1.0e-12,
    )


@pytest.mark.parametrize(
    "contents",
    [
        "60000.5 0.1\n",
        "60000 nan\n",
        "60000 1.01\n",
        "60000 not-a-number\n",
        "60000\n",
        "60000 0.1 extra\n",
        "60001 0.1\n60000 0.2\n",
        "60000 0.1\n60000 0.2\n",
        "# comments only\n",
    ],
)
def test_eop_loader_rejects_malformed_existing_file_without_partial_cache(
    contents: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    path = tmp_path / "eop.txt"
    path.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(EOPRegistry, "_path", path)
    monkeypatch.setattr(EOPRegistry, "_data", None)

    with pytest.raises(ValueError, match="EOP|Malformed"):
        EOPRegistry._load()
    assert EOPRegistry._data is None


def test_eop_loader_allows_missing_file_as_explicit_empty_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(EOPRegistry, "_path", tmp_path / "missing.txt")
    monkeypatch.setattr(EOPRegistry, "_data", None)

    EOPRegistry._load()
    assert EOPRegistry._data == {}


def test_eop_final_row_governs_only_its_own_utc_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(EOPRegistry, "_data", {60000: 0.1})
    utc_start = 2400000.5 + 60000.0
    utc_midday = utc_start + 0.5
    utc_end = utc_start + 1.0
    ut1_midday = utc_midday + 0.1 / 86400.0
    ut1_end = utc_end + 0.1 / 86400.0

    assert EOPRegistry._dut1_optional(utc_midday) is not None
    assert EOPRegistry._delta_t_from_ut1(ut1_midday) is not None
    assert EOPRegistry._dut1_optional(utc_end) is None
    assert EOPRegistry._delta_t_from_ut1(ut1_end) is None


def test_real_eop_coverage_edges_are_c0_and_exactly_invertible() -> None:
    data = EOPRegistry._ensure_loaded()
    keys = EOPRegistry._ordered_mjds(data)
    assert keys
    first = EOPRegistry._segment_bounds(keys[0], data)
    last = EOPRegistry._segment_bounds(keys[-1], data)
    assert first is not None and last is not None
    epsilon = 1e-8

    for edge, measured_delta_t in ((first[0], first[1]), (last[2], last[3])):
        before = delta_t_from_jd(edge - epsilon)
        at = delta_t_from_jd(edge)
        after = delta_t_from_jd(edge + epsilon)
        assert before == pytest.approx(measured_delta_t, abs=1e-6)
        assert at == pytest.approx(measured_delta_t, abs=1e-6)
        assert after == pytest.approx(measured_delta_t, abs=1e-6)

        jd_tt = edge + measured_delta_t / 86400.0
        assert tt_to_ut(jd_tt) == pytest.approx(edge, abs=1e-12)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_public_clock_conversions_reject_nonfinite_values(value: float) -> None:
    for conversion in (
        delta_t,
        delta_t_from_jd,
        delta_t_nasa_canon,
        tai_minus_utc,
        utc_to_tai,
        tai_to_tt,
        utc_to_tt,
        utc_to_ut1,
        ut_to_tt,
        ut_to_tt_nasa_canon,
        tt_to_ut,
        tt_to_ut_nasa_canon,
        tt_to_tdb,
    ):
        with pytest.raises(ValueError, match="finite"):
            conversion(value)


@pytest.mark.parametrize("value", (1.0e100, -1.0e100))
def test_public_clock_conversions_reject_finite_unrepresentable_values(
    value: float,
) -> None:
    for conversion in (
        delta_t,
        delta_t_nasa_canon,
        delta_t_from_jd,
        tai_minus_utc,
        utc_to_tai,
        tai_to_tt,
        utc_to_tt,
        utc_to_ut1,
        _ut1_to_utc,
        ut_to_tt,
        ut_to_tt_nasa_canon,
        tt_to_ut,
        tt_to_ut_nasa_canon,
        tt_to_tdb,
    ):
        with pytest.raises(ValueError, match="representable"):
            conversion(value)


def test_nasa_canon_delta_t_matches_catalog_basis_for_ancient_eclipse_year() -> None:
    assert abs(delta_t_nasa_canon(-1800.67) - 41747.0) < 1.0


@pytest.mark.parametrize("year", (1955.0, 1975.0, 2005.0))
def test_nasa_canon_omits_lunar_ephemeris_correction_in_direct_era(year: float) -> None:
    """NASA declares no secular-acceleration correction for 1955–2005."""

    if year < 1961.0:
        t = year - 1950.0
        expected = 29.07 + 0.407 * t - t**2 / 233.0 + t**3 / 2547.0
    elif year < 1986.0:
        t = year - 1975.0
        expected = 45.45 + 1.067 * t - t**2 / 260.0 - t**3 / 718.0
    else:
        t = year - 2000.0
        expected = 62.92 + 0.32217 * t + 0.005589 * t**2

    assert delta_t_nasa_canon(year) == pytest.approx(expected, abs=1.0e-12)


def test_calendar_datetime_from_jd_supports_bce_years() -> None:
    jd = julian_day(-1321, 7, 20, 0.0)
    cal = calendar_datetime_from_jd(jd)
    assert cal.year == -1321
    assert cal.month == 7
    assert cal.day == 20
    assert cal.isoformat().startswith("-1321-07-20T00:00:00")


def test_calendar_datetime_from_jd_carries_rounded_bce_midnight() -> None:
    midnight = julian_day(-4802, 4, 1, 0.0)
    just_before = math.nextafter(midnight, -math.inf)

    cal = calendar_datetime_from_jd(just_before)

    assert (cal.year, cal.month, cal.day) == (-4802, 4, 1)
    assert (cal.hour, cal.minute, cal.second, cal.microsecond) == (0, 0, 0, 0)


def test_safe_datetime_from_jd_returns_none_for_bce() -> None:
    jd = julian_day(-500, 1, 1, 0.0)
    assert safe_datetime_from_jd(jd) is None


def test_datetime_from_jd_raises_helpful_error_for_bce() -> None:
    jd = julian_day(-500, 1, 1, 0.0)
    with pytest.raises(ValueError, match="calendar_datetime_from_jd"):
        datetime_from_jd(jd)
