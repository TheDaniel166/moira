# Vedic adversarial repair plan

**Status:** Implemented and validated locally; all eleven VA repairs closed. [Completion receipt](../03_validation/VEDIC_ADVERSARIAL_REPAIR_VALIDATION_2026-10-09.md).
**Date:** 9 October 2026.
**Baseline:** engine `b578ec89b90f709c8e64d5d9405ca06d29fcc69c`, generated wiki `9d3591367af6311bbec5f47afeab7918939b5724`, version 6.9.9.
**Scope:** All eleven findings from the Vedic adversarial review, across engine, curated Python/facade surfaces, REST, source evidence and regression coverage.

Repair the existing Dasha and strength foundations before VED-011 purpose elections. Deliver five implementation packages, each with its own tests and transport coverage, followed by one combined acceptance run. The VA identifiers below are repair identifiers, not additional VED techniques or a replacement for the 24-package register.

The audit completed 4,388 tests across 112 files: **4,387 passed, one failed, zero errors/skips**, with all 406 DE441 resource receipts exercised. The isolated failure is VA-11. Ten other defects were reproduced by independent arithmetic, primary-source comparisons, boundary probes and real HTTP requests. The private audit packet, including scripts, JSON, XML, rendered source witnesses and source hashes, is retained at `C:/dev/outputs/vedic-adversarial-review-2026-10-09/`. Passing the existing suite alone will not close these repairs.

## Delivery order and coverage

| Package | Findings | Deliverable | Dependency |
| --- | --- | --- | --- |
| A | VA-01, VA-11 | Correct Dasha time axes and reconcile the historical fixture | First implementation package; independent of strength work |
| B | VA-07, VA-08 | Consistent Varga boundaries and longitude normalization | Complete before the positional-strength repair |
| C | VA-02, VA-03, VA-06 | Source-defined temporal and positional strengths, with explicit calculation context | Uses B; source decisions and independent expectations precede arithmetic edits |
| D | VA-04, VA-05 | One planetary-war calculation and evidence ledger | Uses C's raw components; pairwise and multi-war rules must be recorded |
| E | VA-09, VA-10 | Correct borrowed-reader scope and guaranteed scan progress | Independent repairs; complete before combined acceptance |

Use the order A, B, C, D, E for implementation and review. Source collation for C/D can proceed without changing their runtime while A/B are being completed. Tests, REST contracts and documentation belong in each package. They are not postponed to a separate generic hardening phase.

| Finding | Priority | Required change | Closure witness |
| --- | --- | --- | --- |
| VA-01 | P1 | Subdivide full Dasha parents before clipping visible intervals | All three engines return the correct active child at nonzero birth balance; hierarchy and HTTP agree |
| VA-02 | P1 | Correct Nathonnatha, Paksha, Tribhaga and Ayana | Source-derived component oracles, local solar geometry and planetary declinations |
| VA-03 | P1 | Correct Saptavargaja scales, relationships and division assignment | Both named weight tables; compound relationships; exact source-prescribed Moolatrikona treatment |
| VA-04 | P1 | Resolve multiple wars consistently and derive totals from final components | Synthetic chain/clique and real 18 May 2000 chart; optional-strength Lagna request succeeds |
| VA-05 | P2 | Report actual war adjustments from the owning calculation | Component, network and full HTTP receipts agree for 21 December 2020 and multi-war cases |
| VA-06 | P2 | Include Mercury in the source-defined odd-sign group | Four D1/D9 parity combinations give 30, 15, 15 and 0 |
| VA-07 | P2 | Use one exact Varga partition for segment, sign and degree | Zero disagreements in the retained 65,880-case corpus and the expanded supported-domain checks |
| VA-08 | P2 | Normalize finite angles consistently before named divisions | Tiny negative input succeeds without longitude 360 or index errors across applicable REST routes |
| VA-09 | P2 | Honor Kalavela's supplied reader through the entire computation | Empty/conflicting/nested contexts use the requested reader and restore prior ownership |
| VA-10 | P2 | Reject invalid/non-progressing Sade Sati steps and bound work | Immediate rejection before resource access; every admitted iteration advances within the work limit |
| VA-11 | P2 | Reconcile the Einstein fixture with the corrected precession model | Independent derivation passes the original tolerance; historical values retained as migration evidence |

## Common source and contract rules

Before editing an affected formula, record its computational object, edition/page, inputs, units, frame/time conventions, exceptions and independent expected values. Reuse the inspected BPHS Santhanam I/II and Raman Balas witnesses. Complete targeted local-library and primary-source online collation for unresolved war, relationship and solar-time details; do not reopen a broad search for already established rules.

Keep factual source differences executable as named policies where admitted. The engine owns resolution and the applied receipt; the server copies that receipt. Reject unknown profiles and unsupported combinations before ephemeris work. Historical erroneous arithmetic is migration evidence, not a default source policy.

The principal compatibility policy is to preserve function/route names and existing argument meaning where possible, append keyword-only evidence inputs and additive result metadata, and disclose corrected numerical outputs. A call lacking newly required evidence must receive an explicit missing-context result or error appropriate to its product. It must not silently substitute UTC, another chart's geometry, a speed estimate or a fabricated complete total.

Public exports, canonical vessels, facade and REST are protected contracts under `AGENTS.md`. Their implementation slices require the pre-edit declaration and targeted checks. The astronomical substrate, precession correction, kernel resolver and resource ownership remain the governing services. A discovered need to change those owners must receive its own source review and affected parity tests. Frozen evidence and tolerances cannot be refreshed merely to make a test pass.

## Package A Dasha timing and fixture reconciliation

Owners: [Vimshottari](../../moira/dasha.py), [alternate Dashas](../../moira/dasha_systems.py), their facade/model/serializer/service callers, and the existing Dasha unit/server tests.

### Full parent intervals

Represent the true full parent interval separately from its visible interval. For the birth major period, calculate the original start from the elapsed fraction and full duration. Generate each descendant using that full interval and its source sequence, then intersect it with the requested range. Apply the same process at the final truncated cycle/horizon. Omit empty intersections and preserve the existing half-open boundary ownership.

Keep public `start_jd`/`end_jd` as the visible interval where that is the existing contract. Carry canonical full start/end and clipping evidence in appended metadata; legacy manual objects without that evidence remain visibly unknown. Record the actual year basis, elapsed fraction and origin. Do not reinterpret a duration property silently or mix fixed-year and calendar-anniversary arithmetic.

`current_dasha`, sequence/profile accessors, alternate-Dasha chart products and REST must select the same child at every tested instant. Strengthen tree validation for containment, order, positive representable duration, adjacency and agreement between full and clipped intervals. Test the deepest supported hierarchy without constructing an unbounded tree.

### Required witnesses

- Halfway through Ashwini at J2000, savana-360: Ketu/Rahu at birth, not a restarted Ketu/Ketu interval. The full-axis Rahu interval is JD 2451335–2451713.
- Real natal/current timestamp `2000-01-01T12:00:00Z`, savana-360: Rahu/Mars at birth. The audit's Mars interval is JD 2451424.29907202–2451802.29907202.
- Alternate-system audit fixtures: Yogini Bhramari/Siddha and Ashtottari Rahu/Mercury. Keep the Ashtottari eligibility bypass explicit in the arithmetic fixture and test ordinary eligibility independently.
- Births within every first-major child, exact transitions and neighbouring floats, zero elapsed fraction, near-complete majors, final clipping, all admitted year bases, and multiple hierarchy depths. Derive expected timelines independently from full-period ratios rather than the production builder.

### Historical fixture

Reconcile `test_einstein_jyeshtha_starts_mercury_and_bhadrika` with the admitted general-precession correction in `34e3430`. Preserve the tropical Moon witness and epoch. Independently derive the ayanamsa, nakshatra progress and balances with explicit frame, mode and year basis; then review the proposed replacement expectations.

The audit measured current balances 8.917206594818651 Ashtottari years and 2.8681234660163817 Yogini years. These are candidate regression values, not independent authority by themselves. Substituting only the historical scalar reproduces the old values within the existing 1e-9 tolerance. Retain that migration proof, keep the original tolerance, and do not revert the astronomical correction. Add this source-fixture test to the relevant CI gate so the earlier omission cannot recur.

**Exit:** VA-01 and VA-11 pass independently, together, and through their public/REST consumers; first-period and clipped-horizon chronology is correct under each admitted clock.

## Package B Varga partition and angle normalization

Owners: [Varga](../../moira/varga.py), shared Varga transport, and Varga-consuming dignity, Avastha, strength and Lagna paths.

Generalize the exact partition approach used for D9. Derive the segment and within-segment degree from one exact representation of the supplied binary input. Compose a representable longitude on the same side of the half-open boundary; the sign label, sign degree and longitude must agree. Keep generic harmonic assignment separate from source-specific sign mappings.

Centralize finite-angle normalization for the affected Varga entry points. Preserve their admitted cyclic input semantics. At a nonzero negative residue that rounds to 360, preserve the side below the boundary using a documented representable value; exact multiples of 360 remain zero. Apply this before sign-table indexing and batch composition. Retain strict rejection of invalid types/non-finite values according to each public contract.

Required checks:

- Retain the 65,880 D1–D60 boundary/nextafter cases against an independent rational oracle, with zero wrong signs and zero sign/coordinate disagreements after repair.
- Cover other admitted divisors, large finite inputs, exact sign boundaries, negative zero, tiny negatives, repeated turns, and named unequal-width partitions where present. Do not expand the accepted divisor range just for this repair.
- Preserve the 4,320 explicit D60 source-profile consistency cases and existing source/oracle fixtures; these remain distinct from generic harmonic tests.
- `calculate_varga(30., 27)` returns Cancer at 0 degrees; the retained D7 witness has internally consistent label and longitude.
- `-1e-300` no longer crashes default Shodashvarga. Exercise generic, named, batch, chart-backed and Shodashvarga routes, preserving each route's existing admissible input range.

**Exit:** VA-07/08 close in engine and HTTP, with no doctrine changes hidden inside the numerical boundary repair.

## Package C Source-defined strengths and calculation context

Owners: [Shadbala](../../moira/shadbala.py), source-specific Varga/relationship helpers, facade, [Shadbala service](../../moira_server/services/shadbala.py), models/serializers, Bhava Bala and [dated Lagna](../../moira/muhurta_lagna_dated.py).

### Policy decisions

Admit separate Saptavargaja weight profiles for the two inspected witnesses:

| State | BPHS Santhanam I 27.2–4 | Raman 1996 article 30 |
| --- | ---: | ---: |
| Moolatrikona | 45 | 45 |
| Own sign | 30 | 30 |
| Great friend | 20 | 22.5 |
| Friend | 15 | 15 |
| Neutral | 10 | 7.5 |
| Enemy | 4 | 3.75 |
| Great enemy | 2 | 1.875 |

Recommended corrected default: the verified Raman rule set, consistent with the module's declared engineering reference. Expose the BPHS Santhanam scale as a named selection with its own verified prerequisites. Name profiles narrowly enough that selecting a table does not falsely attribute every other Shadbala component to the same text. Record defaults and supported combinations in engine and REST receipts before admitting them.

Keep sufficiency thresholds explicit and separate from component-method attribution. Do not tune required Rupas to compensate for corrected scores. The earlier Sun-minimum discrepancy is not one of these eleven confirmed defects; a broader source-profile claim must resolve it or state the separately applied threshold convention accurately.

The source packet must settle the local-solar-time definition for Nathonnatha, day/night thirds for Tribhaga, Moon/Mercury nature and doubling rules for Paksha, each planet's Ayana rule, D1 compound-relationship use across divisions, and the edition-specific Moolatrikona award. It must also verify the pairwise war rule needed by D. Existing comments are leads, not authority.

### Required context

Introduce one immutable engine-owned context for the additional evidence: matching epoch/frame/ayanamsa, relevant observer/solar-event geometry, per-planet tropical declinations, and the complete positions required for compound relationships. Retain the provenance needed to distinguish supplied geometry from geometry derived by the serving engine.

Dated composition builds this context once through the serving reader and canonical time/frame services. Direct synthetic inputs must not be silently combined with unrelated real ephemeris positions. Validate epoch, body coverage and frame compatibility before computing a full result. Record missing prerequisites per affected component. Unavailable polar sunrise/sunset geometry cannot yield a fabricated full strength or sufficiency ranking; preserve independently computable evidence using explicit typed unavailable/partial behavior.

### Component repairs

1. **VA-02 Nathonnatha:** replace the sine/fixed-30 proxies with the selected source formula and correct local solar-time basis. Test midnight/noon and intermediate times, contrasting observer longitudes at a common UTC instant.
2. **VA-02 Paksha:** use continuous Sun–Moon separation, the selected nature convention and explicit Moon doubling. Test exact/new/full phases and neighbours; a near-full Moon at 179.9 degrees must meet the source-derived doubled result of 119.933333... where that policy applies.
3. **VA-02 Tribhaga:** give Jupiter the permanent award under the inspected rule, Mercury the first daytime third, and use the actual sunrise-to-sunset or sunset-to-next-sunrise interval. Test exact third boundaries, unequal seasons, local-midnight carryover and equivalent timestamps expressed in different civil timezones.
4. **VA-02 Ayana:** use each planet's tropical declination, planet-dependent sign/absolute rule and Sun doubling. Test both hemispheres, extrema and zero declination. Mercury's additive-declination profile must respect the source minimum of 30.
5. **VA-03 Saptavargaja:** pass complete relationship context, apply the selected scale, distinguish natural from temporary and compound relationships, and make great-friend/enemy states reachable. Apply Raman's 45-point Moolatrikona award only where its source prescribes, including the D1 restriction. Replace the one-degree probe with the actual prerequisite where required.
6. **VA-03 division assignment:** verify all seven divisions used by each strength profile, especially D7/D12/D30. Use source-defined sign assignment for the named strength profile while preserving separately documented public harmonic selectors.
7. **VA-06 Ojayugma:** apply both D1 and D9 odd-sign contributions to Mercury. Verify all four parity combinations, including longitude 1 degrees yielding 30 and 31 degrees yielding 0 under the inspected rule.

Use independently transcribed textbook component examples at their stated input precision. Keep those arithmetic witnesses separate from modern DE441 end-to-end charts; different astronomical inputs cannot justify fitting constants or widening tolerances. Check the rest of each worked total sufficiently to avoid advertising a complete named profile over an unverified component. Any additional discrepancy required to make that selected profile coherent becomes an explicit dependent repair, with its own evidence, before profile closure.

**Exit:** VA-02/03/06 close with source-derived component fixtures, policy-sensitive tests, complete context receipts and consistent engine/facade/HTTP behavior. Correct the module's overstated cross-check/completeness claims to exactly match the evidence delivered.

## Package D Planetary war resolution and evidence

Recheck the pairwise victor/tie rules, transfer base and adjustment formula against BPHS/Raman before retaining the current raw-Chesta transfer assumption. Then define how the admitted rule composes when a body wins multiple pairs or both wins and loses. A change from assignment to addition alone is insufficient.

Use one canonical resolution object containing raw components, every detected pair, resolved adjustments, per-planet debits/credits and the applied rule/source identity. Detection and allocation are separate facts. Define the multi-war allocation explicitly, prove its determinism under input/pair reordering, and prevent repeated spending of a finite loser pool where the admitted rule uses such a pool. Test conservation and bounds appropriate to the selected formula rather than imposing an unrelated scoring model.

If the sources specify only pairwise behavior, finish the targeted source search and document that limit. A necessary multi-way extension must be explicitly named as a Moira composition convention with an inspectable derivation and worked cases; it cannot be attributed to a classical author. Selecting and documenting that rule is a deliverable of D, not a reason to mark VA-04 closed with multi-war charts unsupported.

Derive final components and totals from the same resolution object. The chart, profile, network, Bhava and HTTP full response must consume it. Remove the independent speed-fallback path from receipts claiming an actual transfer. A separately retained estimate must have an explicit estimate label and must not populate the actual-adjustment field.

Strengthen the owning output validator for component sums, totals, Rupas conversion, sufficiency flags, receipts and frame identity. Retain Lagna's strict validation. Keep caller-invalid data distinct from an internally inconsistent server-produced object; an internal invariant failure is not a client input-validation error.

Required witnesses:

- No war, one pair, shared victor, shared loser, chain, clique, equal/tie cases, zero raw component, and a body that both wins and loses. Pair/input permutations must give the same resolved result.
- The real `2000-05-18T00:00:00Z`, latitude 28.6, longitude 77.2 case: ordinary Lagna and Lagna with Shadbala both succeed, with consistent canonical totals and full policy evidence.
- The real `2020-12-21T12:00:00Z` Jupiter–Saturn case: actual adjustments match the chart/network/HTTP receipt. Do not freeze the old 11.8998 amount as classical authority if source repair changes the underlying formula.
- Deliberately corrupted external strength input still fails admission; valid internally generated strength is accepted.

**Exit:** VA-04/05 close with the source/admitted composition policy resolved, actual transfers transported faithfully, and both retained real requests passing.

## Package E Reader ownership and bounded scanning

### VA-09 Kalavela

Bind an explicitly supplied reader around the entire [Kalavela calculation](../../moira/upagrahas.py), including solar events and dependent house/sidereal services. Restore the previous context on success and every exception. Borrowing never transfers ownership or closes the caller's reader.

Test valid explicit reader with no ambient reader; explicit reader A while reader B is active; nested overrides; event/coverage failures; and return to the original context. Include actual discovered/configured-kernel lifecycles and relevant facade/REST compositions. Existing tests that manually supply the missing ambient override must no longer be the only evidence.

### VA-10 Sade Sati

Validate finite ordered range endpoints, finite positive numeric step, supported sampling bound and estimated work before resource access. Reject booleans, zero, negatives, non-finite values, overflow and positive steps that cannot advance the representable Julian date. Assert `next_jd > jd` during the scan and bound refinements; positive input alone does not guarantee progress.

Preserve the existing five-day default initially. Derive and document an admitted upper step bound from the supported event-search contract; do not claim it proves detection of every arbitrarily short retrograde excursion. Include forward/retrograde re-entry and clipped-endpoint regression cases.

Add an explicit, configurable per-request evaluation budget with a preflight estimate and runtime enforcement. Select its default from measured supported searches and record the compatibility impact, rather than inventing an unexplained civil-year cap. Exhaustion must return a typed resource/work-limit outcome, never silently truncated complete windows. Preserve the existing REST surface unless an added budget field is justified; the current HTTP model does not expose `scan_step_days`. Apply the same work bound to engine, facade and server composition so HTTP cannot bypass it. This closes the Sade Sati part of operational bounding only, not the separately deferred whole-REST budgeting programme.

**Exit:** VA-09/10 close with reader restoration and progress/budget invariants tested in isolation and through their consumers; the current infinite-loop repro rejects immediately.

## REST compatibility and evidence in every package

- Engine-owned metadata includes applied source profiles, required geometry availability and the evidence needed to interpret changed results. Every affected serializer transports it losslessly.
- Preserve existing ayanamsa precedence and selected house-policy receipts. Distinguish source-method changes from frame/clock changes; do not substitute one for the other.
- Cover direct, chart-backed, batch, summary/current, network/full and Lagna compositions where applicable. Do not limit acceptance to one representative endpoint.
- Reject unsupported policy values, invalid numeric types and contradictory external evidence at preflight. Test missing kernel, out-of-coverage and missing geometry separately from malformed client input.
- Review additive model fields and any necessary direct-call tightening as explicit compatibility changes. Keep old names where possible; publish before/after examples and migration instructions for changed numerical outputs or evidence requirements.

## Combined acceptance and closure

Use the project `.venv`, no downloads and strict known-issue expiry. Begin each package with the smallest failing witness, then its affected-family checks. After all five packages pass, run the combined checks once; repeat only the slices justified by a subsequent fix.

1. **All eleven witnesses:** turn diagnostic captures into independently derived assertions. Confirm each fails for the audited behavior and passes after its repair. No self-referential expected values from the same production helper.
2. **Source arithmetic:** check both Saptavargaja profiles and the admitted Kala/war rules with edition/page/input/unit/tolerance records. Distinguish printed precision, rational invariants, regression parity and astronomical authority.
3. **Boundary and property checks:** retain/extend the 65,880 Varga corpus, 4,320 explicit D60 checks, Dasha full/visible tree laws, war order invariance and policy-specific allocation laws, reader restoration, and bounded scan progress.
4. **Real resources and REST:** rerun the retained real Dasha, single-war and multi-war requests; add longitude/season/timezone/polar context cases and discovered/configured readers. Record exercised and skipped resources explicitly.
5. **Broad regressions:** rerun all 112 files selected by the adversarial audit, plus new tests and every newly affected consumer. Require zero unresolved failures, including VA-11, and explain any resource skip before making a closure claim. Preserve the selection manifest and XML; do not equate a narrower green CI run with this coverage.
6. **Release contracts:** run the applicable release-hardening groups, exact export/facade/docstring/OpenAPI guards, Python 3.10 grammar and current CI runtime checks, scoped Ruff and whitespace checks. Verify any admitted native counterpart if shared semantics changed; no speculative native port is required.
7. **Documentation:** update owning standards, compatibility notes, source headers and the remaining-work register. Regenerate REST reference, Hellenistic inventory when affected, generated wiki and the allowlisted publication bundle in repository order. Run all six release-facing documentation gates.

Keep an eleven-row completion ledger with code/test/source/REST references and the exact closing receipt for each VA item. A source decision still unresolved, a known valid request still failing, a weakened validator, a hidden fallback or an unexplained skipped check prevents that row from closing.

Completion means every VA row is closed and the combined receipt is green. VED-011 resumes after that checkpoint. Commit/push, package release and deployment remain separate authorized actions; when source publication is requested, publish the generated wiki first and then the parent engine/gitlink.
