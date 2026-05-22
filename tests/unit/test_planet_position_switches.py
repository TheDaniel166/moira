"""
Unit tests for planet_at() position switches.

Covers:
    - apparent, aberration, grav_deflection, nutation, center, frame kwargs
    - CartesianPosition result type
    - sky_position_at correction switches
    - all_planets_at switch propagation

Tests marked @pytest.mark.requires_ephemeris need de441.bsp.
Tests without that mark are pure-unit (no kernel required).
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
import pytest

import moira.planets as planets_module
from moira.planets import (
    CartesianPosition,
    HeliocentricData,
    PlanetData,
    all_planets_at,
    planet_at,
    sky_position_at,
)
from moira.constants import Body

# J2000.0 epoch in UT — stable reference for all ephemeris tests.
_JD_J2000 = 2451545.0


# ---------------------------------------------------------------------------
# Pure-unit: input validation (no ephemeris required)
# ---------------------------------------------------------------------------

def test_planet_at_invalid_center_raises():
    with pytest.raises(ValueError, match="center"):
        planet_at(Body.MARS, _JD_J2000, center="heliocentric")


def test_planet_at_invalid_frame_raises():
    with pytest.raises(ValueError, match="frame"):
        planet_at(Body.MARS, _JD_J2000, frame="spherical")


def test_cartesian_position_repr():
    pos = CartesianPosition(name="Mars", x=1.0, y=2.0, z=3.0, center="geocentric")
    r = repr(pos)
    assert "Mars" in r
    assert "geocentric" in r
    assert "x=" in r


def test_cartesian_position_fields():
    pos = CartesianPosition(name="Venus", x=100.0, y=200.0, z=-50.0, center="barycentric")
    assert pos.name == "Venus"
    assert pos.x == 100.0
    assert pos.y == 200.0
    assert pos.z == -50.0
    assert pos.center == "barycentric"


def test_sky_position_is_frozen():
    pos = planets_module.SkyPosition(
        name="Mars",
        right_ascension=10.0,
        declination=20.0,
        azimuth=30.0,
        altitude=40.0,
        distance=50.0,
    )
    with pytest.raises(FrozenInstanceError):
        pos.altitude = 41.0  # type: ignore[misc]


def test_cartesian_position_is_frozen():
    pos = CartesianPosition(name="Mars", x=1.0, y=2.0, z=3.0, center="geocentric")
    with pytest.raises(FrozenInstanceError):
        pos.x = 4.0  # type: ignore[misc]


def test_heliocentric_data_is_frozen():
    pos = HeliocentricData(
        name="Mars",
        longitude=15.0,
        latitude=1.0,
        distance=2.0,
        speed=0.5,
        retrograde=False,
    )
    with pytest.raises(FrozenInstanceError):
        pos.longitude = 16.0  # type: ignore[misc]


def test_npe_all_planets_mode_is_admitted_requires_exact_surface():
    class _DummyHandle:
        def batch_segment_position_and_velocity(self, specs, jd):
            raise AssertionError("should not run in predicate test")

    class _DummyKernel:
        _handle = _DummyHandle()

    class _DummyReader:
        _kernel = _DummyKernel()

    admitted = planets_module._npe_all_planets_mode_is_admitted(
        bodies=[Body.SUN, Body.MOON, Body.MARS],
        reader=_DummyReader(),
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
        center="geocentric",
        observer_lat=None,
        observer_lon=None,
        observer_elev_m=0.0,
        lst_deg=None,
        delta_t_policy=None,
    )
    assert admitted is False, "exact SpkReader ownership is required for NPE admission"


def test_all_planets_at_returns_native_admitted_result_when_helper_supplies_one(monkeypatch: pytest.MonkeyPatch):
    sentinel = {
        Body.SUN: PlanetData(
            name=Body.SUN,
            longitude=1.0,
            latitude=2.0,
            distance=3.0,
            speed=4.0,
            retrograde=False,
        )
    }

    calls: list[tuple[float, list[str]]] = []

    def _fake_native_helper(jd_ut: float, bodies: list[str], **kwargs):
        calls.append((jd_ut, list(bodies)))
        return sentinel

    monkeypatch.setattr(planets_module, "_native_all_planets_admitted", _fake_native_helper)

    class _DummyReader:
        pass

    result = all_planets_at(_JD_J2000, bodies=[Body.SUN], reader=_DummyReader())
    assert result is sentinel
    assert calls == [(_JD_J2000, [Body.SUN])]


def test_native_all_planets_admitted_uses_native_planetary_evaluator_when_available(monkeypatch: pytest.MonkeyPatch):
    class _DummyEvaluator:
        def __init__(self, handle):
            self.handle = handle
            self.calls = []

        def evaluate_all_planets_apparent_geocentric_ecliptic(
            self,
            bodies,
            public_specs,
            body_specs,
            jd_tt,
            obliquity_deg,
            rotation_matrix,
        ):
            self.calls.append((tuple(bodies), jd_tt, obliquity_deg, rotation_matrix))
            return [
                (Body.SUN, 1.0, 2.0, 3.0, 4.0, False),
                (Body.MARS, 5.0, 6.0, 7.0, -8.0, True),
            ]

    dummy_native = type("DummyNative", (), {"NativePlanetaryEvaluator": _DummyEvaluator})()
    monkeypatch.setattr(planets_module, "_moira_native", dummy_native)
    monkeypatch.setattr(planets_module, "_npe_all_planets_mode_is_admitted", lambda **kwargs: True)
    monkeypatch.setattr(planets_module, "_npe_public_route_segment_specs", lambda reader, jd_tt: [(1, 2, 3)])
    monkeypatch.setattr(
        planets_module,
        "_npe_body_route_segment_specs",
        lambda reader, jd_tt: {
            Body.SUN: ((1, 2, 3),),
            Body.MARS: ((4, 5, 6),),
        },
    )
    monkeypatch.setattr(planets_module, "mean_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr(planets_module, "_nutation", lambda jd_tt: (0.1, 0.2))
    monkeypatch.setattr(
        planets_module,
        "_compose_rotation_matrix",
        lambda *args, **kwargs: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    )

    class _DummyHandle:
        pass

    class _DummyKernel:
        def __init__(self):
            self._handle = _DummyHandle()

    class _DummyReader:
        def __init__(self):
            self._kernel = _DummyKernel()

    reader = _DummyReader()
    result = planets_module._native_all_planets_admitted(
        _JD_J2000,
        [Body.SUN, Body.MARS],
        reader=reader,
        jd_tt=_JD_J2000 + 0.1,
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
        center="geocentric",
        observer_lat=None,
        observer_lon=None,
        observer_elev_m=0.0,
        lst_deg=None,
        delta_t_policy=None,
    )

    assert result is not None
    assert result[Body.SUN].longitude == 1.0
    assert result[Body.MARS].speed == -8.0
    assert result[Body.MARS].retrograde is True
    assert hasattr(reader._kernel, "_planetary_evaluator")


def test_all_planets_at_falls_back_to_python_route_when_native_helper_declines(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(planets_module, "_native_all_planets_admitted", lambda *args, **kwargs: None)

    class _DummyContext:
        obliquity = 23.4
        dpsi_deg = 0.0
        deps_deg = 0.0
        rot_mat = None
        vector_cache = {}

    monkeypatch.setattr(planets_module, "_build_apparent_context", lambda *args, **kwargs: _DummyContext())

    calls: list[str] = []

    def _fake_core(body: str, jd_ut: float, **kwargs):
        calls.append(body)
        return PlanetData(
            name=body,
            longitude=10.0,
            latitude=0.0,
            distance=1.0,
            speed=0.1,
            retrograde=False,
        )

    monkeypatch.setattr(planets_module, "_planet_at_core", _fake_core)

    class _DummyReader:
        pass

    result = all_planets_at(_JD_J2000, bodies=[Body.SUN, Body.MARS], reader=_DummyReader(), center="barycentric")
    assert list(result) == [Body.SUN, Body.MARS]
    assert calls == [Body.SUN, Body.MARS]


@pytest.mark.requires_ephemeris
def test_all_planets_at_native_evaluator_matches_python_fallback():
    if planets_module._moira_native is None or not hasattr(planets_module._moira_native, "NativePlanetaryEvaluator"):
        pytest.skip("native planetary evaluator is unavailable")

    bodies = [Body.SUN, Body.MOON, Body.MARS, Body.JUPITER]
    native_bulk = all_planets_at(_JD_J2000, bodies=bodies)

    original = planets_module._get_native_planetary_evaluator
    planets_module._get_native_planetary_evaluator = lambda reader: None
    try:
        python_bulk = all_planets_at(_JD_J2000, bodies=bodies)
    finally:
        planets_module._get_native_planetary_evaluator = original

    for body in bodies:
        assert abs(native_bulk[body].longitude - python_bulk[body].longitude) < 1e-12
        assert abs(native_bulk[body].latitude - python_bulk[body].latitude) < 1e-12
        assert abs(native_bulk[body].distance - python_bulk[body].distance) < 1e-6
        assert abs(native_bulk[body].speed - python_bulk[body].speed) < 1e-12


def test_planet_at_reuses_cached_apparent_context_for_same_reader_and_jd(monkeypatch: pytest.MonkeyPatch):
    build_calls: list[float] = []
    core_context_ids: list[int] = []
    approx_calls: list[float] = []
    tt_calls: list[tuple[float, float, object]] = []

    class _DummyContext:
        jd_tt = _JD_J2000 + 0.1
        obliquity = 23.4
        dpsi_deg = 0.0
        deps_deg = 0.0
        rot_mat = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        vector_cache = {}
        earth_ssb = (0.0, 0.0, 0.0)
        earth_vel = (0.0, 0.0, 0.0)

    monkeypatch.setattr(
        planets_module,
        "_approx_year",
        lambda jd: (approx_calls.append(jd), (2000, 1, 1, 0))[1],
    )
    monkeypatch.setattr(
        planets_module,
        "ut_to_tt",
        lambda jd, year, delta_t_policy=None: (
            tt_calls.append((jd, year, delta_t_policy)),
            jd + 0.1,
        )[1],
    )
    monkeypatch.setattr(planets_module, "_cached_apparent_context", planets_module._cached_apparent_context)
    monkeypatch.setattr(planets_module, "_store_apparent_context", planets_module._store_apparent_context)
    monkeypatch.setattr(planets_module, "_cached_planet_call_context", planets_module._cached_planet_call_context)
    monkeypatch.setattr(planets_module, "_store_planet_call_context", planets_module._store_planet_call_context)

    def _fake_build(jd_tt, reader, **kwargs):
        build_calls.append(jd_tt)
        return _DummyContext()

    def _fake_core(body: str, jd_ut: float, **kwargs):
        core_context_ids.append(id(kwargs["_context"]))
        return PlanetData(
            name=body,
            longitude=10.0,
            latitude=0.0,
            distance=1.0,
            speed=0.1,
            retrograde=False,
        )

    monkeypatch.setattr(planets_module, "_build_apparent_context", _fake_build)
    monkeypatch.setattr(planets_module, "_planet_at_core", _fake_core)
    monkeypatch.setattr(
        planets_module,
        "_planet_at_default_apparent_geocentric_ecliptic",
        lambda body, **kwargs: _fake_core(body, _JD_J2000, _context=kwargs["context"]),
    )

    class _DummyReader:
        pass

    reader = _DummyReader()
    first = planet_at(Body.SUN, _JD_J2000, reader=reader)
    second = planet_at(Body.MARS, _JD_J2000, reader=reader)

    assert first.name == Body.SUN
    assert second.name == Body.MARS
    assert build_calls == [_JD_J2000 + 0.1]
    assert approx_calls == [_JD_J2000]
    assert tt_calls == [(_JD_J2000, planets_module.decimal_year(2000, 1), None)]
    assert len(core_context_ids) == 2
    assert core_context_ids[0] == core_context_ids[1]


def test_planet_at_uses_default_fast_route_only_for_exact_default_surface(monkeypatch: pytest.MonkeyPatch):
    fast_calls: list[str] = []
    core_calls: list[str] = []

    class _DummyContext:
        jd_tt = _JD_J2000 + 0.1
        obliquity = 23.4
        dpsi_deg = 0.0
        deps_deg = 0.0
        rot_mat = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        vector_cache = {}
        earth_ssb = (0.0, 0.0, 0.0)
        earth_vel = (0.0, 0.0, 0.0)

    monkeypatch.setattr(planets_module, "_approx_year", lambda jd: (2000, 1, 1, 0))
    monkeypatch.setattr(planets_module, "ut_to_tt", lambda jd, year, delta_t_policy=None: jd + 0.1)
    monkeypatch.setattr(planets_module, "_build_apparent_context", lambda *args, **kwargs: _DummyContext())

    def _fake_fast(body: str, **kwargs):
        fast_calls.append(body)
        return PlanetData(
            name=body,
            longitude=1.0,
            latitude=0.0,
            distance=1.0,
            speed=0.1,
            retrograde=False,
        )

    def _fake_core(body: str, jd_ut: float, **kwargs):
        core_calls.append(body)
        return PlanetData(
            name=body,
            longitude=2.0,
            latitude=0.0,
            distance=1.0,
            speed=0.1,
            retrograde=False,
        )

    monkeypatch.setattr(planets_module, "_planet_at_default_apparent_geocentric_ecliptic", _fake_fast)
    monkeypatch.setattr(planets_module, "_planet_at_core", _fake_core)

    class _DummyReader:
        pass

    reader = _DummyReader()
    default_result = planet_at(Body.SUN, _JD_J2000, reader=reader)
    cart_result = planet_at(Body.SUN, _JD_J2000, reader=reader, frame="cartesian")

    assert default_result.longitude == 1.0
    assert isinstance(cart_result, PlanetData)
    assert cart_result.longitude == 2.0
    assert fast_calls == [Body.SUN]
    assert core_calls == [Body.SUN]


def test_rotation_helpers_use_native_then_scalar_fallback(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, object, object]] = []

    class _DummyNative:
        @staticmethod
        def rotation_matrix_multiply(a, b):
            calls.append(("mul", a, b))
            return (("native", 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

        @staticmethod
        def rotation_matrix_apply(m, v):
            calls.append(("apply", m, v))
            return (7.0, 8.0, 9.0)

    monkeypatch.setattr(planets_module, "_HAS_NATIVE_ROTATION", True)
    monkeypatch.setattr(planets_module, "_moira_native", _DummyNative())

    composed = planets_module._compose_rotation_matrix(_JD_J2000, with_nutation=False)
    assert composed == planets_module.precession_matrix_equatorial(_JD_J2000)

    monkeypatch.setattr(
        planets_module,
        "precession_matrix_equatorial",
        lambda jd: ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0), (7.0, 8.0, 9.0)),
    )
    monkeypatch.setattr(
        planets_module,
        "nutation_matrix_equatorial",
        lambda jd: ((9.0, 8.0, 7.0), (6.0, 5.0, 4.0), (3.0, 2.0, 1.0)),
    )
    composed = planets_module._compose_rotation_matrix(_JD_J2000, with_nutation=True)
    assert composed[0][0] == "native"
    assert calls[-1][0] == "mul"

    applied = planets_module._apply_rotation_matrix(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (1.0, 2.0, 3.0))
    assert applied == (7.0, 8.0, 9.0)
    assert calls[-1][0] == "apply"

    monkeypatch.setattr(planets_module, "_HAS_NATIVE_ROTATION", False)
    fallback = planets_module._apply_rotation_matrix(
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        (1.0, 2.0, 3.0),
    )
    assert fallback == (1.0, 2.0, 3.0)


# ---------------------------------------------------------------------------
# Ephemeris tests: default behaviour is unchanged
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_planet_at_default_matches_explicit_apparent_true():
    """Explicit all-default switches must produce identical results to the bare call."""
    default = planet_at(Body.MARS, _JD_J2000)
    explicit = planet_at(
        Body.MARS, _JD_J2000,
        apparent=True, aberration=True, grav_deflection=True, nutation=True,
        center="geocentric", frame="ecliptic",
    )
    assert isinstance(default, PlanetData)
    assert default.longitude == explicit.longitude
    assert default.latitude == explicit.latitude
    assert default.distance == explicit.distance


@pytest.mark.requires_ephemeris
def test_all_planets_at_default_matches_planet_at_loop():
    """all_planets_at must give the same result as calling planet_at per body."""
    bodies = [Body.SUN, Body.MOON, Body.MARS]
    bulk = all_planets_at(_JD_J2000, bodies=bodies)
    for body in bodies:
        single = planet_at(body, _JD_J2000)
        assert abs(bulk[body].longitude - single.longitude) < 1e-10
        assert abs(bulk[body].latitude - single.latitude) < 1e-10


# ---------------------------------------------------------------------------
# Ephemeris tests: aberration switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_aberration_false_changes_position():
    """Disabling aberration must produce a measurably different longitude."""
    with_ab = planet_at(Body.MARS, _JD_J2000, aberration=True)
    without = planet_at(Body.MARS, _JD_J2000, aberration=False)
    assert isinstance(with_ab, PlanetData)
    assert isinstance(without, PlanetData)
    # Annual aberration is ~20 arcseconds; 0.001° ≈ 3.6 arcseconds is a safe threshold.
    diff = abs(with_ab.longitude - without.longitude)
    assert diff > 1e-3, f"Expected >0.001° change from aberration, got {diff}"


@pytest.mark.requires_ephemeris
def test_aberration_false_ignored_when_apparent_false():
    """When apparent=False the aberration flag has no effect."""
    a = planet_at(Body.MARS, _JD_J2000, apparent=False, aberration=True)
    b = planet_at(Body.MARS, _JD_J2000, apparent=False, aberration=False)
    assert a.longitude == b.longitude
    assert a.latitude == b.latitude


# ---------------------------------------------------------------------------
# Ephemeris tests: grav_deflection switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_grav_deflection_false_changes_position():
    """Disabling gravitational deflection must shift the position measurably."""
    with_gd = planet_at(Body.MARS, _JD_J2000, grav_deflection=True)
    without = planet_at(Body.MARS, _JD_J2000, grav_deflection=False)
    diff = abs(with_gd.longitude - without.longitude)
    # Deflection near the Sun is ~1 arcsec; away from it it's ~0.001 arcsec.
    # A non-zero difference at any level is sufficient to confirm the switch works.
    assert diff != 0.0 or abs(with_gd.latitude - without.latitude) != 0.0, (
        "grav_deflection=False produced identical result to True"
    )


@pytest.mark.requires_ephemeris
def test_grav_deflection_not_applied_to_sun():
    """Deflection is never applied to the Sun regardless of the switch."""
    with_gd = planet_at(Body.SUN, _JD_J2000, grav_deflection=True)
    without = planet_at(Body.SUN, _JD_J2000, grav_deflection=False)
    assert with_gd.longitude == without.longitude
    assert with_gd.latitude == without.latitude


@pytest.mark.requires_ephemeris
def test_grav_deflection_false_ignored_when_apparent_false():
    a = planet_at(Body.MARS, _JD_J2000, apparent=False, grav_deflection=True)
    b = planet_at(Body.MARS, _JD_J2000, apparent=False, grav_deflection=False)
    assert a.longitude == b.longitude


# ---------------------------------------------------------------------------
# Ephemeris tests: nutation switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_nutation_false_changes_position():
    """Disabling nutation must produce a different longitude."""
    with_nut = planet_at(Body.MARS, _JD_J2000, nutation=True)
    without  = planet_at(Body.MARS, _JD_J2000, nutation=False)
    diff = abs(with_nut.longitude - without.longitude)
    # Nutation in longitude is ~17 arcseconds peak-to-peak.
    assert diff > 1e-4, f"Expected nutation effect > 0.0001°, got {diff}"


@pytest.mark.requires_ephemeris
def test_nutation_false_ignored_when_apparent_false():
    a = planet_at(Body.MARS, _JD_J2000, apparent=False, nutation=True)
    b = planet_at(Body.MARS, _JD_J2000, apparent=False, nutation=False)
    assert a.longitude == b.longitude


# ---------------------------------------------------------------------------
# Ephemeris tests: center switch
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_barycentric_center_returns_planet_data():
    result = planet_at(Body.MARS, _JD_J2000, center="barycentric")
    assert isinstance(result, PlanetData)


@pytest.mark.requires_ephemeris
def test_barycentric_differs_from_geocentric():
    """Barycentric and geocentric positions must differ by a measurable amount."""
    geo  = planet_at(Body.MARS, _JD_J2000, center="geocentric")
    bary = planet_at(Body.MARS, _JD_J2000, center="barycentric")
    diff = abs(geo.longitude - bary.longitude)
    # Earth–SSB offset is ~450 km; this shifts Mars by several arcseconds.
    assert diff > 1e-4, f"Expected >0.0001° barycentric offset, got {diff}"


@pytest.mark.requires_ephemeris
def test_barycentric_astrometric_differs_from_geocentric_astrometric():
    geo  = planet_at(Body.MARS, _JD_J2000, apparent=False, center="geocentric")
    bary = planet_at(Body.MARS, _JD_J2000, apparent=False, center="barycentric")
    diff = abs(geo.longitude - bary.longitude)
    assert diff > 1e-4


@pytest.mark.requires_ephemeris
def test_barycentric_topocentric_correction_not_applied():
    """Topocentric correction is silently ignored for barycentric output."""
    bary_plain = planet_at(Body.MARS, _JD_J2000, center="barycentric")
    bary_topo  = planet_at(
        Body.MARS, _JD_J2000, center="barycentric",
        observer_lat=51.5, observer_lon=-0.1, lst_deg=100.0,
    )
    assert bary_plain.longitude == bary_topo.longitude


# ---------------------------------------------------------------------------
# Ephemeris tests: frame='cartesian'
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_cartesian_frame_returns_cartesian_position():
    result = planet_at(Body.MARS, _JD_J2000, frame="cartesian")
    assert isinstance(result, CartesianPosition)
    assert result.name == Body.MARS
    assert result.center == "geocentric"


@pytest.mark.requires_ephemeris
def test_cartesian_frame_barycentric_label():
    result = planet_at(Body.MARS, _JD_J2000, frame="cartesian", center="barycentric")
    assert isinstance(result, CartesianPosition)
    assert result.center == "barycentric"


@pytest.mark.requires_ephemeris
def test_cartesian_distance_consistent_with_ecliptic():
    """Distance computed from XYZ must match the PlanetData distance."""
    ecliptic = planet_at(Body.MARS, _JD_J2000, frame="ecliptic")
    cartesian = planet_at(Body.MARS, _JD_J2000, frame="cartesian")
    assert isinstance(ecliptic, PlanetData)
    assert isinstance(cartesian, CartesianPosition)

    xyz_dist = math.sqrt(cartesian.x**2 + cartesian.y**2 + cartesian.z**2)
    # Distances should agree to within 1 km (numerical precision of transforms).
    assert abs(xyz_dist - ecliptic.distance) < 1.0, (
        f"Cartesian distance {xyz_dist:.3f} km vs PlanetData {ecliptic.distance:.3f} km"
    )


@pytest.mark.requires_ephemeris
def test_cartesian_astrometric_frame():
    """frame='cartesian' must also work when apparent=False."""
    result = planet_at(Body.MARS, _JD_J2000, apparent=False, frame="cartesian")
    assert isinstance(result, CartesianPosition)
    assert math.isfinite(result.x)
    assert math.isfinite(result.y)
    assert math.isfinite(result.z)


# ---------------------------------------------------------------------------
# Ephemeris tests: sky_position_at correction switches
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_sky_position_aberration_false_changes_ra():
    lat, lon = 51.5, -0.1
    with_ab  = sky_position_at(Body.MARS, _JD_J2000, lat, lon, aberration=True)
    without  = sky_position_at(Body.MARS, _JD_J2000, lat, lon, aberration=False)
    diff = abs(with_ab.right_ascension - without.right_ascension)
    assert diff > 1e-3, f"Expected >0.001° RA change from aberration, got {diff}"


@pytest.mark.requires_ephemeris
def test_sky_position_nutation_false_changes_dec():
    lat, lon = 51.5, -0.1
    with_nut = sky_position_at(Body.MARS, _JD_J2000, lat, lon, nutation=True)
    without  = sky_position_at(Body.MARS, _JD_J2000, lat, lon, nutation=False)
    diff = abs(with_nut.declination - without.declination)
    assert diff > 1e-4, f"Expected nutation effect in Dec > 0.0001°, got {diff}"


@pytest.mark.requires_ephemeris
def test_sky_position_default_matches_explicit_switches():
    """Explicit all-default switches must match the bare sky_position_at call."""
    lat, lon = 51.5, -0.1
    default  = sky_position_at(Body.MARS, _JD_J2000, lat, lon)
    explicit = sky_position_at(
        Body.MARS, _JD_J2000, lat, lon,
        aberration=True, grav_deflection=True, nutation=True,
    )
    assert default.right_ascension == explicit.right_ascension
    assert default.declination == explicit.declination
    assert default.altitude == explicit.altitude


# ---------------------------------------------------------------------------
# Ephemeris tests: all_planets_at switch propagation
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_all_planets_at_aberration_false_propagates():
    """all_planets_at(aberration=False) must differ from the default for all bodies."""
    bodies = [Body.MARS, Body.VENUS, Body.JUPITER]
    default  = all_planets_at(_JD_J2000, bodies=bodies)
    no_aberr = all_planets_at(_JD_J2000, bodies=bodies, aberration=False)
    for body in bodies:
        assert default[body].longitude != no_aberr[body].longitude, (
            f"aberration=False had no effect on {body}"
        )


@pytest.mark.requires_ephemeris
def test_all_planets_at_apparent_false_matches_planet_at_loop():
    """all_planets_at(apparent=False) must match planet_at(apparent=False) per body."""
    bodies = [Body.MARS, Body.VENUS]
    bulk = all_planets_at(_JD_J2000, bodies=bodies, apparent=False)
    for body in bodies:
        single = planet_at(body, _JD_J2000, apparent=False)
        assert abs(bulk[body].longitude - single.longitude) < 1e-10
