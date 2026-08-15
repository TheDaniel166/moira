# True Node And True Lilith Speed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `true_node` and `true_lilith` `NodeData.speed` the circular TT finite-difference of the published osculating longitude.

**Architecture:** Extract longitude-only helpers. Differentiate in TT days with a 0.002-day step duplicated from `planets._LONGITUDE_RATE_STEP_DAYS`. Do not import `moira.planets` from `nodes.py`. Mean series rates stay analytical.

**Tech Stack:** Python 3.10+, existing DE reader, pytest, `requires_ephemeris`.

**Spec:** `docs/superpowers/specs/2026-08-15-true-node-lilith-speed-design.md`

## Global Constraints

- Signatures `true_node(jd_ut, reader=None, jd_tt=None)` and `true_lilith(jd_ut, reader=None)` do not change.
- Longitude, μ, frame, and eccentricity-vector math do not change.
- Step is `0.002` TT days. Circular unwrap: `((after - before + 180) % 360 - 180) / (2 * step)`.
- Do not import `moira.planets` from `moira.nodes`.
- Do not smooth, clamp, or fall back to the mean rate.
- Do not implement `smoothed_lilith()` or bump the package version in this patch.
- Author on branch `mean-lilith-iers` in `C:\dev\moira`. Use `.\.venv\Scripts\python.exe`.

---

## File map

**Modify**

- `moira/nodes.py` — helpers, true_node/true_lilith speed, docstrings
- `tests/integration/test_true_node_frame_consistency.py` — True Node speed tests
- `tests/integration/test_true_lilith_speed.py` — True Lilith speed tests (new)
- `moira/sky/bodies.py` — blurbs
- `wiki/02_standards/API_REFERENCE.md` — both true-node / true-lilith cells
- `CHANGELOG.md` — `[Unreleased]`
- `moira.wiki/*` — via `scripts/sync_git_wiki.py` only

---

### Task 1: Osculating longitude rate

**Files:**
- Modify: `moira/nodes.py`
- Test: `tests/integration/test_true_node_frame_consistency.py`
- Create: `tests/integration/test_true_lilith_speed.py`

**Interfaces:**
- Consumes: existing true_node / true_lilith geometry
- Produces: `_LONGITUDE_RATE_STEP_DAYS = 2.0e-3`; `_circular_longitude_rate(before, after, span_days) -> float`; `_true_node_longitude(...)` / `_true_lilith_longitude(...)`; public functions return differentiated speed

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_true_node_frame_consistency.py`:

```python
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_true_node_speed_matches_longitude_finite_difference(reader, jd_tt: float) -> None:
    step = 0.002
    before = true_node(jd_tt, reader=reader, jd_tt=jd_tt - step).longitude
    after = true_node(jd_tt, reader=reader, jd_tt=jd_tt + step).longitude
    expected = ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step)
    actual = true_node(jd_tt, reader=reader, jd_tt=jd_tt)
    assert actual.speed == pytest.approx(expected, abs=2.0e-9)


@pytest.mark.requires_ephemeris
def test_true_node_speed_is_not_the_mean_node_constant(reader) -> None:
    actual = true_node(2461199.9375, reader=reader, jd_tt=2461199.9375).speed
    assert actual != pytest.approx(-1934.136261 / 36525.0, abs=1.0e-6)
```

Create `tests/integration/test_true_lilith_speed.py`:

```python
from __future__ import annotations

import pytest

from moira.julian import tt_to_ut
from moira.nodes import mean_lilith, true_lilith


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_true_lilith_speed_matches_longitude_finite_difference(reader, jd_tt: float) -> None:
    step = 0.002
    jd_ut = tt_to_ut(jd_tt)
    before = true_lilith(tt_to_ut(jd_tt - step), reader=reader).longitude
    after = true_lilith(tt_to_ut(jd_tt + step), reader=reader).longitude
    expected = ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step)
    actual = true_lilith(jd_ut, reader=reader)
    assert actual.speed == pytest.approx(expected, abs=2.0e-9)


@pytest.mark.requires_ephemeris
def test_true_lilith_speed_is_not_the_mean_lilith_rate(reader) -> None:
    jd_ut = tt_to_ut(2461199.9375)
    true_speed = true_lilith(jd_ut, reader=reader).speed
    mean_speed = mean_lilith(jd_ut, nutation=False).speed
    assert true_speed != pytest.approx(mean_speed, abs=1.0e-6)
```

Note: the True Lilith FD test steps **UT** via `tt_to_ut` because `true_lilith` has no `jd_tt`. The implementation must still differentiate in TT internally; the public-longitude FD in UT is the same span to first order (ΔT is locally constant). Prefer implementing true_lilith’s internal samples in TT, then converting those TT samples with the same `_ut1_to_ephemeris_tt` used at the centre so the test’s UT-stepped longitudes match.

Cleaner implementation for true_lilith: expose an optional internal TT path, or compute centre TT and sample `centre_tt ± 0.002` by inverting to UT with `tt_to_ut` for the helper that still takes jd_ut. The test above uses `tt_to_ut(jd_tt ± step)` so the implementation should sample those same instants: convert centre `jd_ut` to TT, step TT, convert back with `tt_to_ut` **or** pass TT into the longitude helper. **Use a TT longitude helper** for both functions. For the True Lilith test to match at `2e-9`, `true_lilith` must sample `tt_to_ut(center_tt ± step)` if it only accepts UT — that is what the test measures. Implement true_lilith rate as:

```python
center_tt = _ut1_to_ephemeris_tt(jd_ut, reader)
lon = _true_lilith_longitude(center_tt, reader)
lon_minus = _true_lilith_longitude(center_tt - 0.002, reader)
lon_plus = _true_lilith_longitude(center_tt + 0.002, reader)
```

Then change the True Lilith test to step the same way the implementation does — **do not** use `tt_to_ut(jd_tt ± step)` if the helper is TT-native. Final test for True Lilith (use this, not the UT-stepped draft above):

```python
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_true_lilith_speed_matches_longitude_finite_difference(reader, jd_tt: float) -> None:
    from moira.nodes import _true_lilith_longitude

    step = 0.002
    jd_ut = tt_to_ut(jd_tt)
    expected = (
        (_true_lilith_longitude(jd_tt + step, reader)
         - _true_lilith_longitude(jd_tt - step, reader)
         + 180.0) % 360.0
        - 180.0
    ) / (2.0 * step)
    # Testing via the public longitudes at TT±step requires a TT entry.
    # Assert against the helper the public function uses (exported for tests
    # only if already public). Prefer: compute expected from public
    # true_lilith by calling it three times after adding optional jd_tt.
```

**Locked test design:** add optional `jd_tt: float | None = None` to `true_lilith` **only if** it is already the true_node pattern. Spec said signatures unchanged. Do **not** add `jd_tt` to `true_lilith`.

Locked True Lilith test — public longitudes only, same `jd_ut` conversion both sides:

```python
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_true_lilith_speed_matches_longitude_finite_difference(reader, jd_tt: float) -> None:
    step = 0.002
    jd_ut = tt_to_ut(jd_tt)
    before = true_lilith(tt_to_ut(jd_tt - step), reader=reader).longitude
    after = true_lilith(tt_to_ut(jd_tt + step), reader=reader).longitude
    expected = ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step)
    actual = true_lilith(jd_ut, reader=reader)
    assert actual.speed == pytest.approx(expected, abs=2.0e-6)
```

`2e-6` (not `2e-9`) admits UT1/TT conversion granularity on the public path. Internally still step TT. True Node keeps `2e-9` because it has `jd_tt`.

- [ ] **Step 2: Run tests, expect FAIL**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_true_node_frame_consistency.py::test_true_node_speed_is_not_the_mean_node_constant tests\integration\test_true_lilith_speed.py::test_true_lilith_speed_is_not_the_mean_lilith_rate -v
```

Expected: FAIL — speeds still equal the mean proxies.

- [ ] **Step 3: Implement**

In `moira/nodes.py`, add below the imports:

```python
# Same half-span as moira.planets._LONGITUDE_RATE_STEP_DAYS. Do not import planets.
_LONGITUDE_RATE_STEP_DAYS = 2.0e-3


def _circular_longitude_rate(before: float, after: float, span_days: float) -> float:
    return ((after - before + 180.0) % 360.0 - 180.0) / span_days
```

Move the body of `true_node` after reader/jd_tt resolution into `_true_node_longitude(reader, jd_tt) -> float` (geometry only). Then:

```python
    lon = _true_node_longitude(reader, jd_tt)
    step = _LONGITUDE_RATE_STEP_DAYS
    speed = _circular_longitude_rate(
        _true_node_longitude(reader, jd_tt - step),
        _true_node_longitude(reader, jd_tt + step),
        2.0 * step,
    )
    return NodeData(name="True Node", longitude=lon, speed=speed)
```

Move the body of `true_lilith` after reader resolution into `_true_lilith_longitude(reader, jd_tt) -> float`. Then:

```python
    jd_tt = _ut1_to_ephemeris_tt(jd_ut, reader)
    lon = _true_lilith_longitude(reader, jd_tt)
    step = _LONGITUDE_RATE_STEP_DAYS
    speed = _circular_longitude_rate(
        _true_lilith_longitude(reader, jd_tt - step),
        _true_lilith_longitude(reader, jd_tt + step),
        2.0 * step,
    )
    return NodeData(name="True Lilith", longitude=lon, speed=speed)
```

Delete `speed = -1934.136261 / 36525.0` and `speed = mean_lilith(...).speed`.

Rewrite the Returns sections: speed is the circular TT finite-difference of the osculating true-of-date longitude and can change sign. Remove “approximation” / “compute it independently.”

- [ ] **Step 4: Run tests**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_true_node_frame_consistency.py tests\integration\test_true_lilith_speed.py -v
```

Expected: PASS, including existing longitude invariants.

- [ ] **Step 5: Commit**

```powershell
git add moira/nodes.py tests/integration/test_true_node_frame_consistency.py tests/integration/test_true_lilith_speed.py
git commit -m "fix: differentiate true node and true Lilith longitudes for speed"
```

---

### Task 2: Honesty docs

**Files:**
- Modify: `moira/sky/bodies.py`
- Modify: `wiki/02_standards/API_REFERENCE.md`
- Modify: `CHANGELOG.md`
- Generate: `moira.wiki` via sync

- [ ] **Step 1: Update blurbs and API tables**

`moira/sky/bodies.py`:

```
true_node(jd_ut)    NodeData for the true (osculating) ascending node;
                    speed is dλ/dt of that longitude and can change sign.
true_lilith(jd_ut)  NodeData for true Lilith (osculating apogee);
                    speed is dλ/dt of that longitude and can change sign.
```

API true_node cells:

```
True (osculating) lunar node; speed is the differentiated true-of-date longitude, not the mean-node rate
```

API true_lilith cells:

```
True Lilith (osculating apogee); speed is the differentiated true-of-date longitude, not the mean-apogee rate
```

CHANGELOG `[Unreleased]` add under Changed:

```markdown
- `true_node()` and `true_lilith()` `NodeData.speed` is now the circular
  finite-difference of the DE osculating true-of-date longitude (0.002-day
  TT step, same span as planetary longitude rates). The previous mean-rate
  proxies are removed. Speeds may be large or retrograde; that is the
  geometry. Mean Node / Mean Lilith rates are unchanged.
```

- [ ] **Step 2: Sync wiki and commit**

```powershell
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py
git add moira/sky/bodies.py wiki/02_standards/API_REFERENCE.md CHANGELOG.md moira.wiki
git commit -m "docs: true node and Lilith speed is the sky rate"
```

Do not post #18. Do not bump version.

---

## Self-review

| Spec requirement | Task |
| --- | --- |
| FD of published longitude, 0.002 TT days | Task 1 |
| No planets import | Task 1 |
| No smoothing / no mean fallback | Task 1 |
| Signatures unchanged | Task 1 |
| Mean rates unchanged | Task 1 (existing tests) |
| Docs + CHANGELOG | Task 2 |
| Version bump deferred | Global Constraints |
