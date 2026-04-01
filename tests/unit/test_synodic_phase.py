from __future__ import annotations

import moira.phase as phase


class _P:
    def __init__(self, lon: float) -> None:
        self.longitude = lon
        self.latitude = 0.0


def test_synodic_phase_angle_wraps_forward(monkeypatch) -> None:
    def fake_planet_at(name: str, jd: float):
        return _P(350.0 if name == "A" else 10.0)

    monkeypatch.setattr(phase, "planet_at", fake_planet_at)
    assert phase.synodic_phase_angle("A", "B", 2451545.0) == 20.0


def test_synodic_phase_angle_wraps_reverse(monkeypatch) -> None:
    def fake_planet_at(name: str, jd: float):
        return _P(10.0 if name == "A" else 350.0)

    monkeypatch.setattr(phase, "planet_at", fake_planet_at)
    assert phase.synodic_phase_angle("A", "B", 2451545.0) == 340.0


def test_synodic_phase_state_classification() -> None:
    assert phase.synodic_phase_state(0.0) == "conjunction"
    assert phase.synodic_phase_state(90.0) == "waxing"
    assert phase.synodic_phase_state(180.0) == "opposition"
    assert phase.synodic_phase_state(270.0) == "waning"
    assert phase.synodic_phase_state(359.0) == "conjunction"
