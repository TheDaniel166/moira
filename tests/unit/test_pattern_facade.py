"""Kernel-free forwarding tests for the public pattern facade."""

import moira.facade as facade_module
from moira._facade_special import SpecialTopicsFacadeMixin


class _Chart:
    def longitudes(self):
        return {"A": 0.0, "B": 120.0, "C": 240.0, "D": 60.0}

    def speeds(self):
        return {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}


class _WideGrandTrineChart:
    def longitudes(self):
        return {"Sun": 0.0, "Moon": 127.5, "Mars": 240.0}

    def speeds(self):
        return {"Sun": 1.0, "Moon": 0.5, "Mars": 0.25}


def test_pattern_facade_forwards_opt_in_dominance(monkeypatch) -> None:
    observed: dict[str, object] = {}
    aspects = [object()]

    def _find_aspects(positions, *, speeds, orb_factor):
        observed.update(
            aspect_positions=positions,
            speeds=speeds,
            aspect_orb_factor=orb_factor,
        )
        return aspects

    monkeypatch.setattr(facade_module, "find_aspects", _find_aspects)

    def _find_all_patterns(positions, *, aspects, orb_factor, dominant_only):
        observed.update(
            positions=positions,
            aspects=aspects,
            orb_factor=orb_factor,
            dominant_only=dominant_only,
        )
        return ["result"]

    monkeypatch.setattr(facade_module, "find_all_patterns", _find_all_patterns)

    result = SpecialTopicsFacadeMixin.patterns(
        object(),
        _Chart(),
        orb_factor=1.25,
        dominant_only=True,
    )

    assert result == ["result"]
    assert observed == {
        "aspect_positions": {"A": 0.0, "B": 120.0, "C": 240.0, "D": 60.0},
        "speeds": {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0},
        "aspect_orb_factor": 1.25,
        "positions": {"A": 0.0, "B": 120.0, "C": 240.0, "D": 60.0},
        "aspects": aspects,
        "orb_factor": 1.25,
        "dominant_only": True,
    }


def test_pattern_facade_widened_orb_reaches_initial_aspect_admission() -> None:
    facade = object()
    chart = _WideGrandTrineChart()

    default_names = {
        pattern.name
        for pattern in SpecialTopicsFacadeMixin.patterns(facade, chart)
    }
    widened_names = {
        pattern.name
        for pattern in SpecialTopicsFacadeMixin.patterns(facade, chart, orb_factor=1.25)
    }

    assert "Grand Trine" not in default_names
    assert "Grand Trine" in widened_names
