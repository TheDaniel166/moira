from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira._ephemeris_time as ephemeris_time
import moira._facade_astronomy as astronomy_facade
import moira._facade_classical as classical_facade
import moira._facade_core as core_facade
import moira._facade_predictive as predictive_facade
import moira._facade_spatial as spatial_facade
import moira._facade_special as special_facade
import moira._facade_vedic as vedic_facade
import moira.astrocartography as astrocartography
import moira.julian as julian
import moira.obliquity as obliquity
import moira.panchanga as panchanga
import moira.parans as parans
import moira.phase as phase
import moira.phenomena as phenomena
import moira.planetary_hours as planetary_hours
import moira.progressions as progressions
import moira.stars as stars


_DT = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)


class _Astronomy(astronomy_facade.AstronomyFacadeMixin):
    _reader = object()


class _Core(core_facade.CoreFacadeMixin):
    def chart(self, _dt, *, bodies=None):
        return SimpleNamespace(
            planets={"Sun": SimpleNamespace(longitude=123.0)},
        )


class _Spatial(spatial_facade.SpatialFacadeMixin):
    _reader = object()


class _Special(special_facade.SpecialTopicsFacadeMixin):
    _reader = object()


class _Predictive(predictive_facade.PredictiveFacadeMixin):
    _reader = object()


class _Vedic(vedic_facade.VedicFacadeMixin):
    pass


class _Classical(classical_facade.ClassicalFacadeMixin):
    pass


def test_astronomy_instant_adapters_pass_resolved_ut1_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, float] = {}
    fake_facade = SimpleNamespace(
        jd_from_datetime=lambda _dt: 100.0,
        utc_to_ut1=lambda jd: jd + 0.25,
        angular_diameter=lambda _body, jd: received.setdefault("diameter", jd) or 1.0,
    )
    monkeypatch.setattr(astronomy_facade, "_facade_module", lambda: fake_facade)
    monkeypatch.setattr(phase, "phase_angle", lambda _body, jd: received.setdefault("phase", jd) or 30.0)
    monkeypatch.setattr(phase, "illuminated_fraction", lambda _angle: 0.5)
    monkeypatch.setattr(phase, "apparent_magnitude", lambda _body, jd: received.setdefault("magnitude", jd) or -4.0)
    monkeypatch.setattr(phase, "synodic_phase_angle", lambda _a, _b, jd: received.setdefault("synodic", jd) or 90.0)
    monkeypatch.setattr(phase, "synodic_phase_state", lambda _angle: "waxing")

    _Astronomy().phase("Venus", _DT)
    _Astronomy().synodic_phase("Sun", "Moon", _DT)

    assert received == {
        "phase": 100.25,
        "diameter": 100.25,
        "magnitude": 100.25,
        "synodic": 100.25,
    }


def test_twilight_selects_utc_midnight_before_dut1_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[float] = []
    fake_facade = SimpleNamespace(
        jd_from_datetime=lambda _dt: 100.500001,
        utc_to_ut1=lambda jd: jd - 0.01,
        twilight_times=lambda jd, _lat, _lon: received.append(jd),
    )
    monkeypatch.setattr(astronomy_facade, "_facade_module", lambda: fake_facade)

    _Astronomy().twilight(_DT, 40.0, -75.0)

    # UTC midnight is 100.5; converting first and then flooring would have
    # selected 99.5 under this deliberately large negative DUT1 surrogate.
    assert received == [100.49]


def test_heliacal_and_nakshatra_adapters_receive_ut1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, float] = {}
    fake_facade = SimpleNamespace(
        Ayanamsa=SimpleNamespace(LAHIRI="Lahiri"),
        jd_from_datetime=lambda _dt: 200.0,
        utc_to_ut1=lambda jd: jd + 0.125,
        all_nakshatras_at=lambda _positions, jd, _system: received.setdefault("nakshatra", jd),
    )
    chart = SimpleNamespace(
        jd_ut=200.0,
        longitudes=lambda include_nodes=False: {"Sun": 10.0},
    )
    monkeypatch.setattr(astronomy_facade, "_facade_module", lambda: fake_facade)
    monkeypatch.setattr(
        stars,
        "heliacal_rising",
        lambda _name, jd, _lat, _lon: received.setdefault("heliacal", jd),
    )

    _Astronomy().heliacal_rising("Sirius", _DT, 30.0, 20.0)
    _Astronomy().nakshatras(chart)

    assert received == {"heliacal": 200.125, "nakshatra": 200.125}


def test_spatial_chart_consumers_separate_utc_ut1_and_tt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, list[float]] = {
        "nutation": [],
        "sidereal": [],
        "sky": [],
    }
    fake_facade = SimpleNamespace(
        utc_to_ut1=lambda jd: jd + 0.25,
        utc_to_tt=lambda jd: jd + 0.75,
        sky_position_at=lambda _body, jd, **_kwargs: (
            received["sky"].append(jd) or SimpleNamespace(right_ascension=10.0, declination=20.0)
        ),
        acg_lines=lambda *_args, **_kwargs: (),
        local_space_positions=lambda *_args, **_kwargs: (),
        all_gauquelin_sectors=lambda *_args, **_kwargs: {},
    )
    chart = SimpleNamespace(
        jd_ut=300.0,
        planets={"Sun": SimpleNamespace(longitude=10.0, latitude=0.0)},
        nodes={},
        obliquity=23.4,
    )
    monkeypatch.setattr(spatial_facade, "_facade_module", lambda: fake_facade)
    monkeypatch.setattr(
        obliquity,
        "nutation",
        lambda jd: (received["nutation"].append(jd) or (0.1, 0.0)),
    )
    monkeypatch.setattr(obliquity, "true_obliquity", lambda _jd: 23.4)
    monkeypatch.setattr(
        julian,
        "apparent_sidereal_time",
        lambda jd, *_args: received["sidereal"].append(jd) or 20.0,
    )
    monkeypatch.setattr(
        julian,
        "local_sidereal_time",
        lambda jd, *_args: received["sidereal"].append(jd) or 20.0,
    )

    _Spatial().astrocartography(chart)
    _Spatial().local_space(chart, 40.0, -75.0)
    _Spatial().gauquelin_sectors(chart, 40.0, -75.0)

    assert received["nutation"] == [300.75, 300.75, 300.75]
    assert received["sidereal"] == [300.25, 300.25, 300.25]
    assert received["sky"] == [300.25, 300.25, 300.25]


def test_spatial_day_and_frame_adapters_use_their_declared_scales(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, float] = {}
    fake_facade = SimpleNamespace(
        Body=SimpleNamespace(ALL_PLANETS=["Sun"]),
        jd_from_datetime=lambda _dt: 400.500001,
        utc_to_ut1=lambda jd: jd - 0.01,
        utc_to_tt=lambda jd: jd + 0.75,
        find_parans=lambda _bodies, jd, *_args, **_kwargs: received.setdefault("parans", jd),
        calculate_galactic_houses=lambda jd, *_args: received.setdefault("houses", jd),
        all_galactic_positions=lambda _data, _obl, jd: received.setdefault("galactic", jd),
        galactic_reference_points=lambda _obl, jd: received.setdefault("angles", jd),
        all_uranian_at=lambda jd: received.setdefault("uranian", jd),
    )
    chart = SimpleNamespace(
        jd_ut=400.0,
        obliquity=23.4,
        planets={"Sun": SimpleNamespace(longitude=10.0, latitude=0.0)},
        nodes={},
    )
    monkeypatch.setattr(spatial_facade, "_facade_module", lambda: fake_facade)

    _Spatial().parans(_DT, 40.0, -75.0)
    _Spatial().galactic_houses(_DT, 40.0, -75.0)
    _Spatial().galactic_chart(chart)
    _Spatial().galactic_angles(chart)
    _Spatial().uranian(_DT)

    assert received == {
        "parans": 400.49,
        "houses": 400.490001,
        "galactic": 400.75,
        "angles": 400.75,
        "uranian": 400.490001,
    }


def test_sidereal_chart_resolves_ayanamsa_epoch_to_ut1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[float] = []
    fake_facade = SimpleNamespace(
        Ayanamsa=SimpleNamespace(LAHIRI="Lahiri"),
        jd_from_datetime=lambda _dt: 450.0,
        utc_to_ut1=lambda jd: jd + 0.25,
        ayanamsa=lambda jd, _system: seen.append(jd) or 23.0,
    )
    monkeypatch.setattr(core_facade, "_facade_module", lambda: fake_facade)

    result = _Core().sidereal_chart(_DT)

    assert seen == [450.25]
    assert result == {"Sun": 100.0}


def test_special_datetime_search_adapters_convert_each_endpoint_to_ut1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}
    values = iter((500.0, 600.0, 601.0))
    fake_facade = SimpleNamespace(
        jd_from_datetime=lambda _dt: next(values),
        utc_to_ut1=lambda jd: jd + 0.25,
        void_of_course_window=lambda jd, **_kwargs: received.setdefault("voc", jd),
        find_electional_windows=lambda **kwargs: received.setdefault("electional", kwargs),
    )
    monkeypatch.setattr(special_facade, "_facade_module", lambda: fake_facade)

    _Special().moon_void_of_course(_DT)
    _Special().electional_windows(_DT, _DT, 40.0, -75.0, lambda _chart: True)

    assert received["voc"] == 500.25
    electional = received["electional"]
    assert isinstance(electional, dict)
    assert electional["jd_start"] == 600.25
    assert electional["jd_end"] == 601.25


def test_phase_kernel_vectors_are_evaluated_at_tt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    epochs: list[float] = []

    class _Reader:
        def position(self, _center: int, _target: int, jd: float):
            epochs.append(jd)
            return (0.0, 0.0, 0.0)

    monkeypatch.setattr(phase, "get_reader", lambda: _Reader())
    monkeypatch.setattr(
        phase,
        "_barycentric",
        lambda _body, jd, _reader: epochs.append(jd) or (2.0, 0.0, 0.0),
    )
    monkeypatch.setattr(
        phase,
        "_earth_barycentric",
        lambda jd, _reader: epochs.append(jd) or (1.0, 1.0, 0.0),
    )
    monkeypatch.setattr(
        ephemeris_time,
        "_ut1_to_ephemeris_tt",
        lambda jd, _reader: jd + 0.75,
    )

    assert 0.0 <= phase.phase_angle("Venus", 700.0) <= 180.0
    assert epochs == [700.75, 700.75, 700.75]

    epochs.clear()
    assert phase.apparent_magnitude("Venus", 700.0) < 0.0
    assert epochs == [700.75, 700.75, 700.75]


def test_planetary_hours_utc_adapter_converts_instant_and_civil_noons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    noons: list[float] = []
    monkeypatch.setattr(planetary_hours, "utc_to_ut1", lambda jd: jd - 0.01)
    monkeypatch.setattr(
        planetary_hours,
        "_sunrise_sunset",
        lambda jd_noon, _lat, _lon, _reader: (
            noons.append(jd_noon) or jd_noon - 0.75,
            jd_noon - 0.25,
        ),
    )
    monkeypatch.setattr(
        planetary_hours,
        "_refine_sunrise",
        lambda jd_guess, _lat, _lon, _reader, is_rise: jd_guess,
    )

    result = planetary_hours._planetary_hours_from_utc(
        800.500001, 0.0, 0.0, reader=object()
    )

    assert result.date_jd == pytest.approx(800.490001)
    assert noons == [800.99, 801.99]


def test_predictive_planetary_hours_passes_raw_utc_to_private_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[float] = []
    fake_facade = SimpleNamespace(jd_from_datetime=lambda _dt: 900.0)
    monkeypatch.setattr(predictive_facade, "_facade_module", lambda: fake_facade)
    monkeypatch.setattr(
        planetary_hours,
        "_planetary_hours_from_utc",
        lambda jd, *_args, **_kwargs: received.append(jd),
    )

    _Predictive().planetary_hours(_DT, 40.0, -75.0)

    assert received == [900.0]


def test_subplanetary_facade_chart_resolves_utc_to_ut1_and_tt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, float] = {}

    def fake_planet_at(_body, jd, **kwargs):
        received["planet_ut1"] = jd
        received["planet_tt"] = kwargs["jd_tt"]
        return SimpleNamespace(longitude=10.0, latitude=0.0)

    chart = SimpleNamespace(
        jd_ut=1000.0,
        planets={"Sun": object()},
    )
    monkeypatch.setattr(julian, "utc_to_ut1", lambda jd: jd + 0.25)
    monkeypatch.setattr(julian, "utc_to_tt", lambda jd: jd + 0.75)
    monkeypatch.setattr(obliquity, "nutation", lambda jd: (0.0, 0.0))
    monkeypatch.setattr(obliquity, "true_obliquity", lambda jd: 23.4)
    monkeypatch.setattr(
        julian,
        "apparent_sidereal_time",
        lambda jd, *_args: received.setdefault("sidereal", jd) or 20.0,
    )
    monkeypatch.setattr("moira.planets.planet_at", fake_planet_at)
    monkeypatch.setattr(
        "moira.coordinates.ecliptic_to_equatorial",
        lambda *_args: (10.0, 20.0),
    )

    astrocartography.subplanetary_from_chart(chart)

    assert received == {
        "sidereal": 1000.25,
        "planet_ut1": 1000.25,
        "planet_tt": 1000.75,
    }


def test_predictive_progression_resolves_natal_datetime_to_ut1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[float] = []
    fake_facade = SimpleNamespace(
        jd_from_datetime=lambda _dt: 1100.0,
        utc_to_ut1=lambda jd: jd + 0.25,
        secondary_progression=lambda jd, *_args, **_kwargs: received.append(jd),
    )
    monkeypatch.setattr(predictive_facade, "_facade_module", lambda: fake_facade)

    _Predictive().progression(_DT, _DT)

    assert received == [1100.25]


def test_utc_named_event_properties_invert_ut1_before_formatting() -> None:
    jd_utc = julian.jd_from_datetime(_DT)
    jd_ut1 = julian.utc_to_ut1(jd_utc)
    hour = planetary_hours.PlanetaryHour(
        1, "Sun", jd_ut1, jd_ut1 + 1.0 / 24.0, True
    )
    progression = progressions.ProgressedChart(
            "Secondary Progression",
            jd_ut1,
            jd_ut1,
            _DT,
            0.0,
            {},
    )
    paran = parans.ParanCrossing("Sun", "Rising", jd_ut1, "test")
    phenomenon = phenomena.PhenomenonEvent("Moon", "New Moon", jd_ut1, 0.0)
    rendered = (
        (hour.start_utc, hour.start_calendar_utc),
        (progression.datetime_utc, progression.calendar_utc),
        (paran.datetime_utc, paran.calendar_utc),
        (phenomenon.datetime_utc, phenomenon.calendar_utc),
    )

    for rendered_datetime, rendered_calendar in rendered:
        assert abs((rendered_datetime - _DT).total_seconds()) < 1.0e-5
        assert rendered_calendar.isoformat().startswith("2026-07-17T12:00:00")


def test_progression_age_uses_a_single_resolved_ut1_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(progressions, "jd_from_datetime", lambda _dt: 1200.0)
    monkeypatch.setattr(progressions, "utc_to_ut1", lambda jd: jd + 0.25)

    assert progressions._age_years(1000.25, _DT, 100.0) == pytest.approx(2.0)


def test_panchanga_utc_adapter_separates_ut1_astronomy_from_civil_weekday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(julian, "utc_to_ut1", lambda jd: jd - 0.01)
    monkeypatch.setattr(
        "moira.sidereal.tropical_to_sidereal",
        lambda longitude, _jd, **_kwargs: longitude,
    )
    monkeypatch.setattr(
        "moira.sidereal.nakshatra_of",
        lambda *_args, **_kwargs: object(),
    )

    result = panchanga._panchanga_from_utc(10.0, 40.0, 100.5)

    assert result.jd == pytest.approx(100.49)
    assert result.vara.index == int(100.5 + 1.5) % 7
    assert result.vara.index != int(result.jd + 1.5) % 7


def test_vedic_chart_adapters_route_UT1_to_astronomical_callees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidereal_epochs: list[float] = []
    received: dict[str, object] = {}
    bodies = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    planets = {
        body: SimpleNamespace(longitude=float(index * 20), speed=1.0, latitude=0.0)
        for index, body in enumerate(bodies, start=1)
    }
    chart = SimpleNamespace(
        jd_ut=1300.0,
        planets=planets,
        longitudes=lambda include_nodes=True: {
            body: position.longitude for body, position in planets.items()
        },
    )
    houses = SimpleNamespace(asc=15.0, cusps=tuple(float(i * 30) for i in range(12)))

    def fake_sidereal(longitude, jd, **_kwargs):
        sidereal_epochs.append(jd)
        return longitude

    def fake_shadbala(*args, **_kwargs):
        received["shadbala_jd"] = args[3]
        return object()

    def fake_ashtakavarga(longitudes, **_kwargs):
        received["ashtakavarga"] = longitudes
        return object()

    fake_facade = SimpleNamespace(
        Ayanamsa=SimpleNamespace(LAHIRI="Lahiri"),
        utc_to_ut1=lambda jd: jd + 0.25,
        tropical_to_sidereal=fake_sidereal,
        is_day_chart=lambda *_args: True,
        shadbala=fake_shadbala,
        ashtakavarga=fake_ashtakavarga,
    )
    monkeypatch.setattr(vedic_facade, "_facade_module", lambda: fake_facade)
    monkeypatch.setattr(
        vedic_facade._panchanga,
        "_panchanga_from_utc",
        lambda *_args, **_kwargs: SimpleNamespace(
            tithi=SimpleNamespace(number=1),
            vara_lord="Sun",
        ),
    )

    _Vedic().shadbala_for_chart(chart, houses)
    assert received["shadbala_jd"] == 1300.25
    assert sidereal_epochs == [1300.25] * 7

    sidereal_epochs.clear()
    _Vedic().ashtakavarga_for_chart(chart, houses)
    assert sidereal_epochs == [1300.25] * 8


def test_classical_astronomy_adapters_preserve_utc_day_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    class _Day:
        hours = [SimpleNamespace(ruler="Sun")]

        def hour_at(self, jd):
            received["hour_at"] = jd
            return SimpleNamespace(ruler="Moon")

    def fake_almuten(*_args, **kwargs):
        received["almuten_kwargs"] = kwargs
        return "Sun"

    fake_facade = SimpleNamespace(
        Ayanamsa=SimpleNamespace(LAHIRI="Lahiri"),
        jd_from_datetime=lambda _dt: 1400.0,
        utc_to_ut1=lambda jd: jd + 0.25,
        vimshottari=lambda _longitude, jd, **_kwargs: received.setdefault("vimshottari", jd),
        is_day_chart=lambda *_args: True,
        almuten_figuris=fake_almuten,
    )
    chart = SimpleNamespace(
        jd_ut=1500.0,
        _reader=object(),
        planets={"Moon": SimpleNamespace(longitude=20.0)},
        longitudes=lambda include_nodes=False: {"Sun": 10.0, "Moon": 20.0},
    )
    houses = SimpleNamespace(
        asc=0.0,
        cusps=tuple(float(i * 30) for i in range(12)),
        geo_lat=40.0,
        geo_lon=-75.0,
    )
    monkeypatch.setattr(classical_facade, "_facade_module", lambda: fake_facade)
    monkeypatch.setattr(
        "moira.transits.prenatal_syzygy",
        lambda jd, **_kwargs: (received.setdefault("syzygy", jd) and (1490.0, "New Moon")),
    )
    monkeypatch.setattr(
        "moira.planets.planet_at",
        lambda *_args, **_kwargs: SimpleNamespace(longitude=30.0),
    )
    monkeypatch.setattr(
        planetary_hours,
        "_planetary_hours_from_utc",
        lambda jd, *_args, **_kwargs: received.setdefault("hours_utc", jd) and _Day(),
    )

    _Classical().vimshottari_dasha(chart, _DT)
    result = _Classical().almuten_figuris(chart, houses, strict=True)

    assert result == "Sun"
    assert received["vimshottari"] == 1400.25
    assert received["syzygy"] == 1500.25
    assert received["hours_utc"] == 1500.0
    assert received["hour_at"] == 1500.25
