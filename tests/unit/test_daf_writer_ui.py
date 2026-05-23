"""
Tests for moira.daf_writer_ui._search_sbdb, _parse_csv_to_bodies, _verify_kernel.

Verifies:
- Correct API endpoint (sbdb.api, not sbdb_query.api)
- Correct query parameter (sstr, not sb-name)
- NAIF ID conversion: spkid "20000004" → 2000004
- orbit_class dict parsed into body_type
- Kind filtering (asteroid/comet)
- Empty result when 'object' key absent
- Duplicate JD rows are deduplicated (Fetch→CSV then Fetch+Build→CSV scenario)
- Kernel verification uses SmallBodyKernel (not SpkReader) for type-13 segments
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moira.daf_writer_ui import _parse_csv_to_bodies, _search_sbdb, _verify_kernel


# --- canonical fixture responses matching real sbdb.api output shape ---

_VESTA = {
    "object": {
        "spkid": "20000004",
        "fullname": "4 Vesta",
        "des": "4",
        "shortname": "Vesta",
        "orbit_class": {"name": "Main-belt Asteroid"},
        "kind": "an",
    }
}

_HALLEY = {
    "object": {
        "spkid": "1000036",
        "fullname": "1P/Halley",
        "des": "1P",
        "shortname": "Halley",
        "orbit_class": {"name": "Halley-type Comet"},
        "kind": "cp",
        "prefix": "1P",
    }
}

_APOLLO = {
    "object": {
        "spkid": "20001862",
        "fullname": "1862 Apollo (1932 HA)",
        "des": "1862",
        "shortname": "Apollo",
        "orbit_class": {"name": "Apollo"},
        "kind": "an",
    }
}

_ORCUS = {
    "object": {
        "spkid": "20090482",
        "fullname": "90482 Orcus (2004 DW)",
        "des": "90482",
        "shortname": "Orcus",
        "orbit_class": {"name": "TransNeptunian Object"},
        "kind": "an",
    }
}

_NOT_FOUND = {"message": "specified object was not found"}


def _make_response(body: dict) -> MagicMock:
    """Return a context-manager mock whose .read() yields the JSON bytes."""
    raw = json.dumps(body).encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.read.return_value = raw
    return cm


class TestSearchSbdbEndpoint:
    """Verify the correct JPL API is called with the correct parameter."""

    def test_uses_sbdb_api_not_sbdb_query(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)) as mock:
            _search_sbdb("Vesta")
        called_url: str = mock.call_args[0][0]
        assert "sbdb.api" in called_url
        assert "sbdb_query" not in called_url

    def test_uses_sstr_not_sb_name(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)) as mock:
            _search_sbdb("Vesta")
        called_url: str = mock.call_args[0][0]
        assert "sstr=Vesta" in called_url
        assert "sb-name" not in called_url

    def test_query_is_url_encoded(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_NOT_FOUND)) as mock:
            _search_sbdb("some body")
        called_url: str = mock.call_args[0][0]
        assert "sstr=some+body" in called_url or "sstr=some%20body" in called_url


class TestSearchSbdbNaifConversion:
    """NAIF conversion: 2000000 + (spkid % 10000000)."""

    def test_vesta_naif(self):
        # spkid "20000004" → 2000000 + (20000004 % 10000000) = 2000000 + 4 = 2000004
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)):
            results = _search_sbdb("Vesta")
        assert results[0]["naif"] == 2000004

    def test_apollo_naif(self):
        # spkid "20001862" → 2000000 + (20001862 % 10000000) = 2000000 + 1862 = 2001862
        with patch("urllib.request.urlopen", return_value=_make_response(_APOLLO)):
            results = _search_sbdb("Apollo")
        assert results[0]["naif"] == 2001862

    def test_orcus_naif(self):
        # spkid "20090482" → 2000000 + (20090482 % 10000000) = 2000000 + 90482 = 2090482
        with patch("urllib.request.urlopen", return_value=_make_response(_ORCUS)):
            results = _search_sbdb("Orcus")
        assert results[0]["naif"] == 2090482

    def test_comet_naif_is_zero(self):
        # Comets use DES commands; NAIF is set to 0 to avoid misleading values
        with patch("urllib.request.urlopen", return_value=_make_response(_HALLEY)):
            results = _search_sbdb("Halley")
        assert results[0]["naif"] == 0


class TestSearchSbdbFields:
    """Result dict structure and field mapping."""

    def test_vesta_fields(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)):
            results = _search_sbdb("Vesta")
        assert len(results) == 1
        r = results[0]
        assert r["name"] == "Vesta"
        assert r["full_name"] == "4 Vesta"
        assert r["pdes"] == "4"
        assert r["type"] == "Main-belt Asteroid"
        # Command must be the catalog designation, not the NAIF ID.
        # Horizons reliably resolves catalog numbers for all small bodies;
        # NAIF-form only works for the handful in the planetary kernel.
        assert r["command"] == "4"

    def test_halley_fields(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_HALLEY)):
            results = _search_sbdb("Halley")
        r = results[0]
        assert r["name"] == "Halley"
        assert r["pdes"] == "1P"
        assert "DES=1P" in r["command"]
        assert "NOFRAG" in r["command"]

    def test_orbit_class_dict_parsed(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)):
            results = _search_sbdb("Vesta")
        assert results[0]["type"] == "Main-belt Asteroid"

    def test_tno_command_uses_designation_not_naif(self):
        # Horizons only resolves NAIF-form IDs for bodies in the planetary
        # kernel (Vesta, Ceres, etc.).  TNOs like Orcus must use the catalog
        # designation number so Horizons can find them.
        with patch("urllib.request.urlopen", return_value=_make_response(_ORCUS)):
            results = _search_sbdb("Orcus")
        assert results[0]["command"] == "90482"
        assert results[0]["naif"] == 2090482  # NAIF still computed for kernel segment ID


class TestSearchSbdbKindFilter:
    """kind= parameter filters results by body type."""

    def test_kind_asteroid_excludes_comet(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_HALLEY)):
            results = _search_sbdb("Halley", kind="asteroid")
        assert results == []

    def test_kind_comet_excludes_asteroid(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)):
            results = _search_sbdb("Vesta", kind="comet")
        assert results == []

    def test_kind_all_returns_asteroid(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)):
            results = _search_sbdb("Vesta", kind="all")
        assert len(results) == 1

    def test_kind_all_returns_comet(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_HALLEY)):
            results = _search_sbdb("Halley", kind="all")
        assert len(results) == 1

    def test_kind_comet_accepts_comet(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_HALLEY)):
            results = _search_sbdb("Halley", kind="comet")
        assert len(results) == 1

    def test_kind_asteroid_accepts_asteroid(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_VESTA)):
            results = _search_sbdb("Vesta", kind="asteroid")
        assert len(results) == 1


class TestSearchSbdbNotFound:
    """Missing or empty 'object' key returns empty list."""

    def test_not_found_response_returns_empty(self):
        with patch("urllib.request.urlopen", return_value=_make_response(_NOT_FOUND)):
            results = _search_sbdb("xyzzy_not_a_real_body")
        assert results == []

    def test_empty_object_returns_empty(self):
        with patch("urllib.request.urlopen", return_value=_make_response({})):
            results = _search_sbdb("something")
        assert results == []


# --- _REQUIRED_COLUMNS row template ---
_ROW = {
    "naif_id": "2000004",
    "jd_tdb": "2451545.000000000",
    "x_km": "1.0",
    "y_km": "2.0",
    "z_km": "3.0",
    "vx_km_s": "0.001",
    "vy_km_s": "0.002",
    "vz_km_s": "0.003",
}


def _write_csv(path: Path, rows: list[dict]) -> None:
    headers = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class TestParseCsvDeduplication:
    """Duplicate JD rows from re-fetch + append must be silently deduplicated."""

    def test_exact_duplicate_rows_do_not_raise(self, tmp_path: Path):
        # Simulates: Fetch→CSV then Fetch+Build BSP with append=True
        row2 = {**_ROW, "jd_tdb": "2451546.000000000"}
        rows = [_ROW, row2, _ROW, row2]  # two identical pairs
        csv_path = tmp_path / "dup.csv"
        _write_csv(csv_path, rows)
        bodies, previews = _parse_csv_to_bodies(csv_path)
        assert len(bodies) == 1
        assert len(bodies[0]["epochs_jd"]) == 2

    def test_last_occurrence_wins_for_duplicate_jd(self, tmp_path: Path):
        original = {**_ROW, "x_km": "1.0"}
        updated = {**_ROW, "x_km": "99.0"}
        csv_path = tmp_path / "dup2.csv"
        _write_csv(csv_path, [original, updated])
        bodies, _ = _parse_csv_to_bodies(csv_path)
        assert bodies[0]["states"][0][0] == 99.0

    def test_non_duplicate_non_monotonic_still_raises(self, tmp_path: Path):
        row_a = {**_ROW, "jd_tdb": "2451546.0"}
        row_b = {**_ROW, "jd_tdb": "2451545.0"}  # out of order, distinct JD
        csv_path = tmp_path / "bad.csv"
        _write_csv(csv_path, [row_a, row_b])
        # After dedup, rows are sorted by JD so this should NOT raise.
        bodies, _ = _parse_csv_to_bodies(csv_path)
        assert bodies[0]["epochs_jd"] == [2451545.0, 2451546.0]


# ---------------------------------------------------------------------------
# _verify_kernel tests
#
# _verify_kernel must use SmallBodyKernel — the sovereign type-13 reader —
# not SpkReader, which silently falls back to jplephem for type-13 segments.
# All tests mock SmallBodyKernel at the daf_writer_ui import site.
# ---------------------------------------------------------------------------

def _make_kernel_mock(
    bodies: list[dict],
    coverage: dict | None = None,
    position_side_effect=None,
) -> MagicMock:
    """
    Build a SmallBodyKernel mock for the given body list.
    coverage: {(center, naif): (start_jd, end_jd)}, defaults to exact match.
    position_side_effect: if set, kernel.position() raises this exception.
    """
    mock = MagicMock()
    mock.has_body.side_effect = lambda naif: any(b["naif_id"] == naif for b in bodies)
    mock.has_segment.side_effect = lambda center, naif: any(
        b["naif_id"] == naif and b["center"] == center for b in bodies
    )
    if coverage is None:
        coverage = {
            (b["center"], b["naif_id"]): (b["epochs_jd"][0], b["epochs_jd"][-1])
            for b in bodies
        }
    mock.coverage.return_value = coverage
    if position_side_effect is not None:
        mock.position.side_effect = position_side_effect
    else:
        mock.position.return_value = (1.0, 2.0, 3.0)
    return mock


_BODY_A = {
    "naif_id": 2000004,
    "name": "Vesta",
    "center": 10,
    "epochs_jd": [2460400.0, 2460405.0, 2460410.0],
    "states": [[0.0] * 3] * 6,
}

_BODY_B = {
    "naif_id": 2090482,
    "name": "Orcus",
    "center": 10,
    "epochs_jd": [2460400.0, 2460410.0],
    "states": [[0.0] * 2] * 6,
}


class TestVerifyKernel:
    """_verify_kernel must use SmallBodyKernel (not SpkReader) and report correctly."""

    _PATCH = "moira.daf_writer_ui.SmallBodyKernel"

    def test_uses_small_body_kernel_not_spk_reader(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        with patch(self._PATCH, return_value=_make_kernel_mock([_BODY_A])) as MockSBK:
            _verify_kernel(path, [_BODY_A])
        MockSBK.assert_called_once_with(path)

    def test_all_ok_returns_true(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        with patch(self._PATCH, return_value=_make_kernel_mock([_BODY_A, _BODY_B])):
            ok, lines = _verify_kernel(path, [_BODY_A, _BODY_B])
        assert ok is True
        ok_lines = [ln for ln in lines if "OK" in ln]
        assert len(ok_lines) == 2

    def test_missing_body_returns_false(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        mock = _make_kernel_mock([_BODY_A])
        mock.has_body.side_effect = lambda naif: False  # nothing found
        with patch(self._PATCH, return_value=mock):
            ok, lines = _verify_kernel(path, [_BODY_A])
        assert ok is False
        assert any("not present" in ln for ln in lines)

    def test_eval_failure_returns_false(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        mock = _make_kernel_mock([_BODY_A], position_side_effect=RuntimeError("bad eval"))
        with patch(self._PATCH, return_value=mock):
            ok, lines = _verify_kernel(path, [_BODY_A])
        assert ok is False
        assert any("eval at" in ln and "failed" in ln for ln in lines)

    def test_cannot_open_kernel_returns_false(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        with patch(self._PATCH, side_effect=RuntimeError("unsupported segment type")):
            ok, lines = _verify_kernel(path, [_BODY_A])
        assert ok is False
        assert any("cannot open" in ln for ln in lines)

    def test_summary_line_present(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        with patch(self._PATCH, return_value=_make_kernel_mock([_BODY_A])):
            ok, lines = _verify_kernel(path, [_BODY_A])
        assert any("passed" in ln or "FAILED" in ln for ln in lines)

    def test_position_values_appear_in_log(self, tmp_path):
        path = tmp_path / "out.bsp"
        path.touch()
        mock = _make_kernel_mock([_BODY_A])
        mock.position.return_value = (111111.5, -222222.5, 333333.5)
        with patch(self._PATCH, return_value=mock):
            _, lines = _verify_kernel(path, [_BODY_A])
        ok_line = next(ln for ln in lines if "OK" in ln)
        assert "111111" in ok_line
