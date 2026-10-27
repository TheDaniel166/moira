"""Aktinobolia direction and the opposition gate.

Authority for direction: sight is cast forward and the ray backward, so the
later planet in zodiacal order strikes the earlier one (Hephaistio I.16,
Engelbrecht 1887 p. 74; Antiochus/Rhetorius, CCAG I pp. 155-157, whose own
example is "Aries regards Cancer, Cancer strikes Aries"). The opposition has
no side: Moira excludes it by default, or counts it as a mutual strike as the
Antiochus/Rhetorius "four figures" do.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira.hellenistic import (
    HellenisticProfileOverlays,
    HellenisticProfilePolicy,
    hellenistic_chart_profile,
)
from moira.hellenistic_relations import (
    HellenisticRayOppositionPolicy,
    assemble_hellenistic_condition,
)

# Venus in Cancer squares the Sun in Aries; the Moon opposes the Sun.
POSITIONS = {
    "Sun": 10.0,
    "Moon": 190.5,
    "Mercury": 40.0,
    "Venus": 100.0,
    "Mars": 250.0,
    "Jupiter": 300.0,
    "Saturn": 330.0,
}


def _strikes(subject: str, policy: HellenisticRayOppositionPolicy) -> set[tuple[str, str]]:
    ray = assemble_hellenistic_condition(
        subject, POSITIONS, ray_opposition_policy=policy
    ).ray
    assert ray.opposition_policy is policy
    return {(strike.origin_body, strike.aspect_name) for strike in ray.strikes}


def test_the_later_planet_strikes_the_earlier_one() -> None:
    # Cancer strikes Aries: Venus casts its square ray back onto the Sun ...
    assert ("Venus", "Square") in _strikes("Sun", HellenisticRayOppositionPolicy.EXCLUDED)
    # ... while the Sun, earlier in the order of signs, only regards Venus.
    assert ("Sun", "Square") not in _strikes("Venus", HellenisticRayOppositionPolicy.EXCLUDED)


def test_excluded_gate_ignores_the_opposition() -> None:
    for subject in ("Sun", "Moon"):
        strikes = _strikes(subject, HellenisticRayOppositionPolicy.EXCLUDED)
        assert not any(aspect == "Opposition" for _, aspect in strikes)


def test_mutual_strike_gate_counts_the_opposition_both_ways() -> None:
    sun = _strikes("Sun", HellenisticRayOppositionPolicy.MUTUAL_STRIKE)
    moon = _strikes("Moon", HellenisticRayOppositionPolicy.MUTUAL_STRIKE)

    assert ("Moon", "Opposition") in sun
    assert ("Sun", "Opposition") in moon
    # The sided figures are unchanged by the gate.
    assert ("Venus", "Square") in sun


def test_default_gate_is_excluded_and_type_is_enforced() -> None:
    ray = assemble_hellenistic_condition("Sun", POSITIONS).ray
    assert ray.opposition_policy is HellenisticRayOppositionPolicy.EXCLUDED

    with pytest.raises(TypeError, match="ray_opposition_policy"):
        assemble_hellenistic_condition(
            "Sun", POSITIONS, ray_opposition_policy="mutual_strike"  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="ray_opposition_policy"):
        HellenisticProfileOverlays(ray_opposition_policy="mutual_strike")  # type: ignore[arg-type]


@pytest.mark.parametrize("policy", list(HellenisticRayOppositionPolicy))
def test_profile_overlay_forwards_the_gate(policy: HellenisticRayOppositionPolicy) -> None:
    profile = hellenistic_chart_profile(
        POSITIONS,
        {name: 1.0 for name in POSITIONS},
        {number: (number - 1) * 30.0 for number in range(1, 13)},
        15.0,
        280.0,
        datetime(2000, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 6, 1, tzinfo=timezone.utc),
        policy=HellenisticProfilePolicy(
            overlays=HellenisticProfileOverlays(
                assemble_condition=True,
                ray_opposition_policy=policy,
            )
        ),
    )
    sun = next(planet for planet in profile.planets if planet.planet == "Sun")

    assert sun.assemble_condition.ray.opposition_policy is policy
    has_opposition = any(
        strike.aspect_name == "Opposition"
        for strike in sun.assemble_condition.ray.strikes
    )
    assert has_opposition is (policy is HellenisticRayOppositionPolicy.MUTUAL_STRIKE)
