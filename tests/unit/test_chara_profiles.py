"""Independent printed sequences/durations, calendar arithmetic and legacy parity."""

from dataclasses import asdict, replace
from fractions import Fraction
from math import nextafter, inf
import json
from pathlib import Path

import pytest

from moira._jaimini_profile_inputs import CLASSICAL, CharaProjection, JaiminiChart
from moira.chara_profiles import evaluate_chara_profile
from moira.jaimini_extended import argala, chara_dasha
from moira.jaimini_profile_policy import CHARA_IDS

FIXTURES = Path(__file__).parents[1] / "fixtures/jaimini_profiles"
CORPUS = json.loads((FIXTURES / "chara_source_cases.json").read_text())
RECIPES = dict(zip(("method1", "male", "female"), CHARA_IDS))


@pytest.mark.parametrize(
    "row", CORPUS["sequences"], ids=lambda r: f"{r['branch']}-{r['lagna']}"
)
def test_all_288_printed_sequence_cells(row):
    chart = JaiminiChart("signs", {p: 0 for p in CLASSICAL}, row["lagna"])
    result = evaluate_chara_profile(chart, profile_id=RECIPES[row["branch"]])
    assert [r.sign for r in result.rows] == row["expected_signs"]
    assert len(set(r.sign for r in result.rows)) == 12


@pytest.mark.parametrize("case", CORPUS["durations"], ids=lambda c: c["id"])
def test_published_and_prose_selected_durations(case):
    result = evaluate_chara_profile(
        JaiminiChart(**case["chart"]), profile_id=RECIPES[case["recipe"]]
    )
    assert [[r.sign, r.years] for r in result.rows[: len(case["expected"])]] == case[
        "expected"
    ]
    if case["recipe"] == "female":
        differences = [
            (r.sign, p, r.years)
            for r, p in zip(result.rows, case["published_years"])
            if p != r.years
        ]
        assert differences == [(3, 10, 12)]


@pytest.mark.parametrize(
    "recipe,sign,lord,lord_sign,expected",
    [
        (0, 8, "Jupiter", 9, 0),
        (0, 5, "Mercury", 5, 12),
        (0, 0, "Mars", 9, 10),
        (0, 0, "Mars", 3, 2),
        (1, 0, "Mars", 0, 12),
        (1, 0, "Mars", 1, 2),
        (1, 0, "Mars", 2, 11),
        (2, 0, "Mars", 6, 10),
        (2, 3, "Moon", 3, 12),
        (2, 0, "Mars", 1, 11),
    ],
)
def test_discriminating_source_arithmetic(recipe, sign, lord, lord_sign, expected):
    positions = {p: 0 for p in CLASSICAL}
    positions[lord] = lord_sign
    result = evaluate_chara_profile(
        JaiminiChart("signs", positions, sign), profile_id=CHARA_IDS[recipe]
    )
    assert next(r.years for r in result.rows if r.sign == sign) == expected


@pytest.mark.parametrize("recipe", range(3))
def test_sign_precision_and_longitude_adapter_agree(recipe):
    case = CORPUS["durations"][1]["chart"]
    signs = JaiminiChart(**case)
    degrees = JaiminiChart(
        "sidereal_longitudes",
        {p: s * 30 + 13.125 for p, s in signs.positions},
        signs.lagna * 30 + 29.9,
    )
    a = evaluate_chara_profile(signs, profile_id=CHARA_IDS[recipe])
    b = evaluate_chara_profile(degrees, profile_id=CHARA_IDS[recipe])
    assert a.rows == b.rows and a.total_years == b.total_years


def test_zero_row_preserved_and_rational_calendar_endpoints():
    positions = {p: 0 for p in CLASSICAL} | {"Jupiter": 9}
    chart = JaiminiChart("signs", positions, 8)
    arithmetic = evaluate_chara_profile(chart, profile_id=CHARA_IDS[0])
    result = evaluate_chara_profile(
        chart, profile_id=CHARA_IDS[0], projection=CharaProjection(2451545.125)
    )
    assert arithmetic.rows == result.rows
    assert result.rows[0].years == 0
    assert result.schedule.not_scheduled_zero_duration == tuple(
        r.ordinal for r in result.rows if not r.years
    )
    assert len(result.rows) == 12 and len(result.schedule.intervals) < 12
    cursor = Fraction(2451545) + Fraction(1, 8)
    for interval in result.schedule.intervals:
        row = result.rows[interval.row_ordinal]
        assert interval.start_jd == float(cursor)
        cursor += row.years * Fraction(1461, 4)
        assert interval.end_jd == float(cursor)
        assert interval.start_jd <= nextafter(interval.start_jd, inf) < interval.end_jd
        assert nextafter(interval.end_jd, -inf) < interval.end_jd
    assert result.schedule.intervals[-1].end_jd == float(cursor)
    with pytest.raises(ValueError, match="epoch"):
        evaluate_chara_profile(
            chart, profile_id=CHARA_IDS[0], projection=CharaProjection(1e300)
        )


def test_rows_and_schedules_reject_forged_invariants():
    result = evaluate_chara_profile(
        JaiminiChart(**CORPUS["durations"][1]["chart"]),
        profile_id=CHARA_IDS[1],
        projection=CharaProjection(2451545),
    )
    with pytest.raises(ValueError):
        replace(result, total_years=result.total_years + 1)
    with pytest.raises(ValueError):
        replace(result, rows=result.rows[::-1])
    with pytest.raises(ValueError):
        replace(
            result,
            schedule=replace(result.schedule, intervals=result.schedule.intervals[1:]),
        )
    with pytest.raises(ValueError):
        replace(result.rows[0], years=True)


def test_legacy_valid_numeric_outputs_unchanged():
    corpus = json.loads((FIXTURES / "legacy_regression.json").read_text())
    for case in corpus["argala"]:
        result = asdict(argala(case["chart"], case["lagna"], case["nodes"]))
        receipt = result.pop("computation")
        result.pop("lineage")
        assert receipt["profile_id"] == "moira_argala_existing_v1"
        assert json.loads(json.dumps(result)) == case["expected"]
    for case in corpus["chara"]:
        result = asdict(
            chara_dasha(
                case["chart"], case["lagna"], case["epoch"], cycles=case["cycles"]
            )
        )
        assert json.loads(json.dumps(result)) == case["expected"]
