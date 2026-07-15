"""DE441 integration evidence for Sahl's bounded Moon profile.

This is fixed-kernel regression and substrate-integration evidence. It does
not empirically validate Sahl's astrological doctrine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body, HouseSystem
from moira.planets import planet_at
from moira.spk_reader import SpkReader
from moira.western_electional import (
    SahlBurntPathVariant,
    SahlMoonConditionStatus,
    SahlRuleState,
    sahl_moon_condition_at,
)


@pytest.mark.requires_ephemeris
def test_j2000_london_sahl_profile_preserves_kernel_and_variant_truth() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    assert kernel.name == "de441.bsp"
    jd_ut = 2451545.0
    with SpkReader(kernel) as reader:
        result = sahl_moon_condition_at(
            jd_ut,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
            burnt_path_variant=SahlBurntPathVariant.FALL_DEGREES,
            reader=reader,
        )
        dt = 1e-4
        moon_before = planet_at(Body.MOON, jd_ut - dt, reader=reader, apparent=False)
        moon_after = planet_at(Body.MOON, jd_ut + dt, reader=reader, apparent=False)

    assert Path(result.reader_provenance).name == "de441.bsp"
    assert result.status is SahlMoonConditionStatus.TRIGGERED
    assert result.requested_house_system == HouseSystem.REGIOMONTANUS
    assert result.effective_house_system == HouseSystem.REGIOMONTANUS
    assert result.house_fallback is False
    assert result.triggered_rule_ids == ("moon_joined_or_hard_ray_malefic",)
    assert result.not_evaluable_rule_ids == ()
    assert result.rules[6].state is SahlRuleState.CLEAR
    assert result.rules[9].state is SahlRuleState.CLEAR
    assert result.burnt_path_variant is SahlBurntPathVariant.FALL_DEGREES

    measured_speed = result.rules[8].clauses[0].measurements[0].value
    longitude_delta = (moon_after.longitude - moon_before.longitude + 180.0) % 360.0 - 180.0
    finite_difference_rate = longitude_delta / (2.0 * dt)
    assert measured_speed == pytest.approx(finite_difference_rate, abs=1e-4)


@pytest.mark.requires_ephemeris
def test_default_sahl_burnt_path_keeps_only_that_rule_indeterminate() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        result = sahl_moon_condition_at(
            2451545.0,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
            reader=reader,
        )

    assert result.burnt_path_variant is SahlBurntPathVariant.UNRESOLVED_SOURCE_WORDING
    assert result.not_evaluable_rule_ids == ("moon_cadent_or_burnt_path",)
    assert result.status is SahlMoonConditionStatus.TRIGGERED
