# Sothic epoch dating — research readiness

**Status:** assessment, not a plan of record. No work here is scheduled.
**Date:** 2026-11-15
**Scope:** `moira/sothic.py` and the heliacal path it delegates to.
**Question:** is the Sothic surface usable for research?

## Verdict

Two different uses, two different answers.

**Drift-rate and cycle-structure work: yes.** The fitted rate moves only
0.2491 to 0.2509 d/yr across arcus visionis 9 to 11 degrees, is stable across
2,900 years, and the epoch window size is exactly `2 * tolerance / 0.25` at
every tolerance tested. The astronomy underneath is DE441 with independent
Astropy/ERFA corroboration at two sites and two epochs.

**Epoch dating: not yet.** One parameter that the Sothic path sets by hand
decides whether the anchor year of the whole scheme registers as an epoch, and
whether a computed window sits where it sits.

## The decisive measurement

`moira/stars.py::_default_arcus_for_star` derives arcus visionis from the
star's catalogue magnitude under the visibility model whose canon
`moira/heliacal.py` already names: Schaefer, B.E. (1990), PASP 102, 212-229,
in the Ptolemy/Schoch tradition. For Sirius at magnitude -1.46 it returns
**7.5 degrees**.

`moira/sothic.py` does not use it. `SothicHeliacalPolicy.arcus_visionis`
is **10.0**, a constant with no recorded derivation, and it is passed through
on every call. The two differ by 2.5 degrees.

The rising date moves about one day per degree of arcus visionis. Measured at
Memphis (29.8, 31.3), AD 139:

| arcus visionis | rising date | drift from 1 Thoth |
|---|---|---|
| 7.5 deg — engine's own sourced model | 16 Jul | **-2.90 d** |
| 8 deg | 16 Jul | -2.90 d |
| 10 deg — Sothic hardcoded default | 18 Jul | **-0.91 d** |
| 11 deg | 20 Jul | +1.09 d |
| 14 deg | 23 Jul | +4.08 d |

Two consequences, both load-bearing:

**The Censorinus anchor registers as an epoch under one model and not the
other.** At 10 degrees AD 139 sits 0.91 days from alignment and is inside a
one-day tolerance. At the engine's own 7.5 degrees it sits 2.90 days out and
is not an epoch at all.

**The computed window moves by twelve years.** One cycle before AD 139, with a
one-day tolerance:

```
arcus 10.0  ->  -1319 .. -1312
arcus  7.5  ->  -1307 .. -1300
```

Twelve years of Egyptian chronology turn on a constant that contradicts the
engine's own sourced derivation, with nothing recording why.

This is the condition `AGENTS.md` Part IV calls a hidden default replacing
declared policy. It is not a numerical error — both numbers are computed
correctly from their inputs — and it is not a reason to prefer 7.5 over 10.
It is a reason not to publish an epoch date from either until the choice is
made deliberately and recorded.

## Gaps, with evidence

### G1 — arcus visionis is chosen, not derived, and dominates the result

Evidence: above. `SothicHeliacalPolicy.arcus_visionis = 10.0` against
`_default_arcus_for_star("Sirius") = 7.5`.

To close: record which model governs the Sothic product and why, in the
policy rather than in prose. The current state — a constant that silently
overrides a sourced model — is not defensible either way.

**Choosing by accuracy does not select between 7.5 and 10.** Both are
constants in the legacy geometric criterion, and neither carries external
validation. The engine already has a path that does:

| | geometric arcus path (what Sothic uses) | physical visibility path |
|---|---|---|
| criterion | solar depression and star altitude | limiting magnitude against target magnitude |
| event definition | — | Schaefer, JHA 18 (1987), S19-S33 |
| physical basis | — | Tousey and Koomen, JOSA 43 (1953), 177-183 |
| independent oracle | — | Hipparcos + Astropy/ERFA + JPL Sun, reproduced to 0.01 s |
| validated case | — | `phase3-sirius-2026-morning-first-rising` |

So the accuracy question is not which constant, it is which path. Only the
physical one is anchored, and routing the Sothic search through it is the
change that an accuracy argument actually supports. That is G2, not G1.

Two cautions keep this from being a clean win, both already stated by the
repository itself:

- `heliacal_rising_oracle_matrix.json` admits
  `maximum_legacy_difference_days: 3.0` for Sirius, which is wider than the
  2.5 day gap between the two arcus values. The existing anchor therefore
  cannot discriminate 7.5 from 10 even in principle.
- The visibility authority entry states that "exact dates remain
  observer-policy dependent", the golden's observer protocol is
  `known_location_directed_averted_observation_v1` — a modern directed and
  averted-vision observer, not an ancient one watching an eastern horizon —
  and its limitations record that "subjective observer and real atmosphere
  uncertainty are not probabilistic confidence".

An epoch date will therefore carry a band of days under any model. The
physical path narrows and sources that band; it does not remove it, and no
arcus constant can.

Evidence class required: **doctrine source** for which path governs, then
**authority validation** for the path chosen.

### G2 — the visibility model is geometric, and the physical stack is unwired

`heliacal_rising_event` gates on solar depression and star altitude.
`HeliacalEvent` carries `arcus_visionis`, `elongation_threshold`,
`qualifying_elongation`, `qualifying_sun_altitude` and `event_jd_ut`. There is
no extinction, airmass, sky brightness or limiting magnitude in the result.

`moira/heliacal.py` already implements all of it — `atmospheric_extinction`,
`relative_optical_airmass`, `directional_twilight_sky_brightness`,
`visual_limiting_magnitude`, Krisciunas & Schaefer 1991 — and the Sothic path
never calls it. The physics exists in the repository and is not reached.

Note also that `VisibilityModel()` defaults to 10 C, 1013.25 mbar, 50 percent
relative humidity and extinction coefficient 0.25. Those are not Egyptian
desert conditions at a July pre-dawn horizon, so wiring the stack in without
site-appropriate parameters would exchange one undeclared assumption for
another.

**Desert conditions are a data-resource question, not a parameter question.**
This is the practical finding, and it is easy to get wrong.

The physical path does not take ad-hoc temperature and humidity. Its inputs are
the axes of a precomputed data pack, `VisibilityDataPackDomain`:
`atmosphere_profile`, `aerosol_profile`, `observer_altitude_m`,
`surface_pressure_hpa`, `aod550`, `angstrom_exponent`, `ozone_du`,
`ground_albedo`, and the viewing geometry. Egyptian desert conditions are
expressed there — as aerosol optical depth, Angstrom exponent and the high
ground albedo of sand — not as the `temperature_c` and `relative_humidity`
fields on the legacy vessel.

Three consequences:

- Interpolation is `trilinear` and extrapolation is `prohibited` on every
  axis. A desert value outside the installed pack's grid is not evaluable;
  it is a typed domain error, by design.
- The pack is an **external resource**, `moira-physical-heliacal-visibility`
  1.2.0, CC BY-SA 4.0, built from libRadtran, REPTRAN and CIE source tables.
  The distribution ships only the engine, the compatibility contracts and a
  notice. There is no automatic downloader, and no pack is installed in this
  checkout.
- Rebuilding a pack for a domain the published one does not cover means
  running `scripts/build_visibility_data_pack.py` against libRadtran, which is
  its own provenance exercise.

Two facts in this path's favour, both checked:

- The pack's domain is atmosphere and geometry only. It carries no date axis,
  so ancient epochs are **not** out of domain by virtue of being ancient. The
  domain risk is entirely about atmospheric parameter coverage.
- `Sirius` is already the stellar target profile the pack supports, and the
  result vessel carries `derived_arcus_deg` rather than accepting a constant,
  plus `visibility_margin_bracket_jd_ut` and an
  `atmospheric_scenario_event_interval_jd_ut` on the sensitivity receipt —
  that is G3's band, already built, merely not reached from Sothic.

To close: install the published pack and read its actual domain before
choosing any desert values. If Egyptian aerosol and albedo lie inside it,
route the Sothic search through `physical_visibility_event` with a declared
site profile and carry the receipts onto the Sothic result. If they lie
outside, the honest options are to rebuild the pack or to state the Sothic
product as restricted to the published domain.

Evidence class required: **authority validation** against the named canon,
plus **invariant** checks that the physical path reduces to the geometric one
under matched assumptions.

### G3 — no uncertainty is carried on a rising date

`SothicEntry` exposes a single `jd_rising`. Research needs "day X plus or
minus N", and N is not derivable from the result.

The sensitivity is already measurable and large: about one day per degree of
arcus visionis, and 0.0017 d/yr of drift rate per 0.05 degrees of site
latitude — the latter being larger than the rate's variation across three
thousand years.

To close: propagate the declared parameter ranges into a band on the rising
date, and report it. A single JD with no band invites false precision, which
this subsystem has already demonstrated once: see
`moira/sothic.py::sothic_drift_rate`, whose docstring asserted a rate that was
never measured.

Evidence class required: **invariant** — the band must contain the result
under the stated parameter sweep.

### G4 — delta-T is a point value at epochs where its uncertainty rivals the signal

Measured: 0.106 day at AD 139, 0.371 day at -1321, 0.414 day at -2790.
`DeltaTTruth` carries `seconds`, `source_product`, `retarget_mode` and
`tidal_terms` — no uncertainty band.

At the third millennium BC the uncertainty in delta-T is itself of order the
quantity being measured, so an epoch date there is less determinate than its
single-value presentation suggests.

To close: expose the delta-T uncertainty admitted by the chosen source product
and fold it into the G3 band.

Evidence class required: **authority validation** against the delta-T source
product's own stated uncertainty.

## The circularity to avoid

The obvious move is to choose arcus visionis so that AD 139 lands on 1 Thoth,
since Censorinus says it did. That would make the anchor confirm itself, and
every epoch derived from it would inherit the assumption as though it were a
result.

This subsystem has already produced one instance of exactly this pattern at
smaller scale. Until 2026-11-15 the only numeric test of the drift rate built
a synthetic series stepping by the value the docstring asserted and then
asserted the fit returned that value, so the stated rate could not fail. It
was wrong by 3.7 percent for as long as it stood.

Arcus visionis must therefore be fixed from the visibility model and the
research question, and the anchor's agreement or disagreement reported as an
outcome. If the chosen model puts AD 139 three days from 1 Thoth, that is a
finding about the model, the site, or the tradition — not a defect to tune
away.

## What is already sound, and should not be redone

- Heliacal risings against DE441, with independent Astropy/ERFA corroboration
  at Memphis and Alexandria for AD 139 and -1321.
- The drift rate, now anchored against real risings at two epochs three
  thousand years apart and documented as a range rather than a false constant.
- Epoch window semantics: the window size is `2 * tolerance / 0.25` by
  construction, verified at three tolerances, and the result documents that
  consecutive years are one realignment.
- The schematic projection is labelled `SCHEMATIC_1460_JULIAN_YEAR`, the
  oracle matrix calls the cycle an arithmetic identity rather than
  observational confirmation, and the divergence from the computed window is
  now stated and pinned by test.

The honesty layer is in place. It is the physical layer that is thin.

## Standing status

All twelve Sothic canonical surfaces are classified `unresolved` in
`wiki/03_validation/LIGHT_BOX_CONFORMANCE_MANIFEST.generated.json`. Engine-wide
the count is 0 conformant, 219 partial, 1127 unresolved, so this is not a
Sothic-specific deficit — but nothing here claims conformance, and this
document does not either.

## Reproduction

With the project `.venv` and a discovered DE441 kernel:

```python
from moira import Moira
from moira.spk_reader import use_reader_override
from moira.sothic import sothic_rising, sothic_epochs
from moira.stars import _default_arcus_for_star

m = Moira()
print(_default_arcus_for_star("Sirius"))          # 7.5
with use_reader_override(m._reader):
    for av in (7.5, 10.0):
        e = sothic_rising(29.8, 31.3, 139, 139, arcus_visionis=av)[0]
        w = sothic_epochs(29.8, 31.3, -1335, -1300,
                          tolerance_days=1.0, arcus_visionis=av)
        print(av, e.drift_days, sorted(x.year for x in w))
```

## What this document does not claim

- It does not say 7.5 degrees is correct and 10.0 wrong, or the reverse.
- It does not claim the engine's heliacal risings are inaccurate. No external
  authority comparison of the rising date itself was performed here; the
  Astropy/ERFA corroboration in the test suite is geometric.
- It does not propose a chronology, or bear on any historical dating dispute.
- It does not schedule work.
