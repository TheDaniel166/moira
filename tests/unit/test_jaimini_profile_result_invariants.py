"""Adversarial evidence substitutions, independent of the evaluator's helpers."""

from dataclasses import replace
import importlib

import pytest

from moira._jaimini_profile_inputs import (
    CLASSICAL, NINE, ArgalaReference, CharaProjection, JaiminiChart,
)
from moira._jaimini_profile_results import JaiminiInvariantError
from moira.argala_assessment import ArgalaStrengthFactors, assess_argala
from moira.chara_profiles import evaluate_chara_profile
from moira.jaimini_profile_policy import ARGALA_IDS, CHARA_IDS


def chara(kind):
    return evaluate_chara_profile(
        JaiminiChart("signs", dict.fromkeys(CLASSICAL, 0), 0),
        profile_id=CHARA_IDS[kind],
    )


def argala(kind, basis="sidereal_longitudes"):
    positions = dict.fromkeys(NINE, 95.0) | {
        "Venus": 31.0, "Sun": 355.0, "Ketu": 215.0,
    }
    if basis == "signs":
        positions = {p: int(v // 30) for p, v in positions.items()}
    return assess_argala(
        JaiminiChart(basis, positions, 0), profile_id=ARGALA_IDS[kind],
        references=(ArgalaReference("lagna"),),
    )


def reflow(rows):
    """Keep local row arithmetic valid while substituting contradictory evidence."""
    cursor, output = 0, []
    for ordinal, row in enumerate(rows):
        output.append(replace(
            row, ordinal=ordinal, start_year=cursor, end_year=cursor + row.years,
        ))
        cursor += row.years
    return tuple(output), cursor


@pytest.mark.parametrize("kind", range(3))
@pytest.mark.parametrize("defect", ["direction", "lagna", "sequence"])
def test_chara_sequence_evidence_is_bound_to_profile_and_lagna(kind, defect):
    result = chara(kind)
    if defect == "direction":
        changes = {"sequence_direction": -result.sequence_direction}
    elif defect == "lagna":
        changes = {"chart": replace(result.chart, lagna=1)}
    else:
        rows = list(result.rows)
        rows[1], rows[2] = rows[2], rows[1]
        rows, total = reflow(rows)
        changes = {"rows": rows, "total_years": total}
    with pytest.raises(ValueError, match="Chara (seed|sequence)"):
        replace(result, **changes)


@pytest.mark.parametrize("kind", range(3))
@pytest.mark.parametrize("defect", ["direction", "count", "exception", "base", "dignity"])
def test_chara_duration_derivation_cannot_be_forged(kind, defect):
    result = chara(kind)
    rows = list(result.rows)
    if defect in ("direction", "count", "exception"):
        index = next(i for i, r in enumerate(rows) if r.exception == "own_sign_twelve")
        row = rows[index]
        changes = {
            "direction": {"count_direction": -row.count_direction},
            "count": {"inclusive_count": 5},
            "exception": {"exception": "none"},
        }[defect]
    else:
        index = next(
            i for i, r in enumerate(rows)
            if 1 <= r.base_years <= 10 and r.dignity_adjustment == 0
        )
        row = rows[index]
        changes = (
            {"base_years": row.base_years + 1, "years": row.years + 1,
             "end_year": row.end_year + 1}
            if defect == "base"
            else {"base_years": row.base_years - 1, "dignity_adjustment": 1}
        )
    rows[index] = replace(row, **changes)
    rows, total = reflow(rows)
    with pytest.raises(ValueError, match="duration derivation"):
        replace(result, rows=rows, total_years=total)


@pytest.mark.parametrize("kind", range(3))
@pytest.mark.parametrize("basis", ["signs", "sidereal_longitudes"])
@pytest.mark.parametrize("defect", ["effect", "reason", "comparison", "group", "character"])
def test_argala_verdict_and_character_must_follow_chart_and_profile(kind, basis, defect):
    result = argala(kind, basis)
    ref, pair = result.references[0], result.references[0].pairs[0]
    if defect == "character":
        characters = tuple(
            replace(c, state="malefic", reason="natural_malefic")
            if c.body == "Venus" else c for c in result.characters
        )
        with pytest.raises(ValueError, match="character evidence"):
            replace(result, characters=characters)
        return
    changes = {
        "effect": {"effect_state": "unobstructed", "reason_codes": (),
                   "strength_comparison": "not_required"},
        "reason": {"reason_codes": (
            "degrees_required" if pair.reason_codes != ("degrees_required",)
            else "strength_comparator_not_admitted",
        )},
        "comparison": {"strength_comparison": "not_required"},
        "group": {"causer_character": "malefic"},
    }[defect]
    changed = replace(pair, **changes)
    with pytest.raises(ValueError, match="(effect evidence|group character)"):
        replace(result, references=(replace(ref, pairs=(changed,) + ref.pairs[1:]),))


@pytest.mark.parametrize("side", ["causer", "blocker"])
def test_quarter_witness_degree_must_match_chart_even_within_the_same_quarter(side):
    result = argala(0)
    ref, pair = result.references[0], result.references[0].pairs[0]
    witness = pair.quarter_pairs[0]
    forged = replace(witness, **{f"{side}_degree": getattr(witness, f"{side}_degree") + 1})
    changed = replace(pair, quarter_pairs=(forged,))
    with pytest.raises(ValueError, match="quarter degrees"):
        replace(result, references=(replace(ref, pairs=(changed,) + ref.pairs[1:]),))


@pytest.mark.parametrize("kind", range(3))
@pytest.mark.parametrize("defect", ["occupancy", "profile"])
def test_special_third_is_bound_to_actual_occupants_and_profile(kind, defect):
    result = argala(kind)
    ref = result.references[0]
    special = ref.special_third
    if defect == "occupancy":
        special = replace(special, occupants=("Venus",))
    else:
        special = replace(
            special, state="not_assessed" if kind == 0 else "absent",
            reason="special_third_threshold_not_admitted" if kind == 0
            else "fewer_than_three_possible",
        )
    with pytest.raises(ValueError, match="special-third evidence"):
        replace(result, references=(replace(ref, special_third=special),))


@pytest.mark.parametrize("kind", [0, 1])
def test_non_rath_profile_rejects_even_one_strength_factor(kind):
    result = argala(kind)
    ref, pair = result.references[0], result.references[0].pairs[0]
    changed = replace(pair, strength_factors=(ArgalaStrengthFactors("causer", 1, (), False),))
    with pytest.raises(ValueError, match="strength factors"):
        replace(result, references=(replace(ref, pairs=(changed,) + ref.pairs[1:]),))


@pytest.mark.parametrize("defect", ["side", "sign", "own_sign", "aspect", "duplicate"])
def test_rath_factors_must_describe_the_actual_side_and_chart(defect):
    result = argala(2)
    ref, pair = result.references[0], result.references[0].pairs[0]
    first, second = pair.strength_factors
    if defect == "duplicate":
        factors = (first, first)
    else:
        changes = {
            "side": {"side": "blocker"},
            "sign": {"sign": 6},  # Venus is also lord of Libra; valid in isolation.
            "own_sign": {"own_sign_bodies": ()},
            "aspect": {"jupiter_rasi_aspect": not first.jupiter_rasi_aspect},
        }[defect]
        factors = (replace(first, **changes), second)
    changed = replace(pair, strength_factors=factors)
    with pytest.raises(ValueError, match="strength factors"):
        replace(result, references=(replace(ref, pairs=(changed,) + ref.pairs[1:]),))


@pytest.mark.parametrize("is_chara", [True, False])
def test_internal_result_construction_error_is_distinct_from_input_error(monkeypatch, is_chara):
    module = importlib.import_module("moira.chara_profiles" if is_chara else "moira.argala_assessment")
    vessel = module.CharaArithmeticRow if is_chara else module.ArgalaPairAssessment
    original = vessel.__post_init__

    def corrupt(self):
        object.__setattr__(self, "count_direction" if is_chara else "causer_sign", 99)
        original(self)

    monkeypatch.setattr(vessel, "__post_init__", corrupt)
    with pytest.raises(JaiminiInvariantError) as failure:
        chara(1) if is_chara else argala(0)
    assert isinstance(failure.value.__cause__, ValueError)
    assert not isinstance(failure.value, ValueError)


@pytest.mark.parametrize("epoch", [1e300, -1e300])
def test_unrepresentable_caller_epoch_remains_an_input_error(epoch):
    with pytest.raises(ValueError, match="epoch"):
        evaluate_chara_profile(
            JaiminiChart("signs", dict.fromkeys(CLASSICAL, 0), 0),
            profile_id=CHARA_IDS[1], projection=CharaProjection(epoch),
        )


@pytest.mark.parametrize("recipe", range(3))
def test_duration_sweep_against_independent_sign_walk(recipe):
    # Admitted manual rules, independently walked rather than modular-counted.
    # This checks implementation consistency, not an additional source lineage.
    lords = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")
    exalted = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
               "Jupiter": 3, "Venus": 11, "Saturn": 6}
    forward = {0, 1, 2, 6, 7, 8}

    def walk(start, stop, direction):
        count = 1
        while start != stop:
            start = (start + direction) % 12
            count += 1
        return count

    rows_checked = 0
    for lagna in range(12):
        for body in CLASSICAL:
            for location in range(12):
                positions = dict.fromkeys(CLASSICAL, 0) | {body: location}
                result = evaluate_chara_profile(
                    JaiminiChart("signs", positions, lagna), profile_id=CHARA_IDS[recipe],
                )
                for row in result.rows:
                    sign, lord = row.sign, lords[row.sign]
                    loc = positions[lord]
                    if loc == sign:
                        expected = 12
                    elif recipe == 0:
                        expected = walk(sign, loc, 1 if sign in forward else -1) - 1
                        if loc == exalted[lord]:
                            expected += 1
                        if loc == (exalted[lord] + 6) % 12:
                            expected -= 1
                    elif recipe == 1:
                        expected = walk(loc, sign, 1 if loc % 2 == 0 else -1)
                    elif (loc - sign) % 12 == 6:
                        expected = 10
                    else:
                        expected = walk(loc, sign, 1 if sign % 2 == 0 else -1) - 1
                    assert row.years == expected, (recipe, lagna, body, location, row)
                    rows_checked += 1
    assert rows_checked == 12096


@pytest.mark.parametrize("kind", range(3))
def test_argala_verdict_sweep_against_independent_count_and_quarter_cases(kind):
    cases = 0
    for causers in range(10):
        for blockers in range(10 - causers):
            for cq in range(4):
                for bq in range(4):
                    positions = {
                        p: 31 + 7.5 * cq if i < causers
                        else 331 + 7.5 * bq if i < causers + blockers
                        else 95.0 for i, p in enumerate(NINE)
                    }
                    result = assess_argala(
                        JaiminiChart("sidereal_longitudes", positions, 0.0),
                        profile_id=ARGALA_IDS[kind], references=(ArgalaReference("lagna"),),
                    )
                    if not causers:
                        expected = "absent"
                    elif not blockers:
                        expected = "unobstructed"
                    elif kind == 2:
                        expected = "indeterminate"
                    elif causers > blockers:
                        expected = "unobstructed"
                    elif kind == 1:
                        expected = "obstructed" if blockers > causers else "indeterminate"
                    else:
                        expected = "indeterminate" if (cq, bq) in ((0, 3), (1, 2)) else "unobstructed"
                    assert result.references[0].pairs[0].effect_state == expected
                    cases += 1
    assert cases == 880
