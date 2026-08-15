# Mean Lilith IERS Series Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind `Body.LILITH` / `mean_lilith()` to the IERS 2003 analytical mean apogee `F + Ω − l + 180°`, keep the 5.2.2 `nutation=` frame, and document the Swiss `SE_MEAN_APOG` residual as expected.

**Architecture:** Reuse `_fundamental_args(T)` already admitted for `mean_node()`. Do not add a second polynomial. Speed is the derivative of `F + Ω − l`. Receipts rename the Lilith stage to `iers_2003_mean_apogee_solution`. `smoothed_lilith()` is not implemented.

**Tech Stack:** Python 3.10+, existing `moira.nutation_2000a._fundamental_args`, IAU 2000A nutation, pytest, pyerfa.

**Spec:** `docs/superpowers/specs/2026-08-15-mean-lilith-iers-and-de-smoothed-design.md`

## Global Constraints

- `mean_lilith(jd_ut, *, nutation=True) -> NodeData` keeps this signature. `NodeData.name` stays `"Lilith"`.
- Raw mean-equinox longitude is `normalize_degrees((F + Ω − l) * RAD2DEG + 180.0)` from `_fundamental_args(T)`.
- Default `nutation=True` still adds IAU 2000A Δψ. Speed excludes the Δψ derivative.
- Do not chase Swiss `SE_MEAN_APOG` digits. A ±4–7′ residual is success.
- Do not implement `smoothed_lilith()`, `Body.SMOOTHED_LILITH`, Swiss ELP terms, `SE_INTP_APOG`, or `SE_INTP_PERG`.
- Do not auto-select a DE product because a kernel file is on disk.
- Do not change `true_lilith()` longitude, μ, or frame. Its speed may read `mean_lilith(..., nutation=False).speed` so the Meeus `4069.0137287` coefficient leaves the module.
- Do not change asteroid 1181 Lilith (NAIF 2001181).
- Do not add a golden test of the current Meeus 22.3 coefficients.
- Do not close GitHub issue #18 and do not post on it unless the user asks.
- Do not pick a `moira-astro` version number. Write CHANGELOG under `[Unreleased]`.
- Author in `C:\dev\moira` on a feature branch. Use `.\.venv\Scripts\python.exe` for every command.

---

## File map

**Modify**

- `moira/nodes.py` — replace the Meeus perigee polynomial; IERS speed; docstring; `true_lilith` speed reuse
- `tests/integration/test_mean_node_frame_consistency.py` — ERFA authority, speed, Swiss wide-band witness
- `moira_server/services/chart.py` — Lilith stage name
- `tests/server/test_server_chart_routes.py` — assert `iers_2003_mean_apogee_solution`
- `moira/sky/bodies.py` — one-line mean-Lilith blurb
- `wiki/02_standards/API_REFERENCE.md` — IERS series wording
- `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md` — policy-translation paragraph
- `wiki/03_validation/SWISS_EPHEMERIS_SYMBOL_TABLE.md` — `MEAN_APOG` note
- `CHANGELOG.md` — `[Unreleased]` series-authority note
- `moira.wiki/*` — generated only, via `scripts/sync_git_wiki.py`

**Do not create**

- No new public function, Body enum, kernel probe, or Phase 2 module.

---

### Task 1: IERS mean-apogee series and speed

**Files:**
- Modify: `moira/nodes.py` (`mean_lilith` at lines 292–341; `true_lilith` speed at line 451)
- Test: `tests/integration/test_mean_node_frame_consistency.py`

**Interfaces:**
- Consumes: `_fundamental_args(T) -> tuple` already imported in `nodes.py`; `normalize_degrees`; `RAD2DEG`; `_nutation`; `ut_to_tt`; `centuries_from_j2000`
- Produces: `mean_lilith(jd_ut: float, *, nutation: bool = True) -> NodeData` with IERS longitude and IERS mean-argument speed

- [ ] **Step 1: Create the feature branch**

```powershell
Set-Location C:\dev\moira
git checkout main
git pull --ff-only
git checkout -b mean-lilith-iers
```

- [ ] **Step 2: Write the failing ERFA authority test**

Append these two tests to `tests/integration/test_mean_node_frame_consistency.py`. Keep `test_mean_lilith_uses_the_same_explicit_equinox_policy` unchanged.

```python
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2314654.0, id="1625"),
        pytest.param(2450333.25, id="1996"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_lilith_mean_equinox_matches_iers_erfa(jd_tt: float) -> None:
    """Authority validation against ERFA IERS 2003 F + Ω − l + 180°."""
    jd_ut = tt_to_ut(jd_tt)
    T = centuries_from_j2000(jd_tt)
    expected = (
        math.degrees(erfa.faf03(T) + erfa.faom03(T) - erfa.fal03(T)) + 180.0
    ) % 360.0

    actual = mean_lilith(jd_ut, nutation=False).longitude

    assert abs(_angular_difference_arcsec(actual, expected)) < 1.0e-5


@pytest.mark.parametrize(
    "jd_ut",
    [
        pytest.param(2439528.1944444445, id="1967"),
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_mean_lilith_speed_matches_mean_equinox_polynomial_rate(jd_ut: float) -> None:
    """The reported speed is the derivative of the governing mean argument."""
    step_days = 0.01
    before = mean_lilith(jd_ut - step_days, nutation=False).longitude
    after = mean_lilith(jd_ut + step_days, nutation=False).longitude
    finite_difference = (
        ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step_days)
    )

    actual = mean_lilith(jd_ut, nutation=False)

    assert actual.speed == pytest.approx(finite_difference, abs=2.0e-9)
```

- [ ] **Step 3: Run the new tests and confirm they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_mean_node_frame_consistency.py::test_mean_lilith_mean_equinox_matches_iers_erfa tests\integration\test_mean_node_frame_consistency.py::test_mean_lilith_speed_matches_mean_equinox_polynomial_rate -v
```

Expected: FAIL. The 1625 ERFA case is the clear miss (current Meeus differs by about 1.16″; the new bound is `1.0e-5`″). Do not weaken the bound.

- [ ] **Step 4: Replace `mean_lilith` with the IERS series**

In `moira/nodes.py`, replace the `mean_lilith` function (docstring and body) with:

```python
def mean_lilith(jd_ut: float, *, nutation: bool = True) -> NodeData:
    """
    Compute Mean Black Moon Lilith from the IERS 2003 mean lunar
    apogee ``F + Ω − l + 180°``.

    ``mean`` describes the averaged apogee solution, independently of
    the output frame. By default, nutation in longitude is applied so
    the result is expressed in the true ecliptic and equinox of date,
    matching Moira's default planetary and chart longitudes. Set
    ``nutation=False`` to obtain the raw IERS mean-ecliptic and
    mean-equinox-of-date longitude.

    The expression reuses Moira's admitted IAU 2000A fundamental
    arguments rather than a second Meeus polynomial. TT is used in
    place of TDB as permitted by IERS Conventions (2003), section
    5.7.2.

    Args:
        jd_ut: Julian Day in Universal Time (UT1).
        nutation: If ``True`` (default), add IAU 2000A nutation in
            longitude to express the mean apogee in the true equinox
            of date. If ``False``, return the raw mean-equinox-of-date
            longitude.

    Returns:
        NodeData vessel with name="Lilith", tropical longitude in
        degrees [0, 360), and the mean IERS polynomial rate in
        degrees/day (direct). The speed excludes the short-period
        derivative of nutation even when ``nutation=True``.

    Raises:
        No exceptions under normal operation; propagates any exception
        raised by ut_to_tt() or centuries_from_j2000() on invalid
        input.

    Side effects:
        None.
    """
    jd_tt = ut_to_tt(jd_ut)
    T = centuries_from_j2000(jd_tt)

    l, _lp, F, _D, Om = _fundamental_args(T)[:5]
    lon = normalize_degrees((F + Om - l) * RAD2DEG + 180.0)
    if nutation:
        dpsi_deg, _ = _nutation(jd_tt)
        lon = normalize_degrees(lon + dpsi_deg)

    l_rate_arcsec_per_century = (
        1717915923.2178
        + 2.0 * 31.8792 * T
        + 3.0 * 0.051635 * T**2
        + 4.0 * (-0.00024470) * T**3
    )
    f_rate_arcsec_per_century = (
        1739527262.8478
        + 2.0 * (-12.7512) * T
        + 3.0 * (-0.001037) * T**2
        + 4.0 * 0.00000417 * T**3
    )
    omega_rate_arcsec_per_century = (
        -6962890.5431
        + 2.0 * 7.4722 * T
        + 3.0 * 0.007702 * T**2
        - 4.0 * 0.00005939 * T**3
    )
    speed = (
        f_rate_arcsec_per_century
        + omega_rate_arcsec_per_century
        - l_rate_arcsec_per_century
    ) / (3600.0 * 36525.0)

    return NodeData(name="Lilith", longitude=lon, speed=speed)
```

Those rate coefficients are the first derivatives of the IERS 2003 polynomials already coded in `_fundamental_args`. Do not invent a second argument implementation.

In `true_lilith`, replace only the speed assignment:

```python
    # Speed (estimated via mean apogee speed as it oscillates wildly)
    speed = mean_lilith(jd_ut, nutation=False).speed
```

Do not touch the eccentricity-vector longitude, μ, or frame matrices.

- [ ] **Step 5: Re-run the Lilith series tests and the existing frame invariant**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_mean_node_frame_consistency.py -v
```

Expected: PASS, including `test_mean_lilith_uses_the_same_explicit_equinox_policy` and every mean-node test in the file.

- [ ] **Step 6: Commit**

```powershell
git add moira/nodes.py tests/integration/test_mean_node_frame_consistency.py
git commit -m "feat: bind mean_lilith to IERS 2003 F+Omega-l+180"
```

---

### Task 2: Lilith reduction receipt

**Files:**
- Modify: `moira_server/services/chart.py` (`_MEAN_LILITH_STAGE_SEQUENCE` at lines 46–53)
- Test: `tests/server/test_server_chart_routes.py` (the existing `/v1/chart/reduction` assertion around lines 153–156)

**Interfaces:**
- Consumes: `mean_lilith` from Task 1 (no new arguments)
- Produces: Lilith `stage_sequence` containing `iers_2003_mean_apogee_solution`, then `iau_2000a_nutation_in_longitude`, then `true_equinox_of_date_longitude`. `source_surface` remains `"moira.mean_lilith"`.

- [ ] **Step 1: Extend the existing reduction test**

In `tests/server/test_server_chart_routes.py`, in the test that already checks Lilith's `iau_2000a_nutation_in_longitude` stage, add this assertion immediately after that block:

```python
    assert (
        "iers_2003_mean_apogee_solution"
        in body["reduction"]["node_reductions"]["Lilith"]["stage_sequence"]
    )
    assert (
        "analytical_apogee_solution"
        not in body["reduction"]["node_reductions"]["Lilith"]["stage_sequence"]
    )
    assert body["reduction"]["node_reductions"]["Lilith"]["source_surface"] == (
        "moira.mean_lilith"
    )
```

Do not add a kernel-conditional stage list.

- [ ] **Step 2: Run the reduction test and confirm it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_chart_routes.py -k "reduction" -v
```

Expected: FAIL on `iers_2003_mean_apogee_solution` missing from the Lilith stage list.

- [ ] **Step 3: Rename the Lilith stage**

In `moira_server/services/chart.py`, change `_MEAN_LILITH_STAGE_SEQUENCE` to:

```python
_MEAN_LILITH_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "ut_to_tt",
    "iers_2003_mean_apogee_solution",
    "iau_2000a_nutation_in_longitude",
    "true_equinox_of_date_longitude",
    "lilith_vessel_materialization",
]
```

Do not change `_TRUE_LILITH_STAGE_SEQUENCE` or the Mean Node sequence.

- [ ] **Step 4: Re-run the reduction test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_chart_routes.py -k "reduction" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add moira_server/services/chart.py tests/server/test_server_chart_routes.py
git commit -m "feat: name IERS mean-apogee stage on Lilith receipts"
```

---

### Task 3: Swiss `SE_MEAN_APOG` as a wide-band witness

**Files:**
- Modify: `tests/integration/test_mean_node_frame_consistency.py`

**Interfaces:**
- Consumes: `mean_lilith(jd_ut) -> NodeData` from Task 1 (default `nutation=True`, matching issue #18 chart longitudes)
- Produces: a secondary corroboration test whose pass band is ±10′, not Swiss digit parity

- [ ] **Step 1: Add the issue #18 witness test**

Append to `tests/integration/test_mean_node_frame_consistency.py`. At the top of that file, add `from datetime import datetime, timezone` after `from __future__ import annotations`, and change the existing julian import to:

```python
from moira.julian import centuries_from_j2000, jd_from_datetime, tt_to_ut, ut_to_tt
```

Then append:

```python
@pytest.mark.parametrize(
    ("when", "swiss_mean_apog"),
    [
        pytest.param(
            datetime(1995, 7, 4, 9, 5, tzinfo=timezone.utc),
            80.3030,
            id="issue-18-1995-07-04",
        ),
        pytest.param(
            datetime(1955, 2, 8, 18, 45, tzinfo=timezone.utc),
            236.7037,
            id="issue-18-1955-02-08",
        ),
    ],
)
def test_mean_lilith_swiss_mean_apog_residual_is_a_series_difference(
    when: datetime,
    swiss_mean_apog: float,
) -> None:
    """Secondary corroboration, not a parity target.

    Provenance: GitHub TheDaniel166/moira#18, pyswisseph 2.10.3.2
    ``swe.calc_ut(..., swe.MEAN_APOG)`` on the reporter's UTC instants.
    Swiss ``SE_MEAN_APOG`` keeps ELP periodic terms inside a quantity
    still labelled mean. Moira's ``Body.LILITH`` is the IERS secular
    mean. The ±10′ band admits that known series difference. Shrinking
    the band toward Swiss digits is out of scope.
    """
    actual = mean_lilith(jd_from_datetime(when)).longitude
    residual_arcmin = abs(_angular_difference_arcsec(actual, swiss_mean_apog)) / 60.0

    assert residual_arcmin < 10.0
```

The two dates are the largest #18 residuals (about +6.9′ and −6.7′). Do not add the other six dates. Do not tighten `10.0`.

- [ ] **Step 2: Run the new witness and the IERS tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_mean_node_frame_consistency.py::test_mean_lilith_swiss_mean_apog_residual_is_a_series_difference tests\integration\test_mean_node_frame_consistency.py::test_mean_lilith_mean_equinox_matches_iers_erfa -v
```

Expected: PASS. If the Swiss witness fails, the IERS series was implemented wrong; do not widen the band and do not retarget toward Swiss.

- [ ] **Step 3: Commit**

```powershell
git add tests/integration/test_mean_node_frame_consistency.py
git commit -m "test: treat Swiss MEAN_APOG residual as expected series difference"
```

---

### Task 4: Honesty docs

**Files:**
- Modify: `moira/sky/bodies.py` (mean_lilith blurb at lines 75–78)
- Modify: `wiki/02_standards/API_REFERENCE.md` (lunar-nodes table around line 856; sky table around line 4885)
- Modify: `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md` (body table after line 310)
- Modify: `wiki/03_validation/SWISS_EPHEMERIS_SYMBOL_TABLE.md` (`MEAN_APOG` row at line 205)
- Modify: `CHANGELOG.md` (`## [Unreleased]`)
- Generate: `moira.wiki/API_REFERENCE.md`, `moira.wiki/MIGRATING_FROM_SWISS_EPHEMERIS.md`, `moira.wiki/SWISS_EPHEMERIS_SYMBOL_TABLE.md` via the sync script
- Test: `tests/unit/test_swiss_ephemeris_migration_guide.py`

**Interfaces:**
- Consumes: Task 1 series meaning (`IERS 2003`, `F + Ω − l + 180°`)
- Produces: docs that call `SE_MEAN_APOG` → `Body.LILITH` a symbolic / policy translation, not numerical identity

- [ ] **Step 1: Update the sky blurb and both API tables**

In `moira/sky/bodies.py` replace the `mean_lilith` blurb with:

```
mean_lilith(jd_ut, *, nutation=True)
    NodeData for IERS 2003 mean lunar apogee (F+Ω−l+180°) in an
    explicit mean- or true-equinox-of-date frame.
```

In `wiki/02_standards/API_REFERENCE.md` replace both `mean_lilith` description cells with:

```
IERS 2003 mean lunar apogee (F+Ω−l+180°); true equinox of date by default, raw mean equinox with `nutation=False`
```

Do not edit `moira.wiki/API_REFERENCE.md` by hand.

- [ ] **Step 2: Update the Swiss migration guide and symbol table**

In `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md`, immediately after the body-identity table (after the `SE_CHIRON` row and before the `Body.ALL_PLANETS` paragraph), insert:

```markdown
`SE_MEAN_APOG` maps to `Body.LILITH` as the mean-apogee intent, not
as a numerical identity. Moira uses the IERS 2003 secular mean
`F + Ω − l + 180°`. Swiss `SE_MEAN_APOG` is an ELP hybrid that
keeps selected periodic terms inside a quantity still labelled
mean. Expect a date-dependent residual of about 4–7′. That is a
series difference, not a frame error. `SE_OSCU_APOG` →
`Body.TRUE_LILITH` is the osculating DE product and is the close
numerical match. Interpolated Swiss apogees (`INTP_APOG`,
`INTP_PERG`) still have no public Moira equivalent.
```

In `wiki/03_validation/SWISS_EPHEMERIS_SYMBOL_TABLE.md` change the `MEAN_APOG` row note from `closest body identifier` to:

```
closest body identifier; IERS secular mean, not Swiss ELP hybrid
```

Leave status `mapped` and truth basis `symbolic`.

- [ ] **Step 3: Record the change under `[Unreleased]`**

In `CHANGELOG.md`, under `## [Unreleased]`, add:

```markdown
### Changed
- `mean_lilith()` / `Body.LILITH` now uses the IERS 2003 mean apogee
  `F + Ω − l + 180°` from the same fundamental arguments as
  `mean_node()`. The 5.2.2 `nutation=` frame is unchanged. Modern
  longitudes move by less than 0.2″ versus the previous Meeus
  polynomial. The several-arcminute residual versus Swiss
  `SE_MEAN_APOG` is expected and is not a parity target.
```

Do not create `wiki/03_release/COMPATIBILITY_NOTES_<version>.md` in this task. When a later release task names the version, that file must include:

- signatures unchanged
- series authority is now IERS 2003 `F+Ω−l+180°`
- modern longitudes shift by less than 0.2″; 1625 shifts by about 1.2″
- Swiss `SE_MEAN_APOG` residual of ±4–7′ remains expected
- regenerate cached Mean Lilith only if bit-level identity with 6.2.1 Meeus values was frozen
- `true_lilith` longitude is unchanged

- [ ] **Step 4: Sync the GitHub wiki mirror and run the drift guards**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_swiss_ephemeris_migration_guide.py -v
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
```

Expected: sync writes the three generated wiki files; both commands PASS. If `check_doc_consistency.py` flags a leftover Meeus mean-Lilith sentence, fix that sentence in `wiki/` and re-run the sync. Do not hand-edit `moira.wiki/`.

- [ ] **Step 5: Commit**

```powershell
git add moira/sky/bodies.py wiki/02_standards/API_REFERENCE.md wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md wiki/03_validation/SWISS_EPHEMERIS_SYMBOL_TABLE.md CHANGELOG.md moira.wiki
git commit -m "docs: describe mean Lilith as IERS, Swiss residual expected"
```

- [ ] **Step 6: Do not post issue #18 yet**

Leave this comment in the working notes. Post it only when the user asks, or when Phase 1 is on a published `moira-astro` release:

```text
5.2.2 upgraded the Mean Lilith *frame* (true equinox of date), not
the *series*. This release binds `Body.LILITH` to the IERS 2003
mean apogee F+Ω−l+180°, the same argument family as the mean node
you already measured as 0.0000° versus `SE_MEAN_NODE`.

On your 1955–2010 dates IERS versus the previous Meeus polynomial
is sub-arcsecond. The 4–7′ residual versus `SE_MEAN_APOG` remains,
because Swiss keeps ELP periodic terms inside a quantity labelled
mean. That is an expected series difference, not a Moira frame bug.

`True Lilith` matching `OSCU_APOG` is the intended DE product. A
later named `smoothed_lilith()` may exist; it will not replace
`Body.LILITH` just because a kernel is present.
```

Do not `gh issue close 18`. Do not `gh issue comment`.

---

## Self-review

**Spec coverage**

| Spec requirement | Task |
| --- | --- |
| IERS `F+Ω−l+180°` from `_fundamental_args` | Task 1 |
| ERFA `faf03 + faom03 − fal03 + 180°` within `1.0e-5″` | Task 1 |
| Existing Δψ frame invariant stays | Task 1 |
| Speed = IERS derivative, no Δψ | Task 1 |
| `true_lilith` longitude/μ/frame untouched | Task 1 |
| Receipt stage `iers_2003_mean_apogee_solution` | Task 2 |
| Swiss ±10′ witness, not a target | Task 3 |
| API, migration guide, symbol table, CHANGELOG | Task 4 |
| No `smoothed_lilith`, no Body enum, no kernel fallback | Global Constraints |
| Do not close or comment #18 in this plan | Task 4 Step 6 |
| Version number deferred | Global Constraints / Task 4 |

**Placeholder scan:** none. Compatibility-notes filename waits on the release task by spec; the required body is written in Task 4.

**Type consistency:** `mean_lilith(jd_ut: float, *, nutation: bool = True) -> NodeData` is unchanged across all four tasks.
