# Stage 4: first surface-visibility foundation

**Historical first-increment record.** This increment was verified before
the whole stage was accepted. Its remaining gates are now completed in
`ECLIPSE_STAGE4_ACCEPTANCE.md`. Stage 3 is committed as
`b132dbe0f6b3fffe23648d9cd270c068105e937e`. No push was made.

## Product and scope

The new private solver partitions the entire zero-elevation ellipsoid for
caller-supplied, real geocentric Sun/Moon position boxes in ITRF. The radii
are the existing represented WGS84 coefficients and explicit source radii.
The horizon is the local ellipsoid tangent plane. A positive result requires
the **same ray** to be strictly inside both apparent discs and above that
horizon. There is no refraction, terrain, gravitational bending or implicit
observer-reception correction.

The input boxes are conditional model inputs. The result retains them,
the ellipsoid coefficients, cell domains, exclusion slacks/multipliers,
strict witnesses and evaluation budgets. It does not attest their ephemeris
source, attach UT1/TT correspondence, or bound a continuous time interval.
Freezing native binary64 coordinates as exact real inputs is a distinct
product from enclosing every rounded serving operation.

## Audit of existing infrastructure

* `solar_disc_visibility.py` already checks a common spherical-cap lens. Its
  strict witness is useful as a candidate, and its near-degeneracy guards
  remain intact. In the 2017/2024 axis-site controls an indeterminate ordinary
  circle basis is allowed; a separately checked centre ray proves visibility.
* `solar_visibility_witness.py` supplies the existing zero-elevation and
  separated foreground-depth policy. The new solver preserves that admission:
  overlapping/reversed depth intervals are unresolved, not negative events.
* `solar_eclipse_clipped.py` uses a **Sun-centre** horizon. That differs from
  the visible-common-ray horizon when the solar centre is below the tangent
  plane but a visible part of the lens is above it. Its sampled curves and
  `complete=False` contract cannot be promoted into the new product.
* Its horizon/cone quartic is a useful derivation starting point. The current
  coefficient trimming and binary64 simple-root procedure do not certify
  close/repeated roots, exact tangencies, all periodic components or all
  generator branches. Exact rational construction and root isolation remain
  work to do; the current floating coefficients are not an exact-geometry proof.
* The penumbral envelope in `eclipse.py` follows a contour in time and
  generator azimuth and explicitly handles folded arms. Reuse those geometric
  objects and junction definitions. The structural epoch lattice, sampled
  generator extrema and continuation steps do not prove global completeness.
* `_central_shadow_generator_points` samples the legacy generator family.
  All samples intersecting does not prove that every intermediate generator
  intersects. Existing width admission and withholding are unchanged.
* `_earth_fixed_solar_shadow` can return `None` outside its solar-cone domain;
  this was observed in a nonconjunction probe. A missing shadow is not a global
  occurrence exclusion. The new classifier rejects `None`; a future all-time
  vector provider must be independent of that cone eligibility decision.

No existing public helper, native implementation, tolerance, golden fixture,
catalog or width result was changed by this increment.

## Six-chart surface enclosure

On each signed cube face, set one coordinate of q to +1 or -1 and let its
other two coordinates range over the closed square [-1,1]^2. With
D=diag(a,a,b), map P=D*q/|q|. The denominator is at least one. Every ellipsoid
point has a largest absolute scaled coordinate; choosing that face gives
parameters in the square and recovers the point. Thus all six charts cover
the full ellipsoid, including poles, the antimeridian and shared corners.

The outward normal is unit(D^-1*q). The positive common factor in the
ellipsoid gradient cancels before bounding. Position and normal use rational
interval operations and integer-certified square roots. Binary subdivision
keeps both sides of every shared parameter boundary.

## Common-ray exclusions and witnesses

Let s,m,n be the actual unit Sun, Moon and normal directions. The closed
necessary ray constraints are

    |r|=1, r.s >= ca, r.m >= cm, r.n >= 0,
    ca=sqrt(1-(Rs/ds)^2), cm=sqrt(1-(Rm/dm)^2).

For any nonnegative lambda, mu, nu, summing constraints and applying
Cauchy-Schwarz gives

    lambda*ca + mu*cm <= |lambda*s + mu*m + nu*n|.

A strict reverse **whole-box** inequality therefore excludes the common
intersection. The tested multiplier set is only a sufficient search; failure
to find such an exclusion remains unresolved. Individual disc-separation and
cap-below-horizon exclusions are also sufficient, never positive witnesses.
The joint certificate resolves the analytic example in which the discs
overlap and each individually reaches above the horizon but their common
lens is entirely hidden.

Candidate rays come from disc centres, the normal, a centre combination and
the existing floating solver. Every positive ray is renormalized with rational
enclosures and must have three strictly positive lower-bound clearances.
Exact contact/horizon tangency is neither a positive-area witness nor a strict
negative. No platform trigonometric result sets a proof tolerance.

The complete parameter ledger includes every unresolved or unvisited patch.
A point witness proves existence without resolving the entire surface map.
Absence requires uniform exclusions on all six charts. Whole-patch and
point-witness attempts have separate finite budgets; stopping after a witness
retains the unvisited domain. Input uncertainty is not replaced by a midpoint.

## Verification and remaining work

The focused slice passes **56 tests, no failures/errors/skips**, with five
DE441 resource checks. Independent 90-digit Cartesian constructions test
chart positions and normals; the existing 70-digit lens control corroborates
the horizon examples. Controls cover poles/corners/antimeridian, just-inside,
exact-tangent and just-outside horizons, a hidden common lens, strict witnesses,
upstream domain rejection, uncertainty boxes, retained area and finite budgets.

Frozen 2017/2024 native examples provide rechecked positive rays. A frozen
scene one day after the 2017 positive control is excluded over all six faces;
this is a whole-surface result for those supplied fixed vectors, not a negative
sample or a time-interval certificate. Ruff, engine docstrings and whitespace
checks pass. The native binary is unchanged from the verified Stage 3 build.

At this first increment, remaining work was to connect time/route/vector providers to time x surface
boxes, derive continuous generator and horizon topology (including repeated
roots/apices), and exercise the shared 2648 junction, U1/U4 neighborhoods,
ordinary/noncentral cases, five disputed presence traces and all 92 x 12
snapshots plus 92 x 6 endpoints. The final Stage 4 acceptance record supersedes
this historical list; those implementation and corpus gates now pass.

The underlying convention is the
[NGA WGS84 definition](https://earth-info.nga.mil/?action=wgs84&dir=wgs84);
the current represented coefficients, their precision scope and all new
inequalities are stated above. Existing Moira code supplies the named disc,
foreground and horizon policies; it is regression evidence, not an external
physical-accuracy oracle.
