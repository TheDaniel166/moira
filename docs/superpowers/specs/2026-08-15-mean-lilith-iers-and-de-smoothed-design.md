# Mean Lilith — IERS Default And Named DE-Smoothed Product

**Date:** 2026-08-15
**Status:** Approved
**Addresses:** [TheDaniel166/moira#18](https://github.com/TheDaniel166/moira/issues/18)

## Problem

`Body.LILITH` / `mean_lilith()` is still the Meeus Chapter 47 / §22.3
mean-perigee polynomial plus 180°, then the 5.2.2 IAU 2000A nutation
frame. `mean_node()` already uses the IERS 2003 fundamental argument
Ω from `_fundamental_args(T)[4]` (ERFA `faom03`). Mean Lilith never
got the matching series upgrade. The 5.2.2 work only added
`nutation=True|False`.

Issue #18 reports `Body.LILITH` versus Swiss `SE_MEAN_APOG` at
±4–7′ on eight 1955–2010 charts, with a sign-flipping residual.
`Body.TRUE_LILITH` already matches Swiss `SE_OSCU_APOG` to about 1′.
The reporter is treating Moira as a Swiss drop-in.

That residual is a series difference, not a frame bug:

| Object | What it is | Kernel |
| --- | --- | --- |
| Current `mean_lilith` | Meeus secular perigee + 180° | no |
| IERS analytical mean apogee | `F + Ω − l + 180°` from the same IERS 2003 arguments as the mean node | no |
| Swiss `SE_MEAN_APOG` | ELP-based hybrid that keeps selected periodic terms inside a quantity still labelled “mean” | Swiss files |
| `true_lilith` / `SE_OSCU_APOG` | Instantaneous osculating lunar apogee from DE state | yes |

A measured check of Meeus versus IERS `F+Ω−l+180°` on the eight
#18 dates, plus J2000 and 2026-08-15, differs by **0.003–0.14
arcseconds**. At 1625-01-01 the same pair differs by **1.16
arcseconds**. Finishing the IERS swap therefore does **not** close
the Swiss 4–7′ gap. Copying Swiss periodic terms would be worse
doctrine: Swiss is a secondary comparator, not the authority.

A DE-smoothed “physical mean” extracted from osculating apogee is a
third object. It needs a named window and a planetary kernel. It can
sit degrees away from the analytical mean. It must not silently
replace `Body.LILITH`.

## Decision

Ship mean Lilith as **three named products**, never as one name that
changes meaning when a file appears on disk.

1. **Default, no kernel.** `Body.LILITH` / `mean_lilith()` is the
   IERS 2003 analytical mean lunar apogee, same `nutation=` frame
   policy as `mean_node()`.
2. **Already shipped, kernel required.** `Body.TRUE_LILITH` /
   `true_lilith()` remains the DE osculating apogee.
3. **Later, kernel plus explicit ask.** A new function
   `smoothed_lilith(...)` is the DE-smoothed osculating apogee over a
   documented window. Receipts name that layer. Absence of a kernel
   is an error, not a reason to fall back to (1).

Phase 1 of this spec is (1) plus the documentation that (3) exists
as a later named product. Phase 2 implements (3) under its own plan
and must not retarget `Body.LILITH`.

## Goals

- `mean_lilith(jd_ut, nutation=False)` is the IERS mean apogee
  `F + Ω − l + 180°` from `_fundamental_args(T)`, ERFA-checkable
  against `faf03 + faom03 − fal03 + 180°`.
- Default `nutation=True` still adds IAU 2000A Δψ so chart Lilith
  stays in the true ecliptic and equinox of date.
- `NodeData.speed` is the derivative of that IERS combination. It
  excludes the short-period derivative of Δψ, matching mean-node
  policy.
- Chart, batch, synastry, progressions, and the facade keep calling
  `mean_lilith()`. No new required argument.
- Reduction receipts for Lilith name the IERS mean-apogee solution
  the same way Mean Node already names `iers_2003_mean_node_solution`.
- Docs and #18 state the Swiss residual is expected. Moira does not
  chase `SE_MEAN_APOG` digits.
- Kernel presence never changes which product `Body.LILITH` is.

## Non-goals

- Matching Swiss `SE_MEAN_APOG` to arcminutes or arcseconds.
- Implementing Swiss ELP periodic terms, `SE_INTP_APOG`, or
  `SE_INTP_PERG`.
- Implementing `smoothed_lilith()` in this release.
- Adding `Body.SMOOTHED_LILITH` in this release.
- Silently promoting `Body.LILITH` to a DE product when a kernel is
  found.
- Changing `true_lilith()` math, μ, or frame.
- Changing the 5.2.2 `nutation=` signature or default.
- Changing asteroid 1181 Lilith (NAIF 2001181). That is a different
  body.
- Closing #18 before Phase 1 is on a published engine release, or
  before an honest reply is posted.

## Three named products

| Layer | Public name | Object | Requires kernel | Auto-selected |
| --- | --- | --- | --- | --- |
| Analytical mean | `Body.LILITH`, `mean_lilith()` | IERS secular mean apogee | no | yes, this is the default |
| Osculating | `Body.TRUE_LILITH`, `true_lilith()` | Instantaneous DE apogee | yes | only when the caller asks for True Lilith |
| DE-smoothed mean | `smoothed_lilith()` (Phase 2) | Windowed smooth of osculating apogee | yes | never |

`mean` in `mean_lilith` describes the averaged orbital solution. It
does not describe the output frame. That sentence already governs
`mean_node` and stays true here.

## Phase 1 — IERS analytical mean

### Formula

Reuse the admitted IAU 2000A arguments. Do not add a second
polynomial.

```
l, l′, F, D, Ω = _fundamental_args(T)
mean_apogee_mean_equinox = normalize_degrees((F + Ω − l) * RAD2DEG + 180.0)
```

`T` is Julian centuries from J2000 in TT, via the existing
`ut_to_tt` / `centuries_from_j2000` path that `mean_node` uses.
IERS Conventions (2003) §5.7.2 already permits TT in place of TDB
for these arguments.

Identities:

- Mean lunar longitude `L = F + Ω`
- Mean perigee `L − l = F + Ω − l`
- Mean apogee = mean perigee + 180°

Authority for the raw mean-equinox longitude is ERFA `iauFal03`,
`iauFaf03`, `iauFaom03` (the same family as the existing mean-node
test against `iauFaom03`).

### Frame

Unchanged from 5.2.2:

```python
mean_lilith(jd_ut, *, nutation=True) -> NodeData
```

- `nutation=True` (default): add IAU 2000A Δψ.
- `nutation=False`: return the raw IERS mean-equinox-of-date
  longitude.
- `NodeData.name` stays `"Lilith"`.

### Speed

Differentiate `F + Ω − l` from the IERS 2003 coefficient lists
already coded in `_fundamental_args`. Convert arcseconds/century to
degrees/day by dividing by `3600 * 36525`. Do not fold Δψ into the
speed.

### Call sites

No signature change. These keep calling `mean_lilith(jd)` /
`mean_lilith(jd_ut1)`:

- `moira/chart.py`
- `moira/batch.py`
- `moira/synastry.py`
- `moira/progressions.py`
- facade re-exports

### Receipts

In `moira_server/services/chart.py`, replace the Lilith stage
`analytical_apogee_solution` with
`iers_2003_mean_apogee_solution`. Keep
`iau_2000a_nutation_in_longitude` and
`true_equinox_of_date_longitude`.
`source_surface` stays `moira.mean_lilith`.

Phase 2 receipts must name the smoothed layer explicitly when that
function exists. Phase 1 must not invent a kernel-conditional stage
list.

### Expected numerical shift

On the #18 dates (1955–2010), J2000, and 2026-08-15, IERS minus
current Meeus is **0.003–0.14″**. At 1625-01-01 it is **1.16″**.
This is a provenance repair, not a chart-visible redefinition.
Compatibility notes still record the series authority change.

The #18 Swiss residuals of ±4–7′ remain after Phase 1. That is
success, not a leftover bug.

## Phase 2 — DE-smoothed product (later)

A separate implementation plan owns this. This spec only locks the
product boundary so Phase 1 cannot “helpfully” grow into it.

- Public name: `smoothed_lilith(...)`.
- Object: a documented-window smooth of DE osculating lunar apogee.
  Window length, filter, and kernel identity are named in that later
  plan and in every receipt.
- Missing kernel: raise the same class of error `true_lilith()`
  already raises. Do not return IERS mean apogee.
- Do not assign this value to `Body.LILITH`.
- Do not add `Body.SMOOTHED_LILITH` until that plan is written.
- Do not auto-select this layer because `de441.bsp` (or any other
  file) is on disk. Light Box reproducibility forbids ambient
  promotion.

## Swiss policy

Swiss `SE_MEAN_APOG` is a **secondary corroboration**, the same
status as the existing mean-node Swiss fixture
(`test_mean_node_true_frame_is_corroborated_by_shipped_swiss_fixture`).

- Primary proof: ERFA IERS arguments and the Δψ frame invariant.
- Swiss may appear in a fixture with a tolerance wide enough to
  admit the known ELP-hybrid offset (several arcminutes).
- A Swiss residual inside that band is not a failure.
- Shrinking that band toward Swiss digits is out of scope.
- `SE_MEAN_APOG` → `Body.LILITH` stays a **symbolic** migration
  mapping: same astrological intent (mean apogee), not the same
  series.

`INTP_APOG` / `INTP_PERG` remain “no public Moira equivalent”.

## Documentation

Update these sentences so they stop implying a Meeus-only or
Swiss-identical mean Lilith:

- `moira/nodes.py` `mean_lilith` docstring: IERS 2003 mean apogee,
  same argument family as `mean_node`. Drop the Meeus 22.3 / Chapter
  47 wording.
- `wiki/02_standards/API_REFERENCE.md` (and the generated
  `moira.wiki` copy via the existing sync path).
- `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md`: the
  `SE_MEAN_APOG` row is a policy translation, not a numerical
  identity. State the expected 4–7′ ELP-hybrid residual.
- `wiki/03_validation/SWISS_EPHEMERIS_SYMBOL_TABLE.md`: keep
  `MEAN_APOG` as mapped / symbolic; note the series difference.
- `CHANGELOG.md` and
  `wiki/03_release/COMPATIBILITY_NOTES_<version>.md` for the release
  that ships Phase 1.
- Light Box / provenance text only if it currently claims Meeus as
  the mean-apogee authority.

## Issue #18

Do not close the issue until Phase 1 is in a published
`moira-astro` release, or an honest reply is posted and the reporter
accepts “expected series difference”.

The reply must say:

1. 5.2.2 upgraded the **frame**, not the **series**.
2. Phase 1 binds `Body.LILITH` to IERS `F+Ω−l+180°`, the same
   argument family as the mean node they already measured as 0.0000°
   versus `SE_MEAN_NODE`.
3. IERS versus the previous Meeus polynomial is sub-arcsecond on
   their dates. Their 4–7′ residual versus `SE_MEAN_APOG` remains,
   because Swiss keeps ELP periodic terms inside a “mean” label.
4. True Lilith matching `OSCU_APOG` is the intended DE product.
5. A later named `smoothed_lilith()` may exist. It will not replace
   `Body.LILITH` when a kernel is present.

Do not post that comment until the user asks, or until Phase 1
ships.

## Version

Ship Phase 1 in the next numbered `moira-astro` release that carries
this change. Public signatures do not change. Compatibility notes
are required because the series authority changes, even though
modern longitudes move by less than 0.2″.

Do not pick a version number in this spec. The release task names
it.

## Tests

Add IERS authority tests in
`tests/integration/test_mean_node_frame_consistency.py`, beside the
existing mean-node ERFA tests and the Lilith frame invariant:

- `nutation=False` matches
  `degrees(erfa.faf03(T) + erfa.faom03(T) − erfa.fal03(T)) + 180`
  modulo 360, within `1.0e-5` arcseconds, on the existing 1625 /
  1996 / J2000 / 2026 epochs.
- True-equinox longitude is mean-equinox plus Δψ (the current
  `test_mean_lilith_uses_the_same_explicit_equinox_policy` stays).
- `NodeData.speed` matches a finite difference of
  `nutation=False` longitudes, same tightness as the mean-node speed
  test (`abs=2.0e-9` °/day).
- Optional Swiss fixture on one or two #18 dates: residual versus
  the reporter’s `SE_MEAN_APOG` values is **inside** ±10′, and the
  test name / docstring say this is corroboration of “different
  series”, not a parity target.
- Server reduction test that today only checks
  `iau_2000a_nutation_in_longitude` on Lilith also requires
  `iers_2003_mean_apogee_solution`.

Do not add a golden test that freezes the current Meeus 22.3
coefficients.

## Risks

- **Someone “fixes” #18 by copying Swiss terms.** Forbidden. The
  tests above make Swiss a wide-band witness, not a target.
- **Someone wires kernel-present fallback.** Forbidden. Reproducible
  Light Box charts cannot depend on whether `de441.bsp` happened to
  be found.
- **Confusing asteroid 1181 Lilith with mean apogee.** The wheel
  catalog already labels 1181 as “asteroid Lilith, not mean apogee”.
  Do not blur the names.
- **Phase 2 scope creep.** Window choice, filter, and a new Body
  enum are a later spec. Phase 1 is the IERS default plus honest
  docs.

## Key Decisions

1. **IERS analytical mean is `Body.LILITH`.** Finishes the 5.2.2
   series job. Same argument family as `mean_node`. ERFA is the
   authority.
2. **Do not chase Swiss `SE_MEAN_APOG`.** The 4–7′ residual is the
   ELP hybrid versus a secular mean. Document it.
3. **DE-smoothed is a new named function, later.** Not a silent
   second meaning of `Body.LILITH`.
4. **No disk-based auto-promotion.** Kernel presence is not a
   product selector.
5. **Frame policy stays 5.2.2.** `nutation=True` by default. Speed
   is the mean-argument rate only.

## Open Questions

None that block Phase 1. Phase 2 still needs its own window,
filter, and API shape; those are not decided here.

## PR Plan

### PR 1 — IERS mean Lilith series

- **Title:** Bind `mean_lilith` to IERS 2003 `F+Ω−l+180°`
- **Files:** `moira/nodes.py`,
  `tests/integration/test_mean_node_frame_consistency.py` or sibling,
  `moira_server/services/chart.py`,
  `tests/server/test_server_chart_routes.py`
- **Dependencies:** none
- **Change:** replace the Meeus polynomial; keep the `nutation=`
  frame; update speed and the Lilith receipt stage name.

### PR 2 — Honesty docs and #18

- **Title:** Document mean Lilith as IERS, Swiss residual expected
- **Files:** API reference, Swiss migration guide, symbol table,
  CHANGELOG, compatibility notes
- **Dependencies:** PR 1
- **Change:** say what the series is and what it is not. Close or
  comment #18 only after the user approves the published wording.
