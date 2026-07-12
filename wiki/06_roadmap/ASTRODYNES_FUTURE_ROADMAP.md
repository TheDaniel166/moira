# Astrodynes Future Roadmap

Status: active execution roadmap after completion of the bounded natal
Astrodynes constitution and three-chart displayed-output parity

Date: 2026-07-12

Implementation update (2026-07-12): P0-P12 are admitted for the kernel-free,
explicit-geometry doctrine. Practical distribution, the complete dated table,
facade exports, REST/OpenAPI, and discrepancy provenance are implemented and
tested. The separately bounded Church of Light astronomical chart adapter is
also implemented with explicit time-key, frame, angle, house, and fallback
truth. See
`wiki/02_standards/PROGRESSED_ASTRODYNES_BACKEND_STANDARD.md`.

## 1. Current Baseline

The bounded natal subsystem is complete through:

- source-owned Church of Light dignity, house-power, aspect-orb, parallel,
  harmony/discord, mutual-reception, ruler-share, and Class 5 summary doctrine
- deterministic body, relation, profile, sign, house, summary, and network
  vessels
- kernel-free explicit-geometry computation
- package-root and `Moira` facade exposure
- typed `/v1/astrodynes/doctrine`, `/geometry`, and `/chart` routes
- all displayed planet, relation-grid, sign, house, summary, and chart-total
  outputs for the Trump, Gandhi, and Walters reports within the documented
  explicit-geometry tolerances

This roadmap does not reopen natal doctrine that is already admitted. It
separates residual natal evidence, progressed Astrodynes, astronomical adapters,
and public transport so that no later convenience layer silently changes the
governing object.

## 2. Governing Boundaries

### 2.1 Authority

Primary authority remains Elbert Benjamine and W. M. A. Drake, *The Astrodyne
Manual* (1946). Before progressed implementation, visually inspect and capture
the relevant tables, charts, and examples on manual PDF pages 25-54. Text
extraction is discovery evidence only; layout-bearing tables and chart columns
must be verified from rendered pages.

### 2.2 Ontology

The progressed subsystem must preserve these distinct products:

- natal power and harmony/discord
- the normal progressed horoscope before accessory aspects
- independent major, minor, and transit progressed-aspect influence
- direct and indirect radical/progressed terminals
- minor-aspect reenforcement of major aspects
- practical sign and house totals on a specified date
- integrated influence over a bounded interval

No one generic `progressed_score` may collapse these objects.

### 2.3 Astronomical adapter boundary

The doctrine core must accept explicit, already-resolved geometry and remain
kernel-free. Existing `moira.progressions` products may supply geometry only
after their time key, direction, frame, angle, and terminal semantics have been
shown to match the Church of Light product. Similar terminology is not proof of
equivalence.

### 2.4 Claims

Do not claim progressed parity until the Benjamine worked example is executable
term by term. Do not broaden the three-chart natal parity claim to progressed
work, autonomous reconstruction from printed labels, or independent validation
of the historical Church of Light ephemeris.

## 3. Residual Natal Evidence Track

These items improve the proof record but do not block the admitted natal
surface.

### N1 - Direct mutual-reception table capture

- Locate a legible copy of the standalone table referenced by the manual.
- Render and archive the relevant page with provenance.
- Compare every table entry with the currently derived home-or-exaltation rule.
- Record any exception before changing executable doctrine.

Acceptance gate: either the table is captured and agrees row-for-row, or the
record states that the primary verbal rule plus named worked pairs remains the
best available authority.

### N2 - Exact-degree dignity example

- Search the manual and companion Church of Light lessons for an independent
  numeric example of the one-degree `+4/-4` exaltation/fall tier.
- Pin the inclusive boundary and sign-degree convention if found.

Acceptance gate: an authority-backed example test exists, or the present
source-derived but example-unhit limitation remains explicit.

### N3 - Multi-cusp sign doctrine

- Research whether Church of Light ruler-share aggregation permits more than
  two house cusps in one sign.
- Do not infer an extension merely from the current half-per-cusp formula.
- If authority supports arbitrary counts, generalize `ruler_power_share`, sign
  aggregate validation, explicit-geometry validation, and REST edge tests
  together.

Acceptance gate: either authority-backed generalization with polar fixtures, or
continued explicit rejection as a documented bounded limitation.

### N4 - Benjamine natal reconstruction (optional)

- Transcribe the manual wheel inputs if a direct Benjamine natal oracle is
  desired in addition to the three executable reports.
- Keep historical ephemeris/house-system reconstruction separate from direct
  figure transcription.

Acceptance gate: the fixture names whether it is direct transcription,
historical reconstruction, or modern-engine corroboration.

## 4. Progressed Astrodynes Implementation Sequence

### P0 - Progressed source codex

Create a tracked source-capture document and fixture packet before engine code.
It must transcribe:

- normal progressed carry ratios: major `1/2`, major Moon `1/14`, minor
  `1/54.6`, transit `1/730.50`
- progressed aspect percentage derivation: applicable natal orb degrees times
  `0.05`, parallel treated as conjunction, Mercury using the luminary scoring
  column, and the strongest relevant house class
- major Moon divisor `7`, minor divisor `27.3`, and transit divisor `365.25`
- the one-effective-degree current-date curve, from half peak at 60 arcminutes
  to full peak at perfection
- the progressed mutual-reception `+2.50` rule while the aspect is within orb
- direct/indirect terminal rules and the two-terminal self-aspect exception
- minor reenforcement, including power-only behavior and the half-strength
  indirect-terminal rule
- practical sign/house distribution rules
- total-influence units and the manual's constant-rate `0.75 * peak * duration`
  rule
- every printed intermediate and output in the Benjamine 1949 examples

Required fixtures should include source page, printed input, exact decimal
interpretation, printed output, rounding rule, and evidence class.

Gate P0: no unresolved load-bearing glyph, table cell, terminal label, or unit
conversion remains.

### P1 - Fixed progressed doctrine and scalar truth

Recommended new module: `moira/progressed_astrodynes.py`.

Implement immutable source/policy vessels and pure scalar functions for:

- carried normal power and harmony/discord
- progressed aspect percentage selection
- peak power by progression tier
- current-date power within the 60-arcminute band
- progressed harmony/discord translation
- progressed mutual reception
- constant-rate total influence

Each result retains its operands, selected row/percentage, divisor, distance,
scale fraction, units, and unrounded result.

Gate P1: every scalar manual example passes at internal precision and at the
manual's printed rounding; zero, exact, 60-arcminute, just-outside, Moon,
Mercury, angle, and non-finite cases are pinned.

### P2 - Normal progressed horoscope

Build explicit input and result vessels for the normal progressed figure:

- natal `AstrodyneChartResult` as the immutable baseline
- major progressed planet/angle longitudes, declinations, signs, and houses
- carried power and harmony/discord by planet
- dignity contribution in the progressed sign
- normal progressed sign and house aggregates
- dated cusp/house transitions, including the major progressed Moon

The engine must not acquire ephemerides or choose a progression method here.

Gate P2: the Benjamine normal progressed planet, sign, and house examples pass;
normal totals reconcile deterministically under input-order permutation.

### P3 - Terminal and relation ontology

Add typed identities for:

- radical terminal (`r`)
- major progressed terminal (`p`)
- minor progressed terminal
- transit terminal
- direct versus indirect participation
- major, minor, transit, and reenforcement relation kinds

Relations must preserve all evaluated candidates separately from admitted,
independently scored, and reenforcement-only subsets. Stable relation IDs and
canonical ordering are required.

Gate P3: duplicate, self, missing-terminal, invalid-tier, ambiguous-directness,
and ordering cases fail deterministically.

### P4 - Major progressed peak relations

Implement peak power and peak harmony/discord for major progressed aspects,
including:

- average natal power of the bodies involved
- progressed percentage selected from aspect and strongest house class
- Moon division by seven
- neutral, harmonious, and discordant aspect families
- Venus/Jupiter/Mars/Saturn nature modifiers
- the in-orb progressed mutual-reception addition

Gate P4: reproduce the manual's listed Benjamine peak relations, not merely a
single example.

### P5 - Major progressed influence on a date

Implement the admitted linear one-degree curve and dated relation vessel:

- exact aspect equals peak
- 60 arcminutes equals half peak
- values inside the band interpolate linearly
- values outside the band are detected but not admitted/scored
- power and harmony/discord retain separate truth

Gate P5: boundary/property tests plus all dated major examples pass.

### P6 - Relative terminals and practical distribution

Implement:

- direct terminal receives full aspect influence
- indirect terminal receives half
- normal terminal power/harmony remains visible separately
- ruler distribution to cusp and intercepted signs/houses
- occupied-terminal distribution
- practical planet, sign, and house totals for a date

Gate P6: reproduce the manual's August 29, 1949 terminal calculations and the
worked seventh- and ninth-house totals term by term.

### P7 - Independent minor and transit influence

Implement minor and transit aspects as their own typed products using the
manual divisors, current-date curve, angle/parallel inclusion, and trigger
metadata. Do not encode predictive advice or event certainty.

Gate P7: reproduce the minor progressed Ascendant parallel Venus and transiting
Neptune sesqui-square progressed Sun examples at peak and on the stated date.

### P8 - Minor reenforcement of major aspects

Implement reenforcement separately from independent minor influence:

- evaluate a minor aspect against each lawful major terminal
- select direct or indirect strength
- modify major power only, leaving its harmony/discord unchanged
- admit multiple simultaneous reenforcements additively
- preserve unreenforced, each reenforcement, and final reenforced power

Gate P8: reproduce the June 16, September 5, and August 29 Benjamine examples,
including the direct/indirect half-strength cases.

### P9 - Total influence over an interval

Implement the manual's constant-rate analytic product first:

- explicit entry and exit times for the one-degree band
- duration and unit vessel
- average factor `0.75`
- astrodyne/harmodyne/discordyne days, months, and years
- explicit 30-day month conversion where the manual uses it

Variable-rate integration is not admitted merely by numerical convenience. It
requires a separate doctrine decision defining whether the product is an exact
integral, a sampled observing product, or an approximation to the manual's
constant-rate rule.

Implementation update: this decision is now explicit. The admitted extension
is a sampled numerical integral of the source instantaneous curve, labeled as
Moira composite-trapezoid quadrature with visible step/sample/error truth. It
does not replace or rename the manual's constant-rate rule.

Gate P9: reproduce the Saturn inconjunct natal Sun total-influence example and
reject unsupported variable-rate semantics explicitly.

### P10 - Full Benjamine progressed parity

Create a primary-source integration fixture for the 1949 worked example. It
must cover:

- normal progressed figure
- the printed major relation list
- dated power and harmony/discord
- relative terminals
- practical signs and houses
- minor and transit examples
- reenforcement
- total influence

Gate P10: every captured printed intermediate and output passes under named
tolerances. A modern-kernel reconstruction may corroborate geometry but must not
replace the explicit source fixture.

### P11 - Hardening and constitutional documentation

Add:

- cross-layer validation functions
- deterministic ordering and unique identity tests
- finite/range/type adversarial tests
- exact/orb-boundary and discontinuity tests
- aggregate and distribution invariants
- direct/indirect terminal conservation checks
- regression tests proving natal outputs are unchanged
- a sovereignty/lineage smell audit
- a progressed Astrodynes backend standard and API reference

Gate P11: the focused natal plus progressed suite passes with strict known-issue
expiry and no hidden xfail/skip.

### P12 - Public engine, facade, and REST admission

Only after P10-P11:

- curate module and package-root exports
- add a predictive-facade delegate without moving doctrine into the facade
- expose a kernel-free explicit-geometry route
- expose a chart-backed route only for progression methods whose Church of
  Light geometry mapping has been validated
- expose a doctrine endpoint with the progressed tables, ratios, terminal law,
  and integration limits
- provide fully typed derivation, terminal, distribution, reenforcement,
  interval, validation, and provenance responses

Admitted REST namespace:

- `GET /v1/astrodynes/progressed/doctrine`
- `POST /v1/astrodynes/progressed/normal`
- `POST /v1/astrodynes/progressed/dated-aspect`
- `POST /v1/astrodynes/progressed/major-relation`
- `POST /v1/astrodynes/progressed/accessory-relation`
- `POST /v1/astrodynes/progressed/reenforcement`
- `POST /v1/astrodynes/progressed/practical`
- `POST /v1/astrodynes/progressed/total-influence`
- `POST /v1/astrodynes/progressed/compound-total-influence`
- `POST /v1/astrodynes/progressed/chart`

Do not add arbitrary search, prediction, or advice endpoints in this phase.

Gate P12: OpenAPI operation IDs are unique, request/response schemas are strict,
kernel-free behavior is proved for explicit geometry, chart adapters disclose
time key/frame/house fallback, and engine/REST results agree.

## 5. Post-Constitution Product Work

### X1 - Progressed influence search — Complete

Bounded entry, perfection/closest-approach, exit, and minor reenforcement search
is implemented in `moira.progressed_astrodynes_search`. Results expose terminal
identity, coarse step, refinement tolerances, sample bounds, clipped request
boundaries, and the resolved relation. Variable-rate integration is a separate
Moira numerical product with the manual's constant-rate rule preserved as a
comparator.

### X2 - Urania/workspace packet

Compose existing engine truth into UI-ready packets only after the direct REST
surface is stable. Keep normal baseline, accessory influence, reenforcement,
and integrated influence visually and semantically distinct.

### X3 - Printed-label reconstruction tooling

If needed for research ingestion, build an explicitly non-authoritative helper
that records atlas source, historical timezone, house system, ephemeris, and
residuals. It must never silently overwrite captured wheel geometry.

### X4 - Cosmodynes nomenclature decision

Research whether `Cosmodynes` is merely a lineage/family synonym in the admitted
sources or names an additional computational product. Do not create a second API
name until a distinct governing object is demonstrated.

## 6. Critical Files

Expected new or changed implementation paths:

- `moira/progressed_astrodynes.py`
- `moira/__init__.py`
- `moira/facade.py`
- `moira/_facade_predictive.py`
- `moira_server/models/astrodynes.py`
- `moira_server/services/astrodynes.py`
- `moira_server/serializers/astrodynes.py`
- `moira_server/routers/astrodynes.py`
- `moira_server/openapi.py`
- `tests/unit/test_progressed_astrodynes.py`
- `tests/integration/test_progressed_astrodynes_church_of_light.py`
- `tests/server/test_server_astrodynes_routes.py`
- `tests/fixtures/progressed_astrodynes_church_of_light.json`
- `wiki/02_standards/PROGRESSED_ASTRODYNES_BACKEND_STANDARD.md`
- `wiki/02_standards/API_REFERENCE.md`
- `wiki/02_services/REST_API_REFERENCE.md`

Existing `moira/astrodynes.py` should remain the stable natal constitution.
Share public natal vessels and doctrine deliberately; do not refactor the natal
engine merely to make the progressed module aesthetically symmetrical.

## 7. Verification Ladder

Run the smallest gate first at every phase:

1. scalar manual-example unit tests
2. phase-local adversarial and invariant tests
3. Benjamine explicit-geometry integration fixture
4. natal regression and three-chart parity suite
5. facade/public-export identity tests
6. REST/OpenAPI/error-mapping tests
7. documentation consistency check
8. broader non-network suite only after focused gates pass

All commands use the project `.venv`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, and downloads disabled unless a named validation
step explicitly requires otherwise.

## 8. Recommended Execution Order

1. Commit the current natal documentation cleanup independently.
2. Complete P0 and decide N1-N3 without engine edits.
3. Implement P1-P5 as the kernel-free progressed relation core.
4. Implement P6-P9 as distribution, reenforcement, and interval products.
5. Close P10 primary-source parity.
6. Complete P11 hardening and documentation.
7. Admit P12 public/facade/REST surfaces.
8. Evaluate X1-X4 as separate product decisions.

The first new implementation phase should not begin until the P0 source codex
has cleared its gate.
