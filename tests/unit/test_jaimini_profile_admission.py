"""Adversarial admission, immutable contracts and curated profile identities."""

from dataclasses import FrozenInstanceError, replace
from concurrent.futures import ThreadPoolExecutor
import importlib
from math import inf, nan

import pytest

from moira._jaimini_profile_inputs import (
    CLASSICAL,
    NINE,
    ArgalaReference,
    CharaProjection,
    JaiminiChart,
)
from moira.argala_assessment import assess_argala
from moira.chara_profiles import evaluate_chara_profile
from moira.jaimini_extended import argala, rasi_drishti_of
from moira.jaimini_profile_policy import ARGALA_IDS, CHARA_IDS, list_jaimini_profiles


@pytest.mark.parametrize(
    "value", [True, False, "1", None, nan, inf, -inf, 10**400, -1, 12, 1.1]
)
def test_strict_signs(value):
    with pytest.raises(ValueError):
        JaiminiChart("signs", {p: 0 for p in CLASSICAL} | {"Sun": value}, 0)
    with pytest.raises(ValueError):
        JaiminiChart("signs", {p: 0 for p in CLASSICAL}, value)


@pytest.mark.parametrize(
    "value", [True, False, "1", None, nan, inf, -inf, 10**400, -1, 360]
)
def test_strict_degrees(value):
    with pytest.raises(ValueError):
        JaiminiChart("sidereal_longitudes", {p: 0 for p in NINE} | {"Sun": value}, 0)
    with pytest.raises(ValueError):
        JaiminiChart("sidereal_longitudes", {p: 0 for p in NINE}, value)


@pytest.mark.parametrize(
    "positions",
    [
        {},
        None,
        [],
        "Sun",
        [("Sun", 1)],
        (("Sun", 1),) * 7,
        {p: 0 for p in CLASSICAL if p != "Mars"},
        {p: 0 for p in NINE if p != "Rahu"},
        {p: 0 for p in CLASSICAL} | {"Pluto": 1},
    ],
)
def test_malformed_position_maps(positions):
    with pytest.raises(ValueError):
        JaiminiChart("signs", positions, 0)


@pytest.mark.parametrize(
    "kind,value",
    [
        ("house", True),
        ("house", 1.0),
        ("house", 0),
        ("house", 13),
        ("planet", "Pluto"),
        ("planet", 1),
        ("lagna", 1),
        ("sign", 0),
        (True, None),
    ],
)
def test_typed_references(kind, value):
    with pytest.raises(ValueError):
        ArgalaReference(kind, value)


@pytest.mark.parametrize(
    "references",
    [
        [],
        None,
        "lagna",
        [ArgalaReference("lagna")] * 2,
        [ArgalaReference("lagna")] * 23,
        [{"kind": "lagna"}],
    ],
)
def test_reference_collection_admission(references):
    with pytest.raises(ValueError):
        assess_argala(
            JaiminiChart("signs", {p: 0 for p in NINE}, 0),
            profile_id=ARGALA_IDS[0],
            references=references,
        )


def test_snapshot_ordering_pool_and_mutation():
    positions = {p: i for i, p in enumerate(NINE)}
    chart = JaiminiChart("signs", positions, 0)
    positions["Sun"] = 10
    assert dict(chart.positions)["Sun"] == 0
    reversed_chart = JaiminiChart("signs", dict(reversed(chart.positions)), 0)
    a = assess_argala(
        chart,
        profile_id=ARGALA_IDS[0],
        references=[ArgalaReference("house", 2), ArgalaReference("lagna")],
    )
    b = assess_argala(
        reversed_chart,
        profile_id=ARGALA_IDS[0],
        references=[ArgalaReference("lagna"), ArgalaReference("house", 2)],
    )
    assert a == b
    with pytest.raises(FrozenInstanceError):
        a.chart.lagna = 5
    with pytest.raises(TypeError):
        a.references[0].pairs[0].causers[0] = "Sun"
    with pytest.raises(ValueError):
        evaluate_chara_profile(chart, profile_id=CHARA_IDS[0])
    seven = JaiminiChart("signs", {p: 0 for p in CLASSICAL}, 0)
    with pytest.raises(ValueError):
        assess_argala(
            seven, profile_id=ARGALA_IDS[0], references=(ArgalaReference("lagna"),)
        )


@pytest.mark.parametrize(
    "bad",
    [
        None,
        True,
        [],
        "unknown",
        ARGALA_IDS[0],
        "moira_kn_rao_existing_v1",
        "bphs_chara_research",
    ],
)
def test_invalid_chara_selectors(bad):
    with pytest.raises(ValueError):
        evaluate_chara_profile(
            JaiminiChart("signs", {p: 0 for p in CLASSICAL}, 0), profile_id=bad
        )


@pytest.mark.parametrize(
    "bad",
    [
        None,
        True,
        [],
        "unknown",
        CHARA_IDS[0],
        "moira_argala_existing_v1",
        "argala_general_strength_research",
    ],
)
def test_invalid_argala_selectors(bad):
    with pytest.raises(ValueError):
        assess_argala(
            JaiminiChart("signs", {p: 0 for p in NINE}, 0),
            profile_id=bad,
            references=(ArgalaReference("lagna"),),
        )


def test_forged_inputs_revalidated():
    chart = JaiminiChart("signs", {p: 0 for p in CLASSICAL}, 0)
    object.__setattr__(chart, "lagna", True)
    with pytest.raises(ValueError):
        evaluate_chara_profile(chart, profile_id=CHARA_IDS[0])
    chart = JaiminiChart("signs", {p: 0 for p in CLASSICAL}, 0)
    projection = CharaProjection(1.0)
    object.__setattr__(projection, "epoch_jd", inf)
    with pytest.raises(ValueError):
        evaluate_chara_profile(chart, profile_id=CHARA_IDS[0], projection=projection)
    with pytest.raises(ValueError):
        evaluate_chara_profile(
            chart, profile_id=CHARA_IDS[0], projection={"epoch_jd": 1}
        )
    with pytest.raises(ValueError):
        CharaProjection(1, "tropical_year")


@pytest.mark.parametrize(
    "lagna,nodes",
    [
        (True, None),
        (0, {"Ketu": True}),
        (0, {"Rahu": True}),
        (0, {"Pluto": 0}),
        (0, {"Rahu": nan}),
        (0, {"Ketu": inf}),
        (0, []),
        (0, {"Rahu": "0"}),
    ],
)
def test_legacy_argala_invalid_inputs_repaired(lagna, nodes):
    with pytest.raises(ValueError):
        argala({p: 0 for p in CLASSICAL}, lagna, nodes)


def test_catalogue_and_public_curation():
    catalogue = list_jaimini_profiles()
    assert len(catalogue.profiles) == 13
    assert {
        p.profile_id for p in catalogue.profiles if p.admission == "admitted_bounded"
    } == set(CHARA_IDS + ARGALA_IDS)
    source_ids = {s.source_id for s in catalogue.sources}
    rule_ids = {r.rule_id for r in catalogue.rules}
    assert all(r.source_id in source_ids for r in catalogue.rules)
    assert all(set(p.rule_ids) <= rule_ids for p in catalogue.profiles)
    for owner in (
        "_jaimini_profile_inputs",
        "jaimini_profile_policy",
        "chara_profiles",
        "argala_assessment",
    ):
        module = importlib.import_module("moira." + owner)
        for name in module.__all__:
            for surface in ("moira", "moira.facade", "moira.vedic"):
                target = importlib.import_module(surface)
                assert name in target.__all__ and getattr(target, name) is getattr(
                    module, name
                )
    root = importlib.import_module("moira")
    assert root.Moira.list_jaimini_profiles(object()) == catalogue


@pytest.mark.parametrize(
    "source,expected",
    [
        (0, {4, 7, 10}),
        (1, {3, 6, 9}),
        (2, {5, 8, 11}),
        (3, {1, 7, 10}),
        (4, {0, 6, 9}),
        (5, {2, 8, 11}),
        (6, {1, 4, 10}),
        (7, {0, 3, 9}),
        (8, {2, 5, 11}),
        (9, {1, 4, 7}),
        (10, {0, 3, 6}),
        (11, {2, 5, 8}),
    ],
)
def test_independent_rasi_aspect_table(source, expected):
    assert rasi_drishti_of(source) == expected


def test_no_io_during_evaluation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("arithmetic attempted resource IO")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("moira._kernel_paths.find_planetary_kernel", forbidden)
    for pid in CHARA_IDS:
        evaluate_chara_profile(
            JaiminiChart("signs", {p: 0 for p in CLASSICAL}, 0), profile_id=pid
        )
    for pid in ARGALA_IDS:
        assess_argala(
            JaiminiChart("signs", {p: 0 for p in NINE}, 0),
            profile_id=pid,
            references=(ArgalaReference("lagna"),),
        )


def test_all_twenty_two_references_bounded_and_distinct():
    refs = (
        (ArgalaReference("lagna"),)
        + tuple(ArgalaReference("house", h) for h in range(1, 13))
        + tuple(ArgalaReference("planet", p) for p in NINE)
    )
    result = assess_argala(
        JaiminiChart(
            "sidereal_longitudes", {p: i * 35.0 + 1 for i, p in enumerate(NINE)}, 0
        ),
        profile_id=ARGALA_IDS[2],
        references=refs,
    )
    assert len(result.references) == 22
    assert sum(len(r.pairs) for r in result.references) == 132
    with pytest.raises(ValueError):
        replace(result, references=result.references[::-1])


@pytest.mark.parametrize("ketu_sign", range(12))
def test_reference_reversal_is_profile_specific_for_every_sign(ketu_sign):
    chart = JaiminiChart(
        "signs",
        {p: (i + ketu_sign) % 12 for i, p in enumerate(NINE)} | {"Ketu": ketu_sign},
        ketu_sign,
    )
    refs = (
        ArgalaReference("lagna"),
        ArgalaReference("house", 1),
        ArgalaReference("planet", "Ketu"),
    )
    bphs = assess_argala(chart, profile_id=ARGALA_IDS[0], references=refs)
    assert [r.direction for r in bphs.references] == [1, 1, -1]
    for pid in ARGALA_IDS[1:]:
        result = assess_argala(chart, profile_id=pid, references=refs)
        assert [r.direction for r in result.references] == [-1, -1, -1]
        assert all(
            r.pairs[0].causer_sign == (ketu_sign - 1) % 12 for r in result.references
        )


def test_reentrant_profile_calls_preserve_inputs_and_results():
    seven = JaiminiChart("signs", {p: i for i, p in enumerate(CLASSICAL)}, 7)
    nine = JaiminiChart(
        "sidereal_longitudes", {p: i * 39.0 for i, p in enumerate(NINE)}, 210.0
    )

    def run(pid):
        if pid in CHARA_IDS:
            return evaluate_chara_profile(
                seven, profile_id=pid, projection=CharaProjection(2451545.0)
            )
        return assess_argala(
            nine, profile_id=pid, references=(ArgalaReference("lagna"),)
        )

    identities = CHARA_IDS + ARGALA_IDS
    expected = {pid: run(pid) for pid in identities}
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(run, identities * 4))
    assert actual == [expected[pid] for pid in identities * 4]
