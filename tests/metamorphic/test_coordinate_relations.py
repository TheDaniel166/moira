"""Reviewed public-coordinate metamorphic relations and boundary atlases."""

from __future__ import annotations

import math

from hypothesis import event, example, given, strategies as st, target
import pytest

from evidence.contracts import (
    COORDINATE_SPHERE_INTERIOR_COMPARISON,
    COORDINATE_SPHERE_POLAR_COMPARISON,
    LONGITUDE_QUOTIENT_COMPARISON,
)
from support.metamorphic import MetamorphicViolation
from support.metamorphic_coordinates import (
    COORDINATE_SPHERE_RELATION_ID,
    LONGITUDE_QUOTIENT_RELATION_ID,
    assert_longitude_quotient,
    assert_spherical_inverse,
    observe_longitude_quotient,
    observe_spherical_inverse,
)


pytestmark = [
    pytest.mark.metamorphic,
    pytest.mark.parallel(reason="read_only"),
]


_INTERIOR_VECTOR_LIMIT_DEG = float(
    COORDINATE_SPHERE_INTERIOR_COMPARISON.absolute
)
_POLAR_VECTOR_LIMIT_DEG = float(COORDINATE_SPHERE_POLAR_COMPARISON.absolute)
_LONGITUDE_PERIODIC_LIMIT_DEG = float(LONGITUDE_QUOTIENT_COMPARISON.absolute)


_QUOTIENT_ANGLES = (
    -0.0,
    0.0,
    math.nextafter(0.0, -math.inf),
    math.nextafter(0.0, math.inf),
    math.nextafter(180.0, -math.inf),
    180.0,
    math.nextafter(180.0, math.inf),
    math.nextafter(360.0, -math.inf),
    360.0,
    math.nextafter(360.0, math.inf),
    -360.0,
)


@pytest.mark.validation_contract(COORDINATE_SPHERE_RELATION_ID)
@example(0.0, -0.0, 0.0, 0.0, -0.0)
@example(360.0, 89.0, -360.0, -89.0, 30.0)
@given(
    ecliptic_longitude_deg=st.floats(
        min_value=-1440.0,
        max_value=1440.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    ecliptic_latitude_deg=st.floats(
        min_value=-89.0,
        max_value=89.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    equatorial_ra_deg=st.floats(
        min_value=-1440.0,
        max_value=1440.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    equatorial_declination_deg=st.floats(
        min_value=-89.0,
        max_value=89.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    obliquity_deg=st.floats(
        min_value=-30.0,
        max_value=30.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
)
def test_spherical_coordinate_inverse_relation(
    ecliptic_longitude_deg: float,
    ecliptic_latitude_deg: float,
    equatorial_ra_deg: float,
    equatorial_declination_deg: float,
    obliquity_deg: float,
) -> None:
    observation = observe_spherical_inverse(
        ecliptic_longitude_deg=ecliptic_longitude_deg,
        ecliptic_latitude_deg=ecliptic_latitude_deg,
        equatorial_ra_deg=equatorial_ra_deg,
        equatorial_declination_deg=equatorial_declination_deg,
        obliquity_deg=obliquity_deg,
    )
    target(
        observation.maximum_residual_deg,
        label="coordinate inverse angular residual degrees",
    )
    target(
        max(abs(ecliptic_latitude_deg), abs(equatorial_declination_deg)),
        label="source pole proximity",
    )
    event(f"signed-zero-obliquity={obliquity_deg == 0.0}")
    assert_spherical_inverse(
        observation,
        limit_deg=_INTERIOR_VECTOR_LIMIT_DEG,
    )


@pytest.mark.validation_contract(COORDINATE_SPHERE_RELATION_ID)
def test_spherical_coordinate_boundary_atlas() -> None:
    latitudes = (
        -90.0,
        math.nextafter(-90.0, 0.0),
        -89.999999,
        -0.0,
        0.0,
        89.999999,
        math.nextafter(90.0, 0.0),
        90.0,
    )
    for angle in _QUOTIENT_ANGLES:
        for latitude in latitudes:
            for obliquity in (-30.0, -0.0, 23.4392911, 30.0):
                observation = observe_spherical_inverse(
                    ecliptic_longitude_deg=angle,
                    ecliptic_latitude_deg=latitude,
                    equatorial_ra_deg=angle,
                    equatorial_declination_deg=latitude,
                    obliquity_deg=obliquity,
                )
                assert_spherical_inverse(
                    observation,
                    limit_deg=_POLAR_VECTOR_LIMIT_DEG,
                )


@pytest.mark.validation_contract(COORDINATE_SPHERE_RELATION_ID)
def test_spherical_coordinate_canary_detects_post_observation_bias() -> None:
    mutant_id = "P10-COORD-RECOVERED-LATITUDE-PLUS-ONE-DEGREE"
    observation = observe_spherical_inverse(
        ecliptic_longitude_deg=90.0,
        ecliptic_latitude_deg=30.0,
        equatorial_ra_deg=210.0,
        equatorial_declination_deg=-20.0,
        obliquity_deg=23.4392911,
        recovered_ecliptic_latitude_bias_deg=1.0,
    )
    with pytest.raises(MetamorphicViolation) as raised:
        assert_spherical_inverse(
            observation,
            limit_deg=_INTERIOR_VECTOR_LIMIT_DEG,
            mutant_id=mutant_id,
        )
    violation = raised.value
    assert violation.relation_id == COORDINATE_SPHERE_RELATION_ID
    assert violation.mutant_id == mutant_id
    assert violation.metric == "maximum unit-vector angular separation"
    assert violation.observed > violation.limit
    assert violation.limit == _INTERIOR_VECTOR_LIMIT_DEG


@pytest.mark.validation_contract(LONGITUDE_QUOTIENT_RELATION_ID)
@example(-0.0, 0)
@example(math.nextafter(0.0, -math.inf), 1)
@example(math.nextafter(360.0, math.inf), -1)
@given(
    angle_deg=st.floats(
        min_value=-360.0,
        max_value=360.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    period_shift=st.integers(min_value=-16, max_value=16),
)
def test_longitude_quotient_relation(
    angle_deg: float,
    period_shift: int,
) -> None:
    observation = observe_longitude_quotient(angle_deg, period_shift)
    target(
        observation.periodic_residual_deg,
        label="longitude period-shift residual degrees",
    )
    target(abs(period_shift), label="longitude period-shift magnitude")
    event(f"canonical-zero={observation.normalized_deg == 0.0}")
    assert_longitude_quotient(
        observation,
        limit_deg=_LONGITUDE_PERIODIC_LIMIT_DEG,
    )


@pytest.mark.validation_contract(LONGITUDE_QUOTIENT_RELATION_ID)
def test_longitude_quotient_boundary_atlas() -> None:
    for angle in _QUOTIENT_ANGLES:
        for period_shift in (-16, -1, 0, 1, 16):
            assert_longitude_quotient(
                observe_longitude_quotient(angle, period_shift),
                limit_deg=_LONGITUDE_PERIODIC_LIMIT_DEG,
            )


@pytest.mark.validation_contract(LONGITUDE_QUOTIENT_RELATION_ID)
def test_longitude_quotient_canary_detects_noncanonical_zero() -> None:
    mutant_id = "P10-LONGITUDE-CANONICAL-ZERO-TO-360"
    observation = observe_longitude_quotient(
        0.0,
        1,
        canonical_zero_to_360_mutant=True,
    )
    with pytest.raises(MetamorphicViolation) as raised:
        assert_longitude_quotient(
            observation,
            limit_deg=_LONGITUDE_PERIODIC_LIMIT_DEG,
            mutant_id=mutant_id,
        )
    violation = raised.value
    assert violation.relation_id == LONGITUDE_QUOTIENT_RELATION_ID
    assert violation.mutant_id == mutant_id
    assert violation.metric == "canonical longitude upper bound"
    assert violation.observed == 360.0
    assert violation.observed > violation.limit
