"""
Smoke tests for the test environment itself.
Verifies fixtures, markers, and network-blocking all work.
"""
from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Fixture smoke tests
# ---------------------------------------------------------------------------

def test_moira_engine_fixture(moira_engine):
    """Session-scoped Moira engine is available and has a reader."""
    assert moira_engine is not None
    assert hasattr(moira_engine, "_reader")


def test_natal_chart_fixture(natal_chart):
    """Test chart has expected planets and a valid JD."""
    assert natal_chart.jd_ut > 2451545.0 - 1
    assert "Sun" in natal_chart.planets
    assert "Moon" in natal_chart.planets
    assert 0 <= natal_chart.planets["Sun"].longitude < 360


def test_natal_houses_fixture(natal_houses):
    """House cusps fixture returns valid Placidus cusps."""
    assert len(natal_houses.cusps) == 12
    assert 0 <= natal_houses.asc < 360
    assert 0 <= natal_houses.mc  < 360


def test_jd_j2000_fixture(jd_j2000):
    assert jd_j2000 == 2451545.0


# ---------------------------------------------------------------------------
# Snapshot / golden fixtures
# ---------------------------------------------------------------------------

def test_snapshot_roundtrip(snapshot, tmp_path, monkeypatch):
    """snapshot fixture reads an approved temporary witness without mutation."""
    from tools import snapshots as snap_mod

    monkeypatch.setattr(snap_mod, "SNAPSHOT_DIR", tmp_path)
    path = tmp_path / "test_value.json"
    path.write_text(json.dumps({"value": 42}), encoding="utf-8")
    before = path.read_bytes()

    snapshot("test_value", 42)

    assert path.read_bytes() == before


def test_golden_roundtrip(golden, tmp_path, monkeypatch):
    """golden fixture reads approved temporary storage without mutation."""
    from tools import golden as gold_mod

    monkeypatch.setattr(gold_mod, "GOLDEN_DIR", tmp_path)
    path = tmp_path / "test_gold.json"
    path.write_text(json.dumps({"value": {"a": 1}}), encoding="utf-8")
    before = path.read_bytes()

    golden("test_gold", {"a": 1})

    assert path.read_bytes() == before


# ---------------------------------------------------------------------------
# Network-blocking smoke test
# ---------------------------------------------------------------------------

def test_network_blocked_by_default():
    """Destination operations fail without an explicit network capability."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        with pytest.raises(RuntimeError, match="Moira test network policy"):
            stream.bind(("0.0.0.0", 0))


@pytest.mark.loopback
def test_loopback_allowed_when_marked():
    """@pytest.mark.loopback admits local IPC without external access."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.bind(("127.0.0.1", 0))
