from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
import types
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
        "j1000": (90.32360446070322, -39.37757569328948),
        "j1500": (97.19272108598558, -39.490825300798114),
        "j1900": (102.70854433396688, -39.582258085103554),
        "j2000": (104.07779911495244, -39.60523763643798),
        "j2100": (105.46104473957047, -39.62826706258255),
        "j2500": (110.97900928192942, -39.720896570307346),
        "j3000": (117.89343496021252, -39.837882570037316),
    },
    "Algol": {
        "j1000": (42.25448568839143, 22.316672664226044),
        "j1500": (49.19946039652736, 22.37209322206341),
        "j1900": (54.7783579791782, 22.417168900241563),
        "j2000": (56.16371242149682, 22.42853288122916),
        "j2100": (57.563189959840486, 22.439933048945587),
        "j2500": (63.147402577456376, 22.48587720837214),
        "j3000": (70.14760035486752, 22.544011764736933),
    },
    "Spica": {
        "j1000": (189.91292356422258, -1.983434178589499),
        "j1500": (196.86607486008734, -2.0178343656521114),
        "j1900": (202.45078411978545, -2.046980493763475),
        "j2000": (203.8374892776286, -2.054487268260189),
        "j2100": (205.23827645736424, -2.0620807680437934),
        "j2500": (210.82731512217097, -2.0933081146978925),
        "j3000": (217.83261124230026, -2.1342097753552074),
    },
    "Aldebaran": {
        "j1000": (55.83510042285258, -5.538208227816488),
        "j1500": (62.8012212023749, -5.502958580546604),
        "j1900": (68.39610144669531, -5.474473062595374),
        "j2000": (69.78532088969183, -5.467319969157701),
        "j2100": (71.18861096157622, -5.460156105644142),
        "j2500": (76.7875471943351, -5.43141200581828),
        "j3000": (83.80495856372643, -5.395353053956575),
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

def _load_stars_module():
    root = Path(__file__).resolve().parents[2]
    package = types.ModuleType("moira")
    package.__path__ = [str(root / "moira")]
    sys.modules["moira"] = package

    spec = importlib.util.spec_from_file_location("moira.stars", root / "moira" / "stars.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["moira.stars"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


stars = _load_stars_module()
find_named_stars = stars.find_named_stars
list_named_stars = stars.list_named_stars
load_catalog = stars.load_catalog
star_at = stars.star_at
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
def test_full_catalog_j2000_reference_sweep_has_no_large_outliers() -> None:
    outliers: list[tuple[str, float, float]] = []
    for name, row in _registry_by_name().items():
        star = star_at(name, J2000)
        lon_err = _angular_delta(star.longitude, float(row["ecl_lon_deg"]))
        lat_err = abs(star.latitude - float(row["ecl_lat_deg"]))
        if max(lon_err, lat_err) > 1.0:
            outliers.append((name, lon_err, lat_err))

    assert outliers == []
