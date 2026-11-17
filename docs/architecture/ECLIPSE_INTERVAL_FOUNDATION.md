# Eclipse exact-rational interval foundation

`moira._eclipse_interval` and `moira._eclipse_interval_roots` are private
building blocks for future bounded eclipse searches. They do not by themselves
certify an ephemeris evaluation, a light-time solution, a time-scale mapping,
an eclipse classification, or physical accuracy. Existing eclipse and API
behavior does not automatically become exhaustive by importing them.

## Arithmetic contract

`RationalInterval` stores finite, ordered, closed endpoints as exact
`fractions.Fraction` values. Python `float` inputs are the exact represented
binary64 values, not their intended decimal literals. Boolean and nonfinite
inputs are rejected. Addition, subtraction, multiplication, integer powers,
division with a denominator excluding zero, and square ranges use exact
rational operations.

Square-root bounds use integer square root of a scaled rational; endpoint
inequalities follow from integer comparisons. `quantize_outward` floors and
ceils on an absolute dyadic grid, preserving enclosure while allowing callers
to cap denominator growth. Conversion to binary64 checks the resulting float
endpoints against the original exact rationals and fails if a finite enclosing
pair is unavailable. Explicit input, exponent and precision limits raise
`IntervalBudgetError`, rather than manufacturing a narrower result.

`moira._eclipse_interval_elementary.sin_cos_enclosure` supplies rational
enclosures of mathematical sine and cosine for a rational radian interval,
without using platform `libm`. It repeatedly halves the full argument until
`|x| <= 1`, encloses Taylor polynomials with derivative-bounded Lagrange
remainders, and reverses the halvings using exact double-angle identities.
Intermediate dyadic quantization only widens intervals. Results are clipped
to the universally valid range `[-1, 1]`; a wide domain or dependency widening
may legitimately produce that full range. Work, precision, halvings and Taylor
terms are bounded, with exhaustion reported as `IntervalBudgetError`. The
requested precision names an output dyadic grid, not a guaranteed enclosure
width. This mathematical function bound does not automatically enclose a
particular platform's rounded implementation.

## Root partition contract

`isolate_roots` partitions one finite closed rational domain. The provider
must supply an interval that contains the values of **one stated function**
throughout every requested cell. When the caller asserts continuity, an
endpoint sign change proves a root by the intermediate value theorem. A point
enclosure exactly `[0, 0]` also proves a root at that point. An additional
valid derivative enclosure excluding zero on the entire cell proves that
witnessed root is unique. These conclusions are conditional on the caller's
inclusion, continuity, and derivative contracts; the generic solver cannot
verify an arbitrary callback's honesty or its mathematical model.

Each covering cell is `excluded`, `unique`, `present`, or `unresolved`.
Exclusion follows when the function-value enclosure excludes zero, or when
continuity and a derivative enclosure strictly excluding zero establish
monotonicity and both endpoint enclosures have the same strict sign. An
endpoint enclosure containing zero is not a strict-sign witness. `present`
establishes a root but not uniqueness. Unknown, singular or unsupported domains
must use `EnclosureUnavailable`; a resource limit raises `IntervalBudgetError`.
The partitioner turns only those named failures and its own evaluation-budget
exhaustion into unresolved cells; unexpected exceptions propagate.

Closed neighboring cells share endpoints. Unique cells on both sides of an
exact shared root may refer to the same root; the partition does not claim
deduplicated root identities or counts. `complete` reports that each cell has
an exclusion or a unique-root proof under the declared model. Separately,
`resolution_reached` checks the requested width of every non-excluded cell;
a narrow unresolved cell does not imply completion or root existence, and a
unique coarse cell can be complete without meeting requested time resolution.

Domain `unit` and `time_scale` are explicit metadata. No unit or clock
conversion is performed, and an unresolved region cannot safely be skipped
by an exhaustive nearest-event search.

The conditional native type-2 adapter checks the full native-handle catalog
before relying on a selected descriptor's coverage. Native lookup uses the
first entry with matching payload addresses and type, so conflicting raw
coverage among reused payload keys is rejected even across body pairs. If no
handle is present the adapter checks the reader's catalog under the explicit
unchanged-file premise. These checks do not attest source or binary identity,
reader lifetime, clock convergence, or general route totality.

## Continuous reference phase

`_eclipse_continuous_lunar_phase` composes the generic partitioner with a
separate exact-real reference model built from copied type-2 SPK records.
For a caller-supplied fixed pole it isolates zeros of the oriented projected
Sun-Moon determinant, using the projected dot product to distinguish the
requested new or full phase. The model uses a geometric Moon and ten
retarded-Sun iterations, with a continuous reference TT/TDB clock. It
returns unresolved cells when its continuity, derivative, branch or budget
obligations are unavailable. Source-record and descriptor seams are refused
rather than assumed continuous.

The result is conditional on this specific mathematical model and its frozen
inputs. It does not attest the loaded kernel, bound the legacy evaluator, use
the date-dependent ecliptic plane, identify an eclipse, or certify physical
accuracy. The focused real-DE441 tests exercise one new and one full phase;
they do not establish full-domain completeness.

## Conditional finite-cone serving margin

`_eclipse_lunar_cone_bounds` composes the conditional retarded-Sun and
geometric-Moon split-vector bounds with interval evaluation of the complete
binary64 geometry calculation in `spherical_cone_shadow`. Its assumptions
include unchanged source and constants, represented finite input vectors,
round-to-nearest with gradual underflow, correctly rounded square root,
finite `atan2` on finite inputs, and at-most-one-ulp `hypot` and `fsum`
errors. The `hypot` and `fsum` enclosures
must allow for the change in representable spacing at powers of two. The
rounded downstream-domain and penumbral-nappe branches and one umbral branch
must be established, with every final margin finite, or the adapter declines
the interval. Geometry success is conditional on those stated premises;
it does not establish ephemeris-route or time-conversion success.

The result applies to successful represented TT inputs on the split route;
it does not prove that all inputs succeed, cover the legacy fallback or UT1,
or establish physical accuracy. A margin containing zero is inconclusive.
The event finder's contact-coalescence tolerance is a separate policy: a
strictly negative margin by itself is not an event-search absence certificate,
and no event or contact classification is made by this adapter.

An opt-in sampled route runs the existing `_eclipse_body_pair` split code
against the copied type-2 records already used by the vector bounds. The
native evaluator applies its ordinary descriptor, record-index, normalized
time and file-order position kernel to those copies. The adapter checks the
selected descriptor, frame, source identity, metadata and copied-record
digest, and fails closed on mismatch or missing native capability. DE441
point samples matched the ordinary mapped route bit-for-bit; that sampling is
not proof of equality over a domain. The source identity is the reader's
open-time identity, not an attestation of its live mapping or loaded binary.
This opt-in sample is not wired into the public eclipse search and does not
establish interval coverage, converter totality or absence of an eclipse.
The snapshot factory can prevalidate and retain all fourteen native evaluator
operations and copied coefficient tuples before sampling. Evaluating that
frozen scope no longer rereads live descriptors or mapped records; tests also
exercise evaluation after the reader is closed and after its source identity
changes. Those tests validate the copied execution path, not the integrity of
the source at freeze time or equality to all live evaluations. The scope and
its bound receipts remain replaceable Python objects and are not certificates.

The default split-vector delay bound uses only the guarded coarse norm range.
An optional tighter mode bounds the serving norm's three squares, two
left-associated additions and square root, then its delay division. That mode
adds explicit, unattested premises that binary64 `x**2` and `sqrt` are
correctly rounded. It cannot be used as though those properties were proved
for an arbitrary Python runtime.

For every retained lunar Sun and solar Sun/Moon light-time iteration, the
serving-vector receipts include the input emission-delay enclosure and the
next-delay enclosure. Their exact signed difference encloses the difference
of the represented delay values; a separately outward-rounded difference
encloses the binary64 subtraction used by the source's early-stop test.
These differences inherit all route, source and arithmetic premises of their
parent receipts and may be wide. They describe the residual at the delay used
to calculate that iteration's returned vector. The source returns the *next*
delay, so this is not a residual at that returned delay; obtaining that value
may require an extra emission evaluation. Neither difference proves a fixed
point, a fixed-point error bound, physical precision or search completeness.

`_eclipse_lunar_totality` records conditional obligations over an interval of
represented TT inputs. It checks the split-clock convergence receipt using a
bounded first-part interval, first with a zero reception offset and then with
each of the ten bounded negative Sun-emission delays. It also checks the
initial and ten possible returned Sun vector norms and their source guards.
These results retain the clock and floating-point premises above. The overall
route status remains unresolved because live source identity, native build,
and route totality have not been established. The receipt does not certify
eclipse absence.

The reference normalizes copied coefficient words with uniform `INIT/INTLEN`.
It does not read or verify the per-record `MID/RADIUS` words which NAIF's
[SPK Required Reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html)
uses to define type-2 polynomial normalization. A separate test checks these
words and all coefficients for twelve selected DE441 records at three epochs;
it is a sampled on-disk witness, not an attestation of a live mapped kernel
or all records.

The opt-in continuous Sun light-time certificate bounds the Sun emission-route
speed and reference TT/TDB clock derivative across the frozen horizon. It
requires a contraction factor `q < 1` and an enclosed delay-map image within
`[0, horizon]`. Those premises prove a unique real fixed point. With ten Sun
emission updates from zero delay, the last emission delay's residual is at
most `q**10 * horizon` and its fixed-point error at most that residual divided
by `1-q`; the componentwise Sun vector error is bounded by `c*q` times that
delay error. This concerns the explicitly defined uniform-metadata reference
and does not bound binary64 legacy iterations, their stopping behavior, or
physical model uncertainty.

The conditional solar-serving vector boxes cover the retarded Sun and Moon
only when the guarded split route is actually used with the declared source,
kernel, and arithmetic premises. The production pair selector can fall back
to a legacy single-part route when split evaluation is unsupported. The
solar-serving vector receipt neither rules out that fallback nor encloses its
output. An opt-in adapter can enclose the rounded axis normalization,
projection and distance for successful source calls when the caller explicitly
assumes correctly rounded square root and the documented absolute-error bound
for three-term Python ``sum``. It rejects a box crossing the forward-ray branch
and does not attest those assumptions, source success or the live reader. A
separate conditional ERA bound encloses the Earth Rotation Angle for the
represented UT1 box. Conditional bounds also cover the served polar-motion
table and matrix, IAU 2000A nutation amplitudes, and GAST under their stated
source and arithmetic premises.

The opt-in Earth-fixed vector composition combines the actual served solar
axis, FW precession, the bounded nutation and GAST, and the transposed polar
matrix in the same order as `_earth_fixed_solar_shadow`. It encloses selected
ITRF axis, Sun, fundamental-plane, east and north vectors for **successful**
source evaluations on independent represented UT1 and TT boxes. It applies
only to the FW branch (within +/-50 centuries), and requires unchanged source,
tables and native build; binary64 and libm assumptions are explicit. It does
not prove that the supplied UT1 and TT values correspond, that the live or
split ephemeris routes succeed, or that their source and arithmetic premises
hold. It also does not enclose every terrestrial shadow field, certify eclipse
occurrence, establish a complete event path, or bound physical accuracy. For a
2024 eclipse +/-5-second sample, the first two component widths of the bounded
ITRF fundamental-plane point were about 850-910 km; these are numerical enclosures,
not a claim of physical error or sufficiently narrow path limits.

## What remains for an eclipse certificate

An astronomical provider must independently validate SPK segment and record
routing, all selected vector-route legs, split TT/TDB and UT1 conversion,
retarded-emission iteration and numeric roundoff, model-specific eclipse
geometry, any needed elementary functions and their interval extensions, and
the complete advertised search domain. Unsupported readers, missing ephemeris
coverage, uncertain discontinuities and exhausted budgets cannot certify
absence. A mathematical enclosure for frozen SPK coefficients is distinct
from an enclosure of Moira's serving floating-point evaluator and from a
physical error bound. The proposed lunar exclusion and its proof obligations
are documented in `LUNAR_SHADOW_ABSENCE_CERTIFICATE_RESEARCH.md`.

Focused regressions live in `tests/unit/test_eclipse_interval.py`,
`tests/unit/test_eclipse_interval_roots.py`, and
`tests/unit/test_eclipse_interval_elementary.py`. They cover exact arithmetic and
dyadic/square-root bounds, domain and resource errors, sample analytic roots,
short positive intervals, tangencies, endpoint ownership, discontinuity,
budget exhaustion and full partition coverage. Trigonometric checks include
independent rational Machin-series bounds for π and direct high-precision
decimal Taylor samples; sampled agreement supplements the analytic enclosure
argument and is not a substitute for it.
