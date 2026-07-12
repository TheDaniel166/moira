"""Primary-source, public-contract, and adversarial progressed Astrodyne tests."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import moira
import moira.facade as facade_module
import moira.progressed_astrodynes as progressed_module
from moira.progressed_astrodynes import (
    DEFAULT_PROGRESSED_ASTRODYNE_POLICY,
    ProgressedAstrodynePolicy,
    ProgressedAstrodyneTerminal,
    ProgressedAstrodyneTier,
    ProgressedBaselineValue,
    ProgressedBodyPlacement,
    ProgressedCompoundDuration,
    ProgressedInfluenceUnit,
    ProgressedMutualReceptionAllocation,
    ProgressedNatalBodyValue,
    ProgressedTerminalLocation,
    ProgressedTerminalKind,
    evaluate_major_progressed_relation,
    evaluate_accessory_progressed_relation,
    normal_progressed_horoscope,
    practical_progressed_horoscope,
    progressed_aspect_at_distance,
    progressed_aspect_harmony,
    progressed_aspect_peak_power,
    progressed_aspect_percentage,
    progressed_carry,
    progressed_dated_aspect,
    progressed_compound_total_influence,
    progressed_mutual_reception_bonus,
    progressed_total_influence,
    reenforce_major_progressed_relation,
    relative_major_terminal_truth,
)


_FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "progressed_astrodynes_church_of_light.json"
)
_NORMAL_FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "progressed_astrodynes_benjamine_normal_1949.json"
)
_DATED_FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "progressed_astrodynes_benjamine_dated_1949.json"
)


@pytest.fixture(scope="module")
def source_fixture() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def normal_fixture() -> dict:
    return json.loads(_NORMAL_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dated_fixture() -> dict:
    return json.loads(_DATED_FIXTURE_PATH.read_text(encoding="utf-8"))


def _normal_result(fixture: dict, *, reverse: bool = False):
    bodies = [
        ProgressedNatalBodyValue(body, *values)
        for body, values in fixture["birth_bodies"].items()
    ]
    signs = {
        sign: ProgressedBaselineValue(*values)
        for sign, values in fixture["birth_signs"].items()
    }
    houses = {
        int(house): ProgressedBaselineValue(*values)
        for house, values in fixture["birth_houses"].items()
    }
    placements = [
        ProgressedBodyPlacement(body, *values)
        for body, values in fixture["placements"].items()
    ]
    if reverse:
        bodies.reverse()
        placements.reverse()
    return normal_progressed_horoscope(bodies, signs, houses, placements)


def _dated_normal_result(fixture: dict):
    dated = json.loads(_DATED_FIXTURE_PATH.read_text(encoding="utf-8"))
    bodies = [
        ProgressedNatalBodyValue(body, *values)
        for body, values in fixture["birth_bodies"].items()
    ]
    signs = {
        sign: ProgressedBaselineValue(*values)
        for sign, values in fixture["birth_signs"].items()
    }
    houses = {
        int(house): ProgressedBaselineValue(*values)
        for house, values in fixture["birth_houses"].items()
    }
    placements = []
    for body, values in fixture["placements"].items():
        longitude, house = values
        if body == "Moon":
            house = 7
        placements.append(ProgressedBodyPlacement(body, longitude, house))
    return normal_progressed_horoscope(bodies, signs, houses, placements), dated


def test_fixed_policy_pins_every_source_constant() -> None:
    policy = DEFAULT_PROGRESSED_ASTRODYNE_POLICY
    assert policy.major_carry_factor == 0.5
    assert policy.major_moon_carry_divisor == 14.0
    assert policy.minor_carry_divisor == 54.6
    assert policy.transit_carry_divisor == 730.50
    assert policy.aspect_percentage_per_orb_degree == 0.05
    assert policy.major_moon_aspect_divisor == 7.0
    assert policy.minor_aspect_divisor == 27.3
    assert policy.transit_aspect_divisor == 365.25
    assert policy.effective_orb_arcmin == 60.0
    assert policy.orb_limit_fraction == 0.5
    assert policy.major_mutual_reception_bonus_each == 2.5
    assert policy.total_influence_average_factor == 0.75


def test_internal_module_all_is_unique_bound_and_private_free() -> None:
    assert len(progressed_module.__all__) == len(set(progressed_module.__all__))
    assert all(not name.startswith("_") for name in progressed_module.__all__)
    assert all(hasattr(progressed_module, name) for name in progressed_module.__all__)


def test_progressed_public_exports_are_identity_preserving() -> None:
    admitted = {
        "DEFAULT_PROGRESSED_ASTRODYNE_POLICY",
        "PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES",
        "ProgressedDatedAspectTruth",
        "ProgressedCompoundDuration",
        "ProgressedNormalHoroscope",
        "ProgressedPracticalHoroscope",
        "normal_progressed_horoscope",
        "practical_progressed_horoscope",
        "progressed_dated_aspect",
        "progressed_total_influence",
    }
    for name in admitted:
        expected = getattr(progressed_module, name)
        assert getattr(moira, name) is expected
        assert getattr(facade_module, name) is expected
        assert name in moira.__all__
        assert name in facade_module.__all__


def test_progressed_facade_delegates_without_kernel(monkeypatch) -> None:
    sentinel = object()
    received = {}

    def fake_normal(*args, **kwargs):
        received["args"] = args
        received["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(facade_module, "normal_progressed_horoscope", fake_normal)
    engine = moira.Moira(kernel_path=None)
    result = engine.normal_progressed_astrodynes(
        "bodies",
        "signs",
        "houses",
        "placements",
        policy="policy",
    )

    assert result is sentinel
    assert received == {
        "args": ("bodies", "signs", "houses", "placements"),
        "kwargs": {"policy": "policy"},
    }


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("major_carry_factor", 0.4),
        ("minor_aspect_divisor", 27.0),
        ("effective_orb_arcmin", 59.0),
        ("major_mutual_reception_bonus_each", 5.0),
        ("manual_rounding_digits", 3),
    ),
)
def test_policy_rejects_unsourced_variants(field: str, value: float) -> None:
    with pytest.raises(ValueError, match=field):
        ProgressedAstrodynePolicy(**{field: value})


def test_source_fixture_has_primary_provenance(source_fixture: dict) -> None:
    authority = source_fixture["authority"]
    assert authority["title"] == "The Astrodyne Manual"
    assert authority["year"] == 1946
    assert authority["capture_semantics"].startswith("direct visual inspection")


def test_all_manual_carry_examples(source_fixture: dict) -> None:
    for example in source_fixture["carry_examples"]:
        truth = progressed_carry(
            example["birth_power"],
            example["birth_harmony"],
            example["birth_discord"],
            example["dignity_delta"],
            example["tier"],
        )
        assert truth.manual_carried_power == example["manual_carried_power"]
        assert truth.manual_carried_harmony == example["manual_carried_harmony"]
        assert truth.manual_carried_discord == example["manual_carried_discord"]
        assert truth.manual_dignity_harmony == example["manual_dignity_harmony"]
        assert truth.manual_dignity_discord == example["manual_dignity_discord"]


def test_moon_manual_total_sums_separately_rounded_components(
    source_fixture: dict,
) -> None:
    example = next(
        item
        for item in source_fixture["carry_examples"]
        if item["id"] == "major_moon_home"
    )
    truth = progressed_carry(
        example["birth_power"],
        example["birth_harmony"],
        example["birth_discord"],
        example["dignity_delta"],
        example["tier"],
    )
    assert truth.manual_carried_harmony == 0.79
    assert truth.manual_dignity_harmony == 0.14
    assert truth.manual_total_harmony == 0.93
    assert truth.total_harmony == pytest.approx(13.09 / 14.0)


def test_all_manual_aspect_percentage_peak_and_date_examples(
    source_fixture: dict,
) -> None:
    for example in source_fixture["aspect_examples"]:
        percentage = progressed_aspect_percentage(
            example["aspect"],
            example["governing_house_class"],
            uses_luminary_column=example["uses_luminary_column"],
        )
        assert percentage.selected_orb_degrees == example["selected_orb_degrees"]
        assert percentage.progressed_percentage == pytest.approx(
            example["progressed_percentage"]
        )

        peak = progressed_aspect_peak_power(
            example["birth_power_a"],
            example["birth_power_b"],
            percentage.progressed_percentage,
            example["tier"],
        )
        assert peak.manual_average_birth_power == example[
            "manual_average_birth_power"
        ]
        assert peak.manual_major_peak_power == example["manual_major_peak_power"]
        assert peak.manual_peak_power == example["manual_peak_power"]

        moment = progressed_aspect_at_distance(
            peak.peak_power,
            example["distance_arcmin"],
            manual_peak_power=peak.manual_peak_power,
        )
        assert moment.manual_power == example["manual_power_on_date"]

        if "manual_harmony_on_date" in example:
            harmony = progressed_aspect_harmony(
                example["harmony_body_a"],
                example["harmony_body_b"],
                example["aspect"],
                moment.manual_power,
            )
            assert round(harmony.total_harmony, 2) == example[
                "manual_harmony_on_date"
            ]
        if "manual_discord_on_date" in example:
            harmony = progressed_aspect_harmony(
                example["harmony_body_a"],
                example["harmony_body_b"],
                example["aspect"],
                moment.manual_power,
            )
            assert round(harmony.total_discord, 2) == example[
                "manual_discord_on_date"
            ]


def test_parallel_uses_conjunction_row_and_mercury_can_use_luminary_column() -> None:
    parallel = progressed_aspect_percentage(
        "parallel", "succedent", uses_luminary_column=False
    )
    mercury = progressed_aspect_percentage(
        "opposition", "angular", uses_luminary_column=True
    )
    ordinary = progressed_aspect_percentage(
        "opposition", "angular", uses_luminary_column=False
    )

    assert parallel.source_aspect == "conjunction"
    assert parallel.selected_orb_degrees == 10.0
    assert parallel.progressed_percentage == 0.5
    assert mercury.source_column == "luminary"
    assert mercury.selected_orb_degrees == 15.0
    assert ordinary.selected_orb_degrees == 12.0


@pytest.mark.parametrize(
    ("distance", "within", "fraction", "manual_power"),
    (
        (0.0, True, 1.0, 10.0),
        (30.0, True, 0.75, 7.5),
        (60.0, True, 0.5, 5.0),
        (60.000001, False, 0.0, 0.0),
    ),
)
def test_progressed_orb_boundaries(
    distance: float,
    within: bool,
    fraction: float,
    manual_power: float,
) -> None:
    truth = progressed_aspect_at_distance(10.0, distance)
    assert truth.within_orb is within
    assert truth.scale_fraction == pytest.approx(fraction)
    assert truth.manual_power == manual_power


def test_mutual_reception_tier_examples(source_fixture: dict) -> None:
    expected = source_fixture["mutual_reception_bonus_each"]
    for tier in ProgressedAstrodyneTier:
        truth = progressed_mutual_reception_bonus(tier)
        assert truth.manual_bonus_each == expected[tier.value]


def test_total_influence_manual_year_component(source_fixture: dict) -> None:
    example = source_fixture["total_influence_example"]
    truth = progressed_total_influence(
        example["peak_power"],
        example["peak_harmony"],
        example["peak_discord"],
        example["duration"],
        example["unit"],
    )
    assert truth.unit is ProgressedInfluenceUnit.YEAR
    assert truth.manual_average_power == example["manual_average_power"]
    assert truth.manual_total_power == example["manual_total_power"]
    assert truth.manual_average_discord == example["manual_average_discord"]
    assert truth.manual_total_discord == example["manual_total_discord"]
    assert truth.total_power == pytest.approx(14.37 * 0.75 * 36.0)


def test_compound_total_influence_reproduces_full_manual_example() -> None:
    truth = progressed_compound_total_influence(
        14.37,
        0.0,
        7.185,
        ProgressedCompoundDuration(years=36, months=2, days=12.0),
    )

    assert truth.manual_average_power == 10.78
    assert (truth.power.years, truth.power.months, truth.power.days) == (
        390,
        2,
        25.38,
    )
    assert truth.manual_average_discord == 5.39
    assert (truth.discord.years, truth.discord.months, truth.discord.days) == (
        195,
        1,
        12.69,
    )
    assert truth.harmony.years == truth.harmony.months == 0
    assert truth.harmony.days == 0.0


def test_compound_duration_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ProgressedCompoundDuration(years=-1)
    with pytest.raises(TypeError, match="months must be an integer"):
        ProgressedCompoundDuration(months=1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be ProgressedCompoundDuration"):
        progressed_compound_total_influence(1.0, 0.0, 0.0, 10)  # type: ignore[arg-type]


def test_benjamine_normal_progressed_signs_and_houses(
    normal_fixture: dict,
) -> None:
    result = _normal_result(normal_fixture)

    for sign, expected in normal_fixture["expected_signs"].items():
        entry = result.sign(sign)
        assert entry.manual_total_power == expected[0]
        assert entry.manual_total_harmony == expected[1]
        assert entry.manual_total_discord == expected[2]
    for house, expected in normal_fixture["expected_houses"].items():
        entry = result.house(int(house))
        assert entry.manual_total_power == expected[0]
        assert entry.manual_total_harmony == expected[1]
        assert entry.manual_total_discord == expected[2]

    assert result.checksums_pass
    assert result.power_checksum_delta == pytest.approx(0.0, abs=1e-9)
    assert result.harmony_checksum_delta == pytest.approx(0.0, abs=1e-9)


def test_normal_progressed_profiles_preserve_dignity_and_carry_truth(
    normal_fixture: dict,
) -> None:
    result = _normal_result(normal_fixture)
    profiles = {profile.body: profile for profile in result.profiles}

    assert profiles["Mercury"].placement.sign == "Aquarius"
    assert profiles["Mercury"].dignity_delta == 3.0
    assert profiles["Mercury"].carry.manual_dignity_harmony == 1.5
    assert profiles["Mars"].dignity_delta == -1.0
    assert profiles["Pluto"].dignity_delta == -2.0
    assert profiles["Moon"].carry.tier is ProgressedAstrodyneTier.MAJOR_MOON
    assert profiles["M.C."].dignity_delta == 0.0
    assert profiles["Asc."].dignity_delta == 0.0


def test_normal_progressed_output_is_input_order_independent(
    normal_fixture: dict,
) -> None:
    forward = _normal_result(normal_fixture)
    reverse = _normal_result(normal_fixture, reverse=True)

    assert forward == reverse
    assert tuple(profile.body for profile in forward.profiles) == (
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
        "M.C.",
        "Asc.",
    )


def test_normal_progressed_rejects_incomplete_or_duplicate_inputs(
    normal_fixture: dict,
) -> None:
    bodies = [
        ProgressedNatalBodyValue(body, *values)
        for body, values in normal_fixture["birth_bodies"].items()
    ]
    signs = {
        sign: ProgressedBaselineValue(*values)
        for sign, values in normal_fixture["birth_signs"].items()
    }
    houses = {
        int(house): ProgressedBaselineValue(*values)
        for house, values in normal_fixture["birth_houses"].items()
    }
    placements = [
        ProgressedBodyPlacement(body, *values)
        for body, values in normal_fixture["placements"].items()
    ]

    with pytest.raises(ValueError, match="requires ten planets"):
        normal_progressed_horoscope(bodies[:-1], signs, houses, placements)
    with pytest.raises(ValueError, match="duplicate placements body"):
        normal_progressed_horoscope(
            bodies,
            signs,
            houses,
            [*placements[:-1], placements[0]],
        )
    with pytest.raises(ValueError, match="all twelve signs"):
        normal_progressed_horoscope(
            bodies,
            dict(list(signs.items())[:-1]),
            houses,
            placements,
        )


def test_progressed_placement_rejects_bad_geometry() -> None:
    with pytest.raises(ValueError, match="unsupported Astrodyne body"):
        ProgressedBodyPlacement("Ceres", 0.0, 1)
    with pytest.raises(ValueError, match="house must be in"):
        ProgressedBodyPlacement("Sun", 0.0, 13)
    with pytest.raises(ValueError, match="finite"):
        ProgressedBodyPlacement("Sun", math.nan, 1)


def _sun_moon_major_relation(*, reverse: bool = False, distance_arcmin: float = 4.0):
    sun_p = ProgressedAstrodyneTerminal(
        "Sun", "major_progressed", 0.0, "cadent", 10.0
    )
    moon_r = ProgressedAstrodyneTerminal(
        "Moon",
        "radical",
        45.0 + distance_arcmin / 60.0,
        "succedent",
        20.0,
    )
    sun_r = ProgressedAstrodyneTerminal("Sun", "radical", 300.0, "cadent", 9.0)
    moon_p = ProgressedAstrodyneTerminal(
        "Moon", "major_progressed", 100.0, "succedent", 19.0
    )
    sun = ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65)
    moon = ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0)
    if reverse:
        return evaluate_major_progressed_relation(
            moon_r,
            sun_p,
            moon_p,
            sun_r,
            moon,
            sun,
            "semi-square",
        )
    return evaluate_major_progressed_relation(
        sun_p,
        moon_r,
        sun_r,
        moon_p,
        sun,
        moon,
        "semi-square",
    )


def test_major_relation_preserves_terminals_peak_and_dated_truth() -> None:
    relation = _sun_moon_major_relation()

    assert relation.tier is ProgressedAstrodyneTier.MAJOR
    assert {item.terminal_id for item in relation.direct_terminals} == {
        "Sun:p",
        "Moon:r",
    }
    assert {item.terminal_id for item in relation.indirect_terminals} == {
        "Sun:r",
        "Moon:p",
    }
    assert relation.percentage_truth.governing_house_class == "succedent"
    assert relation.percentage_truth.uses_luminary_column is True
    assert relation.percentage_truth.progressed_percentage == 0.25
    assert relation.peak_truth.manual_peak_power == 16.51
    assert relation.manual_peak_harmony_truth.total_discord == 16.51
    assert relation.distance_arcmin == pytest.approx(4.0)
    assert relation.moment_truth.manual_power == 15.96
    assert relation.manual_moment_harmony_truth.total_discord == 15.96
    assert relation.detected and relation.admitted and relation.scored


def test_major_relation_is_canonical_under_direct_input_reversal() -> None:
    assert _sun_moon_major_relation() == _sun_moon_major_relation(reverse=True)


def test_relative_terminal_truth_reproduces_sun_moon_manual_example(
    normal_fixture: dict,
) -> None:
    relation = _sun_moon_major_relation()
    normal = _normal_result(normal_fixture)
    terminals = {
        item.terminal.terminal_id: item
        for item in relative_major_terminal_truth(relation, normal)
    }

    assert terminals["Sun:r"].direct is False
    assert terminals["Sun:r"].added_discord == 7.98
    assert terminals["Sun:r"].manual_net_harmony == -29.63
    assert terminals["Sun:p"].direct is True
    assert terminals["Sun:p"].normal_discord == 11.83
    assert terminals["Sun:p"].manual_net_harmony == -27.79
    assert terminals["Moon:p"].direct is False
    assert terminals["Moon:p"].normal_harmony == 0.93
    assert terminals["Moon:p"].manual_net_harmony == -7.05
    assert terminals["Moon:r"].direct is True
    assert terminals["Moon:r"].normal_harmony == 11.09
    assert terminals["Moon:r"].manual_net_harmony == -4.87


def test_major_relation_outside_orb_is_detected_but_not_admitted() -> None:
    relation = _sun_moon_major_relation(distance_arcmin=60.0001)

    assert relation.detected
    assert not relation.admitted
    assert not relation.scored
    assert relation.moment_truth.power == 0.0
    assert relation.moment_truth.manual_power == 0.0


def test_major_moon_relation_uses_submajor_divisor() -> None:
    moon_p = ProgressedAstrodyneTerminal(
        "Moon", "major_progressed", 0.0, "succedent", 20.0
    )
    venus_r = ProgressedAstrodyneTerminal(
        "Venus", "radical", 0.0, "succedent", 20.0
    )
    moon_r = ProgressedAstrodyneTerminal(
        "Moon", "radical", 100.0, "succedent", 19.0
    )
    venus_p = ProgressedAstrodyneTerminal(
        "Venus", "major_progressed", 120.0, "succedent", 19.5
    )
    relation = evaluate_major_progressed_relation(
        moon_p,
        venus_r,
        moon_r,
        venus_p,
        ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0),
        ProgressedNatalBodyValue("Venus", 47.63, 11.27, 0.0),
        "conjunction",
    )

    assert relation.tier is ProgressedAstrodyneTier.MAJOR_MOON
    assert relation.peak_truth.tier_divisor == 7.0


def test_same_body_major_relation_has_only_two_terminals() -> None:
    sun = ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65)
    relation = evaluate_major_progressed_relation(
        ProgressedAstrodyneTerminal("Sun", "major_progressed", 90.0, "angular"),
        ProgressedAstrodyneTerminal("Sun", "radical", 0.0, "cadent"),
        None,
        None,
        sun,
        sun,
        "square",
    )

    assert len(relation.direct_terminals) == 2
    assert relation.indirect_terminals == ()


def test_major_relation_rejects_invalid_terminal_assembly() -> None:
    sun_p = ProgressedAstrodyneTerminal("Sun", "major_progressed", 0.0, "cadent")
    moon_r = ProgressedAstrodyneTerminal("Moon", "radical", 45.0, "succedent")
    sun = ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65)
    moon = ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0)

    with pytest.raises(ValueError, match="requires both indirect counterparts"):
        evaluate_major_progressed_relation(
            sun_p, moon_r, None, None, sun, moon, "semi-square"
        )
    with pytest.raises(ValueError, match="same body"):
        evaluate_major_progressed_relation(
            sun_p,
            moon_r,
            ProgressedAstrodyneTerminal("Venus", "radical", 0.0, "cadent"),
            ProgressedAstrodyneTerminal("Moon", "major_progressed", 0.0, "cadent"),
            sun,
            moon,
            "semi-square",
        )


def test_parallel_relation_requires_declinations() -> None:
    sun = ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65)
    moon = ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0)
    with pytest.raises(ValueError, match="require both terminal declinations"):
        evaluate_major_progressed_relation(
            ProgressedAstrodyneTerminal("Sun", "major_progressed", 0.0, "cadent"),
            ProgressedAstrodyneTerminal("Moon", "radical", 0.0, "succedent"),
            ProgressedAstrodyneTerminal("Sun", "radical", 0.0, "cadent"),
            ProgressedAstrodyneTerminal(
                "Moon", "major_progressed", 0.0, "succedent"
            ),
            sun,
            moon,
            "parallel",
        )


def test_minor_asc_parallel_venus_manual_example() -> None:
    relation = evaluate_accessory_progressed_relation(
        ProgressedAstrodyneTerminal(
            "Asc.", "minor_progressed", 0.0, "angular", -20.1
        ),
        ProgressedAstrodyneTerminal(
            "Venus", "major_progressed", 0.0, "succedent", -(19 + 46 / 60)
        ),
        ProgressedAstrodyneTerminal(
            "Venus", "radical", 0.0, "succedent", -18.0
        ),
        ProgressedNatalBodyValue("Asc.", 37.51, 0.0, 6.2),
        ProgressedNatalBodyValue("Venus", 47.63, 11.27, 0.0),
        "parallel",
    )

    assert relation.tier is ProgressedAstrodyneTier.MINOR
    assert relation.distance_arcmin == pytest.approx(20.0)
    assert relation.percentage_truth.progressed_percentage == 0.5
    assert relation.peak_truth.manual_major_peak_power == 21.29
    assert relation.peak_truth.manual_peak_power == 0.78
    assert relation.moment_truth.manual_power == 0.65
    assert round(relation.manual_moment_harmony_truth.total_harmony, 2) == 0.16


def test_transit_neptune_sesquisquare_sun_manual_example() -> None:
    relation = evaluate_accessory_progressed_relation(
        ProgressedAstrodyneTerminal(
            "Neptune", "transit", 193 + 31 / 60, "angular"
        ),
        ProgressedAstrodyneTerminal(
            "Sun", "major_progressed", 328 + 15 / 60, "cadent"
        ),
        ProgressedAstrodyneTerminal("Sun", "radical", 300.0, "cadent"),
        ProgressedNatalBodyValue("Neptune", 35.04, 18.71, 0.0),
        ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65),
        "sesqui-square",
    )

    assert relation.tier is ProgressedAstrodyneTier.TRANSIT
    assert relation.distance_arcmin == pytest.approx(16.0)
    assert relation.percentage_truth.source_column == "planet"
    assert relation.percentage_truth.progressed_percentage == 0.25
    assert relation.peak_truth.manual_major_peak_power == 17.34
    assert relation.peak_truth.manual_peak_power == 0.05
    assert relation.moment_truth.manual_power == 0.04
    assert relation.manual_moment_harmony_truth.total_discord == 0.04


def _minor_neptune_reenforcement(
    major,
    target,
    counterpart,
):
    moving_longitude = (target.longitude_deg + 135.0 + 9.0 / 60.0) % 360.0
    return evaluate_accessory_progressed_relation(
        ProgressedAstrodyneTerminal(
            "Neptune", "minor_progressed", moving_longitude, "cadent"
        ),
        target,
        counterpart,
        ProgressedNatalBodyValue("Neptune", 35.04, 18.71, 0.0),
        (
            ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0)
            if target.body == "Moon"
            else ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65)
        ),
        "sesqui-square",
    )


def test_direct_minor_reenforcement_manual_example() -> None:
    major = _sun_moon_major_relation()
    target = next(
        item for item in major.direct_terminals if item.terminal_id == "Moon:r"
    )
    counterpart = next(
        item for item in major.indirect_terminals if item.terminal_id == "Moon:p"
    )
    minor = _minor_neptune_reenforcement(major, target, counterpart)
    truth = reenforce_major_progressed_relation(major, minor)

    assert truth.target_is_direct
    assert truth.terminal_factor == 1.0
    assert truth.manual_unreenforced_power == 15.96
    assert truth.manual_peak_power == 3.99
    assert truth.moment_truth.manual_power == 3.69
    assert truth.manual_reenforced_power == 19.65
    assert truth.discord_unchanged == 15.96


def test_indirect_minor_reenforcement_is_half_strength() -> None:
    major = _sun_moon_major_relation()
    target = next(
        item for item in major.indirect_terminals if item.terminal_id == "Sun:r"
    )
    counterpart = next(
        item for item in major.direct_terminals if item.terminal_id == "Sun:p"
    )
    # The source's indirect-terminal comparison retains the same .25
    # percentage; use a succedent terminal context to exercise that rule.
    target = ProgressedAstrodyneTerminal(
        target.body,
        target.kind,
        target.longitude_deg,
        "succedent",
        target.declination_deg,
    )
    counterpart = ProgressedAstrodyneTerminal(
        counterpart.body,
        counterpart.kind,
        counterpart.longitude_deg,
        "succedent",
        counterpart.declination_deg,
    )
    major = evaluate_major_progressed_relation(
        next(item for item in major.direct_terminals if item.terminal_id == "Moon:r"),
        counterpart,
        next(item for item in major.indirect_terminals if item.terminal_id == "Moon:p"),
        target,
        ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0),
        ProgressedNatalBodyValue("Sun", 103.64, 0.0, 21.65),
        "semi-square",
    )
    minor = _minor_neptune_reenforcement(major, target, counterpart)
    truth = reenforce_major_progressed_relation(major, minor)

    assert not truth.target_is_direct
    assert truth.terminal_factor == 0.5
    assert truth.manual_peak_power == 2.0
    assert truth.moment_truth.manual_power == 1.85
    assert truth.manual_reenforced_power == 17.81


def test_reenforcement_rejects_transit_and_unrelated_terminal() -> None:
    major = _sun_moon_major_relation()
    transit = evaluate_accessory_progressed_relation(
        ProgressedAstrodyneTerminal("Neptune", "transit", 135.0, "angular"),
        next(item for item in major.direct_terminals if item.terminal_id == "Moon:r"),
        next(item for item in major.indirect_terminals if item.terminal_id == "Moon:p"),
        ProgressedNatalBodyValue("Neptune", 35.04, 18.71, 0.0),
        ProgressedNatalBodyValue("Moon", 28.39, 11.09, 0.0),
        "sesqui-square",
    )
    with pytest.raises(ValueError, match="only a minor"):
        reenforce_major_progressed_relation(major, transit)

    unrelated = evaluate_accessory_progressed_relation(
        ProgressedAstrodyneTerminal("Neptune", "minor_progressed", 135.0, "cadent"),
        ProgressedAstrodyneTerminal("Venus", "radical", 0.0, "succedent"),
        ProgressedAstrodyneTerminal(
            "Venus", "major_progressed", 30.0, "succedent"
        ),
        ProgressedNatalBodyValue("Neptune", 35.04, 18.71, 0.0),
        ProgressedNatalBodyValue("Venus", 47.63, 11.27, 0.0),
        "sesqui-square",
    )
    with pytest.raises(ValueError, match="not a terminal"):
        reenforce_major_progressed_relation(major, unrelated)


def test_complete_dated_manual_table_is_captured_with_explicit_anomalies(
    dated_fixture: dict,
) -> None:
    assert dated_fixture["authority"]["printed_pages"] == [42, 43, 45, 46]
    assert len(dated_fixture["relations"]) == 27
    assert len(dated_fixture["published_anomalies"]) == 9

    exceptional_rows = {
        "saturn_sun",
        "sun_pluto_r",
        "mc_moon",
        "mercury_uranus_p",
        "jupiter_saturn",
        "jupiter_uranus",
    }
    observed_exceptions = set()
    for row in dated_fixture["relations"]:
        truth = progressed_dated_aspect(
            row["id"],
            row["a"],
            row["b"],
            row["aspect"],
            row["direct"],
            row["indirect"],
            row["peak"],
            row["distance"],
        )
        computed = [truth.power, truth.harmony, truth.discord]
        if computed != row["published"]:
            observed_exceptions.add(row["id"])
        else:
            assert row["id"] not in exceptional_rows
    assert observed_exceptions == exceptional_rows


def _practical_result(normal_fixture: dict, dated_fixture: dict):
    normal, _ = _dated_normal_result(normal_fixture)
    aspects = tuple(
        progressed_dated_aspect(
            row["id"],
            row["a"],
            row["b"],
            row["aspect"],
            row["direct"],
            row["indirect"],
            row["peak"],
            row["distance"],
        )
        for row in dated_fixture["relations"]
    )
    locations = tuple(
        ProgressedTerminalLocation(terminal_id, *values)
        for terminal_id, values in dated_fixture["terminal_locations"].items()
    )
    receptions = tuple(
        ProgressedMutualReceptionAllocation(
            row["id"],
            row["body"],
            tuple(row["direct"]),
            tuple(row["indirect"]),
            row["harmony"],
        )
        for row in dated_fixture["mutual_receptions"]
    )
    return practical_progressed_horoscope(
        normal,
        aspects,
        locations,
        {
            int(house): sign
            for house, sign in dated_fixture["house_cusp_signs"].items()
        },
        mutual_receptions=receptions,
    )


def test_practical_distribution_reproduces_reconciled_ninth_house(
    normal_fixture: dict,
    dated_fixture: dict,
) -> None:
    practical = _practical_result(normal_fixture, dated_fixture)
    ninth = practical.house(9)

    assert ninth.normal_power == 51.82
    assert ninth.normal_discord == 10.83
    assert ninth.added_power == 81.94
    assert ninth.total_power == 133.76
    # The executable rule gives 37.33 because two printed dated rows contain
    # staged-arithmetic contradictions. The publication reports 37.32.
    assert ninth.total_discord == 37.33
    assert dated_fixture["published_practical"]["9"]["total"] == [
        133.76,
        0.0,
        37.32,
    ]


def test_practical_distribution_preserves_seventh_house_source_deltas(
    normal_fixture: dict,
    dated_fixture: dict,
) -> None:
    practical = _practical_result(normal_fixture, dated_fixture)
    seventh = practical.house(7)

    assert seventh.normal_power == 145.09
    assert seventh.normal_discord == 10.21
    assert seventh.total_power == 643.80
    assert seventh.net_harmony == 69.24
    published = dated_fixture["published_practical"]["7"]["total"]
    assert published == [643.51, 118.25, 49.16]
    assert seventh.total_power - published[0] == pytest.approx(0.29)
    assert seventh.net_harmony - (published[1] - published[2]) == pytest.approx(
        0.15
    )


def test_practical_distribution_is_order_independent_and_complete(
    normal_fixture: dict,
    dated_fixture: dict,
) -> None:
    expected = _practical_result(normal_fixture, dated_fixture)
    reversed_fixture = dict(dated_fixture)
    reversed_fixture["relations"] = list(reversed(dated_fixture["relations"]))
    reversed_fixture["mutual_receptions"] = list(
        reversed(dated_fixture["mutual_receptions"])
    )
    actual = _practical_result(normal_fixture, reversed_fixture)

    assert actual == expected
    assert len(actual.signs) == 12
    assert len(actual.houses) == 12


def test_practical_distribution_rejects_missing_terminal_location(
    normal_fixture: dict,
    dated_fixture: dict,
) -> None:
    broken = dict(dated_fixture)
    broken["terminal_locations"] = dict(dated_fixture["terminal_locations"])
    broken["terminal_locations"].pop("Sun:r")
    with pytest.raises(ValueError, match="missing practical terminal locations"):
        _practical_result(normal_fixture, broken)


@pytest.mark.parametrize("bad", [-1.0, math.inf, -math.inf, math.nan])
def test_numeric_inputs_reject_negative_or_non_finite_values(bad: float) -> None:
    with pytest.raises(ValueError):
        progressed_aspect_at_distance(1.0, bad)
    with pytest.raises(ValueError):
        progressed_aspect_peak_power(1.0, bad, 0.5, "major")
    with pytest.raises(ValueError):
        progressed_total_influence(1.0, 0.0, 0.0, bad, "day")


def test_type_and_enum_failures_are_explicit() -> None:
    with pytest.raises(TypeError, match="real number"):
        progressed_carry(True, 0.0, 0.0, 0.0, "major")
    with pytest.raises(ValueError, match="unsupported progressed tier"):
        progressed_carry(1.0, 0.0, 0.0, 0.0, "tertiary")
    with pytest.raises(ValueError, match="unsupported house class"):
        progressed_aspect_percentage(
            "square", "floating", uses_luminary_column=False
        )
    with pytest.raises(TypeError, match="must be bool"):
        progressed_aspect_percentage(
            "square", "angular", uses_luminary_column=1  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="unsupported influence unit"):
        progressed_total_influence(1.0, 0.0, 0.0, 1.0, "week")
