# Lunar shadow absence certificates: proposed research

**Status: proposed work, not an implemented or validated certificate.** This
note describes a possible conservative exclusion test for an explicitly bounded
time interval. It does not establish completeness of existing eclipse searches,
guarantee that a full-moon neighborhood contains every eclipse, or validate a
physical model against an external catalog. Ambiguous intervals must remain
unresolved.

## Candidate exclusion

Let `M` be the geocentric Moon vector and `S` the geocentric, incoming
retarded Sun vector, in the same frame and distance unit. Let `d_m=|M|`,
`d_s=|S|`, and let `theta` be the angle from the antisolar direction to `M`.
The normalized-vector chord is

```
c = |M/d_m + S/d_s| = 2 sin(theta/2) <= theta.
```

For the opt-in Danjon angular model, positive penumbral overlap or tangency
requires `theta <= alpha + beta_p`, with

```
alpha  = asin(Rm/d_m)
beta_p = 1.01 asin(Re/d_m) + asin(Rs/d_s) + asin(Re/d_s).
```

Suppose an interval of half-width `h` has certified lower distances `dm`,
`ds` and upper vector speeds `Vm`, `Vs` in consistent time units. A lower
bound on the chord throughout the interval is

```
c_lower = lower(chord_at_midpoint) - h * (Vm/dm + Vs/ds).
```

For `0 <= R < d`, `asin(R/d) <= R/sqrt(d*d - R*R)`. Therefore an upper
bound on `alpha + beta_p` is

```
U = 1.01 Re/sqrt(dm*dm-Re*Re) + Rm/sqrt(dm*dm-Rm*Rm)
  + Rs/sqrt(ds*ds-Rs*Rs) + Re/sqrt(ds*ds-Re*Re).
```

If **`c_lower > U`**, the whole interval is free of Danjon penumbral
overlap, including tangency. Use strict outward-rounded bounds throughout;
otherwise subdivide or return unresolved. Bounds must cover evaluation and
time-conversion errors as well as continuous state motion. This exclusion
alone says nothing about maxima or contact roots.

For the separate static finite-cone model, do not reuse the Danjon threshold.
Within its supported downstream domain, with effective Earth radius `Re_eff`,
let `dm_max` bound lunar distance above and define

```
sp_max = (Rs + Re_eff)/ds
cp_min = sqrt(1 - sp_max*sp_max)
U_cone = sqrt(2) * (Re_eff + sp_max*dm_max + Rm)/(cp_min*dm).
```

When `sp_max < 1` and the downstream domain is certified for the interval,
finite-cone penumbral overlap implies `chord <= U_cone`; thus
`c_lower > U_cone` is also a conservative exclusion. This follows from the
cone clearance inequality `cp*r <= Re_eff + sp*z + Rm`, `r=d_m sin(theta)`,
`z <= d_m`, and `chord <= sqrt(2)*sin(theta)` for `theta < pi/2`.

## Required proof obligations

- Extract bounds from the actual selected SPK routes and records. For a
  type-2 coordinate `sum(c_n T_n(x))`, `|x| <= 1`, a speed bound is
  `sum(n*n*abs(c_n))/record_radius`, because `|T_n'(x)| <= n*n`.
  Moira's loaded coefficient sequence is highest order first, so polynomial
  order is counted from the end. Combine component bounds conservatively,
  convert seconds/days explicitly, and bound every routed leg. Do not assume
  this argument covers other SPK types or arbitrary reader implementations.
- Split or otherwise enclose record and selected-route boundaries, including
  boundaries crossed by the retarded emission epoch. Bound each side of any
  potential discontinuity; do not assume that independent records or kernels
  match exactly. Reject unsupported coverage and route changes rather than
  issuing a certificate from an incomplete bound.
- Derive positive interval distance lower bounds from enclosed midpoint
  vectors and speed bounds, including numerical state error. Verify all model
  domains over the interval. Bounds that reach a singularity or leave a
  supported domain are unresolved.
- Account for reception light time. For the ideal fixed point, if `A` and `B`
  bound barycentric Sun and Earth speed and `A < C`, then
  `|delay'| <= (A+B)/(C-A)` and the geocentric Sun speed is bounded by
  `A*(1+|delay'|)+B`, in a common independent time coordinate. Enclose
  emission-time coverage and the difference between the computed iterative
  state and the exact fixed point using a demonstrated contraction and error
  budget. Moira's finite-iteration stopping branch itself must not simply be
  presumed differentiable.
- Enclose the TT/TDB mapping and, for a UT interval, the applicable piecewise
  Delta-T conversion and its breakpoints. An explicitly TT/TDB-bounded API can
  avoid claiming an unproved UT-to-ephemeris interval mapping. Preserve the
  actual split-epoch or legacy evaluation path and its numerical errors.
- Supply a justified outward-rounding implementation for all arithmetic,
  norms, square roots, coefficient evaluation, and transformations. For
  example, standard-library `decimal` interval arithmetic may be investigated,
  but merely choosing a high precision or assuming platform `libm` is correctly
  rounded is not a proof. Include finite precision and the model's numerical
  tolerance in the enclosure. Reject nonfinite or unbounded intervals.
- Define the search coverage separately. A certificate excludes only the
  intervals actually enclosed. A full-month or next/previous search must also
  prove that its union covers the advertised time range; assuming a fixed
  neighborhood around full moon is insufficient. Detection of one positive
  sample establishes overlap only within the relevant numerical error bounds;
  complete classification, all contact roots and global maxima require
  separate isolation and completeness arguments.

## Minimum verification before using a certificate

- Independent synthetic Chebyshev cases, including extrema near record ends,
  check that analytic bounds enclose high-precision state and derivative
  evaluations; include constant, high-order, and multiple routed legs.
- Place a positive peak shorter than the sampling interval strictly between
  samples. It must never be declared absent; a provably separated case should
  certify absence, while exact tangency and insufficient precision stay
  unresolved. Include a representative approximately 14-second grazing event.
- Exercise each side of record, route, and retarded-emission boundaries;
  Delta-T breakpoints; kernel coverage gaps; unsupported reader/SPK types;
  fixed-point failure; and model-domain limits. No unsupported case may issue
  an absence certificate.
- Compare computed bounds and candidate outcomes with an independently
  implemented higher-precision reference across representative DE441 epochs,
  including historical extremes. Record kernel identity, policy, time scale,
  intervals, failures, and cost. Sampling is a validation aid, not a proof of
  the bound or of full-catalog completeness.
