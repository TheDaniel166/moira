"""Bounded sampled Muhurta scoring; no continuous auspicious interval claim.

The existing Muhurta evaluator owns all judgment and weighting. This module
owns a closed UT1 sample grid, serving-reader clocks and true ayanamsa, threshold
selection, consecutive qualifying runs and stable peak ranking. JD weekday is
explicit; sunrise, Lagna, purpose-specific rules and exact transitions are not
evaluated. Limits are operational policy, not traditional doctrine.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
from types import MappingProxyType

from ._ephemeris_time import _bind_ephemeris_time, _EphemerisTimeBasisError
from .muhurta import (
    MuhurtaPolicy, MuhurtaScore, PersonalMuhurtaScore, _finite_number,
    score_muhurta, personal_muhurta_score,
)
from .panchanga import PanchangaResult, _panchanga_from_resolved_longitudes
from .planets import planet_at
from .sidereal import (
    Ayanamsa, NAKSHATRA_NAMES, _ayanamsa_at_tt, _STAR_ANCHORED,
    _nakshatra_position_from_sidereal,
)
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from .stars import star_at
from .julian import utc_to_ut1

__all__ = [
    "MuhurtaSearchPolicy", "MuhurtaMomentScore", "MuhurtaSearchWindow",
    "MuhurtaSearchResult", "MuhurtaResourceError", "MuhurtaCoverageError",
    "muhurta_score_for_chart", "find_muhurta_windows",
]

MAX_MUHURTA_SAMPLES = 4096
MAX_MUHURTA_SPAN_DAYS = 30.0
MAX_MUHURTA_RESULTS = 128


class MuhurtaResourceError(RuntimeError):
    """A required planetary, clock or live-anchor resource is unavailable."""


class MuhurtaCoverageError(ValueError):
    """A sample falls outside the serving reader's coverage; no partial result."""


def _ayanamsa_name(value: str) -> str:
    if not isinstance(value, str) or value not in Ayanamsa.ALL:
        raise ValueError("ayanamsa_system must be a named Moira ayanamsa")
    return value


def _natal_moon(value, janma_nakshatra=None):
    if value is None:
        if janma_nakshatra is not None:
            raise ValueError("janma_nakshatra alone is insufficient; supply janma_moon_sidereal_lon")
        return None
    value = _finite_number("janma_moon_sidereal_lon", value) % 360
    if janma_nakshatra is not None:
        derived = _nakshatra_position_from_sidereal(value).nakshatra
        if janma_nakshatra not in NAKSHATRA_NAMES or janma_nakshatra != derived:
            raise ValueError("janma_nakshatra disagrees with janma_moon_sidereal_lon")
    return value


@dataclass(frozen=True, slots=True)
class MuhurtaSearchPolicy:
    """Full-range sampling before ranking/truncation; ties prefer earlier UT1."""
    ayanamsa_system: str = Ayanamsa.LAHIRI
    muhurta_policy: MuhurtaPolicy = field(default_factory=MuhurtaPolicy)
    step_days: float = 1 / 24
    min_score: float = 0.0
    max_results: int = 32
    vara_basis: str = field(init=False, default="jd_weekday")
    ayanamsa_mode: str = field(init=False, default="true")
    interval_semantics: str = field(init=False, default="consecutive_qualifying_samples")
    max_samples: int = field(init=False, default=MAX_MUHURTA_SAMPLES)
    max_span_days: float = field(init=False, default=MAX_MUHURTA_SPAN_DAYS)

    def __post_init__(self):
        _ayanamsa_name(self.ayanamsa_system)
        if not isinstance(self.muhurta_policy, MuhurtaPolicy):
            raise ValueError("muhurta_policy must be MuhurtaPolicy")
        step = _finite_number("step_days", self.step_days)
        if not 1 / 1440 <= step <= MAX_MUHURTA_SPAN_DAYS:
            raise ValueError("step_days must be between one minute and 30 days")
        object.__setattr__(self, "step_days", step)
        object.__setattr__(self, "min_score", _finite_number("min_score", self.min_score))
        if (isinstance(self.max_results, bool) or not isinstance(self.max_results, int)
                or not 1 <= self.max_results <= MAX_MUHURTA_RESULTS):
            raise ValueError("max_results must be an integer in [1, 128]")


@dataclass(frozen=True, slots=True)
class MuhurtaMomentScore:
    jd_ut1: float
    jd_tt: float
    sun_tropical_longitude: float
    moon_tropical_longitude: float
    ayanamsa_degrees: float
    panchanga: PanchangaResult
    score: MuhurtaScore | PersonalMuhurtaScore
    janma_moon_sidereal_lon: float | None
    policy: MuhurtaPolicy
    clock_identity: str
    delta_t_source: str = "caller_supplied_chart"
    jd_tdb: float | None = None
    input_time_basis: str = "reader_bound_ut1"

    def __post_init__(self):
        for name in ("jd_ut1", "jd_tt", "sun_tropical_longitude",
                     "moon_tropical_longitude", "ayanamsa_degrees"):
            _finite_number(name, getattr(self, name))
        if not isinstance(self.policy, MuhurtaPolicy):
            raise ValueError("moment policy must be MuhurtaPolicy")
        if self.jd_tdb is not None:
            _finite_number("jd_tdb", self.jd_tdb)
        if self.input_time_basis not in {"reader_bound_ut1", "supplied_ut1_tt", "facade_civil_utc_delta_t"}:
            raise ValueError("unknown input_time_basis")
        if not all(0 <= value < 360 for value in (
            self.sun_tropical_longitude, self.moon_tropical_longitude,
        )):
            raise ValueError("tropical longitudes must be normalized to [0, 360)")
        _ayanamsa_name(self.panchanga.ayanamsa_system)
        natal = _natal_moon(self.janma_moon_sidereal_lon)
        object.__setattr__(self, "janma_moon_sidereal_lon", natal)
        if self.panchanga.jd != self.jd_ut1:
            raise ValueError("Panchanga and moment must share one UT1 epoch")
        personal = self.janma_moon_sidereal_lon is not None
        if personal != isinstance(self.score, PersonalMuhurtaScore):
            raise ValueError("natal input and score mode disagree")
        _finite_number("score.total", self.score.total)
        moon_sid = (self.moon_tropical_longitude - self.ayanamsa_degrees) % 360
        expected_panchanga = _panchanga_from_resolved_longitudes(
            self.sun_tropical_longitude, self.moon_tropical_longitude,
            (self.sun_tropical_longitude - self.ayanamsa_degrees) % 360,
            moon_sid, self.jd_ut1, self.panchanga.ayanamsa_system,
            _nakshatra_position_from_sidereal(moon_sid),
        )
        if self.panchanga != expected_panchanga:
            raise ValueError("Panchanga does not describe the retained longitudes and frame")
        expected_score = (score_muhurta(self.panchanga, self.policy) if natal is None else
                          personal_muhurta_score(self.panchanga, natal, moon_sid, self.policy))
        if self.score != expected_score:
            raise ValueError("score does not describe the retained policy and inputs")
        # Preserve the existing score vessel, while freezing this receipt's copy.
        object.__setattr__(self, "score", replace(
            self.score, breakdown=MappingProxyType(dict(self.score.breakdown)),
        ))

    @property
    def natal_mode(self):
        return "tara_chandra" if self.janma_moon_sidereal_lon is not None else "omitted"


@dataclass(frozen=True, slots=True)
class MuhurtaSearchWindow:
    """First/last qualifying samples and adjacent rejected-sample brackets.

    A singleton has zero sampled span. Brackets are witnesses, not solved
    transition times. A missing bracket means the requested edge was reached.
    """
    samples: tuple[MuhurtaMomentScore, ...]
    peak: MuhurtaMomentScore
    left_unqualified_jd: float | None
    right_unqualified_jd: float | None

    def __post_init__(self):
        object.__setattr__(self, "samples", tuple(self.samples))
        if not self.samples or any(a.jd_ut1 >= b.jd_ut1 for a, b in zip(self.samples, self.samples[1:])):
            raise ValueError("window samples must be nonempty and strictly ordered")
        expected = max(self.samples, key=lambda s: (s.score.total, -s.jd_ut1))
        if self.peak is not expected:
            raise ValueError("peak must be the earliest highest-scored qualifying sample")
        for name in ("left_unqualified_jd", "right_unqualified_jd"):
            if getattr(self, name) is not None:
                _finite_number(name, getattr(self, name))
        if self.left_unqualified_jd is not None and self.left_unqualified_jd >= self.jd_start:
            raise ValueError("left bracket must precede the first sample")
        if self.right_unqualified_jd is not None and self.right_unqualified_jd <= self.jd_end:
            raise ValueError("right bracket must follow the last sample")

    @property
    def jd_start(self):
        return self.samples[0].jd_ut1

    @property
    def jd_end(self):
        return self.samples[-1].jd_ut1

    @property
    def qualifying_jds(self):
        return tuple(s.jd_ut1 for s in self.samples)


@dataclass(frozen=True, slots=True)
class MuhurtaSearchResult:
    start_jd_ut1: float
    end_jd_ut1: float
    policy: MuhurtaSearchPolicy
    janma_moon_sidereal_lon: float | None
    samples: tuple[MuhurtaMomentScore, ...]
    windows: tuple[MuhurtaSearchWindow, ...] = field(init=False)
    observed_window_count: int = field(init=False)

    def __post_init__(self):
        if not isinstance(self.policy, MuhurtaSearchPolicy):
            raise ValueError("search policy must be MuhurtaSearchPolicy")
        samples = tuple(self.samples)
        grid = _sample_grid(_finite_number("start_jd_ut1", self.start_jd_ut1),
                            _finite_number("end_jd_ut1", self.end_jd_ut1), self.policy.step_days)
        if tuple(s.jd_ut1 for s in samples) != grid:
            raise ValueError("search samples must cover the complete requested grid")
        natal = _natal_moon(self.janma_moon_sidereal_lon)
        if any(s.policy != self.policy.muhurta_policy or s.janma_moon_sidereal_lon != natal
               or s.panchanga.ayanamsa_system != self.policy.ayanamsa_system for s in samples):
            raise ValueError("search samples must share the selected policy and natal input")
        windows = _rank_windows(samples, self.policy.min_score)
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "janma_moon_sidereal_lon", natal)
        object.__setattr__(self, "observed_window_count", len(windows))
        object.__setattr__(self, "windows", tuple(windows[:self.policy.max_results]))

    @property
    def truncated(self):
        return self.observed_window_count > len(self.windows)

    @property
    def qualifying_sample_count(self):
        return sum(s.score.total >= self.policy.min_score for s in self.samples)


def _offset(jd_tt, system):
    if system in _STAR_ANCHORED:
        star, target = _STAR_ANCHORED[system]
        try:
            return (star_at(star, jd_tt).longitude - target) % 360
        except (ValueError, FileNotFoundError, KeyError) as exc:
            raise MuhurtaResourceError("required live ayanamsa anchor is unavailable") from exc
    return _ayanamsa_at_tt(jd_tt, system, "true")


def _moment(jd_ut1, jd_tt, sun, moon, system, natal, policy, identity,
            delta_t_source="caller_supplied_chart", jd_tdb=None,
            input_time_basis="reader_bound_ut1"):
    offset = _offset(jd_tt, system)
    sun_sid, moon_sid = (sun - offset) % 360, (moon - offset) % 360
    panchanga = _panchanga_from_resolved_longitudes(
        sun, moon, sun_sid, moon_sid, jd_ut1, system,
        _nakshatra_position_from_sidereal(moon_sid),
    )
    score = (score_muhurta(panchanga, policy) if natal is None else
             personal_muhurta_score(panchanga, natal, moon_sid, policy))
    return MuhurtaMomentScore(jd_ut1, jd_tt, sun, moon, offset, panchanga,
                              score, natal, policy, identity, delta_t_source, jd_tdb, input_time_basis)


def muhurta_score_for_chart(chart, *, janma_moon_sidereal_lon=None,
                            ayanamsa_system=Ayanamsa.LAHIRI, policy=None, reader=None) -> MuhurtaMomentScore:
    """Evaluate supplied tropical Sun/Moon under the chart's declared clock.

    No default longitude or date is synthesized. An explicit reader binds live
    anchor resolution; the caller owns the supplied chart's astronomical truth.
    """
    system = _ayanamsa_name(ayanamsa_system)
    natal = _natal_moon(janma_moon_sidereal_lon)
    policy = MuhurtaPolicy() if policy is None else policy
    if not isinstance(policy, MuhurtaPolicy):
        raise ValueError("policy must be MuhurtaPolicy")
    chart = getattr(chart, "chart", chart)
    planets = getattr(chart, "planets", None)
    if planets is None or any(p not in planets for p in ("Sun", "Moon")):
        raise ValueError("Muhurta scoring requires Sun and Moon")
    # Public facade Chart has a civil-UTC JD and Delta-T, while ChartContext
    # carries UT1 and TT explicitly. Recognize the owning type; never infer a
    # timescale from coincidentally named attributes or default a missing clock.
    from .facade import Chart
    if isinstance(chart, Chart):
        civil_jd = _finite_number("Chart.jd_ut (civil UTC)", chart.jd_ut)
        jd_ut1 = utc_to_ut1(civil_jd)
        jd_tt = jd_ut1 + _finite_number("Chart.delta_t", chart.delta_t) / 86400
        values = [jd_ut1, jd_tt]
        time_basis = "facade_civil_utc_delta_t"
    else:
        values = [getattr(chart, "jd_ut", None), getattr(chart, "jd_tt", None)]
        time_basis = "supplied_ut1_tt"
    values.extend(getattr(planets[p], "longitude", None) for p in ("Sun", "Moon"))
    jd_ut1, jd_tt, sun, moon = (_finite_number(n, v) for n, v in zip(
        ("chart.jd_ut", "chart.jd_tt", "Sun.longitude", "Moon.longitude"), values,
    ))
    if not all(-10_000_000 <= jd <= 10_000_000 for jd in (jd_ut1, jd_tt)):
        raise ValueError("chart epochs must be within JD [-10000000, 10000000]")
    if reader is None:
        return _moment(jd_ut1, jd_tt, sun % 360, moon % 360, system, natal,
                       policy, "caller_supplied_chart", input_time_basis=time_basis)
    with use_reader_override(reader):
        return _moment(jd_ut1, jd_tt, sun % 360, moon % 360, system, natal,
                       policy, "caller_supplied_chart", input_time_basis=time_basis)


def _sample_grid(start, end, step):
    """Integer-indexed cadence; retain each closed-range endpoint exactly once."""
    if not -10_000_000 <= start < end <= 10_000_000:
        raise ValueError("epochs must be ordered within JD [-10000000, 10000000]")
    if end - start > MAX_MUHURTA_SPAN_DAYS:
        raise ValueError("Muhurta search span must not exceed 30 days")
    count = math.floor((end - start) / step)
    if count + 1 > MAX_MUHURTA_SAMPLES:
        raise ValueError("Muhurta search exceeds the 4096 sample cap")
    grid = [jd for i in range(count + 1) if (jd := start + i * step) <= end]
    if grid[-1] < end:
        grid.append(end)
    if len(grid) > MAX_MUHURTA_SAMPLES:
        raise ValueError("Muhurta search exceeds the 4096 sample cap")
    if any(a >= b for a, b in zip(grid, grid[1:])):
        raise ValueError("cadence cannot be represented as a strictly ordered JD grid")
    return tuple(grid)


def find_muhurta_windows(start_jd_ut1: float, end_jd_ut1: float, *,
                         janma_moon_sidereal_lon=None, policy=None, reader=None) -> MuhurtaSearchResult:
    """Rank complete sampled runs; every sample must meet the score threshold.

    The whole requested grid is evaluated before max_results is applied.
    Rejected samples always split runs. Coverage/resource failures abort the
    request, preserving the distinction from a successful empty selection.
    """
    start, end, natal, policy, grid = _search_arguments(
        start_jd_ut1, end_jd_ut1, janma_moon_sidereal_lon, policy,
    )
    samples = []
    try:
        active_reader = get_reader() if reader is None else reader
        with use_reader_override(active_reader):
            for jd in grid:
                bound = _bind_ephemeris_time(jd, active_reader)
                identity = bound.identity
                if identity.planetary_ephemeris is None or identity.lunar_ephemeris is None:
                    raise MuhurtaResourceError("Muhurta requires a declared planetary/lunar clock identity")
                sun, moon = (planet_at(
                    body, jd, reader=active_reader, jd_tt=bound.epoch_tt,
                    apparent=True, aberration=True, grav_deflection=True, nutation=True,
                    center="geocentric", frame="ecliptic",
                ).longitude for body in ("Sun", "Moon"))
                samples.append(_moment(jd, bound.epoch_tt, sun, moon,
                    policy.ayanamsa_system, natal, policy.muhurta_policy, identity.summary_label,
                    bound.raw_delta_t.source_product, bound.epoch_tdb))
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError("Muhurta sample is outside serving ephemeris coverage") from exc
    except (MissingKernelError, FileNotFoundError, _EphemerisTimeBasisError) as exc:
        raise MuhurtaResourceError("required Muhurta ephemeris or clock resource is unavailable") from exc
    return MuhurtaSearchResult(start, end, policy, natal, tuple(samples))


def _search_arguments(start_jd_ut1, end_jd_ut1, janma_moon_sidereal_lon, policy):
    """Shared preflight, including facade calls before lazy reader resolution."""
    policy = MuhurtaSearchPolicy() if policy is None else policy
    if not isinstance(policy, MuhurtaSearchPolicy):
        raise ValueError("policy must be MuhurtaSearchPolicy")
    start = _finite_number("start_jd_ut1", start_jd_ut1)
    end = _finite_number("end_jd_ut1", end_jd_ut1)
    natal = _natal_moon(janma_moon_sidereal_lon)
    grid = _sample_grid(start, end, policy.step_days)
    return start, end, natal, policy, grid


def _rank_windows(samples, min_score):
    """Assemble runs solely from consecutive threshold-qualified samples."""
    windows = []
    run = []
    left = None
    for sample in samples:
        if sample.score.total >= min_score:
            run.append(sample)
        else:
            if run:
                windows.append(MuhurtaSearchWindow(tuple(run),
                    max(run, key=lambda s: (s.score.total, -s.jd_ut1)), left, sample.jd_ut1))
                run = []
            left = sample.jd_ut1
    if run:
        windows.append(MuhurtaSearchWindow(tuple(run),
            max(run, key=lambda s: (s.score.total, -s.jd_ut1)), left, None))
    windows.sort(key=lambda w: (-w.peak.score.total, w.peak.jd_ut1, w.jd_start))
    return windows
