from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from moira.constants import Body
from moira.parans import (
    Paran,
    ParanContourExtraction,
    ParanContourPoint,
    ParanContourSegment,
    ParanCrossing,
    ParanFieldSample,
    ParanSiteResult,
    ParanPolicy,
    ParanSignature,
    CIRCLE_TYPES,
    _SUPPORTED_METRICS,
    analyze_paran_field,
    analyze_paran_field_structure,
    consolidate_paran_contours,
    extract_paran_field_contours,
    _crossing_times,
    _extract_cell_contour_segments,
    _interpolate_contour_point,
    _validate_circle,
    _validate_metric,
    _validate_orb_non_negative,
    evaluate_paran_site,
    evaluate_paran_stability,
    find_parans,
    natal_parans,
    sample_paran_field,
)
from moira.rise_set import find_phenomena, get_transit


def _crossing(
    body: str,
    circle: str,
    jd: float,
    source_method: str = "get_transit",
    altitude_policy: float | None = None,
) -> ParanCrossing:
    return ParanCrossing(
        body=body,
        circle=circle,
        jd=jd,
        source_method=source_method,
        altitude_policy=altitude_policy,
    )


def _paran(
    body1: str,
    circle1: str,
    jd1: float,
    body2: str,
    circle2: str,
    jd2: float,
) -> Paran:
    crossing1 = _crossing(body=body1, circle=circle1, jd=jd1)
    crossing2 = _crossing(body=body2, circle=circle2, jd=jd2)
    circle_alias = {
        "Rising": "rise",
        "Setting": "set",
        "Culminating": "mc",
        "AntiCulminating": "ic",
    }
    axis_alias = {
        "Rising": "horizon",
        "Setting": "horizon",
        "Culminating": "meridian",
        "AntiCulminating": "meridian",
    }
    event_family = "-".join(sorted([circle_alias[circle1], circle_alias[circle2]]))
    axis_family = "-".join(sorted([axis_alias[circle1], axis_alias[circle2]]))
    body_family = "planet-planet"

    return Paran(
        body1=body1,
        body2=body2,
        circle1=circle1,
        circle2=circle2,
        jd1=jd1,
        jd2=jd2,
        orb_min=abs(jd1 - jd2) * 24.0 * 60.0,
        crossing1=crossing1,
        crossing2=crossing2,
        signature=ParanSignature(
            event_family=event_family,
            axis_family=axis_family,
            body_family=body_family,
        ),
    )


def _field_sample(
    lat: float,
    lon: float,
    matched: bool,
    exactness_score: float = 0.0,
    survival_rate: float | None = None,
) -> ParanFieldSample:
    paran = None
    strength = None
    stability = None
    if matched:
        paran = _paran(Body.SUN, "Rising", 2000.0, Body.MOON, "Culminating", 2000.001)
        strength = paran.strength
        strength = type(strength)(
            orb_minutes=strength.orb_minutes,
            exactness_score=exactness_score,
            model=strength.model,
        )
        if survival_rate is not None:
            stability = SimpleNamespace(survival_rate=survival_rate)
    return ParanFieldSample(
        lat=lat,
        lon=lon,
        site_result=ParanSiteResult(
            lat=lat,
            lon=lon,
            matched=matched,
            paran=paran,
            strength=strength,
            stability=stability,
        ),
    )


def _segment(
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    case_index: int = 1,
    ambiguous: bool = False,
    cell_lat_min: float = 0.0,
    cell_lon_min: float = 0.0,
) -> ParanContourSegment:
    return ParanContourSegment(
        start=ParanContourPoint(lat=start[0], lon=start[1]),
        end=ParanContourPoint(lat=end[0], lon=end[1]),
        cell_lat_min=cell_lat_min,
        cell_lon_min=cell_lon_min,
        case_index=case_index,
        ambiguous=ambiguous,
    )


@pytest.mark.slow
def test_crossing_times_match_rise_set_engine() -> None:
    jd_day = 2451544.5
    lat = 51.5
    lon = -0.1

    for body in [Body.SUN, Body.MOON, "Regulus"]:
        crossings = {c.circle: c.jd for c in _crossing_times(body, jd_day, lat, lon)}
        altitude = -0.5667
        phenomena = find_phenomena(body, jd_day, lat, lon, altitude=altitude)

        if "Rise" in phenomena:
            assert crossings["Rising"] == pytest.approx(phenomena["Rise"], abs=1e-6)
        if "Set" in phenomena:
            assert crossings["Setting"] == pytest.approx(phenomena["Set"], abs=1e-6)

        assert crossings["Culminating"] == pytest.approx(
            get_transit(body, jd_day, lat, lon, upper=True),
            abs=1e-6,
        )
        assert crossings["AntiCulminating"] == pytest.approx(
            get_transit(body, jd_day, lat, lon, upper=False),
            abs=1e-6,
        )
        assert jd_day <= crossings["AntiCulminating"] < jd_day + 1.0


@pytest.mark.slow
def test_find_parans_returns_sorted_unique_body_pairs() -> None:
    parans = find_parans([Body.SUN, Body.MOON, "Regulus"], 2451544.5, 51.5, -0.1, orb_minutes=30.0)

    assert parans == sorted(parans, key=lambda p: p.orb_min)
    seen = {(p.body1, p.body2, p.circle1, p.circle2, round(p.jd, 9)) for p in parans}
    assert len(seen) == len(parans)
    for paran in parans:
        assert paran.body1 != paran.body2
        assert paran.orb_min >= 0.0
        assert paran.jd == pytest.approx((paran.jd1 + paran.jd2) / 2.0)
        assert paran.delta_minutes == paran.orb_min
        assert paran.crossing1 is not None
        assert paran.crossing2 is not None
        assert paran.crossing1.jd == paran.jd1
        assert paran.crossing2.jd == paran.jd2
        assert paran.crossing1.body == paran.body1
        assert paran.crossing2.body == paran.body2
        assert paran.crossing1.circle == paran.circle1
        assert paran.crossing2.circle == paran.circle2
        assert paran.signature is not None
        assert paran.event_family == paran.signature.event_family
        assert paran.axis_family == paran.signature.axis_family
        assert paran.body_family == paran.signature.body_family


def test_find_parans_preserves_event_truth_and_classifies(monkeypatch: pytest.MonkeyPatch) -> None:
    sun_crossings = [
        _crossing(
            body=Body.SUN,
            circle="Rising",
            jd=100.0,
            source_method="find_phenomena",
            altitude_policy=-0.5667,
        ),
        _crossing(body=Body.SUN, circle="Culminating", jd=100.25),
    ]
    regulus_crossings = [
        _crossing(body="Regulus", circle="Culminating", jd=100.001),
    ]

    def fake_crossing_times(body, jd_day, lat, lon):
        if body == Body.SUN:
            return sun_crossings
        if body == "Regulus":
            return regulus_crossings
        return []

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    parans = find_parans([Body.SUN, "Regulus"], 99.5, 51.5, -0.1, orb_minutes=2.0)

    assert len(parans) == 1
    paran = parans[0]
    assert paran.body1 == Body.SUN
    assert paran.body2 == "Regulus"
    assert paran.circle1 == "Rising"
    assert paran.circle2 == "Culminating"
    assert paran.jd1 == 100.0
    assert paran.jd2 == 100.001
    assert paran.jd == pytest.approx(100.0005)
    assert paran.delta_minutes == paran.orb_min
    assert paran.crossing1 is sun_crossings[0]
    assert paran.crossing2 is regulus_crossings[0]
    assert paran.crossing1.jd == paran.jd1
    assert paran.crossing2.jd == paran.jd2
    assert paran.signature is not None
    assert paran.event_family == "mc-rise"
    assert paran.axis_family == "horizon-meridian"
    assert paran.body_family == "planet-star"
    assert paran.signature.event_family == "mc-rise"
    assert paran.signature.axis_family == "horizon-meridian"
    assert paran.signature.body_family == "planet-star"


@pytest.mark.parametrize(
    ("crossings_by_body", "expected_event_family", "expected_axis_family", "expected_body_family"),
    [
        (
            {
                Body.SUN: [_crossing(body=Body.SUN, circle="Culminating", jd=200.0)],
                Body.MOON: [_crossing(body=Body.MOON, circle="Culminating", jd=200.001)],
            },
            "mc-mc",
            "meridian-meridian",
            "planet-planet",
        ),
        (
            {
                Body.SUN: [_crossing(body=Body.SUN, circle="Culminating", jd=300.0)],
                Body.MOON: [_crossing(body=Body.MOON, circle="AntiCulminating", jd=300.001)],
            },
            "ic-mc",
            "meridian-meridian",
            "planet-planet",
        ),
        (
            {
                "Regulus": [_crossing(body="Regulus", circle="Culminating", jd=400.0)],
                "Antares": [_crossing(body="Antares", circle="AntiCulminating", jd=400.001)],
            },
            "ic-mc",
            "meridian-meridian",
            "star-star",
        ),
    ],
)
def test_find_parans_classifies_additional_signature_families(
    monkeypatch: pytest.MonkeyPatch,
    crossings_by_body: dict[str, list[ParanCrossing]],
    expected_event_family: str,
    expected_axis_family: str,
    expected_body_family: str,
) -> None:
    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    bodies = list(crossings_by_body.keys())
    parans = find_parans(bodies, 199.5, 51.5, -0.1, orb_minutes=2.0)

    assert len(parans) == 1
    paran = parans[0]
    signature = paran.signature
    assert signature is not None
    assert paran.crossing1 is not None
    assert paran.crossing2 is not None
    assert paran.crossing1.jd == paran.jd1
    assert paran.crossing2.jd == paran.jd2
    assert paran.jd == pytest.approx((paran.jd1 + paran.jd2) / 2.0)
    assert paran.delta_minutes == paran.orb_min
    assert paran.circle1 == paran.crossing1.circle
    assert paran.circle2 == paran.crossing2.circle
    assert paran.event_family == signature.event_family
    assert paran.axis_family == signature.axis_family
    assert paran.body_family == signature.body_family
    assert signature.event_family == expected_event_family
    assert signature.axis_family == expected_axis_family
    assert signature.body_family == expected_body_family


def test_natal_parans_uses_ut_day_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, float] = {}

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0):
        captured["jd_day"] = jd_day
        return []

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)
    natal_parans([Body.SUN, Body.MOON], 2451545.2, 40.0, -74.0)

    assert captured["jd_day"] == math.floor(2451545.2 - 0.5) + 0.5


def test_default_policy_preserves_permissive_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Culminating", jd=500.0)],
        Body.MOON: [_crossing(body=Body.MOON, circle="Culminating", jd=500.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    implicit = find_parans([Body.SUN, Body.MOON], 499.5, 51.5, -0.1, orb_minutes=2.0)
    explicit = find_parans(
        [Body.SUN, Body.MOON],
        499.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(),
    )

    assert len(implicit) == 1
    assert len(explicit) == 1
    assert implicit[0].event_family == "mc-mc"
    assert explicit[0].event_family == "mc-mc"
    assert implicit[0].axis_family == "meridian-meridian"
    assert explicit[0].axis_family == "meridian-meridian"
    assert implicit[0].jd1 == explicit[0].jd1
    assert implicit[0].jd2 == explicit[0].jd2
    assert implicit[0].orb_min == explicit[0].orb_min


def test_policy_can_exclude_same_event_family(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Culminating", jd=600.0)],
        Body.MOON: [_crossing(body=Body.MOON, circle="Culminating", jd=600.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    parans = find_parans(
        [Body.SUN, Body.MOON],
        599.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(allow_same_event_family=False),
    )

    assert parans == []


def test_policy_can_exclude_same_axis_family(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Culminating", jd=700.0)],
        Body.MOON: [_crossing(body=Body.MOON, circle="AntiCulminating", jd=700.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    parans = find_parans(
        [Body.SUN, Body.MOON],
        699.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(allow_same_axis_family=False),
    )

    assert parans == []


def test_policy_can_exclude_body_family_pairings(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Rising", jd=800.0)],
        "Regulus": [_crossing(body="Regulus", circle="Culminating", jd=800.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    blocked = find_parans(
        [Body.SUN, "Regulus"],
        799.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(allowed_body_families=frozenset({"planet-planet"})),
    )
    allowed = find_parans(
        [Body.SUN, "Regulus"],
        799.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(allowed_body_families=frozenset({"planet-star"})),
    )

    assert blocked == []
    assert len(allowed) == 1
    assert allowed[0].body_family == "planet-star"


def test_policy_can_exclude_star_involvement(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Rising", jd=900.0)],
        "Regulus": [_crossing(body="Regulus", circle="Culminating", jd=900.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    parans = find_parans(
        [Body.SUN, "Regulus"],
        899.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(include_stars=False),
    )

    assert parans == []


def test_policy_can_filter_named_stars_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Rising", jd=950.0)],
        "Regulus": [_crossing(body="Regulus", circle="Culminating", jd=950.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    allowed = find_parans(
        [Body.SUN, "Regulus"],
        949.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(allowed_named_stars=frozenset({"Regulus"})),
    )
    blocked = find_parans(
        [Body.SUN, "Regulus"],
        949.5,
        51.5,
        -0.1,
        orb_minutes=2.0,
        policy=ParanPolicy(allowed_named_stars=frozenset({"Antares"})),
    )

    assert len(allowed) == 1
    assert allowed[0].crossing2 is not None
    assert allowed[0].crossing2.body == "Regulus"
    assert blocked == []


def test_paran_strength_is_derived_only_from_existing_orb_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Rising", jd=1000.0)],
        Body.MOON: [_crossing(body=Body.MOON, circle="Culminating", jd=1000.001)],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    paran = find_parans([Body.SUN, Body.MOON], 999.5, 51.5, -0.1, orb_minutes=2.0)[0]
    strength = paran.strength

    assert strength.orb_minutes == paran.orb_min
    assert strength.exactness_score == pytest.approx(1.0 / (1.0 + paran.orb_min))
    assert strength.model == "inverse_minutes"
    assert paran.jd == pytest.approx((paran.jd1 + paran.jd2) / 2.0)
    assert paran.event_family == "mc-rise"
    assert paran.axis_family == "horizon-meridian"


def test_tighter_orb_yields_stronger_exactness_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    crossings_by_body = {
        Body.SUN: [_crossing(body=Body.SUN, circle="Rising", jd=1100.0)],
        Body.MOON: [
            _crossing(body=Body.MOON, circle="Culminating", jd=1100.0005),
            _crossing(body=Body.MOON, circle="Setting", jd=1100.0015),
        ],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    parans = find_parans([Body.SUN, Body.MOON], 1099.5, 51.5, -0.1, orb_minutes=3.0)

    assert len(parans) == 2
    stronger = parans[0].strength
    weaker = parans[1].strength
    assert parans[0].orb_min < parans[1].orb_min
    assert stronger.exactness_score > weaker.exactness_score


def test_equal_orb_yields_equal_exactness_score(monkeypatch: pytest.MonkeyPatch) -> None:
    crossings_by_body = {
        Body.SUN: [
            _crossing(body=Body.SUN, circle="Rising", jd=1200.0),
            _crossing(body=Body.SUN, circle="Setting", jd=1200.01),
        ],
        Body.MOON: [
            _crossing(body=Body.MOON, circle="Culminating", jd=1200.001),
            _crossing(body=Body.MOON, circle="AntiCulminating", jd=1200.011),
        ],
    }

    def fake_crossing_times(body, jd_day, lat, lon):
        return crossings_by_body.get(body, [])

    monkeypatch.setattr("moira.parans._crossing_times", fake_crossing_times)

    parans = find_parans([Body.SUN, Body.MOON], 1199.5, 51.5, -0.1, orb_minutes=2.0)

    assert len(parans) == 2
    assert parans[0].orb_min == pytest.approx(parans[1].orb_min)
    assert parans[0].strength.exactness_score == pytest.approx(
        parans[1].strength.exactness_score
    )


def test_stability_recomputes_under_explicit_time_perturbations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1300.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1300.001,
    )
    called_jd_days: list[float] = []
    offset_to_paran = {
        -1.0: _paran(Body.SUN, "Rising", 1300.0, Body.MOON, "Culminating", 1300.0012),
        1.0: _paran(Body.SUN, "Rising", 1300.0, Body.MOON, "Culminating", 1300.0014),
    }

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        called_jd_days.append(jd_day)
        offset_minutes = round((jd_day - 1299.5) * 24.0 * 60.0, 6)
        paran = offset_to_paran.get(offset_minutes)
        return [] if paran is None else [paran]

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)

    stability = evaluate_paran_stability(
        baseline,
        jd_day=1299.5,
        lat=51.5,
        lon=-0.1,
        orb_minutes=2.0,
        time_offsets_minutes=(-1.0, 1.0),
    )

    assert called_jd_days == pytest.approx(
        [
            1299.5 - (1.0 / (24.0 * 60.0)),
            1299.5 + (1.0 / (24.0 * 60.0)),
        ]
    )
    assert stability.method == "time_anchor_perturbation"
    assert stability.offsets_minutes == (-1.0, 1.0)
    assert stability.survival_rate == 1.0
    assert stability.stable_across_window is True
    assert [sample.survived for sample in stability.samples] == [True, True]


def test_more_persistent_paran_reports_stronger_stability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1400.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1400.001,
    )
    robust_map = {
        -1.0: _paran(Body.SUN, "Rising", 1400.0, Body.MOON, "Culminating", 1400.0011),
        1.0: _paran(Body.SUN, "Rising", 1400.0, Body.MOON, "Culminating", 1400.0012),
    }
    fragile_map = {
        -1.0: _paran(Body.SUN, "Rising", 1400.0, Body.MOON, "Culminating", 1400.0018),
    }

    def make_fake_find_parans(mapping):
        def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
            offset_minutes = round((jd_day - 1399.5) * 24.0 * 60.0, 6)
            paran = mapping.get(offset_minutes)
            return [] if paran is None else [paran]

        return fake_find_parans

    monkeypatch.setattr("moira.parans.find_parans", make_fake_find_parans(robust_map))
    robust = evaluate_paran_stability(
        baseline,
        jd_day=1399.5,
        lat=51.5,
        lon=-0.1,
        time_offsets_minutes=(-1.0, 1.0),
    )

    monkeypatch.setattr("moira.parans.find_parans", make_fake_find_parans(fragile_map))
    fragile = evaluate_paran_stability(
        baseline,
        jd_day=1399.5,
        lat=51.5,
        lon=-0.1,
        time_offsets_minutes=(-1.0, 1.0),
    )

    assert robust.survival_rate > fragile.survival_rate
    assert robust.max_orb_degradation < fragile.max_orb_degradation
    assert robust.max_exactness_drop < fragile.max_exactness_drop


def test_equal_perturbation_behavior_yields_equal_stability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_a = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1500.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1500.001,
    )
    baseline_b = _paran(
        body1=Body.SUN,
        circle1="Setting",
        jd1=1500.01,
        body2=Body.MOON,
        circle2="AntiCulminating",
        jd2=1500.011,
    )

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        offset_minutes = round((jd_day - 1499.5) * 24.0 * 60.0, 6)
        if offset_minutes == -1.0:
            return [_paran(bodies[0], "Rising", 1500.0, bodies[1], "Culminating", 1500.0012)]
        if offset_minutes == 1.0:
            return [_paran(bodies[0], "Rising", 1500.0, bodies[1], "Culminating", 1500.0014)]
        return []

    def fake_find_parans_b(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        offset_minutes = round((jd_day - 1499.5) * 24.0 * 60.0, 6)
        if offset_minutes == -1.0:
            return [_paran(bodies[0], "Setting", 1500.01, bodies[1], "AntiCulminating", 1500.0112)]
        if offset_minutes == 1.0:
            return [_paran(bodies[0], "Setting", 1500.01, bodies[1], "AntiCulminating", 1500.0114)]
        return []

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)
    stability_a = evaluate_paran_stability(
        baseline_a,
        jd_day=1499.5,
        lat=51.5,
        lon=-0.1,
        time_offsets_minutes=(-1.0, 1.0),
    )

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans_b)
    stability_b = evaluate_paran_stability(
        baseline_b,
        jd_day=1499.5,
        lat=51.5,
        lon=-0.1,
        time_offsets_minutes=(-1.0, 1.0),
    )

    assert stability_a.survival_rate == stability_b.survival_rate
    assert stability_a.stable_across_window == stability_b.stable_across_window
    assert stability_a.max_orb_degradation == pytest.approx(
        stability_b.max_orb_degradation
    )
    assert stability_a.max_exactness_drop == pytest.approx(
        stability_b.max_exactness_drop
    )


def test_site_evaluation_is_deterministic_and_uses_explicit_identity_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1600.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1600.001,
    )
    closer_match = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1600.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1600.0012,
    )
    farther_match = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1600.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1600.0020,
    )
    wrong_identity = _paran(
        body1=Body.SUN,
        circle1="Setting",
        jd1=1600.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1600.0011,
    )

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        return [farther_match, wrong_identity, closer_match]

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)

    result = evaluate_paran_site(
        target,
        jd_day=1599.5,
        lat=10.0,
        lon=20.0,
        orb_minutes=2.0,
    )

    assert result.lat == 10.0
    assert result.lon == 20.0
    assert result.matched is True
    assert result.paran is closer_match
    assert result.strength is not None
    assert result.strength.orb_minutes == closer_match.orb_min
    assert result.stability is None


def test_site_evaluation_can_include_stability(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1700.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1700.001,
    )
    site_match = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1700.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1700.0011,
    )
    calls: list[tuple[float, float]] = []

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        calls.append((lat, lon))
        if lat == 30.0 and lon == -40.0:
            return [site_match]
        if lat == 30.0 and lon == -40.0 and jd_day != 1699.5:
            return [site_match]
        return [site_match]

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)

    result = evaluate_paran_site(
        target,
        jd_day=1699.5,
        lat=30.0,
        lon=-40.0,
        stability_time_offsets_minutes=(-1.0, 1.0),
    )

    assert result.matched is True
    assert result.stability is not None
    assert result.stability.offsets_minutes == (-1.0, 1.0)
    assert result.stability.survival_rate == 1.0
    assert calls


def test_site_evaluation_returns_unmatched_when_identity_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1800.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1800.001,
    )

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        return [_paran(bodies[0], "Setting", 1800.0, bodies[1], "Culminating", 1800.001)]

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)

    result = evaluate_paran_site(target, jd_day=1799.5, lat=0.0, lon=0.0)

    assert result.matched is False
    assert result.paran is None
    assert result.strength is None
    assert result.stability is None


def test_grid_evaluation_returns_structured_consistent_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _paran(
        body1=Body.SUN,
        circle1="Rising",
        jd1=1900.0,
        body2=Body.MOON,
        circle2="Culminating",
        jd2=1900.001,
    )

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None):
        if lat == 10.0 and lon == 20.0:
            return [_paran(bodies[0], "Rising", 1900.0, bodies[1], "Culminating", 1900.0011)]
        if lat == 10.0 and lon == 30.0:
            return []
        if lat == 15.0 and lon == 20.0:
            return [_paran(bodies[0], "Rising", 1900.0, bodies[1], "Culminating", 1900.0013)]
        return [_paran(bodies[0], "Setting", 1900.0, bodies[1], "Culminating", 1900.0011)]

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)

    samples = sample_paran_field(
        target,
        jd_day=1899.5,
        latitudes=[10.0, 15.0],
        longitudes=[20.0, 30.0],
    )

    assert len(samples) == 4
    assert [(sample.lat, sample.lon) for sample in samples] == [
        (10.0, 20.0),
        (10.0, 30.0),
        (15.0, 20.0),
        (15.0, 30.0),
    ]
    assert samples[0].site_result.matched is True
    assert samples[0].site_result.paran is not None
    assert samples[1].site_result.matched is False
    assert samples[1].site_result.paran is None
    assert samples[2].site_result.matched is True
    assert samples[3].site_result.matched is False


def test_field_threshold_analysis_and_regions_are_deterministic() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=0.9),
        _field_sample(0.0, 1.0, matched=True, exactness_score=0.8),
        _field_sample(0.0, 2.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=True, exactness_score=0.7),
        _field_sample(1.0, 2.0, matched=False),
        _field_sample(2.0, 0.0, matched=False),
        _field_sample(2.0, 1.0, matched=False),
        _field_sample(2.0, 2.0, matched=True, exactness_score=0.95),
    ]

    analysis = analyze_paran_field(
        samples,
        metric="exactness_score",
        threshold=0.7,
    )

    assert analysis.metric == "exactness_score"
    assert analysis.threshold == 0.7
    assert analysis.adjacency == "orthogonal"
    assert analysis.total_samples == 9
    assert analysis.active_sample_count == 4
    assert len(analysis.regions) == 2
    assert analysis.regions[0].cells == ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0))
    assert analysis.regions[0].sample_count == 3
    assert analysis.regions[0].peak_value == pytest.approx(0.9)
    assert analysis.regions[1].cells == ((2.0, 2.0),)
    assert analysis.regions[1].sample_count == 1
    assert analysis.regions[1].peak_value == pytest.approx(0.95)


def test_field_peak_detection_uses_orthogonal_neighbors() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=0.1),
        _field_sample(0.0, 1.0, matched=True, exactness_score=0.4),
        _field_sample(0.0, 2.0, matched=True, exactness_score=0.2),
        _field_sample(1.0, 0.0, matched=True, exactness_score=0.3),
        _field_sample(1.0, 1.0, matched=True, exactness_score=0.9),
        _field_sample(1.0, 2.0, matched=True, exactness_score=0.5),
        _field_sample(2.0, 0.0, matched=True, exactness_score=0.2),
        _field_sample(2.0, 1.0, matched=True, exactness_score=0.6),
        _field_sample(2.0, 2.0, matched=True, exactness_score=0.1),
    ]

    analysis = analyze_paran_field(
        samples,
        metric="exactness_score",
        threshold=0.0,
    )

    assert [(peak.lat, peak.lon, peak.value) for peak in analysis.peaks] == [
        (1.0, 1.0, pytest.approx(0.9)),
    ]


def test_field_threshold_crossing_edges_are_reported_consistently() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=0.9),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=True, exactness_score=0.8),
        _field_sample(1.0, 1.0, matched=True, exactness_score=0.7),
    ]

    analysis = analyze_paran_field(
        samples,
        metric="match_presence",
        threshold=0.5,
    )

    assert analysis.active_sample_count == 3
    assert [
        (
            edge.start_lat,
            edge.start_lon,
            edge.end_lat,
            edge.end_lon,
            edge.start_value,
            edge.end_value,
        )
        for edge in analysis.threshold_crossings
    ] == [
        (0.0, 0.0, 0.0, 1.0, 1.0, 0.0),
        (0.0, 1.0, 1.0, 1.0, 0.0, 1.0),
    ]


def test_field_analysis_supports_survival_rate_metric() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=0.5, survival_rate=1.0),
        _field_sample(0.0, 1.0, matched=True, exactness_score=0.5, survival_rate=0.4),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=True, exactness_score=0.5, survival_rate=0.8),
    ]

    analysis = analyze_paran_field(
        samples,
        metric="survival_rate",
        threshold=0.75,
    )

    assert analysis.active_sample_count == 2
    assert len(analysis.regions) == 2
    assert [(peak.lat, peak.lon, peak.value) for peak in analysis.peaks] == [
        (0.0, 0.0, pytest.approx(1.0)),
        (1.0, 1.0, pytest.approx(0.8)),
    ]


def test_contour_edge_interpolation_is_linear_for_simple_scalar_case() -> None:
    point = _interpolate_contour_point(
        point_a=(0.0, 0.0),
        value_a=0.0,
        point_b=(0.0, 10.0),
        value_b=1.0,
        threshold=0.25,
    )

    assert point.lat == pytest.approx(0.0)
    assert point.lon == pytest.approx(2.5)


def test_cell_contour_extraction_is_deterministic_for_simple_case() -> None:
    segments, ambiguous = _extract_cell_contour_segments(
        lat_min=0.0,
        lat_max=1.0,
        lon_min=0.0,
        lon_max=1.0,
        bottom_left_value=1.0,
        bottom_right_value=0.0,
        top_right_value=0.0,
        top_left_value=0.0,
        threshold=0.5,
    )

    assert ambiguous is False
    assert len(segments) == 1
    segment = segments[0]
    assert segment.case_index == 1
    assert segment.ambiguous is False
    assert segment.start.lat == pytest.approx(0.5)
    assert segment.start.lon == pytest.approx(0.0)
    assert segment.end.lat == pytest.approx(0.0)
    assert segment.end.lon == pytest.approx(0.5)


def test_contour_extraction_reports_fragments_consistently_on_sampled_grid() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=1.0),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=False),
    ]

    extraction = extract_paran_field_contours(
        samples,
        metric="match_presence",
        threshold=0.5,
    )

    assert extraction.metric == "match_presence"
    assert extraction.threshold == 0.5
    assert extraction.interpolation == "linear"
    assert extraction.ambiguous_cells == ()
    assert len(extraction.segments) == 1
    segment = extraction.segments[0]
    assert segment.case_index == 1
    assert segment.cell_lat_min == pytest.approx(0.0)
    assert segment.cell_lon_min == pytest.approx(0.0)
    assert segment.start.lat == pytest.approx(0.5)
    assert segment.start.lon == pytest.approx(0.0)
    assert segment.end.lat == pytest.approx(0.0)
    assert segment.end.lon == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("bottom_left", "bottom_right", "top_right", "top_left", "expected_case"),
    [
        (1.0, 0.0, 1.0, 0.0, 5),
        (0.0, 1.0, 0.0, 1.0, 10),
    ],
)
def test_ambiguous_cell_cases_are_reported_explicitly_and_predictably(
    bottom_left: float,
    bottom_right: float,
    top_right: float,
    top_left: float,
    expected_case: int,
) -> None:
    segments, ambiguous = _extract_cell_contour_segments(
        lat_min=0.0,
        lat_max=1.0,
        lon_min=0.0,
        lon_max=1.0,
        bottom_left_value=bottom_left,
        bottom_right_value=bottom_right,
        top_right_value=top_right,
        top_left_value=top_left,
        threshold=0.5,
    )

    assert ambiguous is True
    assert len(segments) == 2
    assert {segment.case_index for segment in segments} == {expected_case}
    assert all(segment.ambiguous for segment in segments)


def test_grid_contour_extraction_collects_ambiguous_cells() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=1.0),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=True, exactness_score=1.0),
    ]

    extraction = extract_paran_field_contours(
        samples,
        metric="match_presence",
        threshold=0.5,
    )

    assert extraction.ambiguous_cells == ((0.0, 0.0),)
    assert len(extraction.segments) == 2
    assert {segment.case_index for segment in extraction.segments} == {5}


def test_simple_fragment_chain_stitches_deterministically() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=1),
            _segment((0.0, 1.0), (0.0, 2.0), case_index=3),
            _segment((0.0, 2.0), (0.0, 3.0), case_index=2),
        ),
        ambiguous_cells=(),
    )

    path_set = consolidate_paran_contours(extraction)

    assert path_set.matching_rule == "exact_endpoint"
    assert len(path_set.paths) == 1
    path = path_set.paths[0]
    assert path.closed is False
    assert path.segment_count == 3
    assert path.ambiguous is False
    assert [(point.lat, point.lon) for point in path.points] == [
        (0.0, 0.0),
        (0.0, 1.0),
        (0.0, 2.0),
        (0.0, 3.0),
    ]
    assert path.source_case_indices == (1, 3, 2)
    assert path_set.orphan_segments == ()


def test_closed_loop_is_recognized_correctly() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=1),
            _segment((0.0, 1.0), (1.0, 1.0), case_index=2),
            _segment((1.0, 1.0), (1.0, 0.0), case_index=3),
            _segment((1.0, 0.0), (0.0, 0.0), case_index=4),
        ),
        ambiguous_cells=(),
    )

    path_set = consolidate_paran_contours(extraction)

    assert len(path_set.paths) == 1
    path = path_set.paths[0]
    assert path.closed is True
    assert path.segment_count == 4
    assert path.points[0] == path.points[-1]
    assert path_set.orphan_segments == ()


def test_open_path_is_recognized_correctly() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((1.0, 0.0), (1.0, 1.0), case_index=6),
            _segment((1.0, 1.0), (2.0, 1.0), case_index=7),
        ),
        ambiguous_cells=(),
    )

    path_set = consolidate_paran_contours(extraction)

    assert len(path_set.paths) == 1
    path = path_set.paths[0]
    assert path.closed is False
    assert [(point.lat, point.lon) for point in path.points] == [
        (1.0, 0.0),
        (1.0, 1.0),
        (2.0, 1.0),
    ]


def test_orphan_segments_are_reported_explicitly() -> None:
    orphan = _segment((5.0, 5.0), (6.0, 6.0), case_index=8)
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=1),
            _segment((0.0, 1.0), (0.0, 2.0), case_index=2),
            orphan,
        ),
        ambiguous_cells=(),
    )

    path_set = consolidate_paran_contours(extraction)

    assert len(path_set.paths) == 1
    assert path_set.orphan_segments == (orphan,)


def test_ambiguous_fragment_provenance_is_preserved_in_stitched_paths() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=5, ambiguous=True),
            _segment((0.0, 1.0), (0.0, 2.0), case_index=3, ambiguous=False),
        ),
        ambiguous_cells=((0.0, 0.0),),
    )

    path_set = consolidate_paran_contours(extraction)

    assert len(path_set.paths) == 1
    path = path_set.paths[0]
    assert path.ambiguous is True
    assert path.source_case_indices == (5, 3)


# ===========================================================================
# Phase 11 — higher-order field structure
# ===========================================================================

def _make_closed_square_extraction(
    lat0: float, lon0: float, lat1: float, lon1: float
) -> ParanContourExtraction:
    """Return a 4-segment closed square contour."""
    return ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((lat0, lon0), (lat0, lon1), case_index=2),
            _segment((lat0, lon1), (lat1, lon1), case_index=4),
            _segment((lat1, lon1), (lat1, lon0), case_index=8),
            _segment((lat1, lon0), (lat0, lon0), case_index=1),
        ),
        ambiguous_cells=(),
    )


def test_dominant_path_is_path_with_most_points() -> None:
    short = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=3),
            _segment((0.0, 1.0), (0.0, 2.0), case_index=3),
        ),
        ambiguous_cells=(),
    )
    long_ = _make_closed_square_extraction(2.0, 2.0, 4.0, 4.0)

    short_set = consolidate_paran_contours(short)
    long_set = consolidate_paran_contours(long_)

    from moira.parans import ParanContourPathSet
    combined_set = ParanContourPathSet(
        paths=short_set.paths + long_set.paths,
        orphan_segments=(),
        matching_rule="exact_endpoint",
    )

    samples = [
        _field_sample(2.0, 2.0, matched=True, exactness_score=1.0),
        _field_sample(2.0, 4.0, matched=False),
        _field_sample(4.0, 2.0, matched=False),
        _field_sample(4.0, 4.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, combined_set)

    assert structure.matching_rule == "centroid_in_polygon"
    assert structure.dominant_path_index is not None
    dominant = combined_set.paths[structure.dominant_path_index]
    assert len(dominant.points) == max(len(p.points) for p in combined_set.paths)


def test_empty_path_set_returns_no_dominant_and_empty_structure() -> None:
    from moira.parans import ParanContourPathSet
    empty_set = ParanContourPathSet(paths=(), orphan_segments=(), matching_rule="exact_endpoint")
    samples = [
        _field_sample(0.0, 0.0, matched=False),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, empty_set)

    assert structure.dominant_path_index is None
    assert structure.hierarchy == ()
    assert structure.associations == ()


def test_closed_path_contains_nested_closed_path() -> None:
    outer = _make_closed_square_extraction(0.0, 0.0, 10.0, 10.0)
    inner = _make_closed_square_extraction(3.0, 3.0, 7.0, 7.0)

    from moira.parans import ParanContourPathSet
    outer_set = consolidate_paran_contours(outer)
    inner_set = consolidate_paran_contours(inner)

    combined_set = ParanContourPathSet(
        paths=outer_set.paths + inner_set.paths,
        orphan_segments=(),
        matching_rule="exact_endpoint",
    )

    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=1.0),
        _field_sample(0.0, 10.0, matched=False),
        _field_sample(10.0, 0.0, matched=False),
        _field_sample(10.0, 10.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, combined_set)

    assert len(structure.hierarchy) == 2
    outer_entry = structure.hierarchy[0]
    inner_entry = structure.hierarchy[1]
    assert outer_entry.depth == 0
    assert outer_entry.parent_index is None
    assert inner_entry.depth == 1
    assert inner_entry.parent_index == 0


def test_open_path_has_no_parent_and_depth_zero() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=3),
            _segment((0.0, 1.0), (0.0, 2.0), case_index=3),
        ),
        ambiguous_cells=(),
    )
    path_set = consolidate_paran_contours(extraction)
    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=1.0),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, path_set)

    assert len(structure.hierarchy) == 1
    entry = structure.hierarchy[0]
    assert entry.parent_index is None
    assert entry.depth == 0


def test_non_nested_closed_paths_have_no_parent() -> None:
    left  = _make_closed_square_extraction(0.0,  0.0, 4.0, 4.0)
    right = _make_closed_square_extraction(0.0, 10.0, 4.0, 14.0)

    from moira.parans import ParanContourPathSet
    left_set  = consolidate_paran_contours(left)
    right_set = consolidate_paran_contours(right)

    combined_set = ParanContourPathSet(
        paths=left_set.paths + right_set.paths,
        orphan_segments=(),
        matching_rule="exact_endpoint",
    )

    samples = [
        _field_sample(0.0,  0.0, matched=True, exactness_score=1.0),
        _field_sample(0.0,  4.0, matched=False),
        _field_sample(4.0,  0.0, matched=False),
        _field_sample(4.0,  4.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, combined_set)

    for entry in structure.hierarchy:
        assert entry.depth == 0
        assert entry.parent_index is None


def test_peak_inside_closed_path_is_associated() -> None:
    extraction = _make_closed_square_extraction(0.0, 0.0, 10.0, 10.0)
    path_set = consolidate_paran_contours(extraction)

    samples = [
        _field_sample(0.0,  0.0, matched=True, exactness_score=0.9),
        _field_sample(0.0, 10.0, matched=False),
        _field_sample(10.0, 0.0, matched=False),
        _field_sample(10.0, 10.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, path_set)

    assert len(structure.associations) == 1
    assoc = structure.associations[0]
    if field_analysis.peaks:
        peak = field_analysis.peaks[0]
        path = path_set.paths[0]
        lat_min, lat_max, lon_min, lon_max = (
            min(p.lat for p in path.points),
            max(p.lat for p in path.points),
            min(p.lon for p in path.points),
            max(p.lon for p in path.points),
        )
        peak_in_box = lat_min <= peak.lat <= lat_max and lon_min <= peak.lon <= lon_max
        if peak_in_box:
            assert 0 in assoc.associated_peak_indices


def test_peak_outside_closed_path_bbox_is_not_associated() -> None:
    extraction = _make_closed_square_extraction(0.0, 0.0, 4.0, 4.0)
    path_set = consolidate_paran_contours(extraction)

    samples = [
        _field_sample(0.0, 0.0, matched=False),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=True, exactness_score=1.0),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, path_set)

    assert len(structure.associations) == 1
    assoc = structure.associations[0]
    for pi in assoc.associated_peak_indices:
        peak = field_analysis.peaks[pi]
        assert 0.0 <= peak.lat <= 4.0
        assert 0.0 <= peak.lon <= 4.0


def test_region_association_links_path_to_nearest_region() -> None:
    extraction = _make_closed_square_extraction(0.0, 0.0, 4.0, 4.0)
    path_set = consolidate_paran_contours(extraction)

    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=1.0),
        _field_sample(0.0, 4.0, matched=False),
        _field_sample(4.0, 0.0, matched=False),
        _field_sample(4.0, 4.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    structure = analyze_paran_field_structure(field_analysis, path_set)

    assert len(structure.associations) == 1
    assoc = structure.associations[0]
    if field_analysis.regions:
        assert assoc.region_id == field_analysis.regions[0].region_id
    else:
        assert assoc.region_id is None


def test_structure_is_deterministic_across_repeated_calls() -> None:
    extraction = _make_closed_square_extraction(0.0, 0.0, 6.0, 6.0)
    path_set = consolidate_paran_contours(extraction)

    samples = [
        _field_sample(0.0, 0.0, matched=True, exactness_score=0.8),
        _field_sample(0.0, 6.0, matched=False),
        _field_sample(6.0, 0.0, matched=False),
        _field_sample(6.0, 6.0, matched=False),
    ]
    field_analysis = analyze_paran_field(samples, metric="match_presence", threshold=0.5)

    result_a = analyze_paran_field_structure(field_analysis, path_set)
    result_b = analyze_paran_field_structure(field_analysis, path_set)

    assert result_a.dominant_path_index == result_b.dominant_path_index
    assert result_a.hierarchy == result_b.hierarchy
    assert result_a.associations == result_b.associations


# ===========================================================================
# Phase 12 — doctrine and invariant hardening
# ===========================================================================

# ---------------------------------------------------------------------------
# _validate_circle
# ---------------------------------------------------------------------------

def test_validate_circle_accepts_all_circle_types() -> None:
    for circle in CIRCLE_TYPES:
        _validate_circle(circle)


def test_validate_circle_rejects_unknown_string() -> None:
    with pytest.raises(ValueError, match="Unknown circle type"):
        _validate_circle("Ascending")


def test_validate_circle_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="Unknown circle type"):
        _validate_circle("")


def test_validate_circle_is_case_sensitive() -> None:
    with pytest.raises(ValueError, match="Unknown circle type"):
        _validate_circle("rising")


# ---------------------------------------------------------------------------
# _validate_metric
# ---------------------------------------------------------------------------

def test_validate_metric_accepts_all_supported_metrics() -> None:
    for metric in _SUPPORTED_METRICS:
        _validate_metric(metric)


def test_validate_metric_rejects_unknown_metric() -> None:
    with pytest.raises(ValueError, match="Unsupported field metric"):
        _validate_metric("bad_metric")


def test_validate_metric_error_message_names_the_bad_metric() -> None:
    with pytest.raises(ValueError, match="'unknown'"):
        _validate_metric("unknown")


# ---------------------------------------------------------------------------
# _validate_orb_non_negative
# ---------------------------------------------------------------------------

def test_validate_orb_accepts_zero() -> None:
    _validate_orb_non_negative(0.0)


def test_validate_orb_accepts_positive() -> None:
    _validate_orb_non_negative(4.0)


def test_validate_orb_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        _validate_orb_non_negative(-1.0)


# ---------------------------------------------------------------------------
# find_parans: orb guard fires at the call boundary
# ---------------------------------------------------------------------------

def test_find_parans_raises_on_negative_orb() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        find_parans([Body.SUN, Body.MOON], 2451544.5, 51.5, -0.1, orb_minutes=-1.0)


# ---------------------------------------------------------------------------
# _classify_paran: unknown circle raises immediately
# ---------------------------------------------------------------------------

def test_classify_paran_raises_on_bad_circle() -> None:
    bad_crossing = ParanCrossing(
        body=Body.SUN,
        circle="Ascending",
        jd=2451544.5,
        source_method="test",
    )
    good_crossing = ParanCrossing(
        body=Body.MOON,
        circle="Rising",
        jd=2451544.5,
        source_method="test",
    )
    from moira.parans import _classify_paran
    with pytest.raises(ValueError, match="Unknown circle type"):
        _classify_paran(bad_crossing, good_crossing)


# ---------------------------------------------------------------------------
# analyze_paran_field: metric and grid guards fire at call boundary
# ---------------------------------------------------------------------------

def test_analyze_paran_field_raises_on_bad_metric() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=False),
    ]
    with pytest.raises(ValueError, match="Unsupported field metric"):
        analyze_paran_field(samples, metric="not_a_metric", threshold=0.5)


def test_analyze_paran_field_raises_on_non_rectangular_grid() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
    ]
    with pytest.raises(ValueError, match="rectangular grid"):
        analyze_paran_field(samples, metric="match_presence", threshold=0.5)


def test_analyze_paran_field_error_mentions_expected_count() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
    ]
    with pytest.raises(ValueError, match=r"Expected \d+"):
        analyze_paran_field(samples, metric="match_presence", threshold=0.5)


# ---------------------------------------------------------------------------
# extract_paran_field_contours: same guards
# ---------------------------------------------------------------------------

def test_extract_paran_field_contours_raises_on_bad_metric() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True),
        _field_sample(0.0, 1.0, matched=False),
        _field_sample(1.0, 0.0, matched=False),
        _field_sample(1.0, 1.0, matched=False),
    ]
    with pytest.raises(ValueError, match="Unsupported field metric"):
        extract_paran_field_contours(samples, metric="garbage", threshold=0.5)


def test_extract_paran_field_contours_raises_on_non_rectangular_grid() -> None:
    samples = [
        _field_sample(0.0, 0.0, matched=True),
        _field_sample(1.0, 1.0, matched=False),
    ]
    with pytest.raises(ValueError, match="rectangular grid"):
        extract_paran_field_contours(samples, metric="match_presence", threshold=0.5)


# ---------------------------------------------------------------------------
# consolidate_paran_contours: segment_count invariant
# ---------------------------------------------------------------------------

def test_stitched_path_segment_count_equals_len_points_minus_one() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=1),
            _segment((0.0, 1.0), (0.0, 2.0), case_index=3),
            _segment((0.0, 2.0), (0.0, 3.0), case_index=2),
        ),
        ambiguous_cells=(),
    )
    path_set = consolidate_paran_contours(extraction)

    for path in path_set.paths:
        assert path.segment_count == len(path.points) - 1


def test_closed_path_segment_count_equals_len_points_minus_one() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=2),
            _segment((0.0, 1.0), (1.0, 1.0), case_index=4),
            _segment((1.0, 1.0), (1.0, 0.0), case_index=8),
            _segment((1.0, 0.0), (0.0, 0.0), case_index=1),
        ),
        ambiguous_cells=(),
    )
    path_set = consolidate_paran_contours(extraction)

    assert len(path_set.paths) == 1
    path = path_set.paths[0]
    assert path.closed is True
    assert path.segment_count == len(path.points) - 1


def test_closed_path_first_and_last_points_are_equal() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((0.0, 0.0), (0.0, 1.0), case_index=2),
            _segment((0.0, 1.0), (1.0, 1.0), case_index=4),
            _segment((1.0, 1.0), (1.0, 0.0), case_index=8),
            _segment((1.0, 0.0), (0.0, 0.0), case_index=1),
        ),
        ambiguous_cells=(),
    )
    path_set = consolidate_paran_contours(extraction)

    path = path_set.paths[0]
    assert path.points[0] == path.points[-1]


def test_lone_isolated_segment_becomes_orphan() -> None:
    extraction = ParanContourExtraction(
        metric="match_presence",
        threshold=0.5,
        interpolation="linear",
        segments=(
            _segment((9.0, 9.0), (9.0, 10.0), case_index=1),
        ),
        ambiguous_cells=(),
    )
    path_set = consolidate_paran_contours(extraction)

    assert len(path_set.paths) == 0
    assert len(path_set.orphan_segments) == 1


# ---------------------------------------------------------------------------
# evaluate_paran_stability: empty offsets edge case
# ---------------------------------------------------------------------------

def test_stability_with_empty_offsets_is_vacuously_stable() -> None:
    paran = _paran(Body.SUN, "Rising", 2451544.5, Body.MOON, "Culminating", 2451544.501)
    stability = evaluate_paran_stability(
        paran,
        jd_day=2451544.5,
        lat=51.5,
        lon=-0.1,
        time_offsets_minutes=(),
    )

    assert stability.samples == ()
    assert stability.survival_rate == pytest.approx(1.0)
    assert stability.stable_across_window is True
    assert stability.worst_orb_minutes is None
    assert stability.worst_exactness_score is None
    assert stability.max_orb_degradation is None
    assert stability.max_exactness_drop is None


