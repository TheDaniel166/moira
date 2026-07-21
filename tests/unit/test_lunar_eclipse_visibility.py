"""Global lunar-eclipse visibility-map contracts and geometry."""

from __future__ import annotations

import math

import pytest

import moira
import moira.facade as facade
import moira.sky.eclipse as sky_eclipse
from moira.constants import Body
from moira.eclipse import (
    EARTH_RADIUS_KM,
    EclipseCalculator,
    LunarEclipseVisibilityContactKind,
    LunarEclipseVisibilityLimit,
    LunarEclipseVisibilityMap,
    LunarEclipseVisibilityPoint,
    _WGS84_POLAR_RADIUS_KM,
    _earth_fixed_lunar_reception_vector,
)
from moira.planets import sky_position_at


def test_lunar_visibility_public_exports_share_governing_identity() -> None:
    names = (
        "LunarEclipseVisibilityContactKind",
        "LunarEclipseVisibilityPoint",
        "LunarEclipseVisibilityLimit",
        "LunarEclipseVisibilityMap",
    )
    for name in names:
        assert getattr(moira, name) is getattr(facade, name)
        assert getattr(sky_eclipse, name) is getattr(facade, name)
    assert hasattr(moira.Moira, "lunar_eclipse_visibility_map")
    assert hasattr(EclipseCalculator, "lunar_eclipse_visibility_map")


def test_lunar_visibility_point_and_limit_reject_invalid_geometry() -> None:
    with pytest.raises(ValueError, match="latitude_deg"):
        LunarEclipseVisibilityPoint(90.1, 0.0)
    with pytest.raises(ValueError, match="longitude_deg"):
        LunarEclipseVisibilityPoint(0.0, math.inf)

    points = tuple(LunarEclipseVisibilityPoint(0.0, float(index)) for index in range(9))
    with pytest.raises(ValueError, match="closed ring"):
        LunarEclipseVisibilityLimit(
            contact="p1",
            jd_ut=2_451_545.0,
            sublunar_point=LunarEclipseVisibilityPoint(0.0, 0.0),
            points=points,
        )


@pytest.mark.slow
def test_total_lunar_visibility_map_has_ordered_contact_rings_and_tangent_geometry(
    eclipse_calculator,
) -> None:
    visibility_map = eclipse_calculator.lunar_eclipse_visibility_map(
        2_451_560.0,
        kind="total",
        sample_count=9,
    )

    assert isinstance(visibility_map, LunarEclipseVisibilityMap)
    assert [limit.contact for limit in visibility_map.limits] == list(
        LunarEclipseVisibilityContactKind
    )
    assert visibility_map.ephemeris == "DE-0441LE-0441"
    assert visibility_map.surface_model == "WGS84_ZERO_ELEVATION"
    assert visibility_map.horizon_model == "RETARDED_GEOMETRIC_MOON_CENTER"
    assert visibility_map.atmospheric_refraction is False
    assert visibility_map.visible_side == "CONTAINS_SUBLUNAR_POINT"

    greatest = next(
        limit
        for limit in visibility_map.limits
        if limit.contact is LunarEclipseVisibilityContactKind.GREATEST
    )
    moon_itrf = _earth_fixed_lunar_reception_vector(
        eclipse_calculator,
        greatest.jd_ut,
    )
    a = EARTH_RADIUS_KM
    b = _WGS84_POLAR_RADIUS_KM
    eccentricity_squared = 1.0 - (b * b) / (a * a)

    for point in greatest.points[:-1]:
        latitude = math.radians(point.latitude_deg)
        longitude = math.radians(point.longitude_deg)
        prime_vertical = a / math.sqrt(
            1.0 - eccentricity_squared * math.sin(latitude) ** 2
        )
        observer = (
            prime_vertical * math.cos(latitude) * math.cos(longitude),
            prime_vertical * math.cos(latitude) * math.sin(longitude),
            prime_vertical * (1.0 - eccentricity_squared) * math.sin(latitude),
        )
        normal = (observer[0] / (a * a), observer[1] / (a * a), observer[2] / (b * b))
        sightline = tuple(moon_itrf[index] - observer[index] for index in range(3))
        normalized_tangency = sum(
            normal[index] * sightline[index] for index in range(3)
        ) / math.sqrt(
            sum(value * value for value in normal)
            * sum(value * value for value in sightline)
        )
        assert abs(normalized_tangency) < 2.0e-14

        direct = sky_position_at(
            Body.MOON,
            greatest.jd_ut,
            point.latitude_deg,
            point.longitude_deg,
            reader=eclipse_calculator._reader,
            aberration=False,
            refraction=False,
        )
        assert abs(direct.altitude) < 2.0e-4

    sublunar = greatest.sublunar_point
    direct_sublunar = sky_position_at(
        Body.MOON,
        greatest.jd_ut,
        sublunar.latitude_deg,
        sublunar.longitude_deg,
        reader=eclipse_calculator._reader,
        aberration=False,
        refraction=False,
    )
    assert direct_sublunar.altitude > 89.999


@pytest.mark.slow
@pytest.mark.parametrize(
    ("kind", "expected_contacts"),
    (
        ("partial", ("p1", "u1", "greatest", "u4", "p4")),
        ("penumbral", ("p1", "greatest", "p4")),
    ),
)
def test_lunar_visibility_map_emits_only_contacts_that_occur(
    eclipse_calculator,
    kind: str,
    expected_contacts: tuple[str, ...],
) -> None:
    visibility_map = eclipse_calculator.lunar_eclipse_visibility_map(
        2_451_545.0,
        kind=kind,
        sample_count=9,
    )
    assert tuple(limit.contact.value for limit in visibility_map.limits) == expected_contacts


def test_lunar_visibility_map_validates_density_before_search() -> None:
    calculator = EclipseCalculator(reader=object())
    with pytest.raises(TypeError, match="sample_count"):
        calculator.lunar_eclipse_visibility_map(2_451_545.0, sample_count=True)
    with pytest.raises(ValueError, match="between 9 and 721"):
        calculator.lunar_eclipse_visibility_map(2_451_545.0, sample_count=8)
