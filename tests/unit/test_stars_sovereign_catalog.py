from __future__ import annotations

import csv
import importlib
import json
import math
from pathlib import Path

import pytest


DATA_DIR = Path(__file__).resolve().parents[2] / "moira" / "data"
REGISTRY_PATH = DATA_DIR / "star_registry.csv"
LORE_PATH = DATA_DIR / "star_lore.json"
PROVENANCE_PATH = DATA_DIR / "star_provenance.json"
J2000 = 2451545.0
J1000 = J2000 - 36525.0 * 10
J1500 = J2000 - 36525.0 * 5
J1900 = J2000 - 36525.0
J2100 = J2000 + 36525.0
J2500 = J2000 + 36525.0 * 5
J3000 = J2000 + 36525.0 * 10

EXPECTED_COLUMNS = [
    "name",
    "nomenclature",
    "gaia_dr3_id",
    "ra_deg",
    "dec_deg",
    "pmra_mas_yr",
    "pmdec_mas_yr",
    "parallax_mas",
    "magnitude_v",
    "color_index",
    "ecl_lon_deg",
    "ecl_lat_deg",
    "arc_vis_deg",
    "lat_limit_deg",
]

ORACLE_ANCHORS = {
    "Sirius": {
        "j1000": (90.32324909319895, -39.37754877844545),
        "j1500": (97.19263208055153, -39.490817852676805),
        "j1900": (102.70854076853654, -39.5822577640422),
        "j2000": (104.07779911495244, -39.60523763643798),
        "j2100": (105.46104117154074, -39.628266729915246),
        "j2500": (110.97891995158317, -39.720887671475936),
        "j3000": (117.89307699361329, -39.83784405038369),
    },
    "Algol": {
        "j1000": (42.25448568073526, 22.316672660941258),
        "j1500": (49.19946039461313, 22.372093221241045),
        "j1900": (54.77835797910163, 22.417168900208626),
        "j2000": (56.16371242149682, 22.42853288122916),
        "j2100": (57.56318995976391, 22.43993304891265),
        "j2500": (63.14740257554162, 22.485877207547684),
        "j3000": (70.14760034720712, 22.54401176143551),
    },
    "Spica": {
        "j1000": (189.91292315484398, -1.983434086410985),
        "j1500": (196.86607475777257, -2.017834342465914),
        "j1900": (202.45078411569378, -2.046980492831592),
        "j2000": (203.8374892776286, -2.054487268260189),
        "j2100": (205.23827645327304, -2.062080767109704),
        "j2500": (210.82731501991378, -2.093308091237672),
        "j3000": (217.8326108333824, -2.134209680985559),
    },
    "Aldebaran": {
        "j1000": (55.83509554724193, -5.538208350534762),
        "j1500": (62.80121998379598, -5.502958609581042),
        "j1900": (68.39610139796245, -5.474473063702392),
        "j2000": (69.78532088969183, -5.467319969157701),
        "j2100": (71.18861091284847, -5.460156106723406),
        "j2500": (76.7875459763965, -5.431412031383966),
        "j3000": (83.80495369323836, -5.395353148926334),
    },
}

ORACLE_DATE_POINTS = {
    "j1000": J1000,
    "j1500": J1500,
    "j1900": J1900,
    "j2000": J2000,
    "j2100": J2100,
    "j2500": J2500,
    "j3000": J3000,
}

stars = importlib.import_module("moira.stars")
find_named_stars = stars.find_named_stars
list_named_stars = stars.list_named_stars
load_catalog = stars.load_catalog
star_at = stars.star_at
star_light_time_split = stars.star_light_time_split
stars_by_magnitude = stars.stars_by_magnitude
stars_near = stars.stars_near


def _registry_rows() -> list[dict[str, str]]:
    with REGISTRY_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _registry_by_name() -> dict[str, dict[str, str]]:
    return {row["name"].strip(): row for row in _registry_rows() if row["name"].strip()}


def _load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _angular_delta(a: float, b: float) -> float:
    return abs((((a - b) + 180.0) % 360.0) - 180.0)


@pytest.mark.unit
def test_registry_schema_and_key_alignment() -> None:
    rows = _registry_rows()
    assert rows
    assert list(rows[0].keys()) == EXPECTED_COLUMNS

    names = [row["name"].strip() for row in rows]
    assert len(names) == len(set(names))

    lore = _load_json(LORE_PATH)
    provenance = _load_json(PROVENANCE_PATH)
    assert set(names) == set(lore)
    assert set(names) == set(provenance)


@pytest.mark.unit
def test_registry_numeric_columns_are_parseable_and_finite() -> None:
    numeric_columns = [
        "ra_deg",
        "dec_deg",
        "pmra_mas_yr",
        "pmdec_mas_yr",
        "parallax_mas",
        "magnitude_v",
        "color_index",
        "ecl_lon_deg",
        "ecl_lat_deg",
        "arc_vis_deg",
        "lat_limit_deg",
    ]
    for row in _registry_rows():
        for column in numeric_columns:
            value = float(row[column])
            assert math.isfinite(value), f"{row['name']} has non-finite {column}"


@pytest.mark.unit
def test_public_catalog_matches_registry_count_and_anchors() -> None:
    load_catalog()
    names = list_named_stars()
    registry = _registry_by_name()

    assert len(names) == len(registry)
    assert "Algol" in names
    assert "Sirius" in names
    assert "Spica" in names


@pytest.mark.unit
@pytest.mark.parametrize("name", ["Sirius", "Algol", "Spica", "Aldebaran", "Regulus"])
def test_star_at_matches_registry_reference_longitude_and_latitude(name: str) -> None:
    row = _registry_by_name()[name]
    star = star_at(name, J2000)

    assert star.source == "sovereign"
    assert star.name == name
    assert star.longitude == pytest.approx(float(row["ecl_lon_deg"]), abs=0.01)
    assert star.latitude == pytest.approx(float(row["ecl_lat_deg"]), abs=0.01)
    assert star.magnitude == pytest.approx(float(row["magnitude_v"]), abs=1e-6)


@pytest.mark.unit
@pytest.mark.parametrize("name", ["Sirius", "Algol", "Spica", "Aldebaran"])
@pytest.mark.parametrize("date_key", ["j1000", "j1500", "j1900", "j2000", "j2100", "j2500", "j3000"])
def test_oracle_anchor_reference_positions(name: str, date_key: str) -> None:
    star = star_at(name, ORACLE_DATE_POINTS[date_key])
    expected_lon, expected_lat = ORACLE_ANCHORS[name][date_key]

    assert star.longitude == pytest.approx(expected_lon, abs=1e-9)
    assert star.latitude == pytest.approx(expected_lat, abs=1e-9)


@pytest.mark.unit
@pytest.mark.parametrize("name", ["Sirius", "Algol", "Spica", "Aldebaran"])
def test_oracle_anchor_longitude_progression_across_millennial_span(name: str) -> None:
    samples = [star_at(name, ORACLE_DATE_POINTS[key]) for key in ("j1000", "j1500", "j1900", "j2000", "j2100", "j2500", "j3000")]
    longitudes = [sample.longitude for sample in samples]
    assert longitudes == sorted(longitudes)


@pytest.mark.unit
@pytest.mark.parametrize("name", ["Sirius", "Algol", "Spica", "Aldebaran"])
def test_oracle_anchor_far_past_future_positions_remain_valid(name: str) -> None:
    for date_key in ("j1000", "j3000"):
        star = star_at(name, ORACLE_DATE_POINTS[date_key])
        assert 0.0 <= star.longitude < 360.0
        assert -90.0 <= star.latitude <= 90.0
        assert star.source == "sovereign"


@pytest.mark.unit
def test_star_lookup_is_case_insensitive_but_returns_canonical_name() -> None:
    lower = star_at("algol", J2000)
    upper = star_at("ALGOL", J2000)

    assert lower.name == "Algol"
    assert upper.name == "Algol"
    assert lower.longitude == upper.longitude
    assert lower.nomenclature == "bet Per"


@pytest.mark.unit
def test_bayer_case_collisions_require_exact_casing() -> None:
    upper = star_at("Q Car", J2000)
    lower = star_at("q Car", J2000)

    assert upper.name == "Q Car"
    assert lower.name == "q Car"
    assert upper.longitude != pytest.approx(lower.longitude, abs=1.0)

    with pytest.raises(KeyError):
        star_at("q car", J2000)


@pytest.mark.unit
def test_find_and_search_views_are_catalog_native() -> None:
    assert "Algol" in find_named_stars("alg")

    nearby = stars_near(104.08, J2000, orb=0.2)
    assert nearby
    assert nearby[0].name == "Sirius"

    bright = stars_by_magnitude(1.0, J2000)
    assert bright
    assert bright == sorted(bright, key=lambda star: (star.magnitude, star.name))
    assert any(star.name == "Sirius" for star in bright)


@pytest.mark.unit
def test_fixed_star_results_preserve_unified_merge_condition_profile() -> None:
    star = star_at("Sirius", J2000)

    assert star.condition_profile is not None
    assert star.condition_profile.result_kind == "fixed_star"
    assert star.condition_profile.condition_state.name == "unified_merge"
    assert star.condition_profile.relation_kind == "catalog_merge"
    assert star.condition_profile.relation_basis == "sovereign_registry"
    assert star.condition_profile.source_kind == "sovereign"


@pytest.mark.unit
def test_fixed_star_search_surfaces_preserve_condition_profile() -> None:
    nearby = stars_near(104.08, J2000, orb=0.2)
    bright = stars_by_magnitude(1.0, J2000)

    assert nearby
    assert bright
    assert all(star.condition_profile is not None for star in nearby[:3])
    assert all(star.condition_profile is not None for star in bright[:3])
    assert all(star.condition_profile.condition_state.name == "unified_merge" for star in nearby[:3])
    assert all(star.condition_profile.condition_state.name == "unified_merge" for star in bright[:3])


@pytest.mark.unit
def test_star_light_time_split_preserves_condition_profile_on_both_positions() -> None:
    observed, true = star_light_time_split("Sirius", J2000)

    assert observed.condition_profile is not None
    assert true.condition_profile is not None
    assert observed.condition_profile.condition_state.name == "unified_merge"
    assert true.condition_profile.condition_state.name == "unified_merge"
    assert observed.condition_profile.relation_kind == "catalog_merge"
    assert true.condition_profile.relation_kind == "catalog_merge"


@pytest.mark.unit
def test_fixed_star_exposes_constellation_membership() -> None:
    sirius = star_at("Sirius", J2000)
    betelgeuse = star_at("Betelgeuse", J2000)

    assert sirius.constellation == "Canis Major"
    assert sirius.computation_truth is not None
    assert sirius.computation_truth.constellation == "Canis Major"

    assert betelgeuse.constellation == "Orion"
    assert betelgeuse.computation_truth is not None
    assert betelgeuse.computation_truth.constellation == "Orion"


@pytest.mark.unit
def test_full_catalog_j2000_reference_sweep_has_no_large_outliers() -> None:
    outliers: list[tuple[str, float, float]] = []
    for name, row in _registry_by_name().items():
        star = star_at(name, J2000)
        lon_err = _angular_delta(star.longitude, float(row["ecl_lon_deg"]))
        lat_err = abs(star.latitude - float(row["ecl_lat_deg"]))
        if max(lon_err, lat_err) > 1.0:
            outliers.append((name, lon_err, lat_err))

    assert outliers == []
