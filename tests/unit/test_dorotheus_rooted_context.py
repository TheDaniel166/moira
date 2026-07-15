"""Source-owned tests for the Dorotheus V.6/V.31 rooted context."""

from __future__ import annotations

from dataclasses import replace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western
from moira.chart import ChartContext
from moira.constants import Body, HouseSystem
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.planets import PlanetData


def _planet(name: str, longitude: float) -> PlanetData:
    return PlanetData(
        name=name,
        longitude=longitude % 360.0,
        latitude=0.0,
        distance=1.0,
        speed=1.0,
        retrograde=False,
    )


def _houses(system: str = HouseSystem.PORPHYRY) -> HouseCusps:
    return HouseCusps(
        system=system,
        cusps=tuple(float(degree) for degree in range(0, 360, 30)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=system,
        classification=classify_house_system(system),
        policy=HousePolicy.default(),
    )


def _chart(
    *,
    moon: float = 10.0,
    mercury: float = 95.0,
    venus: float = 125.0,
    mars: float = 250.0,
    jupiter: float = 185.0,
    saturn: float = 215.0,
    sun: float = 155.0,
    house_system: str = HouseSystem.PORPHYRY,
) -> ChartContext:
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=0.0,
        longitude=0.0,
        planets={
            Body.SUN: _planet(Body.SUN, sun),
            Body.MOON: _planet(Body.MOON, moon),
            Body.MERCURY: _planet(Body.MERCURY, mercury),
            Body.VENUS: _planet(Body.VENUS, venus),
            Body.MARS: _planet(Body.MARS, mars),
            Body.JUPITER: _planet(Body.JUPITER, jupiter),
            Body.SATURN: _planet(Body.SATURN, saturn),
        },
        nodes={},
        houses=_houses(house_system),
    )


def _evaluate(
    chart: ChartContext,
    *,
    matter: western.DorotheusMatter = western.DorotheusMatter.LAND_AND_MANAGEMENT,
    election_class: western.WesternElectionClass = western.WesternElectionClass.EPHEMERAL,
    natal_chart: ChartContext | None = None,
) -> western.DorotheusRootedContextEvaluation:
    return western.evaluate_dorotheus_rooted_context(
        chart,
        matter=matter,
        election_class=election_class,
        next_connection=None,
        natal_chart=natal_chart,
        reader_provenance="synthetic_unit_fixture",
    )


def test_rooted_context_is_public_through_engine_facade_and_rest_owner() -> None:
    names = {
        "WesternElectionClass",
        "DorotheusMatter",
        "DorotheusFortificationTestimony",
        "DorotheusFortificationTestimonyState",
        "DorotheusStrengthState",
        "DorotheusRootOutcomePattern",
        "DorotheusSignificatorCondition",
        "DorotheusSupplementaryIndicator",
        "DorotheusSupplementaryIndicatorState",
        "DorotheusPlacementWitness",
        "DorotheusRootOutcomeWitness",
        "DorotheusMatterSignificatorWitness",
        "DorotheusRadicalityWitness",
        "DorotheusRootedContextPolicy",
        "DorotheusRootedContextEvaluation",
        "DOROTHEUS_ROOTED_CONTEXT_V1",
        "evaluate_dorotheus_rooted_context",
        "dorotheus_rooted_context_at",
    }
    assert names <= set(western.__all__)
    assert names <= set(moira.__all__)
    assert names <= set(facade.__all__)
    assert hasattr(moira.Moira, "dorotheus_rooted_context_at")


@pytest.mark.parametrize(
    ("matter", "expected"),
    [
        (western.DorotheusMatter.LAND_AND_MANAGEMENT, (Body.SATURN, Body.JUPITER)),
        (western.DorotheusMatter.MERCURIAL_AFFAIRS, (Body.MERCURY,)),
        (western.DorotheusMatter.MARRIAGE_SEX_AND_PLEASURE, (Body.VENUS,)),
        (western.DorotheusMatter.WAR_AND_ARMS, (Body.MARS,)),
        (western.DorotheusMatter.RULERS_AND_PETITIONS, (Body.JUPITER,)),
        (western.DorotheusMatter.MANIFEST_AND_PROMINENT, (Body.SUN, Body.JUPITER)),
    ],
)
def test_v31_matter_registry_is_exact(
    matter: western.DorotheusMatter,
    expected: tuple[str, ...],
) -> None:
    result = _evaluate(_chart(), matter=matter)
    assert tuple(item.body for item in result.matter_significators) == expected


def test_angular_moon_and_cadent_lord_preserve_good_root_bad_outcome() -> None:
    result = _evaluate(_chart(moon=10.0, mars=250.0))
    assert result.root_outcome.moon.strength is western.DorotheusStrengthState.ANGULAR
    assert result.root_outcome.moon_sign_lord.body == Body.MARS
    assert result.root_outcome.moon_sign_lord.strength is western.DorotheusStrengthState.CADENT
    assert result.root_outcome.pattern is western.DorotheusRootOutcomePattern.GOOD_ROOT_BAD_OUTCOME


def test_cadent_moon_and_angular_lord_preserve_difficult_root_suitable_outcome() -> None:
    result = _evaluate(_chart(moon=65.0, mercury=5.0))
    assert result.root_outcome.moon_sign_lord.body == Body.MERCURY
    assert result.root_outcome.pattern is western.DorotheusRootOutcomePattern.DIFFICULT_ROOT_SUITABLE_OUTCOME


def test_succedent_moon_sign_lord_marks_delay_without_inventing_a_pattern() -> None:
    result = _evaluate(_chart(moon=10.0, mars=35.0))
    assert result.root_outcome.pattern is western.DorotheusRootOutcomePattern.UNCLASSIFIED
    assert result.root_outcome.outcome_delayed is True


def test_nonquadrant_house_system_is_explicitly_not_evaluable() -> None:
    result = _evaluate(_chart(house_system=HouseSystem.WHOLE_SIGN))
    assert result.root_outcome.pattern is western.DorotheusRootOutcomePattern.NOT_EVALUABLE
    assert result.root_outcome.outcome_delayed is None
    assert result.root_outcome.moon.house is None


def test_matter_witness_evaluates_source_defined_bad_place_set() -> None:
    result = _evaluate(_chart(), matter=western.DorotheusMatter.MERCURIAL_AFFAIRS)
    witness = result.matter_significators[0]
    assert witness.bad_place_evaluated is True
    assert witness.bad_place is False
    assert witness.condition in {
        western.DorotheusSignificatorCondition.ONE_OR_MORE_COMPUTED_IMPEDIMENTS,
        western.DorotheusSignificatorCondition.INDETERMINATE,
    }
    assert tuple(item.testimony_id for item in witness.fortification_testimonies) == (
        "under_rays",
        "made_unfortunate",
        "not_looking_at_ascendant",
        "bad_place",
    )
    assert witness.fortification_testimonies[1].state is (
        western.DorotheusFortificationTestimonyState.NOT_EVALUABLE
    )


def test_v6_29_indicators_remain_distinct_and_do_not_replace_primary_outcome_lord() -> None:
    result = _evaluate(_chart())
    ninth, fortune, connection = result.supplementary_indicators

    assert result.root_outcome.moon_sign_lord.body == Body.MARS
    assert ninth.role == "editorial_inception_supplement"
    assert ninth.state is western.DorotheusSupplementaryIndicatorState.NOT_EVALUABLE
    assert fortune.role == "inception_supplement"
    assert fortune.state is western.DorotheusSupplementaryIndicatorState.EVALUATED
    assert fortune.longitude is not None
    assert fortune.ruler in {Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS, Body.JUPITER, Body.SATURN}
    assert fortune.placement is not None
    assert connection.role == "outcome_supplement"
    assert connection.state is western.DorotheusSupplementaryIndicatorState.EVALUATED
    assert connection.body is None


@pytest.mark.parametrize("mercury", (65.0, 155.0, 215.0, 335.0))
def test_whole_sign_places_three_six_eight_and_twelve_are_bad(
    mercury: float,
) -> None:
    result = _evaluate(
        _chart(mercury=mercury),
        matter=western.DorotheusMatter.MERCURIAL_AFFAIRS,
    )
    witness = result.matter_significators[0]
    assert witness.bad_place is True
    assert (
        witness.condition
        is western.DorotheusSignificatorCondition.ONE_OR_MORE_COMPUTED_IMPEDIMENTS
    )


def test_ephemeral_rejects_natal_and_radical_requires_it() -> None:
    chart = _chart()
    with pytest.raises(ValueError, match="ephemeral"):
        _evaluate(chart, natal_chart=chart)
    with pytest.raises(ValueError, match="radical"):
        _evaluate(chart, election_class=western.WesternElectionClass.RADICAL)


def test_radical_context_preserves_natal_evidence_without_success_gate() -> None:
    result = _evaluate(
        _chart(),
        election_class=western.WesternElectionClass.RADICAL,
        natal_chart=_chart(moon=70.0),
    )
    assert result.radicality.natal_required is True
    assert result.radicality.natal_provided is True
    assert result.radicality.natal_ascendant_sign == "Aries"
    assert result.radicality.assessment_semantics == "evidence_only_not_success_gate"
    assert result.complete_electional_judgement is False


def test_policy_is_closed() -> None:
    assert western.DOROTHEUS_ROOTED_CONTEXT_V1.profile_version == "1.2.0"
    with pytest.raises(ValueError, match="under_rays_degrees"):
        replace(western.DOROTHEUS_ROOTED_CONTEXT_V1, under_rays_degrees=12.0)
