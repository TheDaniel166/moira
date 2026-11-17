"""Resume integrity tests for the independent NASA-compatible catalog scan."""
import importlib.util
import json
import math
from pathlib import Path

import pytest

from moira.eclipse_canon import _tt_to_ut_nasa_catalog
from moira.julian import decimal_year_from_jd, julian_day, ut_to_tt_nasa_canon


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "eclipse_catalog"


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("canon_discovery_test", SCRIPTS / "canon_discovery.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resume_verifies_chunk_content_digest(runner, tmp_path):
    payload = tmp_path / "chunk_000.json"
    payload.write_text(json.dumps({"bounds_tt": [1.0, 2.0], "fingerprint": "source",
                                  "runner_sha256": "runner", "rows": [{"jd_tt": 1.5}]}))
    (tmp_path / "chunk_000.sha256").write_text(runner.file_hash(payload) + "\n", encoding="ascii")
    args = (0, 1.0, 2.0, "unused", str(tmp_path), "source", "runner")
    assert runner._scan_chunk(args) == (0, 1)
    payload.write_text(payload.read_text() + " ")  # still valid JSON, different bytes
    with pytest.raises(RuntimeError, match="invalid content digest"):
        runner._scan_chunk(args)


def test_resume_rejects_missing_chunk_or_checksum(runner, tmp_path):
    digest = tmp_path / "chunk_000.sha256"
    digest.write_text("0" * 64, encoding="ascii")
    args = (0, 1.0, 2.0, "unused", str(tmp_path), "source", "runner")
    with pytest.raises(RuntimeError, match="digest but no payload"):
        runner._scan_chunk(args)
    digest.unlink()
    (tmp_path / "chunk_000.json").write_text("{}")
    with pytest.raises(RuntimeError, match="missing or invalid content digest"):
        runner._scan_chunk(args)


def test_resume_rejects_different_frozen_runner(runner, tmp_path):
    payload = tmp_path / "chunk_000.json"
    payload.write_text(json.dumps({"bounds_tt": [1.0, 2.0], "fingerprint": "source",
                                  "runner_sha256": "old-runner", "rows": []}))
    (tmp_path / "chunk_000.sha256").write_text(runner.file_hash(payload), encoding="ascii")
    with pytest.raises(RuntimeError, match="frozen run"):
        runner._scan_chunk((0, 1.0, 2.0, "unused", str(tmp_path), "source", "new-runner"))


@pytest.mark.parametrize("year,month,day", [(-1633, 1, 1), (-1633, 3, 1),
                                             (1582, 10, 15), (2000, 1, 1),
                                             (2020, 3, 1)])
@pytest.mark.parametrize("offset_seconds", [-3.0, 3.0])
def test_catalog_time_round_trip_uses_month_midpoint(runner, year, month, day, offset_seconds):
    jd_ut = julian_day(year, month, day) + offset_seconds / 86400.0
    tt = runner._ut_to_tt_nasa_catalog(jd_ut)
    assert tt == ut_to_tt_nasa_canon(jd_ut, decimal_year_from_jd(jd_ut))
    assert abs(_tt_to_ut_nasa_catalog(tt) - jd_ut) <= 2 * math.ulp(jd_ut)
