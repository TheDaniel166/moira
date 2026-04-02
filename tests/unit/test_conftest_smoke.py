"""
Smoke tests for the test environment itself.
Verifies fixtures, markers, and network-blocking all work.
"""
from __future__ import annotations

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
    """snapshot fixture writes and reads back correctly."""
    import os
    from tools import snapshots as snap_mod

    # Point snapshot dir at a temp location
    monkeypatch.setattr(snap_mod, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setenv("ISOPGEM_SNAPSHOT_UPDATE", "1")

    snap_mod.assert_snapshot("test_value", 42)

    monkeypatch.setenv("ISOPGEM_SNAPSHOT_UPDATE", "0")
    snap_mod.assert_snapshot("test_value", 42)   # should pass


def test_golden_roundtrip(tmp_path, monkeypatch):
    """golden fixture writes and reads back correctly."""
    from tools import golden as gold_mod

    monkeypatch.setattr(gold_mod, "GOLDEN_DIR", tmp_path)
    monkeypatch.setenv("ISOPGEM_GOLDEN_UPDATE", "1")
    gold_mod.assert_golden("test_gold", {"a": 1})

    monkeypatch.setenv("ISOPGEM_GOLDEN_UPDATE", "0")
    gold_mod.assert_golden("test_gold", {"a": 1})


# ---------------------------------------------------------------------------
# Network-blocking smoke test
# ---------------------------------------------------------------------------

def test_network_blocked_by_default():
    """Network calls should raise RuntimeError without @pytest.mark.network."""
    import socket
    with pytest.raises(RuntimeError, match="Network access is disabled"):
        socket.socket()


@pytest.mark.network
def test_network_allowed_when_marked():
    """@pytest.mark.network allows real socket creation."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.close()
