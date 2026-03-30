"""
Moira — electional.py
Electional Search Engine: governs time-window scanning to find moments that
satisfy caller-supplied chart conditions.

Archetype: Engine

Purpose
-------
Provides a deterministic scanner that evaluates a caller-supplied predicate
over a sequence of ChartContext snapshots within a given time range, returning
the qualifying windows as typed result vessels.

Boundary declaration
--------------------
Owns:
    - ElectionalWindow  — result vessel for one qualifying time window.
    - ElectionalPolicy  — frozen policy governing scan step and merge tolerance.
    - find_electional_windows() — primary scanner entry point.
    - find_electional_moments() — returns individual qualifying JDs rather than
      merged windows.
Delegates:
    - Chart construction to moira.chart.create_chart.
    - All positional truth to the engine modules called by create_chart.
    - Kernel I/O to moira.spk_reader.

Import-time side effects: None

External dependency assumptions:
    - DE441 kernel must be accessible via moira.spk_reader.get_reader().
    - Caller-supplied predicate must accept a ChartContext and return bool.
    - Predicate must be pure (no side effects, deterministic for a given JD).

Design notes
------------
The engine does not encode any astrological doctrine about what constitutes a
"good" election. That is the caller's responsibility via the predicate. The
engine answers only: "which moments in this range satisfy your condition?"

The predicate receives a fully populated ChartContext — planets, nodes, houses,
is_day — so the caller has access to every engine primitive without needing to
re-derive positions.

Window merging doctrine
-----------------------
Consecutive qualifying JDs that are separated by no more than
``policy.merge_gap_days`` are merged into a single ElectionalWindow. This
prevents a 1-hour scan step from producing hundreds of single-point windows
when a condition holds for several hours. The merge gap defaults to 1.5× the
scan step, which is the smallest value that guarantees no false splits from
floating-point step accumulation.

Public surface / exports:
    ElectionalPolicy, ElectionalWindow,
    find_electional_windows, find_electional_moments
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from .chart import ChartContext, create_chart
from .constants import HouseSystem
from .julian import datetime_from_jd
from .spk_reader import get_reader, SpkReader

__all__ = [
    "ElectionalPolicy",
    "ElectionalWindow",
    "find_electional_windows",
    "find_electional_moments",
]


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ElectionalPolicy:
    """
    Governing policy for an electional search.

    Fields
    ------
    step_days : float
        Scan step in fractional days. Smaller values increase precision at the
        cost of more chart constructions. Default 1/24 (one hour).
        Must be > 0.

    merge_gap_days : float | None
        Maximum gap between consecutive qualifying JDs that will be merged into
        a single ElectionalWindow. When None, defaults to 1.5 × step_days.
        Set to 0.0 to disable merging (each qualifying JD becomes its own window).

    house_system : str
        House system code passed to create_chart(). Defaults to Placidus.

    bodies : list[str] | None
        Body list passed to create_chart(). None uses the engine default
        (Sun through Pluto + Chiron).

    Raises
    ------
    ValueError
        If step_days <= 0.
        If merge_gap_days < 0.
    """
    step_days:      float       = 1.0 / 24.0   # one hour
    merge_gap_days: float | None = None          # defaults to 1.5 × step_days
    house_system:   str          = HouseSystem.PLACIDUS
    bodies:         list[str] | None = None

    def __post_init__(self) -> None:
        if self.step_days <= 0:
            raise ValueError(
                f"ElectionalPolicy: step_days must be > 0, got {self.step_days!r}"
            )
        if self.merge_gap_days is not None and self.merge_gap_days < 0:
            raise ValueError(
                f"ElectionalPolicy: merge_gap_days must be >= 0, got {self.merge_gap_days!r}"
            )

    @property
    def effective_merge_gap(self) -> float:
        """Resolved merge gap in days (1.5 × step_days when not explicitly set)."""
        if self.merge_gap_days is None:
            return self.step_days * 1.5
        return self.merge_gap_days


# ---------------------------------------------------------------------------
# Result vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ElectionalWindow:
    """
    A contiguous time window during which the electional predicate is satisfied.

    Fields
    ------
    jd_start : float
        Julian Day (UT) of the first qualifying scan point in this window.

    jd_end : float
        Julian Day (UT) of the last qualifying scan point in this window.
        Equal to jd_start when the window contains only one qualifying moment.

    duration_hours : float
        Length of the window in decimal hours. Zero when jd_start == jd_end.

    qualifying_jds : tuple[float, ...]
        All individual qualifying Julian Days within this window, in
        chronological order. Always contains at least one entry.

    Structural invariants
    ---------------------
    - jd_start <= jd_end
    - duration_hours == (jd_end - jd_start) * 24
    - len(qualifying_jds) >= 1
    - qualifying_jds[0] == jd_start
    - qualifying_jds[-1] == jd_end
    """
    jd_start:       float
    jd_end:         float
    duration_hours: float
    qualifying_jds: tuple[float, ...]

    def __repr__(self) -> str:
        try:
            dt = datetime_from_jd(self.jd_start)
            dt_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            dt_str = f"JD{self.jd_start:.4f}"
        return (
            f"ElectionalWindow({dt_str}, "
            f"{self.duration_hours:.1f}h, "
            f"{len(self.qualifying_jds)} point(s))"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _merge_jds(
    qualifying: list[float],
    merge_gap: float,
) -> list[ElectionalWindow]:
    """
    Merge a sorted list of qualifying JDs into ElectionalWindow vessels.

    Consecutive JDs separated by <= merge_gap are grouped into one window.
    """
    if not qualifying:
        return []

    windows: list[ElectionalWindow] = []
    group: list[float] = [qualifying[0]]

    for jd in qualifying[1:]:
        if jd - group[-1] <= merge_gap:
            group.append(jd)
        else:
            windows.append(_make_window(group))
            group = [jd]

    windows.append(_make_window(group))
    return windows


def _make_window(group: list[float]) -> ElectionalWindow:
    jd_start = group[0]
    jd_end   = group[-1]
    return ElectionalWindow(
        jd_start=jd_start,
        jd_end=jd_end,
        duration_hours=(jd_end - jd_start) * 24.0,
        qualifying_jds=tuple(group),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_electional_windows(
    jd_start:  float,
    jd_end:    float,
    latitude:  float,
    longitude: float,
    predicate: Callable[[ChartContext], bool],
    policy:    ElectionalPolicy | None = None,
    reader:    SpkReader | None = None,
) -> list[ElectionalWindow]:
    """
    Scan a time range and return windows where the predicate is satisfied.

    Constructs a ChartContext at each scan step and evaluates the predicate.
    Consecutive qualifying moments separated by no more than
    ``policy.effective_merge_gap`` are merged into a single ElectionalWindow.

    Parameters
    ----------
    jd_start : float
        Start of the search range (Julian Day UT, inclusive).

    jd_end : float
        End of the search range (Julian Day UT, inclusive).

    latitude : float
        Geographic latitude of the election location, degrees [-90, 90].

    longitude : float
        Geographic longitude of the election location, degrees [-180, 180].

    predicate : Callable[[ChartContext], bool]
        A pure function that receives a ChartContext and returns True when the
        chart satisfies the election criteria. The predicate must be
        deterministic and must not mutate the ChartContext.

    policy : ElectionalPolicy | None
        Scan policy. Uses ElectionalPolicy() defaults when None (1-hour step,
        Placidus houses, standard body set).

    reader : SpkReader | None
        SPK kernel reader. Uses the module-level singleton when None.

    Returns
    -------
    list[ElectionalWindow]
        Qualifying windows in chronological order. Empty list when no moments
        satisfy the predicate within the range.

    Raises
    ------
    ValueError
        If jd_start >= jd_end.
        If latitude or longitude are out of range (delegated to create_chart).

    Side effects
        Initialises the SpkReader singleton on first call if reader is None.
    """
    if jd_start >= jd_end:
        raise ValueError(
            f"find_electional_windows: jd_start ({jd_start}) must be < jd_end ({jd_end})"
        )

    if policy is None:
        policy = ElectionalPolicy()

    if reader is None:
        reader = get_reader()

    qualifying: list[float] = []
    jd = jd_start

    while jd <= jd_end:
        chart = create_chart(
            jd_ut=jd,
            latitude=latitude,
            longitude=longitude,
            house_system=policy.house_system,
            bodies=policy.bodies,
        )
        if predicate(chart):
            qualifying.append(jd)
        jd += policy.step_days

    return _merge_jds(qualifying, policy.effective_merge_gap)


def find_electional_moments(
    jd_start:  float,
    jd_end:    float,
    latitude:  float,
    longitude: float,
    predicate: Callable[[ChartContext], bool],
    policy:    ElectionalPolicy | None = None,
    reader:    SpkReader | None = None,
) -> list[float]:
    """
    Scan a time range and return individual qualifying Julian Days.

    Identical to find_electional_windows() but returns the raw list of
    qualifying JDs rather than merged windows. Useful when the caller wants
    to apply their own grouping logic or simply needs the timestamps.

    Parameters
    ----------
    jd_start  : range start (Julian Day UT, inclusive)
    jd_end    : range end   (Julian Day UT, inclusive)
    latitude  : geographic latitude, degrees [-90, 90]
    longitude : geographic longitude, degrees [-180, 180]
    predicate : pure function ChartContext → bool
    policy    : ElectionalPolicy (defaults to 1-hour step when None)
    reader    : SpkReader (uses singleton when None)

    Returns
    -------
    list[float]
        Qualifying Julian Days in chronological order.

    Raises
    ------
    ValueError
        If jd_start >= jd_end.
    """
    if jd_start >= jd_end:
        raise ValueError(
            f"find_electional_moments: jd_start ({jd_start}) must be < jd_end ({jd_end})"
        )

    if policy is None:
        policy = ElectionalPolicy()

    if reader is None:
        reader = get_reader()

    qualifying: list[float] = []
    jd = jd_start

    while jd <= jd_end:
        chart = create_chart(
            jd_ut=jd,
            latitude=latitude,
            longitude=longitude,
            house_system=policy.house_system,
            bodies=policy.bodies,
        )
        if predicate(chart):
            qualifying.append(jd)
        jd += policy.step_days

    return qualifying
