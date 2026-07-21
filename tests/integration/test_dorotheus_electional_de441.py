"""DE441 substrate-integration evidence for Dorotheus V.6.

These tests establish fixed-kernel regression and engine-boundary behavior.
They do not empirically validate Dorotheus's astrological doctrine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body, HouseSystem
from moira.eclipse import EclipseCalculator
from moira.planets import planet_at
from moira.spk_reader import SpkReader
from moira.western_electional import (
    DorotheusConstructionClauseState,
    DorotheusMatter,
    DorotheusMoonConditionStatus,
    DorotheusRuleState,
    dorotheus_rooted_context_at,
    dorotheus_construction_at,
    dorotheus_moon_condition_at,
)


@pytest.mark.requires_ephemeris
def test_j2000_construction_profile_composes_every_de441_backed_layer() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        result = dorotheus_construction_at(
            2451545.0,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
            reader=reader,
        )

    assert Path(result.reader_provenance).name == "de441.bsp"
    assert result.profile_id == "dorotheus_construction_v1"
    assert result.profile_version == "1.1.0"
    assert result.moon_condition.profile_id == "dorotheus_moon_condition_v1"
    assert result.rooted_context.profile_id == "dorotheus_rooted_context_v1"
    assert result.rooted_context.next_connection is not None
    assert result.sign_nature.ascensional_arc_degrees is not None
    calculation = result.construction_clauses[0]
    assert calculation.state is DorotheusConstructionClauseState.SATISFIED
    assert calculation.measurements[2].name == "lunar_equation"
    assert calculation.measurements[2].value == pytest.approx(5.00124, abs=2e-5)
    assert calculation.measurements[3].value == "added"
    assert result.construction_clauses[2].measurements[1].value != 0.0
    assert result.source_complete is True
    assert result.complete_matter_profile is True
    assert result.numerically_complete is False


@pytest.mark.requires_ephemeris
def test_j2000_rooted_context_next_connection_satisfies_de441_geometry() -> None:
    """Invariant evidence for the sign-bounded connection timing witness."""

    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        result = dorotheus_rooted_context_at(
            2451545.0,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
            matter=DorotheusMatter.LAND_AND_MANAGEMENT,
            reader=reader,
        )
        connection = result.next_connection
        assert connection is not None
        moon = planet_at(Body.MOON, connection.jd_exact, reader=reader)
        other = planet_at(connection.body, connection.jd_exact, reader=reader)
        separation = (moon.longitude - other.longitude) % 360.0
        angular_error = abs((separation - connection.angle + 180.0) % 360.0 - 180.0)
        before_exit = planet_at(Body.MOON, connection.jd_sign_exit - 2e-5, reader=reader)
        after_exit = planet_at(Body.MOON, connection.jd_sign_exit + 2e-5, reader=reader)

    assert Path(result.reader_provenance).name == "de441.bsp"
    assert connection.jd_query < connection.jd_exact < connection.jd_sign_exit
    assert connection.body == Body.MARS
    assert connection.aspect_name == "Square"
    assert angular_error < 2e-4
    assert before_exit.sign == connection.moon_sign
    assert after_exit.sign != connection.moon_sign
    ninth, fortune, outcome = result.supplementary_indicators
    assert ninth.state.value == "not_evaluable"
    assert fortune.longitude == pytest.approx(326.969422305233, abs=1e-10)
    assert fortune.sign == "Aquarius"
    assert fortune.ruler == Body.SATURN
    assert outcome.body == connection.body
    assert outcome.placement == result.next_connection_placement
    assert result.complete_electional_judgement is False


@pytest.mark.requires_ephemeris
def test_j2000_london_dorotheus_profile_preserves_kernel_and_rule_truth() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    assert kernel.name == "de441.bsp"
    jd_ut = 2451545.0
    with SpkReader(kernel) as reader:
        result = dorotheus_moon_condition_at(
            jd_ut,
            51.5074,
            -0.1278,
            house_system=HouseSystem.REGIOMONTANUS,
            reader=reader,
        )
        dt = 1e-4
        moon_before = planet_at(Body.MOON, jd_ut - dt, reader=reader, apparent=False)
        moon_after = planet_at(Body.MOON, jd_ut + dt, reader=reader, apparent=False)

    assert Path(result.reader_provenance).name == "de441.bsp"
    assert result.status is DorotheusMoonConditionStatus.TRIGGERED
    assert result.requested_house_system == HouseSystem.REGIOMONTANUS
    assert result.effective_house_system == HouseSystem.REGIOMONTANUS
    assert result.house_fallback is False
    assert result.triggered_rule_ids == (
        "moon_in_malefic_twelfth_part",
        "moon_with_or_looking_at_infortune",
        "moon_in_burned_path",
    )
    assert result.not_evaluable_rule_ids == (
        "moon_on_ecliptic_descending_south",
        "moon_disengaging_from_sun",
    )
    measured_speed = result.rules[7].clauses[0].measurements[0].value
    longitude_delta = (
        moon_after.longitude - moon_before.longitude + 180.0
    ) % 360.0 - 180.0
    finite_difference_rate = longitude_delta / (2.0 * dt)
    assert measured_speed == pytest.approx(finite_difference_rate, abs=1e-4)


@pytest.mark.requires_ephemeris
def test_de441_lunar_eclipse_maximum_triggers_only_the_present_eclipse_gate() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        event = EclipseCalculator(reader=reader).next_lunar_eclipse(
            2451545.0,
            kind="any",
        )
        result = dorotheus_moon_condition_at(
            event.jd_ut,
            0.0,
            0.0,
            house_system=HouseSystem.REGIOMONTANUS,
            reader=reader,
        )

    eclipse_rule = result.rules[0]
    assert eclipse_rule.rule_id == "moon_eclipsed"
    assert eclipse_rule.state is DorotheusRuleState.TRIGGERED
    assert eclipse_rule.clauses[0].measurements[0].value is True
    assert "natal Moon" in eclipse_rule.modifiers[0]
