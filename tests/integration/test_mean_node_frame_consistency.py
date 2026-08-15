from __future__ import annotations

from datetime import datetime, timezone
import math

import pytest

from moira.julian import centuries_from_j2000, jd_from_datetime, tt_to_ut, ut_to_tt
from moira.nodes import mean_lilith, mean_node
from moira.obliquity import nutation

erfa = pytest.importorskip("erfa")


def _angular_difference_arcsec(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2314654.0, id="1625"),
        pytest.param(2450333.25, id="1996"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_node_mean_equinox_matches_iers_erfa(jd_tt: float) -> None:
    """Authority validation against ERFA's IERS 2003 faom03 argument."""
    jd_ut = tt_to_ut(jd_tt)
    T = centuries_from_j2000(jd_tt)
    expected = math.degrees(erfa.faom03(T)) % 360.0

    actual = mean_node(jd_ut, nutation=False).longitude

    assert abs(_angular_difference_arcsec(actual, expected)) < 1.0e-5


@pytest.mark.parametrize(
    "jd_ut",
    [
        pytest.param(2439528.1944444445, id="1967"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_node_true_frame_differs_from_mean_frame_by_dpsi(jd_ut: float) -> None:
    """Frame invariant: true-equinox longitude is mean longitude plus Δψ."""
    jd_tt = ut_to_tt(jd_ut)
    dpsi_deg, _ = nutation(jd_tt)
    mean_longitude = mean_node(jd_ut, nutation=False).longitude
    true_longitude = mean_node(jd_ut, nutation=True).longitude

    assert abs(
        _angular_difference_arcsec(
            true_longitude,
            (mean_longitude + dpsi_deg) % 360.0,
        )
    ) < 1.0e-8
    assert mean_node(jd_ut).longitude == true_longitude


@pytest.mark.parametrize(
    "jd_ut",
    [
        pytest.param(2439528.1944444445, id="1967"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_node_speed_matches_mean_equinox_polynomial_rate(jd_ut: float) -> None:
    """The reported speed is the derivative of the governing mean argument."""
    step_days = 0.01
    before = mean_node(jd_ut - step_days, nutation=False).longitude
    after = mean_node(jd_ut + step_days, nutation=False).longitude
    finite_difference = (
        ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step_days)
    )

    actual = mean_node(jd_ut, nutation=False)

    assert actual.speed == pytest.approx(finite_difference, abs=2.0e-9)


@pytest.mark.parametrize(
    ("jd_tt", "swiss_mean_node"),
    [
        pytest.param(
            2314654.0,
            173.96717511336527,
            id="swe_calc-ipl10-1625",
        ),
        pytest.param(
            2450333.25,
            189.21224137130957,
            id="swe_nod_aps-method1-1996",
        ),
    ],
)
def test_mean_node_true_frame_is_corroborated_by_shipped_swiss_fixture(
    jd_tt: float,
    swiss_mean_node: float,
) -> None:
    """Secondary corroboration, not primary proof.

    Provenance: ``tests/fixtures/swe_t.exp``, Swiss Ephemeris 2.10.02a.
    The 1625 value is ``swe_calc`` body 10 with ``SEFLG_SPEED``; the 1996
    value is the Moon's ascending node from ``swe_nod_aps`` method 1.
    Both use the fixture's default true-equinox-of-date convention. The
    one-arcsecond tolerance admits historical model differences; the IERS
    and frame invariants above carry the primary proof burden.
    """
    actual = mean_node(tt_to_ut(jd_tt)).longitude

    assert abs(_angular_difference_arcsec(actual, swiss_mean_node)) < 1.0


@pytest.mark.parametrize(
    "jd_ut",
    [
        pytest.param(2439528.1944444445, id="1967"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_lilith_uses_the_same_explicit_equinox_policy(jd_ut: float) -> None:
    """Mean Lilith must not remain the chart's hidden mean-frame exception."""
    jd_tt = ut_to_tt(jd_ut)
    dpsi_deg, _ = nutation(jd_tt)
    mean_longitude = mean_lilith(jd_ut, nutation=False).longitude
    true_longitude = mean_lilith(jd_ut, nutation=True).longitude

    assert abs(
        _angular_difference_arcsec(
            true_longitude,
            (mean_longitude + dpsi_deg) % 360.0,
        )
    ) < 1.0e-8
    assert mean_lilith(jd_ut).longitude == true_longitude


@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2314654.0, id="1625"),
        pytest.param(2450333.25, id="1996"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_lilith_mean_equinox_matches_iers_erfa(jd_tt: float) -> None:
    """Authority validation against ERFA IERS 2003 F + Ω − l + 180°."""
    jd_ut = tt_to_ut(jd_tt)
    T = centuries_from_j2000(jd_tt)
    expected = (
        math.degrees(erfa.faf03(T) + erfa.faom03(T) - erfa.fal03(T)) + 180.0
    ) % 360.0

    actual = mean_lilith(jd_ut, nutation=False).longitude

    assert abs(_angular_difference_arcsec(actual, expected)) < 1.0e-5


@pytest.mark.parametrize(
    "jd_ut",
    [
        pytest.param(2439528.1944444445, id="1967"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_lilith_speed_matches_mean_equinox_polynomial_rate(jd_ut: float) -> None:
    """The reported speed is the derivative of the governing mean argument."""
    step_days = 0.01
    before = mean_lilith(jd_ut - step_days, nutation=False).longitude
    after = mean_lilith(jd_ut + step_days, nutation=False).longitude
    finite_difference = (
        ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step_days)
    )

    actual = mean_lilith(jd_ut, nutation=False)

    assert actual.speed == pytest.approx(finite_difference, abs=2.0e-9)


@pytest.mark.parametrize(
    ("when", "swiss_mean_apog"),
    [
        pytest.param(
            datetime(1995, 7, 4, 9, 5, tzinfo=timezone.utc),
            80.3030,
            id="issue-18-1995-07-04",
        ),
        pytest.param(
            datetime(1955, 2, 8, 18, 45, tzinfo=timezone.utc),
            236.7037,
            id="issue-18-1955-02-08",
        ),
    ],
)
def test_mean_lilith_swiss_mean_apog_residual_is_a_series_difference(
    when: datetime,
    swiss_mean_apog: float,
) -> None:
    """Secondary corroboration, not a parity target.

    Provenance: GitHub TheDaniel166/moira#18, pyswisseph 2.10.3.2
    ``swe.calc_ut(..., swe.MEAN_APOG)`` on the reporter's UTC instants.
    Swiss ``SE_MEAN_APOG`` keeps ELP periodic terms inside a quantity
    still labelled mean. Moira's ``Body.LILITH`` is the IERS secular
    mean. The ±10′ band admits that known series difference. Shrinking
    the band toward Swiss digits is out of scope.
    """
    actual = mean_lilith(jd_from_datetime(when)).longitude
    residual_arcmin = abs(_angular_difference_arcsec(actual, swiss_mean_apog)) / 60.0

    assert residual_arcmin < 10.0
