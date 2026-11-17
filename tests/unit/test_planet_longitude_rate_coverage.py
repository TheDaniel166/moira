"""Geocentric longitude-rate behavior when sample coverage ends."""

import pytest

from moira import planets
from moira.spk_reader import OutOfRangeError


@pytest.mark.parametrize("missing", ["lower", "upper"])
def test_one_missing_sample_uses_second_order_one_sided_rate(monkeypatch, missing):
    """A covered one-sided stencil is available at either source edge."""
    epoch = 1000.0
    monkeypatch.setattr(
        planets, "_geocentric_ecliptic_longitude_for_rate",
        lambda _body, jd, _reader, **_kwargs: 30.0 + 2.0 * (jd - epoch),
    )
    valid = object()
    contexts = (None, valid) if missing == "lower" else (valid, None)
    result = planets._geocentric_longitude_rate(
        "Sun", epoch, object(), apparent=True, aberration=True,
        grav_deflection=True, nutation=True, central_longitude=30.0,
        rate_contexts=contexts,
    )
    assert result == pytest.approx(2.0, abs=1e-7)


def test_two_missing_samples_raise_coverage_error_with_scalar_mask():
    """No rate is returned when both sides of the derivative are unavailable."""
    with pytest.raises(OutOfRangeError, match="cannot be evaluated") as exc:
        planets._geocentric_longitude_rate(
            "Sun", 1000.0, object(), apparent=True, aberration=True,
            grav_deflection=True, nutation=True, central_longitude=30.0,
            rate_contexts=(None, None),
        )
    assert exc.value.out_of_range_times is True
