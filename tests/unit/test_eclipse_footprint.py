from __future__ import annotations

import math

import pytest

import moira
import moira.eclipse as eclipse
import moira.facade as facade
import moira.sky.eclipse as sky_eclipse
from moira.eclipse import (
    EclipseCalculator,
    EclipseData,
    EclipseEvent,
    EclipseType,
    SolarEclipseFootprintBoundaryKind,
    SolarEclipseFootprintContacts,
    SolarEclipseFootprintPoint,
    SolarEclipseFootprintTopology,
    SolarEclipseLimitTrack,
    SolarEclipsePenumbralContact,
    SolarEclipsePenumbralContactKind,
    SolarEclipseVisibilityFootprint,
)
from moira.julian import julian_day


def _event(
    *,
    jd_ut: float = 3.0,
    is_solar: bool = True,
    central: bool = False,
) -> EclipseEvent:
    eclipse_type = EclipseType(
        is_partial=is_solar and not central,
        is_annular=False,
        is_total=is_solar and central,
        is_hybrid=False,
        magnitude_umbral=0.5 if is_solar else 0.0,
        magnitude_penumbra=0.5 if is_solar else 0.0,
    )
    data = EclipseData(
        sun_longitude=0.0,
        moon_longitude=0.0,
        node_longitude=0.0,
        galactic_center_longitude=0.0,
        moon_latitude=0.0,
        sun_apparent_radius=0.25,
        moon_apparent_radius=0.25,
        moon_distance_km=384_400.0,
        earth_shadow_apparent_radius=0.0,
        earth_penumbra_apparent_radius=0.0,
        sun_stone=0,
        moon_stone=0,
        node_stone=0,
        south_node_stone=28,
        angular_separation_3d=0.0,
        solar_topocentric_separation=0.25,
        sun_node_distance=0.0,
        is_eclipse_season=is_solar,
        is_solar_eclipse=is_solar,
        is_lunar_eclipse=False,
        eclipse_type=eclipse_type,
        eclipse_magnitude=0.5 if is_solar else 0.0,
        saros_index=0.0,
        metonic_year=0.0,
        metonic_is_reset=False,
        moon_parallax=1.0,
        sun_side=0,
        sun_pos_in_side=0,
    )
    return EclipseEvent(jd_ut=jd_ut, data=data)


def _point(
    jd_ut: float,
    latitude_deg: float = 0.0,
    longitude_deg: float = 0.0,
) -> SolarEclipseFootprintPoint:
    return SolarEclipseFootprintPoint(
        jd_ut=jd_ut,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
    )


def _contact(
    kind: SolarEclipsePenumbralContactKind,
    jd_ut: float,
) -> SolarEclipsePenumbralContact:
    return SolarEclipsePenumbralContact(kind=kind, point=_point(jd_ut))


def _contacts(*, two_limit: bool) -> SolarEclipseFootprintContacts:
    return SolarEclipseFootprintContacts(
        p1=_contact(SolarEclipsePenumbralContactKind.P1, 1.0),
        p2=(
            _contact(SolarEclipsePenumbralContactKind.P2, 2.0)
            if two_limit
            else None
        ),
        p3=(
            _contact(SolarEclipsePenumbralContactKind.P3, 4.0)
            if two_limit
            else None
        ),
        p4=_contact(SolarEclipsePenumbralContactKind.P4, 5.0),
    )


def _track(
    kind: SolarEclipseFootprintBoundaryKind,
    *,
    component_id: int = 0,
    segment_id: int = 0,
    start: float = 2.0,
    end: float = 4.0,
) -> SolarEclipseLimitTrack:
    return SolarEclipseLimitTrack(
        kind=kind,
        component_id=component_id,
        segment_id=segment_id,
        points=(_point(start), _point(end)),
    )


def _tracks(*, two_limit: bool) -> list[SolarEclipseLimitTrack]:
    tracks = [
        _track(SolarEclipseFootprintBoundaryKind.SUNRISE, start=1.0, end=2.0),
        _track(SolarEclipseFootprintBoundaryKind.SUNSET, start=4.0, end=5.0),
        _track(SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH),
    ]
    if two_limit:
        tracks.append(
            _track(
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
                start=1.0,
                end=5.0,
            )
        )
    return tracks


def _footprint(*, two_limit: bool) -> SolarEclipseVisibilityFootprint:
    topology = (
        SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP
        if two_limit
        else SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED
    )
    return SolarEclipseVisibilityFootprint(
        event=_event(central=two_limit),
        greatest=_point(3.0, 12.0, -45.0),
        topology=topology,
        contacts=_contacts(two_limit=two_limit),
        tracks=_tracks(two_limit=two_limit),
        ephemeris="DE441/LE441",
    )


def test_footprint_enum_values_are_stable() -> None:
    assert {kind.value for kind in SolarEclipseFootprintBoundaryKind} == {
        "penumbral_north",
        "penumbral_south",
        "sunrise",
        "sunset",
    }
    assert {kind.value for kind in SolarEclipsePenumbralContactKind} == {
        "p1",
        "p2",
        "p3",
        "p4",
    }
    assert {kind.value for kind in SolarEclipseFootprintTopology} == {
        "one_limit_connected",
        "two_limit_two_loop",
    }


def test_footprint_public_exports_share_governing_identity() -> None:
    names = (
        "SolarEclipseFootprintBoundaryKind",
        "SolarEclipsePenumbralContactKind",
        "SolarEclipseFootprintTopology",
        "SolarEclipseFootprintPoint",
        "SolarEclipsePenumbralContact",
        "SolarEclipseFootprintContacts",
        "SolarEclipseLimitTrack",
        "SolarEclipseVisibilityFootprint",
    )
    for name in names:
        governing = getattr(eclipse, name)
        assert getattr(moira, name) is governing
        assert getattr(facade, name) is governing
        assert getattr(sky_eclipse, name) is governing
    assert hasattr(moira.Moira, "solar_eclipse_footprint")


def test_footprint_point_and_event_offer_bce_safe_utc_calendar() -> None:
    jd_ut = julian_day(-100, 6, 15)
    point = _point(jd_ut)
    event = _event(jd_ut=jd_ut)

    assert point.calendar_utc.year == -100
    assert event.calendar_utc.year == -100
    with pytest.raises(ValueError, match="cannot represent astronomical year"):
        _ = point.datetime_utc


def test_continuous_site_admission_never_discards_an_observed_interior_peak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        eclipse,
        "_penumbral_clearance_km",
        lambda shadow, _xyz: 2.0 if shadow == 1.0 else -1.0,
    )

    maximum = eclipse._continuous_site_maximum_clearance(
        lambda epoch: epoch,
        (0.0, 0.0, 0.0),
        0.5,
        (0.0, 1.0, 2.0),
    )

    assert maximum == 2.0


def test_footprint_point_normalizes_real_values_and_accepts_geographic_edges() -> None:
    point = SolarEclipseFootprintPoint(
        jd_ut=3,
        latitude_deg=90,
        longitude_deg=-180,
    )

    assert point.jd_ut == 3.0
    assert point.latitude_deg == 90.0
    assert point.longitude_deg == -180.0


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("jd_ut", True, TypeError),
        ("jd_ut", math.nan, ValueError),
        ("latitude_deg", math.inf, ValueError),
        ("longitude_deg", -math.inf, ValueError),
        ("latitude_deg", 90.000001, ValueError),
        ("longitude_deg", 180.000001, ValueError),
    ],
)
def test_footprint_point_rejects_non_finite_or_out_of_range_values(
    field: str,
    value: object,
    error: type[Exception],
) -> None:
    values: dict[str, object] = {
        "jd_ut": 3.0,
        "latitude_deg": 0.0,
        "longitude_deg": 0.0,
    }
    values[field] = value

    with pytest.raises(error):
        SolarEclipseFootprintPoint(**values)  # type: ignore[arg-type]


def test_contact_coerces_named_kind_and_requires_a_footprint_point() -> None:
    contact = SolarEclipsePenumbralContact(kind="p1", point=_point(1.0))

    assert contact.kind is SolarEclipsePenumbralContactKind.P1
    with pytest.raises(ValueError, match="invalid solar penumbral contact kind"):
        SolarEclipsePenumbralContact(kind="u1", point=_point(1.0))
    with pytest.raises(TypeError, match="must be a SolarEclipseFootprintPoint"):
        SolarEclipsePenumbralContact(
            kind=SolarEclipsePenumbralContactKind.P1,
            point=object(),  # type: ignore[arg-type]
        )


def test_contacts_require_identity_pairing_and_strict_p1_through_p4_order() -> None:
    contacts = _contacts(two_limit=True)

    assert contacts.p2 is not None
    assert contacts.p3 is not None
    with pytest.raises(ValueError, match="p1 must carry p1"):
        SolarEclipseFootprintContacts(
            p1=_contact(SolarEclipsePenumbralContactKind.P2, 1.0),
            p2=None,
            p3=None,
            p4=_contact(SolarEclipsePenumbralContactKind.P4, 5.0),
        )
    with pytest.raises(ValueError, match="both be present or both be absent"):
        SolarEclipseFootprintContacts(
            p1=_contact(SolarEclipsePenumbralContactKind.P1, 1.0),
            p2=_contact(SolarEclipsePenumbralContactKind.P2, 2.0),
            p3=None,
            p4=_contact(SolarEclipsePenumbralContactKind.P4, 5.0),
        )
    with pytest.raises(ValueError, match="strictly ordered"):
        SolarEclipseFootprintContacts(
            p1=_contact(SolarEclipsePenumbralContactKind.P1, 1.0),
            p2=_contact(SolarEclipsePenumbralContactKind.P2, 4.0),
            p3=_contact(SolarEclipsePenumbralContactKind.P3, 3.0),
            p4=_contact(SolarEclipsePenumbralContactKind.P4, 5.0),
        )


def test_limit_track_defensively_copies_points_and_coerces_kind() -> None:
    source = [_point(1.0), _point(2.0)]
    track = SolarEclipseLimitTrack(
        kind="sunrise",
        component_id=0,
        segment_id=0,
        points=source,  # type: ignore[arg-type]
    )
    source.append(_point(3.0))

    assert track.kind is SolarEclipseFootprintBoundaryKind.SUNRISE
    assert isinstance(track.points, tuple)
    assert tuple(point.jd_ut for point in track.points) == (1.0, 2.0)


@pytest.mark.parametrize(
    ("component_id", "segment_id", "points", "error"),
    [
        (True, 0, (_point(1.0), _point(2.0)), TypeError),
        (-1, 0, (_point(1.0), _point(2.0)), ValueError),
        (0, True, (_point(1.0), _point(2.0)), TypeError),
        (0, -1, (_point(1.0), _point(2.0)), ValueError),
        (0, 0, (_point(1.0),), ValueError),
        (0, 0, (_point(2.0), _point(2.0)), ValueError),
        (0, 0, (_point(2.0), _point(1.0)), ValueError),
        (0, 0, (_point(1.0), object()), TypeError),
    ],
)
def test_limit_track_requires_valid_identity_and_strict_time_order(
    component_id: object,
    segment_id: object,
    points: tuple[object, ...],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.SUNRISE,
            component_id=component_id,  # type: ignore[arg-type]
            segment_id=segment_id,  # type: ignore[arg-type]
            points=points,  # type: ignore[arg-type]
        )


def test_visibility_footprint_defensively_copies_tracks_and_fixes_metadata() -> None:
    source = _tracks(two_limit=False)
    footprint = SolarEclipseVisibilityFootprint(
        event=_event(),
        greatest=_point(3.0),
        topology="one_limit_connected",
        contacts=_contacts(two_limit=False),
        tracks=source,  # type: ignore[arg-type]
        ephemeris="DE441/LE441",
    )
    source.clear()

    assert footprint.topology is SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED
    assert isinstance(footprint.tracks, tuple)
    assert len(footprint.tracks) == 3
    assert footprint.surface_model == "WGS84_ZERO_ELEVATION"
    assert footprint.limb_model == "SPHERICAL_MEAN_LIMB"
    assert footprint.time_scale == "UT1"
    assert footprint.atmospheric_refraction is False


def test_visibility_footprint_accepts_both_governing_topologies() -> None:
    one_limit = _footprint(two_limit=False)
    two_limit = _footprint(two_limit=True)

    assert one_limit.contacts.p2 is None
    assert {
        track.kind
        for track in one_limit.tracks
        if track.kind
        in {
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        }
    } == {SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH}
    assert two_limit.contacts.p2 is not None
    assert {
        track.kind
        for track in two_limit.tracks
        if track.kind
        in {
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        }
    } == {
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
    }


def test_visibility_footprint_rejects_topology_contact_or_limit_mismatches() -> None:
    with pytest.raises(ValueError, match="one-limit topology"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=True),
            tracks=_tracks(two_limit=True),
            ephemeris="DE441/LE441",
        )
    with pytest.raises(ValueError, match="two-limit topology"):
        SolarEclipseVisibilityFootprint(
            event=_event(central=True),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            contacts=_contacts(two_limit=False),
            tracks=_tracks(two_limit=False),
            ephemeris="DE441/LE441",
        )
    with pytest.raises(ValueError, match="requires a central solar eclipse event"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            contacts=_contacts(two_limit=True),
            tracks=_tracks(two_limit=True),
            ephemeris="DE441/LE441",
        )
    with pytest.raises(ValueError, match="one-limit topology"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=_tracks(two_limit=True),
            ephemeris="DE441/LE441",
        )


def test_visibility_footprint_requires_unique_track_identities_and_closures() -> None:
    duplicate = _tracks(two_limit=False)
    duplicate.append(
        _track(
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            start=2.0,
            end=3.0,
        )
    )
    with pytest.raises(ValueError, match="identities must be unique"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=duplicate,
            ephemeris="DE441/LE441",
        )

    disconnected_limit = _tracks(two_limit=False)
    disconnected_limit.append(
        _track(
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            component_id=1,
        )
    )
    with pytest.raises(ValueError, match="exactly one connected component"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=disconnected_limit,
            ephemeris="DE441/LE441",
        )

    missing_sunset = [
        track
        for track in _tracks(two_limit=False)
        if track.kind is not SolarEclipseFootprintBoundaryKind.SUNSET
    ]
    with pytest.raises(ValueError, match="requires sunrise and sunset"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=missing_sunset,
            ephemeris="DE441/LE441",
        )

    open_limit = _tracks(two_limit=False)
    open_limit[-1] = _track(
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
        start=2.1,
        end=4.0,
    )
    with pytest.raises(ValueError, match="exactly two sunrise/sunset incidences"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=open_limit,
            ephemeris="DE441/LE441",
        )

    degenerate_two_loop = _tracks(two_limit=True)
    degenerate_two_loop[-1] = _track(
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
    )
    with pytest.raises(ValueError, match="disjoint north/south horizon incidences"):
        SolarEclipseVisibilityFootprint(
            event=_event(central=True),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            contacts=_contacts(two_limit=True),
            tracks=degenerate_two_loop,
            ephemeris="DE441/LE441",
        )

    crossing_horizon = _tracks(two_limit=True)
    crossing_horizon[0] = SolarEclipseLimitTrack(
        kind=SolarEclipseFootprintBoundaryKind.SUNRISE,
        component_id=0,
        segment_id=0,
        points=(_point(1.0), _point(2.0), _point(4.0)),
    )
    with pytest.raises(ValueError, match="must remain within P1-P2 or P3-P4"):
        SolarEclipseVisibilityFootprint(
            event=_event(central=True),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            contacts=_contacts(two_limit=True),
            tracks=crossing_horizon,
            ephemeris="DE441/LE441",
        )


def test_visibility_footprint_accepts_folded_component_with_two_segments() -> None:
    fold = _point(3.0, 10.0, 20.0)
    tracks = [
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.SUNRISE,
            component_id=0,
            segment_id=0,
            points=(_point(1.0), _point(2.0), _point(2.5)),
        ),
        _track(SolarEclipseFootprintBoundaryKind.SUNSET, start=4.0, end=5.0),
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            component_id=0,
            segment_id=0,
            points=(_point(2.0), fold),
        ),
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            component_id=0,
            segment_id=1,
            points=(_point(2.5), fold),
        ),
    ]

    footprint = SolarEclipseVisibilityFootprint(
        event=_event(),
        greatest=_point(3.0),
        topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
        contacts=_contacts(two_limit=False),
        tracks=tracks,
        ephemeris="DE441/LE441",
    )

    penumbral = tuple(
        track
        for track in footprint.tracks
        if track.kind is SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH
    )
    assert tuple(track.segment_id for track in penumbral) == (0, 1)


def test_visibility_footprint_requires_solar_event_epoch_and_contact_window() -> None:
    with pytest.raises(ValueError, match="event must be a solar eclipse"):
        SolarEclipseVisibilityFootprint(
            event=_event(is_solar=False),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=_tracks(two_limit=False),
            ephemeris="DE441/LE441",
        )
    with pytest.raises(ValueError, match="greatest point epoch"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0001),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=_tracks(two_limit=False),
            ephemeris="DE441/LE441",
        )
    with pytest.raises(ValueError, match="strictly within P1/P4"):
        SolarEclipseVisibilityFootprint(
            event=_event(jd_ut=0.5),
            greatest=_point(0.5),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=_tracks(two_limit=False),
            ephemeris="DE441/LE441",
        )
    with pytest.raises(ValueError, match="strictly within P2/P3"):
        SolarEclipseVisibilityFootprint(
            event=_event(jd_ut=1.5, central=True),
            greatest=_point(1.5),
            topology=SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            contacts=_contacts(two_limit=True),
            tracks=_tracks(two_limit=True),
            ephemeris="DE441/LE441",
        )

    outside = _tracks(two_limit=False)
    outside[0] = _track(
        SolarEclipseFootprintBoundaryKind.SUNRISE,
        start=0.5,
        end=2.0,
    )
    with pytest.raises(ValueError, match="within P1 through P4"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=outside,
            ephemeris="DE441/LE441",
        )

    detached_contacts = [
        _track(
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            start=1.1,
            end=2.0,
        ),
        _track(
            SolarEclipseFootprintBoundaryKind.SUNSET,
            start=4.0,
            end=4.9,
        ),
        _track(SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH),
    ]
    with pytest.raises(ValueError, match="must belong to the sunrise/sunset graph"):
        SolarEclipseVisibilityFootprint(
            event=_event(),
            greatest=_point(3.0),
            topology=SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            contacts=_contacts(two_limit=False),
            tracks=detached_contacts,
            ephemeris="DE441/LE441",
        )


@pytest.mark.parametrize("sample_count", [True, 9.0, "9", None])
def test_footprint_rejects_non_integer_sample_count_before_search(
    monkeypatch: pytest.MonkeyPatch,
    sample_count: object,
) -> None:
    sentinel_reader = object()
    monkeypatch.setattr(eclipse, "get_reader", lambda: sentinel_reader)
    monkeypatch.setattr(
        EclipseCalculator,
        "_search_solar_eclipse",
        lambda *args, **kwargs: pytest.fail("search must not run"),
    )
    calculator = EclipseCalculator()

    with pytest.raises(TypeError, match="sample_count must be an integer"):
        calculator.solar_eclipse_footprint(
            2_451_545.0,
            sample_count=sample_count,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("sample_count", [8, 722])
def test_footprint_rejects_out_of_range_sample_count_before_search(
    monkeypatch: pytest.MonkeyPatch,
    sample_count: int,
) -> None:
    sentinel_reader = object()
    monkeypatch.setattr(eclipse, "get_reader", lambda: sentinel_reader)
    monkeypatch.setattr(
        EclipseCalculator,
        "_search_solar_eclipse",
        lambda *args, **kwargs: pytest.fail("search must not run"),
    )
    calculator = EclipseCalculator()

    with pytest.raises(ValueError, match="sample_count must be between 9 and 721"):
        calculator.solar_eclipse_footprint(
            2_451_545.0,
            sample_count=sample_count,
        )
