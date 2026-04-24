"""
Moira — electional.py

Purpose
-------
This Pillar provides the electional search Engine: a deterministic scan over a
Julian-Day range that evaluates a caller-supplied predicate against successive
chart snapshots or explicit frame-aware electional evaluations and returns
either merged qualifying windows or the raw qualifying moments.

Boundary
--------
Owns:
    - `ElectionalPolicy` — frozen search doctrine for scan cadence, merge
      tolerance, house-system choice, and optional body subset.
    - `ElectionalWindow` — immutable witness vessel for one merged qualifying span.
    - `find_electional_windows()` — public merged-window search surface.
    - `find_electional_moments()` — public raw-moment search surface.
Delegates:
    - Chart assembly to `moira.chart.create_chart`.
    - Positional and house truth to the Pillars called by `create_chart()`.
    - Kernel access to `moira.spk_reader`.
    - Best-effort UTC repr formatting to `moira.julian`.

Import-time side effects
------------------------
None.

External dependency assumptions
-------------------------------
- A compatible planetary kernel must be discoverable when `reader` is omitted.
- The caller-supplied predicate must accept the payload selected by policy and
  return `bool`: `ChartContext` for default tropical search, or
  `ElectionalEvaluation` for explicit sidereal search.
- The predicate is expected to be pure and deterministic for a given chart.
- Search cadence is discrete; this Pillar does not refine truth between scan points.

Public surface / exports
------------------------
`ElectionalPolicy`, `ElectionalEvaluation`, `ElectionalWindow`,
`find_electional_windows`, `find_electional_moments`
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable

from .chart import create_chart
from .constants import HouseSystem
from .julian import datetime_from_jd
from .sidereal import Ayanamsa, ayanamsa, tropical_to_sidereal
from .spk_reader import get_reader, SpkReader

__all__ = [
    "ElectionalPolicy",
    "ElectionalEvaluation",
    "ElectionalWindow",
    "ElectionalScoredWindow",
    "find_electional_windows",
    "find_electional_moments",
    "find_scored_windows",
]


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ElectionalPolicy:
    """
    RITE: Search doctrine vessel for electional scanning.

    THEOREM: ElectionalPolicy stores the caller-visible cadence and merge doctrine for the electional search Engine.

    RITE OF PURPOSE:
        This vessel keeps electional search policy explicit instead of burying
        cadence, merge tolerance, house-system choice, or body selection inside
        the scanner. Without it, the Pillar would rely on ambient defaults and
        the search contract would be less inspectable.

    LAW OF OPERATION:
        Responsibilities:
            - Carry step cadence in fractional days.
            - Carry merge-gap doctrine for consecutive qualifying scan points.
            - Carry requested house-system code and optional body subset.
            - Normalize the body subset into immutable tuple form.
        Non-responsibilities:
            - Conducting any search.
            - Constructing charts.
            - Refining exact transition boundaries between scan points.
        Dependencies:
            - `moira.chart.create_chart()` consumes this vessel's house-system
              and body policy.
        Structural invariants:
            - `step_days > 0`
            - `merge_gap_days is None or merge_gap_days >= 0`
            - `bodies is None or isinstance(bodies, tuple)`
        Failure behavior:
            - Raises `ValueError` for invalid cadence or merge-gap inputs.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.electional.ElectionalPolicy",
      "risk": "medium",
      "api": {
        "frozen": ["step_days", "merge_gap_days", "house_system", "bodies", "effective_merge_gap",
                   "zodiac_frame", "ayanamsa_system", "ayanamsa_mode",
                   "boundary_refine_steps", "max_windows"],
        "internal": ["__post_init__"]
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_value_object", "cross_thread_calls": "safe"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    step_days:      float       = 1.0 / 24.0   # one hour
    merge_gap_days: float | None = None          # defaults to 1.5 × step_days
    house_system:   str          = HouseSystem.PLACIDUS
    bodies:         tuple[str, ...] | None = None
    zodiac_frame:   str          = "tropical"
    ayanamsa_system: str         = Ayanamsa.LAHIRI
    ayanamsa_mode:   str         = "true"
    boundary_refine_steps: int   = 0
    max_windows:    int | None   = None

    def __post_init__(self) -> None:
        """
        Enforce structural constraints and freeze any caller-supplied body list.

        Side effects:
            - Rebinds `bodies` to an immutable tuple when the caller supplied a
              mutable sequence.

        Raises:
            ValueError: If `step_days <= 0` or `merge_gap_days < 0`.
        """
        if self.step_days <= 0:
            raise ValueError(
                f"ElectionalPolicy: step_days must be > 0, got {self.step_days!r}"
            )
        if self.merge_gap_days is not None and self.merge_gap_days < 0:
            raise ValueError(
                f"ElectionalPolicy: merge_gap_days must be >= 0, got {self.merge_gap_days!r}"
            )
        if self.bodies is not None:
            object.__setattr__(self, "bodies", tuple(self.bodies))
        if self.zodiac_frame not in {"tropical", "sidereal"}:
            raise ValueError("ElectionalPolicy: zodiac_frame must be 'tropical' or 'sidereal'")
        if self.ayanamsa_mode not in {"true", "mean"}:
            raise ValueError("ElectionalPolicy: ayanamsa_mode must be 'true' or 'mean'")
        if self.zodiac_frame == "sidereal" and not self.ayanamsa_system:
            raise ValueError("ElectionalPolicy: ayanamsa_system must be non-empty")
        if self.boundary_refine_steps < 0:
            raise ValueError(
                f"ElectionalPolicy: boundary_refine_steps must be >= 0, "
                f"got {self.boundary_refine_steps!r}"
            )
        if self.max_windows is not None and self.max_windows <= 0:
            raise ValueError(
                f"ElectionalPolicy: max_windows must be > 0, got {self.max_windows!r}"
            )

    @property
    def effective_merge_gap(self) -> float:
        """Return the resolved merge gap, defaulting to `1.5 * step_days` when unset."""
        if self.merge_gap_days is None:
            return self.step_days * 1.5
        return self.merge_gap_days


@dataclass(frozen=True, slots=True)
class ElectionalEvaluation:
    """
    Explicit frame-aware evaluation vessel for electional predicates.

    The underlying chart remains the astronomical truth carrier. This vessel
    exposes the longitude frame selected by ``ElectionalPolicy`` without
    mutating the chart's tropical positions.
    """

    chart: object
    zodiac_frame: str
    ayanamsa_system: str | None
    ayanamsa_mode: str
    ayanamsa_value: float
    planet_longitudes: MappingProxyType
    node_longitudes: MappingProxyType
    house_cusps: tuple[float, ...] | None
    longitudes: MappingProxyType


# ---------------------------------------------------------------------------
# Result vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ElectionalWindow:
    """
    RITE: Merged witness vessel of a qualifying electional span.

    THEOREM: ElectionalWindow stores one contiguous merged span of qualifying scan points together with its boundary JDs and duration.

    RITE OF PURPOSE:
        This vessel gives electional search a stable public result shape. It
        preserves both the merged window boundaries and the underlying
        qualifying scan points so callers can inspect what the search witnessed
        without reconstructing the scan history themselves.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the first and last qualifying JDs of one merged span.
            - Carry the exact scan points merged into the span.
            - Carry the derived duration in hours.
            - Enforce structural coherence at construction.
        Non-responsibilities:
            - Conducting the search.
            - Refining exact boundary times between scan points.
            - Producing rich presentation output beyond a concise repr.
        Dependencies:
            - `datetime_from_jd()` is used only for best-effort repr formatting.
        Structural invariants:
            - `jd_start <= jd_end`
            - `len(qualifying_jds) >= 1`
            - `qualifying_jds[0] == jd_start`
            - `qualifying_jds[-1] == jd_end`
            - `duration_hours == (jd_end - jd_start) * 24`
        Failure behavior:
            - Raises `ValueError` when any invariant is violated.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.electional.ElectionalWindow",
      "risk": "medium",
      "api": {
        "frozen": ["jd_start", "jd_end", "duration_hours", "qualifying_jds",
                   "entry_bracket", "exit_bracket"],
        "internal": ["__post_init__", "__repr__"]
      },
      "state": {"mutable": false, "owners": ["_make_window"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_value_object", "cross_thread_calls": "safe"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    jd_start:       float
    jd_end:         float
    duration_hours: float
    qualifying_jds: tuple[float, ...]
    entry_bracket:  tuple[float, float] | None = None
    exit_bracket:   tuple[float, float] | None = None

    def __post_init__(self) -> None:
        """
        Enforce the documented boundary, duration, and ordering invariants.

        Raises:
            ValueError: If any window invariant is violated.
        """
        if not self.qualifying_jds:
            raise ValueError("ElectionalWindow.qualifying_jds must contain at least one JD")
        if not math.isfinite(self.jd_start) or not math.isfinite(self.jd_end):
            raise ValueError("ElectionalWindow jd bounds must be finite")
        if self.jd_start > self.jd_end:
            raise ValueError(
                f"ElectionalWindow.jd_start ({self.jd_start}) must be <= jd_end ({self.jd_end})"
            )
        if self.qualifying_jds[0] != self.jd_start:
            raise ValueError("ElectionalWindow.qualifying_jds[0] must equal jd_start")
        if self.qualifying_jds[-1] != self.jd_end:
            raise ValueError("ElectionalWindow.qualifying_jds[-1] must equal jd_end")
        expected_duration = (self.jd_end - self.jd_start) * 24.0
        if not math.isclose(self.duration_hours, expected_duration, abs_tol=1e-12):
            raise ValueError(
                "ElectionalWindow.duration_hours must equal (jd_end - jd_start) * 24"
            )

    def __repr__(self) -> str:
        """
        Return a concise UTC-oriented summary of the merged electional window.

        Side effects:
            - Calls `datetime_from_jd()` for best-effort UTC formatting and
              falls back to raw JD text if conversion is unavailable.
        """
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
# Scored window vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ElectionalScoredWindow:
    """
    RITE: Scored variant of a qualifying electional window.

    THEOREM: ElectionalScoredWindow pairs a merged qualifying span with a
    scalar quality score and the highest-scored scan point within that span.

    RITE OF PURPOSE:
        This vessel enables ranking and filtering of electional windows by
        numerical quality. The score and peak_jd are derived exclusively from
        the caller-supplied scorer applied to qualifying scan points; this
        vessel does not participate in the search itself.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the underlying ElectionalWindow.
            - Carry the aggregate score for the window's qualifying span.
            - Carry the JD of the highest-scored qualifying scan point.
            - Enforce structural coherence at construction.
        Non-responsibilities:
            - Computing scores (that is the caller's scorer function).
            - Conducting the search (that is find_scored_windows).
        Structural invariants:
            - score is finite.
            - peak_jd is one of window.qualifying_jds.
        Failure behavior:
            - Raises ValueError when invariants are violated.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.electional.ElectionalScoredWindow",
      "risk": "low",
      "api": {
        "frozen": ["window", "score", "peak_jd"],
        "internal": ["__post_init__"]
      },
      "state": {"mutable": false, "owners": ["find_scored_windows"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_value_object", "cross_thread_calls": "safe"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    window:  ElectionalWindow
    score:   float
    peak_jd: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.score):
            raise ValueError(
                f"ElectionalScoredWindow.score must be finite, got {self.score!r}"
            )
        if self.peak_jd not in self.window.qualifying_jds:
            raise ValueError(
                "ElectionalScoredWindow.peak_jd must be one of window.qualifying_jds"
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _merge_jds(
    qualifying: list[float],
    merge_gap: float,
) -> list[ElectionalWindow]:
    """
    Merge sorted qualifying scan points into contiguous electional windows.

    Behavior:
        Consecutive JDs separated by no more than `merge_gap` are grouped into
        the same `ElectionalWindow`; larger gaps start a new merged window.

    Failure behavior:
        Expects `qualifying` to already be in chronological order.
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
    """Materialize one merged `ElectionalWindow` from a non-empty chronological JD group."""
    jd_start = group[0]
    jd_end   = group[-1]
    return ElectionalWindow(
        jd_start=jd_start,
        jd_end=jd_end,
        duration_hours=(jd_end - jd_start) * 24.0,
        qualifying_jds=tuple(group),
    )


def _body_longitudes(items: object) -> dict[str, float]:
    """Extract longitudes from a chart planet/node mapping without mutating it."""
    return {name: float(body.longitude) for name, body in dict(items).items()}


def _converted_longitudes(
    longitudes: dict[str, float],
    jd_ut: float,
    policy: ElectionalPolicy,
) -> dict[str, float]:
    if policy.zodiac_frame == "tropical":
        return {name: lon % 360.0 for name, lon in longitudes.items()}
    return {
        name: tropical_to_sidereal(
            lon,
            jd_ut,
            system=policy.ayanamsa_system,
            mode=policy.ayanamsa_mode,
        )
        for name, lon in longitudes.items()
    }


def _evaluation_for_chart(chart: object, policy: ElectionalPolicy) -> ElectionalEvaluation:
    """Build the explicit electional evaluation view for a chart and policy."""
    jd_ut = float(getattr(chart, "jd_ut"))
    planet_lons = _converted_longitudes(
        _body_longitudes(getattr(chart, "planets", {})),
        jd_ut,
        policy,
    )
    node_lons = _converted_longitudes(
        _body_longitudes(getattr(chart, "nodes", {})),
        jd_ut,
        policy,
    )
    raw_houses = getattr(getattr(chart, "houses", None), "cusps", None)
    house_cusps = None
    if raw_houses is not None:
        house_cusps = tuple(
            _converted_longitudes(
                {str(index): float(cusp) for index, cusp in enumerate(raw_houses)},
                jd_ut,
                policy,
            ).values()
        )
    combined = {**planet_lons, **node_lons}
    if policy.zodiac_frame == "sidereal":
        ayanamsa_value = ayanamsa(jd_ut, policy.ayanamsa_system, policy.ayanamsa_mode)
        ayanamsa_system: str | None = policy.ayanamsa_system
    else:
        ayanamsa_value = 0.0
        ayanamsa_system = None
    return ElectionalEvaluation(
        chart=chart,
        zodiac_frame=policy.zodiac_frame,
        ayanamsa_system=ayanamsa_system,
        ayanamsa_mode=policy.ayanamsa_mode,
        ayanamsa_value=ayanamsa_value,
        planet_longitudes=MappingProxyType(planet_lons),
        node_longitudes=MappingProxyType(node_lons),
        house_cusps=house_cusps,
        longitudes=MappingProxyType(combined),
    )


def _predicate_payload(chart: object, policy: ElectionalPolicy) -> object:
    """Return the object passed to the predicate under the selected frame."""
    if policy.zodiac_frame == "tropical":
        return chart
    return _evaluation_for_chart(chart, policy)


def _scan_groups(
    jd_start:  float,
    jd_end:    float,
    latitude:  float,
    longitude: float,
    predicate: Callable[[object], bool],
    policy:    ElectionalPolicy,
    reader:    SpkReader,
    scorer:    Callable[[object], float] | None = None,
) -> list[list[tuple[float, float | None]]]:
    """
    Scan a JD range and return qualifying scan points as merged groups.

    Applies the merge-gap doctrine in-scan rather than post-hoc, enabling
    early exit once policy.max_windows completed groups have been found.

    Returns
    -------
    list of groups, where each group is a list of (jd, score_or_None) tuples.
    Groups correspond 1:1 with the ElectionalWindows that _make_window would
    produce from the same qualifying JDs.
    """
    completed: list[list[tuple[float, float | None]]] = []
    group:     list[tuple[float, float | None]] = []
    merge_gap  = policy.effective_merge_gap
    jd         = jd_start

    while jd <= jd_end:
        chart   = create_chart(
            jd_ut=jd,
            latitude=latitude,
            longitude=longitude,
            house_system=policy.house_system,
            bodies=policy.bodies,
            reader=reader,
        )
        payload = _predicate_payload(chart, policy)

        if predicate(payload):
            if group and (jd - group[-1][0]) > merge_gap:
                completed.append(group)
                group = []
                if policy.max_windows is not None and len(completed) >= policy.max_windows:
                    return completed
            score = scorer(payload) if scorer is not None else None
            group.append((jd, score))

        jd += policy.step_days

    if group:
        completed.append(group)

    return completed


def _bisect_boundary(
    jd_lo:      float,
    jd_hi:      float,
    true_at_lo: bool,
    latitude:   float,
    longitude:  float,
    predicate:  Callable[[object], bool],
    policy:     ElectionalPolicy,
    reader:     SpkReader,
    steps:      int,
) -> tuple[float, float]:
    """
    Narrow a predicate transition boundary between jd_lo and jd_hi via bisection.

    Precondition: predicate(jd_lo) == true_at_lo, predicate(jd_hi) == (not true_at_lo).
    Each bisection step halves the bracket width.

    Returns
    -------
    (jd_lo', jd_hi') — refined bracket satisfying the same invariant.
    Width is reduced by 2^steps from the initial |jd_hi - jd_lo|.
    """
    for _ in range(steps):
        mid   = (jd_lo + jd_hi) / 2.0
        chart = create_chart(
            jd_ut=mid,
            latitude=latitude,
            longitude=longitude,
            house_system=policy.house_system,
            bodies=policy.bodies,
            reader=reader,
        )
        if predicate(_predicate_payload(chart, policy)) == true_at_lo:
            jd_lo = mid
        else:
            jd_hi = mid

    return (jd_lo, jd_hi)


def _refine_window(
    window:         ElectionalWindow,
    jd_range_start: float,
    jd_range_end:   float,
    latitude:       float,
    longitude:      float,
    predicate:      Callable[[object], bool],
    policy:         ElectionalPolicy,
    reader:         SpkReader,
) -> ElectionalWindow:
    """
    Attempt to narrow a window's entry and exit boundaries via bisection.

    Each boundary is refined only when a non-qualifying adjacent scan point
    can be confirmed within the searched range.  A boundary that falls at or
    before the scan range edge (no adjacent False JD available on that side)
    is left unrefined.

    entry_bracket = (false_jd, true_jd): F→T transition lies between them (lo < hi).
    exit_bracket  = (true_jd, false_jd): T→F transition lies between them (lo < hi).

    Returns the original window unchanged when neither boundary can be refined.
    """
    steps = policy.boundary_refine_steps
    step  = policy.step_days
    entry_bracket: tuple[float, float] | None = None
    exit_bracket:  tuple[float, float] | None = None

    jd_before = window.jd_start - step
    if jd_before >= jd_range_start:
        chart = create_chart(
            jd_ut=jd_before,
            latitude=latitude,
            longitude=longitude,
            house_system=policy.house_system,
            bodies=policy.bodies,
            reader=reader,
        )
        if not predicate(_predicate_payload(chart, policy)):
            entry_bracket = _bisect_boundary(
                jd_lo=jd_before,
                jd_hi=window.jd_start,
                true_at_lo=False,
                latitude=latitude,
                longitude=longitude,
                predicate=predicate,
                policy=policy,
                reader=reader,
                steps=steps,
            )

    jd_after = window.jd_end + step
    if jd_after <= jd_range_end:
        chart = create_chart(
            jd_ut=jd_after,
            latitude=latitude,
            longitude=longitude,
            house_system=policy.house_system,
            bodies=policy.bodies,
            reader=reader,
        )
        if not predicate(_predicate_payload(chart, policy)):
            exit_bracket = _bisect_boundary(
                jd_lo=window.jd_end,
                jd_hi=jd_after,
                true_at_lo=True,
                latitude=latitude,
                longitude=longitude,
                predicate=predicate,
                policy=policy,
                reader=reader,
                steps=steps,
            )

    if entry_bracket is None and exit_bracket is None:
        return window

    return ElectionalWindow(
        jd_start=window.jd_start,
        jd_end=window.jd_end,
        duration_hours=window.duration_hours,
        qualifying_jds=window.qualifying_jds,
        entry_bracket=entry_bracket,
        exit_bracket=exit_bracket,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_electional_windows(
    jd_start:  float,
    jd_end:    float,
    latitude:  float,
    longitude: float,
    predicate: Callable[[object], bool],
    policy:    ElectionalPolicy | None = None,
    reader:    SpkReader | None = None,
) -> list[ElectionalWindow]:
    """
    Scan a Julian-Day range and return merged windows where the predicate holds.

    Behavior:
        Constructs a `ChartContext` at each discrete scan point, evaluates the
        caller predicate against the policy-selected payload, records qualifying
        JDs, then merges adjacent qualifying points using
        `policy.effective_merge_gap`.

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

    predicate : Callable[[object], bool]
        A pure function that receives either a ChartContext under default
        tropical policy or ElectionalEvaluation under explicit sidereal policy.
        It returns True when the chart satisfies the election criteria. The
        predicate must be deterministic and must not mutate the payload.

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
        Initialises the `SpkReader` singleton on first call if `reader` is None.

    Concurrency contract
        Pure with respect to module state except for lazy singleton reader
        initialization when `reader` is omitted.
    """
    if jd_start >= jd_end:
        raise ValueError(
            f"find_electional_windows: jd_start ({jd_start}) must be < jd_end ({jd_end})"
        )

    if policy is None:
        policy = ElectionalPolicy()

    if reader is None:
        reader = get_reader()

    groups  = _scan_groups(jd_start, jd_end, latitude, longitude,
                           predicate, policy, reader)
    windows = [_make_window([jd for jd, _ in g]) for g in groups]

    if policy.boundary_refine_steps > 0:
        windows = [
            _refine_window(w, jd_start, jd_end, latitude, longitude,
                           predicate, policy, reader)
            for w in windows
        ]

    return windows


def find_electional_moments(
    jd_start:  float,
    jd_end:    float,
    latitude:  float,
    longitude: float,
    predicate: Callable[[object], bool],
    policy:    ElectionalPolicy | None = None,
    reader:    SpkReader | None = None,
) -> list[float]:
    """
    Scan a Julian-Day range and return the raw qualifying scan points.

    Behavior:
        Conducts the same discrete chart scan as `find_electional_windows()`
        but skips the merge stage and returns the qualifying JDs directly.

    Parameters
    ----------
    jd_start  : range start (Julian Day UT, inclusive)
    jd_end    : range end   (Julian Day UT, inclusive)
    latitude  : geographic latitude, degrees [-90, 90]
    longitude : geographic longitude, degrees [-180, 180]
    predicate : pure function over ChartContext or ElectionalEvaluation
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
        If latitude or longitude are out of range (delegated to create_chart).

    Side effects
        Initialises the `SpkReader` singleton on first call if `reader` is None.
    """
    if jd_start >= jd_end:
        raise ValueError(
            f"find_electional_moments: jd_start ({jd_start}) must be < jd_end ({jd_end})"
        )

    if policy is None:
        policy = ElectionalPolicy()

    if reader is None:
        reader = get_reader()

    groups = _scan_groups(jd_start, jd_end, latitude, longitude,
                          predicate, policy, reader)
    return [jd for group in groups for jd, _ in group]


def find_scored_windows(
    jd_start:  float,
    jd_end:    float,
    latitude:  float,
    longitude: float,
    predicate: Callable[[object], bool],
    scorer:    Callable[[object], float],
    policy:    ElectionalPolicy | None = None,
    reader:    SpkReader | None = None,
) -> list[ElectionalScoredWindow]:
    """
    Scan a Julian-Day range and return scored, merged windows where the predicate holds.

    Behavior:
        Conducts the same discrete chart scan as find_electional_windows() but
        also applies the caller-supplied scorer at each qualifying scan point.
        Each returned window carries the score of its peak qualifying scan point
        and the JD of that peak point, enabling ranking by quality.

        The scorer receives the same payload as the predicate (ChartContext for
        tropical policy, ElectionalEvaluation for sidereal) and must return a
        finite float. It is called only at scan points where predicate returns
        True. Higher scores indicate more favorable conditions; the convention
        is caller-defined.

        Boundary refinement and max_windows early-exit are honoured when set
        in policy, identical to find_electional_windows().

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
    predicate : Callable[[object], bool]
        Pure function returning True when the chart satisfies the election
        criteria. Must not mutate the payload.
    scorer : Callable[[object], float]
        Pure function returning a finite float quality score for qualifying
        charts. Applied only at qualifying scan points. Must not mutate the
        payload.
    policy : ElectionalPolicy | None
        Scan policy. Uses ElectionalPolicy() defaults when None.
    reader : SpkReader | None
        SPK kernel reader. Uses the module-level singleton when None.

    Returns
    -------
    list[ElectionalScoredWindow]
        Scored qualifying windows in chronological order. Each window carries
        the score of its highest-scored qualifying scan point and the JD of
        that peak point. Empty list when no moments satisfy the predicate.

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
            f"find_scored_windows: jd_start ({jd_start}) must be < jd_end ({jd_end})"
        )

    if policy is None:
        policy = ElectionalPolicy()

    if reader is None:
        reader = get_reader()

    groups = _scan_groups(jd_start, jd_end, latitude, longitude,
                          predicate, policy, reader, scorer=scorer)

    results: list[ElectionalScoredWindow] = []
    for group in groups:
        jds    = [jd for jd, _ in group]
        scores = [s for _, s in group]
        window = _make_window(jds)

        if policy.boundary_refine_steps > 0:
            window = _refine_window(
                window, jd_start, jd_end, latitude, longitude,
                predicate, policy, reader,
            )

        best_i = max(
            range(len(scores)),
            key=lambda i: scores[i] if scores[i] is not None else float("-inf"),
        )
        results.append(ElectionalScoredWindow(
            window=window,
            score=scores[best_i],  # type: ignore[arg-type]
            peak_jd=jds[best_i],
        ))

    return results
