"""Reviewed hybrid UT1/TT inverse relation and time-boundary atlas."""

from __future__ import annotations

import math

from hypothesis import event, example, given, strategies as st, target
import pytest

from evidence.contracts import TIMESCALE_HYBRID_INVERSE_COMPARISON
from moira.julian import tt_to_ut, ut_to_tt
from support.metamorphic import MetamorphicViolation
from support.metamorphic_timescales import (
    HYBRID_TIMESCALE_RELATION_ID,
    REVIEWED_MAX_JD_UT1,
    REVIEWED_MIN_JD_UT1,
    assert_hybrid_inverse,
    observe_hybrid_inverse,
)


pytestmark = [
    pytest.mark.metamorphic,
    pytest.mark.parallel(reason="read_only"),
    pytest.mark.validation_contract(HYBRID_TIMESCALE_RELATION_ID),
]


_HYBRID_INVERSE_LIMIT_ULPS = float(
    TIMESCALE_HYBRID_INVERSE_COMPARISON.absolute
)
_J2000 = 2_451_545.0
_BOUNDARY_JDS = (
    (-1000, 1_355_817.5),
    (-500, 1_538_438.5),
    (0, 1_721_059.5),
    (500, 1_903_681.5),
    (1600, 2_305_447.5),
    (1700, 2_341_972.5),
    (1800, 2_378_496.5),
    (1860, 2_400_410.5),
    (1900, 2_415_020.5),
    (1920, 2_422_324.5),
    (1941, 2_429_995.5),
    (1955, 2_435_108.5),
    (1961, 2_437_300.5),
    (1986, 2_446_431.5),
    (2005, 2_453_371.5),
    (2026, 2_461_041.5),
    (2050, 2_469_807.5),
    (2150, 2_506_331.5),
    (5000, 3_547_272.5),
)


@example(REVIEWED_MIN_JD_UT1)
@example(_J2000)
@example(REVIEWED_MAX_JD_UT1)
@given(
    jd_ut1=st.floats(
        min_value=REVIEWED_MIN_JD_UT1,
        max_value=REVIEWED_MAX_JD_UT1,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    )
)
def test_hybrid_ut1_tt_inverse_relation(jd_ut1: float) -> None:
    observation = observe_hybrid_inverse(jd_ut1)
    target(
        observation.maximum_round_trip_residual_ulps,
        label="hybrid UT1 round-trip residual ULPs",
    )
    target(abs(jd_ut1 - _J2000), label="distance from J2000 in days")
    event(
        "round-trip-residual="
        f"{observation.maximum_round_trip_residual_ulps:g}-ulps"
    )
    assert_hybrid_inverse(
        observation,
        limit_ulps=_HYBRID_INVERSE_LIMIT_ULPS,
    )


def test_hybrid_ut1_tt_boundary_atlas() -> None:
    for _year, boundary_jd in _BOUNDARY_JDS:
        for jd_ut1 in (
            math.nextafter(boundary_jd, -math.inf),
            boundary_jd,
            math.nextafter(boundary_jd, math.inf),
        ):
            if not REVIEWED_MIN_JD_UT1 <= jd_ut1 <= REVIEWED_MAX_JD_UT1:
                continue
            assert_hybrid_inverse(
                observe_hybrid_inverse(jd_ut1),
                limit_ulps=_HYBRID_INVERSE_LIMIT_ULPS,
            )


@pytest.mark.parametrize(
    "bad_jd",
    (float("nan"), float("inf"), -float("inf"), 1.0e100, -1.0e100),
)
def test_hybrid_clock_rejects_nonfinite_and_extreme_inputs(
    bad_jd: float,
) -> None:
    with pytest.raises(ValueError):
        ut_to_tt(bad_jd)
    with pytest.raises(ValueError):
        tt_to_ut(bad_jd)


def test_hybrid_inverse_canary_detects_one_second_mutation() -> None:
    mutant_id = "P10-TIMESCALE-RECOVERED-UT1-PLUS-ONE-SECOND"
    observation = observe_hybrid_inverse(
        _J2000,
        recovered_ut1_bias_seconds=1.0,
    )
    with pytest.raises(MetamorphicViolation) as raised:
        assert_hybrid_inverse(
            observation,
            limit_ulps=_HYBRID_INVERSE_LIMIT_ULPS,
            mutant_id=mutant_id,
        )
    violation = raised.value
    assert violation.relation_id == HYBRID_TIMESCALE_RELATION_ID
    assert violation.mutant_id == mutant_id
    assert violation.metric == "maximum hybrid UT1 round-trip residual"
    assert violation.observed > violation.limit
    assert violation.limit == _HYBRID_INVERSE_LIMIT_ULPS
