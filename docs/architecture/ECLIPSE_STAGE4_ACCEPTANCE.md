# Stage 4: global occurrence and instantaneous constraint topology

**Status: accepted for the declared bounded products, 2026-11-17.**
All **240 distinct checks pass**, with no failures, errors or skips. The
92-case replay includes all 1,104 snapshots and 552 endpoint states for both
the cone and clipping-circle arrangements. Stage 5 has not begun. Changes
are local and uncommitted; no push was made.

## Supported mathematical products

Stage 4 supplies two separate private products. They do not replace a public
selector, API schema, published catalog, path width or event-wide boundary.

1. A closed **UT1 interval x full zero-elevation WGS84 ellipsoid** occurrence
   ledger. Its DE441 adapter uses the explicitly frozen continuous real
   current-policy lift established in Stage 3: the source UT1/TT clock,
   implicit real TT/TDB conversion, represented raw type-2 polynomials, ten
   finite reception light-time updates for both Sun and Moon, current
   nutation/precession coefficients, true-circle Earth rotation, and polar
   interpolation. No cone-axis or eclipse-season decision admits/discards
   a time cell. General vector bounds work away from conjunction.
2. A **complete instantaneous constraint arrangement** for exact frozen
   affine-cone coefficients: both cone/ellipsoid roots, all generator
   parameters, forward-plane cuts, Sun-centre horizon cuts, both signed
   nappes, periodic chart seams, repeated/close roots, contacts and apex
   collapse. It includes every open horizon/forward-circle arc with its
   cone/other-plane signs and shared cone-junction identities.

The first product uses the **same visible ray** above the local tangent
plane and inside both apparent discs. The second has the distinct
**Sun-centre horizon** convention inherited from the existing clipped-cone
diagnostic. These horizons are not interchangeable near sunrise/sunset.
There is no refraction or terrain. Foreground depth intervals must be
separated. Unsupported sources, unproved signs and exhausted finite budgets
remain bounded unknowns; they cannot become certified absence.

The snapshot theorem is about the exact real family defined by the captured
coefficients. It does not enclose every rounded native generator operation
or an evolving cone over a time interval. The time product separately bounds
model/time uncertainty. Neither product certifies physical ephemeris or
historical Delta-T accuracy. The existing current-policy p_A discrepancy
documented in Stage 3 remains explicit; this work does not attest IAU
conformance or silently change shared frame policy.

## Time and surface proof

The six signed cube-face charts and their exact ellipsoid/normal bounds are
described in `ECLIPSE_STAGE4_FOUNDATION.md`. Every closed child retains its
shared boundary. The new time cover uses breadth-first adaptive time/surface
subdivision. Each ledger cell names its exact time interval and surface chart;
an omitted chart means the entire six-chart surface. The whole requested
domain remains in the ledger after stopping, including after a positive
witness. Evaluation and cooperative wall-clock budgets are exposed; a single
already-running enclosure is not preempted by the wall-clock limit.

For geocentric vectors S,M and |P|<=a, parallax is at most asin(a/|V|).
For a cap with sine radius x, its Euclidean chord radius is

    c(x) = sqrt(2-2*sqrt(1-x*x)).

The unit-vector triangle inequality implies the necessary overlap condition

    |unit(S)-unit(M)| <= c(a/|S|)+c(a/|M|)
                         +c(Rs/(|S|-a))+c(Rm/(|M|-a)).

A strictly positive lower bound on left minus right excludes every surface
point throughout the time interval, without needing Earth orientation.
Otherwise existing joint cap/horizon inequalities bound individual patches.
Neither a midpoint miss nor a missing native shadow excludes a time box.
Hints from native sites and the existing floating cap solver carry no proof:
the exact surface point and candidate ray must pass all three strict rational
cap/horizon margins. An unsuccessful witness search stays unresolved.

The value-only source adapter uses independently implemented exact Clenshaw
centre values plus whole-record derivative bounds. From
[DLMF 18.9.21](https://dlmf.nist.gov/18.9.E21), T'_n=n U_(n-1), and the
finite trigonometric sum for U gives |U_(n-1)|<=n on [-1,1], including
endpoint limits. Thus sum(n*n*abs(c_n)) bounds the derivative of each stored
polynomial. Actual MID/RADIUS words set its dimensional scale.
The short retarded Earth/EMB difference is also bounded by the derivative
times the correlated emission delay **plus every intervening raw-record
jump**. Independent difference bounds are intersected; no C0 join is assumed.
All ten delay iterations are retained. Raw words, records, clock digests and
rotation scopes remain inspectable. These are sufficient real-model bounds,
not a convergence claim for light time or a native-rounding attestation.
[NAIF's SPK specification](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html)
governs the record format and route interpretation.

## Exact cone and clipping arrangement

The frozen generator is

    X(theta,t) = P + R*r(theta) + t*(u+K*r(theta)),
    r(theta) = e*cos(theta)+n*sin(theta).

The captured basis (u,e,n) must be nonsingular and is preserved exactly,
including tiny binary64 deviations from orthonormality. For central cones
K=-central_slope; for penumbral cones K=+penumbral_slope. The forward plane
is t>=axis_projection+Moon_radius. In the ordinary controls the Earth roots
are safely beyond that plane; general synthetic controls exercise it directly.

Two closed charts with sign s=+1,-1 and x in [-1,1] use

    cos(theta)=s*(1-x*x)/(1+x*x), sin(theta)=s*2*x/(1+x*x).

After substituting into X.Q.X=1, Q=diag(1/a²,1/a²,1/b²), the line equation
is A*t²+2*B*t+C=0 with A>0. Every possible branch or constraint change is
in one of the exact polynomial zero sets

    discriminant: B²-A*C,
    forward:      A*f²+2*B*f+C,
    horizon:      A*h0²-2*B*h0*h1+C*h1².

The horizon is h0+h1*t=0. Only exact divisions by positive powers of
(1+x²) remove factors. No floating coefficient trimming or near-zero
threshold is used. The reduced critical polynomials are at most quartic.
Signed primitive Sturm chains isolate every distinct real root, with the
gcd/derivative chain retaining multiplicity. The root/sign method is derived
from rational division and the Sturm variation theorem, independently
formalized in [Eberl's AFP development](https://isa-afp.org/entries/Sturm_Sequences.html).
No external algebra dependency is added.

At each critical root the signs of L+E*sqrt(D) are decided using exact
algebraic gcd/sign queries and L²-E²D, with sign guards before squaring.
An open complementary cell has no relevant zero, so its proven sample sign
labels the entire open cell by continuity. `ConeArc.parameter` is only an
outer rational hull; the two algebraic roots define the cell, and labels
do not extend to their isolator halos. Closed contact vertices are separate.
Both near/far roots and both nappes are kept. Repeated tangencies and
four-arm contacts survive; shared seams and a collapsed apex reuse one
vertex identity. Axis-only degeneracy gives points instead of fake loops.

Scaling X=D*z turns each horizon/forward plane into n.z=c on the unit sphere.
Its section is empty, a tangent point or a circle. All cone cuts come from
the complete generator arrangement; plane/plane cuts are solved separately.
Certified algebraic point ordering gives both periodic circle charts. With
all cuts excluded from an open arc, the other constraint signs cannot change.
Exact conic proportionality handles a whole coincident circle. The output
retains contact and coincident constraint strata; it does not infer counts of
filled surface regions from boundary loops or claim that every contact curve
is an outer boundary. Event-wide boundary selection belongs to Stage 5.

## Existing envelope audit and compatibility

The new code reuses the current native Earth-fixed shadow coefficients,
ellipsoid, Sun/Moon radii, forward geometry, frame infrastructure and
same-ray primitive. Existing penumbral and central generator formulas match
the affine family above. The penumbral envelope's sampled extrema and
time/azimuth continuation remain numerical candidates; they cannot establish
all components or exclusion of a time/surface box. No duplicate public
envelope or width convention is introduced. The exact arrangement supplies
the instantaneous cut sets that later boundary work can consume.

The 720-generator legacy width guard, its 92 withheld widths, all public
types and existing catalog/model differences are preserved. C++ and the
installed native binary are unchanged by Stage 4. No push was performed.

## Acceptance checks

The final receipt records exact test counts, source/build/resource hashes,
JUnit evidence and the selected command. Required controls include:

* Exact sphere/cylinder inside, tangent and outside; split/merge; even and
  repeated roots; roots separated by 2^-100; chart endpoints, poles and
  antimeridian; two nappes, axis-only and apex collapse; coincident and
  tangent clipping planes/circles; bounded budget exhaustion.
* Independent rational direct substitution checks of the cone/ellipsoid
  polynomial, 90-digit atlas checks, independent cap/horizon geometry and
  120-digit raw-coefficient forward-recurrence/light-time replay over actual
  source record joins. Finite replays corroborate implementation; the domain
  proof comes from the enclosure and root-isolation constructions.
* A complete ten-day DE441 whole-Earth interval exclusion, a synthetic
  complete 34-day interval, and a short positive interval missed by midpoint
  and endpoint samples. Both seeded and unseeded strict ray search and
  retained complements are checked.
* All 92 fresh events, each at 12 snapshots and six endpoints: the actual
  returned U1 and U4 binary64 epochs and their ±1-second neighbours. These
  are exact frozen snapshot inputs, not assertions that numerical contact
  epochs are exact roots of a different real time model. Analytic controls
  supply exact geometric tangencies.
* Modern 2017/2024, noncentral 2014/2043, the -500 short-axis case in the
  92 corpus, central/penumbral families, and the 2648 shared cone/horizon
  junction with the same endpoint objects in both arrangements.
* Five disputed traces on bounded eight-hour domains: lunations -33903
  and -32201 have strict visible-ray witnesses; -47467, -45765 and -24109
  retain bounded unresolved global status after their unsuccessful sites.
  None of the latter is called absent. External catalog labels are unchanged.
* Focused native footprint, clipped-boundary, noncentral, same-ray, source
  predicate and Stage 3 clock/continuous-path regression checks; scoped Ruff,
  engine docstring governance and whitespace checks.

Stage 5 remains separate: event-wide inner/outer enclosures, geographic limits,
cross-track width and publication-specific comparisons are not Stage 4 claims.
