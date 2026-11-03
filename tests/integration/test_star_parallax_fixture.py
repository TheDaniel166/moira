"""Every registry row's parallax candidates re-derive from the frozen primary-catalog fixture.

The fixture was fetched by ``augment_star_registry_astrometry.py fetch-plx`` on 2026-11-03
and re-derived offline with ``derive-plx``. Nothing here needs the network or the
``gaiadr3-zeropoint`` package: the zero-point is stored.

Governing record: docs/architecture/STAR_PARALLAX_SIGNIFICANCE_POLICY_DESIGN.md, Section 4.
"""

from __future__ import annotations

import collections
import csv
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "star_parallax_primary_2026_11_03.json"
REGISTRY = ROOT / "moira" / "data" / "star_registry.csv"


def _ingest():
    path = ROOT / "scripts" / "data_ingestion" / "augment_star_registry_astrometry.py"
    spec = importlib.util.spec_from_file_location("augment_star_registry_astrometry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ingest = _ingest()
CANDIDATE = json.loads(FIXTURE.read_text(encoding="utf-8"))
STARS = CANDIDATE["stars"]
SOURCE_COUNTS = {
    "gaia_hipparcos_combined": 1331,
    "gaia_hipparcos_combined_discordant": 151,
    "hipparcos_2007": 236,
    "gaia_dr3": 51,
    "gaia_dr3_uncalibrated": 13,
    "simbad_fallback": 8,
    "none": 19,
}


def test_fixture_covers_every_registry_row_exactly_once() -> None:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        names = [row["name"] for row in csv.DictReader(handle)]
    assert len(names) == len(set(names))
    assert set(STARS) == set(names)


def test_every_row_reproduces_from_its_frozen_inputs() -> None:
    mismatched = [n for n, e in STARS.items() if ingest.adopt_parallax(e["inputs"]) != e["derived"]]
    assert mismatched == []


def test_adoption_source_counts_are_frozen() -> None:
    counts = collections.Counter(e["derived"]["parallax_source"] for e in STARS.values())
    assert dict(counts) == SOURCE_COUNTS
    assert sum(counts.values()) == 1809


def test_source_block_records_how_the_fixture_was_made() -> None:
    source = CANDIDATE["source"]
    assert source["zero_point_package"] == "gaiadr3-zeropoint==0.1.0"
    assert source["discordance_z"] == 3.0
    assert source["retrieved_utc"].startswith("2026-11-03")
    assert {"ident", "simbad", "gaia", "hipparcos_neighbour", "hipparcos", "distance"} <= set(source["queries"])


def test_the_gaia_cross_match_places_every_star_where_the_registry_does() -> None:
    offsets = [(e["inputs"]["gaia_position_offset_arcsec"], n) for n, e in STARS.items()
               if e["inputs"]["gaia_position_offset_arcsec"] is not None]
    assert len(offsets) > 1500
    assert max(offsets)[0] < 2.0, max(offsets)
    assert all(len(e["inputs"]["gaia_source_ids"]) <= 1 for e in STARS.values())


def test_zero_point_is_stored_only_inside_its_published_validity() -> None:
    defined = undefined = 0
    for name, entry in STARS.items():
        gaia = entry["inputs"]["gaia"]
        if gaia is None:
            continue
        if gaia["zero_point"] is None:
            undefined += 1
            continue
        defined += 1
        assert gaia["astrometric_params_solved"] in (31, 95), name
        assert 6.0 <= gaia["phot_g_mean_mag"] <= 21.0, name
        assert abs(gaia["zero_point"]) < 0.1, name
    assert defined > 50 and undefined > 1000


def test_undefined_zero_point_agrees_with_the_validity_rule() -> None:
    for name, entry in STARS.items():
        gaia = entry["inputs"]["gaia"]
        if gaia is not None and gaia["zero_point"] is None:
            assert ingest.gaia_zero_point(gaia) is None, name


def test_discordant_rows_are_marked_and_span_both_measurements() -> None:
    discordant = [(n, e["derived"]) for n, e in STARS.items()
                  if e["derived"]["parallax_source"] == "gaia_hipparcos_combined_discordant"]
    assert len(discordant) == 151
    for name, derived in discordant:
        assert "discordant" in derived["flags"], name
        assert derived["discordance_z"] > 3.0, name
        gaia, hipparcos = derived["candidates"]["gaia"], derived["candidates"]["hipparcos"]
        for candidate in (gaia, hipparcos):
            reach = abs(derived["parallax_mas"] - candidate["parallax_mas"])
            assert reach <= derived["parallax_error_mas"] * (1 + 1e-9), name
    undisputed = [d for e in STARS.values() for d in [e["derived"]]
                  if d["parallax_source"] == "gaia_hipparcos_combined"]
    assert all(d["discordance_z"] <= 3.0 and "discordant" not in d["flags"] for d in undisputed)


def test_every_adopted_value_has_a_positive_finite_error() -> None:
    for name, entry in STARS.items():
        derived = entry["derived"]
        if derived["parallax_source"] == "none":
            assert derived["parallax_mas"] is None and derived["parallax_error_mas"] is None, name
            continue
        assert math.isfinite(derived["parallax_mas"]), name
        assert derived["parallax_error_mas"] > 0.0 and math.isfinite(derived["parallax_error_mas"]), name
        assert derived["parallax_bibcodes"], name


def test_hipparcos_matches_are_catalogued_or_named_by_simbad() -> None:
    kinds = {e["inputs"]["hipparcos"]["match"] for e in STARS.values() if e["inputs"]["hipparcos"]}
    assert kinds == {"gaia_dr3_hipparcos2_best_neighbour", "simbad_identifier"}


def test_bailer_jones_distances_are_frozen_for_later_corroboration() -> None:
    present = [e["inputs"]["bailer_jones_2021"] for e in STARS.values() if e["inputs"]["bailer_jones_2021"]]
    assert len(present) > 1000
    assert all(d["r_lo_geo"] <= d["r_med_geo"] <= d["r_hi_geo"] for d in present)


@pytest.mark.parametrize("name", ["bet Phe", "Polis", "Garnet Star"])
def test_the_defect_stars_have_a_fractional_error_above_the_limit(name: str) -> None:
    derived = STARS[name]["derived"]
    assert derived["parallax_error_mas"] / derived["parallax_mas"] > 0.2


def test_omicron_cassiopeiae_has_a_usable_distance() -> None:
    derived = STARS["omi Cas"]["derived"]
    fraction = derived["parallax_error_mas"] / derived["parallax_mas"]
    assert fraction <= 0.2
    assert 600.0 < 3261.56 / derived["parallax_mas"] < 800.0


def test_calibrated_distances_agree_with_bailer_jones_2021() -> None:
    """Cross-engine corroboration where Gaia's zero-point is defined (G >= 6).

    The published 16-84% interval should hold roughly two thirds of independent
    estimates; our adopted distances sit inside it for nearly all calibrated stars.
    Brighter stars are excluded on evidence: Gaia's formal errors there are optimistic
    (about 40% inside, with the intervals only about 1% wide), so the same test is
    not a statement about them.
    """
    inside = []
    for entry in STARS.values():
        derived, gaia, bj = entry["derived"], entry["inputs"]["gaia"], entry["inputs"]["bailer_jones_2021"]
        if not (bj and gaia and gaia["zero_point"] is not None and derived["parallax_mas"]):
            continue
        if derived["parallax_source"] == "gaia_hipparcos_combined_discordant":
            continue
        if derived["parallax_mas"] <= 0 or derived["parallax_error_mas"] / derived["parallax_mas"] > 0.2:
            continue
        distance_pc = 1000.0 / derived["parallax_mas"]
        inside.append(bj["r_lo_geo"] <= distance_pc <= bj["r_hi_geo"])
    assert len(inside) > 100
    assert sum(inside) / len(inside) > 0.95
