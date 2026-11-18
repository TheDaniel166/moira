# Stage 6: bounded products, public contracts and compatibility

**Status: accepted for the additive bounded-evidence v1 integration,
2026-11-17.** The acceptance set has **396 distinct passing checks**, eight
real HTTP transport checks, no outstanding test failures, no test errors and
no skips. The earlier full-window lunar probe exposed an adapter defect; its
failing receipt is retained alongside the passing correction checks. The
scientific supported-domain limits accepted in Stages 3–5 remain explicit.

Stage 5 is committed as `1a0f1f55f9cfe1f41383b175b4dde4909ddcd4cb`, with
parent `12eaaf807b0e38f9bd316a23de7135f98ab1bf37`. All 14 committed files
match the accepted Stage 5 bytes after Git's documented newline conversion.
Stage 6 remains uncommitted. Nothing was pushed. Stage 7 has not started.

## Public integration

`moira.eclipse_evidence` provides frozen, typed, recursively immutable
contracts and an exact-bound serializer. `EclipseCalculator.solar_evidence`
and `.lunar_evidence` expose the opt-in products using the calculator's own
reader. The additive `/v1/eclipses/{solar,lunar}/bounded-evidence` POST routes
use the request engine's reader and publish a complete typed OpenAPI schema.
See [Bounded eclipse evidence v1](../eclipse-bounded-evidence.md) for requests,
statuses, model conventions and examples.

Solar domains use numeric UT1, including BCE epochs. Lunar domains use TT.
Exact rational bounds, outward numeric displays, source/model/clock/horizon,
topology, components, limits, retained domains, precision, budget and cause
survive serialization. Each product has its own result. Proved presence,
complete complementary exclusion, a clipped event window, requested numerical
precision and full-domain retention remain separate propositions.

Unrequested, unsupported, unresolved, error, not-applicable and evaluated-zero
results remain distinct. Numeric zero is distinct from an uncomputed quantity.
Exceptions without a reliable returned work counter expose a null counter.
No evidence call certifies a nearest event. Missing, closed, ambiguous or
out-of-coverage providers never become negative event findings.

A kernel pool is admitted only under a pinned read lease with one direct,
unshadowed planetary spine and complete supplemental pair inventories.
Unknown or competing target routes are rejected conservatively. There is no
unrelated global-reader substitution. Source identity distinguishes copied
record verification from reader-open identity and a live-file attestation.

Existing numerical strict-maximum selectors already govern Python searches,
range/local methods and API services. Their focused regressions still pass.
Legacy dataclass/JSON shapes, native/canon policies and nullable geometry are
preserved. The 92 withheld legacy support widths remain withheld. The new
geographic metric does not replace a legacy width or become NASA-compatible.

## Verification and corrected lunar adapter

The 255-check compatibility slice covers the existing and new server
contracts, serialization clocks, numerical event ordering, native/canon
selection, nullable solar/lunar products and affected analytic geometry.
The final 67-check correction slice rechecks the contracts, real short-window
products, concurrent determinism, source admission and accepted angular/cone
contact controls. Overlapping test identities are counted only once.

The first full eight-hour lunar-window probe failed because the contact
adapter used the extrema curvature evaluator. Its broad-box norm requirement
returned unavailable before the root solver could subdivide. Contacts now
use the accepted value/first-rate evaluators, with the same geometric-Moon
vectors, radii and continuity checks. Curvature remains an extrema concern.
Both corrected full-window policy tests pass:

| Geometric-Moon reference | Contact root callbacks | Vector enclosures | Contact roots | Extrema |
| --- | ---: | ---: | ---: | --- |
| Danjon angular | 358 | 320 | Six unique roots; complete partitions at requested 0.1-second width | Critical set covered; bounded |
| Static finite cone, Earth scale 1.01 | 366 | 328 | Six unique roots; complete partitions at requested 0.1-second width | Critical set covered; bounded |

Both prove occurrence while retaining three and two unresolved occurrence
complement cells respectively. Those unknown cells do not become absence.
The policies remain separate from legacy native/apparent-Moon canon routes.

All 92 fresh event epochs produce positive bounded geographic widths and
complete frozen-coefficient surface arrangements at the declared 4096-query
allocation. Fifty-one width intervals meet the requested 1-km span; 41 retain
coarser valid intervals. The 1,432 unresolved section cells include retained
limit bands, not fabricated exact roots or complete swept boundaries.

Actual IPv4 loopback HTTP checks cover typed OpenAPI, repeated identical solar
JSON, both lunar reference policies, BCE UT1, zero budgets, model-alias
rejection, legacy previous-event selection/shape and solar/lunar coverage
failures. Post-correction HTTP checks pass. The user's existing API process
on port 8765 remains running; disposable verification servers were stopped.

## Work budgets and measured cost

The public products use deterministic evaluation limits. Existing private
helpers retain their default wall cutoff, while explicit `max_seconds=None`
selects evaluation-only operation. A clock-jump control proves that this mode
still respects its finite evaluation allocation and preserves the domain.
Request-local immutable bounds are reused, and preparation/provider work is
reported separately. Elapsed time is excluded from evidence equality.

The 92-case width/topology workload used four isolated pytest workers. Median
per-request wall time was 16.13 seconds, with a maximum of 16.87 seconds;
section predicates ranged from 81 to 683 and Sturm queries from 960 to 1296.
The largest worker peak working set was 150,953,984 bytes. These are observed
costs on this machine, not throughput guarantees.

At 128 evaluations per product, full eight-hour all-product solar workloads
took 39.47–151.88 seconds across ordinary, polar, near-axis tangent and
early/late epochs. They intentionally retain unresolved paths/topology at
that allocation. The noncentral 2014 width is not applicable, independently
of unresolved occurrence. Complete frozen arrangements use the larger corpus
allocation above. Both full lunar bundles took about 148–152 seconds during
overlapping validation work.

Timing begins after fixture reader initialization and, for the 92 cases,
event identification. Initial kernel content hashing is excluded. OS process
peak working set is cumulative per worker and includes mapped/native resident
pages; it is not a per-request heap allocation or a sum across workers.
Some corpus, compatibility and HTTP work overlapped; a single diagnostic stack
sample was taken during the earlier lunar probe. The performance receipt
records these conditions and per-case costs. There is no synchronous API
latency, total-memory, cancellation or catalog-throughput guarantee.

## Source and readiness limits

The original checkout's Python 3.14.8 and DE441 content identity
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`
were used with downloads disabled and strict known-issue expiry checking.
The installed CPython 3.14 native extension imports successfully and retains
SHA256 `b5a215bc9f1f749bd08ce2fe4d7bc449f564122f410ba1fb8e25569a56f207ba`.
No C++ source changed and no native rebuild was needed.

Scoped Ruff, all eight engine-file docstring preflights and changed-line
whitespace checks pass. Eleven pre-existing `eclipse.py` lint findings match
the Stage 5 baseline exactly; no new finding is admitted. The Python source
freeze records 17 files. Only the lunar adapter changed after the solar
corpus/profile checks; its corrected behavior is covered by the later
contract, full-window and transport checks.

Machine receipts retain all source hashes, exact width endpoints, test XML,
per-case telemetry, the corrected earlier failure, transport responses and a
source archive based on Stage 5. They are saved in the task's outputs folder.

No physical accuracy, live mapped-file lifetime, rounded native execution,
IAU p_A correction, complete exact vector path, solar NASA width convention
or final-catalog readiness is asserted. Stage 7 still requires final-source
catalog regeneration, row-level comparisons and individual discrepancy
dispositions. Stage 6 acceptance establishes the explicit bounded public
contract and compatibility gate; retained scientific unknowns remain visible.
