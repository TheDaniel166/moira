"""Adversarial UTC/UT1/TT checks for server-only adapter boundaries."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from moira.asteroids import ASTEROID_NAIF, AsteroidData
from moira.comets import COMET_NAIF, CometData
from moira.panchanga import panchanga_at
from moira.sade_sati import SadeSatiResult
from moira_server.models.asteroids import AsteroidPositionRequest
from moira_server.models.comets import CometPositionRequest
from moira_server.models.galactic_houses import GalacticHousesChartRequest
from moira_server.models.geodetic import GeodeticChartBackedChartRequest
from moira_server.models.jaimini import JaiminiChartRequest
from moira_server.models.dasha import DashaCurrentRequest, DashaNatalRequest
from moira_server.models.progressions import (
    HouseFrameArcRequest,
    HouseFrameNatalRequest,
    HouseFrameProgressionRequest,
    ProgressionNatalRequest,
    SecondaryProgressionRequest,
)
from moira_server.models.sade_sati import SadeSatiWindowsRequest
from moira_server.models.shadbala import ShadbalaChartRequest
from moira_server.models.sidereal_context import SiderealChartBaseRequest
from moira_server.models.varshaphal import VarshaphalChartRequest
from moira_server.models.vedic_extended import KalavelaRequest
from moira_server.services.sidereal_context import SiderealChartRequirements


_DT = datetime(2026, 6, 13, 12, tzinfo=timezone.utc)
_JD_UTC = 2_461_205.0
_JD_UT1 = _JD_UTC + 0.625 / 86_400.0
_JD_TT = _JD_UTC + 69.2 / 86_400.0


class _Reader:
    def __init__(self, covered: set[int] | None = None) -> None:
        self._covered = frozenset(covered or ())

    def covered_bodies(self) -> frozenset[int]:
        return self._covered


def test_small_body_adapters_pass_ut1_to_both_engine_paths(monkeypatch) -> None:
    from moira_server.services import asteroids, comets

    asteroid_calls: list[float] = []
    comet_calls: list[float] = []
    monkeypatch.setattr(asteroids, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(comets, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(
        asteroids,
        "asteroid_at",
        lambda _body, jd_ut, *, reader=None: (
            asteroid_calls.append(jd_ut)
            or AsteroidData(
                name="Ceres",
                naif_id=ASTEROID_NAIF["Ceres"],
                longitude=15.0,
                latitude=1.0,
                distance=300_000_000.0,
                speed=0.2,
                retrograde=False,
            )
        ),
    )
    monkeypatch.setattr(
        comets,
        "comet_at",
        lambda _body, jd_ut, *, reader=None: (
            comet_calls.append(jd_ut)
            or CometData(
                name="Halley",
                naif_id=COMET_NAIF["Halley"],
                longitude=215.0,
                latitude=-12.0,
                distance=4.0,
                speed=0.08,
                retrograde=False,
                sign="Scorpio",
                sign_symbol="Sc",
            )
        ),
    )
    engine = SimpleNamespace(
        _reader=_Reader({ASTEROID_NAIF["Ceres"], COMET_NAIF["Halley"]})
    )

    asteroid = asteroids.compute_asteroid_position(
        engine, AsteroidPositionRequest(dt=_DT, body="Ceres")
    )
    comet = comets.compute_comet_position(
        engine, CometPositionRequest(dt=_DT, body="Halley")
    )

    assert asteroid_calls == [_JD_UT1]
    assert comet_calls == [_JD_UT1]
    assert asteroid.provenance.jd_ut == _JD_UT1
    assert comet.provenance.jd_ut == _JD_UT1


def test_astrocartography_sidereal_context_routes_ut1_and_tt(monkeypatch) -> None:
    from moira_server.services import astrocartography

    seen: dict[str, float] = {}
    monkeypatch.setattr(astrocartography, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(astrocartography, "utc_to_tt", lambda _jd: _JD_TT)
    monkeypatch.setattr(
        astrocartography,
        "nutation",
        lambda jd: (seen.setdefault("nutation", jd) or 0.25, 0.0),
    )
    monkeypatch.setattr(
        astrocartography,
        "true_obliquity",
        lambda jd: seen.setdefault("obliquity", jd) or 23.4,
    )

    def fake_sidereal(jd_ut: float, _dpsi: float, _obliquity: float) -> float:
        seen["sidereal"] = jd_ut
        return 123.0

    monkeypatch.setattr(astrocartography, "apparent_sidereal_time", fake_sidereal)

    _dpsi, _obl, gmst, jd_ut, jd_tt = astrocartography._sidereal_context(_JD_UTC)

    assert seen == {
        "nutation": _JD_TT,
        "obliquity": _JD_TT,
        "sidereal": _JD_UT1,
    }
    assert (gmst, jd_ut, jd_tt) == (123.0, _JD_UT1, _JD_TT)


def test_galactic_houses_resolves_both_scales_before_reduction(monkeypatch) -> None:
    from moira_server.services import galactic_houses

    seen: dict[str, float] = {}
    cusps = object()
    monkeypatch.setattr(galactic_houses, "jd_from_datetime", lambda _dt: _JD_UTC)
    monkeypatch.setattr(galactic_houses, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(galactic_houses, "utc_to_tt", lambda _jd: _JD_TT)
    monkeypatch.setattr(
        galactic_houses,
        "nutation",
        lambda jd: (seen.setdefault("nutation", jd) or 0.2, 0.0),
    )
    monkeypatch.setattr(
        galactic_houses,
        "true_obliquity",
        lambda jd: seen.setdefault("obliquity", jd) or 23.4,
    )

    def fake_lst(jd_ut, _longitude, _dpsi, _obliquity):
        seen["sidereal"] = jd_ut
        return 42.0

    def fake_houses(jd_ut, _latitude, _longitude):
        seen["houses"] = jd_ut
        return cusps

    monkeypatch.setattr(galactic_houses, "local_sidereal_time", fake_lst)
    monkeypatch.setattr(galactic_houses, "calculate_galactic_houses", fake_houses)

    result = galactic_houses.compute_galactic_house_cusps(
        GalacticHousesChartRequest(dt=_DT, latitude=40.0, longitude=-74.0)
    )

    assert result.cusps is cusps
    assert result.provenance.jd_ut == _JD_UT1
    assert result.provenance.jd_tt == _JD_TT
    assert seen == {
        "nutation": _JD_TT,
        "obliquity": _JD_TT,
        "sidereal": _JD_UT1,
        "houses": _JD_UT1,
    }


def test_geodetic_and_sidereal_context_use_ut1_for_ayanamsa(monkeypatch) -> None:
    from moira_server.services import geodetic, sidereal_context

    planet = SimpleNamespace(longitude=120.0, speed=1.0)
    chart = SimpleNamespace(
        jd_ut=_JD_UTC,
        datetime_utc=_DT,
        planets={"Sun": planet},
        nodes={},
    )
    engine = SimpleNamespace(chart=lambda *_args, **_kwargs: chart)
    seen: list[tuple[str, float]] = []

    monkeypatch.setattr(geodetic, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(geodetic, "utc_to_tt", lambda _jd: _JD_TT)
    monkeypatch.setattr(geodetic, "true_obliquity", lambda jd: 23.4)
    monkeypatch.setattr(
        geodetic,
        "ayanamsa",
        lambda jd, _system: seen.append(("geodetic", jd)) or 24.0,
    )
    geodetic_chart = object()
    monkeypatch.setattr(geodetic, "geodetic_chart", lambda *_args, **_kwargs: geodetic_chart)

    geodetic_result = geodetic.compute_geodetic_chart_backed_chart(
        engine,
        GeodeticChartBackedChartRequest(
            dt=_DT,
            geo_longitude=-74.0,
            geo_latitude=40.0,
            zodiac="sidereal",
            ayanamsa_system="Lahiri",
        ),
    )

    monkeypatch.setattr(sidereal_context, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(
        sidereal_context,
        "ayanamsa",
        lambda jd, _system: seen.append(("sidereal_context", jd)) or 24.0,
    )
    sidereal_result = sidereal_context.derive_sidereal_chart_context(
        engine,
        SiderealChartBaseRequest(dt=_DT),
        SiderealChartRequirements(required_bodies=("Sun",)),
    )

    assert geodetic_result.chart is geodetic_chart
    assert geodetic_result.provenance.jd_ut == _JD_UT1
    assert geodetic_result.provenance.jd_tt == _JD_TT
    assert sidereal_result.jd_ut == _JD_UT1
    assert seen == [("geodetic", _JD_UT1), ("sidereal_context", _JD_UT1)]


def test_jaimini_and_shadbala_receive_resolved_ut1(monkeypatch) -> None:
    from moira_server.services import jaimini, shadbala

    names = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    planets = {
        name: SimpleNamespace(longitude=10.0 + index * 31.0, speed=1.0, latitude=0.1)
        for index, name in enumerate(names)
    }
    chart = SimpleNamespace(
        jd_ut=_JD_UTC,
        planets=planets,
        nodes={},
        longitudes=lambda include_nodes=False: {
            name: planet.longitude for name, planet in planets.items()
        },
    )
    houses = SimpleNamespace(asc=0.0)
    engine = SimpleNamespace(
        chart=lambda *_args, **_kwargs: chart,
        houses=lambda *_args, **_kwargs: houses,
    )
    seen: list[float] = []

    monkeypatch.setattr(jaimini, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(
        jaimini,
        "tropical_to_sidereal",
        lambda longitude, jd, system: seen.append(jd) or longitude,
    )
    jaimini.compute_jaimini_chart(engine, JaiminiChartRequest(dt=_DT))

    sentinel = object()
    captured: dict[str, float] = {}
    monkeypatch.setattr(shadbala, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(
        shadbala,
        "tropical_to_sidereal",
        lambda longitude, jd, system: seen.append(jd) or longitude,
    )
    monkeypatch.setattr(
        shadbala,
        "_panchanga_from_utc",
        lambda *_args, **_kwargs: SimpleNamespace(
            tithi=SimpleNamespace(number=1), vara_lord="Sun"
        ),
    )
    monkeypatch.setattr(
        shadbala,
        "shadbala",
        lambda **kwargs: captured.update(jd=kwargs["jd"]) or sentinel,
    )
    monkeypatch.setattr(shadbala, "validate_shadbala_output", lambda _result: None)
    monkeypatch.setattr(shadbala, "graha_yuddha_pairs", lambda *_args: ())
    monkeypatch.setattr(shadbala, "is_day_chart", lambda *_args: True)

    assert shadbala.compute_shadbala_chart(
        engine,
        ShadbalaChartRequest(dt=_DT, observer_lat=40.0, observer_lon=-74.0),
    ) is sentinel
    assert seen == [_JD_UT1] * 14
    assert captured == {"jd": _JD_UT1}


def test_panchanga_uses_ut1_but_keeps_utc_civil_weekday(monkeypatch) -> None:
    from moira import julian
    from moira_server.services import panchanga

    jd_utc = 100.499_999
    jd_ut = 100.500_001
    monkeypatch.setattr(julian, "utc_to_ut1", lambda _jd: jd_ut)

    result = panchanga._panchanga_from_utc(
        280.0,
        40.0,
        jd_utc,
        ayanamsa_system="Lahiri",
        policy=None,
    )
    civil = panchanga_at(280.0, 40.0, jd_utc)

    assert result.jd == jd_ut
    assert result.vara == civil.vara
    assert result.vara_lord == civil.vara_lord


def test_sade_sati_window_bounds_are_converted_to_ut1(monkeypatch) -> None:
    from moira_server.services import sade_sati

    seen: list[tuple[float, float]] = []
    monkeypatch.setattr(sade_sati, "utc_to_ut1", lambda jd: jd + 0.625 / 86_400.0)

    def fake_windows(_moon, start_jd, end_jd, **_kwargs):
        seen.append((start_jd, end_jd))
        return SadeSatiResult(
            janma_rashi_index=1,
            start_jd=start_jd,
            end_jd=end_jd,
            ayanamsa_system="Lahiri",
            windows=(),
        )

    monkeypatch.setattr(sade_sati, "sade_sati_windows", fake_windows)
    request = SadeSatiWindowsRequest(
        natal_moon_sidereal_lon=35.0,
        start_dt=_DT,
        end_dt=datetime(2027, 6, 13, 12, tzinfo=timezone.utc),
    )
    response = sade_sati.compute_sade_sati_windows(
        SimpleNamespace(_reader_obj=object()), request
    )

    assert seen == [(response.start_jd, response.end_jd)]
    assert response.start_jd != _JD_UTC


def test_primary_directions_proxy_exposes_ut1_tt_and_exact_delta_t(monkeypatch) -> None:
    from moira_server.services import primary_directions

    monkeypatch.setattr(primary_directions, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(primary_directions, "utc_to_tt", lambda _jd: _JD_TT)
    base = SimpleNamespace(jd_ut=_JD_UTC, marker="base")

    chart = primary_directions._PrimaryDirectionsChartClock(base)

    assert chart.jd_ut == _JD_UT1
    assert chart.jd_tt == _JD_TT
    assert chart.delta_t == pytest.approx((_JD_TT - _JD_UT1) * 86_400.0)
    assert chart.marker == "base"


def test_kalavela_routes_ut1_astronomy_without_rewriting_civil_result(monkeypatch) -> None:
    """UTC must own civil selection once the engine exposes a dual-clock policy.

    Until then the adapter supplies UT1 for astronomy and faithfully preserves
    the engine's weekday result instead of silently manufacturing UTC parity.
    """
    from moira import facade, upagrahas
    from moira_server.routers import vedic_extended

    seen: list[float] = []
    monkeypatch.setattr(vedic_extended, "jd_from_datetime", lambda _dt: _JD_UTC)
    monkeypatch.setattr(vedic_extended, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(facade, "use_reader_override", lambda _reader: nullcontext())
    monkeypatch.setattr(
        upagrahas,
        "kalavela_upagrahas",
        lambda jd_ut, *_args, **_kwargs: (
            seen.append(jd_ut)
            or SimpleNamespace(
                is_day_birth=True,
                weekday_index=6,
                arc_start_jd=jd_ut - 0.25,
                arc_end_jd=jd_ut + 0.25,
                ayanamsa_system="Lahiri",
                upagrahas={},
            )
        ),
    )

    response = vedic_extended.kalavelas_route(
        KalavelaRequest(dt=_DT, latitude=40.0, longitude=-74.0),
        SimpleNamespace(_reader_obj=object()),
    )

    assert seen == [_JD_UT1]
    assert response.weekday_index == 6
    assert response.arc_start_jd < _JD_UT1 < response.arc_end_jd


def test_progression_services_route_natal_datetimes_to_ut1(monkeypatch) -> None:
    from moira_server.services import progressions

    seen: list[tuple[str, float]] = []
    secondary = object()
    daily = object()
    angle_arc = object()
    monkeypatch.setattr(progressions, "jd_from_datetime", lambda _dt: _JD_UTC)
    monkeypatch.setattr(progressions, "utc_to_ut1", lambda _jd: _JD_UT1)
    monkeypatch.setattr(
        progressions,
        "secondary_progression",
        lambda **kwargs: (
            seen.append(("secondary", kwargs["natal_jd_ut"])) or secondary
        ),
    )
    monkeypatch.setattr(
        progressions,
        "daily_house_frame",
        lambda **kwargs: seen.append(("daily", kwargs["natal_jd_ut"])) or daily,
    )
    monkeypatch.setitem(
        progressions._HOUSE_FRAME_ARC_DISPATCH,
        "ascendant_arc",
        (
            lambda **kwargs: (
                seen.append(("angle_arc", kwargs["natal_jd_ut"])) or angle_arc
            ),
            lambda **_kwargs: object(),
        ),
    )

    natal = ProgressionNatalRequest(dt=_DT)
    assert progressions.compute_secondary_progression_chart(
        SimpleNamespace(),
        SecondaryProgressionRequest(natal=natal, target_dt=_DT),
    ) is secondary

    house_natal = HouseFrameNatalRequest(
        dt=_DT,
        latitude=40.0,
        longitude=-74.0,
    )
    assert progressions.compute_daily_house_frame(
        SimpleNamespace(),
        HouseFrameProgressionRequest(natal=house_natal, target_dt=_DT),
    ) is daily
    assert progressions.compute_house_frame_arc_chart(
        SimpleNamespace(),
        HouseFrameArcRequest(
            natal=house_natal,
            target_dt=_DT,
            method="ascendant_arc",
        ),
    ) is angle_arc

    assert seen == [
        ("secondary", _JD_UT1),
        ("daily", _JD_UT1),
        ("angle_arc", _JD_UT1),
    ]


def test_dasha_service_routes_natal_and_current_datetimes_to_ut1(monkeypatch) -> None:
    from moira_server.services import dasha

    current_dt = datetime(2027, 6, 13, 12, tzinfo=timezone.utc)
    jd_current_utc = _JD_UTC + 365.0
    jd_current_ut1 = _JD_UT1 + 365.0
    encoded = {_DT: _JD_UTC, current_dt: jd_current_utc}
    converted = {_JD_UTC: _JD_UT1, jd_current_utc: jd_current_ut1}
    seen: dict[str, tuple[float, float]] = {}
    active = object()
    line = object()

    monkeypatch.setattr(dasha, "jd_from_datetime", encoded.__getitem__)
    monkeypatch.setattr(dasha, "utc_to_ut1", converted.__getitem__)

    def fake_current_dasha(_moon, natal_jd, current_jd, **_kwargs):
        seen["clocks"] = (natal_jd, current_jd)
        return active

    monkeypatch.setattr(dasha, "current_dasha", fake_current_dasha)
    monkeypatch.setattr(dasha, "dasha_active_line", lambda _active: line)
    chart = SimpleNamespace(
        longitudes=lambda include_nodes=False: {"Moon": 123.0},
    )
    engine = SimpleNamespace(chart=lambda _dt: chart)

    result = dasha.compute_dasha_active_line(
        engine,
        DashaCurrentRequest(
            natal=DashaNatalRequest(dt=_DT),
            current_dt=current_dt,
        ),
    )

    assert result is line
    assert seen == {"clocks": (_JD_UT1, jd_current_ut1)}


def test_varshaphal_separates_birth_civil_year_from_ut1_astronomy(monkeypatch) -> None:
    """A negative DUT1 at New Year must not decrement years elapsed."""
    from moira_server.services import varshaphal

    new_year_utc = datetime(2000, 1, 1, tzinfo=timezone.utc)
    jd_utc = 2_451_544.5
    jd_ut1 = jd_utc - 0.25 / 86_400.0
    sentinel = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(varshaphal, "jd_from_datetime", lambda _dt: jd_utc)
    monkeypatch.setattr(varshaphal, "utc_to_ut1", lambda _jd: jd_ut1)

    def fake_build(
        birth_jd,
        birth_civil_year,
        natal_latitude,
        natal_longitude,
        year,
        latitude,
        longitude,
        **kwargs,
    ):
        captured.update(
            birth_jd=birth_jd,
            birth_civil_year=birth_civil_year,
            year=year,
        )
        return sentinel

    monkeypatch.setattr(
        varshaphal,
        "_build_varshaphal_chart_for_birth_year",
        fake_build,
    )
    request = VarshaphalChartRequest(
        natal_dt=new_year_utc,
        natal_latitude=40.0,
        natal_longitude=-74.0,
        year=2025,
        latitude=40.0,
        longitude=-74.0,
    )

    assert varshaphal._build_chart(request) is sentinel
    assert captured == {
        "birth_jd": jd_ut1,
        "birth_civil_year": 2000,
        "year": 2025,
    }


def test_varshaphal_natal_offset_owns_doctrinal_civil_year(monkeypatch) -> None:
    """Equivalent instants may lawfully carry different local birth dates."""
    from moira_server.services import varshaphal

    local_birth = datetime(
        2005,
        1,
        1,
        0,
        0,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )
    utc_representation = local_birth.astimezone(timezone.utc)
    captured_years: list[int] = []
    sentinel = object()

    monkeypatch.setattr(varshaphal, "jd_from_datetime", lambda _dt: _JD_UTC)
    monkeypatch.setattr(varshaphal, "utc_to_ut1", lambda _jd: _JD_UT1)

    def fake_build(_birth_jd, birth_civil_year, *_args, **_kwargs):
        captured_years.append(birth_civil_year)
        return sentinel

    monkeypatch.setattr(
        varshaphal,
        "_build_varshaphal_chart_for_birth_year",
        fake_build,
    )

    def request(dt: datetime) -> VarshaphalChartRequest:
        return VarshaphalChartRequest(
            natal_dt=dt,
            natal_latitude=40.0,
            natal_longitude=-74.0,
            year=2025,
            latitude=40.0,
            longitude=-74.0,
        )

    assert varshaphal._build_chart(request(local_birth)) is sentinel
    assert varshaphal._build_chart(request(utc_representation)) is sentinel
    assert local_birth.timestamp() == utc_representation.timestamp()
    assert captured_years == [2005, 2004]
