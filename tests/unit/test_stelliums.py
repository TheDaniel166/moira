"""Synthetic geometry contracts for moira.stellium.v1; no ephemeris oracle.

The expected planet counts and circular arcs below are the admitted product
policy, not a claim about a universal historical stellium definition.
"""

from dataclasses import asdict, replace
from itertools import permutations
import math

import pytest

from moira.constants import Body
from moira.houses import HouseCusps, classify_house_system
from moira.stelliums import (
    STELLIUM_CORE,
    StelliumAnalysisPolicy,
    StelliumContext,
    StelliumHouseContext,
    StelliumSelection,
    analyze_stelliums,
)


CORE = ("Sun", "Moon", "Mercury", "Venus")


def analyze(lons=(0.0, 2.0, 4.0, 6.0), *, preset="strict", extra=None, **kwargs):
    positions = dict(zip(CORE, lons))
    positions.update(extra or {})
    return analyze_stelliums(
        positions,
        policy=StelliumAnalysisPolicy(preset=preset),
        selection=StelliumSelection(
            core=CORE[: len(lons)], associated=tuple(extra or {})
        ),
        **kwargs,
    )


def whole_sign():
    return StelliumHouseContext(
        houses=HouseCusps(
            system="W",
            effective_system="W",
            classification=classify_house_system("W"),
            cusps=tuple(i * 30.0 for i in range(12)),
            asc=0,
            mc=270,
            armc=270,
        ),
        longitude_frame="tropical",
    )


def matches(result, criterion):
    return [
        (g, m) for g in result.groups for m in g.matches if m.criterion == criterion
    ]


def test_core_roster_is_frozen_ten_not_all_points():
    assert (
        STELLIUM_CORE
        == tuple(Body.ALL_PLANETS)
        == (
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Jupiter",
            "Saturn",
            "Uranus",
            "Neptune",
            "Pluto",
        )
    )


def test_three_planets_plus_node_is_broad_not_strict():
    assert not analyze((0, 2, 4), extra={"North Node": 3}).groups
    result = analyze((0, 2, 4), preset="broad", extra={"North Node": 3})
    group, match = matches(result, "tight")[0]
    assert group.core_count == 3
    assert group.core_members == CORE[:3]
    assert tuple(a.body for a in match.associations) == ("North Node",)


def test_two_planets_and_any_associated_factors_cannot_qualify():
    assert not analyze(
        (1, 2), preset="broad", extra={"Chiron": 3, "ASC": 4, "Fortune": 5}
    ).groups


def test_associations_never_move_geometry_membership_or_ids():
    first = analyze()
    second = analyze(extra={"Chiron": 3, "North Node": 50, "Fortune": 0})
    assert first.groups[0].id == second.groups[0].id
    assert first.input_fingerprint != second.input_fingerprint
    for (g1, m1), (g2, m2) in zip(matches(first, "tight"), matches(second, "tight")):
        assert g1.core_members == g2.core_members
        assert m1.arc == m2.arc
        assert m1.id == m2.id
        assert {a.body for a in m2.associations} == {"Chiron", "Fortune"}


def test_identical_members_merge_sign_house_and_tight():
    result = analyze(houses=whole_sign())
    assert len(result.groups) == 1
    assert {m.criterion for m in result.groups[0].matches} == {"sign", "house", "tight"}
    assert result.status == "complete"


def test_house_and_sign_independent_and_exact_cusp_belongs_next_house():
    houses = replace(
        whole_sign().houses,
        system="E",
        effective_system="E",
        asc=15,
        classification=classify_house_system("E"),
        cusps=tuple((15 + i * 30) % 360 for i in range(12)),
    )
    context = StelliumHouseContext(houses, "tropical")
    assert not matches(analyze((1, 10, 15, 29), houses=context), "house")
    result = analyze((15, 25, 30, 44), houses=context)
    assert not matches(result, "sign")
    assert matches(result, "house")[0][1].house == 1


def test_tight_wraparound_and_no_conjunction_chaining():
    arc = matches(analyze((358, 0, 2, 4)), "tight")[0][1].arc
    assert (arc.start, arc.end, arc.span, arc.wraps) == (358, 4, 6, True)
    assert not matches(analyze((0, 4, 8, 12)), "tight")
    groups = matches(analyze((0, 4, 8, 12), preset="broad"), "tight")
    assert {g.core_members for g, _ in groups} == {CORE[:3], CORE[1:]}
    assert len(matches(analyze((0, 4, 8, 12), preset="broad"), "sign")) == 1


def test_total_span_boundary_is_inclusive_without_display_rounding():
    assert matches(analyze((0, 2, 4, 8)), "tight")
    assert not matches(analyze((0, 2, 4, math.nextafter(8.0, math.inf))), "tight")


def test_distinct_planets_at_identical_longitudes_count_once_each():
    arc = matches(analyze((5, 5, 5, 5)), "tight")[0][1].arc
    assert (arc.start, arc.end, arc.span) == (5, 5, 0)


def test_missing_houses_is_not_a_negative_house_result():
    result = analyze(house_unavailable_reason="Unknown birth time")
    evaluation = next(e for e in result.evaluations if e.criterion == "house")
    assert evaluation.status == "not_evaluable"
    assert evaluation.reason == "Unknown birth time"
    assert result.status == "partial"
    assert matches(result, "sign")


def test_unrequested_houses_does_not_make_analysis_partial():
    result = analyze_stelliums(
        dict(zip(CORE, (0, 2, 4, 6))),
        selection=StelliumSelection(CORE),
        policy=StelliumAnalysisPolicy(criteria=("sign", "tight")),
    )
    assert result.status == "complete"


def test_incomplete_requested_selection_remains_partial_even_when_group_qualifies():
    result = analyze_stelliums(
        dict(zip(CORE, (0, 2, 4, 6))),
        selection=StelliumSelection((*CORE, "Mars")),
        houses=whole_sign(),
    )
    assert result.status == "partial"
    assert result.coverage.missing_core == ("Mars",)
    assert result.groups


def test_sign_boundary_normalization_and_offset_is_receipt_not_second_transform():
    result = analyze(
        (30, 31, 32, 33),
        context=StelliumContext(
            zodiac="sidereal", zodiac_offset_degrees=24, ayanamsa="LAHIRI"
        ),
    )
    assert matches(result, "sign")[0][1].sign_index == 1
    assert matches(analyze((360, 361, 362, 363)), "sign")[0][1].sign_index == 0


def test_house_frame_mismatch_rejected_not_silently_placed():
    with pytest.raises(ValueError, match="frame"):
        analyze(
            houses=whole_sign(),
            context=StelliumContext(
                zodiac="sidereal", ayanamsa="LAHIRI", zodiac_offset_degrees=24
            ),
        )


def test_invalid_house_geometry_rejected():
    with pytest.raises(ValueError):
        StelliumHouseContext(
            replace(whole_sign().houses, cusps=(0.0,) * 12), "tropical"
        )


def test_permutation_and_association_order_do_not_change_output():
    positions = {"Sun": 358, "Moon": 0, "Mercury": 2, "Venus": 4, "Chiron": 3}
    expected = analyze_stelliums(
        positions, selection=StelliumSelection(CORE, ("Chiron",))
    )
    for keys in list(permutations(positions))[:30]:
        actual = analyze_stelliums(
            {k: positions[k] for k in keys},
            selection=StelliumSelection(tuple(reversed(CORE)), ("Chiron",)),
        )
        assert asdict(actual) == asdict(expected)


@pytest.mark.parametrize("value", [True, "8", -1, 180, math.inf, math.nan])
def test_invalid_span_rejected(value):
    with pytest.raises(ValueError):
        StelliumAnalysisPolicy(max_span_degrees=value)


@pytest.mark.parametrize(
    "positions", [{"Sun": True}, {"Sun": math.nan}, {"": 1}, {"Sun": 1, "sun": 2}]
)
def test_invalid_positions_rejected(positions):
    with pytest.raises(ValueError):
        analyze_stelliums(positions)


def test_selection_cannot_promote_chiron_or_unknown_name_to_core():
    for body in ("Chiron", "North Node", "Imaginary Planet"):
        with pytest.raises(ValueError, match="core"):
            StelliumSelection((body,))
    with pytest.raises(ValueError, match="duplicate"):
        StelliumSelection(("Sun", "sun"))


def test_legacy_detector_keeps_its_existing_contract():
    from moira.patterns import find_stelliums

    assert find_stelliums({"A": 0, "B": 2, "C": 4})


def test_associations_are_per_match_and_closed_arc_does_not_expand():
    houses = replace(
        whole_sign().houses,
        system="E",
        effective_system="E",
        asc=15,
        classification=classify_house_system("E"),
        cusps=tuple((15 + i * 30) % 360 for i in range(12)),
    )
    result = analyze(
        (17, 19, 21, 23),
        houses=StelliumHouseContext(houses),
        extra={"Fortune": 14, "Chiron": 40, "North Node": 17, "South Node": 23},
    )
    evidence = {
        m.criterion: {a.body for a in m.associations} for m in result.groups[0].matches
    }
    assert evidence == {
        "sign": {"Fortune", "North Node", "South Node"},
        "house": {"Chiron", "North Node", "South Node"},
        "tight": {"North Node", "South Node"},
    }


def test_core_selection_reanalyzes_five_to_four_and_does_not_drop_the_group():
    positions = dict(zip((*CORE, "Mars"), (1, 2, 3, 4, 5)))
    first = analyze_stelliums(positions, selection=StelliumSelection((*CORE, "Mars")))
    second = analyze_stelliums(positions, selection=StelliumSelection(CORE))
    assert first.groups[0].core_count == 5
    assert second.groups[0].core_count == 4
    assert second.coverage.excluded == ("Mars",)


def test_only_house_requested_without_house_context_is_not_evaluable():
    result = analyze_stelliums(
        {},
        selection=StelliumSelection(()),
        policy=StelliumAnalysisPolicy(criteria=("house",)),
    )
    assert result.status == "not_evaluable"
    assert not result.groups


def test_tight_membership_is_rotation_invariant_away_from_numeric_boundaries():
    original = {"Sun": 358.0, "Moon": 0.0, "Mercury": 2.0, "Venus": 4.0, "Mars": 200.0}
    policy = StelliumAnalysisPolicy(criteria=("tight",))
    selection = StelliumSelection((*CORE, "Mars"))
    expected = analyze_stelliums(original, policy=policy, selection=selection)
    for offset in (0, 1, 15.5, 24.125, 179.0, 300.0):
        result = analyze_stelliums(
            {n: (v - offset) % 360 for n, v in original.items()},
            policy=policy,
            selection=selection,
            context=StelliumContext(zodiac="draconic", zodiac_offset_degrees=offset),
        )
        assert tuple(g.core_members for g in result.groups) == tuple(
            g.core_members for g in expected.groups
        )
        assert result.groups[0].matches[0].arc.span == 6


def test_canonical_house_figure_round_trip_uses_actual_membership(
    natal_chart, natal_houses
):
    # DE441 fixture: structural integration only, not an external accuracy oracle.
    from moira.houses import assign_house

    positions = natal_chart.longitudes()
    result = analyze_stelliums(positions, houses=StelliumHouseContext(natal_houses))
    for group, match in matches(result, "house"):
        assert all(
            assign_house(positions[n], natal_houses).house == match.house
            for n in group.core_members
        )


def test_nonfinite_python_house_receipt_and_oversized_integer_are_rejected():
    with pytest.raises(ValueError, match="finite"):
        analyze_stelliums({"Sun": 10**1000})
    with pytest.raises(ValueError, match="finite"):
        StelliumHouseContext(replace(whole_sign().houses, armc=math.nan))
