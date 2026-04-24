from __future__ import annotations

from types import MappingProxyType, SimpleNamespace

import pytest

from moira.aspects import (
    AspectPolicy,
    aspect_harmonic_profile,
    aspect_motion_state,
    build_aspect_graph,
    find_aspects,
)
from moira.chart import ChartContext
from moira.constants import sign_of
from moira.dasha import VIMSHOTTARI_SEQUENCE, current_dasha, dasha_balance, vimshottari
from moira.dignities import calculate_dignities
from moira.houses import HouseCusps, HousePolicy, assign_house, classify_house_system
from moira.lots import (
    LotsComputationPolicy,
    LotsReferenceFailureMode,
    calculate_lot_condition_network_profile,
    calculate_lots,
)
from moira.manazil import MANSION_SPAN, mansion_of
from moira.midpoints import _midpoint, to_dial_90
from moira.profections import annual_profection, monthly_profection
from moira.sidereal import Ayanamsa, NAKSHATRA_SPAN, nakshatra_of, sidereal_to_tropical
from moira.antiscia import antiscion, contra_antiscion, find_antiscia
from moira.timelords import (
    FIRDARIA_DIURNAL,
    current_firdaria,
    firdaria,
    validate_firdaria_output,
    validate_releasing_output,
    zodiacal_releasing,
)


J2000 = 2451545.0
EPS = 1e-9


def _equal_house_dict(start: float = 0.0) -> dict[int, float]:
    return {i + 1: (start + i * 30.0) % 360.0 for i in range(12)}


def _equal_house_rows(start: float = 0.0) -> list[dict[str, float | int]]:
    return [{"number": number, "degree": degree} for number, degree in _equal_house_dict(start).items()]


def _house_cusps(start: float = 0.0) -> HouseCusps:
    cusps = list(_equal_house_dict(start).values())
    system = "E"
    return HouseCusps(
        system=system,
        cusps=cusps,
        asc=cusps[0],
        mc=cusps[9],
        armc=0.0,
        vertex=None,
        anti_vertex=None,
        effective_system=system,
        fallback=False,
        fallback_reason=None,
        classification=classify_house_system(system),
        policy=HousePolicy.default(),
    )


def _lot_by_name(parts, name: str):
    for part in parts:
        if part.name == name:
            return part
    raise AssertionError(f"missing lot: {name}")


def test_zodiac_house_aspect_and_nakshatra_boundaries_are_exactly_assigned() -> None:
    assert sign_of(29.999999999)[0] == "Aries"
    assert sign_of(30.0)[0] == "Taurus"
    assert sign_of(359.999999999)[0] == "Pisces"
    assert sign_of(360.0)[0] == "Aries"

    cusps = _house_cusps(10.0)
    assert assign_house(39.999999999, cusps).house == 1
    cusp_hit = assign_house(40.0, cusps)
    assert cusp_hit.house == 2
    assert cusp_hit.exact_on_cusp is True

    within = find_aspects({"Sun": 0.0, "Moon": 65.0}, include_minor=False, orbs={60.0: 5.0})
    outside = find_aspects({"Sun": 0.0, "Moon": 65.000001}, include_minor=False, orbs={60.0: 5.0})
    assert len(within) == 1
    assert within[0].aspect == "Sextile"
    assert within[0].orb == pytest.approx(5.0, abs=EPS)
    assert outside == []

    before_boundary = nakshatra_of(
        sidereal_to_tropical(NAKSHATRA_SPAN - EPS, J2000, Ayanamsa.LAHIRI),
        J2000,
        Ayanamsa.LAHIRI,
    )
    at_boundary = nakshatra_of(
        sidereal_to_tropical(NAKSHATRA_SPAN, J2000, Ayanamsa.LAHIRI),
        J2000,
        Ayanamsa.LAHIRI,
    )
    assert before_boundary.nakshatra_index == 0
    assert before_boundary.pada == 4
    assert at_boundary.nakshatra_index == 1
    assert at_boundary.pada == 1
    assert at_boundary.degrees_in == pytest.approx(0.0, abs=1e-10)


def test_mirror_midpoint_and_mansion_seams_are_reversible_and_half_open() -> None:
    for longitude in (0.0, 29.999999999, 90.0, 180.0, 270.0, 359.999999999):
        assert antiscion(antiscion(longitude)) == pytest.approx(longitude % 360.0, abs=EPS)
        assert contra_antiscion(contra_antiscion(longitude)) == pytest.approx(longitude % 360.0, abs=EPS)

    contacts = find_antiscia({"Sun": 359.999999999, "Moon": 180.000000001}, orb=1e-6)
    assert [(c.aspect, c.orb < 1e-6) for c in contacts] == [("Antiscion", True)]

    assert _midpoint(350.0, 10.0) == pytest.approx(0.0, abs=EPS)
    assert _midpoint(10.0, 350.0) == pytest.approx(0.0, abs=EPS)
    assert to_dial_90(22.5) == pytest.approx(0.0, abs=EPS)
    assert to_dial_90(89.999999999) == pytest.approx(89.999999996, abs=EPS)
    assert to_dial_90(90.0) == pytest.approx(0.0, abs=EPS)

    before = mansion_of(MANSION_SPAN - EPS)
    at = mansion_of(MANSION_SPAN)
    wrap = mansion_of(360.0)
    assert before.mansion.index == 1
    assert at.mansion.index == 2
    assert at.degrees_in == pytest.approx(0.0, abs=1e-10)
    assert wrap.mansion.index == 1
    assert wrap.degrees_in == pytest.approx(0.0, abs=EPS)


def test_lots_day_night_reversal_preserves_visible_computation_truth() -> None:
    positions = {
        "Sun": 20.0,
        "Moon": 80.0,
        "Mercury": 100.0,
        "Venus": 130.0,
        "Mars": 180.0,
        "Jupiter": 240.0,
        "Saturn": 300.0,
    }
    houses = _equal_house_dict(100.0)

    day_parts = calculate_lots(positions, houses, is_day_chart=True)
    night_parts = calculate_lots(positions, houses, is_day_chart=False)

    day_fortune = _lot_by_name(day_parts, "Fortune")
    day_spirit = _lot_by_name(day_parts, "Spirit")
    night_fortune = _lot_by_name(night_parts, "Fortune")
    night_spirit = _lot_by_name(night_parts, "Spirit")

    assert day_fortune.longitude == pytest.approx((100.0 + 80.0 - 20.0) % 360.0)
    assert day_spirit.longitude == pytest.approx((100.0 + 20.0 - 80.0) % 360.0)
    assert night_fortune.longitude == pytest.approx(day_spirit.longitude)
    assert night_spirit.longitude == pytest.approx(day_fortune.longitude)

    assert day_fortune.computation_truth is not None
    assert day_fortune.computation_truth.reversed_for_chart is False
    assert day_fortune.computation_truth.effective_add_key == "Moon"
    assert day_fortune.computation_truth.effective_sub_key == "Sun"

    assert night_fortune.computation_truth is not None
    assert night_fortune.computation_truth.reversed_for_chart is True
    assert night_fortune.computation_truth.effective_add_key == "Sun"
    assert night_fortune.computation_truth.effective_sub_key == "Moon"


def test_lot_dependency_network_is_deterministic_under_input_permutation() -> None:
    positions = {
        "Sun": 20.0,
        "Moon": 80.0,
        "Mercury": 100.0,
        "Venus": 130.0,
        "Mars": 180.0,
        "Jupiter": 240.0,
        "Saturn": 300.0,
    }
    reversed_positions = dict(reversed(list(positions.items())))
    houses = _equal_house_dict(100.0)

    first = calculate_lot_condition_network_profile(positions, houses, is_day_chart=True)
    second = calculate_lot_condition_network_profile(reversed_positions, houses, is_day_chart=True)

    first_nodes = [(node.part_name, node.incoming_count, node.outgoing_count, node.reciprocal_count) for node in first.nodes]
    second_nodes = [(node.part_name, node.incoming_count, node.outgoing_count, node.reciprocal_count) for node in second.nodes]
    first_edges = [(edge.source_part, edge.target_part, edge.role.value, edge.mode.value) for edge in first.edges]
    second_edges = [(edge.source_part, edge.target_part, edge.role.value, edge.mode.value) for edge in second.edges]

    assert first_nodes == second_nodes
    assert first_edges == second_edges
    assert first.isolated_parts == second.isolated_parts
    assert first.most_connected_parts == second.most_connected_parts


def test_aspect_permutation_attack_preserves_graph_and_harmonic_truth() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 120.0,
        "Mars": 240.0,
        "Venus": 60.0,
    }
    reversed_positions = dict(reversed(list(positions.items())))

    aspects = find_aspects(positions, include_minor=False)
    reversed_aspects = find_aspects(reversed_positions, include_minor=False)

    signature = sorted((tuple(sorted((a.body1, a.body2))), a.aspect, round(a.orb, 12)) for a in aspects)
    reversed_signature = sorted(
        (tuple(sorted((a.body1, a.body2))), a.aspect, round(a.orb, 12)) for a in reversed_aspects
    )
    assert signature == reversed_signature

    graph = build_aspect_graph(aspects, bodies=positions)
    harmonic = aspect_harmonic_profile(aspects)

    assert graph.nodes == tuple(sorted(graph.nodes, key=lambda node: node.name))
    assert graph.edges == tuple(sorted(graph.edges, key=lambda edge: (edge.body1, edge.body2, edge.aspect)))
    assert harmonic.chart.total == len(aspects)
    for node in graph.nodes:
        assert sum(node.family_counts.values()) == node.degree
        assert harmonic.by_body[node.name].total == node.degree


def test_dignity_sign_boundary_does_not_bleed_across_adjacent_signs() -> None:
    houses = _equal_house_rows(0.0)
    planets = [
        {"name": "Sun", "degree": 149.999999999, "is_retrograde": False},
        {"name": "Moon", "degree": 150.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": False},
    ]

    by_name = {d.planet: d for d in calculate_dignities(planets, houses)}

    assert by_name["Sun"].sign == "Leo"
    assert by_name["Sun"].essential_dignity == "Domicile"
    assert by_name["Moon"].sign == "Virgo"
    assert by_name["Moon"].essential_dignity != "Domicile"
    assert by_name["Moon"].essential_truth is not None
    assert by_name["Moon"].essential_truth.sign == "Virgo"


def test_profection_cycle_monthly_lords_and_activation_are_adversarially_stable() -> None:
    natal_asc = 0.0
    natal_positions = {
        "Sun": 29.999999999,
        "Moon": 30.000000001,
        "Mars": 0.000000001,
    }

    opening = annual_profection(natal_asc, 0, natal_positions=natal_positions, activation_orb=1e-6)
    cycle_return = annual_profection(natal_asc, 12, natal_positions=natal_positions, activation_orb=1e-6)
    next_year = annual_profection(natal_asc, 13, natal_positions=natal_positions, activation_orb=1e-6)

    assert opening.profected_house == 1
    assert cycle_return.profected_house == 1
    assert opening.profected_sign == cycle_return.profected_sign
    assert opening.lord_of_year == cycle_return.lord_of_year
    assert opening.monthly_lords == cycle_return.monthly_lords
    assert next_year.profected_house == 2
    assert next_year.profected_sign == "Taurus"
    assert "Mars" in opening.activated_planets
    assert "Sun" not in opening.activated_planets

    month_0 = monthly_profection(natal_asc, 13, 0)
    month_11 = monthly_profection(natal_asc, 13, 11)
    assert month_0[1:] == ("Taurus", "Venus")
    assert month_11[1:] == ("Aries", "Mars")


def test_vimshottari_boundary_and_cycle_failures_are_explicit() -> None:
    before = dasha_balance(sidereal_to_tropical(NAKSHATRA_SPAN - EPS, J2000), J2000)
    at_boundary = dasha_balance(sidereal_to_tropical(NAKSHATRA_SPAN, J2000), J2000)

    assert before[0] == VIMSHOTTARI_SEQUENCE[0]
    assert at_boundary[0] == VIMSHOTTARI_SEQUENCE[1]

    periods = vimshottari(sidereal_to_tropical(NAKSHATRA_SPAN, J2000), J2000, levels=2)
    assert periods[0].planet == VIMSHOTTARI_SEQUENCE[1]
    assert periods[0].birth_nakshatra is not None
    assert periods[0].nakshatra_fraction == pytest.approx(0.0, abs=1e-10)

    with pytest.raises(ValueError, match="must not be earlier than natal_jd"):
        current_dasha(0.0, J2000, J2000 - EPS)
    with pytest.raises(ValueError, match="supported Vimshottari doctrine key"):
        vimshottari(0.0, J2000, year_basis="ambient-default")


def test_timelord_sequences_validate_containment_and_half_open_boundaries() -> None:
    periods = firdaria(J2000, is_day_chart=True, include_node_subperiods=True)
    validate_firdaria_output(periods)

    majors = [period for period in periods if period.level == 1]
    assert [period.planet for period in majors] == [planet for planet, _ in FIRDARIA_DIURNAL]
    assert sum(period.years for period in majors) == pytest.approx(75.0)

    first_major_end = majors[0].end_jd
    active_at_boundary, _ = current_firdaria(
        J2000,
        first_major_end,
        is_day_chart=True,
        include_node_subperiods=True,
    )
    assert active_at_boundary.planet == majors[1].planet

    with pytest.raises(ValueError, match="outside the 75-year Firdaria cycle"):
        current_firdaria(J2000, J2000 + 75.0 * 365.25, is_day_chart=True)

    releasing = zodiacal_releasing(0.0, J2000, levels=3, fortune_longitude=90.0)
    validate_releasing_output(releasing)
    assert {period.level for period in releasing} == {1, 2, 3}

    with pytest.raises(ValueError, match="levels must be"):
        zodiacal_releasing(0.0, J2000, levels=5)
    with pytest.raises(ValueError, match="lot_name"):
        zodiacal_releasing(0.0, J2000, lot_name="Ambient")


def test_malformed_doctrine_inputs_fail_before_silent_substitution() -> None:
    positions = {"Sun": 20.0, "Moon": 80.0}
    houses = _equal_house_dict(100.0)

    with pytest.raises(ValueError, match="Lot house cusps missing"):
        calculate_lots(positions, {1: 100.0}, is_day_chart=True)

    strict_policy = LotsComputationPolicy(unresolved_reference_mode=LotsReferenceFailureMode.RAISE)
    with pytest.raises(ValueError, match="Unresolved lot ingredient reference"):
        calculate_lots(positions, houses, is_day_chart=True, policy=strict_policy)

    with pytest.raises(ValueError, match="orb_factor"):
        AspectPolicy(orb_factor=0.0)


def test_public_chart_vessel_preserves_lower_layer_truth_without_recomputation() -> None:
    planets = MappingProxyType(
        {
            "Sun": SimpleNamespace(longitude=20.0, speed=1.0),
            "Moon": SimpleNamespace(longitude=80.0, speed=12.0),
            "Mercury": SimpleNamespace(longitude=100.0, speed=1.2),
            "Venus": SimpleNamespace(longitude=130.0, speed=1.1),
            "Mars": SimpleNamespace(longitude=180.0, speed=0.7),
            "Jupiter": SimpleNamespace(longitude=240.0, speed=0.2),
            "Saturn": SimpleNamespace(longitude=300.0, speed=0.1),
        }
    )
    houses = _house_cusps(100.0)
    chart = ChartContext(
        jd_ut=J2000,
        jd_tt=J2000 + 0.0008,
        latitude=35.0,
        longitude=-80.0,
        planets=planets,
        nodes={},
        houses=houses,
    )

    lower_positions = {name: body.longitude for name, body in chart.planets.items()}
    lower_houses = {i + 1: cusp for i, cusp in enumerate(chart.houses.cusps)}

    chart_lots = calculate_lots(lower_positions, lower_houses, chart.is_day)
    chart_aspects = find_aspects(lower_positions, include_minor=False)
    dignity_rows = [
        {"name": name, "degree": body.longitude, "is_retrograde": body.speed < 0.0}
        for name, body in chart.planets.items()
    ]
    chart_dignities = calculate_dignities(dignity_rows, _equal_house_rows(100.0))

    assert _lot_by_name(chart_lots, "Fortune").longitude == pytest.approx(
        (lower_houses[1] + lower_positions["Moon"] - lower_positions["Sun"]) % 360.0
        if chart.is_day
        else (lower_houses[1] + lower_positions["Sun"] - lower_positions["Moon"]) % 360.0
    )
    assert all(aspect_motion_state(aspect).name in {"APPLYING", "SEPARATING", "INDETERMINATE", "STATIONARY"} for aspect in chart_aspects)
    assert {d.planet for d in chart_dignities} == set(lower_positions)

    network = calculate_lot_condition_network_profile(lower_positions, lower_houses, chart.is_day)
    assert network.node_count == len(network.nodes)
    assert network.edge_count == len(network.edges)
