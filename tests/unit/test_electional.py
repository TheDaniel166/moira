from __future__ import annotations

import pytest

from moira.electional import (
    ElectionalPolicy,
    ElectionalWindow,
    find_electional_moments,
    find_electional_windows,
)


def test_electional_policy_converts_body_list_to_tuple() -> None:
    policy = ElectionalPolicy(bodies=["Sun", "Moon"])

    assert policy.bodies == ("Sun", "Moon")
    assert isinstance(policy.bodies, tuple)
    assert hash(policy) == hash(ElectionalPolicy(bodies=("Sun", "Moon")))


def test_electional_window_rejects_empty_qualifying_jds() -> None:
    with pytest.raises(ValueError, match="must contain at least one JD"):
        ElectionalWindow(
            jd_start=2451545.0,
            jd_end=2451545.0,
            duration_hours=0.0,
            qualifying_jds=(),
        )


def test_electional_window_rejects_mismatched_start_end() -> None:
    with pytest.raises(ValueError, match="qualifying_jds\\[0\\] must equal jd_start"):
        ElectionalWindow(
            jd_start=2451545.0,
            jd_end=2451545.5,
            duration_hours=12.0,
            qualifying_jds=(2451545.25, 2451545.5),
        )

    with pytest.raises(ValueError, match="qualifying_jds\\[-1\\] must equal jd_end"):
        ElectionalWindow(
            jd_start=2451545.0,
            jd_end=2451545.5,
            duration_hours=12.0,
            qualifying_jds=(2451545.0, 2451545.25),
        )


def test_electional_window_rejects_bad_duration() -> None:
    with pytest.raises(ValueError, match="duration_hours must equal"):
        ElectionalWindow(
            jd_start=2451545.0,
            jd_end=2451545.5,
            duration_hours=6.0,
            qualifying_jds=(2451545.0, 2451545.5),
        )


def test_find_electional_windows_merges_consecutive_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    created_jds: list[float] = []

    def fake_chart(*, jd_ut, latitude, longitude, house_system, bodies, reader):
        created_jds.append(jd_ut)
        return {"jd": jd_ut, "house_system": house_system, "bodies": bodies, "reader": reader}

    monkeypatch.setattr("moira.electional.create_chart", fake_chart)
    monkeypatch.setattr("moira.electional.get_reader", lambda: "READER")

    def predicate(chart) -> bool:
        return chart["jd"] in {0.0, 0.25, 0.75}

    policy = ElectionalPolicy(step_days=0.25, merge_gap_days=0.26, bodies=["Sun", "Moon"])
    windows = find_electional_windows(
        jd_start=0.0,
        jd_end=1.0,
        latitude=51.5,
        longitude=-0.1,
        predicate=predicate,
        policy=policy,
    )

    assert created_jds == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])
    assert len(windows) == 2

    first, second = windows
    assert first.qualifying_jds == pytest.approx((0.0, 0.25))
    assert first.duration_hours == pytest.approx(6.0, abs=1e-12)
    assert second.qualifying_jds == pytest.approx((0.75,))
    assert second.duration_hours == pytest.approx(0.0, abs=1e-12)


def test_find_electional_moments_returns_raw_hits_without_merging(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chart(*, jd_ut, latitude, longitude, house_system, bodies, reader):
        return {"jd": jd_ut}

    monkeypatch.setattr("moira.electional.create_chart", fake_chart)
    monkeypatch.setattr("moira.electional.get_reader", lambda: "READER")

    policy = ElectionalPolicy(step_days=0.25, merge_gap_days=10.0)
    moments = find_electional_moments(
        jd_start=0.0,
        jd_end=1.0,
        latitude=0.0,
        longitude=0.0,
        predicate=lambda chart: chart["jd"] in {0.25, 0.5, 0.75},
        policy=policy,
    )

    assert moments == pytest.approx([0.25, 0.5, 0.75])


def test_find_electional_windows_uses_default_merge_gap_when_unspecified(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chart(*, jd_ut, latitude, longitude, house_system, bodies, reader):
        return {"jd": jd_ut}

    monkeypatch.setattr("moira.electional.create_chart", fake_chart)
    monkeypatch.setattr("moira.electional.get_reader", lambda: "READER")

    policy = ElectionalPolicy(step_days=0.25)
    windows = find_electional_windows(
        jd_start=0.0,
        jd_end=0.5,
        latitude=0.0,
        longitude=0.0,
        predicate=lambda chart: chart["jd"] in {0.0, 0.25},
        policy=policy,
    )

    assert len(windows) == 1
    assert windows[0].qualifying_jds == pytest.approx((0.0, 0.25))


def test_find_electional_windows_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="jd_start"):
        find_electional_windows(
            jd_start=2.0,
            jd_end=1.0,
            latitude=0.0,
            longitude=0.0,
            predicate=lambda chart: True,
            policy=ElectionalPolicy(),
            reader="READER",
        )


def test_find_electional_moments_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="jd_start"):
        find_electional_moments(
            jd_start=2.0,
            jd_end=1.0,
            latitude=0.0,
            longitude=0.0,
            predicate=lambda chart: True,
            policy=ElectionalPolicy(),
            reader="READER",
        )
