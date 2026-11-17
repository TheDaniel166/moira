# Instantaneous clipped solar-shadow candidates

`moira.solar_eclipse_clipped.inspect_instantaneous_clipped_central_boundary`
inspects a single UT1 epoch. A `candidate` contains sampled curve points and
an `unresolved` result contains no curve. Both have `complete=False`: the
native generator interval and finite samples do not prove that every component
or narrow transition has been found. In particular, unresolved does not mean
that an eclipse is absent. Unexpected calculation or kernel errors propagate.
The result carries the UT1 epoch, engine version, model radii, and kernel
filename when the reader exposes one. A filename is not a content hash; pool
readers without a single named source report no filename. Reproducibility
requires a separate receipt identifying and hashing the actual inputs.

The model uses Moira's native Earth-fixed central cone, a zero-elevation WGS84
ellipsoid, and the unrefracted geometric horizon of the Sun's centre. It is not
an observer's local contact calculation and does not assert NASA or EclipseWise
conventions. Curves are sampled for presentation; connecting the points is an
approximation.

The bounded candidate has a cone arc and a horizon arc meeting at identical
shared endpoint objects. Each shared point is checked against the ellipsoid,
cone, horizon, and physically allowed forward cone before it is used. A limited
periodic candidate has a sampled closed cone arc and no horizon arc. Its
daylight and physical-branch checks are performed at the returned samples;
they do not rule out a narrow feature between samples. Tangencies, multiple
components, crossings, apex transitions, and other ambiguous periodic cases
remain unresolved unless the numerical checks admit the indicated candidate.

On bounded arcs, accepted cone samples allow an unnormalized dimensionless
ellipsoid-normal horizon-plane residual down to `-1e-6`; horizon samples
allow signed cone clearance down to `-1e-5 km`. The largest allowed absolute
ellipsoid residual is `2e-12`; the horizon and cone boundary residual limits
are respectively `2e-10` and `1e-6 km`. These are numerical admission checks,
not physical-accuracy estimates. Different model inputs, Delta T, refraction,
lunar topography, and external-table rounding remain separate uncertainties.

This product is not a time-stamped published path limit, the boundary of the
event-wide union of shadow positions, or a catalog width. Those require separate
definitions and complete branch or envelope isolation; a source width cannot
be inferred from the distance between the two reported limit points. Existing
path and width availability semantics remain unchanged.

The existing `instantaneous_clipped_central_boundary` function retains its
bounded-cap-only contract and raises `ClippedBoundaryIndeterminate` for
unsupported topology. The new inspector additionally supplies the provisional
periodic candidate and turns that typed geometric uncertainty into an explicit
result; it does not catch general provider or computation failures.
