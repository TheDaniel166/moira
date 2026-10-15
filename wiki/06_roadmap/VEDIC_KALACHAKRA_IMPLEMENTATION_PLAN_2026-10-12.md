# VED-014: Kalachakra Dasha implementation plan

**Date:** 12 October 2026. **Status:** All seven stages implemented and validated locally.
**Inspected baseline:** `8852052f317d7f3841e1e390578e303f438140a8`, Moira 6.9.9,
project Python 3.14.3. **Owner:** [remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md).
**Evidence:** [online and local source research](VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md).
**Execution:** [validation receipt](../03_validation/VEDIC_KALACHAKRA_VALIDATION_2026-10-12.md) and [public API](../02_services/KALACHAKRA_DASHA_API.md).

Deliver the named `bphs_santhanam_longitude_row_cycle_v1` profile through the
Python engine, public facades and REST, with identical doctrine, bounds,
provenance and validation. The profile identifies the inspected Santhanam
translation/commentary and its reconciled tables; it does not claim that all
BPHS editions or Kalachakra traditions agree.

This document settles the implementation choices left by the research packet.
The user subsequently authorized execution of all seven stages. Publication
remains a separate request. The seven stages below form one implementation package. Website
features, native acceleration, additional traditions and unrestricted deeper
subdivision are separate packages.

## 1. Admission decisions

| Concern | Initial contract |
| --- | --- |
| Profile selection | Required exact profile ID; no unnamed default, `classical` boolean or caller-editable recipe |
| Seed | Equal 27 nakshatras / 108 padas from sidereal lunar longitude; the special Kalachakra rows are not ordinary D9 output |
| Balance | BPHS 46.93: fraction traversed in the occupied pada times that row's total source years |
| Major periods | Select an occurrence by cumulative duration, then repeat the same natal row; exactly nine MD occurrences including the residual birth MD |
| Antardashas | Optional level two: rotate the natal row from each MD's row occurrence; divide by the unchanged natal-row total |
| Bounds | `levels` is a strict integer, 1 or 2, default 2; nine MDs and at most 81 ADs; no cycles, duration-horizon, arbitrary window or deeper-level switches |
| Deha/Jeeva | Endpoints of the natal row, reversed for Apasavya; return `reference=natal_row` |
| Gati | Ordered transition evidence and the bounded classification in section 3.5; contested Cancer/Leo direction remains explicitly unresolved |
| Eligibility | `eligibility_status=not_evaluated`, with KC-12 evidence; no invented Moon/navamsa-lord strength threshold or assertion of universal applicability |
| Source/calendar separation | Source-only results require no projection or kernel for supplied sidereal longitude. Calendar projection is optional and separately identified |
| Calendar clock | Projection requires `savana_360` or `julian_365.25`; no default clock or arbitrary days-per-year override |
| Calendar axis | UTC-derived Julian date, named `jd_utc`, for fixed-day scheduling; separate `jd_ut1` / TT / TDB provenance for astronomy |
| Active lookup | Explicit query instant, half-open intervals, bounded coverage; never implicitly use the wall clock or extend the sequence |

Traditional row totals are duration weights, not factual lifespan estimates.
Gati and Deha/Jeeva remain source-defined metadata, without newly generated
illness, death, fortune or election predictions.

## 2. Source-conflict ledger and acceptance assertions

Source IDs, hashes, one-based PDF pages and printed-page coordinates come from
section 2 of the research packet. Retain rule-level citations and applied
correction IDs in catalogue metadata and results. Separate literal readings,
selected corrections, independently derived values and unresolved evidence.

| ID | Decision for this profile | Required acceptance assertion |
| --- | --- | --- |
| KC-01 | Select the reconciled Rohini tables: A1/1 ends Cancer; A1/2 ends Libra | Both nine-entry rows match independent fixtures; the legitimate two Scorpios and two Libras in A1/2 survive |
| KC-02 | Select Mrigashira-2 `Ge Ta Ar Sg Cp Aq Pi Ar Ta` | Exactly nine occurrences; both Aries and Taurus repetitions retained |
| KC-03 | Revati belongs to S1 and Uttara Bhadrapada to S2 | All 27 memberships exactly once; both disputed memberships asserted explicitly |
| KC-04 | Use Cp/Aq in the disputed S1/2 Krittika diagram position | Compare against the upper BPHS table and Rao Table 44, not the defective duplicate diagram |
| KC-05 | BPHS 46.84 weights govern AD formulas; only visually checked AD cells become numerical source oracles | Scorpio 7, Virgo 9, Libra 16; formula conservation plus checked Aries/Aries and Taurus/Taurus witnesses. Extraction flags are not all declared print errors |
| KC-06 | Select longitude fraction under 46.93 | Reject ghatika/bhayat/bhabhoga inputs and time-balance switches; keep fixed-15 and actual-quarter calculations as distinct evidence |
| KC-07 | Repeat the natal row after its last occurrence | BPHS 34°50′ continuation matches its printed sequence and differs from Rao 2000's continuous traversal and JP's pada-sign school |
| KC-08 | Rotate that same row for ADs; denominator is its total | Taurus/Taurus is `256/100`, not Rao's `256/97`; never substitute the competing school's AD start |
| KC-09 | Deha/Jeeva use the complete natal row | Clipping, birth occurrence and generated depth cannot change these labels |
| KC-10 | Preserve both directed Cancer/Leo edges as unresolved classification with this conflict ID | No corrected Markati label is inferred from Rao; sequence order is unaffected |
| KC-11 | Kapoor's Phaladeepika reflow is not sequence authority here | Its conflicting direction labels, seed mapping and Bharani-3 ending cannot override the selected catalogue |
| KC-12 | Record eligibility as not evaluated | Missing strength never becomes zero, false or an implicit unconditional eligibility claim |
| KC-13 | Preserve exact source durations and require a named projection clock | Same source sequence under both clocks; endpoints differ only by the declared projection; astronomy and schedule timescales remain distinct |
| KC-14 | Product returns nine MDs | No tenth partial MD to fill a nominal horizon; preserve the complete ten-entry printed Rao exercise as candidate evidence |

Research candidates remain discoverable with `admission_status=research_candidate`
and `selectable=false`: Rao 2000 continuous traversal, Sastri's pada-sign school,
Rao's later reformulation, Rath's named alternatives, and software-listed
methods whose full recipes have not been reviewed. Use stable candidate record
IDs outside the admitted profile selector. Candidates are never partially
executable through policy flags.

## 3. Computational and numerical contract

### 3.1 Input admission and exact seed arithmetic

Admit finite Python `int` / `float` longitudes in `[0,360)`, excluding booleans,
numeric strings and arbitrary numeric objects. Reject rather than normalize
caller-supplied out-of-range angles. Derived tropical-to-sidereal reduction alone
uses `(tropical - ayanamsa) % 360` once. The same rules apply to JSON inputs.

Interpret each accepted float as its exact binary64 ratio. Use rational
boundaries `b[k] = 10*k/3` degrees for `k=0..108`; select `b[k] <= L < b[k+1]`.
Do not add epsilon or snap an input to a theoretical pada boundary. For example,
`float(10/3)` is a representable neighbour of the rational edge, not an exact
sexagesimal boundary. Tests must establish its side using an independent ratio.

For the chosen row `R`, integer weights `w`, total `P`, and fraction
`f = (L-b[k]) / (10/3)`, calculate `E = f*P`. Let `C[i]` be the cumulative
weight before row occurrence `i`. Select `C[i] <= E < C[i+1]` by exact comparison.
All weights and source-year partitions use `fractions.Fraction` or equivalent
integer-ratio arithmetic. Converting public longitude to a ratio does not make
its originally intended decimal/sexagesimal value exact.

Use zero-based sign indices, row positions, path ordinals and cycle indices;
use one-based nakshatra numbers and pada numbers, with field names documenting
the distinction. Validate the complete 16-row / 27-membership catalogue at
construction and against independently transcribed fixtures.

### 3.2 Nine MD occurrences and full-parent ADs

Birth is source-year offset zero. The first MD's full interval is
`[C[i]-E, C[i+1]-E)` and its visible interval begins at zero. Later MDs follow
the row cyclically. For emitted MD ordinal `m=0..8`:

- Row position is `(i+m) % 9`; MD row-cycle index is `(i+m) // 9`.
- Full length is that occurrence's sign weight; continue from the exact previous
  full endpoint. Only the first MD can begin before birth.
- Path is `(m,)`; identical sign/ruler names never identify a period uniquely.

For every MD at row position `j`, construct nine full ADs in order
`R[(j+a)%9]`, `a=0..8`, with duration `w(R[j])*w(R[(j+a)%9])/P`.
Their axis begins at the MD's full start, not at birth or its visible start.
Intersect with the MD's visible interval only after constructing all nine.
An AD has path `(m,a)`, its own row position and rotation ordinal; wrapping its
row does not increment its parent's MD cycle index.

Return all generated full period records, preserving stable paths. For an AD
entirely before birth, its visible interval is null and
`visibility=clipped_before_birth`; do not invent a zero-duration interval or
renumber the surviving children. This gives exactly 9 nodes at level one and
90 at level two, with a separately reported visible-node count. At level one,
children are absent with `children_status=not_requested`, not an unexplained
empty list. All nine MDs have positive visible duration.

Record `row_total_years`, `elapsed_row_years`, `natal_row_remaining_years`,
`birth_md_full_years`, `birth_md_remaining_years`, and `coverage_years`
separately. BPHS 34°50′ distinguishes row total 83, unrotated remainder 45.65
and nine-MD visible coverage 82.65. No extra MD is added to reach 83.

### 3.3 Result vessels and exact transport

Use immutable, deeply validated vessels for profile descriptors, source rules,
seed/provenance, exact intervals, periods, transitions, sequence, projection and
active line. Every result carries profile/version, source/rule IDs, applied
correction IDs, requested/generated levels and coverage. Every period carries
sign/ruler, full path, row identity/position, parent identity, integer weights,
denominator, full source span and nullable visible source span.

Retain exact ratios in Python. Serialize exact source-year values as normalized
`{numerator: "signed decimal integer", denominator: "positive decimal integer"}`
objects; decimal strings prevent JSON/JavaScript integer precision loss.
Require reduced ratios, positive denominators and canonical zero `0/1`.
Bound components to 400 digits for this binary64-input, depth-two product and
verify that bound from worst-case admitted input in tests. These ratio objects
are output evidence, not a new arbitrary-rational request interface. Any
convenience numeric year fields are explicitly approximate and cannot govern
partition validation or boundary ownership.

Construction and public consumers validate profile/row/seed consistency,
occurrence identity, parentage, ordering, full partition conservation, visible
intersection, unique paths, Deha/Jeeva and projection provenance. Validators
must resist forged/replaced frozen dataclasses as well as normal construction;
frozen fields alone are insufficient. Bound node counts before walking any
caller-supplied object. REST accepts bounded seeds, never uploaded period trees.

### 3.4 Projection and active lookup

The two admitted clocks have exact day ratios: 360 and `1461/4`. Use a
`birth_epoch` vessel identifying either an aware civil datetime or a strict
finite `jd_utc`. Normalize datetimes to UTC through the existing Julian-date
owner. Never interpret a supplied schedule JD as UT1 or TT.

For each unique exact source boundary `t`, project once from the common origin:
`float(Fraction.from_float(birth_jd_utc) + t * year_days)`.
Reuse that one projected value for every occurrence of the boundary. Do not
subdivide rounded JD parents or repeatedly add rounded durations. Reject
nonfinite endpoints, collapsed positive spans or ordering/containment failure.
Every retained full and visible MD/AD interval must be representable. A valid
source-only result may therefore succeed while projection raises a typed
precision error; never drop the short MD/AD to make the projection succeed.

Use projected numeric endpoints as the authority for public date lookup, with
`start <= query < end` and no epsilon. Return `before_birth`, `active`, or
`after_coverage` and the unique visible parent/child path when active. The exact
final endpoint is outside coverage. Clipped pre-birth ADs are not active even
when their full spans contain a query. Queries outside coverage are valid
results, not malformed requests or permission to generate another cycle.

Initial active lookup requires a projected schedule. It accepts a query
`birth_epoch`-shaped instant, never `now` or arbitrary source-ratio queries.
No fabricated dates are returned for source-only results. Date strings are
normalization/provenance fields; projected `jd_utc` endpoints remain the timing
contract, avoiding truncation to whole days or mandatory datetime rendering
outside Python's civil-year range. Fixed-day projection is an engineering
calendar convention, not a leap-second-aware physical elapsed-time model.

### 3.5 Gati evidence

Emit edges only between adjacent full MDs, and between adjacent full ADs of the
same parent. Each edge records source/destination paths and row positions,
level, exact source boundary, projected boundary when requested, ordered signs,
whether it crosses the row seam, and whether it occurs within visible coverage.
Keep pre-birth evidence marked non-visible. Do not manufacture an edge before
the first returned MD, after the ninth MD, or between unrelated AD parents.

The initial classification table is deliberately limited to the inspected
BPHS 46.96–100 examples: Virgo→Cancer and Leo→Gemini are Mandooki;
Pisces→Scorpio and Sagittarius→Aries are Simhavlokan. The two Cancer/Leo
directions return `classification_status=unresolved_source_conflict`,
`classification=null`, with KC-10. Evaluate the row-seam rule first: seams return
`classification_status=row_seam_not_classified`. Other edges return
`classification_status=not_classified_by_profile`, not a claim that no tradition
recognizes a gati there. Reverse pairs are not automatically admitted. No generic
modular-distance classifier or predictive interpretation is introduced.

## 4. Engine ownership and public API

Proposed new owners; names below are the implementation target, not existing APIs:

| Owner | Responsibility |
| --- | --- |
| `moira/kalachakra_policy.py` | Immutable profile, rows, weights, membership, rule/conflict metadata and discovery |
| `moira/_kalachakra_types.py` | Strict seed/epoch/projection vessels, exact result structures, bounded validation and typed errors |
| `moira/kalachakra.py` | Exact seed/balance, MD/AD construction, gati evidence, projection and lookup; public re-exports of its vessels |
| `moira/_kalachakra_astronomy.py` | Reader-bound Moon/ayanamsa composition and epoch/resource provenance; no server imports |

Admit these public operations consistently in the owner module,
`moira/__init__.py`, `moira/facade.py`, `moira/vedic.py` and the `Moira` instance
surface in `moira/_facade_vedic.py`:

- `kalachakra_profiles()` — source/conflict discovery, candidates and capabilities.
- `kalachakra_sequence(seed, *, profile_id, levels=2, birth_epoch=None,
  projection=None, reader=None)` — supplied sidereal or tropical seed through
  one admission owner; tropical input requires epoch and named ayanamsa.
- `kalachakra_for_datetime(birth_dt, *, profile_id, ayanamsa_system, levels=2,
  projection=None, reader=None)` — derive the Moon once, then use the same owner.
- `project_kalachakra_sequence(sequence, *, birth_epoch, year_basis)` — project a
  validated source sequence without changing its source arithmetic.
- `current_kalachakra_periods(schedule, query_epoch)` — validate and find the
  unique visible line in an existing projected schedule.

The facade binds its own reader only for resource-dependent paths. Supplied
sidereal calculations, discovery, source-result projection and lookup work
without accessing a kernel. Validate all caller choices before acquiring a
reader or running astronomy. Re-projection must respect any natal epoch already
bound to tropical/derived seed provenance; reject a different birth instant.
An epoch-free supplied sidereal result may be projected at a caller's origin,
which remains explicitly supplied provenance.

### Astronomy composition

Use the existing engine primitives demonstrated by
[dated Gochar](../../moira/gochara_dated.py): UTC→UT1, reader-bound
`_bind_ephemeris_time`, `planet_at("Moon", ..., jd_tt=bound.epoch_tt)`, and one
true-ayanamsa evaluation at that same TT. Declare apparent geocentric,
true-ecliptic-of-date longitude, with the established light-time, aberration,
gravitational-deflection and nutation settings. Do not compute other planets,
nodes, houses, location or a fabricated time.

Admit the existing named Moira ayanamsas, explicitly selected; no custom numeric
offset or `UserDefinedAyanamsa` in this package. For live-star systems, resolve
the named anchor at the bound TT and fail with a resource error if unavailable;
do not inherit the public helper's polynomial fallback while claiming a live
anchor. Record ayanamsa name, mode, offset and resource identity. Reuse existing
engine astronomical primitives, with one narrow composition owner shared by
Python and REST; do not rewrite the astronomical algorithms.

For supplied tropical longitude, derive only the epoch/ayanamsa context and
retain `input_origin=supplied_tropical`; never claim the Moon itself was computed.
For supplied sidereal longitude, use `input_origin=supplied_sidereal` with no
invented ayanamsa/kernel provenance. For derived Moon, require complete reader
and lunar time identity and use `input_origin=derived_moon`.

Preflight astronomical epochs against the existing dated-product JD domain
`[-10000000,10000000]` before time binding/resource work, then enforce actual
reader coverage. This range applies to tropical/derived astronomical composition;
source-only arithmetic has no epoch and pure projection instead uses its finite
and representability checks. Datetime normalization overflow is an input error.

The current server [sidereal context](../../moira_server/services/sidereal_context.py)
is a useful transport pattern, but its `jd_ut` field is UT1 and it independently
calls the public ayanamsa helper. This package must not import that server service
into the engine or blindly reuse its epoch/frame assumptions. Both new entry
paths call the new engine-owned composition; legacy routes keep their current
contracts. This refines the research packet's proposed reuse.

Similarly, [_dasha_intervals.py](../../moira/_dasha_intervals.py) supplies useful
full/visible interval doctrine and validators, but its float-based subdivision
routine cannot own the new exact source partitions. Reuse compatible validation
without changing legacy numerical behavior. Do not extend the two-system Literal,
eight-child vessels, lord-name selection or fixed-year-horizon loops in
`dasha_systems.py` / the alternate-dasha REST family.

## 5. REST parity contract

Create `moira_server/{models,services,serializers,routers}/kalachakra.py` and
register the router in the existing application, router exports and OpenAPI
metadata. Service code is admission/composition/serialization glue; it must
not contain a second sequence, source correction, projection or lookup formula.

| Route | Contract |
| --- | --- |
| `GET /v1/dasha/kalachakra/profiles` | Same admitted/candidate catalogue, source/conflict metadata, supported clocks, depth and resource bounds as Python; no kernel work |
| `POST /v1/dasha/kalachakra/sequence` | Direct supplied seed, optional projection; full source and nullable projected result |
| `POST /v1/dasha/kalachakra/chart/sequence` | Aware natal timestamp and named ayanamsa; derive Moon once, same result type and explicit derived provenance |
| `POST /v1/dasha/kalachakra/current` | Direct sequence request plus explicit query instant; projection required; rebuild the bounded result and use engine lookup |
| `POST /v1/dasha/kalachakra/chart/current` | Chart sequence request plus explicit query instant; same active/outside-coverage contract |

Direct request shape: required `profile_id`, tagged `seed`, `levels=2`, optional
`birth_epoch`, and optional `projection={year_basis}`. The `seed.basis` union is:

- `sidereal`: only `moon_sidereal_lon`.
- `tropical`: only `moon_tropical_lon` and required `ayanamsa_system`.

`birth_epoch` is a tagged `datetime` / `jd_utc` vessel. Tropical seeds require
it even without projection; any projection also requires it. Sidereal source-only
requests omit it. Chart requests instead require `birth_datetime` and
`ayanamsa_system`, which populate the same engine epoch/seed contracts; the
optional projection still requires its explicit clock. Current requests add
`query_epoch`; source-only current requests are rejected. Each request has one
natal instant and one ayanamsa selector, avoiding conflicting duplicate settings.

Use `_StrictModel`, strict finite numbers, strict bounded integers and aware
civil timestamps following `_vedic_inputs.py`. Exclude extra fields and union
branch leakage. Reject booleans as numbers, numeric strings, naive timestamps,
Unix timestamps masquerading as civil dates, null required selectors, nonfinite
numbers, angles outside `[0,360)`, unsupported profiles/clocks/depths and proposed
candidate IDs. Forbidden knobs include observer/house/node inputs, eligibility
bypass, ghatika fractions, row edits, external trees, extra cycles and free clock
lengths. Enforce bounds before ephemeris calls or allocation, including facade
entry points; retrieving a startup engine reference alone is not astronomy.

Responses expose the same exact ratios, paths, full/visible periods, seed basis,
correction IDs, unresolved evidence, coverage, eligibility status and clock
provenance as Python. Use explicit discriminated projection and visibility
states so null never means several different omissions. OpenAPI must state
exactly nine MDs, either no requested children or exactly nine full AD records,
the total 90-node ceiling, valid selectors and all error/status variants.

### Failure semantics

Add narrowly scoped error translation in `moira_server/errors.py`, preserving
the established error envelope and request IDs:

| Condition | Engine / HTTP outcome |
| --- | --- |
| Invalid type, selector, combination or object supplied to a public consumer | Typed input error / 422 `validation_error` |
| Valid source result whose requested JD projection overflows or collapses a positive interval | Typed projection error / 422 `kalachakra_projection_unrepresentable`, with bounded path/reason details |
| Astronomical epoch outside serving resource coverage | Typed coverage error / 422 `kalachakra_epoch_out_of_coverage` |
| Missing kernel, missing lunar clock identity or unavailable required live anchor | Typed resource error / 503 `kalachakra_resource_unavailable` |
| Finite query before birth or at/after coverage end | 200 with the explicit outside-coverage status and no active line |
| Generated result violates an invariant after validated input | `KalachakraInvariantError` / sanitized 500 `kalachakra_internal_invariant`, logged with request ID |

Input admission precedes the invariant wrapper. Do not turn a programming defect
into a caller 422, a missing resource into unsupported doctrine, or an error
into an empty successful schedule. Existing generic missing-engine translation
may retain its established `kernel_not_ready` code at that outer boundary;
document and test both layers explicitly. Never expose filesystem paths,
tracebacks or arbitrary exception representations in the new error details.

## 6. Independent validation fixtures

Freeze a new `tests/fixtures/kalachakra/` corpus before writing the calculator.
Its tables and rational expectations are entered from the inspected sources and
independent derivations, never generated from runtime constants or result JSON.
Include source ID/hash, edition, PDF and printed pages, rule, input units,
literal expectation, selected/corrected expectation, evidence class and rationale.
Keep full copyrighted books, OCR and private renders outside the repository.

| Fixture group | Required evidence |
| --- | --- |
| Catalogue | 27 group memberships, 108 pada associations, 16 rows / 144 entries, integer sign weights, row totals and all natal-row Deha/Jeeva endpoints |
| BPHS 46.93 | Exact sexagesimal 34°50′; S1/3, Cp occurrence 4, elapsed 0.35 and balance 3.65; all nine printed MDs; 83 / 45.65 / 82.65 distinction |
| BPHS chapter 64 | Aries/Aries `49/100`, Taurus/Taurus `256/100`, whole rotated rows and exact conservation; traditional y/m/d/ghatika presentation checked independently |
| JP paired example | 284°29′39″; A1/2, first Scorpio occurrence 2, balance `3.09525`; record the competing Libra `10.428` as a different school's expectation |
| Duplicate occurrence | Rao Example 95's shared seed/balance: 45°50′, A1/2, second Scorpio occurrence 7, balance 4.75. Derive this profile's ADs independently; Rao's Leo AD balance 0.34 is not a Santhanam oracle |
| Method discriminators | Rao's `Cp Sg Ar Ta Ge Cn Le Vi Li`, Taurus AD `256/97`, Example 96 subgroup continuation, Example 97 denominator 86, complete ten-entry Exercise 34, and JP's different MD/AD start |
| Time-fraction discriminators | Fixed-15 balance 2.25 versus actual-quarter `5403/3571`; both remain distinct from longitude-only input |
| Gati | Each admitted directed example, both contested Cancer/Leo directions, reverse pairs, seams, pre-birth edges, and terminal absence |

Source witnesses use exact sexagesimal rational inputs in the independent
oracle. The public numeric-input tests separately convert to binary64 and
bound the resulting error from the input conversion, source slope and final
rounding. Do not demand literal 3.65 from an inexact binary longitude or weaken
all tests with a generic `1e-6` tolerance. Discrete classification is exact for
the admitted value; no tolerance governs occurrence selection.

Required adversarial coverage:

- All 108 pada intervals and `nextafter` neighbours of every finite theoretical
  boundary; 0, the nearest value below 360, and rejected 360/negative values.
- Every within-row MD cutover, all 144 MD/AD row rotations, every repeated sign,
  both directions, row seams, and first/last birth occurrence. Test exactly
  representable boundaries and the two sides of unrepresentable rational ones.
- Exact full/visible conservation, 9/90 node counts, clipped-away ADs, immutable
  structures and forged objects with wrong profile, seed, ruler, path, parent,
  cycle, denominators, containment or overlapping partitions.
- Shared projected endpoint identity, both clocks, subnormal/near-cutover inputs,
  overflow, representability loss, no dropped periods, birth/internal/final
  lookup boundaries and adjacent floats. Projection failure must leave the
  source-only computation valid.
- JSON round trips preserving exact ratio strings, field bounds and provenance;
  strict Python and HTTP rejection matrix; OpenAPI and route discovery.
- Equivalent timezone offsets produce identical normalized astronomical and
  scheduled values; original timestamp spelling may differ in provenance.
- Direct sidereal result versus date-derived result using the returned longitude
  and same epoch/clock: exact schedule and lookup equality, with intentionally
  different origin receipts. Tropical versus date-derived composition uses the
  same bound TT and ayanamsa once; no double subtraction.
- Injected missing kernel/time identity/live anchor and coverage failures;
  injected internal invariant failure; every documented HTTP outcome exercised.
- Operation-count checks: zero astronomy for discovery/sidereal/projection-only
  paths, zero calls for rejected requests, one Moon derivation and one ayanamsa
  reduction for each chart request. No hidden seven-body chart, scans, unbounded
  recursion, repeated chart calculation for current lookup, or global mutable cache.

Use independent source authority, structural invariants, existing-regression
parity and real-kernel composition as separate evidence classes. A future JHora
comparison must pin version, exact variant, seed, ayanamsa, clock, timestamp and
exported MD/AD values; it is useful additional corroboration, not a substitute
for these fixtures or a blocker to this source-defined profile.

## 7. Seven implementation stages and gates

### Stage 1 — Freeze scope, policy and contract

Declare the protected public/export/server paths before editing. Recheck the
active checkout, baseline, venv and concurrent work. Freeze sections 1–5 as
the backend/API standard, including exact float interpretation, ratios,
projection timescale, partial visibility and bounded gati classification.
Reconcile the research packet's float-subdivision/server-context reuse wording
with the decisions above; add the plan link to the VED-014 register entry.

**Gate:** every computational choice and KC-01–14 has an explicit selected,
unresolved or non-admitted treatment. New public names, routes, schemas and
failure contracts are enumerated; there is no generic BPHS or candidate default.

### Stage 2 — Freeze independent source fixtures

Create the fixture corpus and a standard-library rational oracle without imports
from the new implementation. Audit all 144 entries, source hashes/coordinates,
checked AD cells and paired-school distinctions. Record fixture content hashes
before calculator work. Source corrections retain both the printed defect and
the selected reading rather than replacing history.

**Gate:** independently verify memberships, totals, all rotations and the
section-6 witnesses. Source-derived expected values remain independent of
runtime constants. Unverified OCR cells are excluded from authority assertions.

### Stage 3 — Catalogue, strict vessels and seed/balance

Implement the immutable policy catalogue, discovery and strict input/result
vessels, then the exact longitude/pada/occurrence calculator. Add source and
conflict lineage plus explicit eligibility/Deha/Jeeva scope. Establish numeric
input and exact-ratio transport bounds before adding period trees.

**Gate:** catalogue fixtures, all 108 padas, binary boundary neighbours, duplicate
occurrence witnesses and hostile input cases pass. Sidereal arithmetic remains
kernel-free, and candidates cannot be selected through any engine entry point.

### Stage 4 — MD/AD engine and transition evidence

Build exactly nine full MDs and optional full-parent AD partitions, then derive
visible intersections. Implement occurrence paths, cycle accounting, coverage,
gati evidence and whole-result validators. Public consumers revalidate bounded
objects. Keep existing alternate-dasha logic unchanged.

**Gate:** independent exact partitions and worked source sequences pass; all
9/90 node and conservation assertions hold. No sign-key lookup, birth-restarted
AD, accidental cycle advance, fabricated seam label or tenth MD survives the
adversarial cases.

### Stage 5 — Projection, astronomy composition and public engine parity

Add both explicit clocks, common-origin projection, representability checks and
active lookup. Implement the reader-bound Moon adapter and direct tropical
composition with complete epoch/frame/resource receipts. Wire module/root/vedic
exports and `Moira` wrappers to the same owners. Preserve legacy defaults.

**Gate:** clock, endpoint, failure and forged-result tests pass through every
public path; source-only success remains independent of projection success.
Real-kernel date/direct parity and equivalent timezone tests pass with downloads
disabled. All unsupported requests fail before acquiring astronomical resources.

### Stage 6 — REST models, services, serializers and discovery

Implement the five routes in section 5, strict discriminated requests, exact
ratio serialization, bounded response schemas and typed error mapping. Add
router/OpenAPI registration and executable request examples. Merge only scoped
registration hunks in files also touched by concurrent natal-discovery work.

**Gate:** every engine capability and limitation has matching REST behavior.
Fixture-driven engine/HTTP parity, all status/error variants, malformed payloads,
resource-call counts, serialization, OpenAPI and `/v1/meta/routes` discovery pass.
There is no REST-only doctrine or misleading derived provenance.

### Stage 7 — Integrated validation, documentation and handoff

Run the targeted feature suite and affected legacy/public/server regressions.
Add the kernel-free Kalachakra tests to the release-hardening workflow and its
minimum-Python import/schema smoke. Perform correctness and lineage reviews;
fix findings before recording completion. Do not add a native layer for this
bounded calculation or relax protected baselines/tolerances to obtain green tests.

Publish canonical backend/API documentation, examples and a validation receipt;
refresh affected generated inventories/reference/wiki with their generators.
The generated Hellenistic API inventory also observes public-surface changes:
check it even though this feature is Vedic, preventing the previously observed
stale-inventory release failure. Preserve generated files' source ownership.

**Gate:** the selected profile is complete across source arithmetic, projection,
lookup, facade and REST with all checks and limitations recorded. Mark VED-014
complete for this named scope and retain candidates, deeper levels, full gati
taxonomy and eligibility evaluation as explicit remaining capabilities. Commit,
push, tagging and website deployment still require their separate user request.

## 8. Verification commands and completion receipt

Use `C:\dev\moira\.venv\Scripts\python.exe`, `MOIRA_NO_DOWNLOAD=1` and
`MOIRA_STRICT_KNOWN_ISSUES=1`. The new fixture/tests below are proposed files:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe tests/unit/test_docstring_governance.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_kalachakra_sources.py tests/unit/test_kalachakra.py tests/unit/test_kalachakra_admission.py tests/unit/test_kalachakra_projection.py tests/unit/test_kalachakra_astronomy.py tests/unit/test_kalachakra_public_api.py tests/server/test_server_kalachakra.py tests/server/test_server_kalachakra_openapi.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_dasha.py tests/unit/test_dasha_systems.py tests/unit/test_dasha_full_intervals.py tests/unit/test_chara_profiles.py tests/server/test_server_alternate_dashas_routes.py tests/server/test_server_jaimini_profiles.py tests/server/test_vedic_direct_input_hardening.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_public_api_drift.py tests/unit/test_public_api_contract.py tests/unit/test_api_surface_adversarial_audit.py tests/server/test_server_route_discoverability.py tests/server/test_server_error_mapping.py tests/server/test_error_mapping.py -q
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe scripts/generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
```

Regenerate stale derived artifacts through those scripts before their final
`--check` runs. Also run the release workflow's current-source website-docs
publication-candidate check; this produces a validation artifact, not a website
deployment. Verify Python 3.10 compatibility through the existing CI lane and
record local unavailability honestly. Never represent unrun CI as passed.

Separate kernel-free selection from explicitly collected real-kernel cases.
Confirm the intended tests were collected; no unreported ephemeris skips count
as a passed integration gate. Record discovered reader identity/coverage,
download-disabled configuration, exact command/results, test counts, fixture
hashes, source cases, clock and boundary cases, outstanding limitations and
whether the full repository suite ran. Expand regression selection only when
changed shared paths or failures justify it.

The earlier 468 research assertions and 170 existing-engine baseline tests are
inherited research evidence, not coverage of the new implementation. This
planning turn runs no runtime tests and changes no protected fixtures. Its
verification is document structure, source/contract traceability, path/link
existence and whitespace checks.

**Planning receipt:** a read-only project-Python document check confirmed seven
ordered stage headings, all fourteen KC decision rows, resolving relative links,
existing regression/script command targets and no trailing whitespace.
`git diff --check` passed for the tracked working tree; the new untracked plan
was checked directly by the document check. Concurrent changes were inspected
and left untouched. These results validate the plan artifact, not the proposed
engine or REST implementation.

## 9. Workspace scope

The planning turn authored only this document. The subsequent authorized
implementation is recorded in the linked validation receipt; the research
packet and register were reconciled with the selected delivery. Concurrent natal-discovery/light-box work,
small-body metadata/manifests and their fixtures are outside this package.
The eventual implementation must inventory these again rather than assume
the present dirty-file list is stable. Do not stage another task's changes or
replace shared registration files wholesale.

Implemented canonical additions include
`wiki/02_standards/KALACHAKRA_DASHA_STANDARD.md`,
`wiki/02_services/KALACHAKRA_DASHA_API.md` and a dated validation receipt under
`wiki/03_validation/`. Update this plan and the remaining-work register only
with demonstrated execution results. Generated `moira.wiki/` is refreshed by
`scripts/sync_git_wiki.py`, never hand-edited. If later publication includes
that nested repository, publish the wiki first and then the parent gitlink/code
under the user's publication authorization.
