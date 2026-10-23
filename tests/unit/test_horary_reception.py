"""P2 runtime evidence checked against the independently collated Lilly data."""
from dataclasses import FrozenInstanceError, asdict, replace
from itertools import combinations, permutations
import json
from pathlib import Path

import pytest

from moira.classical_perfection import LILLY_1647_PERFECTION_V1, _moiety
from moira.constants import TRADITIONAL_MOIETY_ORBS
from moira.dignities import calculate_receptions
from moira.dignities_types import PlanetaryReception, ReceptionBasis, ReceptionMode
from moira.horary_reception import (
    LILLY_1647_CONDITION_RECEPTION,
    LillyDignityBasis as Basis,
    LillyDignityEvidence,
    LillyDirectedReception,
    LillyEvidenceState as State,
    LillyMechanism,
    LillyMechanismReceptionPrerequisites,
    LillyMutualReception,
    LillyOrbState,
    LillyPlanetPosition,
    LillyReceptionRequirement,
    LillySnapshotContext,
    adapt_generic_lilly_reception,
    lilly_collection_reception,
    lilly_condition_snapshot,
    lilly_orb_evidence,
    lilly_position_from_longitude,
    lilly_reception_evidence,
    lilly_translation_reception,
)

FIXTURE = Path(__file__).parents[1] / "fixtures/horary/lilly_core_decisions_2026_10_23.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
ROWS = DATA["table_rows"]
CASES = {case["id"]: case for case in DATA["teaching_examples"]}
PLANETS = tuple(DATA["body_scope"])
BASE_NAMES = {Basis.DOMICILE: "house", **{b: b.value for b in Basis if b is not Basis.DOMICILE}}


def context(day=True, epoch="question", jd=None):
    return LillySnapshotContext(epoch, day, jd)


def snapshot(body, sign, degree=None, ctx=None):
    return lilly_condition_snapshot(LillyPlanetPosition(body, sign, degree),
                                    context=context() if ctx is None else ctx)


def photographed_position(position, ctx):
    degree = position.get("degree")
    if degree is not None:
        degree += position.get("minute", 0) / 60
    return snapshot(position["body"], position["sign"], degree, ctx)


def states(evidence):
    return {item.basis: item.state for item in evidence.dignities}


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["sign"])
@pytest.mark.parametrize("day", [True, False], ids=["day", "night"])
@pytest.mark.parametrize("body", PLANETS)
def test_runtime_condition_matches_photographed_cells_on_both_sides_of_boundaries(row, day, body):
    boundaries = {0, 10, 20, *(segment["end_degree"] for segment in row["terms_raw"])}
    degrees = {x for b in boundaries for x in (b - 1 / 3600, b, b + 1 / 3600) if 0 <= x < 30}
    for degree in sorted(degrees):
        result = snapshot(body, row["sign"], degree, context(day))
        # Expected owners come only from the previously photographed fixture.
        owners = {
            Basis.DOMICILE: row["domicile"],
            Basis.EXALTATION: None if row["exaltation"] is None else row["exaltation"]["body"],
            Basis.TRIPLICITY: row["triplicity_day" if day else "triplicity_night"],
            Basis.TERM: next(s["ruler"] for s in row["terms_raw"] if degree < s["end_degree"]),
            Basis.FACE: next(s["ruler"] for s in row["faces_raw"] if degree < s["end_degree"]),
        }
        expected = {basis: State.PRESENT if owner == body else State.ABSENT
                    for basis, owner in owners.items()}
        assert states(result) == expected, (row["sign"], degree, body, day)
        assert result.detriment is (row["detriment"] == body)
        assert result.fall is (row["fall_printed"] == body)
        assert result.peregrine is (State.PRESENT if body not in owners.values() else State.ABSENT)
        for item in result.dignities:
            assert item.source_points == DATA["dignity_policy"]["points"][BASE_NAMES[item.basis]]
            assert not item.missing_inputs


@pytest.mark.parametrize("day", [True, False, None])
def test_sign_only_self_condition_keeps_known_positive_and_negative_facts(day):
    saturn = snapshot("Saturn", "Aries", ctx=context(day))
    assert saturn.fall and saturn.detriment is False
    assert states(saturn)[Basis.TERM] is State.NOT_EVALUABLE
    assert saturn.peregrine is State.NOT_EVALUABLE
    sun = snapshot("Sun", "Cancer", ctx=context(day))
    assert set(states(sun).values()) == {State.ABSENT}
    assert sun.peregrine is State.PRESENT
    aries_sun = snapshot("Sun", "Aries", ctx=context(day))
    assert states(aries_sun)[Basis.EXALTATION] is State.PRESENT
    assert aries_sun.peregrine is State.ABSENT


def test_unknown_sect_and_degree_do_not_erase_known_basis_or_invent_missing_inputs():
    guest = snapshot("Venus", "Aries", ctx=context(None, "didactic_unspecified"))
    result = LillyDirectedReception("Sun", guest)
    assert states(result) == {Basis.DOMICILE: State.ABSENT, Basis.EXALTATION: State.PRESENT,
                              Basis.TRIPLICITY: State.NOT_EVALUABLE,
                              Basis.TERM: State.ABSENT, Basis.FACE: State.NOT_EVALUABLE}
    assert result.state is State.PRESENT
    assert {d.basis: d.missing_inputs for d in result.dignities if d.missing_inputs} == {
        Basis.TRIPLICITY: ("chart_sect",), Basis.FACE: ("degree",),
    }
    water = LillyDirectedReception("Mars", snapshot("Venus", "Cancer", ctx=context(None)))
    assert states(water)[Basis.TRIPLICITY] is State.PRESENT
    assert next(d for d in water.dignities if d.basis is Basis.TRIPLICITY).possible_rulers == ("Mars",)
    assert guest.context.jd_ut is None and guest.position.degree is None


@pytest.mark.parametrize("identifier", ["D05-HOUSE", "D05-TRIPLICITY", "D05-TERM"])
def test_historical_reception_directions_and_partial_inputs(identifier):
    case = CASES[identifier]
    ctx = context(case["given"]["is_day"], "didactic_unspecified")
    snapshots = tuple(photographed_position(p, ctx) for p in case["given"]["positions"])
    network = lilly_reception_evidence(snapshots)
    edges = {(edge.host, edge.guest): edge for edge in network.directed}
    for host, guest, basis in case["expected"]["required_edges"]:
        canonical = Basis.DOMICILE if basis == "house" else Basis(basis)
        assert states(edges[host, guest])[canonical] is State.PRESENT
    assert network.mutual[0].state is State.PRESENT
    assert all(s.context.jd_ut is None for s in snapshots)


@pytest.mark.parametrize("degree,peregrine", [(10, State.PRESENT), (27, State.ABSENT), (28, State.ABSENT)])
def test_saturn_in_fall_and_peregrinity_remain_separate(degree, peregrine):
    result = snapshot("Saturn", "Aries", degree)
    assert result.fall is True
    assert result.peregrine is peregrine


def test_same_and_mixed_reciprocity_are_distinct_positive_witnesses():
    ctx = context(True)
    sun = snapshot("Sun", "Taurus", ctx=ctx)
    moon = snapshot("Moon", "Leo", ctx=ctx)
    mutual = lilly_reception_evidence((sun, moon)).mutual[0]
    assert mutual.state is State.PRESENT
    assert not mutual.same_bases
    assert (Basis.DOMICILE, Basis.EXALTATION) in mutual.mixed_bases
    term_case = CASES["D05-TERM"]
    pair = lilly_reception_evidence(tuple(photographed_position(p, ctx)
                                         for p in term_case["given"]["positions"])).mutual[0]
    assert Basis.TERM in pair.same_bases


def test_one_direction_never_manufactures_the_reverse():
    sun = snapshot("Sun", "Aries", 14, context(False))
    moon = snapshot("Moon", "Leo", 1, context(False))
    pair = lilly_reception_evidence((sun, moon)).mutual[0]
    assert pair.forward.host == "Sun" and pair.forward.guest == "Moon"
    assert pair.forward.state is State.PRESENT
    assert pair.reverse.state is State.ABSENT
    assert pair.state is State.ABSENT


def test_every_supplied_direction_is_retained_in_stable_planet_order():
    inputs = (snapshot("Mars", "Aries", 16), snapshot("Sun", "Leo", 2),
              snapshot("Mercury", "Gemini", 21))
    expected = lilly_reception_evidence(inputs)
    for order in permutations(inputs):
        assert lilly_reception_evidence(order) == expected
    assert len(expected.directed) == 6 and len(expected.mutual) == 3
    assert [s.position.body for s in expected.snapshots] == ["Sun", "Mercury", "Mars"]
    assert len(lilly_reception_evidence((inputs[0],)).directed) == 0
    assert any(edge.state is State.ABSENT for edge in expected.directed)


def test_full_seven_body_matrix_has_no_missing_or_self_edges():
    network = lilly_reception_evidence(tuple(snapshot(p, "Aries", 5) for p in PLANETS))
    assert len(network.directed) == 42 and len(network.mutual) == 21
    assert {(e.host, e.guest) for e in network.directed} == {(a, b) for a in PLANETS for b in PLANETS if a != b}


@pytest.mark.parametrize("other_context", [context(epoch="contact"), context(False), context(jd=1.0)])
def test_snapshot_context_is_never_silently_reused(other_context):
    a = snapshot("Venus", "Aries", 24)
    b = snapshot("Mars", "Gemini", 16, other_context)
    with pytest.raises(ValueError, match="context"):
        lilly_reception_evidence((a, b))
    with pytest.raises(ValueError, match="context"):
        lilly_translation_reception(a, b)
    with pytest.raises(ValueError, match="context"):
        LillyMutualReception(LillyDirectedReception("Venus", b), LillyDirectedReception("Mars", a))


def test_changed_dignity_at_contact_uses_the_contact_position():
    initial = snapshot("Mars", "Gemini", 16)
    contact = snapshot("Mars", "Gemini", 21, context(epoch="contact"))
    assert LillyDirectedReception("Venus", initial).present_bases == (Basis.TERM,)
    assert LillyDirectedReception("Venus", contact).state is State.ABSENT
    assert initial.context != contact.context


def test_p111_translation_proves_the_reception_prerequisite_only():
    case = CASES["D04-TRANSLATION"]
    ctx = context(None, "didactic_unspecified")
    supplied = {p["body"]: photographed_position(p, ctx) for p in case["given"]["positions"]}
    result = lilly_translation_reception(supplied["Mars"], supplied["Mercury"])
    assert result.state is State.PRESENT
    requirement = result.requirements[0]
    assert (requirement.evidence.host, requirement.evidence.guest) == ("Mars", "Mercury")
    assert (requirement.host_role, requirement.guest_role) == ("source_principal", "translator")
    assert Basis.DOMICILE in requirement.qualifying_bases
    assert result.scope == "reception_prerequisites_only"
    assert case["expected"]["full_p126_perfection_established"] is False


@pytest.mark.parametrize("host,degree", [("Sun", 14), ("Venus", 25)])
def test_exaltation_or_face_alone_cannot_qualify_translation(host, degree):
    ctx = context(False)
    result = lilly_translation_reception(snapshot(host, "Leo", 1, ctx),
                                        snapshot("Mercury", "Aries", degree, ctx))
    req = result.requirements[0]
    assert req.evidence.state is State.PRESENT
    assert req.state is result.state is State.ABSENT
    assert set(req.allowed_bases) == {Basis.DOMICILE, Basis.TRIPLICITY, Basis.TERM}
    assert not req.qualifying_bases


@pytest.mark.parametrize("day,expected", [(True, State.PRESENT), (False, State.ABSENT),
                                          (None, State.NOT_EVALUABLE)])
def test_translation_qualification_requires_known_allowed_evidence(day, expected):
    ctx = context(day)
    result = lilly_translation_reception(snapshot("Sun", "Leo", 1, ctx),
                                        snapshot("Mercury", "Aries", 14, ctx))
    assert result.state is expected


def test_collection_has_two_principal_receivers_and_one_collector_guest():
    venus, mercury, saturn = (snapshot("Venus", "Aries", 10), snapshot("Mercury", "Aries", 10),
                               snapshot("Saturn", "Taurus", 10))
    result = lilly_collection_reception(venus, mercury, saturn)
    assert result.state is State.PRESENT
    assert [(r.evidence.host, r.evidence.guest) for r in result.requirements] == [
        ("Venus", "Saturn"), ("Mercury", "Saturn"),
    ]
    assert [r.host_role for r in result.requirements] == ["principal_a", "principal_b"]
    assert all(r.guest_role == "collector" for r in result.requirements)
    assert result.requirements[1].qualifying_bases == (Basis.TERM,)
    assert LillyDirectedReception("Saturn", mercury).state is State.ABSENT


def test_collection_missing_degree_is_unknown_and_a_failed_leg_dominates_unknown():
    unknown_collector = snapshot("Saturn", "Taurus")
    venus = snapshot("Venus", "Aries", 1)
    mercury = snapshot("Mercury", "Aries", 1)
    result = lilly_collection_reception(venus, mercury, unknown_collector)
    assert [r.state for r in result.requirements] == [State.PRESENT, State.NOT_EVALUABLE]
    assert result.state is State.NOT_EVALUABLE
    failed = lilly_collection_reception(snapshot("Sun", "Leo", 1), mercury, unknown_collector)
    assert [r.state for r in failed.requirements] == [State.ABSENT, State.NOT_EVALUABLE]
    assert failed.state is State.ABSENT


def test_collection_requires_both_receivers_at_the_current_degree():
    result = lilly_collection_reception(snapshot("Venus", "Aries", 1),
                                       snapshot("Mercury", "Aries", 1), snapshot("Saturn", "Taurus", 20))
    assert result.requirements[0].state is State.PRESENT
    assert result.requirements[1].state is State.ABSENT
    assert result.state is State.ABSENT


@pytest.mark.parametrize("a,b", list(combinations(PLANETS, 2)))
def test_selected_orbs_match_independent_full_orb_fixture(a, b):
    full = DATA["orb_tables_full_arcminutes"]["p107_second"]
    allowance = (full[a] + full[b]) / 120
    for error, state in ((allowance - 1 / 60, LillyOrbState.INTERIOR),
                         (allowance, LillyOrbState.BOUNDARY),
                         (allowance + 1 / 60, LillyOrbState.EXTERIOR)):
        for sign in (-1, 1):
            result = lilly_orb_evidence(a, b, sign * error, context=context())
            assert result.combined_moiety_deg == allowance
            assert result.full_orb_a_deg == full[a] / 60
            assert result.full_orb_b_deg == full[b] / 60
            assert result.state is state
            assert result.within_orb is (state is LillyOrbState.INTERIOR)


def test_new_orb_profile_and_all_existing_v1_orbs_remain_distinct():
    result = lilly_orb_evidence("Jupiter", "Saturn", 9, context=context())
    assert result.state is LillyOrbState.BOUNDARY and not result.within_orb
    assert result.combined_moiety_deg == 9
    assert _moiety("Jupiter", "Saturn") == 11
    assert dict(TRADITIONAL_MOIETY_ORBS) == {
        body: value / 60 for body, value in DATA["orb_tables_full_arcminutes"]["existing_v1_frozen"].items()
    }
    assert LILLY_1647_PERFECTION_V1.profile_id == "lilly_1647_perfection_v1"
    assert LILLY_1647_CONDITION_RECEPTION.profile_id != LILLY_1647_PERFECTION_V1.profile_id
    # P.107's first-set example does not silently switch this new policy.
    assert lilly_orb_evidence("Venus", "Saturn", 8, context=context()).state is LillyOrbState.BOUNDARY
    assert DATA["runtime_admitted"] is False  # Preserve the historical fixture checkpoint.


def test_generic_adapter_uses_host_planet_as_host_and_receiving_planet_as_guest():
    legacy = calculate_receptions([{"name": "Moon", "degree": 125}, {"name": "Sun", "degree": 35}])
    relation = next(r for r in legacy if r.receiving_planet == "Moon" and r.host_planet == "Sun")
    ctx = context()
    result = adapt_generic_lilly_reception(relation, guest_snapshot=snapshot("Moon", "Leo", 5, ctx),
                                         relation_context=ctx)
    assert (result.host, result.guest) == ("Sun", "Moon")
    assert Basis.DOMICILE in result.present_bases
    relation.host_planet = "Mars"
    assert result.host == "Sun"  # No mutable generic object is retained.


def test_generic_mutual_metadata_does_not_manufacture_reverse_evidence():
    relation = PlanetaryReception("Moon", "Sun", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL,
                                 "Leo", "Aries", ("Leo",))
    ctx = context(False)
    result = adapt_generic_lilly_reception(relation, guest_snapshot=snapshot("Moon", "Leo", 1, ctx),
                                         relation_context=ctx)
    reverse = LillyDirectedReception("Moon", snapshot("Sun", "Aries", 14, ctx))
    assert result.state is State.PRESENT and reverse.state is State.ABSENT
    assert LillyMutualReception(result, reverse).state is State.ABSENT


def test_generic_adapter_rejects_wrong_context_sign_guest_and_unverified_claim():
    relation = PlanetaryReception("Moon", "Sun", ReceptionBasis.DOMICILE, ReceptionMode.UNILATERAL,
                                 "Leo", "Aries", ("Leo",))
    guest = snapshot("Moon", "Leo", 1)
    with pytest.raises(ValueError, match="context"):
        adapt_generic_lilly_reception(relation, guest_snapshot=guest, relation_context=context(epoch="contact"))
    with pytest.raises(ValueError, match="planet/sign"):
        adapt_generic_lilly_reception(relation, guest_snapshot=snapshot("Mars", "Leo", 1),
                                     relation_context=context())
    with pytest.raises(ValueError, match="planet/sign"):
        adapt_generic_lilly_reception(relation, guest_snapshot=snapshot("Moon", "Aries", 1),
                                     relation_context=context())
    relation.basis = ReceptionBasis.EXALTATION
    with pytest.raises(ValueError, match="not established"):
        adapt_generic_lilly_reception(relation, guest_snapshot=guest, relation_context=context())


@pytest.mark.parametrize("longitude,sign,degree", [(0, "Aries", 0), (30, "Taurus", 0),
                                                  (359.5, "Pisces", 29.5), (-1, "Pisces", 29)])
def test_longitude_factory_preserves_periodicity_and_sign_boundaries(longitude, sign, degree):
    for cycle in range(-2, 3):
        result = lilly_position_from_longitude("Mercury", longitude + 360 * cycle)
        assert (result.sign, result.degree) == (sign, degree)


@pytest.mark.parametrize("body", ["NorthNode", "Uranus", "", None])
def test_classical_scope_is_enforced_for_hosts_and_guests(body):
    with pytest.raises(ValueError, match="classical seven"):
        LillyPlanetPosition(body, "Aries", 0)
    with pytest.raises(ValueError, match="classical seven"):
        LillyDirectedReception(body, snapshot("Mercury", "Aries", 0))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_coordinates_epoch_jd_and_orb_error_fail_closed(value):
    for operation in (lambda: LillyPlanetPosition("Sun", "Aries", value),
                      lambda: lilly_position_from_longitude("Sun", value),
                      lambda: context(jd=value),
                      lambda: lilly_orb_evidence("Sun", "Moon", value, context=context())):
        with pytest.raises(ValueError, match="finite"):
            operation()


@pytest.mark.parametrize("degree", [-1, 30, 360])
def test_degree_in_sign_is_not_silently_normalized_to_a_different_sign(degree):
    with pytest.raises(ValueError, match=r"\[0,30\)"):
        LillyPlanetPosition("Sun", "Aries", degree)


def test_invalid_or_inconsistent_public_inputs_are_rejected():
    with pytest.raises(ValueError, match="epoch"):
        context(epoch=" ")
    with pytest.raises(TypeError, match="bool"):
        context(day=1)
    with pytest.raises(TypeError, match="boolean"):
        LillyPlanetPosition("Sun", "Aries", True)
    with pytest.raises(ValueError, match="sign"):
        LillyPlanetPosition("Sun", "not-a-sign")
    with pytest.raises(ValueError, match="distinct"):
        LillyDirectedReception("Sun", snapshot("Sun", "Aries", 0))
    with pytest.raises(ValueError, match="distinct"):
        lilly_reception_evidence((snapshot("Sun", "Aries", 0), snapshot("Sun", "Leo", 0)))
    with pytest.raises(TypeError, match="tuple"):
        lilly_reception_evidence([snapshot("Sun", "Aries", 0)])
    with pytest.raises(TypeError, match="nonempty"):
        lilly_reception_evidence(())
    with pytest.raises(ValueError, match="distinct"):
        lilly_collection_reception(snapshot("Sun", "Leo", 0), snapshot("Sun", "Aries", 1),
                                  snapshot("Saturn", "Aries", 2))
    with pytest.raises(ValueError, match="distinct"):
        lilly_orb_evidence("Sun", "Sun", 1, context=context())
    with pytest.raises(ValueError, match="circular residual"):
        lilly_orb_evidence("Sun", "Moon", 181, context=context())
    with pytest.raises(ValueError, match="one source"):
        LillyMechanismReceptionPrerequisites(LillyMechanism.TRANSLATION, (), snapshot("Moon", "Aries", 1))


def test_typed_outputs_are_immutable_and_serialize_without_losing_unknowns():
    result = snapshot("Saturn", "Aries", ctx=context(None, "didactic_unspecified"))
    with pytest.raises(FrozenInstanceError):
        result.fall = False
    with pytest.raises(FrozenInstanceError):
        result.position.degree = 0
    # Python 3.14 raises TypeError; older supported Python versions raise ValueError.
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(result.policy, orb_table="legacy")
    encoded = json.loads(json.dumps(asdict(result)))
    assert encoded["position"]["degree"] is None and encoded["context"]["jd_ut"] is None
    assert encoded["peregrine"] == "not_evaluable"
    assert encoded["policy"]["orb_table"] == "lilly_1647_p107_second"
    assert encoded["fall"] is True


def test_sign_local_degree_adjacent_to_boundary_does_not_become_the_following_sign():
    # The sign/degree input preserves its supplied sign even when adding a tiny
    # local degree to a large absolute longitude would round to the next sign.
    result = snapshot("Saturn", "Pisces", 29.999999999999996)
    assert result.position.sign == "Pisces"
    assert states(result)[Basis.TERM] is State.PRESENT


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["sign"])
@pytest.mark.parametrize("day", [True, False, None])
def test_partial_membership_and_peregrinity_follow_only_possible_source_owners(row, day):
    possible = {
        Basis.DOMICILE: {row["domicile"]},
        Basis.EXALTATION: set() if row["exaltation"] is None else {row["exaltation"]["body"]},
        Basis.TRIPLICITY: ({row["triplicity_day"], row["triplicity_night"]} if day is None
                          else {row["triplicity_day" if day else "triplicity_night"]}),
        Basis.TERM: {segment["ruler"] for segment in row["terms_raw"]},
        Basis.FACE: {segment["ruler"] for segment in row["faces_raw"]},
    }
    for body in PLANETS:
        expected = {basis: (State.ABSENT if body not in owners else State.PRESENT
                            if len(owners) == 1 else State.NOT_EVALUABLE)
                    for basis, owners in possible.items()}
        result = snapshot(body, row["sign"], ctx=context(day))
        assert states(result) == expected
        expected_peregrine = (State.ABSENT if State.PRESENT in expected.values() else
                             State.NOT_EVALUABLE if State.NOT_EVALUABLE in expected.values()
                             else State.PRESENT)
        assert result.peregrine is expected_peregrine


def test_receipt_constructors_reject_mutable_or_contradictory_evidence():
    with pytest.raises(TypeError, match="immutable"):
        LillyDignityEvidence(Basis.TERM, State.NOT_EVALUABLE, ["Mars", "Venus"], ("degree",), 2)
    with pytest.raises(ValueError, match="source points"):
        LillyDignityEvidence(Basis.TERM, State.PRESENT, ("Venus",), (), 5)
    with pytest.raises(ValueError, match="unknown membership"):
        LillyDignityEvidence(Basis.TERM, State.NOT_EVALUABLE, ("Venus",), ("degree",), 2)
    with pytest.raises(ValueError, match="known membership"):
        LillyDignityEvidence(Basis.TERM, State.PRESENT, ("Venus", "Mars"), (), 2)
    edge = LillyDirectedReception("Venus", snapshot("Mars", "Taurus", 1))
    with pytest.raises(TypeError, match="immutable"):
        LillyReceptionRequirement(edge, "principal", "collector", [Basis.DOMICILE])
    with pytest.raises(ValueError, match="distinct"):
        LillyReceptionRequirement(edge, "principal", "collector", (Basis.DOMICILE, Basis.DOMICILE))
    with pytest.raises(ValueError, match="roles"):
        LillyReceptionRequirement(edge, "", "collector", (Basis.DOMICILE,))
