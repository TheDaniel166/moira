"""Branch boundaries and independent ellipse geometry for derived points."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira
import moira.derived_points as points
import moira.facade as facade
from moira.nodes import mean_lilith
from moira.orbits import OrbitalCenter, OrbitalFrame, OrbitalInputError, OrbitShape


@pytest.mark.parametrize("sun,mercury,expected", [
    (100, 120, 117), (100, 80, 83), (359, 10, 7), (1, 350, 353),
    (100, 100, 100), (100, 102, 100), (100, 97, 100), (100, 103, 100),
    (100, 103.001, 100.001), (100, 96.999, 99.999),
    (-1, 370, 7), (721, -10, 353),
])
def test_baker_documented_rule(sun, mercury, expected):
    result = points.baker_vulcan_from_longitudes(sun, mercury)
    assert result.longitude == pytest.approx(expected, abs=1e-12)
    assert result.kind == "symbolic_longitude"
    assert result.jd_ut is None and result.kernel_identity is None
    assert not hasattr(result, "distance_au")
    assert not hasattr(result, "speed")


@pytest.mark.parametrize("shift", [-720, -1, 0, 89, 359, 720])
def test_baker_is_covariant_under_zodiac_rotation(shift):
    for sun, mercury in [(0, 20), (0, -20), (0, 2)]:
        baseline = points.baker_vulcan_from_longitudes(sun, mercury)
        rotated = points.baker_vulcan_from_longitudes(sun + shift, mercury + shift)
        assert rotated.longitude == pytest.approx((baseline.longitude + shift) % 360)


@pytest.mark.parametrize("sun,mercury", [(0, 180), (180, 0), (10, 550)])
def test_baker_rejects_ambiguous_antipodal_arc(sun, mercury):
    with pytest.raises(ValueError, match="Antipodal"):
        points.baker_vulcan_from_longitudes(sun, mercury)


@pytest.mark.parametrize("bad", [True, False, math.nan, math.inf, -math.inf, "0", None, 10**400])
def test_symbolic_and_lunar_inputs_reject_nonfinite_or_coerced_values(bad):
    for call in [
        lambda: points.baker_vulcan_from_longitudes(bad, 0),
        lambda: points.baker_vulcan_from_longitudes(0, bad),
        lambda: points.baker_vulcan_at(bad),
        lambda: points.mean_priapus(bad),
        lambda: points.osculating_priapus(bad),
    ]:
        with pytest.raises(ValueError, match="finite real"):
            call()


@pytest.mark.parametrize("jd", [2415020.5, 2451545.0, 2461199.9375, 2488069.5])
@pytest.mark.parametrize("nutation", [False, True])
def test_mean_perigee_remains_antipodal_in_selected_frame(jd, nutation):
    result = points.mean_priapus(jd, nutation=nutation)
    apogee = mean_lilith(jd, nutation=nutation)
    assert (result.longitude - apogee.longitude) % 360 == pytest.approx(180)
    assert result.speed == apogee.speed
    assert "excluding_nutation_derivative" in result.speed_method
    assert result.source_apogee_truth is None
    assert result.frame.startswith("true_" if nutation else "mean_")


def test_mean_perigee_rejects_implicit_frame_coercion():
    with pytest.raises(ValueError, match="Boolean"):
        points.mean_priapus(2451545, nutation="false")


def _elements(a=2.0, e=0.4, p=(1.0, 0.0, 0.0), **overrides):
    """Minimal geometric input; full typed source receipts are exercised with kernels."""
    values = dict(
        shape=OrbitShape.ELLIPTIC, semi_major_axis_au=a, eccentricity=e,
        pericenter_ecliptic_lon_deg=math.degrees(math.atan2(p[1], p[0])) % 360,
        pericenter_ecliptic_lat_deg=math.degrees(math.atan2(p[2], math.hypot(*p[:2]))),
        provenance=SimpleNamespace(singularity_thresholds=SimpleNamespace(
            circular_e_tolerance=1e-10,
        )),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("node,peri,inc", [(0, 0, 0), (359, 83, 37), (42, 163, 123), (85, 30, 90)])
def test_second_focus_satisfies_independent_ellipse_distance_sum(node, peri, inc):
    node, peri, inc = map(math.radians, (node, peri, inc))
    cO, sO, cw, sw, ci, si = (
        math.cos(node), math.sin(node), math.cos(peri), math.sin(peri),
        math.cos(inc), math.sin(inc),
    )
    p = (cO*cw-sO*sw*ci, sO*cw+cO*sw*ci, sw*si)
    q = (-cO*sw-sO*cw*ci, -sO*sw+cO*cw*ci, cw*si)
    a, e = 2.3, 0.61
    source = _elements(a, e, p)
    focus = points.second_focus_from_elements(source)
    assert focus.source_elements is source
    assert focus.status is points.SecondFocusStatus.DEFINED
    assert math.dist(focus.vector_au, (0, 0, 0)) == pytest.approx(2*a*e)
    b = a * math.sqrt(1-e*e)
    for anomaly in range(0, 360, 13):
        E = math.radians(anomaly)
        position = tuple(a*(math.cos(E)-e)*p[k] + b*math.sin(E)*q[k] for k in range(3))
        distance_sum = math.dist(position, (0, 0, 0)) + math.dist(position, focus.vector_au)
        assert distance_sum == pytest.approx(2*a, abs=1e-13)
    assert focus.distance_au != pytest.approx(a*(1+e))  # apocenter is a different point


@pytest.mark.parametrize("e,status,vector", [
    (0, points.SecondFocusStatus.COINCIDENT_FOCI, (0, 0, 0)),
    (1e-12, points.SecondFocusStatus.CIRCULAR_DIRECTION_UNDEFINED, None),
])
def test_circular_policy_withholds_undefined_angles(e, status, vector):
    result = points.second_focus_from_elements(_elements(
        e=e, pericenter_ecliptic_lon_deg=None, pericenter_ecliptic_lat_deg=None,
    ))
    assert result.status is status
    assert result.vector_au == vector
    assert result.longitude is None and result.latitude is None
    assert result.distance_au == pytest.approx(4*e, abs=1e-24)


@pytest.mark.parametrize("shape,e,a", [(OrbitShape.PARABOLIC, 1, None), (OrbitShape.HYPERBOLIC, 1.5, -2)])
def test_nonelliptic_outcome_has_no_elliptic_focus(shape, e, a):
    result = points.second_focus_from_elements(_elements(a=a, e=e, shape=shape))
    assert result.status is points.SecondFocusStatus.NON_ELLIPTIC
    assert result.vector_au is None and result.distance_au is None
    assert result.longitude is None and result.latitude is None


@pytest.mark.parametrize("latitude", [-90.0, 90.0])
def test_polar_focus_has_vector_but_no_spherical_longitude(latitude):
    result = points.second_focus_from_elements(_elements(
        pericenter_ecliptic_lat_deg=latitude,
    ))
    assert result.vector_au == (0, 0, -math.copysign(1.6, latitude))
    assert result.longitude is None and result.latitude == -latitude


@pytest.mark.parametrize("overrides", [
    {"semi_major_axis_au": None}, {"semi_major_axis_au": math.inf},
    {"eccentricity": math.nan}, {"eccentricity": 1},
    {"pericenter_ecliptic_lon_deg": None}, {"pericenter_ecliptic_lat_deg": math.inf},
    {"semi_major_axis_au": 1e308, "eccentricity": 0.9},
])
def test_inconsistent_supplied_elements_fail_closed(overrides):
    with pytest.raises(ValueError):
        points.second_focus_from_elements(_elements(**overrides))


def test_second_focus_preserves_strict_core_error_and_explicit_policy(monkeypatch):
    calls = []
    error = OrbitalInputError("body", True)
    reader = object()

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise error

    monkeypatch.setattr(points, "osculating_elements", fail)
    with pytest.raises(OrbitalInputError) as caught:
        points.orbital_second_focus(True, 2451545, center=OrbitalCenter.EARTH,
                                   frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE, reader=reader)
    assert caught.value is error
    assert calls == [((True, 2451545), dict(center=OrbitalCenter.EARTH,
                    frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE, reader=reader))]


@pytest.mark.parametrize("method,entrypoint,extra", [
    ("baker_vulcan", "baker_vulcan_at", {}),
    ("mean_priapus", "mean_priapus", {"nutation": False}),
    ("osculating_priapus", "osculating_priapus", {}),
    ("orbital_second_focus", "orbital_second_focus", {"center": "EARTH", "frame": "J2000_ECLIPTIC"}),
])
def test_facade_uses_ut1_and_owned_reader(monkeypatch, method, entrypoint, extra):
    calls = []
    sentinel = object()
    owner = SimpleNamespace(_reader=object())
    dt = datetime(2026, 10, 26, tzinfo=timezone.utc)
    monkeypatch.setattr(facade, entrypoint, lambda *args, **kw: calls.append((args, kw)) or sentinel)
    monkeypatch.setattr(facade, "jd_from_datetime", lambda dt: 2451545.0)
    monkeypatch.setattr(facade, "utc_to_ut1", lambda jd: jd + 0.25)
    args = (owner, "Moon", dt) if method == "orbital_second_focus" else (owner, dt)
    assert getattr(moira.Moira, method)(*args, **extra) is sentinel
    expected_args = ("Moon", 2451545.25) if method == "orbital_second_focus" else (2451545.25,)
    expected_kw = dict(extra)
    if method != "mean_priapus":
        expected_kw["reader"] = owner._reader
    assert calls == [(expected_args, expected_kw)]


def test_public_discovery_keeps_physical_and_uranian_identities_separate():
    assert {point.id for point in points.derived_point_catalog()} == {
        "baker_vulcan", "mean_priapus", "osculating_priapus", "orbital_second_focus",
    }
    for name in points.__all__:
        assert name in moira.__all__ and name in facade.__all__
        assert getattr(moira, name) is getattr(points, name)
        assert getattr(facade, name) is getattr(points, name)
    from moira.uranian import list_uranian
    assert "Vulkanus" in list_uranian()
    assert "Baker Vulcan" not in list_uranian()
