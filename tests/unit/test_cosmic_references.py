"""Semantic and geometric covenants for the cosmic-reference registry."""

from __future__ import annotations

import math

import pytest

from moira.constants import J2000
from moira.cosmic_references import (
    CosmicReferenceKind,
    all_cosmic_references_at,
    cosmic_reference_at,
    cosmic_reference_definition,
    list_cosmic_references,
)
from moira.deep_sky import deep_sky_at
from moira.galactic import equatorial_to_galactic


EXPECTED_KIND_COUNTS = {
    CosmicReferenceKind.PHYSICAL_OBJECT: 2,
    CosmicReferenceKind.COORDINATE_LANDMARK: 7,
    CosmicReferenceKind.PROXY_REFERENCE: 3,
}


def _angular_separation_deg(
    ra1_deg: float,
    dec1_deg: float,
    ra2_deg: float,
    dec2_deg: float,
) -> float:
    ra1 = math.radians(ra1_deg)
    dec1 = math.radians(dec1_deg)
    ra2 = math.radians(ra2_deg)
    dec2 = math.radians(dec2_deg)
    cosine = (
        math.sin(dec1) * math.sin(dec2)
        + math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def test_registry_has_three_explicit_semantic_classes() -> None:
    assert {
        kind: len(list_cosmic_references(kind))
        for kind in CosmicReferenceKind
    } == EXPECTED_KIND_COUNTS
    assert len(list_cosmic_references()) == 12


def test_every_definition_has_non_null_source_and_semantic_receipts() -> None:
    for name in list_cosmic_references():
        definition = cosmic_reference_definition(name)
        values = (
            definition.reference_id,
            definition.name,
            definition.anchor,
            definition.position_semantics,
            definition.coordinate_authority,
            definition.semantic_authority,
            definition.source_version,
            definition.citation_urls,
            definition.catalog_version,
        )
        assert all(value is not None for value in values)
        assert definition.citation_urls


@pytest.mark.parametrize(
    ("query", "reference_id"),
    [
        ("GC", "galactic_frame_origin"),
        ("Formal Supergalactic Origin", "supergalactic_longitude_origin"),
        ("Sgr A*", "sagittarius_a_star"),
        ("M87", "m87_galaxy"),
        ("Super-Galactic Center", "virgo_m87_astrological_sgc"),
        ("Great Attractor", "great_attractor_norma_proxy"),
        ("ACO 3558", "shapley_a3558_proxy"),
    ],
)
def test_exact_aliases_resolve_without_collapsing_semantics(
    query: str,
    reference_id: str,
) -> None:
    assert cosmic_reference_definition(query).reference_id == reference_id


def test_similarly_named_centers_remain_distinct_astronomical_objects() -> None:
    frame_origin = cosmic_reference_definition("Galactic Center")
    sgr_a = cosmic_reference_definition("Sagittarius A*")
    formal_supergalactic = cosmic_reference_definition(
        "Supergalactic Longitude Origin"
    )
    m87 = cosmic_reference_definition("M87 Galaxy")
    astrological_sgc = cosmic_reference_definition("Astrological SGC")

    assert frame_origin.kind is CosmicReferenceKind.COORDINATE_LANDMARK
    assert sgr_a.kind is CosmicReferenceKind.PHYSICAL_OBJECT
    frame_source_separation = _angular_separation_deg(
        frame_origin.icrs_ra_deg,
        frame_origin.icrs_dec_deg,
        sgr_a.icrs_ra_deg,
        sgr_a.icrs_dec_deg,
    )
    assert 0.07 < frame_source_separation < 0.08
    assert formal_supergalactic.kind is CosmicReferenceKind.COORDINATE_LANDMARK
    assert m87.kind is CosmicReferenceKind.PHYSICAL_OBJECT
    assert astrological_sgc.kind is CosmicReferenceKind.PROXY_REFERENCE
    assert _angular_separation_deg(
        formal_supergalactic.icrs_ra_deg,
        formal_supergalactic.icrs_dec_deg,
        m87.icrs_ra_deg,
        m87.icrs_dec_deg,
    ) > 100.0
    assert astrological_sgc.reference_id != m87.reference_id
    assert astrological_sgc.icrs_ra_deg == m87.icrs_ra_deg
    assert astrological_sgc.icrs_dec_deg == m87.icrs_dec_deg


def test_formal_supergalactic_landmarks_preserve_source_frame_directions() -> None:
    origin = cosmic_reference_definition("Supergalactic Longitude Origin")
    north = cosmic_reference_definition("North Supergalactic Pole")
    south = cosmic_reference_definition("South Supergalactic Pole")

    origin_l, origin_b = equatorial_to_galactic(origin.icrs_ra_deg, origin.icrs_dec_deg)
    north_l, north_b = equatorial_to_galactic(north.icrs_ra_deg, north.icrs_dec_deg)
    south_l, south_b = equatorial_to_galactic(south.icrs_ra_deg, south.icrs_dec_deg)

    assert origin_l == pytest.approx(137.37, abs=2e-5)
    assert origin_b == pytest.approx(0.0, abs=2e-5)
    assert north_l == pytest.approx(47.37, abs=2e-5)
    assert north_b == pytest.approx(6.32, abs=2e-5)
    assert south_l == pytest.approx(227.37, abs=2e-5)
    assert south_b == pytest.approx(-6.32, abs=2e-5)


def test_coordinate_landmark_antipodes_are_geometrically_opposite() -> None:
    pairs = [
        ("Galactic Center Frame Origin", "Galactic Anti-Center"),
        ("North Galactic Pole", "South Galactic Pole"),
        ("North Supergalactic Pole", "South Supergalactic Pole"),
    ]
    for first_name, second_name in pairs:
        first = cosmic_reference_definition(first_name)
        second = cosmic_reference_definition(second_name)
        separation = _angular_separation_deg(
            first.icrs_ra_deg,
            first.icrs_dec_deg,
            second.icrs_ra_deg,
            second.icrs_dec_deg,
        )
        assert separation == pytest.approx(180.0, abs=2e-6)


@pytest.mark.parametrize(
    ("reference_name", "deep_sky_name"),
    [
        ("Sagittarius A*", "Sagittarius A*"),
        ("M87 Galaxy", "M87 Galaxy"),
        ("Virgo/M87 Astrological SGC", "M87 Galaxy"),
    ],
)
def test_physical_and_conventional_anchors_match_deep_sky_truth(
    reference_name: str,
    deep_sky_name: str,
) -> None:
    jd_tt = J2000 + 9500.25
    reference = cosmic_reference_at(reference_name, jd_tt)
    deep_sky = deep_sky_at(deep_sky_name, jd_tt)
    assert reference.longitude == pytest.approx(deep_sky.longitude, abs=1e-12)
    assert reference.latitude == pytest.approx(deep_sky.latitude, abs=1e-12)


def test_proxy_records_name_their_anchor_and_non_point_semantics() -> None:
    great_attractor = cosmic_reference_definition("Great Attractor")
    shapley = cosmic_reference_definition("Shapley Concentration")
    virgo = cosmic_reference_definition("Super-Galactic Center")

    assert great_attractor.anchor == "Norma Cluster (ACO 3627) catalog center"
    assert great_attractor.icrs_ra_deg == pytest.approx(243.59375, abs=1e-12)
    assert great_attractor.icrs_dec_deg == pytest.approx(-60.86861111111111, abs=1e-12)
    assert "not_unique_point_center" in great_attractor.position_semantics
    assert shapley.anchor.startswith("ACO 3558 catalog center")
    assert "not_unique_supercluster_center" in shapley.position_semantics
    assert virgo.name == "Virgo/M87 Astrological SGC"
    assert "not_formal_supergalactic_origin" in virgo.position_semantics


def test_local_group_barycenter_is_not_invented_without_a_mass_model() -> None:
    with pytest.raises(KeyError, match="not in the released registry"):
        cosmic_reference_definition("Local Group barycenter")


def test_all_positions_are_finite_and_deterministically_ordered() -> None:
    positions = all_cosmic_references_at(J2000)
    assert list(positions) == sorted(positions)
    assert len(positions) == 12
    assert all(
        math.isfinite(position.longitude)
        and math.isfinite(position.latitude)
        and 0.0 <= position.longitude < 360.0
        and -90.0 <= position.latitude <= 90.0
        for position in positions.values()
    )


@pytest.mark.parametrize("bad_jd", [math.nan, math.inf, -math.inf, True])
def test_position_rejects_non_finite_or_boolean_jd(bad_jd: float) -> None:
    with pytest.raises(ValueError, match="jd_tt must be finite"):
        cosmic_reference_at("GC", bad_jd)


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        cosmic_reference_definition("  ")
    with pytest.raises(ValueError, match="kind must be one of"):
        list_cosmic_references("center")
