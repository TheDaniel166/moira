"""Composition parity with house/aspect owners, no ephemeris required."""

from dataclasses import replace

import pytest

from moira.aspects import AspectPolicy, aspects_to_point
from moira.constants import HouseSystem
from moira.geodetic import GeodeticLocation, _armc_from_mc, geodetic_mc
from moira.geodetic_analysis import (
    GeodeticNamedLocation, compare_geodetic_locations,
    geodetic_house_chart, geodetic_natal_overlay,
)
from moira.geodetic_inputs import geodetic_snapshot_from_positions
from moira.houses import HousePolicy, houses_from_armc, assign_house


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN])
@pytest.mark.parametrize("zodiac,offset", [("tropical", 0), ("sidereal", 24)])
def test_house_composition_and_static_body_family_parity(system, zodiac, offset):
    location = GeodeticLocation(40, -74)
    figure = geodetic_house_chart(location, obliquity=23.44, system=system, zodiac=zodiac, ayanamsa_deg=offset)
    owner = houses_from_armc(_armc_from_mc(geodetic_mc(-74), 23.44), 23.44, 40, system,
                            policy=HousePolicy.strict(), ayanamsa_offset=offset)
    assert figure.houses == owner
    snapshot = geodetic_snapshot_from_positions({"Sun": 5, "Ceres": 25, "Chiron": 60, "Eris": 170, "comet:Halley": 286},
                                               source_frame=figure.source_frame, zodiac=zodiac, ayanamsa_deg=offset)
    policy = AspectPolicy(tier=0)
    overlay = geodetic_natal_overlay(figure, snapshot, aspect_policy=policy, include_cusps=True)
    assert len(figure.houses.cusps) == 12
    assert [p.placement for p in overlay.placements] == [assign_house(p.selected_longitude_deg, owner) for p in snapshot.positions]
    assert overlay.contacts == tuple(c for name, lon in overlay.target_longitudes for c in aspects_to_point(lon, snapshot.longitudes, point_name=name, policy=policy))
    assert all(c.applying is None for c in overlay.contacts)
    if system == HouseSystem.PLACIDUS:
        assert ("ASC", "Cusp 1") in overlay.coincident_targets
    else:
        assert figure.targets["MC"] != figure.houses.cusps[9]


def test_solar_input_and_frame_epoch_mismatch():
    with pytest.raises(ValueError):
        geodetic_house_chart(GeodeticLocation(40, -74), obliquity=23.44, system=HouseSystem.SUNSHINE)
    figure = geodetic_house_chart(GeodeticLocation(40, -74), obliquity=23.44, system=HouseSystem.SUNSHINE, sun_longitude=42)
    snapshot = geodetic_snapshot_from_positions({"Sun": 42}, source_frame="different")
    with pytest.raises(ValueError, match="frame"):
        geodetic_natal_overlay(figure, snapshot, aspect_policy=AspectPolicy())
    snapshot = replace(snapshot, source_frame=figure.source_frame, jd_ut1=2451545, jd_tt=2451545.001)
    with pytest.raises(ValueError, match="epochs"):
        geodetic_natal_overlay(figure, snapshot, aspect_policy=AspectPolicy())


def test_comparison_order_failures_and_circular_deltas():
    places = [GeodeticNamedLocation("west", GeodeticLocation(30, -179), "Same"),
              GeodeticNamedLocation("pole", GeodeticLocation(90, 0)),
              GeodeticNamedLocation("east", GeodeticLocation(30, 179), "Same")]
    snapshot = geodetic_snapshot_from_positions({"comet:Halley": 2}, source_frame="explicit")
    result = compare_geodetic_locations(places, snapshot, obliquity=23.44, system=HouseSystem.EQUAL,
                                       aspect_policy=AspectPolicy(tier=0), error_policy="collect")
    assert [r.place.location_id for r in result.results] == ["west", "pole", "east"]
    assert result.results[1].overlay is None and result.results[1].reason
    assert dict(result.results[2].difference.angle_deltas_deg)["MC"] == -2
    for r in (result.results[0], result.results[2]):
        direct = geodetic_house_chart(r.place.location, obliquity=23.44, system=HouseSystem.EQUAL, source_frame="explicit")
        assert r.overlay.house_chart == direct
        assert r.overlay.snapshot is snapshot
    with pytest.raises(ValueError, match="duplicate"):
        compare_geodetic_locations([places[0], places[0]], snapshot, obliquity=23.44, system=HouseSystem.EQUAL, aspect_policy=AspectPolicy())


def test_polar_strict_refusal_and_explicit_fallback_receipt():
    location = GeodeticLocation(80, 0)
    with pytest.raises(ValueError, match="RAISE"):
        geodetic_house_chart(location, obliquity=23.44, system=HouseSystem.PLACIDUS)
    figure = geodetic_house_chart(location, obliquity=23.44, system=HouseSystem.PLACIDUS, house_policy=HousePolicy.default())
    owner = houses_from_armc(0, 23.44, 80, HouseSystem.PLACIDUS, policy=HousePolicy.default(), ayanamsa_offset=0)
    assert figure.houses == owner
    assert figure.houses.fallback
    assert figure.houses.fallback_reason == owner.fallback_reason


def test_stable_metric_ties_and_solar_snapshot_reuse():
    snapshot = geodetic_snapshot_from_positions({"Sun": 20, "comet:Halley": 40}, source_frame="explicit")
    places = [GeodeticNamedLocation(name, GeodeticLocation(30, 0)) for name in ("second", "first")]
    result = compare_geodetic_locations(places, snapshot, obliquity=23.44, system=HouseSystem.SUNSHINE,
                                       aspect_policy=AspectPolicy(tier=0), order_by="minimum_contact_orb")
    assert result.complete
    assert [r.place.location_id for r in result.results] == ["second", "first"]
    assert result.baseline_id == "second"
    with pytest.raises(ValueError, match="obliquity"):
        compare_geodetic_locations(places, snapshot, obliquity=0, system=HouseSystem.EQUAL,
                                   aspect_policy=AspectPolicy(), error_policy="collect")
