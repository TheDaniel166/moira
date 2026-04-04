from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from moira.bridges.harmograms import (
    HarmogramProgressionFamily,
    build_converse_solar_arc_directed_harmogram_samples,
    build_directed_to_natal_harmogram_samples,
    build_dynamic_harmogram_samples,
    build_dynamic_harmogram_samples_for_range,
    build_minor_progressed_harmogram_samples,
    build_progressed_to_natal_harmogram_samples,
    build_progression_family_harmogram_samples,
    build_secondary_progressed_harmogram_samples,
    build_transit_to_natal_harmogram_samples,
    build_transit_to_natal_harmogram_samples_for_range,
    filter_harmogram_body_positions,
)
from moira.facade import Chart
from moira.harmograms import (
    HarmogramChartDomain,
    HarmogramIntensityPolicy,
    HarmogramPolicy,
    HarmogramTraceFamily,
    HarmonicDomain,
    PointSetHarmonicVectorPolicy,
    harmogram_trace,
)
from moira.julian import jd_from_datetime
from moira.planets import PlanetData
from moira.progressions import ProgressedChart, ProgressedPosition


def _chart(longitudes: dict[str, float]) -> Chart:
    planets = {
        name: PlanetData(
            name=name,
            longitude=longitude,
            latitude=0.0,
            distance=1.0,
            speed=1.0,
            retrograde=False,
        )
        for name, longitude in longitudes.items()
    }
    return Chart(
        jd_ut=2460000.5,
        planets=planets,
        nodes={},
        obliquity=23.4,
        delta_t=69.0,
    )


def _progressed_chart(longitudes: dict[str, float], chart_type: str = "Secondary Progression") -> ProgressedChart:
    positions = {
        name: ProgressedPosition(name=name, longitude=longitude)
        for name, longitude in longitudes.items()
    }
    return ProgressedChart(
        chart_type=chart_type,
        natal_jd_ut=2460000.5,
        progressed_jd_ut=2460100.5,
        target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        solar_arc_deg=0.0,
        positions=positions,
    )


class _FakeMoira:
    def __init__(self) -> None:
        self.chart_calls: list[dict[str, object]] = []
        self.progression_calls: list[tuple[str, datetime, datetime, list[str] | None]] = []

    def chart(
        self,
        dt: datetime,
        bodies: list[str] | None = None,
        include_nodes: bool = True,
        observer_lat: float | None = None,
        observer_lon: float | None = None,
        observer_elev_m: float = 0.0,
    ) -> Chart:
        self.chart_calls.append(
            {
                "dt": dt,
                "bodies": bodies,
                "include_nodes": include_nodes,
                "observer_lat": observer_lat,
                "observer_lon": observer_lon,
                "observer_elev_m": observer_elev_m,
            }
        )
        day_offset = float(len(self.chart_calls) - 1)
        return _chart({"Sun": 10.0 + day_offset, "Moon": 120.0 + day_offset, "Mars": 220.0 + day_offset})

    def progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        self.progression_calls.append(("progression", natal_dt, target_dt, bodies))
        return _progressed_chart({"Sun": 20.0, "Moon": 150.0, "Mars": 210.0})

    def minor_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        self.progression_calls.append(("minor_progression", natal_dt, target_dt, bodies))
        return _progressed_chart({"Sun": 25.0, "Moon": 160.0, "Mars": 215.0}, chart_type="Minor Progression")

    def solar_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        self.progression_calls.append(("solar_arc_directions", natal_dt, target_dt, bodies))
        return _progressed_chart({"Sun": 30.0, "Moon": 170.0, "Mars": 225.0}, chart_type="Solar Arc Direction")

    def converse_solar_arc(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        self.progression_calls.append(("converse_solar_arc", natal_dt, target_dt, bodies))
        return _progressed_chart(
            {"Sun": 35.0, "Moon": 175.0, "Mars": 230.0},
            chart_type="Converse Solar Arc Direction",
        )


def test_build_dynamic_harmogram_samples_accepts_chart_and_mapping_sources() -> None:
    samples = build_dynamic_harmogram_samples(
        [
            (0.0, _chart({"Sun": 10.0, "Moon": 120.0})),
            (1.0, {"Sun": 20.0, "Moon": 130.0}),
        ]
    )

    assert samples[0]["time"] == 0.0
    assert samples[0]["positions"][0]["name"] == "Sun"
    assert len(samples[1]["positions"]) == 2


def test_filter_harmogram_body_positions_supports_include_and_exclude_filters() -> None:
    positions = filter_harmogram_body_positions(
        {"Sun": 20.0, "Moon": 130.0, "Mars": 210.0},
        bodies=("Sun", "Moon"),
        exclude_bodies=("Moon",),
    )

    assert positions == [{"name": "Sun", "degree": 20.0}]


def test_filter_harmogram_body_positions_rejects_empty_result() -> None:
    with pytest.raises(ValueError, match="removed every position"):
        filter_harmogram_body_positions({"Sun": 20.0}, exclude_bodies=("Sun",))


def test_build_transit_to_natal_harmogram_samples_accepts_native_chart_sources() -> None:
    natal = _chart({"Sun": 0.0, "Moon": 90.0})
    transits = [
        (0.0, _chart({"Sun": 10.0, "Moon": 120.0})),
        (1.0, _chart({"Sun": 15.0, "Moon": 125.0})),
    ]

    samples = build_transit_to_natal_harmogram_samples(transits, natal)

    assert samples[0]["natal_positions"][0]["name"] == "Sun"
    assert samples[1]["transit_positions"][1]["degree"] == 125.0


def test_build_directed_and_progressed_harmogram_samples_accept_progressed_charts() -> None:
    natal = _chart({"Sun": 5.0, "Moon": 80.0})
    directed = build_directed_to_natal_harmogram_samples(
        [
            (0.0, _progressed_chart({"Sun": 15.0, "Moon": 100.0}, chart_type="Solar Arc Direction")),
        ],
        natal,
    )
    progressed = build_progressed_to_natal_harmogram_samples(
        [
            (0.0, _progressed_chart({"Sun": 25.0, "Moon": 140.0})),
        ],
        natal,
    )

    assert directed[0]["directed_positions"][0]["degree"] == 15.0
    assert progressed[0]["progressed_positions"][1]["degree"] == 140.0


def test_transit_bridge_samples_feed_harmogram_trace_end_to_end() -> None:
    natal = _chart({"Sun": 0.0, "Moon": 90.0})
    transits = [
        (0.0, _chart({"Sun": 10.0, "Moon": 120.0})),
        (1.0, _chart({"Sun": 15.0, "Moon": 125.0})),
    ]
    samples = build_transit_to_natal_harmogram_samples(transits, natal)

    trace = harmogram_trace(
        samples,
        harmonic_numbers=(2,),
        policy=HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
            intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
            chart_domain=HarmogramChartDomain.TRANSIT_TO_NATAL_TRACE,
            trace_family=HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS,
        ),
    )

    assert trace.get_series(2).harmonic_number == 2
    assert len(trace.get_series(2).samples) == 2


def test_build_secondary_progressed_harmogram_samples_uses_native_progression_surface() -> None:
    engine = _FakeMoira()
    natal_dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    target_dates = (
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    samples = build_secondary_progressed_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        progression_bodies=("Sun", "Moon"),
        bodies=("Sun", "Moon"),
    )

    assert samples[0]["time"] == jd_from_datetime(target_dates[0])
    assert samples[0]["progressed_positions"] == [
        {"name": "Sun", "degree": 20.0},
        {"name": "Moon", "degree": 150.0},
    ]
    assert engine.progression_calls == [
        ("progression", natal_dt, target_dates[0], ["Sun", "Moon"]),
        ("progression", natal_dt, target_dates[1], ["Sun", "Moon"]),
    ]


def test_build_progression_family_harmogram_samples_routes_minor_and_solar_arc_to_correct_keys() -> None:
    engine = _FakeMoira()
    natal_dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    target_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)

    minor_samples = build_minor_progressed_harmogram_samples(
        engine,
        natal_dt,
        (target_dt,),
        bodies=("Sun",),
    )
    directed_samples = build_converse_solar_arc_directed_harmogram_samples(
        engine,
        natal_dt,
        (target_dt,),
        bodies=("Sun",),
    )

    assert "progressed_positions" in minor_samples[0]
    assert minor_samples[0]["progressed_positions"] == [{"name": "Sun", "degree": 25.0}]
    assert "directed_positions" in directed_samples[0]
    assert directed_samples[0]["directed_positions"] == [{"name": "Sun", "degree": 35.0}]


def test_build_progression_family_harmogram_samples_accepts_explicit_family_enum() -> None:
    engine = _FakeMoira()
    natal_dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    target_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)

    samples = build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        (target_dt,),
        family=HarmogramProgressionFamily.SOLAR_ARC,
        bodies=("Moon",),
    )

    assert samples[0]["directed_positions"] == [{"name": "Moon", "degree": 170.0}]
    assert engine.progression_calls[-1][0] == "solar_arc_directions"


def test_build_dynamic_harmogram_samples_for_range_uses_chart_sampling_and_julian_times() -> None:
    engine = _FakeMoira()
    start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    stop_dt = datetime(2025, 1, 3, tzinfo=timezone.utc)

    samples = build_dynamic_harmogram_samples_for_range(
        engine,
        start_dt,
        stop_dt,
        timedelta(days=1),
        chart_bodies=("Sun", "Moon", "Mars"),
        bodies=("Sun", "Moon"),
        observer_lat=40.7,
        observer_lon=-74.0,
    )

    assert [sample["time"] for sample in samples] == [
        jd_from_datetime(start_dt),
        jd_from_datetime(start_dt + timedelta(days=1)),
        jd_from_datetime(stop_dt),
    ]
    assert samples[0]["positions"] == [
        {"name": "Sun", "degree": 10.0},
        {"name": "Moon", "degree": 120.0},
    ]
    assert engine.chart_calls[0]["observer_lat"] == 40.7
    assert engine.chart_calls[0]["bodies"] == ["Sun", "Moon", "Mars"]


def test_build_transit_to_natal_harmogram_samples_for_range_reuses_filtered_natal_positions() -> None:
    engine = _FakeMoira()
    natal = _chart({"Sun": 0.0, "Moon": 90.0, "Mars": 180.0})
    start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    stop_dt = datetime(2025, 1, 2, tzinfo=timezone.utc)

    samples = build_transit_to_natal_harmogram_samples_for_range(
        engine,
        natal,
        start_dt,
        stop_dt,
        timedelta(days=1),
        bodies=("Sun", "Moon"),
        exclude_bodies=("Moon",),
    )

    assert samples[0]["natal_positions"] == [{"name": "Sun", "degree": 0.0}]
    assert samples[1]["transit_positions"] == [{"name": "Sun", "degree": 11.0}]


def test_build_dynamic_harmogram_samples_for_range_rejects_non_positive_step() -> None:
    engine = _FakeMoira()
    start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    stop_dt = datetime(2025, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="step must be positive"):
        build_dynamic_harmogram_samples_for_range(engine, start_dt, stop_dt, timedelta(0))
