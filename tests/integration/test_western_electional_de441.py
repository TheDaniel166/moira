"""DE441 regression integration for the admitted Ramesey Moon profile.

This is fixed-kernel regression evidence, not historical or empirical
validation of electional doctrine.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body, HouseSystem
from moira.planets import planet_at
from moira.spk_reader import SpkReader
from moira.western_electional import (
    RameseyMoonConditionStatus,
    RameseyRuleState,
    ramesey_moon_condition_at,
)


_TRADITIONAL_ASPECT_BODIES = (
    Body.SUN,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
)
_DIRECTIONAL_PTOLEMAIC_TARGETS = (0.0, 60.0, 90.0, 120.0, 180.0, 240.0, 270.0, 300.0)
_INDEPENDENT_SCAN_STEP = 1.0 / 96.0  # 15 minutes; independent of the engine's 6-hour step.


def _longitude(body: str, jd_ut: float, reader: SpkReader) -> float:
    position = planet_at(body, jd_ut, reader=reader, apparent=True)
    return position.longitude % 360.0


def _independent_next_moon_ingress(jd_ut: float, reader: SpkReader) -> float:
    sign_index = int(_longitude(Body.MOON, jd_ut, reader) // 30.0)
    lo = jd_ut
    hi = jd_ut + _INDEPENDENT_SCAN_STEP
    limit = jd_ut + 3.0
    while hi <= limit and int(_longitude(Body.MOON, hi, reader) // 30.0) == sign_index:
        lo = hi
        hi += _INDEPENDENT_SCAN_STEP
    if hi > limit:
        raise AssertionError("independent Moon ingress search exceeded three days")
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if int(_longitude(Body.MOON, mid, reader) // 30.0) == sign_index:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _aspect_signal(jd_ut: float, body: str, target: float, reader: SpkReader) -> float:
    separation = (_longitude(Body.MOON, jd_ut, reader) - _longitude(body, jd_ut, reader)) % 360.0
    return (separation - target + 180.0) % 360.0 - 180.0


def _bisect_independent_perfection(
    body: str,
    target: float,
    lo: float,
    hi: float,
    reader: SpkReader,
) -> float:
    signal_lo = _aspect_signal(lo, body, target, reader)
    for _ in range(50):
        mid = (lo + hi) / 2.0
        signal_mid = _aspect_signal(mid, body, target, reader)
        if signal_lo * signal_mid <= 0.0:
            hi = mid
        else:
            lo = mid
            signal_lo = signal_mid
    return (lo + hi) / 2.0


def _independent_forward_perfections(
    jd_ut: float,
    jd_ingress: float,
    reader: SpkReader,
) -> list[tuple[float, str, float]]:
    perfections: list[tuple[float, str, float]] = []
    for body in _TRADITIONAL_ASPECT_BODIES:
        lo = jd_ut
        raw_previous = (
            _longitude(Body.MOON, lo, reader) - _longitude(body, lo, reader)
        ) % 360.0
        unwrapped_previous = raw_previous
        while lo < jd_ingress:
            hi = min(lo + _INDEPENDENT_SCAN_STEP, jd_ingress)
            raw_current = (
                _longitude(Body.MOON, hi, reader) - _longitude(body, hi, reader)
            ) % 360.0
            phase_delta = (raw_current - raw_previous + 180.0) % 360.0 - 180.0
            unwrapped_current = unwrapped_previous + phase_delta
            for target in _DIRECTIONAL_PTOLEMAIC_TARGETS:
                if unwrapped_current > unwrapped_previous:
                    multiple = math.floor((unwrapped_previous - target) / 360.0) + 1
                    crossed = target + 360.0 * multiple
                    intersects = crossed <= unwrapped_current
                else:
                    multiple = math.ceil((unwrapped_previous - target) / 360.0) - 1
                    crossed = target + 360.0 * multiple
                    intersects = crossed >= unwrapped_current
                if intersects:
                    exact = _bisect_independent_perfection(body, target, lo, hi, reader)
                    if jd_ut < exact < jd_ingress:
                        perfections.append((exact, body, target))
            lo = hi
            raw_previous = raw_current
            unwrapped_previous = unwrapped_current
    perfections.sort()
    return perfections


@pytest.mark.requires_ephemeris
def test_j2000_london_de441_rule_witness_regression() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    assert kernel.name == "de441.bsp"
    with SpkReader(kernel) as reader:
        result = ramesey_moon_condition_at(
            2451545.0,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
            reader=reader,
        )
        dt = 1e-4
        moon_before = planet_at(Body.MOON, 2451545.0 - dt, reader=reader, apparent=False)
        moon_after = planet_at(Body.MOON, 2451545.0 + dt, reader=reader, apparent=False)

    assert Path(result.reader_provenance).name == "de441.bsp"
    assert result.status is RameseyMoonConditionStatus.TRIGGERED
    assert result.requested_house_system == HouseSystem.REGIOMONTANUS
    assert result.effective_house_system == HouseSystem.REGIOMONTANUS
    assert result.house_fallback is False
    assert result.triggered_rule_ids == (
        "moon_joined_or_hard_aspect_malefic",
        "moon_cadent_or_via_combusta",
        "moon_slow_below_ramesey_mean",
    )
    assert result.not_evaluable_rule_ids == ()
    assert result.complete_electional_judgement is False
    assert result.advice_language == "not_provided"
    assert result.recommendation_language == "not_provided"
    remedy = result.remedies[0]
    assert remedy.fulfillment.value == "not_fulfilled"
    assert remedy.clauses[0].state.value == "not_fulfilled"
    assert remedy.clauses[1].state.value == "fulfilled"
    assert remedy.clauses[-1].measurements[0].value == Body.MERCURY
    speed_measurement = result.rules[8].clauses[0].measurements[0]
    longitude_delta = (moon_after.longitude - moon_before.longitude + 180.0) % 360.0 - 180.0
    finite_difference_rate = longitude_delta / (2.0 * dt)
    assert speed_measurement.value == pytest.approx(finite_difference_rate, abs=1e-4)


@pytest.mark.requires_ephemeris
def test_ramesey_voc_matches_independent_forward_geometry_around_last_aspect_and_ingress() -> None:
    """Covenant: future perfection, not the VOC implementation, determines state.

    Corpus: four DE441 probes around the final Mars square and following
    Scorpio-to-Sagittarius ingress after J2000. Positions are apparent,
    geocentric, ecliptic-of-date. The independent scan uses 15-minute steps,
    then 50 bisections; root/ingress comparisons allow 2e-5 day (~1.7 s).
    """

    kernel = find_planetary_kernel()
    assert kernel is not None
    assert kernel.name == "de441.bsp"
    probes = (
        (2451546.300, False),
        (2451546.320, True),
        (2451546.396, True),
        (2451546.405, False),
    )

    with SpkReader(kernel) as reader:
        first_ingress = _independent_next_moon_ingress(probes[0][0], reader)
        first_perfections = _independent_forward_perfections(
            probes[0][0], first_ingress, reader
        )
        assert first_perfections
        final_exact, final_body, final_target = first_perfections[-1]
        assert final_body == Body.MARS
        assert final_target == 270.0
        assert final_exact == pytest.approx(2451546.31116, abs=2e-5)
        assert first_ingress == pytest.approx(2451546.39704, abs=2e-5)

        observed_states: list[bool] = []
        for jd_ut, expected_void in probes:
            ingress = _independent_next_moon_ingress(jd_ut, reader)
            future_perfections = _independent_forward_perfections(jd_ut, ingress, reader)
            independent_void = not future_perfections
            result = ramesey_moon_condition_at(
                jd_ut,
                51.5074,
                -0.1278,
                house_system=HouseSystem.REGIOMONTANUS,
                reader=reader,
            )
            rule_state = result.rules[9].state

            assert independent_void is expected_void
            assert (rule_state is RameseyRuleState.TRIGGERED) is independent_void
            observed_states.append(independent_void)

    assert set(observed_states) == {False, True}
