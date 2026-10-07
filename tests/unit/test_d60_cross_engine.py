"""Frozen independent-function evidence; no comparator code/dependency import.

PyJHora returns full positions. Maitreya returns a sign; its recorded longitude
is an instrumented intermediate. D1 planetary inputs are Moira/DE441-derived,
so these witnesses validate conditioned D60 mapping, not ephemeris accuracy.
"""
from collections import Counter
import json
from pathlib import Path

import pytest

from moira import Moira
from moira.varga import D60Method, shashtiamsha, vimshopaka_bala

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = json.loads((ROOT / "tests/artifacts/oracle/d60_cross_engine_2026-10-07.json").read_text(encoding="utf-8"))
CASES = EVIDENCE["cases"]
TOLERANCE = EVIDENCE["numeric_absolute_tolerance_deg"]
PROFILE = D60Method.PVR_TEXTBOOK_LINEAR
SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
CHARTS = sorted({(row["dt"], row["ayanamsa_system"]) for row in CASES if row["kind"] == "planetary"})
REPRESENTATIVES = [next(row for row in CASES if row["kind"] == "random" and row["natal_sign_index"] == sign) for sign in range(12)]


@pytest.fixture(params=[PROFILE, D60Method.CLASSICAL_DERIVED_LINEAR])
def profile(request):
    return request.param


def assert_external_position(point, row, profile):
    assert row["pyjhora_sign_index"] == row["maitreya_sign_index"], row["id"]
    assert point.sign == SIGNS[row["pyjhora_sign_index"]], row["id"]
    assert int(point.varga_longitude // 30) == row["pyjhora_sign_index"], row["id"]
    assert point.sign_degree == pytest.approx(row["pyjhora_sign_degree"], abs=TOLERANCE, rel=0), row["id"]
    assert point.varga_longitude == pytest.approx(row["maitreya_instrumented_longitude"], abs=TOLERANCE, rel=0), row["id"]
    assert 0 <= point.sign_degree < 30 and 0 <= point.varga_longitude < 360
    assert point.d60_method is profile


def test_external_fixture_identity_precision_and_coverage():
    assert EVIDENCE["evidence_class"] == "cross_engine_corroboration"
    assert EVIDENCE["profile"] == PROFILE.value
    assert EVIDENCE["source_manifest"] == json.loads((ROOT / "scripts/d60_cross_engine_sources.json").read_text(encoding="utf-8"))
    assert {source["engine"]: source["commit"] for source in EVIDENCE["source_manifest"]} == {
        "pyjhora": "48e57d29b47a3143519910a24866758116467485",
        "maitreya": "dc468ded92798638f36a318838fc34eaf8623640",
    }
    assert Counter(row["kind"] for row in CASES) == {"interior": 2160, "boundary": 2160, "random": 120, "planetary": 112}
    assert len({row["id"] for row in CASES}) == len(CASES) == 4552
    assert len(CHARTS) == 16
    assert {row["natal_sign_index"] for row in CASES if row["kind"] == "planetary"} == set(range(12))


@pytest.mark.parametrize("natal_sign", range(12))
@pytest.mark.parametrize("kind", ["interior", "boundary"])
def test_every_segment_against_both_pinned_implementations(natal_sign, kind, profile):
    rows = [row for row in CASES if row["kind"] == kind and row["natal_sign_index"] == natal_sign]
    assert len(rows) == 180
    for row in rows:
        assert_external_position(shashtiamsha(row["longitude"], d60_method=profile), row, profile)


@pytest.mark.parametrize("kind", ["random", "planetary"])
def test_seeded_and_planetary_full_positions_against_external_outputs(kind, profile):
    for row in CASES:
        if row["kind"] == kind:
            assert_external_position(shashtiamsha(row["longitude"], d60_method=profile), row, profile)


@pytest.mark.parametrize("row", REPRESENTATIVES, ids=lambda row: row["id"])
def test_facade_full_position_uses_external_expected_values(row, profile):
    engine = Moira.__new__(Moira)
    engine._reader_obj = None
    assert_external_position(engine.varga_named(row["longitude"], "shashtiamsha", d60_method=profile), row, profile)
    assert_external_position(engine.shodashvarga(row["longitude"], d60_method=profile)["shashtiamsha"], row, profile)


@pytest.mark.parametrize("date,frame", CHARTS)
@pytest.mark.parametrize("group,weight", [("dashavarga", 5), ("shodashavarga", 4)])
def test_strength_d60_sign_selection_uses_external_planetary_witnesses(date, frame, group, weight, profile):
    rows = [row for row in CASES if row["kind"] == "planetary" and (row["dt"], row["ayanamsa_system"]) == (date, frame)]
    assert len(rows) == 7
    longitudes = {row["body"]: row["longitude"] for row in rows}
    for row in rows:
        strength = vimshopaka_bala(row["body"], longitudes, group, d60_method=profile)
        entry = next(entry for entry in strength.entries if entry.division == 60)
        assert entry.varga_sign_index == row["pyjhora_sign_index"] == row["maitreya_sign_index"]
        assert entry.weight == weight
        assert strength.d60_method is profile
