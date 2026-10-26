"""Source checkpoints, branch invariance and independent prescribed-ellipse proofs."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import math
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.hypothetical as h
from moira.julian import julian_day
from moira.orbits import OrbitalCenter, OrbitalFrame, OrbitShape


def _policy(epoch=2451545.0):
    return h.HistoricalRealization(epoch, h.ConventionClock.TT, 0.0, 365.25)


def test_arta_returns_node_cross_at_apogee_opposition():
    result = h.arta_four_points(17, 31, 211, input_model="supplied_mean", frame="common")
    assert result.longitudes == (17, 107, 197, 287)
    assert result.symbol == "\u2bdf"
    assert not hasattr(result, "longitude")


@pytest.mark.parametrize("node_turn,lunar_turn,solar_turn", [
    (1, 0, 0), (0, 1, 0), (0, 0, -1), (-2, 3, 7), (100, -100, 100),
])
def test_arta_set_is_invariant_under_independent_angle_lifts(node_turn, lunar_turn, solar_turn):
    args = dict(input_model="same_model", frame="same_frame")
    expected = h.arta_four_points(12.5, 331.25, 102.75, **args).longitudes
    actual = h.arta_four_points(12.5+360*node_turn, 331.25+360*lunar_turn,
                               102.75+360*solar_turn, **args).longitudes
    assert actual == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("year_days", [365.25, 365.2425])
def test_selena_returns_to_supplied_anchor_and_has_no_physical_radius(year_days):
    args = dict(anchor_jd=2451545, anchor_longitude=237.5, year_days=year_days,
                timescale=h.ConventionClock.TT, frame="mean_ecliptic_of_date")
    anchor = h.selena_seven_year_at(2451545, **args)
    assert anchor.longitude == 237.5
    assert h.selena_seven_year_at(2451545+7*year_days, **args).longitude == pytest.approx(237.5, abs=1e-9)
    assert h.selena_seven_year_at(2451545+3.5*year_days, **args).longitude == pytest.approx(57.5, abs=1e-9)
    assert not hasattr(anchor, "distance_au")
    assert dict(anchor.parameters)["anchor_longitude"] == 237.5


def test_abramov_source_anchor_and_distinct_time_rules():
    args = dict(timescale="TT", frame="caller_selected_source_frame")
    jan = julian_day(1900, 1, 1)
    for rule in h.ProserpinaRule:
        assert h.abramov_proserpina_at(jan, rule=rule, **args).longitude == 170.73
    # Source annual increment is 0.5105 degrees, not 365 * 0.0014.
    before = h.abramov_proserpina_at(julian_day(1901, 1, 1)-1e-6, rule=h.ProserpinaRule.CALENDAR, **args)
    after = h.abramov_proserpina_at(julian_day(1901, 1, 1), rule=h.ProserpinaRule.CALENDAR, **args)
    assert before.longitude-after.longitude == pytest.approx(0.0005, abs=2e-9)
    continuous = h.abramov_proserpina_at(jan+365.25, rule=h.ProserpinaRule.JULIAN_YEAR, **args)
    assert continuous.longitude == pytest.approx(171.2405)
    assert after.symbol == "\u2bd8" and after.center == "heliocentric"


def test_harrington_retains_printed_nominal_period_and_exact_ellipse_extrema():
    epoch = julian_day(1789, 8, 6)
    orbit = h.harrington_1988_orbit(_policy(epoch))
    period = 1019*365.25
    assert orbit.mean_anomaly_rate_deg_per_day*period == pytest.approx(360)
    first = h.hypothetical_orbit_at(orbit, epoch, frame=OrbitalFrame.MEAN_ECLIPTIC_OF_DATE)
    opposite = h.hypothetical_orbit_at(orbit, epoch+period/2, frame=OrbitalFrame.J2000_ECLIPTIC)
    assert first.distance_au == pytest.approx(101.2*(1-0.411), rel=2e-15)
    assert opposite.distance_au == pytest.approx(101.2*(1+0.411), rel=2e-15)
    assert first.source_orbit is orbit
    assert orbit.center is OrbitalCenter.SUN


@pytest.mark.parametrize("eccentricity", [0, 0.3, 0.95, 0.9999])
@pytest.mark.parametrize("mean_anomaly", [0, 3, 90, 179.9, -179.9])
def test_eccentric_anomaly_solver_satisfies_independent_kepler_equation(eccentricity, mean_anomaly):
    epoch = julian_day(1789, 8, 6)
    orbit = replace(h.harrington_1988_orbit(_policy(epoch)), semi_major_axis_au=2.0,
                    eccentricity=eccentricity, inclination_deg=0, ascending_node_deg=0,
                    perihelion_longitude_deg=0, mean_anomaly_deg=mean_anomaly)
    result = h.hypothetical_orbit_at(orbit, epoch, frame=OrbitalFrame.MEAN_ECLIPTIC_OF_DATE)
    x, y, z = result.vector_au
    cosE = x/2 + eccentricity
    sinE = y/(2*math.sqrt(1-eccentricity**2))
    E = math.atan2(sinE, cosE)
    assert z == pytest.approx(0, abs=1e-14)
    assert cosE*cosE+sinE*sinE == pytest.approx(1, abs=2e-12)
    assert E-eccentricity*math.sin(E) == pytest.approx(math.radians(mean_anomaly), abs=2e-12)


def test_adams_original_second_hypothesis_ratios_and_phase():
    orbit = h.adams_1846_orbit(_policy(), uranus_semimajor_axis_au=19.18,
                               uranus_sidereal_period_days=30688)
    assert 19.18/orbit.semi_major_axis_au == pytest.approx(0.515)
    assert orbit.eccentricity == 0.120615
    assert orbit.mean_anomaly_deg+orbit.perihelion_longitude_deg == pytest.approx(323+2/60)
    assert orbit.mean_anomaly_rate_deg_per_day/(360/30688) == pytest.approx(0.515**1.5)
    assert orbit.inclination_deg == 0


def test_leverrier_contemporary_transcription_keeps_one_equinox():
    orbit = h.leverrier_1846_orbit(_policy())
    # Gould p.21: mean longitude 1847 Jan 1 = 318d47m04s.
    assert orbit.mean_anomaly_deg+orbit.perihelion_longitude_deg == pytest.approx(318+47/60+4/3600)
    assert orbit.mean_anomaly_rate_deg_per_day*217.387*365.25 == pytest.approx(360)
    assert orbit.semi_major_axis_au == 36.1539 and orbit.eccentricity == 0.10761


def test_polar_orbit_withholds_undefined_longitude():
    epoch = julian_day(1789, 8, 6)
    orbit = replace(h.harrington_1988_orbit(_policy(epoch)), inclination_deg=90,
                    ascending_node_deg=0, perihelion_longitude_deg=90)
    result = h.hypothetical_orbit_at(orbit, epoch, frame=OrbitalFrame.MEAN_ECLIPTIC_OF_DATE)
    assert result.latitude == 90.0
    assert result.longitude is None


def test_calendar_approximation_rejects_epochs_outside_safe_native_calendar_domain():
    with pytest.raises(ValueError, match="long-term epoch interval"):
        h.abramov_proserpina_at(1e13, rule="abramov_calendar", timescale="TT", frame="selected")


def test_koch_quoted_mean_longitude_perigee_and_node_constraints():
    orbit = h.koch_waldemath_orbit(source_equinox_jd_tt=2414291, berlin_local_minus_ut1_hours=0)
    assert orbit.mean_anomaly_deg+orbit.perihelion_longitude_deg == pytest.approx(214.73)
    perigee = julian_day(1898, 4, 8, 12)
    assert orbit.mean_anomaly_deg+(perigee-orbit.epoch_jd)*orbit.mean_anomaly_rate_deg_per_day == pytest.approx(0)
    node_epoch = julian_day(1898, 2, 3, 18+27/60)
    node = orbit.ascending_node_deg+(node_epoch-orbit.epoch_jd)*orbit.node_rate_deg_per_day
    assert node % 360 == pytest.approx(135+13/60)
    assert orbit.mean_anomaly_rate_deg_per_day+orbit.perihelion_rate_deg_per_day == pytest.approx(360/119.227434)
    assert orbit.mean_anomaly_rate_deg_per_day+orbit.perihelion_rate_deg_per_day-orbit.node_rate_deg_per_day == pytest.approx(360/118.003952)
    assert orbit.center is OrbitalCenter.EARTH
    local = h.koch_waldemath_orbit(source_equinox_jd_tt=2414291, berlin_local_minus_ut1_hours=0.893333333)
    assert local.epoch_jd == pytest.approx(orbit.epoch_jd-0.893333333/24)
    assert local.perihelion_longitude_deg != orbit.perihelion_longitude_deg


def test_weston_selects_stahl_revision_and_keeps_prescribed_nodal_motion():
    orbit = h.weston_stahl_vulcan_orbit(source_equinox_jd_tt=2415020, year_days=365.25)
    assert orbit.model == "weston_stahl_1968"
    assert orbit.epoch_jd == 2415020
    assert orbit.mean_anomaly_deg+orbit.perihelion_longitude_deg == pytest.approx(265+34/60+27/3600)
    assert orbit.mean_anomaly_rate_deg_per_day == pytest.approx(19+22/60+17.1138/3600)
    assert orbit.node_rate_deg_per_day*365.25 == pytest.approx(-(18+42/60+21/3600))
    assert orbit.mean_anomaly_rate_deg_per_day != pytest.approx(0.9856076686/0.13744**1.5, abs=1e-4)
    # Stahl p.21-22 worked example uses astronomical time 8h39m = UT1 20h39m.
    epoch = julian_day(1907, 6, 25, 20+39/60)
    mean_longitude = (orbit.mean_anomaly_deg+orbit.perihelion_longitude_deg
                      +orbit.mean_anomaly_rate_deg_per_day*(epoch-orbit.epoch_jd)) % 360
    assert mean_longitude == pytest.approx(275+16/60+36.5819/3600, abs=0.5/3600)


def test_arta_uses_earth_pericenter_as_geocentric_solar_apogee(monkeypatch):
    calls = []
    common = dict(frame=OrbitalFrame.J2000_ECLIPTIC, shape=OrbitShape.ELLIPTIC,
                  epoch_tt=2451545.0, epoch_tdb=2451545.0)
    lunar = SimpleNamespace(lon_ascending_node_deg=17, pericenter_ecliptic_lon_deg=211, **common)
    earth = SimpleNamespace(pericenter_ecliptic_lon_deg=211, **common)

    def elements(body, jd, **kwargs):
        calls.append((body, jd, kwargs))
        return lunar if body == "Moon" else earth

    monkeypatch.setattr(h, "osculating_elements", elements)
    reader = object()
    result = h.arta_osculating_set_at(2451545, frame=OrbitalFrame.J2000_ECLIPTIC, reader=reader)
    assert result.points.longitudes == (17, 107, 197, 287)
    assert result.lunar_elements is lunar and result.earth_elements is earth
    assert [c[2]["center"] for c in calls] == [OrbitalCenter.EARTH, OrbitalCenter.SUN]
    assert all(c[2]["reader"] is reader for c in calls)
    lunar.lon_ascending_node_deg = None
    with pytest.raises(ValueError, match="requires defined"):
        h.arta_osculating_set_at(2451545, frame=OrbitalFrame.J2000_ECLIPTIC, reader=reader)
    lunar.shape = OrbitShape.HYPERBOLIC
    with pytest.raises(ValueError, match="elliptic"):
        h.arta_osculating_set_at(2451545, frame=OrbitalFrame.J2000_ECLIPTIC, reader=reader)
    lunar.shape = OrbitShape.ELLIPTIC
    earth.epoch_tt += 0.01
    with pytest.raises(ValueError, match="same bound clock"):
        h.arta_osculating_set_at(2451545, frame=OrbitalFrame.J2000_ECLIPTIC, reader=reader)


@pytest.mark.parametrize("bad", [True, None, "2451545", math.nan, math.inf, 1e308])
def test_new_inputs_fail_closed(bad):
    if bad != 1e308:  # finite angles can always be reduced modulo a full turn
        with pytest.raises(ValueError):
            h.arta_four_points(bad, 2, 3, input_model="x", frame="x")
    with pytest.raises(ValueError):
        h.selena_seven_year_at(bad, anchor_jd=2451545, anchor_longitude=0,
                               year_days=365.25, timescale="TT", frame="x")
    with pytest.raises(ValueError):
        h.abramov_proserpina_at(bad, rule="abramov_calendar", timescale="TT", frame="x")


def test_public_exports_and_clock_conversion(monkeypatch):
    for name in h.__all__:
        assert getattr(moira, name) is getattr(h, name)
        assert getattr(facade, name) is getattr(h, name)
        assert name in moira.__all__ and name in facade.__all__
    assert len(h.hypothetical_catalog()) == 11
    calls = []
    monkeypatch.setattr(facade, "jd_from_datetime", lambda dt: 1)
    monkeypatch.setattr(facade, "utc_to_tt", lambda jd: 2)
    monkeypatch.setattr(facade, "utc_to_ut1", lambda jd: 3)
    monkeypatch.setattr(facade, "abramov_proserpina_at", lambda *a, **k: calls.append((a,k)))
    owner = SimpleNamespace()
    dt = datetime(2000, 1, 1, tzinfo=timezone.utc)
    for scale, expected in [("TT", 2), ("UT1", 3)]:
        moira.Moira.abramov_proserpina(owner, dt, rule="abramov_calendar", timescale=scale, frame="supplied")
        assert calls[-1][0] == (expected,)


def test_planet_nine_is_an_explicit_scenario_with_source_extrema():
    peri = h.fienga_2016_planet_nine_scenario(0, source_equinox_jd_tt=2451545)
    apo = h.fienga_2016_planet_nine_scenario(180, source_equinox_jd_tt=2451545)
    assert peri.distance_au == pytest.approx(280)
    assert apo.distance_au == pytest.approx(1120)
    assert math.hypot(*peri.vector_au) == pytest.approx(280)
    assert peri.vector_au[2]/280 == pytest.approx(0.25)
    assert not hasattr(peri, "epoch_jd")
    assert h.fienga_2016_planet_nine_scenario(360, source_equinox_jd_tt=2451545) == peri
