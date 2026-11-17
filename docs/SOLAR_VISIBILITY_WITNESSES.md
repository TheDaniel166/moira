# Solar visibility at a site

`solar_visibility_at_site` evaluates one observer and epoch. It determines
whether the *same sky direction* lies inside both modeled Sun and Moon discs
and above the local geometric horizon. The pure spherical-cap calculation is
`moira.solar_disc_visibility.solar_disc_visibility`; the native WGS-84
adapter and supplied-candidate search are in `moira.solar_visibility_witness`.
These are opt-in diagnostics and do not change Moira's existing solar event
search or classifications.

```python
from moira.eclipse import EclipseCalculator
from moira.julian import julian_day
from moira.solar_visibility_witness import solar_visibility_at_site

result = solar_visibility_at_site(
    EclipseCalculator(), julian_day(2024, 4, 8, 18 + 40/60),
    latitude_deg=32.7767, longitude_deg=-96.7970,
)
print(result.geometry.status, result.geometry.maximum_altitude_rad)
```

The algorithm intersects exact angular spherical caps on the observer's unit
sky, not planar discs. It maximizes altitude over the common solar/lunar lens,
considering cap interiors, circle extrema and circle intersections, with
separate containment and degenerate handling. Independent tests include a
counterexample where both discs individually cross the horizon and overlap,
but their common lens remains below the horizon. A `visible` result carries a
strictly interior common-ray witness above the horizon, distinct from the
maximum direction, which may lie on a disc boundary. `hidden` means the common
lens is below the geometric horizon at that particular site and instant;
`disjoint` means the local discs do not overlap. `tangent` is a certified
degenerate contact; `indeterminate` covers numerical threshold cases.
Angular threshold and returned altitudes/margins are in radians. The minimum
accepted binary64 guard is `1e-12` radians; smaller requested tolerances are
rejected. This guard is not a rigorously certified floating-point error bound,
model-uncertainty estimate, or observation-accuracy estimate.

The native adapter uses zero-elevation WGS-84 geodetic latitude/longitude,
the local ellipsoid normal, and Moira's Sun and Moon vectors retarded to the
Earth reception epoch, transformed into ITRF. It uses spherical model radii,
with a geometric horizon and no refraction, terrain, annual/diurnal aberration,
or separate observer-reception light-time solution. It rejects overlapping
Sun/Moon foreground depth intervals as unsupported. Results record UT1, TT,
ephemeris identity, site, policies, and an optional caller-provided lunation;
the lunation label is not independently verified. Provider/domain failures
are raised and never converted into absence.

`inspect_solar_visibility_candidates` accepts explicit
`(jd_ut1, latitude_deg, longitude_deg)` tuples. It returns the first positive
witness or `unresolved` after exhausting those tuples. Both results carry
`complete=False`: finite site/time sampling neither searches all of Earth nor
proves that an event or a short visible phase is absent. A local negative
result likewise says nothing about other sites or times. A global exclusion
requires additional certified space/time bounds.

`refine_solar_visibility_candidate` searches a continuous, caller-specified
box of UT1, latitude and longitude around an explicit seed. It uses
derivative-free bounded coordinate-pattern refinement of a heuristic
combining disc-overlap angle and common-lens altitude; no SciPy dependency is
required. Returned metadata includes the box, evaluations, numerical step
sizes, and local step-convergence flag. A positive result retains a strict
same-ray witness; otherwise the result is `unresolved`, including at
tangencies or iteration limits. The heuristic may be discontinuous at lens
degeneracies, so local convergence does not prove a global optimum, absence,
or complete interval coverage. Sub-JD-resolution time tolerances are rejected.
The five historical sample sites are exercised from displaced seeds using
bounded searches; for -33903 the seed is initially hidden and local
refinement finds a visible witness. Comparing coarse and finer tolerances is a
numerical convergence check, not a certified physical accuracy bound.

The five disputed historical lunar-number cases have been replayed at one
previously selected local optimizer site and epoch each under native DE441.
Lunations -33903 and -32201 yield positive local witnesses; -47467, -45765,
and -24109 have disjoint discs at the sampled sites. Those three negatives are
not global absence findings, and the results do not establish which catalog
is physically correct. The fixture documents sources and the same-model
research comparison; that comparison is not an independent ephemeris oracle.
