"""Derived-point admission against actual DE441 and frozen Horizons elements."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from moira._ephemeris_time import _bind_ephemeris_time
from moira.derived_points import (
    baker_vulcan_at, orbital_second_focus, osculating_priapus,
)
from moira.julian import jd_from_datetime, tdb_to_tt, utc_to_ut1
from moira.nodes import true_lilith_with_truth
from moira.orbits import OrbitalCenter, OrbitalFrame
from moira.planets import planet_at

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris]

_HOLDOUT = json.loads((Path(__file__).parents[1] / "fixtures" /
                       "horizons_orbital_elements_holdout.json").read_text(encoding="utf-8"))["records"]


def _ut1_at_tdb(epoch_tdb, reader):
    jd_ut = tdb_to_tt(epoch_tdb)
    for _ in range(8):
        residual = epoch_tdb - _bind_ephemeris_time(jd_ut, reader).epoch_tdb
        if abs(residual) <= math.ulp(epoch_tdb):
            return jd_ut
        jd_ut += residual
    raise AssertionError("could not bind frozen Horizons TDB epoch")


@pytest.mark.parametrize("record", _HOLDOUT, ids=lambda r: r["case_key"])
def test_second_focus_against_frozen_horizons_geometry(record, planetary_reader):
    jd_ut = _ut1_at_tdb(record["jd_tdb"], planetary_reader)
    actual = orbital_second_focus(record["body_naif_id"], jd_ut,
                                  center=OrbitalCenter.SUN, frame=OrbitalFrame.J2000_ECLIPTIC,
                                  reader=planetary_reader)
    source = record["elements_j2000_ecliptic_au_day"]
    a, e = source["semi_major_axis_au"], source["eccentricity"]
    node, peri, inc = map(math.radians, (source["lon_ascending_node_deg"],
                                       source["arg_perihelion_deg"], source["inclination_deg"]))
    # Independently rotate the focus of an ellipse in its own orbital plane.
    p = (math.cos(node)*math.cos(peri)-math.sin(node)*math.sin(peri)*math.cos(inc),
         math.sin(node)*math.cos(peri)+math.cos(node)*math.sin(peri)*math.cos(inc),
         math.sin(peri)*math.sin(inc))
    expected = tuple(-2*a*e*component for component in p)
    assert actual.vector_au == pytest.approx(expected, abs=2e-12)
    assert actual.source_elements.body.naif_id == record["body_naif_id"]
    assert actual.source_elements.epoch_tdb == pytest.approx(record["jd_tdb"], abs=1e-9)
    assert actual.source_elements.provenance.state_source.legs


@pytest.mark.parametrize("jd_ut", [2451545.0, 2461199.9375])
def test_lunar_perigee_preserves_parent_truth_and_measured_rate(planetary_reader, jd_ut):
    perigee = osculating_priapus(jd_ut, reader=planetary_reader)
    apogee = true_lilith_with_truth(jd_ut, reader=planetary_reader)
    assert (perigee.longitude - apogee.result.longitude) % 360 == pytest.approx(180)
    assert perigee.source_apogee_truth == apogee.truth
    step = 0.002
    before = osculating_priapus(jd_ut-step, reader=planetary_reader).longitude
    after = osculating_priapus(jd_ut+step, reader=planetary_reader).longitude
    measured_rate = ((after-before+180) % 360-180)/(2*step)
    assert perigee.speed == pytest.approx(measured_rate, abs=2e-5)


def test_baker_dated_inputs_and_facade_use_owned_reader(moira_engine):
    dt = datetime(2026, 10, 26, tzinfo=timezone.utc)
    jd_ut = utc_to_ut1(jd_from_datetime(dt))
    reader = moira_engine._reader
    result = baker_vulcan_at(jd_ut, reader=reader)
    sun = planet_at("Sun", jd_ut, reader=reader).longitude
    mercury = planet_at("Mercury", jd_ut, reader=reader).longitude
    assert result.sun_longitude == sun and result.mercury_longitude == mercury
    assert min((result.longitude-sun) % 360, (sun-result.longitude) % 360) == pytest.approx(
        max(min((mercury-sun) % 360, (sun-mercury) % 360)-3, 0), abs=1e-12,
    )
    bound = _bind_ephemeris_time(jd_ut, reader)
    assert result.epoch_tdb == bound.epoch_tdb
    assert result.kernel_identity == bound.identity.summary_label
    assert moira_engine.baker_vulcan(dt) == result
    assert moira_engine.osculating_priapus(dt) == osculating_priapus(jd_ut, reader=reader)
    assert moira_engine.orbital_second_focus(
        "Moon", dt, center="EARTH", frame="TRUE_ECLIPTIC_OF_DATE",
    ) == orbital_second_focus("Moon", jd_ut, center=OrbitalCenter.EARTH,
                             frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE, reader=reader)
