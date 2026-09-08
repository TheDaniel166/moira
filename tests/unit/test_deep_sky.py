"""Unit coverage for the release-bound deep-sky coordinate-anchor surface."""

from __future__ import annotations

import math

import pytest

import moira
from moira import facade
from moira.constants import J2000
from moira.deep_sky import (
    DeepSkyClass,
    all_deep_sky_at,
    deep_sky_at,
    deep_sky_object,
    find_deep_sky_objects,
    list_deep_sky_objects,
)
from moira.stars import star_at


EXPECTED_CLASS_COUNTS = {
    DeepSkyClass.GALAXY: 15,
    DeepSkyClass.NEBULA: 15,
    DeepSkyClass.STAR_CLUSTER: 15,
    DeepSkyClass.COMPACT_OBJECT: 5,
    DeepSkyClass.STELLAR_REMNANT: 5,
    DeepSkyClass.HOST_STAR: 5,
}


def test_catalog_has_release_bound_sixty_object_scope() -> None:
    assert len(list_deep_sky_objects()) == 60
    assert {
        object_class: len(list_deep_sky_objects(object_class))
        for object_class in DeepSkyClass
    } == EXPECTED_CLASS_COUNTS


def test_deep_sky_surface_is_exported_from_public_package() -> None:
    expected = {
        "DeepSkyClass",
        "DeepSkyObject",
        "DeepSkyPosition",
        "deep_sky_object",
        "deep_sky_at",
        "all_deep_sky_at",
        "list_deep_sky_objects",
        "find_deep_sky_objects",
    }
    assert expected <= set(moira.__all__)
    assert expected <= set(facade.__all__)
    assert all(getattr(moira, name) is getattr(facade, name) for name in expected)
    assert moira.deep_sky_object("M31").canonical_name == "Andromeda Galaxy"


@pytest.mark.parametrize(
    ("query", "canonical_name"),
    [
        ("M31", "Andromeda Galaxy"),
        ("ngc 224", "Andromeda Galaxy"),
        ("M  31", "Andromeda Galaxy"),
        ("Sgr A*", "Sagittarius A*"),
        ("51 Pegasi", "Helvetios"),
        ("alpha centauri c", "Proxima Centauri"),
    ],
)
def test_lookup_accepts_curated_aliases_and_simbad_identity(
    query: str,
    canonical_name: str,
) -> None:
    assert deep_sky_object(query).canonical_name == canonical_name


def test_lookup_rejects_empty_and_unknown_names() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        deep_sky_object("  ")
    with pytest.raises(KeyError, match="not in the released catalog"):
        deep_sky_object("Hale-Bopp")


def test_class_filter_accepts_enum_and_string() -> None:
    enum_names = list_deep_sky_objects(DeepSkyClass.NEBULA)
    string_names = list_deep_sky_objects("nebula")
    assert enum_names == string_names
    assert "Orion Nebula" in enum_names
    assert "Crab Nebula" not in enum_names


def test_invalid_class_filter_lists_admitted_values() -> None:
    with pytest.raises(ValueError, match="object_class must be one of"):
        list_deep_sky_objects("solar_system_body")


def test_find_searches_names_designations_and_aliases() -> None:
    assert find_deep_sky_objects("ngc 224") == ["Andromeda Galaxy"]
    assert find_deep_sky_objects("nebula", DeepSkyClass.STELLAR_REMNANT) == ["Crab Nebula"]
    assert find_deep_sky_objects("m", DeepSkyClass.HOST_STAR) == ["Proxima Centauri"]


def test_andromeda_j2000_anchor_and_projection_are_stable() -> None:
    record = deep_sky_object("Andromeda Galaxy")
    assert record.simbad_main_id == "M  31"
    assert record.ra_deg == pytest.approx(10.684708333333333, abs=1e-12)
    assert record.dec_deg == pytest.approx(41.26875, abs=1e-12)
    assert record.coordinate_bibcode == "2006AJ....131.1163S"

    position = deep_sky_at("M31", J2000)
    assert position.longitude == pytest.approx(27.845269578977963, abs=1e-10)
    assert position.latitude == pytest.approx(33.34860635813377, abs=1e-10)
    assert position.position_semantics == "catalog_center"
    assert position.position_source == "simbad_catalog_anchor"
    assert position.proper_motion_applied is False


def test_static_extended_anchor_precesses_without_admitting_source_pm() -> None:
    record = deep_sky_object("M87")
    assert record.pmra_mas_yr is not None
    assert record.proper_motion_admitted is False
    j2000 = deep_sky_at("M87", J2000)
    future = deep_sky_at("M87", J2000 + 36525.0)
    assert future.proper_motion_applied is False
    assert abs(future.longitude - j2000.longitude) > 0.5


def test_cluster_center_uses_only_explicitly_admitted_proper_motion() -> None:
    record = deep_sky_object("Pleiades")
    assert record.proper_motion_admitted is True
    assert record.pmra_mas_yr == pytest.approx(19.997)
    assert record.pmdec_mas_yr == pytest.approx(-45.548)
    position = deep_sky_at("Pleiades", J2000 + 36525.0)
    assert position.proper_motion_applied is True


@pytest.mark.parametrize(
    ("query", "star_name", "planet_count"),
    [
        ("51 Pegasi", "Helvetios", 1),
        ("55 Cancri", "Copernicus", 5),
        ("Epsilon Eridani", "Ran", 1),
        ("Proxima Cen", "Proxima Centauri", 2),
        ("Beta Pic", "bet Pic", 3),
    ],
)
def test_host_stars_delegate_to_sovereign_star_positions(
    query: str,
    star_name: str,
    planet_count: int,
) -> None:
    jd_tt = J2000 + 9131.25
    record = deep_sky_object(query)
    position = deep_sky_at(query, jd_tt)
    star = star_at(star_name, jd_tt)
    assert record.confirmed_planet_count == planet_count
    assert position.position_source == "sovereign_star_registry"
    assert position.longitude == pytest.approx(star.longitude, abs=1e-12)
    assert position.latitude == pytest.approx(star.latitude, abs=1e-12)


def test_all_positions_are_finite_and_deterministically_ordered() -> None:
    positions = all_deep_sky_at(J2000)
    assert list(positions) == sorted(positions)
    assert len(positions) == 60
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
        deep_sky_at("M31", bad_jd)


def test_solar_system_objects_are_not_misrepresented_as_j2000_anchors() -> None:
    names = set(list_deep_sky_objects())
    assert names.isdisjoint({"Io", "Halley", "Hale-Bopp", "Oumuamua"})
