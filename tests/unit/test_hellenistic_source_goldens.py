"""Independent source-owned golden checks for the Hellenistic engine gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.constants import SIGNS
from moira.decanates import chaldean_face
from moira.dignities import PLANETARY_JOYS, is_in_joy
from moira.egyptian_bounds import (
    CHALDEAN_DAY_BOUNDS,
    CHALDEAN_NIGHT_BOUNDS,
    EGYPTIAN_BOUNDS,
    PTOLEMAIC_BOUNDS,
    EgyptianBoundsDoctrine,
    EgyptianBoundsPolicy,
    egyptian_bound_of,
)
from moira.lots import PARTS_DEFINITIONS, calculate_lots
from moira.timelords import decennials
from moira.triplicity import TriplicityDoctrine, triplicity_assignment_for


_GOLDEN_DIR = Path(__file__).parents[1] / "golden"
_SOURCE_TABLES_PATH = _GOLDEN_DIR / "hellenistic_source_tables.json"
_ZR_PATH = _GOLDEN_DIR / "hellenistic_zr_valens_iv4.json"


@pytest.fixture(scope="module")
def source_tables() -> dict:
    return json.loads(_SOURCE_TABLES_PATH.read_text(encoding="utf-8"))


def _normalized_segments(
    table: dict[str, list[tuple[str, float, float]]],
) -> dict[str, list[list[str | float]]]:
    return {
        sign: [[ruler, float(start), float(end)] for ruler, start, end in rows]
        for sign, rows in table.items()
    }


def _segments_from_chaldean_rule(
    specification: dict,
) -> dict[str, list[list[str | float]]]:
    result: dict[str, list[list[str | float]]] = {}
    widths = specification["segment_widths"]
    for group in specification["triplicity_orders"]:
        for sign in group["signs"]:
            start = 0.0
            rows: list[list[str | float]] = []
            for ruler, width in zip(group["rulers"], widths, strict=True):
                end = start + float(width)
                rows.append([ruler, start, end])
                start = end
            result[sign] = rows
    return result


def _all_bound_goldens(source_tables: dict) -> dict[str, dict[str, list[list[str | float]]]]:
    bounds = source_tables["bounds"]
    return {
        "egyptian": {
            sign: [[ruler, float(start), float(end)] for ruler, start, end in rows]
            for sign, rows in bounds["egyptian"]["segments"].items()
        },
        "ptolemaic": {
            sign: [[ruler, float(start), float(end)] for ruler, start, end in rows]
            for sign, rows in bounds["ptolemaic"]["segments"].items()
        },
        "chaldean_day": _segments_from_chaldean_rule(bounds["chaldean_day"]),
        "chaldean_night": _segments_from_chaldean_rule(bounds["chaldean_night"]),
    }


def _planetary_totals(
    table: dict[str, list[list[str | float]]],
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for rows in table.values():
        for ruler, start, end in rows:
            totals[str(ruler)] = totals.get(str(ruler), 0.0) + (
                float(end) - float(start)
            )
    return totals


def test_source_goldens_carry_authority_semantics_units_and_tolerance(
    source_tables: dict,
) -> None:
    governance = source_tables["governance"]
    assert source_tables["schema_version"] == 1
    assert "never be regenerated from Moira runtime output" in governance["ownership"]
    assert governance["absolute_tolerance"] == pytest.approx(1e-12)
    assert governance["interval_semantics"] == "left_closed_right_open"
    assert governance["numeric_units"] == {
        "longitude": "tropical ecliptic degrees",
        "bound_width": "degrees within one 30-degree zodiac sign",
        "timelord_month": "symbolic 30-day month",
        "timelord_year": "symbolic 360-day year",
    }

    for family in (
        "dorothean_triplicity",
        "planetary_joys",
        "bounds",
        "chaldean_faces",
        "profile_lots",
        "decennials",
    ):
        authority = source_tables[family]["authority"]
        assert authority["work"]
        assert authority["edition"]
        assert authority["location"]
        assert authority["evidence_grade"]
        assert any(key.startswith("online_") for key in authority)

    zr = json.loads(_ZR_PATH.read_text(encoding="utf-8"))
    authority = zr["authority"]
    assert authority["work"] == "Vettius Valens, Anthologies"
    assert authority["section"] == "Book IV, chapter 4"
    assert authority["online_witness"].startswith("https://")
    assert authority["absolute_tolerance"] == pytest.approx(1e-9)
    assert "never regenerate" in authority["ownership"]


@pytest.mark.validation_contract(
    "MOIRA-DOROTHEAN-TRIPLICITY-PINGREE1976-V1"
)
@pytest.mark.parallel(reason="read_only")
def test_dorothean_triplicity_matches_the_named_pingree_table(
    source_tables: dict,
) -> None:
    golden = source_tables["dorothean_triplicity"]
    assert golden["doctrine"] == TriplicityDoctrine.DOROTHEAN_PINGREE_1976.value

    for group in golden["groups"]:
        for sign in group["signs"]:
            day = triplicity_assignment_for(
                sign,
                is_day_chart=True,
                doctrine=TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
            )
            night = triplicity_assignment_for(
                sign,
                is_day_chart=False,
                doctrine=TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
            )
            assert day.element.value == group["element"]
            assert day.signs == tuple(group["signs"])
            assert day.day_ruler == group["day_ruler"]
            assert day.night_ruler == group["night_ruler"]
            assert day.participating_ruler == group["participating_ruler"]
            assert day.active_ruler == group["day_ruler"]
            assert night.active_ruler == group["night_ruler"]


def test_planetary_joy_assignments_match_the_source_synthesis(
    source_tables: dict,
) -> None:
    expected = source_tables["planetary_joys"]["assignments"]
    assert PLANETARY_JOYS == expected
    for planet, house in expected.items():
        assert is_in_joy(planet, house)
        assert not is_in_joy(planet, 1 if house != 1 else 2)


def test_all_four_bound_doctrines_match_the_source_owned_tables_and_rules(
    source_tables: dict,
) -> None:
    expected = _all_bound_goldens(source_tables)
    actual = {
        "egyptian": _normalized_segments(EGYPTIAN_BOUNDS),
        "ptolemaic": _normalized_segments(PTOLEMAIC_BOUNDS),
        "chaldean_day": _normalized_segments(CHALDEAN_DAY_BOUNDS),
        "chaldean_night": _normalized_segments(CHALDEAN_NIGHT_BOUNDS),
    }
    assert actual == expected

    for doctrine, table in expected.items():
        assert set(table) == set(SIGNS)
        source_totals = source_tables["bounds"][doctrine]["planetary_totals"]
        assert _planetary_totals(table) == {
            planet: float(total) for planet, total in source_totals.items()
        }


def test_bound_lookup_obeys_source_intervals_at_every_segment(
    source_tables: dict,
) -> None:
    expected = _all_bound_goldens(source_tables)
    tolerance = source_tables["governance"]["absolute_tolerance"]

    for doctrine_name, table in expected.items():
        policy = EgyptianBoundsPolicy(EgyptianBoundsDoctrine(doctrine_name))
        for sign_index, sign in enumerate(SIGNS):
            sign_start = sign_index * 30.0
            for ruler, start, end in table[sign]:
                for degree in (float(start), (float(start) + float(end)) / 2.0):
                    truth = egyptian_bound_of(sign_start + degree, policy=policy)
                    assert truth.sign == sign
                    assert truth.ruler == ruler
                    assert truth.segment_start_degree == pytest.approx(
                        float(start), abs=tolerance
                    )
                    assert truth.segment_end_degree == pytest.approx(
                        float(end), abs=tolerance
                    )


def test_chaldean_faces_match_the_identified_later_witness_cycle(
    source_tables: dict,
) -> None:
    golden = source_tables["chaldean_faces"]
    cycle = golden["ruler_cycle_from_aries_zero"]
    width = float(golden["face_width_degrees"])
    assert golden["face_count"] == 36

    for index in range(golden["face_count"]):
        expected = cycle[index % len(cycle)]
        boundary = chaldean_face(index * width)
        midpoint = chaldean_face(index * width + width / 2.0)
        assert boundary.ruling_planet == expected
        assert midpoint.ruling_planet == expected
        assert boundary.decan_number == index % 3 + 1


def test_profile_lot_formulas_and_concrete_case_match_valens(
    source_tables: dict,
) -> None:
    golden = source_tables["profile_lots"]
    formulas = golden["formulas"]
    definitions = {definition.name: definition for definition in PARTS_DEFINITIONS}

    for name, formula in formulas.items():
        definition = definitions[name]
        assert definition.projector == formula["projector"]
        assert definition.day_add == formula["day_add"]
        assert definition.day_sub == formula["day_sub"]
        assert definition.reverse_at_night is formula["reverse_at_night"]

    case = golden["case"]
    house_cusps = {number: (number - 1) * 30.0 for number in range(1, 13)}
    tolerance = source_tables["governance"]["absolute_tolerance"]
    for is_day_chart, expected_key in (
        (True, "day_expected"),
        (False, "night_expected"),
    ):
        parts = calculate_lots(
            case["planet_longitudes"],
            house_cusps,
            is_day_chart,
            asc_longitude=case["asc_longitude"],
            mc_longitude=case["mc_longitude"],
        )
        by_name = {part.name: part for part in parts}
        for name, expected in case[expected_key].items():
            part = by_name[name]
            truth = part.computation_truth
            assert part.longitude == pytest.approx(float(expected), abs=tolerance)
            assert truth is not None
            assert truth.projector_key == formulas[name]["projector"]
            assert truth.requested_add_key == formulas[name]["day_add"]
            assert truth.requested_sub_key == formulas[name]["day_sub"]
            assert truth.reversed_at_night is formulas[name]["reverse_at_night"]
            assert truth.reversed_for_chart is (
                formulas[name]["reverse_at_night"] and not is_day_chart
            )


def test_decennials_l1_l2_match_valens_minor_period_arithmetic(
    source_tables: dict,
) -> None:
    golden = source_tables["decennials"]
    case = golden["synthetic_geometry_case"]
    tolerance = source_tables["governance"]["absolute_tolerance"]
    periods = decennials(
        float(case["natal_jd"]),
        case["natal_positions"],
        case["is_day_chart"],
        levels=2,
    )
    major = [period for period in periods if period.level == 1]
    assert [period.planet for period in major] == case["expected_sequence"]
    assert all(
        period.months
        == pytest.approx(float(golden["major_period_months"]), abs=tolerance)
        for period in major
    )
    assert all(
        period.years
        == pytest.approx(float(golden["major_period_years"]), abs=tolerance)
        for period in major
    )
    assert all(
        period.month_basis_days
        == pytest.approx(float(golden["month_basis_days"]), abs=tolerance)
        for period in major
    )

    first_major = major[0]
    assert first_major.sequence == tuple(case["expected_sequence"])
    assert first_major.end_distribution_day - first_major.start_distribution_day == (
        pytest.approx(
            float(golden["major_period_months"])
            * float(golden["month_basis_days"]),
            abs=tolerance,
        )
    )
    subs = [
        period
        for period in periods
        if period.level == 2 and period.major_planet == first_major.planet
    ]
    assert [period.planet for period in subs] == case["expected_sequence"]
    assert [period.months for period in subs] == pytest.approx(
        [
            float(golden["minor_period_months"][planet])
            for planet in case["expected_sequence"]
        ],
        abs=tolerance,
    )
    assert sum(period.months for period in subs) == pytest.approx(
        float(golden["major_period_months"]),
        abs=tolerance,
    )
