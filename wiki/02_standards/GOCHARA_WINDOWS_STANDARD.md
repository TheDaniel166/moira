# Bounded Gochar windows standard

Date: 11 October 2026. Owner: `moira/gochara_windows.py`. The implementation
and its acceptance evidence are recorded in the
[validation receipt](../03_validation/GOCHARA_WINDOWS_VALIDATION_2026-10-11.md).
This is the window extension of VED-017, alongside the existing
[dated snapshot](GOCHARA_DATE_DERIVED_STANDARD.md) and
[snapshot doctrine](GOCHARA_BACKEND_STANDARD.md).

## Admitted product

Return the time partition of the existing Phaladeepika/Sastri seven-classical
Gochar profile relative to the natal Moon. Every request searches Sun, Moon,
Mars, Mercury, Jupiter, Venus and Saturn, including potential blockers that
are absent from the requested presentation subjects. The existing evaluator
owns favorable houses, historical indications, all directed Vedha witnesses,
exemptions, baseline-only omission and raw BAV testimony.

The twelve named ayanamsas are Lahiri, Fagan-Bradley, Krishnamurti, Raman,
Yukteshwar, Djwhal Khul, True Chitrapaksha, De Luce, Aldebaran (15 Tau),
True Revati, True Pushya and True Mula. Each is evaluated at the required TT
epoch. The five live-star systems resolve the sovereign anchor record directly;
missing anchors never fall back to a polynomial. The frame/anchor model is
the existing dated Gochar model, not a new interpretation of these traditions.

Optional raw natal BAV derives once from the same seven natal signs and Lagna,
using the existing unreduced Raman encoding. Birth location is required exactly
when this mode is selected. State rows select the subject's own BAV by absolute
transit sign. No threshold, score, probability or strength override is added.

VED-018/019 remain separate: alternative source tables, nodes, other reference
points, counter-Vedha, thirds/halves activation, Murthi, dasha/dignity modifiers,
nakshatra/chakra techniques and remedies are not selected by this product.
The [research checkpoint](../06_roadmap/VEDIC_GOCHAR_WINDOWS_SOURCE_RESEARCH_2026-10-11.md)
preserves their source differences and locators.

## Engine and REST

```python
from moira import Moira, GocharaWindowSearchPolicy

m = Moira()
result = m.gochara_windows(
    2451545.0, 2460967.0, 2460968.0,
    subjects=("Jupiter",),
    search_policy=GocharaWindowSearchPolicy(require_resolved=True),
)
assert result.coverage.domain_accounted
assert len(result.coverage.participants) == 7
assert any(e.planet == "Jupiter" and e.direction == 1 for e in result.events)
assert result.resolve_sample(0).transit == result.samples[0].epoch
```

`gochara_windows(natal_jd_ut1, start_jd_ut1, end_jd_ut1, *, birth_location=None,
policy=None, search_policy=None, subjects=None, reader=None)` is the standalone
entry. `gochara_windows_for_datetimes(natal_dt, start_dt, end_dt, **kwargs)`
accepts three aware civil instants. Both are also instance-reader-bound `Moira`
methods. `gochara_window_capabilities()` is available through the curated root,
facade and Vedic surfaces and as a static facade method.

| Method | Route | Contract |
| --- | --- | --- |
| POST | `/v1/gochara/windows/from-epochs` | Three UT1 JDs, existing date policy, separate search policy, optional birth location and subjects. |
| POST | `/v1/gochara/windows/from-datetimes` | Three offset-aware ISO datetime strings; convert each exactly once using the existing UTC/UT1 owner. |
| GET | `/v1/gochara/windows/capabilities` | Profiles, systems, nominal domain, limits, endpoint and uncertainty semantics; no kernel/anchor probe. |

Example epoch request:

```json
{
  "natal_jd_ut1": 2451545.0,
  "start_jd_ut1": 2460967.0,
  "end_jd_ut1": 2460968.0,
  "subjects": ["Jupiter"],
  "policy": {"ayanamsa_system": "Lahiri"},
  "search_policy": {"boundary_tolerance_seconds": 1.0, "require_resolved": true}
}
```

Unknown fields, boolean/nonfinite numbers, numeric strings, invalid/duplicate
subjects, contradictory BAV policy, zero/reversed duration and naive or
numeric civil instants fail before astronomical evaluation. Result schema is
`moira.gochara.windows.v1`. Pydantic declares every nested field, validates the
result, and REST sends the engine's exact canonical JSON bytes. The base engine
uses standard-library serialization and does not import Pydantic.

The result's selected options include `forecast.dated_events`; the dated and
supplied-position snapshot policies do not select that option. Catalogue
admission describes this bounded window product, not an expansion of snapshot
claims. Eight Gochar routes are now discoverable under `classical-vedic`.

## Domain, clocks and resources

Nominal transit certification is UT1 JD `[2415020.5, 2488434.5)`, corresponding
to 1900-01-01 through, but excluding, 2101-01-01. The actual interval must also
fit converted TT frame support, required retarded SPK epochs, reader identity
and anchor support. The clock adapter derives safe UT1/TT intersection endpoints
and returns them in resource receipts. Near either nominal edge, nominal UT1
admission alone does not guarantee support. Natal epochs retain the dated
compositor's point-domain rules and may precede 1900.

One request pins a borrowed pool's reader order, owns its point/interval caches
and work meter, and restores reader context on every exit. It never closes a
caller-owned reader. In particular, prewarmed serving-reader point caches are
not inherited by the proxy: their stored readers could bypass request metering.
Clock/EOP and anchor identities are checked for change before returning.
Receipts retain clock/anchor input hashes, the anchor record, serving time
identity, SPK source hashes and cache occupancy/hit/miss measurements.

## Partition, evidence and numerical meaning

The requested interval is closed. Each instant belongs to exactly one region:

| Kind | Meaning |
| --- | --- |
| `certain` | Seven constant signs and their discrete doctrine state, justified by exclusion evidence; one individually dated astronomical sample. |
| `boundary_band` | Closed event-time enclosure with accepted classification/order and requested width. It has no asserted constant state. |
| `unresolved_band` | Closed interval where count, contact, order, width, source continuity or another named dependency remains unresolved. Reasons and individual events survive merging. |

Neighboring certain regions exclude the endpoints owned by a closed band.
Request-edge clipping is retained. Overlapping distinct events share a band
and preserve `event_order_unresolved`; their order is not guessed. Subject
views retain references to this atomic partition, including blocker-only bands;
this admission does not provide a separate coalescing/stitching API.

An open gap with no representable binary64 interior epoch is retained with
`no_representable_interior_witness`; it cannot acquire a sample on an excluded
band endpoint. A certain region touching a request edge may instead use that
owned endpoint as its witness. Individual event evidence survives either case.

The existing point rule remains authoritative: exactly 30 degrees is Taurus,
including on a retrograde pass. A tangent may have different singleton and
neighboring states. The solver conservatively retains possible contacts and
does not manufacture an exact singleton from a rounded time. The event schema
can distinguish contact/model-seam records; this implementation establishes
crossings where proved and otherwise retains possible contacts or reasoned
unresolved seam regions. It does not assert exact contact existence.

All twelve sign rays for all seven bodies are searched. Interval value
exclusion and necessary Newton contraction account for omitted domains;
adaptive subdivision retains possible roots and source/record seams. The
initial one-day subdivision seed is not a sampling-based completeness proof.
Periodic targets are rebased after both subdivision and coarse-to-precise
evaluation so a changed angular lift cannot erase a crossing.

The arithmetic certificate is conditional on RN binary64 arithmetic with
gradual underflow and transcendental error at most four ulps. Differential
arithmetic encloses a family of continuous surrogate branches, each holding
its rounding parameters fixed over the complete interval. Light-time stop
branches are retained as a family. Clock/record seams disable continuous
contraction where continuity cannot be established.

**A crossing count of one means one crossing per continuous surrogate branch
under this declared model.** It is not a count of sub-ulp sign flips of the
discontinuous rounded program, nor a proof of exact physical event time.
Endpoint brackets use the full interval's center and derivative enclosures;
fresh point calls cannot shrink away its branch/rounding uncertainty to claim
existence. Definite derivative sign proves direction and uniqueness within
each branch; the retained time band covers the branch family.

Existence/count, direction, event order and time width are separate facts.
A proved crossing can still be qualified by
`boundary_width_exceeds_requested_tolerance`. Ordinary mode preserves it in an
unresolved band; strict mode rejects the result. A one-second numerical target
does not imply one-second agreement with external astronomy.

`coverage.domain_accounted` reports full partition ownership.
`coverage.exclusion_certified` means discarded domains have the declared
exclusion evidence; it does not mean no uncertainty exists.
`coverage.events_resolved` additionally requires no unresolved region.
Participant and doctrine coverage are separate fields. Degrees, clocks and
ayanamsa values remain time-dependent and appear only in dated samples.

Frozen result construction rechecks types, IDs, ordering, references, source
testimony, event evidence, sample signs, exclusions and partition ownership.
Natal integrity is checked without repeating BAV. These are consistency checks,
not cryptographic authentication of someone else's fabricated kernel result.

## Work, output and failure law

The default boundary target is 1 second; admitted targets are 0.01–60 seconds,
subject to the representability floor. Callers can lower each positive integer
limit, but cannot exceed these finite ceilings:

| Limit | Maximum/default |
| --- | ---: |
| Requested days | 366 |
| Evaluations | 2,000,000 |
| Reader calls | 20,000,000 |
| Root iterations | 500,000 |
| Subdivisions | 500,000 |
| Retained event candidates | 8,192 |
| Cells | 16,384 |
| Dated samples | 16,384 |
| Evidence records/candidates | 500,000 |
| Canonical UTF-8 JSON bytes | 32,000,000 |

The evaluation counter includes isolation visits and evaluated astronomy;
reader calls count actual serving operations. Cached work is not recharged.
Candidate counts can exceed merged events. Evidence includes retained unresolved
candidates as well as exclusion records. Output records are charged before
retention, then the complete compact UTF-8 encoding is checked, including civil
receipts. Its own byte count is omitted from `work` to avoid self-reference.

These ceilings retain headroom above the measured annual corpus (about 40,000
evaluations, 210,000 reader calls, 210 samples and 5 MB), including tighter
targets and difficult geometry; they are not a latency SLA. Every request is
still bounded by the earliest exhausted cap. The exact benchmark matrix and
peak resident-memory measurements are in the validation receipt. Annual calls
are synchronous work taking minutes on the measured host. Proxy/client timeouts
do not cancel a running Python worker; it finishes within its work limits and
restores its context. No asynchronous job service is implied.

| Outcome | HTTP | Code |
| --- | ---: | --- |
| Malformed input, policy contradiction or nonunique Lagna | 422 | `validation_error` |
| Outside serving ephemeris coverage | 422 | `gochara_date_outside_coverage` |
| Outside effective certification domain | 422 | `gochara_window_outside_certified_domain` |
| Duration/work/output exhaustion | 422 | `gochara_window_budget_exceeded` |
| Unresolved result requested in strict mode | 422 | `gochara_window_unresolved` |
| Required kernel/time/anchor resource unavailable | 503 | `gochara_resource_unavailable` |

Gochar window error details have a dedicated typed schema retaining numeric
counts/bounds and reason lists. A budget failure discards the incomplete result;
no partial 200 or silent truncation is permitted. Ordinary unresolved results
return 200 with their evidence. Unexpected failures retain the existing
sanitized server-error behavior.

## Ownership and preservation

`_event_search` owns shared intervals, roundoff, differentials, frame/clock and
serving-astronomy enclosures, isolation, budgets and reader loans. Original
marriage module paths alias these owners for import/monkeypatch compatibility;
marriage policy, horizons, history and election composition stay in their
existing owners. No native formula, dependency, source table, snapshot default,
website or Urania flow changes in this admission. The focused validation
includes shared-owner regressions and native-record parity; it is not a claim
that the whole repository was tested or that astrology's predictive validity
was established. Publication, version release and deployment are separate.
