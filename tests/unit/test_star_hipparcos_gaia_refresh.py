"""The del Ind and sig02 UMa registry rows re-derive from their frozen inputs.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 3.3.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "star_hipparcos_gaia_refresh_2026_10_30.json"
REGISTRY = ROOT / "moira" / "data" / "star_registry.csv"
PROVENANCE = ROOT / "moira" / "data" / "star_provenance.json"


def _ingest():
    path = ROOT / "scripts" / "data_ingestion" / "augment_star_registry_astrometry.py"
    spec = importlib.util.spec_from_file_location("augment_star_registry_astrometry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CANDIDATE = json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["del Ind", "sig02 UMa"])
def test_refreshed_row_reproduces_from_hipparcos_and_gaia(name: str) -> None:
    entry = CANDIDATE["stars"][name]
    derived = _ingest().hipparcos_gaia_astrometry(entry["inputs"])
    assert derived == entry["derived"]
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        row = {r["name"]: r for r in csv.DictReader(handle)}[name]
    for column in ("ra_deg", "dec_deg", "pmra_mas_yr", "pmdec_mas_yr", "parallax_mas"):
        assert float(row[column]) == derived[column], column
    assert row["ref_epoch_jd"] == "2451545.0" and row["frame"] == "ICRS"
    sources = json.loads(PROVENANCE.read_text(encoding="utf-8"))[name]["astrometry_sources"]["hipparcos_gaia"]
    assert sources["gaia_dr3_source_id"] == entry["inputs"]["source_id"]
    assert sources["parallax_source"] == derived["parallax_source"]


def test_parallax_follows_the_gaia_quality_rule() -> None:
    ingest = _ingest()
    # Gaia's fit of del Ind is poor (RUWE 11.6), so Hipparcos keeps the parallax.
    assert CANDIDATE["stars"]["del Ind"]["inputs"]["ruwe"] > ingest.GAIA_RUWE_LIMIT
    assert CANDIDATE["stars"]["del Ind"]["derived"]["parallax_source"] == "hipparcos_2007"
    assert CANDIDATE["stars"]["sig02 UMa"]["inputs"]["ruwe"] <= ingest.GAIA_RUWE_LIMIT
    assert CANDIDATE["stars"]["sig02 UMa"]["derived"]["parallax_source"] == "gaia_dr3"


def test_long_term_motion_lies_on_the_hipparcos_gaia_chord() -> None:
    ingest = _ingest()
    for entry in CANDIDATE["stars"].values():
        inputs, derived = entry["inputs"], entry["derived"]
        east, north = ingest._offset_mas(inputs["hip_ra"], inputs["hip_dec"], inputs["ra"], inputs["dec"])
        assert derived["pmra_mas_yr"] == pytest.approx(east / 24.75, abs=5e-4)
        assert derived["pmdec_mas_yr"] == pytest.approx(north / 24.75, abs=5e-4)
