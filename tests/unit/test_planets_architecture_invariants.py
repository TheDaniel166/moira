"""Regression evidence for planetary cache, context, and ordering invariants."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import inspect
from itertools import permutations
import threading

import pytest

import moira.asteroids as asteroids_module
import moira.planets as planets_module
from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.constants import Body
from moira.coordinates import icrf_to_ecliptic
from moira.julian import DeltaTPolicy
from moira.obliquity import true_obliquity
from moira.planets import all_planets_at, planet_at
from moira.spk_reader import SpkReader


_JD_J2000 = 2_451_545.0


def _native_capable_reader() -> SpkReader:
    class _Handle:
        def batch_segment_position_and_velocity(self, specs, jd_tt):
            raise AssertionError("mode-decision tests must not execute the handle")

    class _Kernel:
        _handle = _Handle()

    reader = object.__new__(SpkReader)
    reader._kernel = _Kernel()
    return reader


def _planet_values(result) -> tuple[float, float, float, float, bool]:
    return (
        result.longitude,
        result.latitude,
        result.distance,
        result.speed,
        result.retrograde,
    )


@pytest.mark.requires_ephemeris
def test_explicit_jd_tt_cannot_contaminate_later_derived_call(
    planetary_kernel_path,
) -> None:
    jd_ut = _JD_J2000 + 0.125
    with (
        SpkReader(planetary_kernel_path) as exercised_reader,
        SpkReader(planetary_kernel_path) as fresh_reader,
    ):
        overridden = planet_at(
            Body.MOON,
            jd_ut,
            reader=exercised_reader,
            jd_tt=jd_ut + 0.5,
        )
        derived_after_override = planet_at(
            Body.MOON,
            jd_ut,
            reader=exercised_reader,
        )
        fresh_derived = planet_at(Body.MOON, jd_ut, reader=fresh_reader)

    assert _planet_values(derived_after_override) == _planet_values(fresh_derived)
    assert _planet_values(derived_after_override) != _planet_values(overridden)


@pytest.mark.requires_ephemeris
def test_custom_delta_t_policies_have_distinct_call_cache_entries(
    planetary_kernel_path,
) -> None:
    jd_ut = _JD_J2000 + 0.25
    short_delta_t = DeltaTPolicy(model="fixed", fixed_delta_t=30.0)
    long_delta_t = DeltaTPolicy(model="fixed", fixed_delta_t=120.0)
    with (
        SpkReader(planetary_kernel_path) as exercised_reader,
        SpkReader(planetary_kernel_path) as fresh_reader,
    ):
        short_result = planet_at(
            Body.MOON,
            jd_ut,
            reader=exercised_reader,
            delta_t_policy=short_delta_t,
        )
        long_after_short = planet_at(
            Body.MOON,
            jd_ut,
            reader=exercised_reader,
            delta_t_policy=long_delta_t,
        )
        fresh_long = planet_at(
            Body.MOON,
            jd_ut,
            reader=fresh_reader,
            delta_t_policy=long_delta_t,
        )

    assert _planet_values(long_after_short) == _planet_values(fresh_long)
    assert _planet_values(short_result) != _planet_values(long_after_short)


@pytest.mark.requires_ephemeris
def test_injected_context_rejects_epoch_reader_and_nutation_mismatches(
    planetary_kernel_path,
) -> None:
    with (
        SpkReader(planetary_kernel_path) as first_reader,
        SpkReader(planetary_kernel_path) as second_reader,
    ):
        jd_tt = _ut1_to_ephemeris_tt(_JD_J2000, first_reader)
        matching = planets_module._build_apparent_context(
            jd_tt,
            first_reader,
            apparent=True,
            nutation=True,
        )
        wrong_epoch = planets_module._build_apparent_context(
            jd_tt + 0.25,
            first_reader,
            apparent=True,
            nutation=True,
        )
        wrong_nutation = planets_module._build_apparent_context(
            jd_tt,
            first_reader,
            apparent=True,
            nutation=False,
        )

        with pytest.warns(DeprecationWarning, match="private reduction hooks"):
            accepted = planet_at(
                Body.MARS,
                _JD_J2000,
                reader=first_reader,
                jd_tt=jd_tt,
                _context=matching,
            )
        assert accepted.name == Body.MARS

        with (
            pytest.warns(DeprecationWarning, match="private reduction hooks"),
            pytest.raises(ValueError, match="epoch"),
        ):
            planet_at(
                Body.MARS,
                _JD_J2000,
                reader=first_reader,
                jd_tt=jd_tt,
                _context=wrong_epoch,
            )
        with (
            pytest.warns(DeprecationWarning, match="private reduction hooks"),
            pytest.raises(ValueError, match="different reader"),
        ):
            planet_at(
                Body.MARS,
                _JD_J2000,
                reader=second_reader,
                jd_tt=jd_tt,
                _context=matching,
            )
        with (
            pytest.warns(DeprecationWarning, match="private reduction hooks"),
            pytest.raises(ValueError, match="nutation"),
        ):
            planet_at(
                Body.MARS,
                _JD_J2000,
                reader=first_reader,
                jd_tt=jd_tt,
                nutation=True,
                _context=wrong_nutation,
            )
        with (
            pytest.warns(DeprecationWarning, match="private reduction hooks"),
            pytest.raises(ValueError, match="require a matching _context"),
        ):
            planet_at(
                Body.MARS,
                _JD_J2000,
                reader=first_reader,
                jd_tt=jd_tt,
                _vector_cache={},
            )


def test_reader_memoization_is_namespaced_per_thread() -> None:
    class _WritableReader:
        pass

    reader = _WritableReader()
    worker_count = 8
    barrier = threading.Barrier(worker_count)

    def cache_identity(_index: int) -> tuple[int, int]:
        cache = planets_module._reader_apparent_context_cache(reader)
        assert cache is not None
        cache[threading.get_ident()] = object()
        barrier.wait(timeout=5.0)
        return id(cache), len(cache)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(cache_identity, range(worker_count)))

    assert len({cache_id for cache_id, _size in results}) == worker_count
    assert {size for _cache_id, size in results} == {1}


def test_reader_cache_attachment_propagates_unexpected_failures() -> None:
    class _UnexpectedReader:
        def __setattr__(self, name, value):
            raise RuntimeError("unexpected attachment failure")

    with pytest.raises(RuntimeError, match="unexpected attachment failure"):
        planets_module._reader_thread_caches(_UnexpectedReader())


def test_native_evaluator_fallback_is_narrow(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Kernel:
        _handle = object()

    class _Reader:
        _kernel = _Kernel()

    class _ExpectedUnavailable:
        def __init__(self, handle):
            raise RuntimeError("capability unavailable")

    monkeypatch.setattr(
        planets_module,
        "_moira_native",
        type("Native", (), {"NativePlanetaryEvaluator": _ExpectedUnavailable}),
    )
    assert planets_module._get_native_planetary_evaluator(_Reader()) is None

    class _UnexpectedFailure:
        def __init__(self, handle):
            raise ValueError("bad evaluator state")

    monkeypatch.setattr(
        planets_module,
        "_moira_native",
        type("Native", (), {"NativePlanetaryEvaluator": _UnexpectedFailure}),
    )
    with pytest.raises(ValueError, match="bad evaluator state"):
        planets_module._get_native_planetary_evaluator(_Reader())


def test_native_mode_decision_has_stable_rejection_reasons() -> None:
    reader = _native_capable_reader()
    base = {
        "bodies": [Body.SUN, Body.MOON, Body.MARS],
        "reader": reader,
        "apparent": True,
        "aberration": True,
        "grav_deflection": True,
        "nutation": True,
        "center": "geocentric",
        "observer_lat": None,
        "observer_lon": None,
        "observer_elev_m": 0.0,
        "lst_deg": None,
        "delta_t_policy": None,
    }

    def decision(**overrides):
        return planets_module._npe_all_planets_mode_decision(
            **(base | overrides)
        )

    assert decision(bodies=[]).reason is planets_module._NativeAdmissionReason.UNSUPPORTED_BODY_SET
    assert decision(apparent=False).reason is planets_module._NativeAdmissionReason.NONDEFAULT_CORRECTION_POLICY
    assert decision(center="barycentric").reason is planets_module._NativeAdmissionReason.NON_GEOCENTRIC_CENTER
    assert decision(
        observer_lat=42.0,
        observer_lon=-83.0,
        lst_deg=100.0,
    ).reason is planets_module._NativeAdmissionReason.TOPOCENTRIC_REQUEST
    assert decision(
        delta_t_policy=DeltaTPolicy(model="fixed", fixed_delta_t=69.0)
    ).reason is planets_module._NativeAdmissionReason.CUSTOM_DELTA_T_POLICY
    assert decision(
        reader=object()
    ).reason is planets_module._NativeAdmissionReason.UNSUPPORTED_READER_TYPE

    no_batch_reader = object.__new__(SpkReader)
    no_batch_reader._kernel = type("Kernel", (), {"_handle": object()})()
    assert decision(
        reader=no_batch_reader
    ).reason is planets_module._NativeAdmissionReason.BATCH_CAPABILITY_UNAVAILABLE

    elevation_only = decision(observer_elev_m=1500.0)
    assert elevation_only.admitted is True
    assert elevation_only.backend is planets_module._NativeAllPlanetsBackend.NATIVE_BATCH


def test_native_plan_explains_route_and_backend_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _native_capable_reader()
    common = {
        "reader": reader,
        "jd_tt": _JD_J2000,
        "apparent": True,
        "aberration": True,
        "grav_deflection": True,
        "nutation": True,
        "center": "geocentric",
        "observer_lat": None,
        "observer_lon": None,
        "observer_elev_m": 0.0,
        "lst_deg": None,
        "delta_t_policy": None,
    }
    public_specs = [(1, 2, 3)]
    body_specs = {Body.SUN: ((1, 2, 3),)}

    monkeypatch.setattr(
        planets_module,
        "_npe_public_route_segment_specs",
        lambda reader, jd_tt: None,
    )
    plan = planets_module._native_all_planets_plan([Body.SUN], **common)
    assert plan.reason is planets_module._NativeAdmissionReason.PUBLIC_ROUTE_UNAVAILABLE

    monkeypatch.setattr(
        planets_module,
        "_npe_public_route_segment_specs",
        lambda reader, jd_tt: public_specs,
    )
    monkeypatch.setattr(
        planets_module,
        "_npe_body_route_segment_specs",
        lambda reader, jd_tt: None,
    )
    plan = planets_module._native_all_planets_plan([Body.SUN], **common)
    assert plan.reason is planets_module._NativeAdmissionReason.BODY_ROUTE_UNAVAILABLE

    monkeypatch.setattr(
        planets_module,
        "_npe_body_route_segment_specs",
        lambda reader, jd_tt: body_specs,
    )
    monkeypatch.setattr(
        planets_module,
        "_get_native_planetary_evaluator",
        lambda reader: None,
    )
    plan = planets_module._native_all_planets_plan([Body.SUN], **common)
    assert plan.admitted is True
    assert plan.reason is planets_module._NativeAdmissionReason.ADMITTED_NATIVE_BATCH
    assert plan.public_specs == tuple(public_specs)

    evaluator = object()
    monkeypatch.setattr(
        planets_module,
        "_get_native_planetary_evaluator",
        lambda reader: evaluator,
    )
    monkeypatch.setattr(
        planets_module,
        "_npe_public_route_segment_specs",
        lambda reader, jd_tt: (
            public_specs if jd_tt == _JD_J2000 else None
        ),
    )
    plan = planets_module._native_all_planets_plan([Body.SUN], **common)
    assert plan.reason is planets_module._NativeAdmissionReason.RATE_ROUTE_UNAVAILABLE

    monkeypatch.setattr(
        planets_module,
        "_npe_public_route_segment_specs",
        lambda reader, jd_tt: public_specs,
    )
    plan = planets_module._native_all_planets_plan([Body.SUN], **common)
    assert plan.admitted is True
    assert plan.backend is planets_module._NativeAllPlanetsBackend.NATIVE_EVALUATOR
    assert plan.reason is planets_module._NativeAdmissionReason.ADMITTED_NATIVE_EVALUATOR
    assert plan.evaluator is evaluator
    assert len(plan.rate_specs) == 2
    assert planets_module._reader_apparent_context_cache(reader) is not None
    assert len(planets_module._reader_apparent_context_cache(reader)) == 0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_ut", [_JD_J2000, 2_460_000.5])
def test_python_multibody_results_are_exactly_order_independent(
    monkeypatch: pytest.MonkeyPatch,
    reader,
    jd_ut: float,
) -> None:
    monkeypatch.setattr(
        planets_module,
        "_native_all_planets_admitted",
        lambda *args, **kwargs: None,
    )
    bodies = (Body.MARS, Body.JUPITER, Body.SATURN)
    reference = None
    for order in permutations(bodies):
        result = all_planets_at(jd_ut, bodies=list(order), reader=reader)
        values = {body: _planet_values(result[body]) for body in bodies}
        if reference is None:
            reference = values
        assert values == reference


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_ut", [2_415_020.5, _JD_J2000, 2_460_000.5])
def test_native_and_python_planetary_products_agree_across_epochs(
    monkeypatch: pytest.MonkeyPatch,
    reader,
    jd_ut: float,
) -> None:
    bodies = list(Body.ALL_PLANETS)
    native = all_planets_at(jd_ut, bodies=bodies, reader=reader)
    monkeypatch.setattr(
        planets_module,
        "_native_all_planets_admitted",
        lambda *args, **kwargs: None,
    )
    python = all_planets_at(jd_ut, bodies=bodies, reader=reader)

    for body in bodies:
        assert native[body].longitude == pytest.approx(
            python[body].longitude,
            abs=1e-12,
        )
        assert native[body].latitude == pytest.approx(
            python[body].latitude,
            abs=1e-12,
        )
        assert native[body].distance == pytest.approx(
            python[body].distance,
            abs=1e-6,
        )
        assert native[body].speed == pytest.approx(
            python[body].speed,
            abs=1e-12,
        )


@pytest.mark.requires_ephemeris
def test_jupiter_and_saturn_are_never_their_own_deflectors(reader) -> None:
    jd_tt = _ut1_to_ephemeris_tt(_JD_J2000, reader)
    context = planets_module._build_apparent_context(
        jd_tt,
        reader,
        apparent=True,
        nutation=True,
    )

    jupiter_vectors = [
        vector
        for vector, _radius in planets_module._deflectors_for_body(
            Body.JUPITER,
            jd_tt,
            reader,
            context,
        )
    ]
    saturn_vectors = [
        vector
        for vector, _radius in planets_module._deflectors_for_body(
            Body.SATURN,
            jd_tt,
            reader,
            context,
        )
    ]

    assert context.jupiter_geocentric not in jupiter_vectors
    assert context.saturn_geocentric in jupiter_vectors
    assert context.saturn_geocentric not in saturn_vectors
    assert context.jupiter_geocentric in saturn_vectors


@pytest.mark.requires_ephemeris
def test_shared_reader_concurrent_calls_match_serial_results(reader) -> None:
    jobs = [
        (_JD_J2000 + offset / 10.0, body)
        for offset in range(8)
        for body in (Body.MERCURY, Body.MARS, Body.JUPITER, Body.SATURN)
    ]
    expected = {
        job: _planet_values(planet_at(job[1], job[0], reader=reader))
        for job in jobs
    }

    def calculate(job: tuple[float, str]):
        jd_ut, body = job
        return job, _planet_values(planet_at(body, jd_ut, reader=reader))

    with ThreadPoolExecutor(max_workers=8) as executor:
        actual = dict(executor.map(calculate, jobs * 3))

    assert actual == expected


def test_retained_private_planet_signature_is_explicitly_governed() -> None:
    signature = inspect.signature(planet_at)
    retained = {
        "_dpsi_deg",
        "_deps_deg",
        "_rot_mat",
        "_vector_cache",
        "_context",
    }
    assert retained <= set(signature.parameters)
    assert all(
        signature.parameters[name].kind
        is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for name in retained
    )
    assert "compatibility-only internal reduction hooks" in (planet_at.__doc__ or "")
    private_signature = inspect.signature(planets_module._planet_at_impl)
    assert "_workspace" in private_signature.parameters
    assert retained.isdisjoint(private_signature.parameters)
    assert "_planet_at_impl" not in planets_module.__all__


@pytest.mark.requires_ephemeris
def test_topocentric_asteroid_spherical_adapter_preserves_vector(
    monkeypatch: pytest.MonkeyPatch,
    small_body_reader_pool,
) -> None:
    captured_vectors = []
    refraction_calls = []
    original_equatorial = planets_module.icrf_to_equatorial

    def capture_equatorial(vector):
        captured_vectors.append(vector)
        return original_equatorial(vector)

    monkeypatch.setattr(planets_module, "icrf_to_equatorial", capture_equatorial)
    monkeypatch.setattr(
        planets_module,
        "apply_refraction",
        lambda *args, **kwargs: refraction_calls.append((args, kwargs)),
    )

    result = planet_at(
        "asteroid:Ceres",
        _JD_J2000,
        reader=small_body_reader_pool,
        observer_lat=42.3314,
        observer_lon=-83.0458,
        observer_elev_m=180.0,
        lst_deg=100.0,
    )

    assert len(captured_vectors) == 1
    jd_tt = _ut1_to_ephemeris_tt(_JD_J2000, small_body_reader_pool)
    direct_lon, direct_lat, direct_distance = icrf_to_ecliptic(
        captured_vectors[0],
        true_obliquity(jd_tt),
    )
    longitude_delta = (result.longitude - direct_lon + 180.0) % 360.0 - 180.0
    assert longitude_delta == pytest.approx(0.0, abs=1e-12)
    assert result.latitude == pytest.approx(direct_lat, abs=1e-12)
    assert result.distance == direct_distance
    assert result.is_topocentric is True
    assert refraction_calls == []


@pytest.mark.requires_ephemeris
def test_asteroid_owned_vector_adapter_matches_flag_aware_product(
    small_body_reader_pool,
) -> None:
    direct = asteroids_module.asteroid_at(
        "Ceres",
        _JD_J2000,
        reader=small_body_reader_pool,
    )
    flag_aware = asteroids_module._asteroid_at_with_flags(
        "Ceres",
        _JD_J2000,
        reader=small_body_reader_pool,
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
    )

    assert direct == flag_aware
