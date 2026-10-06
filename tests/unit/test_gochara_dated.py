"""Clock, reader, policy and same-birth input invariants for VED-017."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone, timedelta
import importlib
from types import SimpleNamespace

import pytest

from moira.gochara import (
    GOCHARA_PLANETS, GocharaPolicy, GocharaBavMode, GocharaVedhaMode,
    gochara_from_positions, gochara_subsystem_profile,
)
from moira.ashtakavarga import REKHA_TABLES
from moira.spk_reader import get_active_reader, use_reader_override, OutOfRangeError, MissingKernelError

dated = importlib.import_module("moira.gochara_dated")
NATAL, TRANSIT = 2447892.5, 2461320.5


@pytest.fixture
def astronomy(monkeypatch):
    reader = object()
    calls = []
    identity = SimpleNamespace(summary_label="DE-0441LE-0441", planetary_ephemeris="DE441",
        lunar_ephemeris="LE441", lunar_tidal_acceleration_arcsec_per_cy2=-25.936)

    def clock(jd, active_reader):
        assert active_reader is reader and get_active_reader() is reader
        calls.append(("clock", jd))
        return SimpleNamespace(epoch_tt=jd+1200/86400, epoch_tdb=jd+1200/86400+0.001/86400,
            delta_t_seconds=1200, delta_t_correction_seconds=99, tdb_minus_tt_seconds=0.001,
            raw_delta_t=SimpleNamespace(source_product="analytic_clock"), identity=identity)

    def ayanamsa(tt, system, mode):
        assert get_active_reader() is reader and mode == "true"
        calls.append(("ayanamsa", tt))
        return 10 + (tt-NATAL)*0.001

    def planet(body, jd, **kw):
        assert kw == dict(reader=reader, jd_tt=jd+1200/86400,
            apparent=True, aberration=True, grav_deflection=True, nutation=True,
            center="geocentric", frame="ecliptic")
        assert get_active_reader() is reader
        calls.append((body, jd))
        return SimpleNamespace(longitude=(50 + GOCHARA_PLANETS.index(body)*40 + (jd-NATAL)*0.03) % 360)

    monkeypatch.setattr(dated, "get_reader", lambda: reader)
    monkeypatch.setattr(dated, "_bind_ephemeris_time", clock)
    monkeypatch.setattr(dated, "_ayanamsa_at_tt", ayanamsa)
    monkeypatch.setattr(dated, "planet_at", planet)
    return reader, calls


def test_complete_snapshot_owns_separate_clocks_and_restores_reader(astronomy):
    reader, calls = astronomy
    outer = object()
    with use_reader_override(outer):
        result = dated.gochara_at(NATAL, TRANSIT, reader=reader)
        assert get_active_reader() is outer
    assert calls.count(("clock", NATAL)) == calls.count(("clock", TRANSIT)) == 1
    assert [c[1] for c in calls if c[0] == "ayanamsa"] == [NATAL+1200/86400, TRANSIT+1200/86400]
    assert result.natal.ayanamsa_degrees != result.transit.ayanamsa_degrees
    natal_moon = (90-result.natal.ayanamsa_degrees) % 360
    transit = {p: ((50+i*40+(TRANSIT-NATAL)*0.03) % 360-result.transit.ayanamsa_degrees) % 360
               for i, p in enumerate(GOCHARA_PLANETS)}
    manual = gochara_from_positions(natal_moon, transit, policy=result.policy.gochara_policy)
    assert result.profile == gochara_subsystem_profile(manual)
    assert result.profile.snapshot.missing_planets == ()
    assert result.bav_source is None and result.natal_ascendant_sidereal is None
    assert result.natal.delta_t_correction_seconds == 99
    assert {o.id for o in result.policy.selected_options} == {"astronomy.reader_epochs", "bav.omit"}
    with pytest.raises(FrozenInstanceError):
        result.natal.jd_tt = 0


def test_raw_bav_uses_natal_clock_lagna_and_absolute_transit_sign(astronomy, monkeypatch):
    reader, _ = astronomy
    tt = NATAL+1200/86400
    monkeypatch.setattr(dated, "nutation", lambda epoch: (0.01, 0.02) if epoch == tt else pytest.fail("wrong Lagna TT"))
    monkeypatch.setattr(dated, "mean_obliquity", lambda epoch: 23 if epoch == tt else pytest.fail("wrong obliquity TT"))
    def sidereal_time(jd, epoch_tt, lon, dpsi, eps):
        assert (jd, epoch_tt, lon, dpsi, eps) == (NATAL, tt, 77, 0.01, 23)
        return 45
    monkeypatch.setattr(dated, "_local_sidereal_time_at_tt", sidereal_time)
    monkeypatch.setattr(dated, "_asc_from_armc", lambda armc, eps, lat: 90)
    policy = dated.GocharaDatePolicy(natal_bav_mode=dated.GocharaNatalBavMode.COMPUTE_RAW,
        gochara_policy=GocharaPolicy(bav_mode=GocharaBavMode.REQUIRE_ALL_RAW))
    result = dated.gochara_at(NATAL, TRANSIT, reader=reader, policy=policy,
                              birth_location=dated.GocharaBirthLocation(28, 77))
    assert result.natal_ascendant_sidereal == 90-result.natal.ayanamsa_degrees
    indices = dict(result.natal_sign_indices)
    assert len(indices) == 8 and indices["Lagna"] == 2
    for bav in result.profile.snapshot.bhinna:
        # Independent sign-distance accumulation over the owning table encoding.
        expected = tuple(sum((sign-indices[ref]) % 12+1 in distances
                             for ref, distances in REKHA_TABLES[bav.planet].items())
                         for sign in range(12))
        assert bav.rekhas == expected
        assessment = result.profile.snapshot.for_planet(bav.planet)
        assert assessment.ashtakavarga_rekhas == expected[assessment.position.rashi_index]
    assert "unreduced" in result.bav_source
    assert result.profile == replace(result).profile


@pytest.mark.parametrize("system,anchor,target", [("True Chitrapaksha", "Spica", 180),
    ("Aldebaran (15 Tau)", "Aldebaran", 45)])
def test_live_anchor_is_at_each_tt_and_never_falls_back(astronomy, monkeypatch, system, anchor, target):
    reader, _ = astronomy
    def star(name, tt):
        assert name == anchor and get_active_reader() is reader
        return SimpleNamespace(longitude=(target+20+(tt-NATAL)*0.001) % 360)
    monkeypatch.setattr(dated, "star_at", star)
    result = dated.gochara_at(NATAL, TRANSIT, reader=reader,
                              policy=dated.GocharaDatePolicy(ayanamsa_system=system))
    assert result.natal.ayanamsa_method == result.transit.ayanamsa_method == "live_star_anchor"
    assert result.natal.ayanamsa_anchor == anchor
    monkeypatch.setattr(dated, "star_at", lambda *args: (_ for _ in ()).throw(KeyError("missing private path")))
    outer = object()
    with use_reader_override(outer), pytest.raises(dated.GocharaResourceError, match="natal") as error:
        dated.gochara_at(NATAL, TRANSIT, reader=reader, policy=result.policy)
    assert "private path" not in str(error.value)


@pytest.mark.parametrize("kw", [
    {"natal_jd_ut1": True}, {"transit_jd_ut1": float("inf")}, {"natal_jd_ut1": "2447892.5"},
    {"natal_jd_ut1": 10_000_001}, {"natal_jd_ut1": 10**500}, {"policy": {}},
    {"birth_location": dated.GocharaBirthLocation(0, 0)},
    {"policy": dated.GocharaDatePolicy(natal_bav_mode=dated.GocharaNatalBavMode.COMPUTE_RAW)},
])
def test_invalid_inputs_rejected_before_resource_access(monkeypatch, kw):
    monkeypatch.setattr(dated, "get_reader", lambda: pytest.fail("invalid input reached resources"))
    with pytest.raises((TypeError, ValueError)):
        dated.gochara_at(**dict(natal_jd_ut1=NATAL, transit_jd_ut1=TRANSIT) | kw)


@pytest.mark.parametrize("kw", [
    {"ayanamsa_system": "unknown"}, {"natal_bav_mode": "compute_raw"}, {"gochara_policy": {}},
    {"gochara_policy": GocharaPolicy(bav_mode=GocharaBavMode.REQUIRE_ALL_RAW)},
    {"natal_bav_mode": dated.GocharaNatalBavMode.COMPUTE_RAW,
     "gochara_policy": GocharaPolicy(bav_mode=GocharaBavMode.OMIT)},
])
def test_policy_rejects_unadmitted_or_contradictory_choices(kw):
    with pytest.raises((TypeError, ValueError)):
        dated.GocharaDatePolicy(**kw)


@pytest.mark.parametrize("lat,lon", [(90, 0), (-90, 0), (0, 181), (True, 0), (0, float("nan"))])
def test_location_domain(lat, lon):
    with pytest.raises((TypeError, ValueError)):
        dated.GocharaBirthLocation(lat, lon)


def test_vessels_rederive_products_and_reject_clock_frame_forgery(astronomy):
    result = dated.gochara_at(NATAL, TRANSIT)
    for kw in ({"jd_tt": result.natal.jd_tt+1}, {"jd_tdb": result.natal.jd_tdb+1},
               {"tropical_longitudes": (0,)*6}, {"delta_t_seconds": True},
               {"kernel_label": ""}, {"tropical_longitudes": (360,)*7}):
        with pytest.raises((TypeError, ValueError)):
            replace(result.natal, **kw)
    with pytest.raises(ValueError, match="ayanamsas"):
        replace(result, policy=dated.GocharaDatePolicy(ayanamsa_system="Raman"))
    changed = replace(result.transit, tropical_longitudes=(0,)*7)
    new = replace(result, transit=changed)
    assert new.profile.snapshot != result.profile.snapshot


@pytest.mark.parametrize("exception,kind", [
    (MissingKernelError("private file"), dated.GocharaResourceError),
    (dated._EphemerisTimeBasisError("unknown identity"), dated.GocharaResourceError),
    (KeyError("missing segment"), dated.GocharaResourceError),
    (OutOfRangeError("private coverage", True), dated.GocharaCoverageError),
])
def test_resource_errors_are_distinct_and_reader_is_restored(astronomy, monkeypatch, exception, kind):
    reader, _ = astronomy
    monkeypatch.setattr(dated, "planet_at", lambda *a, **kw: (_ for _ in ()).throw(exception))
    outer = object()
    with use_reader_override(outer):
        with pytest.raises(kind) as error:
            dated.gochara_at(NATAL, TRANSIT, reader=reader)
        assert get_active_reader() is outer
    assert "private" not in str(error.value)


def test_aware_instants_convert_once_and_offset_equivalence(astronomy, monkeypatch):
    calls = []
    original = dated.utc_to_ut1
    monkeypatch.setattr(dated, "utc_to_ut1", lambda jd: calls.append(jd) or original(jd))
    natal = datetime(1990, 1, 1, tzinfo=timezone.utc)
    transit = datetime(2026, 10, 6, tzinfo=timezone.utc)
    a = dated.gochara_for_datetimes(natal, transit)
    assert len(calls) == 2
    offset = timezone(timedelta(hours=5, minutes=30))
    b = dated.gochara_for_datetimes(natal.astimezone(offset), transit.astimezone(offset))
    assert a == b
    with pytest.raises(ValueError, match="timezone-aware"):
        dated.gochara_for_datetimes(natal.replace(tzinfo=None), transit)
    with pytest.raises(TypeError):
        dated.gochara_for_datetimes(natal.date(), transit)


def test_facade_delegates_its_reader(monkeypatch):
    from moira import Moira
    reader = object()
    def call(*args, **kw):
        assert args == (NATAL, TRANSIT) and kw == dict(reader=reader, policy=None, birth_location=None)
        return "receipt"
    monkeypatch.setattr(dated, "gochara_at", call)
    assert Moira.gochara_at(SimpleNamespace(_reader=reader), NATAL, TRANSIT) == "receipt"


def test_sidereal_boundaries_preserve_sign_ownership():
    assert dated.GocharaDatedPosition("Sun", 30, 0).position.rashi_index == 1
    assert dated.GocharaDatedPosition("Sun", 0, 1e-300).position.rashi_index == 11


def test_nonunique_lagna_is_rejected(astronomy, monkeypatch):
    monkeypatch.setattr(dated, "nutation", lambda tt: (0, 0))
    monkeypatch.setattr(dated, "mean_obliquity", lambda tt: 30)
    monkeypatch.setattr(dated, "_local_sidereal_time_at_tt", lambda *args: 90)
    with pytest.raises(ValueError, match="unique Lagna"):
        dated.gochara_at(NATAL, TRANSIT, birth_location=dated.GocharaBirthLocation(-60, 0),
            policy=dated.GocharaDatePolicy(natal_bav_mode=dated.GocharaNatalBavMode.COMPUTE_RAW))


def test_missing_reader_is_a_resource_failure_before_any_epoch(monkeypatch):
    monkeypatch.setattr(dated, "get_reader", lambda: (_ for _ in ()).throw(MissingKernelError("private path")))
    with pytest.raises(dated.GocharaResourceError, match="reader") as error:
        dated.gochara_at(NATAL, TRANSIT)
    assert "private path" not in str(error.value)


def test_transit_failure_restores_context_and_never_returns_partial_result(astronomy, monkeypatch):
    reader, _ = astronomy
    original = dated.planet_at
    def position(body, jd, **kw):
        if jd == TRANSIT:
            raise OutOfRangeError("private coverage", True)
        return original(body, jd, **kw)
    monkeypatch.setattr(dated, "planet_at", position)
    outer = object()
    with use_reader_override(outer):
        with pytest.raises(dated.GocharaCoverageError, match="transit"):
            dated.gochara_at(NATAL, TRANSIT, reader=reader)
        assert get_active_reader() is outer


def test_all_dated_exports_are_curated_with_shared_identity():
    import moira
    import moira.facade as facade
    import moira.vedic as vedic
    for surface in (moira, facade, vedic):
        assert set(dated.__all__) <= set(surface.__all__)
        for name in dated.__all__:
            assert getattr(surface, name) is getattr(dated, name)


def test_unidentified_time_basis_fails_before_position_computation(astronomy, monkeypatch):
    reader, _ = astronomy
    original = dated._bind_ephemeris_time
    def clock(jd, active):
        bound = original(jd, active)
        bound.identity.lunar_tidal_acceleration_arcsec_per_cy2 = None
        return bound
    monkeypatch.setattr(dated, "_bind_ephemeris_time", clock)
    monkeypatch.setattr(dated, "planet_at", lambda *a, **kw: pytest.fail("unidentified reader reached positions"))
    with pytest.raises(dated.GocharaResourceError, match="identity"):
        dated.gochara_at(NATAL, TRANSIT, reader=reader)
