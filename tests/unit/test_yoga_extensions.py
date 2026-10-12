"""Source fixtures, independent sign geometry and finite-profile invariants."""

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from importlib import import_module
import json
import math
from pathlib import Path
import random

import pytest

from moira import Moira
from moira.yoga_extension_policy import list_yoga_extension_rules, YogaExtensionPolicy
from moira.yoga_extensions import evaluate_yoga_extensions

FIXTURE = json.loads(
    (
        Path(__file__).parents[1] / "fixtures/yoga_extensions/source_cases.json"
    ).read_text()
)
CASES = FIXTURE["cases"]
PROFILES = tuple(p.profile_id for p in list_yoga_extension_rules().profiles)
BASE = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mars": 20.0,
    "Mercury": 160.0,
    "Jupiter": 245.0,
    "Venus": 185.0,
    "Saturn": 280.0,
}


def evaluate(lons=BASE, lagna=5.0, profiles=PROFILES):
    return evaluate_yoga_extensions(lons, lagna, profile_ids=profiles)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_independent_source_case(case):
    r = evaluate(case["longitudes"], case["lagna"], (case["profile_id"],))
    y = next(y for y in r.results if y.rule.rule_id == case["rule_id"])
    assert y.formation_state == case["expected"]
    assert y.qualifications and all(
        q.assessment == "not_evaluated" for q in y.qualifications
    )
    assert y.cancellation_assessment == "not_specified_by_selected_passage"


def test_published_chart_122_signs_are_independent_of_adapter_degrees():
    src = FIXTURE["published_chart122"]
    r = evaluate(
        {p: v for p, v in src["representative_longitudes"].items() if p != "Lagna"},
        271.0,
    )
    assert {p.planet: p.d1_sign_index for p in r.positions} == {
        p: v for p, v in src["d1_signs"].items() if p != "Lagna"
    }
    assert {p.planet: p.d9_sign_index for p in r.positions} == {
        p: v for p, v in src["d9_signs"].items() if p != "Lagna"
    }
    assert r.results[1].formation_state == "formed"
    assert {c.planet for c in r.results[1].branches[0].clauses} == {"Sun", "Mars"}


@pytest.mark.parametrize("sign", range(12))
def test_d9_midpoints_against_classical_modality_sequence(sign):
    start = (sign + (0, 8, 4)[sign % 3]) % 12
    for pada in range(9):
        lon = float(
            Fraction(30 * sign) + Fraction(10, 3) * (Fraction(pada) + Fraction(1, 2))
        )
        r = evaluate(BASE | {"Mercury": lon}, profiles=(PROFILES[0],))
        pos = next(p for p in r.positions if p.planet == "Mercury")
        assert pos.d9_sign_index == (start + pada) % 12


@pytest.mark.parametrize("partition", range(108))
def test_d9_exact_rational_boundaries_and_neighbors(partition):
    edge = float(Fraction(10 * partition, 3))
    for lon in (math.nextafter(edge, -math.inf), edge, math.nextafter(edge, math.inf)):
        if not 0 <= lon < 360:
            continue
        expected = int(Fraction.from_float(lon) * Fraction(3, 10)) % 12
        r = evaluate(BASE | {"Mercury": lon}, profiles=(PROFILES[0],))
        assert (
            next(p for p in r.positions if p.planet == "Mercury").d9_sign_index
            == expected
        )


# Independent verse/ascendant table from printed BPHS 402-404; does not import
# engine rule tables. All named occupants are tested, one failing at a time.
H5 = [
    (2, 2, "Venus", ("Mars",)),
    (9, 2, "Venus", ("Mars",)),
    (1, 3, "Mercury", ("Moon", "Mars", "Jupiter")),
    (10, 3, "Mercury", ("Moon", "Mars", "Jupiter")),
    (0, 4, "Sun", ("Saturn", "Moon", "Jupiter")),
    (5, 5, "Saturn", ("Sun", "Moon")),
    (6, 5, "Saturn", ("Sun", "Moon")),
    (4, 6, "Jupiter", ("Mercury",)),
    (7, 6, "Jupiter", ("Mercury",)),
    (3, 7, "Mars", ("Venus",)),
    (8, 7, "Mars", ("Venus",)),
    (11, 8, "Moon", ("Saturn",)),
]


@pytest.mark.parametrize("lagna,verse,resident,others", H5)
def test_wealth_covers_twelve_lagnas_and_every_required_member(
    lagna, verse, resident, others
):
    lons = (
        BASE
        | {resident: ((lagna + 4) % 12) * 30 + 5}
        | {p: ((lagna + 10) % 12) * 30 + 5 for p in others}
    )

    def state(values):
        return next(
            r
            for r in evaluate(values, lagna * 30 + 5, (PROFILES[2],)).results
            if r.rule.rule_id == f"bphs.41.{verse}"
        ).formation_state

    assert state(lons) == "formed"
    for p in others:
        assert state(lons | {p: (lons[p] + 30) % 360}) == "not_formed"


H1 = [
    (9, "Sun", 4, ("Mars", "Jupiter")),
    (10, "Moon", 3, ("Mercury", "Jupiter")),
    (11, "Mars", 0, ("Mercury", "Venus", "Saturn")),
    (12, "Mercury", 2, ("Saturn", "Jupiter")),
    (13, "Jupiter", 8, ("Mercury", "Mars")),
    (14, "Venus", 1, ("Saturn", "Mercury")),
    (15, "Saturn", 9, ("Mars", "Jupiter")),
]
DISTANCES = {
    "Sun": {7},
    "Moon": {7},
    "Mars": {4, 7, 8},
    "Mercury": {7},
    "Jupiter": {5, 7, 9},
    "Venus": {7},
    "Saturn": {3, 7, 10},
}


@pytest.mark.parametrize("verse,resident,sign,supporters", H1)
def test_each_supporter_direction_and_mixed_conjunction_aspect(
    verse, resident, sign, supporters
):
    base = BASE | {p: sign * 30 + 5 for p in (resident, *supporters)}
    for supporter in supporters:
        for source in range(12):
            got = next(
                r
                for r in evaluate(
                    base | {supporter: source * 30 + 5}, sign * 30 + 5, (PROFILES[2],)
                ).results
                if r.rule.rule_id == f"bphs.41.{verse}"
            )
            expected = (
                source == sign or (sign - source) % 12 + 1 in DISTANCES[supporter]
            )
            assert (got.formation_state == "formed") == expected


def test_profiles_do_not_collapse_and_empty_candidates_do_not_pass():
    jp = next(c for c in CASES if c["case_id"] == "jp_movable_lagna_positive")
    r = evaluate(jp["longitudes"], jp["lagna"])
    assert [y.formation_state for y in r.results[:2]] == ["formed", "not_formed"]
    r = evaluate(
        {
            p: v
            for p, v in FIXTURE["published_chart122"][
                "representative_longitudes"
            ].items()
            if p != "Lagna"
        },
        305.0,
    )
    assert [y.formation_state for y in r.results[:2]] == ["not_formed", "formed"]
    r = evaluate(BASE)
    assert [y.formation_state for y in r.results[:2]] == [
        "not_applicable",
        "not_applicable",
    ]


def test_role_aliases_are_preserved_without_self_conjunction():
    # Libra: Saturn owns both H4/H5; Venus L1 and Moon L10. Three bodies
    # can meet the four roles of 39.36, but Saturn cannot conjoin itself.
    r = evaluate(
        BASE | {"Saturn": 65.0, "Venus": 65.0, "Moon": 65.0}, 185.0, (PROFILES[3],)
    )
    y36 = next(y for y in r.results if y.rule.rule_id == "bphs.39.36")
    assert y36.formation_state == "formed" and len(y36.branches[0].clauses) == 4
    y37 = next(y for y in r.results if y.rule.rule_id == "bphs.39.37")
    assert (
        next(b for b in y37.branches if b.branch_id == "L4_L5").state == "not_satisfied"
    )


def test_deferred_39_35_has_no_all_to_all_full_aspect_witness():
    for distances in DISTANCES.values():
        for source in range(12):
            assert not (
                (3 - source) % 12 + 1 in distances
                and (9 - source) % 12 + 1 in distances
            )
    cat = list_yoga_extension_rules()
    assert (
        len(cat.rules) == 22 and sum(r.admission == "admitted" for r in cat.rules) == 21
    )
    assert (
        cat.rules[-1].rule_id == "bphs.39.35"
        and cat.rules[-1].admission == "research_required"
    )
    assert all(y.rule.rule_id != "bphs.39.35" for y in evaluate().results)


def test_curated_identity_facade_subset_order_and_purity():
    for owner_name in ("moira.yoga_extensions", "moira.yoga_extension_policy"):
        owner = import_module(owner_name)
        for name in owner.__all__:
            for path in ("moira", "moira.facade", "moira.vedic"):
                target = import_module(path)
                assert name in target.__all__ and getattr(target, name) is getattr(
                    owner, name
                )
    before = BASE.copy()
    all_result = evaluate()
    assert (
        Moira.yoga_extensions_from_longitudes(object(), BASE, 5.0, profile_ids=PROFILES)
        == all_result
    )
    assert evaluate(profiles=tuple(reversed(PROFILES))) == all_result
    for profile in PROFILES:
        assert evaluate(profiles=(profile,)).results == tuple(
            y for y in all_result.results if y.rule.profile_id == profile
        )
    assert BASE == before
    assert (
        all_result.evaluated_count
        == all_result.formed_count
        + all_result.not_formed_count
        + all_result.not_applicable_count
        == 21
    )
    with pytest.raises(FrozenInstanceError):
        all_result.positions = ()


def test_constructor_guards_and_derived_states():
    r = evaluate()
    with pytest.raises(ValueError):
        replace(r, results=r.results[:-1])
    with pytest.raises(ValueError):
        replace(r, positions=list(r.positions))
    clause = r.results[2].branches[0].clauses[0]
    with pytest.raises(ValueError):
        replace(clause, state="forged")
    with pytest.raises(ValueError):
        replace(clause, sign_index=True)
    with pytest.raises(ValueError):
        replace(r.results[2], rule=list_yoga_extension_rules().rules[-1])
    with pytest.raises(ValueError):
        replace(r.results[2].branches[0], clauses=())
    with pytest.raises(ValueError):
        replace(r, lagna_sign_index=1)
    assert YogaExtensionPolicy(list(PROFILES)).profile_ids == PROFILES


def test_d9_call_budget_and_no_resource_calls(monkeypatch):
    import moira.yoga_extensions as owner

    calls = []
    original = owner.navamsa

    def count(lon):
        calls.append(lon)
        return original(lon)

    monkeypatch.setattr(owner, "navamsa", count)

    def forbidden(*args, **kwargs):
        pytest.fail("longitude evaluation attempted resource access")

    monkeypatch.setattr("moira.spk_reader.get_reader", forbidden)
    monkeypatch.setattr("moira.spk_reader._open_kernel", forbidden)
    monkeypatch.setattr("moira._kernel_paths.find_planetary_kernel", forbidden)
    monkeypatch.setattr("moira.planets.planet_at", forbidden)
    # Each selected D9 body computed once; this product does not need D9 Lagna.
    evaluate()
    assert len(calls) == 7
    calls.clear()
    evaluate(profiles=PROFILES[2:])
    assert calls == []


def test_upper_zodiac_neighbor_and_immutable_context():
    import moira.yoga_extensions as owner

    lon = math.nextafter(360.0, 0.0)
    result = evaluate(BASE | {"Sun": lon}, lon, (PROFILES[0],))
    assert result.lagna_sign_index == 11
    assert result.positions[0].d1_sign_index == result.positions[0].d9_sign_index == 11
    context = owner._Context(BASE, 5.0, True)
    with pytest.raises(TypeError):
        context.d9["Sun"] = 0
    with pytest.raises(FrozenInstanceError):
        context.lagna = 1


@pytest.mark.parametrize(
    "verse,resident,sign,supporters",
    [
        (11, "Mars", 7, ("Mercury", "Venus", "Saturn")),
        (12, "Mercury", 5, ("Saturn", "Jupiter")),
        (13, "Jupiter", 11, ("Mercury", "Mars")),
        (14, "Venus", 6, ("Saturn", "Mercury")),
        (15, "Saturn", 10, ("Mars", "Jupiter")),
    ],
)
def test_wealth_second_own_sign(verse, resident, sign, supporters):
    test_each_supporter_direction_and_mixed_conjunction_aspect(
        verse, resident, sign, supporters
    )


LORDS = (
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
)


@pytest.mark.parametrize("lagna", range(12))
def test_royal_branches_against_independent_sign_oracle(lagna):
    # No engine table/function supplies expectations. Random grids supplement
    # deliberate shared-sign/opposite layouts; each branch is checked separately.
    rng = random.Random(3900 + lagna)
    grids = [{p: rng.randrange(12) for p in BASE} for _ in range(80)]
    grids += [
        {p: (a if i % 2 else b) for i, p in enumerate(BASE)}
        for a in range(12)
        for b in range(12)
    ]
    lord = {h: LORDS[(lagna + h - 1) % 12] for h in (1, 4, 5, 9, 10)}
    for signs in grids:

        def joined(a, b):
            return a != b and signs[a] == signs[b]

        def aspect(a, b):
            return a != b and (signs[b] - signs[a]) % 12 + 1 in DISTANCES[a]

        def house(p):
            return (signs[p] - lagna) % 12 + 1

        expected = {
            "bphs.39.33-34": {
                "mutual_aspect": aspect(lord[5], lord[9]) and aspect(lord[9], lord[5]),
                "conjunction": joined(lord[5], lord[9]),
                "opposition": lord[5] != lord[9]
                and (signs[lord[9]] - signs[lord[5]]) % 12 == 6,
            },
            "bphs.39.36": {
                "all_roles_in_ninth": all(house(lord[h]) == 9 for h in (5, 10, 4, 1))
            },
            "bphs.39.37": {
                f"L{a}_L{b}": joined(lord[a], lord[b]) for a in (4, 10) for b in (5, 9)
            },
            "bphs.39.38": {
                f"L5_L{h}": house(lord[5]) in (1, 4, 10) and joined(lord[5], lord[h])
                for h in (9, 1)
            },
            "bphs.39.39": {
                role: signs["Jupiter"] in (8, 11)
                and house("Jupiter") == 9
                and joined("Jupiter", p)
                for p, role in (("Venus", "Venus"), (lord[5], "L5"))
            },
        }
        result = evaluate(
            {p: s * 30 + 5 for p, s in signs.items()}, lagna * 30 + 5, (PROFILES[3],)
        )
        for row in result.results:
            assert {
                b.branch_id: b.state == "satisfied" for b in row.branches
            } == expected[row.rule.rule_id]
            assert (row.formation_state == "formed") == any(
                expected[row.rule.rule_id].values()
            )


def test_jp_frames_gates_and_self_dispositor():
    # Mercury at 333 is debilitated in D1 and in Cancer D9. Its D9 lord
    # Moon is placed in D1 Aries (H1), although Moon's own D9 is Leo.
    lons = BASE | {"Mercury": 333.0, "Moon": 15.0, "Mars": 4.0}
    row = evaluate(lons, 5.0, (PROFILES[0],)).results[0]
    assert row.formation_state == "formed"
    clause = next(c for c in row.branches[0].clauses if c.clause_id == "lord_house")
    assert clause.planet == "Moon" and clause.frame == "D1" and clause.house == 1
    # Moving Moon out of both kendra/trikona defeats BOTH movable branches.
    row = evaluate(lons | {"Moon": 65.0}, 5.0, (PROFILES[0],)).results[0]
    assert all(b.state == "not_satisfied" for b in row.branches)
    # Fixed Taurus Lagna: D1 Lagna lord Venus, not D9 Lagna's lord.
    # Taurus 35 has Aquarius D9 (Saturn), while Venus 4 has Taurus D9.
    # Saturn 271 is movable in D9, and must not make the Venus gate pass.
    row = evaluate(
        lons | {"Moon": 125.0, "Venus": 4.0, "Saturn": 271.0}, 35.0, (PROFILES[0],)
    ).results[0]
    assert row.formation_state == "not_formed"
    gate = row.branches[1].clauses[-1]
    assert (
        gate.planet == "Venus" and gate.role == "D1_lagna_lord" and gate.sign_index == 1
    )
    # Debilitated Venus in Virgo 164 has Venus-ruled Taurus D9; self-lord
    # PLACEMENT is valid in H1, unlike a self-conjunction relation.
    row = evaluate(
        BASE | {"Venus": 164.0, "Mercury": 181.0}, 155.0, (PROFILES[0],)
    ).results[0]
    assert row.formation_state == "formed"
    identity = next(c for c in row.branches[0].clauses if c.predicate == "navamsa_lord")
    assert identity.planet == identity.related_planet == "Venus"
