# VED-017 Gochar windows implementation plan

**Date:** 11 October 2026. **Status:** all seven stages complete locally for
the bounded modern whole-sign profile. The subsequent authorized source-publication
checkpoint is linked in section 9; release and deployment remain separate.
**Baseline:** Moira 6.9.9, engine `524a8d3caf3470634080fc930479625e0f7f29c9`.
**Authority:** [source research and diagnostic receipts](VEDIC_GOCHAR_WINDOWS_SOURCE_RESEARCH_2026-10-11.md),
[dated Gochar standard](../02_standards/GOCHARA_DATE_DERIVED_STANDARD.md),
[snapshot standard](../02_standards/GOCHARA_BACKEND_STANDARD.md),
and the existing `tests/fixtures/gochara_phaladeepika_26.json`.

This is one delivery package with seven implementation stages. Completion
requires the engine, facade, REST, validation evidence and documentation
together. Stages are implementation checkpoints, not separate feature releases.

The original plan and planning receipt below remain a dated record. The
[implemented standard](../02_standards/GOCHARA_WINDOWS_STANDARD.md),
[final validation](../03_validation/GOCHARA_WINDOWS_VALIDATION_2026-10-11.md)
and section 8 now govern its completion status and measured limits.

## 1. Product and admission decisions

Return a bounded timeline of the existing Gochar observations and directed
Vedha relations. Evaluate all seven classical participants using the current
Phaladeepika/Sastri profile, natal-Moon reference, exemptions and historical
indications. Retain optional same-birth raw Raman-encoded BAV without a new
threshold, ranking or outcome score. Both ordinary Vedha and baseline-only
policies remain available with their existing meanings.

All twelve named ayanamsas are required for completion: seven polynomial
systems and the five existing live-star systems. Resolve the selected ayanamsa
at every required TT epoch. Missing live anchors fail explicitly.

Window constancy means constancy of **discrete doctrine state under the named
computational model**. Planetary degrees, clocks and ayanamsa values remain
time-dependent and belong in individually dated samples. The result does not
assert exact physical ingress times or predict the probability of life events.

The research established source differences in thirds/halves activation,
alternative tables, counter-Vedha and ingress-Moon Murthi. Keep them visible in
the existing doctrine catalogue under VED-018/019. This package supplies the
reusable event machinery those rules could later consume; it does not silently
admit them, nodes, other reference points, aspect/dasha modifiers or remedies.

### Certified time domain

Admit an initial modern window profile with nominal search domain
**1900-01-01 through, but excluding, 2101-01-01**. This follows the existing
clock and frame enclosures. The effective domain is their intersection with
converted TT support, required retarded ephemeris epochs, serving-record
coverage and anchor validity. Validate every dependency; a nominally valid
UT1 endpoint alone does not prove certification is available.

`MarriageClockEnclosures.jet()` uses a strict upper bound, and
`FrameEnclosures.nutation()` independently bounds TT. Derive and expose safe
effective endpoints rather than rounding them to an unsupported calendar date.
The existing dated snapshot domain stays intact. A natal instant may precede
1900 when the existing point compositor and optional natal BAV support it;
the interval certificate applies to the searched transit interval.

Require finite bounded requests. The workload design target is a **366-day
maximum request**, allowing ordinary annual use and chunked longer histories.
This is a proposed product cap, not a throughput claim. Stage 6 must demonstrate
that the published duration/work caps are usable and safe before API admission;
any smaller delivered range must be recorded as an explicit plan change.

## 2. Public engine and REST contract

Use the existing `GocharaDatePolicy` for astronomy/doctrine and a separate
`GocharaWindowSearchPolicy` for the search. Do not duplicate ayanamsa or BAV
choices in two policies.

```python
gochara_windows(
    natal_jd_ut1, start_jd_ut1, end_jd_ut1, *,
    birth_location=None,
    policy=None,                 # GocharaDatePolicy
    search_policy=None,          # GocharaWindowSearchPolicy
    subjects=None,               # presentation selection only
    reader=None,
) -> GocharaWindowResult

gochara_windows_for_datetimes(
    natal_dt, start_dt, end_dt, *,
    birth_location=None, policy=None, search_policy=None,
    subjects=None, reader=None,
) -> GocharaWindowResult

gochara_window_capabilities() -> GocharaWindowCapabilities
```

Expose both calculation methods through `Moira`, bound to that instance's
reader. Standalone calls follow the existing explicit reader-context rules.
Capabilities are resource-free and disclose that installed availability has
not been probed. They list profiles, systems, nominal certification domain,
endpoint semantics, finite limits and uncertainty behaviour.

| REST surface | Contract |
|---|---|
| `POST /v1/gochara/windows/from-epochs` | Natal/start/end UT1 JDs, date policy, search policy, optional birth location and presentation subjects. |
| `POST /v1/gochara/windows/from-datetimes` | The same operation from three timezone-aware civil instants; each converted once to UT1. |
| `GET /v1/gochara/windows/capabilities` | The engine capability vessel through a typed response, without acquiring a kernel. |

Both POST routes return the same canonical result through **one serializer**.
Engine and REST accept the same scientific choices and enforce the same hard
limits. HTTP code does not independently classify a transit, rebuild a Vedha
table, round an event into a different sign or hide unresolved evidence.

Reject nonfinite or boolean numeric values, zero/reversed duration, unknown
fields, invalid subjects, duplicate subjects, naive/bare-date/numeric civil
timestamps, unsupported search ranges and contradictory BAV settings before
expensive work. Require birth location exactly when natal BAV is computed.
Accept offset-equivalent instants and supported retrospective windows.
Selecting one subject never removes any of the seven potential blockers.

### Search policy

Expose `boundary_tolerance_seconds`, `require_resolved` and immutable
`GocharaWindowSearchLimits`. The proposed default boundary tolerance is one
second; it is a numerical isolation target, not a physical timing guarantee.
Reject tolerances below the supported representable/roundoff floor rather
than silently widening the caller's request. Publish requested and achieved
widths separately, including wider merged event bands.

Limits cover duration, evaluations, reader calls, subdivisions, root
iterations, candidate/event count, cells, samples, evidence records and output
bytes. Internal scan steps may seed subdivision but are not public accuracy
or completeness controls. No unbounded mode is admitted. Operational caps are
calibrated in stage 6; callers may lower limits within the admitted ranges.

### Result vessels and invariants

| Vessel | Required contents and checks |
|---|---|
| `GocharaNatalContext` | One natal astronomical receipt, Moon longitude/sign, optional birth Lagna and raw BAV tables, source/policy and resource identity. Construct once per request. |
| `GocharaWindowState` | All seven signs, derived relative positions, source-attributed baseline/indication keys, Vedha conditions and every directed witness/exemption, raw BAV values and omitted-layer markers. No continuously varying degrees in its equality key. |
| `GocharaWindowSample` | A full dated `GocharaEpoch` and references to natal context/state. An engine resolver reconstructs the existing snapshot result without repeating natal tables throughout the payload. |
| `GocharaIngressEvent` | Body, boundary ray, classification, time enclosure, before/after evidence, direction when proved, existence/count/order evidence and dependencies. Include confirmed crossings, contacts, possible contacts and model-seam changes as distinct kinds. |
| `GocharaWindowRegion` | Discriminated `certain`, `boundary_band` or `unresolved_band`; endpoints/inclusions, state/sample references when meaningful, event references, and uncertainty reasons/dependencies. |
| `GocharaWindowCoverage` | Participant completeness, domain accounting, exclusion certification, event resolution and doctrine coverage as separate fields. Counts, durations and maximum widths support those claims. |
| `GocharaWindowResult` | Policies, requested interval, optional civil-input receipt, one natal context, interned states/samples, event records, ordered regions, optional subject views, serving identities and work/coverage receipts. |

Frozen constructors validate nested vessel types, canonical ordering, finite
values, unique IDs, reference integrity, chronology, policy consistency and
partition coverage. Reconstruct discrete testimony with the existing evaluator
at each stored sample. Reject mutated or contradictory constructed results.
Structural validity is not authentication of kernel computation: callers
cannot submit fabricated result vessels through the window requests as trusted
certification evidence.

## 3. Exact interval and event semantics

Use the **closed requested interval `[start,end]`**, with `start < end`.
Every requested instant must belong to exactly one partition region.
Interior boundary/unresolved bands are closed; adjacent certain regions exclude
those band endpoints. When no band occupies a request edge, the adjacent certain
region includes that edge. Clip bands at request bounds and record the clip.
Merge touching/overlapping uncertainty bands while retaining individual events.

The point evaluator remains authoritative: exact 30 degrees belongs to Taurus
in both directions. At a retrograde crossing, that is the pre-crossing sign.
Do not impose a universal right-continuous state on temporal windows. A maximum
touching 30 degrees can have Taurus only at the singleton contact and Aries on
both sides; a minimum there can retain Taurus throughout. Emit a singleton
only when exact contact is established, never from a rounded timestamp.

Candidate retention, event existence, uniqueness/count, direction, order and
boundary-time width are distinct facts. An endpoint sign change can contain
three crossings; it does not prove one. A narrow possible-root band can contain
no actual crossing. Confirm only what interval evidence establishes, and keep
remaining ambiguity as a typed unresolved region.

Use all seven angular streams plus clock/source/record seams as partition
inputs. Establish continuity before applying continuous-root arguments.
If a serving-model seam changes occupancy without a continuous zero, record
a model-seam change or unresolved band, rather than labelling it an ingress.
Reject or isolate ambiguous serving-record priority and coverage joins.

A station within a sign does not itself change the admitted Gochar doctrine.
Motion bounds and extrema support discovery of repeat crossings; continuous
retrograde status is not promised as a constant field of every cell. Crossing
direction remains event evidence. Request cuts are not invented sign entries,
and clipped visits make no claim about their true start before the query.

`require_resolved=False` permits an honest bounded result with explicit
unresolved regions. It never permits unreported gaps. `require_resolved=True`
requires classified events with established count/order and accepted widths,
and no unresolved regions. Ordinary nonzero root-time bands remain present;
strict mode does not mean infinitely precise event times.

Subject views are projections of the canonical seven-body partition. Coalesce
only adjacent certain regions under a documented subject-state key that keeps
witness identities and exemptions. Never bridge an unresolved band. Retain
atomic region references and omitted/intervening event references. At a split
query's shared endpoint, stitching must de-duplicate ownership and event evidence;
equivalence is semantic within declared enclosures, not identical solver bit
patterns from differently seeded searches.

## 4. Implementation stages

### Stage 1 — Freeze contracts and acceptance cases

Create `moira/gochara_windows.py` for public frozen types, policies, errors and
the two entry-point signatures. Define the endpoint and coverage semantics
above, canonical state projection and capability schema. Add synthetic test
fixtures with independently specified expected signs and witnesses, without
rewriting the existing classical fixture or changing snapshot defaults.

Define a private reusable natal-context builder shared with `gochara_dated.py`
so repeated windows do not repeatedly derive natal astronomy, Lagna or BAV.
Keep `GocharaDateResult` and all existing snapshot payloads compatible.

**Exit:** constructor/admission tests, explicit schema examples and every
research finding mapped to an executable acceptance case. Contracts must not
advertise the feature as implemented before its search exists.

### Stage 2 — Extract reusable interval and resource support

Introduce the private package `moira/_event_search/` with narrowly owned modules
for intervals/roundoff/differentials, clocks/frames, serving astronomy,
isolation and budgets. Move common arithmetic and ownership logic, keeping
compatibility adapters in the current marriage modules. Avoid duplicated
formula implementations that can drift independently.

Reuse the current `isolate()` exclusion/possible-root contract. The existing
marriage `EventCertificates.angular()` endpoint-sign wrapper is not a Gochar
multiplicity or completeness proof. Keep horizon calculations, election history,
marriage policy and purpose doctrine in their current owners.

Extract a neutral budget exception contract and metered borrowed-reader adapter.
Preserve existing marriage/election error classes, messages, defaults, counters
and HTTP semantics. Gochar must not inherit a marriage-specific public error
just to satisfy `WorkMeter`'s current subclass check. Borrowed readers cannot
be closed by a request. Restore reader context on success and every failure.

**Exit:** existing enclosure/reuse/election tests remain compatible; old and
new adapters agree on values, retained regions, source identities and metered
work under the same inputs. Extraction introduces no new base dependency or
unrequested native implementation.

### Stage 3 — Implement all twelve sidereal astronomy adapters

Build `moira/_gochara_window_astronomy.py` against the same serving-reader
UT1→TT→TDB path and apparent planetary corrections as `_epoch()`.
Every interval operation must enclose its corresponding point operation,
including roundoff, light-time branches and selected SPK records.

Parameterize polynomial frames with the selected reference value and any drift
term. For live anchors, freeze the resolved sovereign record identity; enclose
the existing proper-motion/distance/radial-velocity vector propagation,
normalization and true-ecliptic transformation. Add no stellar correction that
the current point owner does not perform. Match the direct anchor lookup in
dated Gochar; never use the generic helper's missing-anchor fallback.

Freeze request-owned clock tables/EOP and catalog inputs or fail explicitly if
their identities change. Preflight the effective certification domain and
required retarded epochs. Split on clock branches, frame limits and serving
record/priority seams, with continuity and one-sided evidence retained.

**Exit:** all twelve systems pass point-containment, rate/enclosure and domain
edge tests. Missing/invalid anchors and time identity fail as typed resource
errors. Existing Lahiri marriage calculations retain their admitted results.

### Stage 4 — Solve events and compose the timeline

Implement `moira/_gochara_window_search.py` and
`moira/_gochara_window_partition.py`. Search all twelve sign rays for all seven
bodies using interval exclusion, subdivision and valid derivative contraction.
Retain evidence for excluded intervals and every possible boundary region.
Prove crossing count/direction where possible; preserve touches, higher-order
roots, overlapping events and unresolved order conservatively.

Build a single ordered partition from the seven streams and model seams.
Certify a region's seven signs before assigning its constant state. Evaluate
the existing Gochar owner at a representative interior point and extract its
discrete state; the proof of constancy comes from exclusion/sign containment,
not from agreement of a few sampled points.

Intern fixed natal context, repeated states and samples with bounded,
request-owned exact-input caches. Compute raw BAV once and select values by
each subject's absolute transit sign. Build projected subject views only after
the full state graph is available. An unsupported numerical subdomain remains
explicit; budget exhaustion raises and discards the incomplete result.

**Exit:** synthetic and real direct/retrograde/re-entry cases, blocker-only
changes, multiple/exempt witnesses, wraparound, exact endpoints, both tangent
types, simultaneous candidates and model seams preserve full domain accounting.
Certain-region snapshots agree with the existing dated evaluator.

### Stage 5 — Complete facade and REST parity

Wire the entry points into `moira/_facade_vedic.py`, and curate exports in
`moira/__init__.py`, `moira/facade.py` and `moira/vedic.py`.
Add `moira_server/models/gochara_windows.py`; extend existing Gochar services,
serializer and router, plus `moira_server/models/__init__.py` and error handling.

Use a Gochar-window-specific error response schema whose `details` match real
payloads. The common `ErrorEnvelope` currently declares `dict[str,str]`, while
budget handlers emit numeric counters. Do not repeat that mismatch or broaden
unrelated endpoint schemas in this package.

| Condition | HTTP / engine contract |
|---|---|
| Malformed input or contradictory policy | 422 `validation_error`; matching engine admission failure before expensive work. |
| Outside serving ephemeris coverage | Existing 422 `gochara_date_outside_coverage`. |
| Outside the window certificate's effective domain | 422 `gochara_window_outside_certified_domain`, with failed dependency and bounds. |
| Missing kernel, time identity or required live anchor | Existing 503 `gochara_resource_unavailable`. |
| Deterministic duration/work/output limit exceeded | 422 `gochara_window_budget_exceeded`; typed `limit_kind`, `limit`, `count`, `stage`. No partial successful result. |
| Unresolved result when strict resolution was requested | 422 `gochara_window_unresolved`, with typed reason/count/width summary. |
| Retained numerical ambiguity in ordinary mode | 200 canonical result with explicit unresolved regions and coverage status. |
| Unexpected implementation failure | Existing sanitized server-error contract; never disguised as an empty successful search. |

Extend Pydantic preflight-error unwrapping: the current handler recognizes only
marriage budget exceptions. Ensure Gochar cap failures retain their named
error before reader acquisition. Validate all error examples against the
declared OpenAPI models. Preserve null, omitted and not-evaluated meanings.

On successful admission, update `forecast.dated_events` to describe this
specific window product. Snapshot selected-policy receipts must not claim to
have performed a search. Capabilities, selected options and route documentation
must agree about all twelve systems, domain and limits.

**Exit:** both POST routes equal the engine serializer result for every
admitted policy combination, including raw BAV, baseline-only and ordinary
Vedha, subject projection, unresolved bands and strict failures. Capability
discovery, curated exports, response/error schemas and Python 3.10 server
compatibility are checked alongside the Python 3.14 development runtime.

### Stage 6 — Complete adversarial, external and performance validation

Use the matrix in section 5. Retain independent expected values for analytic
signals and source tables. Capture reproducible real-kernel and external
receipts with input/resource identity, tested range, frame, units, tolerance
and residuals. A skipped required oracle is an incomplete gate, not a pass.

Measure cold and warm 1-day, 30-day and 366-day requests for Lahiri and at least
one live anchor, with all bodies, both BAV modes and an adverse dense-boundary
case. Exercise the remaining systems with bounded integration cases. Record
wall time, reader/evaluation work, subdivisions, root iterations, cache size,
memory, cells and serialized bytes. Retain exact scientific parity when caches
are disabled or evicted. Optimize repeated calculations rather than dropping
participants, corrections or small events.

Freeze work/cache/output maxima from these measurements and test just-below,
at and just-above every admitted cap. Bound output allocation incrementally;
do not build an unbounded result before checking its size. Use one
stdlib-compatible canonical wire projection for byte accounting, and verify
the REST encoding has the same representation/size. Avoid a self-referential
byte counter; define precisely which completed payload bytes are counted.
Pydantic remains optional and cannot enter base engine imports.

Synchronous REST execution must be measured under the server's existing
worker/concurrency model; demonstrate isolated reader contexts and meters for
simultaneous requests. A client disconnect/timeout must not corrupt a shared
reader or cache. Publish actual latency and supported range honestly. Do not
introduce queued jobs or promise interactive annual results without evidence.

**Exit:** mandatory semantic, astronomical, external, transport and budget
gates pass; any failures are repaired without widening tolerances to fit the
candidate or silently shrinking its contract. Perform a focused adversarial
review of the completed diff and repair its in-scope findings before closure.

### Stage 7 — Document admission and reconcile generated surfaces

Add `wiki/02_standards/GOCHARA_WINDOWS_STANDARD.md` and a dated validation
receipt under `wiki/03_validation/`. Update the dated/REST standards, Gochar
constitutional ledger and VED-017 register with the exact admitted scope,
domain, systems, error semantics, measured limits and verification results.
Keep the research document as a dated evidence checkpoint.

Refresh generated REST reference and inventories using their owning scripts.
Reconcile the generated `moira.wiki` only through `scripts/sync_git_wiki.py`.
Run the release-hardening checks relevant to changed API/docs, including the
Hellenistic inventory that previously failed after unrelated API additions.
Add new canonical documents to the intended publication manifest before wiki
generation; its discovery uses tracked files.

**Exit:** mark VED-017 `LOCAL_COMPLETE` only for the bounded modern whole-sign
window profile after all mandatory gates, while preserving VED-018/019 as
separate work. Source commit/push, version release, deployment and website
adoption remain separate publication actions. If source publication is later
requested, publish the generated wiki before the parent engine gitlink.

## 5. Required validation matrix

| Finding / risk | Mandatory acceptance evidence |
|---|---|
| Current-state classical Vedha | All 36 directed pairs and four exemptions, all twelve natal-sign rotations; subject stationary while each possible blocker enters/leaves; multiple blockers and exempt-plus-real witnesses. |
| Conflicting activation and source tables | Existing source fixture unchanged; catalogue distinguishes selected, disputed and unadmitted layers; windows do not enable halves/thirds, reverse Vedha or Murthi accidentally. |
| Sampled search misses | Analytic two/three crossings inside one seed step, root on a sample, short visit and short gap; changing seed step cannot justify loss of a retained candidate. |
| Exact spatial/temporal boundaries | Direct and retrograde 30-degree boundaries, 0/360 wrapping, request-edge roots, maximum singleton contact and minimum contact; test representable neighbours and clipped bands. |
| Root proof versus possible root | False candidates, stationary/higher-order roots, simultaneous bodies, uncertain event order and wide merged bands; strict and ordinary modes differ only in admission, not hidden evidence. |
| Computational seams | Clock/EOP branch boundaries, SPK record boundaries, selected-segment priority changes and discontinuities; continuous-root arguments only on proved continuous pieces. |
| Twelve ayanamsas | Seven polynomial offsets/drifts plus Spica, Aldebaran, Revati, Asellus Australis and Shaula; each point/interval path agrees and missing anchors fail without fallback. |
| Coverage and resource lifetime | UT1/TT domain intersection and retarded-epoch coverage; invalid requests before access; borrowed reader never closed; context restored after every failure; mid-request source identity changes rejected. |
| Natal reuse and BAV | Natal work once, existing BAV table provenance, birth-Lagna failures preserved, absolute-sign BAV lookup, no threshold/strength override. |
| State/transport integrity | Forged references, changed policy/natal signs, mutated nested records, duplicate/missing participants, false constancy, lost witness identities and incorrect null handling are rejected. |
| Complete partition and projections | Exact domain accounting; interior point agreement; coalescing retains evidence; adjacent-query stitching and overlap comparison preserve semantics within boundary enclosures. |
| Failure and budget contracts | All limit kinds, preflight Pydantic wrapping, typed 422/503 responses, ordinary unresolved 200 versus strict 422, no truncated successful output, no silent output-byte overflow. |
| Shared-owner regressions | Marriage enclosure, windows, reuse, purpose-election and repair suites; native/Python parity where a shared operation or binding actually changes. |
| Runtime and publication | Base install retains no Pydantic requirement; current supported Python/API imports, all generated API/wiki checks, curated exports and examples. |

### External astronomical evidence

Compare quantities in layers before comparing ingress timestamps:

1. **Planetary substrate:** use existing Horizons infrastructure with exact
   Moira body identities (including planetary-system barycentres where used),
   geocentric origin, matched time scales, corrections and reference frames.
   Retain raw responses and query metadata. `HorizonsOracle.fetch_ecliptic()`
   describes J2000 ecliptic coordinates and cannot be compared directly with
   true-ecliptic-of-date Gochar longitudes.
2. **Frames and anchors:** independently reconstruct the admitted transform
   and five catalog-anchor propagations using the existing ERFA/SOFA research
   infrastructure and source records. Check the seven polynomial systems
   against their reference/drift data and independently computed transforms.
   Existing Swiss fixtures are secondary model comparisons, not a substitute
   for matched-frame authority or a subsecond timing oracle.
3. **Events:** require at least one retained real crossing for each of the
   seven bodies under each of the twelve systems (84 body/system combinations).
   Include direct–retrograde–direct sequences for Mercury, Venus, Mars,
   Jupiter and Saturn, plus Moon/Sun wraparound and coincident/near-station
   cases. A single request may supply several corpus entries.
4. **Tolerance:** declare angular/frame/catalog/clock uncertainty before
   evaluating candidate residuals. Translate angular uncertainty into a
   timing bound only with a justified nonzero speed bound. Near a station,
   compare angular residuals and uncertainty-region overlap; a one-second
   solver band does not authorize a one-second external timing claim.

Internal point reconstruction, analytic completeness tests, source collation
and external astronomy answer different questions. Keep all four evidence
classes in the final receipt and account explicitly for every required corpus
cell; no unexplained missing combinations or skipped failures.

## 6. File ownership and verification commands

Primary new owners: `moira/gochara_windows.py`, the private
`moira/_event_search/` package, `_gochara_window_astronomy.py`,
`_gochara_window_search.py`, `_gochara_window_partition.py`, and
`moira_server/models/gochara_windows.py`. Existing integration owners are
`gochara_dated.py`, `gochara_policy.py`, the Gochar server adapter files,
`moira_server/errors.py`, curated exports and the marriage compatibility wrappers.

Planned test owners are `tests/unit/test_gochara_windows.py`,
`test_gochara_window_astronomy.py`, `test_gochara_window_partition.py`,
`tests/server/test_server_gochara_windows.py`, and
`tests/integration/test_gochara_windows_ephemeris.py`, with separately identified
oracle corpus and benchmark tooling. Freeze the external corpus specification
before generating candidates. Keep copyright-sensitive book scans outside
the runtime package; retain source locators/hashes and bounded source fixtures.

These changes intersect protected astronomy, clocks, catalogue access,
public exports, REST and validation zones. Before each implementation slice,
declare its exact owners, authority, fixtures and smallest relevant checks.
Use `.venv\Scripts\python.exe`; enable `MOIRA_NO_DOWNLOAD=1` and
`MOIRA_STRICT_KNOWN_ISSUES=1`. Discover kernel resources through their owner.

Run the existing 349-case Gochar unit/server slice first, then new focused
files as they land, then the shared marriage/election slices affected by the
extraction. Include `tests/integration/test_gochara_dated_ephemeris.py` when
natal composition is shared. Run only the relevant external checks with their
required explicit harness/network policy; required acceptance cases cannot be
counted as passed when skipped.

At final admission, the current documentation checks are:

```powershell
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe scripts/generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
git diff --check
```

No full-suite run substitutes for missing targeted semantic or external
evidence. Broaden testing when shared-owner changes or failures justify it.

## 7. Completion checklist and planning receipt

VED-017 is complete only when all twelve systems work inside the declared
domain; all seven subject/blocker streams are accounted for; certain regions
carry justified constant state; boundary uncertainty and source seams are
visible; epoch/civil engine and REST results agree; limits are measured and
enforced; the external matrix is accounted for; and shared-owner regressions,
focused adversarial review and generated documentation checks pass.

This planning pass inspected the current engine, server, interval/clock/frame
owners, error envelopes, oracle adapters and release-hardening workflow.
It adds **only this plan file**. The preceding research document and register
link are preserved. The earlier 349 passing tests and research probes are
baseline evidence from the research pass, not tests of an implemented window
feature. No implementation, source publication or deployment occurred during
planning.

## 8. Seven-stage execution receipt — 11 October 2026

| Stage | Completed outcome |
| --- | --- |
| 1 — Contracts | Frozen policies/results/errors, analytic/source cases, shared natal context and a predeclared external corpus specification. Existing snapshot defaults retained. |
| 2 — Shared support | Private `_event_search` owners, compatibility imports, independent budgets and metered reader loans. MC, VV, KP and carryover real regressions completed. |
| 3 — Astronomy | All twelve systems, including five live anchors; serving-model containment, UT1/TT domain intersection, resource identities and 48 ERFA comparisons. |
| 4 — Timeline | All seven subject/blocker streams, direct/retrograde/re-entry evidence, complete partitions, exact endpoint ownership and conservative unresolved regions. Natal BAV derives once. |
| 5 — Public and REST | Twenty curated exports, facade methods, two strict calculation routes and resource-free capabilities. Canonical engine/HTTP bytes, typed OpenAPI errors and measured caps agree. |
| 6 — Validation | 1,443 distinct accepted tests across the documented slices; 101 primary Horizons comparisons; 26 measured benchmark requests. Focused review findings repaired without widening scientific tolerances. |
| 7 — Documentation | Standard, validation receipt, doctrine ledger and VED-017 register reconciled; generated API/wiki surfaces and release-facing consistency checks pass. |

The delivered maximum is 366 days, as planned. Annual requests in the
contended-host benchmark take approximately 212–278 seconds; this is an honest
synchronous bounded product, not an interactive latency promise. Error details,
strict unresolved rejection, resource/cache bounds and numerical assumptions
are exposed through both engine and REST.

Implementation organization consolidated planned unit astronomy/partition
checks into `tests/unit/test_gochara_windows.py`; real astronomy, ERFA and
retained-reference integrity have their own integration files. The new private
package is explicitly included in setuptools discovery. No base dependency,
native coefficient, source table, default snapshot policy or external threshold
changed. Broader VED-018/019 source admissions remain separate.

The validation receipt names the exact commands and their execution evidence,
including the deliberately interrupted combined historical run and separately
completed cases. Python 3.10 syntax was checked; runtime/ABI execution here is
Python 3.14.3 only. No source commit/push, release or deployment occurred.

## 9. Authorized source-publication package — 12 October 2026

The user subsequently authorized commit and push. The
[publication checkpoint](../03_validation/GOCHARA_WINDOWS_VALIDATION_2026-10-11.md#authorized-source-publication-checkpoint--12-october-2026)
records the upstream fast-forward, unchanged computational/evidence bytes and
803 fresh passing tests, including all 29 required serving-resource cases.
Upstream dynamic API guards replace the redundant local fixed-name additions.
Publication includes the generated wiki first and then engine `main` with its
gitlink. The seven-stage feature scope and version 6.9.9 remain unchanged;
release, deployment and website adoption remain separate.
