"""Governance checks for the Orbital Core Stage 4 validation receipt."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


TEST_ROOT = Path(__file__).parents[1]
RECEIPT_PATH = (
    TEST_ROOT
    / "artifacts"
    / "release"
    / "orbital_core_stage4_validation_2026-09-17.json"
)
SPEC_PATH = (
    TEST_ROOT.parent
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-15-orbital-core-design.md"
)
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<!http)(?<!htt)(?:[a-z]:[\\/])")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage4_receipt_is_path_free_and_binds_governing_spec() -> None:
    rendered = RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = json.loads(rendered)
    spec_bytes = SPEC_PATH.read_bytes()

    assert receipt["schema"] == "moira.orbital-core-stage4.validation/v1"
    assert not WINDOWS_ABSOLUTE_PATH.search(rendered)
    assert receipt["algorithm_version"] == "MOIRA_SHADBALA_CHESTA_BALA_STAGE4_V1"
    assert receipt["status"] == "implemented_and_verified"
    assert receipt["network_boundary"]["external_network_used"] is False

    governing_spec = receipt["governing_spec"]
    assert governing_spec["path"] == "docs/superpowers/specs/2026-09-15-orbital-core-design.md"
    assert governing_spec["sha256"] == hashlib.sha256(spec_bytes).hexdigest()


def test_stage4_receipt_records_bibliographic_authority_and_retired_mechanisms() -> None:
    receipt = _load(RECEIPT_PATH)

    bib = receipt["bibliographic_authority"]
    assert bib["author"] == "Bangalore Venkata Raman"
    assert bib["title"] == "Graha and Bhava Balas"
    assert bib["edition"] == "Thirteenth Edition"
    assert bib["preface_date"] == "1992-02-01"

    citations = bib["citations"]
    assert citations["non_luminaries"]["chapter"] == "VI"
    assert "64-79" in citations["non_luminaries"]["pages"]
    assert citations["luminaries"]["chapter"] == "X"
    assert "§§136-137" in citations["luminaries"]["sections"]

    retired = receipt["retired_legacy_mechanisms"]
    assert any("_sun_mandoccha_lon" in r for r in retired)
    assert any("_moon_mandoccha_lon" in r for r in retired)


def test_stage4_receipt_verifies_all_seven_planetary_shifts() -> None:
    receipt = _load(RECEIPT_PATH)
    shifts = receipt["measured_j2000_shifts"]

    planets = {s["planet"] for s in shifts}
    assert planets == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}

    for s in shifts:
        assert 0.0 <= s["legacy_chesta_sha"] <= 60.0
        assert 0.0 <= s["stage4_chesta_sha"] <= 60.0
        expected_delta = round(s["stage4_chesta_sha"] - s["legacy_chesta_sha"], 4)
        assert round(s["delta_sha"], 4) == expected_delta
