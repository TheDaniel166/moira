# VED-017 Gochar windows source research

**Date:** 11 October 2026. **Status:** research complete for the existing
whole-sign profile; window implementation remains open. **Runtime baseline:**
Moira 6.9.9, engine `524a8d3caf3470634080fc930479625e0f7f29c9`.

## 1. Recommended product boundary

Complete VED-017 by finding the bounded intervals over which Moira's existing
Gochar observations and Vedha relations remain constant. Preserve the selected
`phaladeepika_26_sastri_1950_seven_classical` profile, natal-Moon reference,
directed exemptions, historical indications and optional raw natal BAV.

The classical basis is sufficient. Phaladeepika 26.3–8 conditions the subject's
result on which planets occupy the corresponding Vedha signs at the time under
consideration. Consequently, a window can end when a **blocker** changes signs
even when the subject does not. Retrograde re-entry follows the same positional
rule: re-evaluate actual sign occupancy on every crossing. This is a temporal
composition of the admitted rule, not a new prescription about retrograde
strength or repeated-event intensity.

Source-specific activation within a sign, counter-Vedha, Murthi, additional
references, nodes, aspects and dasha modifiers retain their separate VED-018/019
admission boundaries. The window engine should accommodate future additional
boundary signals without enabling those doctrines now.

## 2. Source ledger and evidence quality

The local corpus is `C:\dev\ASTROLOGY-BOOKS-DATABASE`, commit
`b5d07260d2c0dd11a1c8e4162c9f998a995c47be`. The research evidence directory is
`C:\dev\outputs\ved017-gochar-windows-research-2026-10-11`.
`source_manifest.json` records fresh SHA-256 hashes, page counts, selected pages
and render locations for eight PDFs. All six corpus PDFs match their earlier
inventory hashes. Downloaded source copies are identified separately; they are
not represented as files already present in the book database.

PDF page numbers below are one-based. Text extraction located passages;
fourteen rendered pages were visually inspected, including the core Sastri
Vedha rules, all principal activation comparisons, the Prasna Marga table
discrepancies and Rao's ingress-Moon example. This is a targeted chapter study,
not a claim to have read every page of every book.

| Source and edition | Verified locator | Finding and authority boundary |
|---|---|---|
| Mantreswara, Phaladeepika, V. Subrahmanya Sastri, second edition, 1950; previously downloaded primary scan | Printed 286–288 / PDF 321–323, 26.1–8; printed 296 / PDF 331, 26.25; extracted printed 303 / PDF 338, 26.41 | Governing edition for the current natal-Moon baseline and ordinary Vedha. The source explicitly contains Rahu material; seven participants is Moira's selected admission, not an assertion that the text excludes nodes. |
| Local `Classics books/Mantreswara_Phaladeeplka.pdf`, Kapoor translation | PDF/printed 246–251; activation paragraph on page 251 | Corroborates thirds-of-sign activation. This copy prints the activation paragraph as **30**, between 24 and 26. Preserve edition/page identification instead of propagating that number as the Sastri verse locator. |
| Varahamihira, Brihat Samhita, Sastri/Bhat 1946; local `Classics books/brihatsamhita.pdf` | Printed 785–786 / PDF 802–803, 104.49–50 | Sun/Mars use the first **half**, Moon/Saturn the latter half, and Mercury the whole sign. This differs materially from Phaladeepika's thirds. These verses do not supply a complete Jupiter/Venus activation table. |
| Prasna Marga, B. V. Raman translation, Part II, 1992; previously downloaded scan | Printed 184 / PDF 203, 22.26 and following notes; printed 187–188 / PDF 206–207, 22.36–43 | Beginning/middle/end language; aspect and dasha comments are separately labelled notes. Counter-Vedha and discrepant tables cannot silently extend the current profile. The corpus's `PRASNA MARGA.doc` is the previously identified Part I, not this Part II scan. |
| Jataka Parijata, local Vol. III translation/commentary | Printed 833–834 / PDF 127–128, **notes following** 13.60 | Commentary explicitly discusses current occupancy of Vedha signs and the two father/son exemptions. Its explanatory table includes reverse pairings. Treat those as commentary, not an independent classical verse admitting counter-Vedha into Moira. |
| Jataka Parijata, local Vol. II | Printed 667–669 / PDF 341–343, extracted commentary | Relevant to BAV interpretation, not a new ingress clock. Its thresholds and reconciliations must not turn the current raw BAV field into an unstated strength rule. |
| P. V. R. Narasimha Rao, Vedic Astrology: An Integrated Approach; local `Good books/vedic_astro_textbook.pdf`, and author's online copy | Printed 346–348 / PDF 358–360; 26.2–26.3, Tables 62–63 | Modern primary author source for ingress-Moon Murthi. It fixes a classification using the Moon at ingress; this requires ingress history outside a clipped query. Its Venus table also differs from the selected Sastri table. |
| Local `Classics books/Uttara-kalamrita-kalidas.pdf` | Printed 37–40 / PDF 40–43, extracted text | The located Vedha passages concern aspects and Bhava obstruction. They do not establish the ordinary Gochar window rule and were not promoted to that authority. |

Online verification on 11 October 2026:

- [Phaladeepika chapter 26, Sastri translation](https://www.wisdomlib.org/hinduism/book/phaladeepika-by-mantreswara-text-and-translation/d/doc1621598.html)
  and [original 1950 scan](https://www.wisdomlib.org/uploads/ocr/essays/phaladeepika/phaladeepika-2nd-ed-1950-by-v-subrahmanya-sastri-text.pdf).
  The HTML warns that its OCR is unproofread; the scan controls the locators.
- [Brihat Samhita chapter 104, Iyer translation](https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc229368.html)
  and Sanskrit/translations of [104.49](https://www.siva.sh/brihat-samhita/104/49)
  and [104.50](https://www.siva.sh/brihat-samhita/104/50). The Iyer HTML repeats
  the number 48 for the half-sign paragraph; the Sanskrit and local scan locate
  it at 49.
- [Rao's author-hosted textbook](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf).
- [Prasna Marga Part II scan source](https://storage.yandexcloud.net/j108/library/j8jiaafw/Panangadu_Nambudhiri_-_Prasna_Marga_%28Part_II%29.pdf):
  the retained copy was hashed and visually checked locally in this pass.
- [NAIF Geometry Finder required reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/gf.html),
  especially search steps, convergence, missed events and piecewise monotonicity.
- [JPL ephemeris export documentation](https://ssd.jpl.nasa.gov/planets/eph_export.html)
  and [IERS time scales](https://www.iers.org/iers/en/dataproducts/tools/timescales/timescales).

The NAIF material explains why a small root-refinement tolerance does not prove
that all events were found: coarse sampling can skip an entire event or a gap
between events. Its numerical searches also depend on finding relevant extrema.
Moira should use its own admitted computational substrate; this reference is
algorithmic authority, not a proposal to add SPICE as a base runtime dependency.

## 3. Source distinctions that affect window design

### Current occupancy and blockers

Sastri 26.3–8 gives 36 directed pairs. For example, Jupiter in the second from
the natal Moon is obstructed by occupancy of the twelfth. The Sun/Saturn and
Moon/Mercury exemptions do not exempt an unrelated planet occupying the same
blocking sign. All witnesses matter: one blocking planet leaving does not
release an obstruction while another remains. An exempt witness can change
without changing the overall verdict. These distinctions must remain visible
in window evidence rather than being reduced to a single favourable flag.

### Activation within a sign

| Rule family | Sun, Mars | Jupiter, Venus | Moon, Saturn | Mercury |
|---|---|---|---|---|
| Phaladeepika 26.25, Sastri | First 10 degrees | Middle 10 degrees | Final 10 degrees | Entire sign |
| Brihat Samhita 104.49–50, Sastri/Bhat | First 15 degrees | Not assigned by these two verses | Final 15 degrees | Entire sign |
| Prasna Marga 22.26, Raman | Beginning | Middle | Last part | Entire sign |

Phaladeepika additionally names Rahu as effective throughout. Ketu must not be
added by copying that sentence. The Raman paragraph alone does not quantify
its three parts; its numerical interpretation needs its own named derivation.
None of these passages says to use one third or one half of **elapsed time**:
the Phaladeepika rule expressly uses angular degrees. Retrograde visits make
elapsed-duration subdivision particularly unsuitable.

These sources support future separate activation profiles. They do not decide
whether an implementation should suppress all baseline testimony outside an
active portion, report a separate activation layer, or modify blocker efficacy.
For VED-017, retain the existing whole-sign testimony. For VED-019, prefer a
separate attributed activation layer before considering any suppression rule.

### Variant tables and ingress-dependent memory

The visually checked Raman Part II pages differ from the current profile:
Moon's last two mappings read 10→9 and 3→4; Mercury's last pair reads 11→11;
Jupiter's sequence includes 8 where the Sastri sequence has 7. These are printed
discrepancies, not merely this pass's OCR errors. Do not silently correct them
or call every one a distinct school before collating another edition. Rao's
Table 63 has Venus 11→6 and 12→3, whereas the selected Sastri profile has
11→3 and 12→6. VED-018 owns admission or reconciliation of those profiles.

Rao 26.2 fixes Murthi from the transiting Moon **at the subject's sign entry**.
That differs from ordinary Vedha, which is evaluated at the current instant.
The inspected passage does not settle how a later retrograde re-entry resets
Murthi. Retain ingress identities and ordered visits in a reusable event layer,
but do not invent a reset rule or let this VED-019 question block VED-017.

## 4. Runtime audit and executable findings

The current dated product is in `moira/gochara_dated.py`, with strict models,
services and routes under `moira_server`. It derives seven complete positions,
separate natal/transit clocks and ayanamsas, and optional same-birth raw BAV.
Its five routes cover evaluation, profiles, doctrine discovery and the two
dated snapshot inputs. There is no Gochar window route.

The governing frame is apparent geocentric true ecliptic of date, with light
time, aberration, gravitational deflection and nutation. Each epoch binds
UT1→TT→TDB to the serving reader. JPL's ephemeris integration scale is TDB;
solver coordinates, ephemeris arguments and returned timestamps must not be
interchanged. Civil endpoints must each pass through the existing aware-time
conversion once. Solver precision must be distinguished from astronomical,
Earth-rotation and birth-input uncertainty.

### The generic ingress finder cannot certify this product

`moira/transits.py:find_ingresses` currently compares sampled **tropical**
longitudes against the twelve multiples of 30 degrees. It requires a strict
sign change between consecutive samples and estimates direction using samples
one quarter-day on either side of a candidate. Its `CrossingSearchTruth`
records the scan and refinement; it does not prove no crossings were missed.

`research_probes.py` reproduced zero detected events for a quadratic path with
two crossings at times 0.4 and 0.6 inside one step, and for a linear crossing
exactly on an interior sample. Exact request-end crossings are also excluded
by the strict product test. Start-edge ownership is unspecified for the new
product and must be defined deliberately. These synthetic results demonstrate
algorithmic limits; they do not claim a particular real planetary event was
missed in production.

The marriage interval isolator retained both quadratic root regions and a
tangency region, with exclusion evidence elsewhere. A retained possible-root
region does not itself prove root existence, uniqueness or a sign change.
Those properties need separate witnesses or a conservative unresolved status.

### Sidereal search must preserve all admitted choices

The real DE441 probe resolved all twelve current dated ayanamsas: seven
polynomial systems and five live anchors. Polynomial windows need the selected
J2000 value, precession, any per-century drift and true-mode nutation. The
existing marriage `FrameEnclosures.angles()` instead hardcodes Lahiri.

The five live systems are True Chitrapaksha/Spica, Aldebaran (15 Tau), True
Revati/Revati, True Pushya/Asellus Australis and True Mula/Shaula. Their window
offset must follow the same `star_at(anchor, reader_bound_TT)` operation as the
dated product. The current star owner propagates its catalog ICRS vector using
proper motion and, where admitted, distance/radial velocity, then transforms
to true ecliptic coordinates. This supplies a concrete enclosure path:
enclose that propagated vector, its normalization and the same frame rotation;
retain catalog/record identity and all singularity branches. Do not add stellar
corrections absent from that owner merely because a helper docstring calls the
result apparent.

The dated Gochar owner directly resolves live anchors and fails when they are
missing. The general sidereal helper has a polynomial fallback on some catalog
failures. Reusing that helper unconditionally in windows would violate the
dated product. Certified support for all twelve is the proposed completion
target; accepting a name while silently using Lahiri is never acceptable.

### Real ingress illustration

Using reader identity `DE-0441LE-0441`, the probe scanned Jupiter from 1 May 2025
through 15 July 2026 with true Lahiri evaluated at every epoch. It found these
candidates, then narrowed each bracket to approximately 0.0824 seconds:

| Sidereal boundary | Direction | Approximate midpoint JD UT1 |
|---|---|---|
| 60 degrees | Direct | 2460810.213054525 |
| 90 degrees | Direct | 2460967.096463071 |
| 90 degrees | Retrograde | 2461014.996371137 |
| 90 degrees | Direct | 2461193.347415792 |

Freezing ayanamsa at the request start moved the three 90-degree examples by
approximately −8269.94, +10556.31 and −7712.53 seconds. This deliberately
incorrect comparison illustrates why a constant offset is unsuitable.
The exploratory two-day scan is **not** a completeness certificate, and its
narrow brackets are not an external accuracy claim. Exact receipts are in
`astronomy_probes.json`.

## 5. Window semantics required before implementation

Let `s_p(t)` be the floor of the normalized sidereal longitude divided by 30
for participant `p`. Fix the natal reference, source profile and natal BAV.
On any region where all seven `s_p(t)` are constant, the admitted baseline,
indication keys, raw sign-based BAV and ordinary Vedha relations are constant.
This follows from the current evaluator's dependencies; continuous longitudes,
clocks and ayanamsa values themselves are **not** constant.

The complete candidate boundary set is the union of all seven bodies' sign
boundary contacts, plus request cuts and any unresolved computational regions.
Each retained candidate needs left/right occupancy evidence and attribution to
the body and ray. A station inside a sign does not change the current doctrine;
stations still matter to the search's ability to discover repeat crossings.
If continuous retrograde status becomes a promised window field, stations
become additional segmentation events and require explicit admission.

Required decisions:

1. **Separate state from samples.** A discrete state key includes the source
   and policy, seven signs, natal reference, subject conditions, all witness
   identities/exemptions, source locators and applicable raw BAV values. An
   astronomical sample carries its own epoch. Do not promise that an entire
   dated snapshot, including its degrees, applies unchanged over an interval.
2. **Retain full and projected views.** Canonical atomic cells retain all
   admitted state changes. An optional subject-focused view can coalesce cells
   only according to a declared state key and with underlying event references.
   Selecting Jupiter for display must not remove the Moon or other blockers
   from the computation.
3. **Distinguish spatial from temporal endpoints.** The existing spatial rule
   assigns exactly 30 degrees to Taurus in either direction. At a retrograde
   crossing, that is the pre-crossing sign; immediately afterwards is Aries.
   Blindly labelling every temporal `[start,end)` interval with its right-hand
   sign would contradict exact point evaluation. Preserve certain interiors
   and explicit boundary regions with endpoint inclusion metadata.
4. **Handle touches and coincident candidates.** A maximum that just touches
   30 degrees can have Aries on both sides and Taurus only at the exact point.
   The diagnostic verifies this singleton behaviour. Do not manufacture a
   positive-duration transit or discard a possible singleton. Refine overlapping
   bands when possible; otherwise report unresolved event order jointly.
5. **Cover the whole requested domain.** Ordered certain cells, boundary bands
   and unresolved regions must account for it without hidden gaps or overlaps.
   Clipped endpoints are request cuts, not invented ingress times. Do not infer
   a visit's true start from the start of the query.
6. **Report completeness separately.** Seven-body input completeness, search
   coverage, numerical boundary resolution and doctrinal layer coverage are
   different claims. `retain_partial` from the snapshot policy is not consent
   to omit unsearched time or a missing blocker ephemeris.

## 6. Engine, facade and REST requirements

Use one immutable engine result and one serializer for both epoch and civil
window entry points. Suggested route names are
`POST /v1/gochara/windows/from-epochs` and
`POST /v1/gochara/windows/from-datetimes`; these are proposals, not current routes.
Facade names and curated exports should follow the dated product's conventions.

The request needs a natal instant, an ordered bounded search interval, the
existing date/doctrine policy, optional birth location exactly when raw BAV
is computed, and a typed search policy. Require finite numbers, reject boolean
numeric coercion, unknown fields, naive datetimes and contradictory policies
before opening resources. Preserve valid retrospective searches: a search
before birth is already allowed by the dated snapshot contract.

The response should expose:

- Request interval and time-scale/civil-conversion receipts, immutable natal
  context, selected policies and source profile.
- All seven participant identities, serving kernel/time identity, frame and
  correction choices, ayanamsa method and live-anchor identity where applicable.
- Atomic cells with discrete states and individually dated representative
  samples, plus optional coalesced views linked back to atomic cells.
- Boundary/event identifiers, body, angular ray, direction when established,
  enclosing time band, before/after witnesses, changed subjects and changed
  relations; unresolved regions retain reasons and affected dependencies.
- Coverage/completeness status, boundary tolerance in seconds, actual work
  counters and explicit request clipping. No invented probability of an
  astrological outcome and no combined BAV/Vedha strength score.

Keep current validation/coverage errors distinct from resource failures
(currently 422 and 503 respectively). Add an explicit typed work-budget failure
using the server's established election-search convention. A failed or truncated
search must never become an ordinary successful empty window list. If a bounded
result with unresolved bands is admitted, its incompleteness must survive
serialization, OpenAPI and every public convenience view.

Bound duration, evaluations, root refinements, candidates, output cells and
request-owned cache sizes. Set numerical caps from representative benchmarks
before API admission; this research establishes no production latency promise.
Monthly and yearly Gochar requests must be measured, not inferred from the
marriage search timings.

## 7. Reusable implementation direction and acceptance gates

Factor a small technique-neutral event layer from the existing interval
arithmetic, serving-record/clock enclosures, frame operations, root isolation
and deterministic budget accounting. Keep marriage consumers compatible through
their existing adapters. Gochar should not need a marriage policy, location,
horizon calculation, lunar-month history or election scoring to find sign
crossings. Any shared protected-owner changes require their existing parity
and adversarial checks in addition to Gochar tests.

Compute natal astronomy/BAV once per request. Reuse exact-input frame/ayanamsa
work across bodies and shared interval cells. Transit astronomy is independent
of the natal chart, so an immutable event stream can later support multiple
nativities. Start with bounded request-owned caches; a cross-request cache
requires complete kernel, catalog, frame, clock, policy and version identities.
Do not key reusable results only by a body name, filename or rounded time.

| Gate | Required evidence |
|---|---|
| Doctrine preservation | Existing 36 directed pairs and four directed exemptions; multiple/exempt witnesses; no implicit nodes, counter-Vedha, activation or BAV thresholds. Source fixture remains independent of implementation. |
| Event completeness | Independent analytic signals with two crossings inside one step, tangent extrema, stationary roots, exact sample/request edges, 0/360 wrapping and overlapping events. Every rejected region has exclusion evidence; possible roots are not automatically confirmed crossings. |
| Frame and clock parity | All seven polynomial and five live-anchor systems; drift and TT use; missing anchors fail; same serving reader and correction model as `gochara_at`; catalog changes cannot reuse stale evidence. |
| Numerical astronomy | Point containment and velocity/rate checks across serving record boundaries, retarded epochs and coverage edges; real direct–retrograde–direct sequences. External comparisons must align frame, time scale, corrections and ayanamsa before applying a declared tolerance. |
| Composition | Each certain cell reproduces the existing snapshot's discrete result at independent interior probes; blocker-only changes, unchanged verdict with changed witnesses, subject views and raw BAV indexing are preserved. Probes supplement rather than replace exclusion proofs. |
| Partition and boundaries | Full domain accounting, explicit endpoint ownership, clipped requests, unresolved ordering and singleton contacts. Splitting a request must reproduce the combined result modulo declared clipping/coalescing. |
| Engine/REST parity | Epoch/civil equivalence, offset-equivalent instants, all admitted policy combinations, strict payloads, typed errors, OpenAPI/curated exports, null-versus-omitted fields and exact serializer preservation of uncertainty. |
| Work and reuse | Deterministic budget exhaustion without partial success; natal work once; cache parity/isolation; repeated calls; day/month/year measurements; no unbounded resource or output growth. |

The appropriate next step is an implementation plan covering these gates as
one VED-017 package: discrete window contracts; reusable astronomy and all
ayanamsas; complete event partitioning; engine/facade/REST delivery; adversarial
and external-frame validation; measured resource limits. Admission of VED-018/019
rules is a subsequent source-profile decision.

## 8. Research verification receipt

Project runtime: `.venv\Scripts\python.exe`, Python 3.14.3. Kernel discovery
used `moira._kernel_paths.find_planetary_kernel()` with `MOIRA_NO_DOWNLOAD=1`;
the serving path was `C:\Users\nilad\.moira\kernels\de441.bsp` and the reader
reported `DE-0441LE-0441`. No kernel download, source fixture rewrite, runtime
code change, source publication, release or deployment occurred.

Commands and outcomes:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe C:\dev\outputs\ved017-gochar-windows-research-2026-10-11\research_sources.py
.\.venv\Scripts\python.exe C:\dev\outputs\ved017-gochar-windows-research-2026-10-11\research_probes.py
.\.venv\Scripts\python.exe C:\dev\outputs\ved017-gochar-windows-research-2026-10-11\research_probes.py --semantic-only
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py tests/unit/test_gochara_dated.py tests/server/test_server_gochara.py tests/server/test_server_gochara_dated.py -q
```

PDF extraction/hash checks and final diagnostic assertions passed. The initial
astronomy probe correctly refused a legacy `get_reader()` call without an
active owner; the completed probe explicitly uses the Moira facade's reader.
The five-file existing Gochar regression slice passed **349 tests**, with no
failures or skips; collection count was checked separately. These validate
the current snapshot baseline and research diagnostics, not an implemented
window product. The real candidate search is internally reconstructed evidence,
not a newly completed external oracle comparison.

Tracked research changes are this source record and its link in the
[remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md). The generated
`moira.wiki` mirror and protected runtime/validation owners are untouched.
