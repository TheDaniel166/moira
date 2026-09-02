# Natal Grid Series Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `find_aspect_transits_to_longitudes()` scan one longitude series per mover for every admitted mover (planets, nodes, Liliths, asteroids), using native evaluators wherever one exists, so a True Node natal grid drops from ~13 s to well under 1 s with bit-identical event times.

**Architecture:** A private series provider in `moira/transits_aspects.py` returns a `LongitudeSeries` for any mover through three tiers (native planetary route, native small-body route, Python resolver sampling), with the scan step owned by `_auto_step` and a generic quarter-turn guard. The grid search derives candidate windows from that series and refines each with the unchanged bisection. The REST route and the batch kind share one admitted-mover set.

**Tech Stack:** Python 3.14 project `.venv`, pybind11 native module `moira._moira_native` (`load_spk_segment_evaluator`, `SumEvaluator`, `ecliptic_longitude_batch`), pytest with the repository fixtures `planetary_reader`, `small_body_reader_context`, `jd_j2000`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-02-natal-grid-series-provider-design.md`.
- Engine `AGENTS.md` is law: run everything with `.\.venv\Scripts\python.exe`; `MOIRA_TEST_MODE=1 MOIRA_STRICT_KNOWN_ISSUES=1` for tests; never touch goldens or snapshots; smallest correct change.
- `moira/transits_aspects.py` is a technique module (normal zone). `moira/transits.py` `_auto_step` and `moira_server/` are PROTECTED (public defaults, REST contracts): declare before editing, keep edits minimal.
- No new dependencies. No new C++.
- Event times must equal per-target `find_aspect_transits()` results to `1e-6` day.
- Version stays 6.4.0 until the release task; changelog entries go under `## [Unreleased]`.
- Commit after every task with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer.

## File structure

- `moira/transits_aspects.py` — `LongitudeSeries` dataclass, `_sample_resolver_series`, `_native_small_body_series`, `_longitude_series` (provider with tiers and guard), `NATAL_ASPECT_MOVERS`, updated `find_aspect_transits_to_longitudes`.
- `moira/transits.py` — two new `_auto_step` entries.
- `moira_server/services/transits.py` — natal-aspects body check uses `NATAL_ASPECT_MOVERS`.
- `moira_server/models/transits.py` — `body` field description.
- `moira/batch.py` — validate `natal_aspect_transits` body against `NATAL_ASPECT_MOVERS` before searching.
- `tests/unit/test_transits_aspects_native_numeric.py` — provider, tier, guard, dual-path, timing tests.
- `tests/server/test_server_natal_aspect_routes.py` — transport parity.
- `CHANGELOG.md`, `wiki/02_services/REST_API_REFERENCE.md`, `wiki/02_standards/API_REFERENCE.md`.

Verification commands used throughout (PowerShell form; Git Bash form is the same with `./.venv/Scripts/python.exe`):

```powershell
$env:MOIRA_TEST_MODE = "1"; $env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider
```

---

### Task 1: `LongitudeSeries` and the resolver-sampling tier with the quarter-turn guard

**Files:**
- Modify: `moira/transits_aspects.py` (after `_windows_from_longitude_series`, before `_native_ecliptic_longitude_series`)
- Test: `tests/unit/test_transits_aspects_native_numeric.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class LongitudeSeries:
      jd_start: float
      step_days: float
      values: tuple[float, ...]
      tier: str  # "native_planet" | "native_small_body" | "resolver"

  def _sample_resolver_series(body, jd_start, jd_end, step_days, reader) -> LongitudeSeries
  def _series_max_circular_step(values) -> float
  def _longitude_series(body, jd_start, jd_end, step_days, reader) -> LongitudeSeries | None
  ```
  In this task `_longitude_series` only has the resolver tier and the guard; Tasks 2 and 3 add the native tiers above it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_transits_aspects_native_numeric.py`:

```python
from moira.transits_aspects import (
    LongitudeSeries,
    _longitude_series,
    _sample_resolver_series,
    _series_max_circular_step,
)


def test_sample_resolver_series_uses_the_transit_resolver(planetary_reader, jd_j2000, monkeypatch) -> None:
    calls: list[float] = []

    def fake_resolve(spec, jd, reader):
        calls.append(jd)
        return (jd - jd_j2000) * 10.0 % 360.0

    monkeypatch.setattr("moira.transits_aspects._resolve_longitude", fake_resolve)
    series = _sample_resolver_series("True Node", jd_j2000, jd_j2000 + 3.0, 1.0, planetary_reader)
    assert isinstance(series, LongitudeSeries)
    assert series.tier == "resolver"
    assert series.jd_start == jd_j2000
    assert series.step_days == 1.0
    assert series.values == (0.0, 10.0, 20.0, 30.0)
    assert calls == [jd_j2000, jd_j2000 + 1.0, jd_j2000 + 2.0, jd_j2000 + 3.0]


def test_series_max_circular_step_wraps_at_360() -> None:
    assert _series_max_circular_step((350.0, 5.0, 20.0)) == pytest.approx(15.0)
    assert _series_max_circular_step((10.0,)) == 0.0


def test_longitude_series_halves_the_step_when_a_sample_jumps_a_quarter_turn(
    planetary_reader, jd_j2000, monkeypatch
) -> None:
    # 100°/day at a 1-day step trips the guard; at 0.5 day it is 50°/step and passes.
    monkeypatch.setattr(
        "moira.transits_aspects._resolve_longitude",
        lambda spec, jd, reader: ((jd - jd_j2000) * 100.0) % 360.0,
    )
    series = _longitude_series("Mean Node", jd_j2000, jd_j2000 + 4.0, 1.0, planetary_reader)
    assert series is not None
    assert series.tier == "resolver"
    assert series.step_days == 0.5
    assert _series_max_circular_step(series.values) <= 90.0


def test_longitude_series_gives_up_after_four_halvings(planetary_reader, jd_j2000, monkeypatch) -> None:
    # A resolver that always reports a 100° jump between consecutive samples,
    # whatever the step, can never satisfy the guard.
    counter = {"n": 0}

    def hostile(spec, jd, reader):
        counter["n"] += 1
        return (counter["n"] * 100.0) % 360.0

    monkeypatch.setattr("moira.transits_aspects._resolve_longitude", hostile)
    assert _longitude_series("Mean Node", jd_j2000, jd_j2000 + 4.0, 1.0, planetary_reader) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider -k "resolver_series or circular_step or halves or gives_up"`
Expected: FAIL at import with `ImportError: cannot import name 'LongitudeSeries'`.

- [ ] **Step 3: Implement the dataclass, sampler, guard, and provider**

In `moira/transits_aspects.py`, after `_windows_from_longitude_series` and before `_native_ecliptic_longitude_series`, add:

```python
_QUARTER_TURN_DEG = 90.0
_MAX_STEP_HALVINGS = 4


@dataclass(frozen=True, slots=True)
class LongitudeSeries:
    """One mover's ecliptic longitude sampled at a fixed step over a window.

    ``tier`` names the provider that produced it (``native_planet``,
    ``native_small_body``, ``resolver``). Search code never branches on it;
    it exists for tests and receipts.
    """

    jd_start: float
    step_days: float
    values: tuple[float, ...]
    tier: str


def _sample_jds(jd_start: float, jd_end: float, step_days: float) -> list[float]:
    jds: list[float] = []
    curr = jd_start
    while curr <= jd_end:
        jds.append(curr)
        curr += step_days
    return jds


def _sample_resolver_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> LongitudeSeries:
    """Tier 3: sample the transit resolver itself. Admits every body it admits."""
    values = tuple(
        _resolve_longitude(body, jd, reader) % 360.0 for jd in _sample_jds(jd_start, jd_end, step_days)
    )
    return LongitudeSeries(jd_start=jd_start, step_days=step_days, values=values, tier="resolver")


def _series_max_circular_step(values: Sequence[float]) -> float:
    """Largest absolute circular difference between consecutive samples, degrees."""
    worst = 0.0
    for i in range(len(values) - 1):
        worst = max(worst, abs(_signed_diff(values[i + 1], values[i])))
    return worst


def _longitude_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> LongitudeSeries | None:
    """Return the mover's longitude series for candidate-window detection.

    Tries native providers first (Tasks 2 and 3 insert them here), then the
    resolver. Whatever produced the series, the quarter-turn guard halves the
    step and resamples while any consecutive pair differs by more than 90°,
    up to ``_MAX_STEP_HALVINGS`` times. Returns ``None`` when no provider can
    satisfy the guard; the caller then falls back to per-target searches.
    """
    step = float(step_days)
    for _ in range(_MAX_STEP_HALVINGS + 1):
        series = _sample_resolver_series(body, jd_start, jd_end, step, reader)
        if len(series.values) < 2:
            return None
        if _series_max_circular_step(series.values) <= _QUARTER_TURN_DEG:
            return series
        step /= 2.0
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider`
Expected: all pass (the three pre-existing tests still pass; nothing calls the provider yet).

- [ ] **Step 5: Commit**

```bash
git add moira/transits_aspects.py tests/unit/test_transits_aspects_native_numeric.py
git commit -m "feat(transits): longitude series provider with resolver tier and quarter-turn guard"
```

---

### Task 2: Route the grid search through the provider, with the engine step policy

**Files:**
- Modify: `moira/transits_aspects.py` (`find_aspect_transits_to_longitudes`, and `_longitude_series` gains the native planetary tier)
- Modify: `moira/transits.py` (`_auto_step` table; PROTECTED, two lines)
- Test: `tests/unit/test_transits_aspects_native_numeric.py`

**Interfaces:**
- Consumes: `LongitudeSeries`, `_longitude_series`, `_native_ecliptic_longitude_series` (existing), `_auto_step` from `moira.transits`.
- Produces: `_longitude_series` now returns `tier == "native_planet"` for planets when native is available, falling through to `"resolver"` otherwise. `find_aspect_transits_to_longitudes` uses `policy.transit.step_days_override or _auto_step(body)` and the provider.

- [ ] **Step 1: Write the failing tests**

Append:

```python
from moira.transits import _auto_step
from moira.transits_aspects import find_aspect_transits_to_longitudes


def _grid_and_singles(body, jd_start, jd_end, reader, specs):
    grid = find_aspect_transits_to_longitudes(body, specs, jd_start, jd_end, reader=reader)
    singles = []
    for longitude, angle, orb in specs:
        singles.extend(find_aspect_transits(body, longitude, angle, orb, jd_start, jd_end, reader=reader))
    key = lambda e: (round(e.jd_exact, 6), float(e.target), e.angle, e.is_retrograde_hit)
    return sorted(key(e) for e in grid), sorted(key(e) for e in singles)


_GRID_ANGLES = ((0.0, 8.0), (60.0, 5.0), (90.0, 7.0), (120.0, 7.0), (180.0, 8.0))


def _grid_specs(anchor_longitude: float):
    longitudes = [(anchor_longitude + offset) % 360.0 for offset in (4.0, 37.0, 91.0, 150.0, 212.0, 301.0)]
    return [(lon, angle, orb) for lon in longitudes for angle, orb in _GRID_ANGLES]


@pytest.mark.requires_ephemeris
def test_planet_grid_uses_native_tier_and_matches_singles(planetary_reader, jd_j2000) -> None:
    series = _longitude_series(Body.SATURN, jd_j2000, jd_j2000 + 365.0, _auto_step(Body.SATURN), planetary_reader)
    assert series is not None and series.tier == "native_planet"
    saturn = planet_at(Body.SATURN, jd_j2000, reader=planetary_reader).longitude
    grid, singles = _grid_and_singles(Body.SATURN, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(saturn))
    assert grid == singles and grid


@pytest.mark.requires_ephemeris
def test_true_node_grid_uses_resolver_tier_and_matches_singles(planetary_reader, jd_j2000) -> None:
    series = _longitude_series(Body.TRUE_NODE, jd_j2000, jd_j2000 + 365.0, _auto_step(Body.TRUE_NODE), planetary_reader)
    assert series is not None and series.tier == "resolver"
    from moira.transits import _resolve_longitude
    node = _resolve_longitude(Body.TRUE_NODE, jd_j2000, planetary_reader)
    grid, singles = _grid_and_singles(Body.TRUE_NODE, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(node))
    assert grid == singles and grid


@pytest.mark.requires_ephemeris
def test_true_lilith_grid_matches_singles(planetary_reader, jd_j2000) -> None:
    from moira.transits import _resolve_longitude
    lilith = _resolve_longitude(Body.TRUE_LILITH, jd_j2000, planetary_reader)
    grid, singles = _grid_and_singles(Body.TRUE_LILITH, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(lilith))
    assert grid == singles and grid


def test_auto_step_tightens_osculating_points() -> None:
    assert _auto_step(Body.TRUE_NODE) == 0.25
    assert _auto_step(Body.TRUE_LILITH) == 0.25
    assert _auto_step(Body.MEAN_NODE) == 1.0
    assert _auto_step(Body.LILITH) == 1.0


@pytest.mark.requires_ephemeris
def test_grid_falls_back_to_singles_when_no_series(planetary_reader, jd_j2000, monkeypatch) -> None:
    monkeypatch.setattr("moira.transits_aspects._longitude_series", lambda *a, **k: None)
    saturn = planet_at(Body.SATURN, jd_j2000, reader=planetary_reader).longitude
    grid, singles = _grid_and_singles(Body.SATURN, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(saturn))
    assert grid == singles and grid
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider -k "grid or auto_step"`
Expected: `test_planet_grid_uses_native_tier...` fails on `series.tier == "native_planet"` (resolver tier today); `test_auto_step_tightens...` fails on `0.25 != 1.0`; the node and Lilith tests pass slowly or fail on tier.

- [ ] **Step 3: Add the native planetary tier to the provider**

In `_longitude_series`, replace the loop body so the planetary tier is tried first:

```python
    step = float(step_days)
    for _ in range(_MAX_STEP_HALVINGS + 1):
        series: LongitudeSeries | None = None
        native = _native_ecliptic_longitude_series(body, jd_start, jd_end, step, reader)
        if native is not None:
            series = LongitudeSeries(
                jd_start=jd_start,
                step_days=step,
                values=tuple(float(v) % 360.0 for v in native),
                tier="native_planet",
            )
        if series is None:
            series = _sample_resolver_series(body, jd_start, jd_end, step, reader)
        if len(series.values) < 2:
            return None
        if _series_max_circular_step(series.values) <= _QUARTER_TURN_DEG:
            return series
        step /= 2.0
    return None
```

- [ ] **Step 4: Use the provider and the engine step in the grid search**

In `find_aspect_transits_to_longitudes`, replace the block from `scan_step = 1.0` through `series = _native_ecliptic_longitude_series(...)` and the later `_windows_from_longitude_series(series, jd_start, scan_step, ...)` call with:

```python
    scan_step = float(step_days) if step_days is not None else (policy.transit.step_days_override or _auto_step(body))
    series = _longitude_series(body, jd_start, jd_end, scan_step, reader)
    events: list[AspectTransitEvent] = []
    if series is None:
        # fallback loop unchanged
        ...
    for longitude, angle, orb in targets:
        ...
        windows = _windows_from_longitude_series(series.values, series.jd_start, series.step_days, float(longitude), float(angle))
```

Keep the padding `max(jd_start, jd_lo - 0.1)` / `min(jd_end, jd_hi + 0.1)`; change it to pad by one full `series.step_days` on each side instead of the literal 0.1 so a quarter-day series still brackets the crossing:

```python
            pad = series.step_days
            events.append(_process_aspect_hit(body, float(longitude), float(angle), float(orb),
                                              max(jd_start, jd_lo - pad), min(jd_end, jd_hi + pad),
                                              jd_start, jd_end, reader, policy, search_motion))
```

- [ ] **Step 5: Add the two `_auto_step` entries (PROTECTED edit, declare it in the commit)**

In `moira/transits.py` `_STEPS`, after the `Body.PLUTO` line:

```python
        Body.TRUE_NODE:   0.25,  # osculating; can swing several degrees/day
        Body.TRUE_LILITH: 0.25,  # osculating apogee; same reason
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py tests\unit\test_batch.py -q -p no:cacheprovider`
Expected: all pass. Note the wall time of the True Node test; it should be a few seconds including the per-target singles it compares against.

- [ ] **Step 7: Commit**

```bash
git add moira/transits_aspects.py moira/transits.py tests/unit/test_transits_aspects_native_numeric.py
git commit -m "feat(transits): natal grid scans one series per mover with the engine step policy"
```

---

### Task 3: Native small-body tier

**Files:**
- Modify: `moira/transits_aspects.py` (new `_native_small_body_series`; provider tries it after the planetary tier)
- Test: `tests/unit/test_transits_aspects_native_numeric.py`

**Interfaces:**
- Consumes: `ASTEROID_NAIF` (`moira.asteroids`), `KernelPool._readers`, `SmallBodyKernel.has_body/_kernel.segments` with `_Type13Segment.start_jd/end_jd/center/target/_load_native_evaluator()`, `SpkReader._segment_for(0, 10, jd_tt)`, `mn.load_spk_segment_evaluator`, `mn.SumEvaluator`, `mn.ecliptic_longitude_batch`, `_earth_native_evaluator`.
- Produces: `_native_small_body_series(body, jd_start, jd_end, step_days, reader) -> list[float] | None`; provider tier `"native_small_body"`.

- [ ] **Step 1: Write the failing tests**

Append:

```python
from moira.transits_aspects import _native_small_body_series


@pytest.mark.requires_ephemeris
def test_ceres_grid_uses_native_small_body_tier_and_matches_singles(small_body_reader_context, jd_j2000) -> None:
    pool = small_body_reader_context
    series = _longitude_series("Ceres", jd_j2000, jd_j2000 + 365.0, _auto_step("Ceres"), pool)
    assert series is not None and series.tier == "native_small_body"
    from moira.transits import _resolve_longitude
    ceres = _resolve_longitude("Ceres", jd_j2000, pool)
    grid, singles = _grid_and_singles("Ceres", jd_j2000, jd_j2000 + 365.0, pool, _grid_specs(ceres))
    assert grid == singles and grid


@pytest.mark.requires_ephemeris
def test_ceres_native_series_agrees_with_resolver_sampling(small_body_reader_context, jd_j2000) -> None:
    pool = small_body_reader_context
    native = _native_small_body_series("Ceres", jd_j2000, jd_j2000 + 30.0, 1.0, pool)
    assert native is not None
    sampled = _sample_resolver_series("Ceres", jd_j2000, jd_j2000 + 30.0, 1.0, pool)
    # geometric native vs apparent resolver: light time on Ceres is minutes, so
    # agreement is a small fraction of a degree, far inside the window guard.
    for a, b in zip(native, sampled.values, strict=True):
        assert abs(_signed_diff(a, b)) < 0.05


@pytest.mark.requires_ephemeris
def test_ceres_grid_falls_to_resolver_when_native_small_body_is_off(small_body_reader_context, jd_j2000, monkeypatch) -> None:
    pool = small_body_reader_context
    monkeypatch.setattr("moira.transits_aspects._native_small_body_series", lambda *a, **k: None)
    series = _longitude_series("Ceres", jd_j2000, jd_j2000 + 365.0, 1.0, pool)
    assert series is not None and series.tier == "resolver"


def test_native_small_body_series_is_none_for_non_asteroids(planetary_reader, jd_j2000) -> None:
    assert _native_small_body_series(Body.SATURN, jd_j2000, jd_j2000 + 10.0, 1.0, planetary_reader) is None
    assert _native_small_body_series(Body.TRUE_NODE, jd_j2000, jd_j2000 + 10.0, 1.0, planetary_reader) is None
```

Also import `_signed_diff` at the top of the test file: `from moira.transits_aspects import _signed_diff`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider -k "ceres or non_asteroids"`
Expected: FAIL with `ImportError: cannot import name '_native_small_body_series'`.

- [ ] **Step 3: Implement the small-body series**

In `moira/transits_aspects.py`, add `from .asteroids import ASTEROID_NAIF` to the imports, then after `_native_ecliptic_longitude_series`:

```python
_SSB = 0
_SUN = 10


def _small_body_segment(reader, naif_id: int, jd_tt_start: float, jd_tt_end: float):
    """Return the Type 13 segment covering the whole window for *naif_id*, or None."""
    readers = getattr(reader, "_readers", None)
    if readers is None:
        return None
    for candidate in readers:
        has_body = getattr(candidate, "has_body", None)
        kernel = getattr(candidate, "_kernel", None)
        if not callable(has_body) or kernel is None or not has_body(naif_id):
            continue
        for seg in kernel.segments:
            if seg.target == naif_id and seg.start_jd <= jd_tt_start and jd_tt_end <= seg.end_jd:
                return seg
    return None


def _native_small_body_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> list[float] | None:
    """Tier 2: geometric ecliptic longitude of a named asteroid from its Type 13 evaluator."""
    if mn is None:
        return None
    naif_id = ASTEROID_NAIF.get(body)
    if naif_id is None:
        return None
    resolver = getattr(reader, "_primary_planetary_reader", None)
    planetary_reader = resolver() if callable(resolver) else None
    if not isinstance(planetary_reader, SpkReader):
        return None
    jd_tt_start = _ut1_to_ephemeris_tt(jd_start, reader)
    jd_tt_end = _ut1_to_ephemeris_tt(jd_end, reader)
    seg = _small_body_segment(reader, naif_id, jd_tt_start, jd_tt_end)
    if seg is None:
        return None
    try:
        e_body = seg._load_native_evaluator()
    except Exception:
        return None
    if e_body is None:
        return None
    path = str(planetary_reader.path)
    if seg.center == _SUN:
        sun = planetary_reader._segment_for(_SSB, _SUN, jd_tt_start)
        if sun is None:
            return None
        e_sun = mn.load_spk_segment_evaluator(path, int(sun.start_i), int(sun.end_i), True, int(sun.data_type))
        e_target = mn.SumEvaluator(e_sun, e_body)
    elif seg.center == _SSB:
        e_target = e_body
    else:
        return None
    e_earth = _earth_native_evaluator(planetary_reader, path, jd_tt_start)
    if e_earth is None:
        return None
    jds_tt = [_ut1_to_ephemeris_tt(jd, reader) for jd in _sample_jds(jd_start, jd_end, step_days)]
    if len(jds_tt) < 2:
        return None
    from .nutation_2000a import _ensure_tables_loaded

    _ensure_tables_loaded()
    try:
        return list(mn.ecliptic_longitude_batch(e_target, e_earth, jds_tt))
    except Exception:
        return None
```

Then in `_longitude_series`, after the planetary attempt and before the resolver fallback:

```python
        if series is None:
            native_sb = _native_small_body_series(body, jd_start, jd_end, step, reader)
            if native_sb is not None:
                series = LongitudeSeries(
                    jd_start=jd_start,
                    step_days=step,
                    values=tuple(float(v) % 360.0 for v in native_sb),
                    tier="native_small_body",
                )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider`
Expected: all pass. If `test_ceres_native_series_agrees_with_resolver_sampling` fails by a constant offset near 0.005° or more, the SumEvaluator order is wrong (must be SSB→Sun plus Sun→asteroid); if it fails by large values the Earth evaluator was built from the wrong reader.

- [ ] **Step 5: Commit**

```bash
git add moira/transits_aspects.py tests/unit/test_transits_aspects_native_numeric.py
git commit -m "feat(transits): native Type 13 series for asteroid movers in the natal grid"
```

---

### Task 4: One admitted mover set for the route and the batch kind

**Files:**
- Modify: `moira/transits_aspects.py` (export `NATAL_ASPECT_MOVERS`)
- Modify: `moira/batch.py:868-892` (validate body before searching)
- Modify: `moira_server/services/transits.py:27-33` and `compute_natal_aspect_transits`
- Modify: `moira_server/models/transits.py` (`NatalAspectSearchRequest.body` description)
- Test: `tests/server/test_server_natal_aspect_routes.py`, `tests/unit/test_batch.py`

**Interfaces:**
- Produces: `NATAL_ASPECT_MOVERS: frozenset[str]` in `moira.transits_aspects`, listed in `__all__`; `moira_server.services.transits._require_natal_aspect_mover(body)` raising `ValueError` with the message `unsupported natal-aspect mover {body!r}; supported: planets, True Node, Mean Node, Lilith, True Lilith, and named asteroids`.

- [ ] **Step 1: Write the failing tests**

In `tests/server/test_server_natal_aspect_routes.py` append:

```python
@pytest.mark.parametrize("body", ["True Node", "True Lilith", "Ceres"])
def test_natal_aspects_route_admits_lunar_points_and_asteroids(client_with_engine: TestClient, body: str) -> None:
    response = client_with_engine.post(
        _NATAL_ASPECTS_PATH,
        json={"body": body, "natal_longitudes": [10.0], "aspect_angles": [0.0], "jd_start": 2451545.0, "jd_end": 2451545.0 + 30.0},
    )
    assert response.status_code == 200, response.text
    assert "events" in response.json()


def test_natal_aspects_route_and_batch_reject_the_same_unknown_mover(client_with_engine: TestClient) -> None:
    route = client_with_engine.post(
        _NATAL_ASPECTS_PATH,
        json={"body": "Planet X", "natal_longitudes": [10.0], "aspect_angles": [0.0], "jd_start": 2451545.0, "jd_end": 2451555.0},
    )
    assert route.status_code == 422
    assert "unsupported natal-aspect mover 'Planet X'" in route.json()["message"]

    batch = client_with_engine.post(
        "/v1/batch/events",
        json={"requests": [{"kind": "natal_aspect_transits", "body": "Planet X", "jd_start": 2451545.0, "jd_end": 2451555.0, "natal_longitudes": [10.0], "aspect_angles": [0.0]}]},
    )
    assert batch.status_code == 200
    item = batch.json()["results"][0]
    assert item["ok"] is False
    assert "unsupported natal-aspect mover 'Planet X'" in item["failure"]["message"]
```

In `tests/unit/test_batch.py` append:

```python
def test_natal_aspect_movers_cover_planets_lunar_points_and_asteroids() -> None:
    from moira.constants import Body
    from moira.asteroids import ASTEROID_NAIF
    from moira.transits_aspects import NATAL_ASPECT_MOVERS

    assert set(Body.ALL_PLANETS) <= NATAL_ASPECT_MOVERS
    assert {Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH, Body.TRUE_LILITH} <= NATAL_ASPECT_MOVERS
    assert "Ceres" in NATAL_ASPECT_MOVERS and len(NATAL_ASPECT_MOVERS) >= len(ASTEROID_NAIF) + 14
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_natal_aspect_routes.py tests\unit\test_batch.py -q -p no:cacheprovider -k "admits or same_unknown or movers_cover"`
Expected: route test for True Node returns 422 (planets only today); batch import of `NATAL_ASPECT_MOVERS` fails.

- [ ] **Step 3: Define the set and use it in both transports**

In `moira/transits_aspects.py`, after the imports:

```python
NATAL_ASPECT_MOVERS: frozenset[str] = frozenset(
    (*Body.ALL_PLANETS, Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH, Body.TRUE_LILITH, *ASTEROID_NAIF.keys())
)
"""Movers admitted to the frozen-longitude natal aspect grid on every transport."""


def _require_natal_aspect_mover(body: str) -> None:
    if body not in NATAL_ASPECT_MOVERS:
        raise ValueError(
            f"unsupported natal-aspect mover {body!r}; supported: planets, True Node, Mean Node, "
            "Lilith, True Lilith, and named asteroids"
        )
```

Add `"NATAL_ASPECT_MOVERS"` to `__all__`. Call `_require_natal_aspect_mover(body)` as the first line of `find_aspect_transits_to_longitudes` after `_require_non_empty_body(body)`.

In `moira/batch.py` the `natal_aspect_transits` branch already calls `find_aspect_transits_to_longitudes`, so the batch item fails with that message through the existing per-item failure capture; no change needed there beyond confirming the test passes.

In `moira_server/services/transits.py` import the engine's checker so the two transports cannot drift:

```python
from moira.transits_aspects import _require_natal_aspect_mover
```

and in `compute_natal_aspect_transits` replace `_require_supported_body(request.body)` with `_require_natal_aspect_mover(request.body)`.

In `moira_server/models/transits.py` change the `body` description to:

```python
        description=(
            "Moving body searched against the frozen natal longitudes: any planet Sun through Pluto, "
            "True Node, Mean Node, Lilith, True Lilith, or a named asteroid from the loaded small-body catalog."
        ),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests\server\test_server_natal_aspect_routes.py tests\unit\test_batch.py tests\unit\test_api_surface_adversarial_audit.py -q -p no:cacheprovider`
Expected: all pass. If the route's 422 message differs, check `moira_server` maps `ValueError` to `validation_error` with the exception text (it does for the existing planets-only check).

- [ ] **Step 5: Commit**

```bash
git add moira/transits_aspects.py moira_server/services/transits.py moira_server/models/transits.py tests/server/test_server_natal_aspect_routes.py tests/unit/test_batch.py
git commit -m "feat(transits): one admitted mover set for natal aspects on the route and the batch kind"
```

---

### Task 5: Timing covenant, changelog, and reference docs

**Files:**
- Test: `tests/unit/test_transits_aspects_native_numeric.py`
- Modify: `CHANGELOG.md` (Unreleased), `wiki/02_services/REST_API_REFERENCE.md` (natal-aspects paragraph), `wiki/02_standards/API_REFERENCE.md` (natal aspect grid subsection)

- [ ] **Step 1: Write the timing covenant**

Append:

```python
@pytest.mark.requires_ephemeris
def test_true_node_grid_is_bounded_in_time(planetary_reader, jd_j2000) -> None:
    import time
    from moira.transits import _resolve_longitude

    node = _resolve_longitude(Body.TRUE_NODE, jd_j2000, planetary_reader)
    specs = [((node + o) % 360.0, angle, orb) for o in range(0, 360, 30) for angle, orb in _GRID_ANGLES]
    started = time.perf_counter()
    events = find_aspect_transits_to_longitudes(Body.TRUE_NODE, specs, jd_j2000, jd_j2000 + 365.0, reader=planetary_reader)
    elapsed = time.perf_counter() - started
    assert events
    assert elapsed < 2.0, f"True Node grid took {elapsed:.2f}s; the series provider is not being used"
```

- [ ] **Step 2: Run it**

Run: `.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits_aspects_native_numeric.py -q -p no:cacheprovider -k bounded`
Expected: PASS well under 2 s.

- [ ] **Step 3: Changelog and docs**

`CHANGELOG.md` under `## [Unreleased]`:

```markdown
### Changed
- `find_aspect_transits_to_longitudes()` now scans one longitude series per
  mover for every admitted mover, not only planets: native planetary route,
  native Type 13 small-body route for named asteroids, and resolver sampling
  for the lunar nodes and Liliths. The scan step follows `_auto_step`
  (True Node and True Lilith now 0.25 day) with a quarter-turn guard that
  halves the step when consecutive samples jump. Exact event times are
  unchanged; a one-year True Node grid drops from ~13 s to under 1 s.
- `POST /v1/transits/natal-aspects` admits the same movers as the
  `natal_aspect_transits` batch kind (planets, True/Mean Node, Lilith,
  True Lilith, named asteroids) through the shared `NATAL_ASPECT_MOVERS`.
```

`wiki/02_services/REST_API_REFERENCE.md`: in the `/v1/transits/natal-aspects` paragraph replace "(`body`, Sun through Pluto)" with "(`body`: any planet, True Node, Mean Node, Lilith, True Lilith, or a named asteroid)" and add one sentence: "Every mover is scanned as one longitude series per window: native evaluators for planets and asteroids, resolver sampling for the lunar points."

`wiki/02_standards/API_REFERENCE.md` "Natal aspect grid" subsection: add after the code block: "`NATAL_ASPECT_MOVERS` lists every admitted mover. Planets and asteroids are scanned natively; nodes and Liliths are sampled through the transit resolver at the engine's step for that body."

- [ ] **Step 4: Run the release-facing guards**

Run:
```powershell
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts\generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_api_drift.py tests\unit\test_api_surface_adversarial_audit.py tests\unit\test_docstring_governance.py -q -p no:cacheprovider
```
Expected: all pass. If `test_api_surface_adversarial_audit` reports a new root name, add `NATAL_ASPECT_MOVERS` to the expected facade set in that test (it is exported from `moira.transits_aspects`, and `moira.facade` re-exports it only if you add it there; do not add it to the facade in this task).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_transits_aspects_native_numeric.py CHANGELOG.md wiki/02_services/REST_API_REFERENCE.md wiki/02_standards/API_REFERENCE.md
git commit -m "test(transits): bound the True Node grid; document the series provider"
```

---

### Task 6: Release 6.4.1

**Files:**
- Modify: `pyproject.toml`, `moira/facade.py` (`__version__`), `CHANGELOG.md`, `llms.txt`, `wiki/02_standards/API_REFERENCE.md` (baseline), `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md` (verified against), `wiki/03_validation/*.generated.md` (regenerate), `website_docs/publication_sources.json` (release summary), `website_docs/publication.json` (regenerate), `moira.wiki` (sync)
- Create: `wiki/03_release/RELEASE_NOTES_6.4.1.md`, `wiki/03_release/COMPATIBILITY_NOTES_6.4.1.md`

- [ ] **Step 1: Stamp the version**

Replace `6.4.0` with `6.4.1` in `pyproject.toml` `version`, `moira/facade.py` `__version__`, `llms.txt` "(current: 6.4.0)", `API_REFERENCE.md` "**Engine baseline:** 6.4.0", and the migration guide "**Verified against:** `moira-astro` 6.4.0<br>". In `CHANGELOG.md` insert `## [6.4.1] - <today>` under a fresh empty `## [Unreleased]`.

- [ ] **Step 2: Release notes and compatibility notes**

`RELEASE_NOTES_6.4.1.md`: title "Moira 6.4.1 - Natal Grid for Every Mover", release date, upgrade path 6.4.0 to 6.4.1, "In this release" bullets copied from the changelog, "REST contracts" listing `/v1/transits/natal-aspects` admitting lunar points and asteroids, "Not in 6.4.1": native node/Lilith series, cross-item series sharing, Workspace defaults; install block `pip install moira-astro==6.4.1`.

`COMPATIBILITY_NOTES_6.4.1.md`: backward compatible from 6.4.0 for every request; only change visible to a client is that the dedicated route now accepts more `body` values; event times identical; step-policy change affects candidate detection only; rollback pin 6.4.0.

- [ ] **Step 3: Regenerate and check**

```powershell
.\.venv\Scripts\python.exe scripts\generate_hellenistic_inventory.py
.\.venv\Scripts\python.exe scripts\generate_physical_visibility_inventory.py
.\.venv\Scripts\python.exe scripts\check_release_identity.py --tag v6.4.1
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
```
Then add a `6.4.1` entry at the top of `release_summaries` in `website_docs/publication_sources.json` (same shape as the 6.4.0 entry), run `scripts\build_website_docs_bundle.py`, then `--check`, then `scripts\sync_git_wiki.py --repo-ref main` and `--check`.

- [ ] **Step 4: Rebuild the editable install and run the release slice**

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,server]"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_doctrine_alignment.py tests\unit\test_website_docs_bundle_generation.py tests\unit\test_hellenistic_inventory_generation.py tests\unit\test_physical_visibility_phase7_release.py tests\unit\test_swiss_ephemeris_migration_guide.py tests\unit\test_transits_aspects_native_numeric.py tests\server\test_server_natal_aspect_routes.py -q -p no:cacheprovider
```
Expected: all pass.

- [ ] **Step 5: Commit, push, tag (tag push publishes to PyPI; confirm with the user first)**

```bash
git add -A -- pyproject.toml moira/facade.py CHANGELOG.md llms.txt wiki website_docs
git commit -m "release: moira-astro 6.4.1 natal grid for every mover"
git -C moira.wiki add -A && git -C moira.wiki commit -m "docs: stamp 6.4.1" && git -C moira.wiki push origin master
git add moira.wiki && git commit -m "docs: point the wiki mirror at the 6.4.1 stamp"
git push origin main
git tag v6.4.1 && git push origin v6.4.1
```
Then watch the `PyPI Publish` and `Release Hardening` workflows, and bank the publish in `C:\dev\moira-state\GENERAL.md`. The box pin follows through the Urania backend train exactly as for 6.4.0 (bump `requirements-ui.txt` pin and `MOIRA_ENGINE_CONTRACT` together on MoiraWeb `main`; the Time Map is staging-only, so publish with `-DeployStaging` only unless the user ends the dwell).
