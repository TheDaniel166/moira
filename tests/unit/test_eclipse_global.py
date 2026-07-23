from __future__ import annotations

import math

import pytest

from moira._eclipse_solar_geometry import _circle_overlap_fraction
from moira.julian import julian_day


def test_circle_overlap_fraction_covers_all_geometric_branches() -> None:
    assert _circle_overlap_fraction(1.0, 1.0, 2.0) == 0.0
    assert _circle_overlap_fraction(1.0, 1.0, 0.0) == 1.0
    assert _circle_overlap_fraction(1.0, 0.5, 0.0) == pytest.approx(0.25)
    assert _circle_overlap_fraction(1.0, 2.0, 0.5) == 1.0
    partial = _circle_overlap_fraction(1.0, 1.0, 1.0)
    assert 0.0 < partial < 1.0
    assert partial == pytest.approx(
        2.0 / 3.0 - math.sqrt(3.0) / (2.0 * math.pi)
    )


@pytest.mark.parametrize(
    "values",
    [
        (0.0, 1.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, -0.1),
        (float("nan"), 1.0, 0.0),
    ],
)
def test_circle_overlap_fraction_rejects_invalid_geometry(
    values: tuple[float, float, float],
) -> None:
    with pytest.raises(ValueError):
        _circle_overlap_fraction(*values)


@pytest.mark.slow
def test_total_solar_global_circumstances_promote_existing_products(
    eclipse_calculator,
) -> None:
    result = eclipse_calculator.solar_global_circumstances(
        julian_day(2027, 7, 20),
        kind="total",
    )
    assert result.ephemeris == "DE-0441LE-0441"
    assert result.event == result.footprint.event
    assert result.greatest.epoch.jd_ut1 == pytest.approx(result.event.jd_ut)
    assert result.greatest.local_class == "total"
    assert result.greatest.magnitude > 1.0
    assert result.greatest.obscuration == 1.0
    assert result.greatest.path_width_km > 0.0
    assert result.greatest.central_duration_seconds > 0.0
    assert result.equatorial_conjunction.kind.value == "equatorial"
    assert result.ecliptic_conjunction.kind.value == "ecliptic"
    assert (
        result.equatorial_conjunction.epoch.jd_ut1
        < result.ecliptic_conjunction.epoch.jd_ut1
        < result.greatest.epoch.jd_ut1
    )
    assert result.first_central_line_limit is not None
    assert result.last_central_line_limit is not None
    assert (
        result.first_central_line_limit.epoch.jd_ut1
        < result.event.jd_ut
        < result.last_central_line_limit.epoch.jd_ut1
    )
    assert result.gamma_earth_radii == pytest.approx(
        math.copysign(
            math.hypot(result.besselian.x, result.besselian.y),
            result.besselian.y,
        )
    )
    assert result.umbral_contacts_admitted is True
    contacts = result.umbral_contacts
    assert contacts is not None
    assert (
        contacts.u1.epoch.jd_ut1
        < contacts.u2.epoch.jd_ut1
        < result.event.jd_ut
        < contacts.u3.epoch.jd_ut1
        < contacts.u4.epoch.jd_ut1
    )
    assert result.greatest_duration_admitted is True
    assert result.greatest_duration is not None
    assert (
        result.first_central_line_limit.epoch.jd_ut1
        < result.greatest_duration.epoch.jd_ut1
        < result.last_central_line_limit.epoch.jd_ut1
    )
    assert (
        result.greatest_duration.central_duration_seconds
        >= result.greatest.central_duration_seconds
    )


@pytest.mark.slow
def test_partial_solar_global_circumstances_do_not_invent_central_products(
    eclipse_calculator,
) -> None:
    result = eclipse_calculator.solar_global_circumstances(
        julian_day(2029, 6, 1),
        kind="partial",
    )
    assert result.greatest.local_class == "partial"
    assert 0.0 < result.greatest.magnitude < 1.0
    assert 0.0 < result.greatest.obscuration < 1.0
    assert result.greatest.path_width_km == 0.0
    assert result.greatest.central_duration_seconds == 0.0
    assert result.first_central_line_limit is None
    assert result.last_central_line_limit is None
    assert result.umbral_contacts_admitted is True
    assert result.umbral_contacts is None
    assert result.greatest_duration_admitted is True
    assert result.greatest_duration is None


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_solar_global_circumstances_reject_invalid_seed(
    eclipse_calculator,
    value: object,
) -> None:
    error = TypeError if value is True else ValueError
    with pytest.raises(error):
        eclipse_calculator.solar_global_circumstances(value)
