"""Identity/frame contracts; canonical provider parity is integration-tested."""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from moira.geodetic_inputs import (
    geodetic_snapshot_at, geodetic_snapshot_from_positions,
    geodetic_snapshot_from_chart,
)


def test_manual_names_aliases_and_mutable_input_isolation():
    source = {"comet:Halley": -1, "asteroid:Eris": 361, "External point": 40}
    snapshot = geodetic_snapshot_from_positions(source, source_frame="declared_frame")
    source["External point"] = 90
    assert snapshot.longitudes == {"comet:1P/Halley": 359, "asteroid:Eris": 1, "External point": 40}
    assert snapshot.positions[0].identity.naif_id == 1000001
    values = snapshot.longitudes
    values.clear()
    assert len(snapshot.positions) == 3
    with pytest.raises(FrozenInstanceError):
        snapshot.positions = ()


@pytest.mark.parametrize("names", [{"Halley": 0}, {"comet:Halley": 0, "comet:1P/Halley": 1}, {}])
def test_ambiguous_duplicate_and_empty_inputs_refused(names):
    with pytest.raises(ValueError):
        geodetic_snapshot_from_positions(names, source_frame="ecliptic")


def test_sidereal_requires_explicit_offset_and_vessel_checks_consistency():
    with pytest.raises(ValueError, match="explicit"):
        geodetic_snapshot_from_positions({"Sun": 1}, source_frame="ecliptic", zodiac="sidereal")
    snapshot = geodetic_snapshot_from_positions({"Sun": 1}, source_frame="ecliptic", zodiac="sidereal", ayanamsa_deg=24)
    assert snapshot.longitudes["Sun"] == 337
    with pytest.raises(ValueError, match="disagrees"):
        replace(snapshot, ayanamsa_deg=23)


def test_engine_resolves_once_and_collects_explicit_failures(monkeypatch):
    calls = []
    monkeypatch.setattr("moira._ephemeris_time._ut1_to_ephemeris_tt", lambda jd, reader: jd + .001)

    def position(name, jd, *, reader):
        calls.append((name, jd))
        if name == "asteroid:Eris":
            raise ValueError("resource does not cover epoch")
        return SimpleNamespace(longitude=1, latitude=50, speed=-.1)

    monkeypatch.setattr("moira.planets.planet_at", position)
    snapshot = geodetic_snapshot_at(2451545., ["comet:Halley", "asteroid:Eris"], reader=object(), error_policy="collect")
    assert calls == [("comet:1P/Halley", 2451545.), ("asteroid:Eris", 2451545.)]
    assert not snapshot.complete
    assert snapshot.positions[0].ecliptic_latitude_deg == 50
    assert snapshot.failures[0].body_id == "asteroid:Eris"
    assert snapshot.resource_receipt_status == "not_exposed_by_source"


def test_existing_chart_adapter_preserves_epochs_and_refuses_topocentric(planetary_reader, jd_j2000):
    from moira.chart import create_chart
    original = create_chart(jd_j2000, 40, -74, bodies=["Sun"], reader=planetary_reader)
    snapshot = geodetic_snapshot_from_chart(original, ["Sun"])
    assert snapshot.jd_tt == original.jd_tt
    assert snapshot.positions[0].tropical_longitude_deg == original.planets["Sun"].longitude
    topocentric = replace(original.planets["Sun"], is_topocentric=True)
    chart = replace(original, planets={"Sun": topocentric})
    with pytest.raises(ValueError, match="geocentric"):
        geodetic_snapshot_from_chart(chart)
