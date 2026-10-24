"""Resolve existing chart clock contracts without changing public chart vessels.

Facade Chart snapshots carry civil UTC in jd_ut. ChartContext and explicit
direction snapshots carry UT1 and may supply TT directly. Delta-T is TT-UT1;
it must never be added to a facade's UTC-coded epoch.
"""

import math
from numbers import Real

from ..julian import utc_to_tt, utc_to_ut1, ut_to_tt


def _finite_epoch(value: object, name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"chart must expose a finite {name}")
    return float(value)


def _chart_ut1(chart: object) -> float:
    """Resolve the natal rotation clock without requiring a dynamical epoch."""
    from ..facade import Chart

    raw = _finite_epoch(getattr(chart, "jd_ut", getattr(chart, "jd", None)), "natal jd_ut or jd")
    if isinstance(chart, Chart):
        return utc_to_ut1(raw)
    return raw


def _chart_tt(chart: object) -> float:
    """Resolve TT, preserving explicitly TT-only fixed-star input snapshots."""
    from ..facade import Chart

    if isinstance(chart, Chart):
        return utc_to_tt(_finite_epoch(chart.jd_ut, "natal civil UTC"))
    supplied_tt = getattr(chart, "jd_tt", None)
    if supplied_tt is not None:
        return _finite_epoch(supplied_tt, "natal TT")
    ut1 = _chart_ut1(chart)
    delta_t = getattr(chart, "delta_t", None)
    if delta_t is not None:
        seconds = _finite_epoch(delta_t, "Delta-T seconds")
        return _finite_epoch(ut1 + seconds / 86400., "natal TT")
    return ut_to_tt(ut1)
