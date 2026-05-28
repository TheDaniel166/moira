from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from moira.constants import Body
from moira.heliacal import (
    ObserverVisibilityEnvironment,
    VisibilityPolicy,
    is_visible_tonight,
    visibility_assessment,
    visibility_tonight,
    visual_limiting_magnitude,
)
from moira.julian import jd_from_datetime
from moira.transits import find_lunar_phases, next_ingress, next_ingress_into


@pytest.mark.requires_ephemeris
def test_adversarial_public_visibility_aliases_preserve_extreme_observer_truth(
    moira_engine,
) -> None:
    jd_ut = 2451545.0
    lat = 89.9
    lon = 179.999
    policy = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(
            limiting_magnitude=-30.0,
            local_horizon_altitude_deg=-90.0,
        )
    )

    direct = visibility_assessment(Body.VENUS, jd_ut, lat, lon, policy=policy)
    alias = visibility_tonight(Body.VENUS, jd_ut, lat, lon, policy=policy)
    via_facade = moira_engine.visibility_tonight(Body.VENUS, jd_ut, lat, lon, policy=policy)

    assert alias == direct
    assert via_facade == direct
    assert is_visible_tonight(Body.VENUS, jd_ut, lat, lon, policy=policy) is direct.observable
    assert moira_engine.is_visible_tonight(Body.VENUS, jd_ut, lat, lon, policy=policy) is direct.observable
    assert math.isfinite(direct.true_altitude_deg)
    assert math.isfinite(direct.apparent_altitude_deg)
    assert math.isfinite(direct.apparent_magnitude)
    assert math.isfinite(direct.effective_limiting_magnitude)
    assert -90.0 <= direct.true_altitude_deg <= 90.0
    assert -90.0 <= direct.apparent_altitude_deg <= 90.0


@pytest.mark.parametrize(
    ("fn", "args", "match"),
    [
        (visibility_assessment, (Body.VENUS, float("nan"), 0.0, 0.0), "jd_ut must be finite"),
        (visibility_assessment, (Body.VENUS, 2451545.0, 90.1, 0.0), r"lat must be in \[-90, 90\]"),
        (visibility_assessment, (Body.VENUS, 2451545.0, 0.0, 180.1), r"lon must be in \[-180, 180\]"),
        (visibility_tonight, (Body.VENUS, float("inf"), 0.0, 0.0), "jd_ut must be finite"),
        (visibility_tonight, (Body.VENUS, 2451545.0, -90.1, 0.0), r"lat must be in \[-90, 90\]"),
        (is_visible_tonight, (Body.VENUS, 2451545.0, 0.0, float("-inf")), r"lon must be in \[-180, 180\]"),
        (visual_limiting_magnitude, (float("nan"), 0.0, 0.0), "jd_ut must be finite"),
        (visual_limiting_magnitude, (2451545.0, 91.0, 0.0), r"lat must be in \[-90, 90\]"),
        (visual_limiting_magnitude, (2451545.0, 0.0, -181.0), r"lon must be in \[-180, 180\]"),
    ],
)
def test_adversarial_public_visibility_wrappers_reject_nonfinite_and_out_of_range_inputs(
    fn,
    args: tuple[object, ...],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        fn(*args)


@pytest.mark.parametrize("bad_jd", [float("nan"), float("inf"), float("-inf")])
def test_adversarial_public_find_lunar_phases_rejects_nonfinite_windows(bad_jd: float) -> None:
    with pytest.raises(ValueError, match="jd_start must be finite"):
        find_lunar_phases(bad_jd, 2451545.0)
    with pytest.raises(ValueError, match="jd_end must be finite"):
        find_lunar_phases(2451545.0, bad_jd)


@pytest.mark.requires_ephemeris
def test_adversarial_public_ingress_wrappers_return_none_on_tiny_horizons(
    moira_engine,
) -> None:
    jd_start = jd_from_datetime(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc))

    module_any = next_ingress(Body.SATURN, jd_start, max_days=1.0)
    facade_any = moira_engine.next_ingress(Body.SATURN, jd_start, max_days=1.0)
    module_specific = next_ingress_into(Body.SATURN, "Aries", jd_start, max_days=1.0)
    facade_specific = moira_engine.next_ingress_into(Body.SATURN, "Aries", jd_start, max_days=1.0)

    assert module_any is None
    assert facade_any is None
    assert module_specific is None
    assert facade_specific is None


def test_adversarial_public_next_ingress_into_rejects_invalid_sign_on_module_and_facade(
    moira_engine,
) -> None:
    jd_start = 2451545.0

    with pytest.raises(ValueError, match="not a valid zodiac sign"):
        next_ingress_into(Body.JUPITER, "Ophiuchus", jd_start)

    with pytest.raises(ValueError, match="not a valid zodiac sign"):
        moira_engine.next_ingress_into(Body.JUPITER, "Ophiuchus", jd_start)
