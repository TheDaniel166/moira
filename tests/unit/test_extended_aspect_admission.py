"""Independent harmonic geometry for the added aspects and retained Quindecile."""

from types import SimpleNamespace

import pytest

from moira.aspects import (
    CANONICAL_ASPECTS,
    AspectDomain,
    AspectFamily,
    AspectMotionState,
    AspectPolicy,
    AspectTier,
    aspect_harmonic_profile,
    aspect_motion_witness,
    aspects_between,
    aspects_from_longitudes,
    aspects_to_point,
    build_aspect_graph,
    find_aspects,
)
from moira.constants import ASPECT_TIERS, DEFAULT_ORBS, Aspect
from moira.synastry import synastry_aspects


# Expected angles come from circle fractions, independently of the registry.
_CASES = [
    ("Tao", 11 * 360 / 24, AspectFamily.UNTION),
    ("Hexadecile", 360 / 16, AspectFamily.HEXADECILE),
    ("Seminovile", 360 / 18, AspectFamily.SEMINOVILE),
    ("Untion", 360 / 24, AspectFamily.UNTION),
    ("Quindecile", 360 / 15, AspectFamily.QUINDECILE),
]


def _cross_chart(name: str, longitude: float) -> SimpleNamespace:
    return SimpleNamespace(
        longitudes=lambda *, include_nodes: {name: longitude},
        speeds=lambda: {},
    )


@pytest.mark.parametrize(("name", "angle", "family"), _CASES)
def test_registry_admits_each_geometry_only_in_extended_tier(name, angle, family):
    definition = getattr(Aspect, name.upper())
    assert definition.name == name
    assert definition.angle == angle
    assert definition.default_orb == 1.0
    assert definition.is_major is False
    assert definition.symbol
    assert DEFAULT_ORBS[angle] == 1.0
    assert name in CANONICAL_ASPECTS
    assert Aspect.EXTENDED_MINOR.count(definition) == 1
    assert Aspect.ALL.count(definition) == 1
    assert definition in ASPECT_TIERS[2]
    assert definition not in ASPECT_TIERS[0]
    assert definition not in ASPECT_TIERS[1]


@pytest.mark.parametrize(("name", "angle", "family"), _CASES)
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("offset", [0.0, 0.75, 1.0, 1.0001])
def test_all_detection_paths_preserve_wraparound_orb_and_family(
    name, angle, family, direction, offset,
):
    first = 355.0
    second = (first + direction * (angle + offset)) % 360
    positions = {"Sun": first, "Moon": second}
    paths = [
        find_aspects(positions, tier=2),
        aspects_between("Sun", first, "Moon", second, tier=2),
        aspects_to_point(second, {"Sun": first}, "Moon", tier=2),
        aspects_from_longitudes(positions, tier=2).aspects,
        synastry_aspects(
            _cross_chart("Sun", first), _cross_chart("Moon", second), tier=2,
        ),
    ]
    for results in paths:
        matches = [aspect for aspect in results if aspect.aspect == name]
        assert len(matches) == (1 if offset <= 1.0 else 0)
        if not matches:
            continue
        aspect = matches[0]
        assert aspect.angle == angle
        assert aspect.separation == pytest.approx(angle + offset, abs=1e-12)
        assert aspect.orb == pytest.approx(offset, abs=1e-12)
        assert aspect.allowed_orb == 1.0
        assert aspect.classification.domain is AspectDomain.ZODIACAL
        assert aspect.classification.tier is AspectTier.EXTENDED_MINOR
        assert aspect.classification.family is family


@pytest.mark.parametrize(("name", "angle", "family"), _CASES)
def test_common_minor_defaults_and_moiety_do_not_admit_extended_aspects(
    name, angle, family,
):
    positions = {"Sun": 0.0, "Moon": angle}
    for results in (
        find_aspects(positions),
        aspects_between("Sun", 0.0, "Moon", angle, tier=0),
        aspects_between("Sun", 0.0, "Moon", angle, tier=1),
        aspects_to_point(angle, {"Sun": 0.0}),
        aspects_from_longitudes(positions).aspects,
        find_aspects(positions, policy=AspectPolicy(tier=2, orb_mode="moiety")),
    ):
        assert all(aspect.aspect != name for aspect in results)


@pytest.mark.parametrize(("name", "angle", "family"), _CASES)
def test_added_aspects_honor_explicit_orb_and_scaling_policies(name, angle, family):
    for arguments, expected_orb in (
        ({"orbs": {angle: 2.0}, "orb_factor": 0.1}, 2.0),
        ({"orb_factor": 2.0}, 2.0),
    ):
        results = aspects_between("Sun", 0.0, "Moon", angle + 1.5, **arguments)
        match = next(aspect for aspect in results if aspect.aspect == name)
        assert match.allowed_orb == expected_orb
        assert match.orb == 1.5
    results = aspects_between(
        "Sun", 0.0, "Moon", angle + 0.75, orbs={angle: 0.5}, orb_factor=2.0,
    )
    assert all(aspect.aspect != name for aspect in results)


@pytest.mark.parametrize(("name", "angle", "family"), _CASES)
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("offset", [-0.5, 0.5])
def test_signed_motion_uses_each_independent_target(name, angle, family, direction, offset):
    witness = aspect_motion_witness(
        "Sun", 355.0, "Moon", (355 + direction * (angle + offset)) % 360, name,
        speed1_deg_per_day=1.0,
        speed2_deg_per_day=2.0,
        reference_frame="geocentric_ecliptic_of_date",
        timescale="TT",
    )
    expected_state = (
        AspectMotionState.APPLYING if direction * offset < 0
        else AspectMotionState.SEPARATING
    )
    assert witness.angle_deg == angle
    assert witness.target_directed_separation_deg == direction * angle
    assert witness.directed_error_deg == direction * offset
    assert witness.orb_deg == 0.5
    assert witness.allowed_orb_deg == 1.0
    assert witness.within_orb is True
    assert witness.state is expected_state


def test_tao_and_untion_share_harmonic_family_and_keep_distinct_graph_names():
    aspects = []
    for name, angle in (("Tao", 165.0), ("Untion", 15.0), ("Quindecile", 24.0)):
        aspects.extend(
            aspect for aspect in aspects_between("Sun", 0.0, name, angle)
            if aspect.aspect == name
        )
    profile = aspect_harmonic_profile(aspects)
    assert profile.chart.counts == {AspectFamily.QUINDECILE: 1, AspectFamily.UNTION: 2}
    graph = build_aspect_graph(aspects)
    sun = next(node for node in graph.nodes if node.name == "Sun")
    # The graph's historical family_counts field counts aspect names; the
    # harmonic profile owns grouping by the actual harmonic-family enum.
    assert sun.family_counts == {"Quindecile": 1, "Tao": 1, "Untion": 1}
