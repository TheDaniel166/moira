"""Bounded Chara contracts and edition-owned D60 sign/name admission.

Source authority: Santhanam BPHS I, printed p.83 (PDF p.82), ch.6.33-41.
The Capricorn example is published; other sign fixtures are derivations of
its stated integer-remainder/count rule, not independent published charts.
Chara co-lord fixtures witness Moira's retained convention, not source proof.
"""
from dataclasses import FrozenInstanceError, asdict, replace
import importlib
from math import nextafter

import pytest

from moira import Moira
from moira.jaimini_extended import CharaDashaComputation, CharaDashaResult, chara_dasha
from moira.varga import (
    D60Method, D60SignResult, SHASHTIAMSHA_DEITIES, calculate_varga, d60_sign,
    shashtiamsha, varga_sign_index, vimshopaka_bala,
)

LONS = {"Sun": 130, "Moon": 200, "Mars": 125, "Mercury": 160,
        "Jupiter": 40, "Venus": 310, "Saturn": 190}
SOURCE = D60Method.SANTHANAM_SIGN


@pytest.mark.parametrize("cycles", [True, False, 0, -1, 3, 1.0, "2", None])
def test_chara_cycles_are_bounded_strict_integers(cycles):
    with pytest.raises(ValueError, match="cycles"):
        chara_dasha(LONS, 5, 2451545, cycles=cycles)


@pytest.mark.parametrize("field", ["Sun", "lagna", "epoch", "Rahu"])
@pytest.mark.parametrize("bad", [True, "12", float("nan"), float("inf"), 10**400])
def test_chara_numbers_fail_before_intervals(field, bad):
    lons, lagna, epoch, nodes = dict(LONS), 5, 2451545, {"Rahu": 45, "Ketu": 225}
    if field == "Sun":
        lons[field] = bad
    elif field == "lagna":
        lagna = bad
    elif field == "epoch":
        epoch = bad
    else:
        nodes[field] = bad
    with pytest.raises(ValueError):
        chara_dasha(lons, lagna, epoch, nodes)


@pytest.mark.parametrize("lons", [None, {}, {"Sun": 10}, LONS | {"Rahu": 10}, list(LONS)])
def test_chara_requires_exact_classical_map(lons):
    with pytest.raises(ValueError, match="sidereal_longitudes"):
        chara_dasha(lons, 5, 2451545)


@pytest.mark.parametrize("nodes", [{}, {"Rahu": 20}, {"Ketu": 200}, {"Rahu": 20, "Ketu": 200, "Sun": 1}])
def test_chara_supplied_nodes_require_exact_pair(nodes):
    with pytest.raises(ValueError, match="node_longitudes"):
        chara_dasha(LONS, 5, 2451545, nodes)


@pytest.mark.parametrize("lagna,direction", [(5, 1), (35, -1)])
@pytest.mark.parametrize("nodes,mode", [(None, "classical_seven"), ({"Rahu": 45, "Ketu": 225}, "moira_existing_co_lords")])
def test_chara_receipt_and_repeated_cycle_intervals(lagna, direction, nodes, mode):
    first = chara_dasha(LONS, lagna, 2451545, nodes)
    both = chara_dasha(LONS, lagna, 2451545, nodes, cycles=2)
    assert first.period_count == 12 and both.period_count == 24
    assert both.direction == direction
    assert first.periods == both.periods[:12]
    assert asdict(both.computation) == {
        "cycle_count": 2, "lord_mode": mode, "formulation_id": "moira_kn_rao_existing_v1",
        "cycle_policy": "repeat_first_cycle", "year_basis": "julian_365.25",
        "year_days": 365.25, "epoch_basis": "caller_supplied_julian_day",
    }
    for a, b in zip(first.periods, both.periods[12:]):
        assert (a.sign, a.years, a.lord) == (b.sign, b.years, b.lord)
    for i, period in enumerate(both.periods):
        assert period.sign == (int(lagna // 30) + direction * i) % 12
        assert period.end_jd - period.start_jd == period.years * 365.25
        assert period.antardasha_signs[-1] == period.sign
        endpoints = period.antardasha_starts + (period.end_jd,)
        assert all(a < b for a, b in zip(endpoints, endpoints[1:]))
    assert all(a.end_jd == b.start_jd for a, b in zip(both.periods, both.periods[1:]))
    with pytest.raises(FrozenInstanceError):
        both.computation.cycle_count = 3


def test_chara_legacy_constructor_keeps_metadata_unknown():
    current = chara_dasha(LONS, 5, 2451545)
    legacy = CharaDashaResult(current.lagna_sign, current.direction, current.birth_jd, current.periods, current.lineage)
    assert legacy.computation is None and legacy.period_count == 12
    with pytest.raises(ValueError, match="period_count"):
        replace(current, computation=CharaDashaComputation(2, "classical_seven"))
    with pytest.raises(ValueError, match="ordered"):
        chara_dasha(LONS, 5, 1e308)


@pytest.mark.parametrize("mars,ketu,lord,years", [
    (225, 225, "Mars+Ketu", 12), (225, 15, "Ketu", 5), (125, 225, "Mars", 9),
    (135, 15, "Mars", 9), (15, 135, "Ketu", 9),  # companions
    (245, 315, "Mars", 1), (315, 5, "Mars", 3), (5, 245, "Ketu", 1),  # modality
    (5, 105, "Ketu", 8), (15, 105, "Mars", 5), (5, 95, "Mars", 5),  # degree, exact tie
])
def test_retained_chara_scorpio_co_lord_branch_witnesses(mars, ketu, lord, years):
    lons = dict.fromkeys(LONS, 130) | {"Mars": mars}
    result = chara_dasha(lons, 5, 2451545, {"Rahu": 45, "Ketu": ketu})
    period = next(p for p in result.periods if p.sign == 7)
    assert (period.lord, period.years) == (lord, years)


def test_published_chara_duration_witness_does_not_claim_chart_reconstruction():
    # Rao's Chandrasekhar article reports Aries 2y and Taurus 12y again in
    # cycle two. These synthetic longitudes isolate those durations only.
    result = chara_dasha(LONS | {"Mars": 75, "Venus": 35}, 5, 2451545, cycles=2)
    assert [p.years for p in result.periods[:2]] == [2, 12]
    assert [p.years for p in result.periods[12:14]] == [2, 12]


@pytest.mark.parametrize("saturn,rahu,lord,years", [
    (305, 305, "Saturn+Rahu", 12), (305, 15, "Rahu", 10), (125, 305, "Saturn", 6),
    (135, 15, "Saturn", 6), (15, 135, "Rahu", 6),
    (245, 45, "Saturn", 2), (45, 5, "Saturn", 9), (5, 245, "Rahu", 2),
    (5, 105, "Rahu", 7), (15, 105, "Saturn", 10), (5, 95, "Saturn", 10),
])
def test_retained_chara_aquarius_co_lord_branch_witnesses(saturn, rahu, lord, years):
    lons = dict.fromkeys(LONS, 130) | {"Saturn": saturn}
    result = chara_dasha(lons, 5, 2451545, {"Rahu": rahu, "Ketu": 45})
    period = next(p for p in result.periods if p.sign == 10)
    assert (period.lord, period.years) == (lord, years)


def test_santhanam_published_example_is_a_sign_only_object():
    result = d60_sign(283 + 25 / 60, method=SOURCE)
    assert isinstance(result, D60SignResult)
    assert (result.sign_index, result.sign, result.position_scope) == (11, "Pisces", "sign_only")
    assert d60_sign(283 + 25 / 60).sign == "Gemini"
    assert not hasattr(result, "sign_degree") and not hasattr(result, "varga_longitude")
    assert "printed83" in result.source_reference
    with pytest.raises(FrozenInstanceError):
        result.method = D60Method.HARMONIC


@pytest.mark.parametrize("natal_sign", range(12))
def test_source_count_rule_is_forward_for_both_parities(natal_sign):
    # Inclusive (remainder+1) count from natal sign implies these offsets.
    for offset, expected_offset in [(0, 0), (0.5, 1), (13 + 25 / 60, 2), (29.75, 11)]:
        assert d60_sign(natal_sign * 30 + offset, method=SOURCE).sign_index == (natal_sign + expected_offset) % 12


def test_d60_half_degree_sign_boundary_and_circular_limits():
    assert d60_sign(nextafter(0.5, 0), method=SOURCE).sign_index == 0
    assert d60_sign(0.5, method=SOURCE).sign_index == 1
    assert d60_sign(nextafter(30, 0), method=SOURCE).sign_index == 11
    assert d60_sign(30, method=SOURCE).sign_index == 1
    assert d60_sign(360, method=SOURCE) == d60_sign(0, method=SOURCE)
    assert d60_sign(-0.25, method=SOURCE).sign_index == 10
    assert d60_sign(-1e-300, method=SOURCE).sign_index == 10


@pytest.mark.parametrize("ordinal,odd_lon,even_lon,name", [
    (6, 2.75, 57.25, "Kinnara"), (37, 18.25, 41.75, "Sudha"),
    (52, 25.75, 34.25, "Dandayudha"), (59, 29.25, 30.75, "Bhramana"),
])
def test_corrected_deity_names_use_printed_ordinal_in_both_parities(ordinal, odd_lon, even_lon, name):
    assert SHASHTIAMSHA_DEITIES[ordinal - 1] == name
    assert shashtiamsha(odd_lon).deity == name
    assert shashtiamsha(even_lon).deity == name


def test_deity_half_degree_boundaries_and_generic_null():
    assert len(SHASHTIAMSHA_DEITIES) == 60
    assert SHASHTIAMSHA_DEITIES.count("Ghora") == 2  # names are not unique identities
    assert shashtiamsha(nextafter(2.5, 0)).deity == "Yaksh"
    assert shashtiamsha(2.5).deity == "Kinnara"
    assert shashtiamsha(nextafter(57.5, 0)).deity == "Kinnara"
    assert shashtiamsha(57.5).deity == "Yaksh"
    point = calculate_varga(283 + 25 / 60, 60)
    assert point.deity is None and point.d60_method is D60Method.HARMONIC
    assert replace(point, d60_method=None).d60_method is None  # legacy/manual unknown
    with pytest.raises(ValueError, match="sign-only"):
        replace(point, d60_method=SOURCE)
    with pytest.raises(ValueError, match="division 60"):
        replace(point, varga_number=9)


@pytest.mark.parametrize("bad", [True, "12", float("nan"), float("inf"), 10**400])
def test_sign_only_input_is_strict_finite(bad):
    with pytest.raises(ValueError):
        d60_sign(bad, method=SOURCE)


def test_source_method_cannot_claim_full_point_or_unrelated_division():
    with pytest.raises(TypeError):
        d60_sign(10, method="bphs_santhanam_sign")
    with pytest.raises(ValueError, match="sign-only"):
        shashtiamsha(10, d60_method=SOURCE)
    with pytest.raises(ValueError):
        varga_sign_index(10, 9, d60_method=SOURCE)
    assert varga_sign_index(283 + 25 / 60, 60, d60_method=SOURCE) == 11
    engine = Moira.__new__(Moira)  # pure facade delegation needs no reader
    engine._reader_obj = None
    assert engine.d60_sign(283 + 25 / 60, method=SOURCE).sign == "Pisces"
    for operation in [
        lambda: engine.varga_named(10, "shashtiamsha", d60_method=SOURCE),
        lambda: engine.shodashvarga(10, d60_method=SOURCE),
        lambda: engine.varga_for_chart(None, "Sun", "shashtiamsha", d60_method=SOURCE),
        lambda: engine.shodashvarga_for_chart(None, "Sun", d60_method=SOURCE),
    ]:
        with pytest.raises(ValueError, match="sign-only"):
            operation()


@pytest.mark.parametrize("group,weight", [("dashavarga", 5.0), ("shodashavarga", 4.0)])
def test_source_sign_changes_only_d60_strength_contribution(group, weight):
    # Venus Capricorn 13d25m: Gemini/Mercury -> Pisces/Jupiter. D1 Mercury
    # Aquarius is a temporary friend, Jupiter Cancer a temporary enemy.
    # Venus naturally befriends Mercury and is neutral toward Jupiter:
    # adhi_mitra=18 vs shatru=7. Source/default delta is (7-18)*weight/20.
    lons = LONS | {"Venus": 283 + 25 / 60, "Mercury": 315, "Jupiter": 105}
    old = vimshopaka_bala("Venus", lons, group)
    new = vimshopaka_bala("Venus", lons, group, d60_method=SOURCE)
    assert old.entries[:-1] == new.entries[:-1]
    a, b = old.entries[-1], new.entries[-1]
    assert (a.division, a.varga_sign_index, a.lord, a.dignity, a.vishva, a.weight) == (60, 2, "Mercury", "adhi_mitra", 18.0, weight)
    assert (b.division, b.varga_sign_index, b.lord, b.dignity, b.vishva, b.weight) == (60, 11, "Jupiter", "shatru", 7.0, weight)
    assert a.points == weight * 18 / 20 and b.points == weight * 7 / 20
    assert new.total - old.total == pytest.approx(-11 * weight / 20, abs=1e-12)
    assert new.total == pytest.approx(sum(e.points for e in old.entries[:-1]) + weight * 7 / 20, abs=1e-12)
    assert old.d60_method is D60Method.HARMONIC and new.d60_method is SOURCE


def test_non_d60_strength_groups_report_no_applied_method():
    assert vimshopaka_bala("Sun", LONS, "shadvarga").d60_method is None
    with pytest.raises(ValueError, match="containing D60"):
        vimshopaka_bala("Sun", LONS, "shadvarga", d60_method=SOURCE)


def test_new_public_objects_have_one_canonical_identity():
    for module_name in ("moira", "moira.facade", "moira.vedic"):
        module = importlib.import_module(module_name)
        for value in (CharaDashaComputation, D60Method, D60SignResult, d60_sign):
            assert getattr(module, value.__name__) is value
            assert value.__name__ in module.__all__
