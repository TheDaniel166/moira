"""Moira facade access to the Geodetic analysis modules.

Governing object: each ``Moira.geodetic_*`` method composes the owning
modules (moira.geodetic_inputs/_analysis/_curves/_timing/_uncertainty) on one
epoch with the engine's own reader. It adds no doctrine of its own.

Evidence class: dual-path equivalence. Each method must equal the hand-built
composition of the owning functions on the same epoch, offset and reader,
compared exactly. Lane-law refusals and the epoch-sharing invariant that
overlays require are asserted directly. The timing case places the Geodetic MC
on the mover's own longitude at the reference epoch, so an exact contact at
that epoch is known in advance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.aspects import AspectPolicy
from moira.constants import HouseSystem
from moira.geodetic import (
    GeodeticInputUncertainty,
    GeodeticLocation,
    geodetic_chart,
    geodetic_chart_at_location,
)
from moira.geodetic_analysis import (
    GeodeticNamedLocation,
    compare_geodetic_locations,
    geodetic_house_chart,
    geodetic_natal_overlay,
)
from moira.geodetic_curves import geodetic_angular_loci
from moira.geodetic_inputs import geodetic_snapshot_at
from moira.geodetic_timing import (
    GeodeticFixedReference,
    GeodeticTimingPolicy,
    find_geodetic_transits,
)
from moira.geodetic_uncertainty import GeodeticDiagnosticPolicy, diagnose_geodetic_uncertainty
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.obliquity import true_obliquity
from moira.planets import planet_at
from moira.sidereal import ayanamsa

pytestmark = pytest.mark.requires_ephemeris

NATAL = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
NEW_YORK = GeodeticLocation(40.7, -74.0)
LONDON = GeodeticLocation(51.5, -0.1)
BODIES = ["Sun", "Moon", "Mars", "Venus"]
POLICY = AspectPolicy(tier=0)


def _jd_ut1(dt: datetime) -> float:
    return utc_to_ut1(jd_from_datetime(dt))


def _snapshot(engine, zodiac="tropical", system=None):
    jd_ut1 = _jd_ut1(NATAL)
    offset = ayanamsa(jd_ut1, system) if zodiac == "sidereal" else None
    return geodetic_snapshot_at(jd_ut1, BODIES, reader=engine._reader, zodiac=zodiac,
                                ayanamsa_deg=offset, ayanamsa_system=system)


@pytest.mark.parametrize("zodiac,system", [("tropical", None), ("sidereal", "Lahiri")])
def test_houses_match_owner_on_the_engine_epoch(moira_engine, zodiac, system) -> None:
    jd_ut1 = _jd_ut1(NATAL)
    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, moira_engine._reader)
    expected = geodetic_house_chart(
        NEW_YORK, obliquity=true_obliquity(jd_tt), system=HouseSystem.PLACIDUS, zodiac=zodiac,
        ayanamsa_deg=ayanamsa(jd_ut1, system) if system else None, ayanamsa_system=system,
        jd_ut1=jd_ut1, jd_tt=jd_tt,
    )
    got = moira_engine.geodetic_houses(NEW_YORK, NATAL, HouseSystem.PLACIDUS,
                                       zodiac=zodiac, ayanamsa_system=system)
    assert got == expected


@pytest.mark.parametrize("zodiac,system", [("tropical", None), ("sidereal", "Lahiri")])
def test_overlay_matches_owner_and_shares_the_snapshot_epoch(moira_engine, zodiac, system) -> None:
    snapshot = _snapshot(moira_engine, zodiac, system)
    figure = geodetic_house_chart(
        NEW_YORK, obliquity=true_obliquity(snapshot.jd_tt), system=HouseSystem.EQUAL, zodiac=zodiac,
        ayanamsa_deg=snapshot.ayanamsa_deg if system else None, ayanamsa_system=system,
        source_frame=snapshot.source_frame, jd_ut1=snapshot.jd_ut1, jd_tt=snapshot.jd_tt,
    )
    expected = geodetic_natal_overlay(figure, snapshot, aspect_policy=POLICY)
    got = moira_engine.geodetic_overlay(NATAL, NEW_YORK, HouseSystem.EQUAL, aspect_policy=POLICY,
                                        bodies=BODIES, zodiac=zodiac, ayanamsa_system=system)
    assert got == expected
    assert got.house_chart.jd_tt == got.snapshot.jd_tt
    assert got.house_chart.jd_ut1 == got.snapshot.jd_ut1


def test_overlay_defaults_to_the_ten_planets(moira_engine) -> None:
    got = moira_engine.geodetic_overlay(NATAL, NEW_YORK, HouseSystem.EQUAL, aspect_policy=POLICY)
    assert [p.requested_name for p in got.snapshot.positions] == [
        "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    ]


def test_compare_matches_owner(moira_engine) -> None:
    places = [GeodeticNamedLocation("ny", NEW_YORK), GeodeticNamedLocation("ldn", LONDON)]
    snapshot = _snapshot(moira_engine)
    expected = compare_geodetic_locations(
        places, snapshot, obliquity=true_obliquity(snapshot.jd_tt), system=HouseSystem.EQUAL,
        aspect_policy=POLICY,
    )
    got = moira_engine.geodetic_compare(NATAL, places, HouseSystem.EQUAL, aspect_policy=POLICY, bodies=BODIES)
    assert got == expected
    assert [r.place.location_id for r in got.results] == ["ny", "ldn"]


def test_loci_match_owner(moira_engine) -> None:
    snapshot = _snapshot(moira_engine)
    expected = geodetic_angular_loci(snapshot, obliquity=true_obliquity(snapshot.jd_tt))
    got = moira_engine.geodetic_loci(NATAL, bodies=BODIES)
    assert got == expected
    assert got.complete


def test_transits_find_the_contact_built_into_the_reference(moira_engine) -> None:
    # Geodetic MC equals geographic longitude (0 Aries at Greenwich), so a place
    # on Mars's longitude has its MC exactly on Mars at the reference epoch.
    jd_ut1 = _jd_ut1(NATAL)
    mars = planet_at("Mars", jd_ut1, reader=moira_engine._reader).longitude
    place = GeodeticLocation(35.0, (mars + 180.0) % 360.0 - 180.0)
    start, end = NATAL - timedelta(days=2), NATAL + timedelta(days=2)
    policy = GeodeticTimingPolicy(step_days=0.5)

    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, moira_engine._reader)
    reference = GeodeticFixedReference(geodetic_chart_at_location(place, true_obliquity(jd_tt)), jd_ut1, jd_tt, ("MC",))
    expected = find_geodetic_transits(reference, "Mars", _jd_ut1(start), _jd_ut1(end), aspects=((0.0, 1.0),),
                                      policy=policy, reader=moira_engine._reader)
    got = moira_engine.geodetic_transits(place, NATAL, "Mars", start, end, aspects=((0.0, 1.0),),
                                         policy=policy, angles=("MC",))
    assert got == expected
    assert got.complete, got.reasons
    assert any(abs(event.jd_ut1 - jd_ut1) <= 2e-6 for event in got.events)


def test_uncertainty_delegates_to_owner(moira_engine) -> None:
    chart = geodetic_chart(-74.0, 40.7, 23.44)
    uncertainty = GeodeticInputUncertainty(0.1, 0.1, 0.0)
    policy = GeodeticDiagnosticPolicy(1e-3)
    assert moira_engine.geodetic_uncertainty(chart, uncertainty, policy=policy) == diagnose_geodetic_uncertainty(
        chart, uncertainty, policy=policy,
    )


@pytest.mark.parametrize("kwargs,message", [
    ({"zodiac": "sidereal"}, "ayanamsa_system is required"),
    ({"ayanamsa_system": "Lahiri"}, "does not take an ayanamsa_system"),
])
def test_lane_law_is_enforced_before_computation(moira_engine, kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        moira_engine.geodetic_houses(NEW_YORK, NATAL, HouseSystem.EQUAL, **kwargs)
    with pytest.raises(ValueError, match=message):
        moira_engine.geodetic_loci(NATAL, bodies=BODIES, **kwargs)


def test_geocentric_latitude_is_refused_for_timing(moira_engine) -> None:
    place = GeodeticLocation(40.7, -74.0, latitude_kind="geocentric")
    with pytest.raises(ValueError, match="geocentric latitude"):
        moira_engine.geodetic_transits(place, NATAL, "Mars", NATAL, NATAL + timedelta(days=1),
                                       aspects=((0.0, 1.0),), policy=GeodeticTimingPolicy(step_days=0.5))
