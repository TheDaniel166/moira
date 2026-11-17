"""Contracts of the isolated, provisional eclipse discovery runner."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PATH = Path(__file__).resolve().parents[2] / "scripts" / "eclipse_catalog" / "discovery.py"
SPEC = importlib.util.spec_from_file_location("eclipse_discovery_runner", PATH)
discovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discovery)


def test_historical_year_changes_at_year_boundary():
    # NASA historical calendar: -1999 starts at JD 990923.5 TT.
    assert discovery.historical_year(990923.5) == -1999
    assert discovery.historical_year(990923.5 - 1) == -2000
    assert discovery.historical_year(2451544.5) == 2000


def test_discovery_persists_half_open_rows_and_refuses_overwrite(tmp_path, monkeypatch):
    source = tmp_path / "src"
    source.mkdir()
    native = source / "native.pyd"
    native.write_bytes(b"test native")
    kernel = tmp_path / "kernel.bsp"
    kernel.write_bytes(b"test kernel")
    digest = hashlib.sha256(kernel.read_bytes()).hexdigest()
    output = tmp_path / "out"
    monkeypatch.setattr(discovery, "ROOT", source)
    monkeypatch.setattr(discovery, "_moira_native", SimpleNamespace(__file__=str(native)))
    monkeypatch.setattr(discovery, "find_planetary_kernel", lambda: kernel)
    monkeypatch.setattr(discovery, "source_fingerprint", lambda: "test-fingerprint")
    monkeypatch.setattr(discovery, "_ut1_to_ephemeris_tt", lambda jd, reader: jd)
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")

    class Reader:
        def __init__(self, path):
            assert path == kernel

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def event(jd, lunation):
        return SimpleNamespace(jd_ut=jd, data=SimpleNamespace(
            eclipse_type="Partial", saros_series=1, saros_lunation_number=lunation))

    class Calculator:
        def __init__(self, reader):
            pass

        def solar_eclipses_in_range(self, start, end):
            return [event(2459000.5, 1), event(2459001.5, 2), event(2459002.5, 3)]

    monkeypatch.setattr(discovery, "SpkReader", Reader)
    monkeypatch.setattr(discovery, "EclipseCalculator", Calculator)
    argv = ["--family", "solar", "--directory", str(output), "--kernel-sha256", digest,
            "--start-jd-tt", "2459000.5", "--end-jd-tt", "2459002.5"]
    assert discovery.main(argv) == 0
    with (output / "discovery.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [int(row["lunation_number"]) for row in rows] == [1, 2]
    original = (output / "discovery.csv").read_bytes()
    with pytest.raises(RuntimeError, match="merged output exists"):
        discovery.main(argv)
    assert (output / "discovery.csv").read_bytes() == original
