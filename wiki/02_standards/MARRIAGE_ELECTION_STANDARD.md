# Marriage election composition standard

**Date:** 10 October 2026. **Status:** selected profile admitted locally.
The selected scope is defined by the [approved plan](../06_roadmap/VEDIC_MARRIAGE_ELECTION_IMPLEMENTATION_PLAN_2026-10-10.md)
and [source research](../06_roadmap/VEDIC_MARRIAGE_ELECTION_SOURCE_RESEARCH_2026-10-10.md).
The catalogue reports `source_scoped_public`; the
[executed validation receipt](../03_validation/MARRIAGE_ELECTION_VALIDATION_2026-10-10.md)
records the completed gates and their precise evidence scope. Publication and
release are separate from local admission.

## 1. Owned object and public surface

The object is the source-selected suitability of a declared ritual anchor
instant. `MarriageElectionPolicy` requires a nonempty `ritual_anchor` and an
explicit `regional_tradition`. The ordinary authority is MC, Ramlal Avasthi,
2004; personal assessment and Godhuli composition are independently visible.
Lahiri, apparent geocentric true ecliptic of date and true geometric nodes
are the admitted common coordinate basis. Other schools remain catalogue
research entries and reject as executable profile selectors.

`assess_marriage_election` accepts immutable raw evidence, checks its internal
relations and performs no resource discovery. Its provenance remains
`caller_supplied_conditional_on_evidence`. Positions, solar parents, lunar
month, full phase occurrences, ingresses, historical cells and apparition
witnesses are transported without accepting caller-supplied verdicts.

`marriage_election_for_datetime` and `marriage_election_windows` build these
same inputs from one borrowed serving reader. A pool is leased with its
reader order pinned for the entire operation. Its owner retains lifetime
control. Validation precedes resource acquisition; resource, coverage and
deterministic budget errors remain distinct.

The facade and curated Python exports mirror the engine. REST has four
operations at `/v1/muhurta/marriage/{catalogue,direct,datetime,windows}`;
catalogue is GET and the other three are POST. Requests reject extra fields,
unsupported selectors, boolean/string numeric coercion, nonfinite coordinates,
contradictory witnesses and invalid civil instants. The serializer projects
engine results and owns no astronomical or doctrinal decisions.

## 2. Decisions and finite source coverage

Every required family is enumerated in `_muhurta_marriage_manifest.py`, with
M01–M30 and F01–F09 coverage, source locus, formula, exact component profile,
clock/partition, transition dependencies, missing-input semantics, exception
targets and fixture paths. `_muhurta_marriage_sources.py` owns the separately
transcribed tables. The MC PDF fingerprint is
`9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777`.

Three independent result layers are retained: astronomical, personal and
requested composition. Any effective required restriction produces
`restricted`, even with incomplete evidence elsewhere. No established
restriction plus any required unknown produces `indeterminate`. A pass
requires complete required coverage. Unrequested personal assessment is
`not_requested`; it is never promoted to personal eligibility.

Each finding retains raw detection, applicability, evidence, exceptions,
effective restriction and completeness. Unknown exception prerequisites never
cancel a restriction. Advisory placement quality and the source's textual
100/200/100000 capacities do not subtract arbitrary software rows. MC92's
placement total below five is a separate required restriction.

Both ordinary and Godhuli findings remain visible when Godhuli is requested.
Godhuli retains personal, availability, calendar and ingress restrictions;
its finite exception set cannot expand when another detector is added.

## 3. Source interpretation worksheet

| Governing object | Selected mathematical interpretation |
| --- | --- |
| Wedding stars/tithi/Karana | Eleven MC55 stars, including Mula. Both pakshas prohibit tithis4/6/8/9/12/14; Krishna15 also prohibited. Vishti is prohibited; no additional MC Kinstughna veto was established. |
| Calendar | Physical ordinary amanta lunations under Vivaha13 precedence over general Samskara26. The twelve-month/sign table is a declared derivation, including Ashadha only in Gemini, Shukla1–10. |
| 28-star identity | Insert Abhijit at the exact rational interval `[830/3,2528/9)` degrees. Equal Abhijit subarcs are a Moira pada convention; other stars retain physical original padas. |
| Regional rules | User-selected Kuru/Bahlika Upagraha, Kalinga/Vanga Pata, Saurashtra/Shalva Latta or Dakshinatya Bana; geography does not infer a school. Universal vedha remains independent. |
| Occupancy history | MC58's unquantified past/future language becomes nearest previous/current/next complete27-star passages. Election Moon is excluded as its own occupancy afflictor by explicit Moira composition. Permanent benefics do not cause occupancy. Mercury association is evaluated at the historical event time. |
| Persistent piercing | Event-time malefic five/seven-line piercing persists until a full actual traversal of the affected unequal28-star by Moon. A fixed elapsed-month approximation is forbidden. Historical Moon remains a piercing cause. |
| Planet nature | The admitted BPHS3.11 verse phase/same-sign composition, rather than an unlabelled universal nature rule. Historical uncertain bands enclose every possible sign/pada and Moon phase; clear endpoint samples do not prove absence of an intervening cause. |
| Pata | Qualifying yoga END within the same complete Moon27 occurrence; repeated occurrence of the same star index is distinct. The selected solar-pada qualification remains explicit. |
| Ingress | MC79 cardinal solar ingress owns its sunrise date and adjacent solar dates; others use16ghati on either side. MC80's total ghatis are split symmetrically as a Moira convention, for both crossing directions. |
| Durmuhurta/Kulika | Complete daylight/night parents. MC52–54 weekday prohibitions apply to both fifteen-deity tables; Saturday's extra Kulika is the final night fifteenth. |
| Vishanadi/Yamaghanta | Explicit MC scaled start/fixed four-ghati width; fixed Gandanta widths. Yamaghanta Kala is a sixteenth of full daylight, distinct from MC64's adverse eighth. |
| Remedies | MC68 finite own/exalted luminaries subset; MC83 Lagna lord OR Jupiter aspect; MC88 component-specific weak afflictors; finite MC89–91 targets. MC90 Moon11 applies to Durmuhurta and malefic-owned allowed-sign D9 only, not last/movable D9. |
| Personal | Exactly two explicit bride/groom rule roles; independent natal Moon references, firstborn, birth month/tithi/star/Lagna facts. Missing facts remain unknown. Matching/compatibility and historical social prescriptions are excluded. |
| Godhuli | VV geometric half-ghati on each side of half setting, with selected MC99–101 qualifications. Thursday after/full setting and Saturday before/full setting remain; no calendar/ingress cancellation. |

The manifest enumerates exclusions individually, including MC93 predictions,
MC94 social variants, MC95 special historical marriage forms, preparatory
ceremonies and family ritual obligations. None is an unimplemented required
rule disguised as missing caller data.

## 4. SS-derived availability geometry

The SS IX object is degrees of sidereal rotation between the frozen solar and
planetary horizon crossings. The modern extension uses current apparent
geocentric RA/declination, preserving ecliptic latitude, under a common frame:

`H = acos(-tan(latitude) * tan(declination))`.

With signed nearest-branch `delta = RA_planet - RA_sun`, rising lead is
`-delta + H_planet - H_sun`; setting lag is `delta + H_planet - H_sun`.
RA branch cuts, tangent and circumpolar geometry cannot be bridged as roots.
This model includes neither atmosphere nor a prediction of observed first
visibility. It is not a literal historical SS ephemeris or longitude-orb
combustion. The source is Burgess1860 IX.1–11, PDF237–240, hash
`2eb5c967bb5363e4e5d3e8c9a0e51fc92855af3b6d023166dcc0526ec25b930b`.

Jupiter uses east appearance11 and west disappearance11 time-degrees. Venus
uses east appearance8/disappearance10 and west appearance10/disappearance8.
Each event retains directional crossing witnesses. Full adjacent event
context determines asta, balya, available, vriddha or uncertain; MC waiting
periods use declared elapsed UT1 shifts. Jupiter15/15; Venus east3/15 and
west10/5 days. Root brackets survive every shift and intersection.

`marriage_visibility_cases.json` holds independent analytic cases and source
thresholds. ERFA horizon-root construction is a separate geometry comparison.
Neither validates the complete marriage doctrine as an external oracle.

## 5. Numerical coverage and uncertainty

The verifier reads bounded Chebyshev record batches from the exact native
serving evaluator. It carries source identities, descriptor/record branches,
clock knots, apparent-place corrections, frames, solar observer geometry and
the canonical finite-TT-difference motion definition. It does not reopen a
kernel or estimate a proof bound from sampled velocities.

Interval value/derivative families cover all admitted branch choices.
Zero-free intervals are excluded by enclosures; possible-root boxes are
retained. Interval Newton uses the full domain's center hull. Periodic rays
are re-enumerated after subdivision so a changed angle lift cannot discard
the same physical boundary. Tangencies and paired crossings survive without
an endpoint sign change. A witnessed candidate only seeds a finite supporting
range; the entire range between enclosing events must then be certified.
Every contracted Newton cell is re-evaluated, including cells already below
the requested time tolerance: contraction alone does not establish a root.

Arithmetic certification is conditional on the named model
`binary64_RN_gradual_underflow_libm_4ulp.v1`: nearest rounding, gradual
underflow, no overflow, and the declared transcendental/remainder/power error
bound. This is not platform-independent formal verification. Source-derived
uniform guards cover native/Python evaluation schedules. Trigonometric range
enclosures include endpoints and every possible internal extremum using
interval pi. Initial clock/frame certificates cover 1900–2100 inclusive;
unsupported supporting epochs retain explicit numerical unavailability.

Receipts preserve requested limits, actual counters, achieved root-band
width, source/table/native hashes, pool generation and each supporting
certificate's domain and unresolved regions. Requested tolerance is not
silently substituted for a wider achieved bracket. A source-table change
during a request invalidates admission.

Windows retain all underlying cells, shared raw-evidence/finding registries
and nonzero uncertainty bands. Calendar and phase-owner brackets are both
retained. Full parents are solved before clipping; derived fixed/affine
exclusion edges are partitioned in a second pass. `.at(jd)` returns a
certified cell witness only outside unresolved bands. It does not fabricate
new epoch-specific positions at that query instant. A numerical gap cannot
produce an eligible interval.
Lagna unavailability at a midpoint is not a constancy proof over the window.
An uncertified seasonal subpolar-domain seam remains a numerical gap.

If an actual seed sample has undefined horizon geometry inside the required
adjacent-apparition parent, that availability component is unavailable. The
receipt retains its exact witness times and the incomplete parent domain;
there is no need to exhaust the root budget refining an undefined quantity.
A witnessed failure of the source quantity is sufficient to deny admission.
It is not sampled evidence of a zero-free interval. Undefined samples in the
unused discovery pad do not invalidate an otherwise supported parent.

## 6. Operational bounds and compatibility

Duration, supporting-history extent, evaluations, reader calls, transitions,
root iterations, historical cells, output cells and output bytes have separate
finite limits. Output size is checked while interning shared evidence and
again on the assembled result. Exhaustion raises a named budget error;
there is no truncated successful result. Defaults are calibrated against the
measured corpus in the validation receipt; hard maxima protect resources.
The catalogue exposes defaults, hard maxima, the minimum 65-day calendar
parent radius and the numerical epoch domain. REST preserves the named
budget envelope for both preflight and running-operation exhaustion.
Root work includes candidate bisection and adaptive apparition-seed calls,
even when those calls reuse cached positions.

The admitted finite bounds are:

| Work limit | Default | Hard maximum |
| --- | ---: | ---: |
| Requested duration, days | 7 | 31 |
| Supporting search radius, days | 2,048 | 4,096 |
| Evaluations | 300,000 | 400,000 |
| Reader calls | 2,000,000 | 4,000,000 |
| Root iterations | 100,000 | 200,000 |
| Transitions | 8,192 | 16,384 |
| Output cells | 2,048 | 4,096 |
| Historical cells | 4,096 | 4,096 |
| Conservatively accounted output bytes | 8,000,000 | 32,000,000 |

These are distinct operational outcomes:

- A completed, certified partition with no eligible intervals means that no
  returned cell passes the selected profile. Its restrictions remain visible.
- Missing source inputs or unavailable astronomical/numerical evidence retain
  explicit unknown findings and indeterminate cells. An empty eligible list
  alone does not establish a completed negative search.
- Exceeding a work or response-size limit raises `MarriageSearchBudgetError`
  (REST code `marriage_search_budget`) with the counter, limit and stage.
  It does not return a partially evaluated window list as success.

The accepted maximum duration is an input bound, not a guarantee that every
request of that duration fits the other limits. Supporting history extends
outside the requested interval and is reported separately. Full calculations
can take many minutes; deployments must allow an appropriate execution timeout
or deliberately choose smaller work limits. A transport timeout is not an
astronomical result. This package does not add a background-job service.

Legacy `get_muhurta_guidance_for_activity('marriage')` retains its mapping
shape but emits `DeprecationWarning`, corrects Mula and the eleven-star list,
and labels tithis as absolute zero-based 0–29. Its good/avoid sets are disjoint
and exhaustive. Call the new complete assessment for decisions; existing
sampled/scoring Muhurta products retain their own contracts.

## 7. Validation and lineage

Source arithmetic, serving-reader regression parity, primary geometric
comparison, uncertainty invariants and performance are separate evidence
classes. The selected package requires real HTTP/resource worked cases,
adversarial transitions, full affected Vedic regression coverage and final
documentation/discovery gates. Private source PDFs remain outside the repo.

The governing decomposition is Moira-owned: source finding, raw witness,
named exception, independent coverage, and certified half-open partition.
The verifier mirrors Moira's actual serving arithmetic only to bound that
product. No Swiss/JHora implementation structure, oracle-tuned thresholds or
new external runtime dependency is admitted. Native record access exposes
immutable coefficients/metadata, not a second ephemeris evaluator.
