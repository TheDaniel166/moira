# Explicit lunar shadow candidates

Moira exposes two opt-in lunar-shadow sensitivity models. They are separate
from the existing native and NASA-compatible event APIs; those defaults and
their historical definitions are unchanged. The models do not force
agreement with any eclipse catalog.

```python
from moira.eclipse import EclipseCalculator
from moira.julian import julian_day
from moira.lunar_shadow_events import inspect_lunar_shadow_candidate

calculator = EclipseCalculator()
result = inspect_lunar_shadow_candidate(
    calculator, julian_day(2020, 7, 5, 4.5), policy="danjon_angular"
)
if result.status == "detected":
    print(result.event.candidate_type, result.event.contacts)
else:
    print(result.reason)  # unresolved; not proof that no eclipse occurred
```

`danjon_angular` compares geocentric angular circles. Its penumbral and
umbral shadow radii use NASA's published Danjon expressions: `Rp = 1.01*Pm +
Ss + Ps` and `Ru = 1.01*Pm - Ss + Ps`, with lunar parallax `Pm`, solar
semidiameter `Ss`, and solar parallax `Ps`. The Moon's angular radius and
angular separation are compared in the same radians. NASA describes the
convention and its atmospheric and Earth-oblateness approximation in its
[shadow geometry notes](https://eclipse.gsfc.nasa.gov/LEcat5/shadow.html).
This policy selects the formula, not NASA's entire ephemeris, time, reduction,
maximum, or contact pipeline.

`static_finite_cone` computes Sun/Earth common-tangent cones and the distance
from the finite spherical Moon to the cone. The default Earth radius scale is
1.0; `earth_radius_scale=1.01` is an explicit sensitivity parameter. A scaled
static cone is not equivalent to the Danjon angular prescription or a full
moving-body photon-propagation solution. The model requires the Moon to lie
wholly downstream of the effective Earth's bounding sphere. Unsupported
geometry raises `LunarShadowDomainError`; it is never counted as absence.

Both pure-vector functions `danjon_angular_shadow` and
`spherical_cone_shadow`, in `moira.lunar_shadow_models`, return an immutable
`LunarShadowGeometry`. Physical perpendicular axis distance is in kilometres,
and unsigned gamma is that distance divided by the unscaled Earth radius.
These remain separate from model-specific phase margins: radians for Danjon,
kilometres for the finite cone. Positive margins mean overlap or, for the
total margin, containment. Angular magnitudes are provided only by the
angular model; finite-cone magnitudes are left undefined.

For candidate evaluation, vectors use Moira's incoming retarded Sun and
simultaneous geocentric Moon, without annual aberration. Every returned phase
and contact uses the same selected model and vector policy. Each phase has a
separate numerically refined maximum. The reported `greatest_jd_ut` maximizes
penumbral signed overlap (in geocentric arc-equivalent kilometres for the
angular model, or cone clearance kilometres for the finite cone); this need
not be a minimum-axis, maximum-umbral, apparent-observer, or NASA epoch.
The separate `axis_distance_minimum_jd_ut` and
`angular_opposition_minimum_jd_ut` fields expose bounded candidate extrema
for those distinct criteria under the same vectors. Like the phase maxima,
their global uniqueness is not certified and no NASA epoch equivalence is
implied.
Contact solver coalescence tolerance is `1e-6` km, where angular margins are
scaled by Moon distance to arc-equivalent kilometres. This is a numerical
threshold, not a physical uncertainty estimate.

Candidate results are provisional. `complete` and
`event.completeness_certified` are always false: numerical optimization and
finite contact sampling do not establish global uniqueness, exclude other
short components, or prove that a missing umbral contact is absent. No
detected candidate produces `status="unresolved"`, not a negative event
finding. The lower-level `lunar_shadow_event_near` reports the same condition
as `LunarShadowUnresolvedError`. A truncated contact window raises
`LunarShadowWindowError`. Contact candidates must also pass nesting checks.
There is intentionally no new unrestricted next/previous or full-catalog
search; safely excluding every intervening lunation requires certified
interval bounds. The existing event search remains available with its prior
behavior and conventions.

For numerical work on a specified interval, the separate opt-in
`inspect_lunar_shadow_tt_interval(calculator, start_tt, end_tt)` evaluates
the static finite-cone model on **represented binary64 TT** Julian days. It
constructs its own bounded Earth/Moon/Sun routes and frozen type-2 records;
the user cannot provide a previously generated receipt as proof. The result
returns `conditionally_excluded` only if the penumbral-margin upper bound is
strictly below the negative contact tolerance, `conditionally_overlapping`
only if its lower bound is strictly above the positive tolerance, and
`unresolved` otherwise. These conditional statuses require the documented
source, native-build, rounding, libm, and resource premises; none are attested
by the returned record. The kernel hash is its reader-open observation, and
the ordered route records identify the copied coefficient snapshots and the
number of bounded route calls, not live mapped-file integrity. Callers can set
`max_route_calls` and `max_records`; budget exhaustion returns `unresolved`.
When preparation fails before returning route evidence, the number of calls
already made is unavailable rather than reported as zero.

These conclusions apply only to the indicated copied-record execution and
represented TT values: they do not cover the live-mapped evaluator, UT1,
continuous real times between binary64 values, physical accuracy, or complete
event-search absence. The historical ~13.9-second native grazing control uses
a different shadow model; its outcome cannot be imposed on this finite-cone
policy. Unsupported routes and unproved clock/model conditions are unresolved.

The verification suite includes independent cone tangent/distance and
angular grazing examples, synthetic phase/contact trajectories, and DE441
penumbral, partial and total candidate controls. The pre-implementation
26-disagreement replay compares the same models and ephemeris with separate
grid-plus-golden numerical searches; this is a numerical regression, not an
independent physical oracle. The 2020 OPALE control uses a different ephemeris
and epoch definition and is therefore only compared within a broad tolerance.
For five detected candidates per policy, contact scans at 120, 60, 30 and 10
seconds are compared for phase presence and timing convergence; convergence
does not certify an exhaustive phase search.
