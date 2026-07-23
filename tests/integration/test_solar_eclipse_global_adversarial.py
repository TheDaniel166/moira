from __future__ import annotations

import pytest

from moira.julian import julian_day


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]


@pytest.mark.parametrize(
    ("seed", "kind", "type_attribute"),
    (
        (julian_day(1991, 1, 1), "annular", "is_annular"),
        (julian_day(2015, 3, 1), "total", "is_total"),
        (julian_day(2048, 1, 1), "hybrid", "is_hybrid"),
    ),
)
def test_central_global_products_survive_fold_polar_and_hybrid_geometry(
    eclipse_calculator,
    seed: float,
    kind: str,
    type_attribute: str,
) -> None:
    result = eclipse_calculator.solar_global_circumstances(seed, kind=kind)

    assert getattr(result.event.data.eclipse_type, type_attribute)
    assert result.umbral_contacts is not None
    assert result.first_central_line_limit is not None
    assert result.last_central_line_limit is not None
    assert result.greatest_duration is not None
    assert (
        result.footprint.contacts.p1.point.jd_ut
        < result.umbral_contacts.u1.epoch.jd_ut1
        < result.umbral_contacts.u2.epoch.jd_ut1
        < result.event.jd_ut
        < result.umbral_contacts.u3.epoch.jd_ut1
        < result.umbral_contacts.u4.epoch.jd_ut1
        < result.footprint.contacts.p4.point.jd_ut
    )
    assert result.greatest_duration.central_duration_seconds > 0.0
    for conjunction in (
        result.equatorial_conjunction,
        result.ecliptic_conjunction,
    ):
        assert (
            result.footprint.contacts.p1.point.jd_ut
            < conjunction.epoch.jd_ut1
            < result.footprint.contacts.p4.point.jd_ut
        )
        assert abs(conjunction.epoch.jd_ut1 - result.event.jd_ut) < 0.25

    if kind == "hybrid":
        assert result.greatest_duration.epoch.jd_ut1 == pytest.approx(
            result.first_central_line_limit.epoch.jd_ut1,
            abs=1.0e-10,
        )
        assert result.greatest_duration.path_width_km == 0.0
