"""Cross-consumer witnesses for registry selection and aspect policy forwarding."""

from types import SimpleNamespace

import pytest

from moira import Moira
from moira.aspect_registry import ASPECT_ALIASES, ASPECT_DEFINITIONS, resolve_aspect
from moira.aspects import (
    AspectPolicy, aspect_harmonic_profile, aspect_motion_witness,
    aspect_strength, aspects_between, build_aspect_graph, find_aspects,
)
from moira.constants import HouseSystem
from moira.geodetic import GeodeticLocation
from moira.geodetic_analysis import geodetic_house_chart, geodetic_natal_overlay
from moira.geodetic_inputs import geodetic_snapshot_from_positions
from moira.harmonics import DEFAULT_HARMONIC_REFERENCE_ORB_DEG, HARMONIC_PRESETS, HarmonicsService
from moira.optional_aspects import OPTIONAL_ASPECT_FRACTIONS, OPTIONAL_ASPECT_SETS
from moira.patterns import find_all_patterns
from moira.relationship_forecasting import _selected_aspects
from moira.synastry import synastry_aspects


def _engine():
    engine = Moira.__new__(Moira)
    engine._reader_obj = None
    return engine


@pytest.mark.parametrize("value", [False, 0, 0.0, "", b"", {}, set()])
def test_synastry_facade_rejects_the_same_falsey_invalid_set_selectors(value):
    first = SimpleNamespace(longitudes=lambda **_: {"Sun": 0}, speeds=lambda: {})
    second = SimpleNamespace(longitudes=lambda **_: {"Moon": 9}, speeds=lambda: {})
    with pytest.raises(ValueError):
        synastry_aspects(first, second, optional_sets=value)
    with pytest.raises(ValueError):
        _engine().synastry_aspects(first, second, optional_sets=value)


def test_registered_septile_pattern_is_found_by_automatic_and_facade_consumers():
    # Independent exact-turn geometry: edges 1/7, 2/7, and 3/7 of a turn.
    positions = {"Sun": 0, "Moon": 360 / 7, "Mercury": 1080 / 7}
    supplied = find_aspects(positions, tier=2)
    expected = find_all_patterns(positions, aspects=supplied, include=["Septile Triangle"])
    assert len(expected) == 1
    automatic = find_all_patterns(positions, include=["Septile Triangle"])
    assert [pattern.name for pattern in automatic] == ["Septile Triangle"]
    chart = SimpleNamespace(longitudes=lambda: positions, speeds=lambda: {})
    assert any(pattern.name == "Septile Triangle" for pattern in _engine().patterns(chart))


@pytest.mark.parametrize("definition", ASPECT_DEFINITIONS, ids=lambda definition: definition.name)
def test_entire_catalog_survives_strength_graph_family_and_geodetic_consumers(definition):
    optional = tuple(OPTIONAL_ASPECT_SETS)
    results = aspects_between("Sun", definition.angle, "MC", 0, optional_sets=optional)
    aspect = next(item for item in results if item.aspect == definition.name)
    assert aspect.allowed_orb == definition.default_orb
    assert aspect_strength(aspect).exactness == pytest.approx(1, abs=1e-12)
    graph = build_aspect_graph([aspect])
    assert graph.edges == (aspect,)
    assert aspect_harmonic_profile([aspect]).chart.counts == {aspect.classification.family: 1}
    # Longitude 0 at the equator gives a location-native MC of 0 degrees.
    figure = geodetic_house_chart(GeodeticLocation(0, 0), obliquity=23.44, system=HouseSystem.EQUAL)
    snapshot = geodetic_snapshot_from_positions({"Sun": definition.angle}, source_frame=figure.source_frame)
    policy = AspectPolicy(tier=2, optional_sets=optional)
    overlay = geodetic_natal_overlay(figure, snapshot, aspect_policy=policy, angles=("MC",))
    hit = next(item for item in overlay.contacts if item.aspect == definition.name)
    assert hit.angle == definition.angle and hit.allowed_orb == definition.default_orb
    assert overlay.aspect_policy.optional_sets == optional


@pytest.mark.parametrize(("alias", "canonical"), ASPECT_ALIASES.items())
def test_aliases_and_orbs_match_motion_forecast_and_transport_selection(alias, canonical):
    from moira_server.services.forecasting import _selected_server_aspects

    normalized = alias.swapcase().replace(" ", "_").replace("-", "_")
    definition = resolve_aspect(canonical)
    selected = _selected_aspects(2, [normalized], tuple(OPTIONAL_ASPECT_SETS))
    assert selected == _selected_server_aspects(2, [normalized], tuple(OPTIONAL_ASPECT_SETS)) == (definition,)
    witness = aspect_motion_witness(
        "Sun", 0, "Moon", definition.angle, normalized,
        reference_frame="geocentric_ecliptic_of_date", timescale="TT",
    )
    assert witness.aspect == canonical
    assert witness.allowed_orb_deg == definition.default_orb
    if canonical in OPTIONAL_ASPECT_FRACTIONS:
        with pytest.raises(ValueError, match="unavailable"):
            _selected_aspects(2, [normalized])
    with pytest.raises(ValueError, match="unique"):
        _selected_server_aspects(2, [canonical, normalized], tuple(OPTIONAL_ASPECT_SETS))


def test_all_presets_match_engine_and_optional_orb_policy():
    from moira_server.services.harmonics import _preset_for

    assert len(HARMONIC_PRESETS) == 22
    for harmonic, (name, description) in HARMONIC_PRESETS.items():
        assert HarmonicsService.get_preset_info(harmonic) == (name, description)
        assert _preset_for(harmonic) == (name, None)
        if harmonic > 1:
            assert resolve_aspect(name).angle == pytest.approx(360 / harmonic, abs=1e-12)
    for members in OPTIONAL_ASPECT_SETS.values():
        for member in members:
            assert member.definition.default_orb == DEFAULT_HARMONIC_REFERENCE_ORB_DEG / member.denominator


def test_numeric_natal_transit_facade_and_batch_accept_the_entire_catalog(monkeypatch):
    import moira.batch as batch
    import moira.facade as facade
    from moira._facade_predictive import PredictiveFacadeMixin

    captured = []

    def fake_search(body, specs, start, end, **kwargs):
        captured.append(tuple(specs))
        return []

    monkeypatch.setattr(facade, "find_aspect_transits_to_longitudes", fake_search)
    monkeypatch.setattr(batch, "find_aspect_transits_to_longitudes", fake_search)
    angles = tuple(definition.angle for definition in ASPECT_DEFINITIONS)
    orbs = tuple(definition.default_orb for definition in ASPECT_DEFINITIONS)
    PredictiveFacadeMixin.natal_aspect_transits(
        SimpleNamespace(_reader=object()), "Mars", [0], angles,
        2_460_000, 2_460_001, aspect_orbs=orbs,
    )
    request = batch.EventBatchRequest(
        "natal_aspect_transits", "Mars", 2_460_000, 2_460_001,
        natal_longitudes=(0,), aspect_angles=angles, aspect_orbs=orbs,
    )
    result, = batch.batch_events([request], reader=object())
    assert result.ok
    assert captured == [tuple((0, angle, orb) for angle, orb in zip(angles, orbs))] * 2
