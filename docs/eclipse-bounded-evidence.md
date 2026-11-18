# Bounded eclipse evidence v1

Stage 6 adds opt-in immutable evidence contracts. Existing event searches,
dataclasses, JSON responses, native/canon policy selectors and legacy
instantaneous support widths keep their established interfaces.

```python
from moira.eclipse import EclipseCalculator
from moira.eclipse_evidence import serialize_eclipse_evidence

calculator = EclipseCalculator(reader=reader)
bundle = calculator.solar_evidence(
    2457987.267724502,
    offset_days=(-1/6, 1/6),
    products=('occurrence', 'geographic_width'),
    max_evaluations=256,
)
wire = serialize_eclipse_evidence(bundle)
```

The equivalent additive routes are `POST /v1/eclipses/solar/bounded-evidence`
and `POST /v1/eclipses/lunar/bounded-evidence`. OpenAPI defines the complete
recursive response, including every product's independent status. Requests
are strict: unknown fields, duplicate products, non-finite numbers and
incompatible model options are rejected. These calls inspect the supplied
epoch/domain; they do not select an eclipse or certify a nearest event.

## Domains and products

Solar requests use a numeric `jd_ut1` anchor and two closed `offset_days`
including zero, spanning at most one day. This supports BCE dates without a
Python datetime or a UTC conversion. Lunar requests instead use `jd_tt` and
allow a TT interval of at most 34 days. The represented binary64 anchor is
part of the model input. Offsets, bounds and algebraic isolators retain exact
rational endpoint strings; numeric display endpoints enclose those strings.

| Product | Domain and meaning |
| --- | --- |
| Solar occurrence | Requested UT1 interval × complete zero-elevation WGS84 surface. Partial-disc occurrence requires a common visible geometric ray; a strict witness establishes presence without excluding the complement. |
| Solar central_path | Requested UT1 interval. Legal axis intervals, phase sequence and transition brackets; a complete event sequence/subtype requires `event_interval_enclosed`. A clipped complete window is only `bounded`. |
| Solar surface_topology | Instantaneous anchor. Exact cone/ellipsoid/forward-plane/Sun-centre-horizon arrangement of the frozen native coefficient family. Components count cone intersections, not filled regions. |
| Solar swept_region | Requested UT1 interval. Certified inner/outer mesh of the visible central footprint's spatial union, retaining every unresolved rectangle and its complete time ledger. Sun-centre horizon; no exact boundary curve or Hausdorff error claim. |
| Solar geographic_width | Instantaneous anchor. `WGS84_central_plane_cross_track_arc_length`, using the near-axis reference and differentiated local track. Two limit bands, conditioning and interval span are explicit. A proven unavailable near-axis reference is `not_applicable`, independently of event presence. |
| Lunar occurrence | Complete requested TT interval for the selected geometric-Moon shadow policy. |
| Lunar contacts | Three separate penumbral, umbral and total contact root partitions. Zero contacts inside an eclipse window is compatible with proved occurrence. Shared endpoint cells are not deduplicated contact identities. |
| Lunar extrema | All retained source critical-set domains, including unresolved regions and source-join exclusions. This does not imply a certified nearest event or a complete lunation. |

Every response includes all products in stable canonical order. Unselected
products are `not_computed`. `configuration`, source/clock domains, model ID,
horizon policy, exact bounds, components, topology, budget and cause travel
with each result. `None` quantities retain `not_computed`, distinct from zero.

## Status and resource semantics

`proved` means the stated model-specific positive/completeness proposition
passed its proof checks. `bounded` retains a valid enclosure whose precision
or event completeness can be limited. `evaluated_zero` requires complete
exclusion on the stated domain for that product. `not_applicable` means the
product's required reference is proved unavailable. `not_computed`,
`unsupported`, `unresolved` and `error` respectively mean unrequested work,
unsupported source/domain, retained uncertainty, and an independent runtime
failure. Missing/closed providers and unsupported coverage never become
negative event findings. An error in one product does not erase another.

`coverage_complete`, `precision_met`, `event_interval_enclosed` and
`full_surface_domain_retained` answer separate questions. For example,
occurrence can be proved by one strict witness while its complement stays
unresolved. A width can be bounded while `precision_met` is false.

`max_evaluations` allocates 0–4096 evaluations to **each** selected product;
units differ and are reported (root callbacks, section predicates, Sturm
queries, etc.). Zero budget retains uncertainty without source preparation.
Initialization, copied records, provider calls and native hint evaluations
are disclosed separately in `preparation`. Budgets do not bound all wall
time, allocation or internal arithmetic work. Time tolerance is 0.001–86400
seconds; requested width interval span is positive and at most 100 km.
If an exception interrupts a product before a trustworthy counter returns,
`budget.used` is null rather than an invented zero.

Public evidence uses deterministic evaluation limits without a wall-clock
cutoff. Existing private helpers retain their default 120-second cutoff;
`max_seconds=None` explicitly selects evaluation-only mode. Timings and OS
process peak working sets belong in benchmark receipts, never deterministic
evidence payloads. The synchronous API has no streaming, cancellation or
throughput guarantee; use explicit budgets appropriate to the workload.

Acceptance measurements include 39–152-second all-product solar calls at
128 evaluations per product and roughly 148–152-second full lunar bundles
during overlapping validation. The 92 width/topology requests had a median
wall time of 16.13 seconds across four workers. Reader initialization and
initial kernel hashing are outside those request timings. These observations
do not establish an API latency or memory limit.

A direct supported `SpkReader` may be borrowed. A `KernelPool` is admitted
under a read lease only when exactly one direct planetary spine is present,
all pair inventories are inspectable and supplemental readers cannot shadow
required targets. Unknown or competing routes are `unsupported`; there is
no silent fallback to another global reader. The pinned pool generation is
reported. The request does not close or reopen the borrowed reader.

## Scientific scope and compatibility

Continuous solar products use the accepted current-policy real reference:
explicit TT/TDB clock mapping, finite ten-step retarded Sun/Moon iteration,
current nutation/Fukushima–Williams policy and bounded Earth orientation.
The existing p_A polynomial discrepancy remains visible and unchanged;
this profile does not claim IAU conformance. Frozen native topology is a
different conditional real affine family, with its input values and native
snapshot TT exposed. It does not certify every native floating operation.

Lunar `danjon_angular` and `static_finite_cone` are explicitly geometric-Moon
reference policies. `earth_radius_scale` applies only to the finite-cone
policy. They are not aliases for legacy `native`, `nasa_compat` or
`nasa_canon`; those stay on their established routes with apparent/geometric
and clock distinctions preserved. No solar NASA-compatible width is claimed.

Source metadata separates reader-open kernel identity, copied raw-record
word verification and table hashes. It does not attest the live mapped
file's entire lifetime, physical accuracy or native execution. Precision is
an enclosure span in the named mathematical model, not physical uncertainty.
Legacy widths withheld in the 92 one-limit cases remain withheld. Numerical
strict-maximum selection, inclusive ranges and local visible-search semantics
continue to use the corrected existing core selector; no new search model
is silently substituted by these evidence routes.

See the Stage 3–5 acceptance documents for the underlying supported-domain
proofs. Stage 6 integration evidence does not replace Stage 7's final-source
catalog regeneration, row-level comparisons and individual dispute ledger.
