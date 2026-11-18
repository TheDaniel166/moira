# Stage 5: event-domain enclosures and geographic cross-track widths

**Status: accepted for the bounded enclosure and named geographic-width
products, 2026-11-17.** All **392 distinct checks pass**, with no failures,
errors or skips. All 92 event domains have certified inner and exterior cells;
51 width intervals meet the requested 1-km span and 41 retain explicit coarser
precision bounds. The finite-budget meshes retain 3,121 unresolved cells;
no complete exact vector path is claimed. Stage 4 is committed as
`12eaaf807b0e38f9bd316a23de7135f98ab1bf37`. No push has been made.

## Products and exact scope

The new private products are a certified inner/outer **mesh enclosure** of a
finite event-domain union, and a time-stamped **geographic cross-track width
interval**. The mesh is the first boundary product required by the Stage 5
plan. It does not purport to be an exact vector curve. Unresolved cells stay
in the outer cover. An unresolved tangent is not advertised as a complete
path. Public selectors, catalogs, JSON shapes and the 92 withheld legacy
support widths are unchanged; Stage 6 integration remains separate.

Both products use the explicit continuous real current-policy lift accepted
in Stages 3–4, including copied DE441 words, UT1/TT mapping, implicit TT/TDB,
ten finite retarded Sun/Moon updates, current orientation coefficients and
true-circle Earth rotation/polar motion. They do not certify every rounded
native execution, physical accuracy, historical Delta-T or IAU conformance.
The previously documented p_A policy discrepancy is preserved explicitly.

The central footprint uses **spherical-limb disc containment, separated
foreground depths and the geometric Sun-centre tangent horizon**, with
zero elevation and no terrain/refraction. This preserves the existing
central-interior convention. Stage 4's same-visible-ray partial-occurrence
product has a different horizon convention and is not replaced by this mesh.

For an explicitly chosen closed UT1-offset interval I, define U(I) as the
union of its modeled central footprints relative to the WGS84 surface.
The 92-case corpus uses I=[-1/6,+1/6] day about each freshly calculated native
event epoch. This is the declared event domain; no result claims exclusion
outside it, a complete lunation, or a certified nearest-event search.

## Central-footprint interval predicate

For observer rays S,M with distances ds,dm and source radii Rs,Rm, let

    B = Rm*sqrt(ds²-Rs²) - Rs*sqrt(dm²-Rm²),
    C = |S cross M|.

On the admitted acute-ray branch, |B|-C>=0 is exactly disc containment:
B/(ds*dm) is sin(beta-alpha), and C/(ds*dm) is sin(separation). The remaining
necessary constraints are positive source-exterior/foreground admission,
S.M>0, and Sun-centre daylight. Rational intervals and integer-certified
square roots bound these expressions without an angular epsilon.

`SolarFrameBounds` retains celestial Sun/Moon jets and their **common** real
rotation. Observer positions/normals are transformed back together before
the predicate is evaluated. Independent ITRF body boxes would discard the
rotation correlation and produce much weaker bounds. A strictly negative
daylight bound may exclude a box before Moon cap normalization is admitted;
uncomputed other margins remain `None`, not fictitious numbers. Inclusion
always requires every margin and its strict positive lower bound.

## Inner and outer enclosure proof

The six closed pole-safe surface charts are inherited from Stage 4. At each
surface rectangle, the algorithm searches its entire closed time interval.

* **Inside:** a common time is proved for the whole rectangle, with all strict
  containment, daylight and foreground margins. Different times at different
  points are insufficient. The stored time and bounds witness a surface-relative
  interior subset of U(I).
* **Outside:** a closed time partition covers all of I, and every piece excludes
  at least one necessary predicate uniformly over the whole rectangle.
* **Unresolved:** retain the whole surface rectangle in the outer enclosure,
  including unsupported domains, exact equalities and exhausted budgets.

Time and surface subdivision retain shared endpoints/edges. Separate time
work limits prevent a difficult coarse face exhausting all useful spatial
work. Evaluation and cooperative wall-clock budgets are explicit. A call
already in progress is not preempted by the wall clock.

Optional spatial/time hints carry no authority. Exact grid cuts around an
axis hint and a night-side hint retain **all** surface complements. Area and
interior-overlap checks prove a full six-face partition. A caller-supplied
partial region does not acquire a false whole-Earth flag. The real corpus
requires both strict interior cells and whole-event exterior cells; an
all-unknown globe is not an accepted corpus result.

The inner cells are a subset of the union interior. The complement of the
outside cells is an outer cover of U(I). Consequently every boundary point
is retained in the unresolved band, including chart seams, poles, the
antimeridian, contacts and transitions. This is a certified enclosure, not
a Hausdorff error claim, an exact boundary trace, or a claim that every
unresolved cell contains an actual boundary. Finite-budget real meshes can
retain broad uncertain regions; consumers must display that uncertainty.

## Envelope branches and existing infrastructure

For an exact vector boundary, smooth envelope candidates would satisfy a
central-boundary equation G=0 and its time stationarity G_t=0 with appropriate
strict horizon/foreground constraints. Other candidates are temporal endpoints,
horizon-active arcs, cone/horizon junctions, apex collapse, source/policy joins
and changes in component topology. These conditions identify candidates;
they do not establish which curves are outer boundaries of a temporal union.

The new enclosure covers the entire time/surface product, so all those
families are retained without assuming a single smooth envelope. It shares
the established frame/source/interval geometry and Stage 4's instantaneous
arrangements. The sampled penumbral envelope and legacy generator products
remain numerical candidates. No sampled envelope is silently promoted to a
certified swept boundary. Exact/bracketed vector curves remain withheld where
continuation, root uniqueness and complementary exclusion are unproved.

The 2003 source-limit control is decisive: the listed rounded northern point
has a negative geometric Sun-centre altitude at 04:08 under this model, then
has all strict central-interior margins at 04:09. The new bounded provider
certifies that same-time interior over the supplied two-minute event interval.
It cannot be labeled a boundary of that union merely because it appeared in
a time-stamped published table.

## Geographic width definition and proof

The metric identifier is **WGS84_central_plane_cross_track_arc_length**.
It measures arc length on the plane through Earth's centre and the near-axis
reference, whose tangent at that reference is perpendicular to the local
track motion. It is a central plane section; it does not use the classical
surface-normal section, a geodesic or a tangent-plane extrapolation.

The near-axis reference is obtained from the real Sun/Moon line and WGS84
quadratic. Its derivative comes from the differentiated implicit solution
with the source/clock/rotation jets. No fixed +/-30-second finite difference
sets the track direction. At a continuous policy knot, the enclosing local
derivative family retains the one-sided tangent possibilities. A stationary
or unconditioned track, source discontinuity, noncentral/no-axis reference or
unproved forward branch gives no numeric width.

With D=diag(a,a,b), reference X0, normal QX0 and velocity V, define

    A = unit(D^-1 X0), B = unit(D^-1((QX0) cross V)).

The underlying A,B are orthonormal. The curve X(phi)=D(A cos(phi)+B sin(phi))
lies exactly on the ellipsoid; at phi=0 its tangent is perpendicular to V.
The implementation carries conservative boxes for this same underlying pair,
not an assertion that all independent box corners are orthonormal.

The local branch policy chooses the connected visible central component
containing this strict near-axis reference. A rational half-angle chart covers
its entire reference hemisphere. A width requires excluded outer complements,
one certified interior component and two retained limit bands. Multiple
unseparated components or missing limits produce an explicit unresolved state.
The component edges are bracketed; uniqueness of every root inside a band is
not falsely asserted. Limits record their epoch, parameter and ITRF coordinate
boxes as **negative/positive cross-track** sides, without invented north/south
labels near poles.

The width lower bound integrates the section arc between the inner limit
bracket endpoints; the upper bound integrates between the outer endpoints.
Midpoint quadrature has the explicit second-derivative remainder
M*(delta_phi)^3/24. From v=X', v'=-X, v''=-v, interval norm bounds give M
directly. Independent coefficient/track uncertainty is bounded with the
norm's 1-Lipschitz inequality and added separately; it cannot be reduced by
subdividing the quadrature indefinitely. Endpoint atan enclosures include
their own interval tails.

`bounded_width` meets the requested interval span. A valid coarser enclosure
is labeled `bounded_precision_limited`, with its full interval and conditioning
reason. `unresolved` has no numeric width. No missing value becomes zero.
Neither numeric status means NASA compatibility, physical accuracy or a
width of the event-wide spatial union. The timestamp, event-domain association,
reference, track-speed/discriminant bounds and metric remain visible.

## Publication-specific research and comparison

The sources must be compared as separate publications. Their row coordinates,
epochs and numeric widths do not define this new Moira metric. The path keys
place circumstances at the central line; they do not disclose enough of the
exact publication-specific algorithm to admit a NASA-compatible implementation.
The exact width algorithm remains **not established**, as allowed by Stage 5's
explicit source-convention rule. No approximate formula or fitted number
replaces it.

| Publication | Model/time and formatting evidence | Disposition |
| --- | --- | --- |
| NASA 2003 original Table 1.3 | [Chapter 1](https://eclipse.gsfc.nasa.gov/SEpubs/20030000/text/section1.html) specifies DE200/LE200, reduced antumbral lunar-radius convention, no refraction, and 0.1-arcminute coordinate rounding. [Table 1.3](https://eclipse.gsfc.nasa.gov/SEpubs/20030000/tables/table_1.3.html) leaves widths blank at the central-line rows used here. The chapter describes a roughly 1200-km terminator-limited D-shaped path. | Retain blank as not published; not zero. The 04:08 coordinate is a time-stamped source limit, not a proven temporal-union boundary under Moira. |
| NASA 2003 web table | [Source](https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2003May31Apath.html): VSOP87/ELP2000-85, Delta-T=64.5 s, WGS84, 120-s rows; at 04:08 the table lists 4678 km. | Different ephemeris, time/radius/construction policies. Retain its numeric value without treating it as the expected Moira geographic arc. |
| EclipseWise 2003 | [Source](https://eclipsewise.com/solar/SEpath/2001-2100/SE2003May31Apath.html): DE406, Moon centre of mass, Delta-T=64.4 s, WGS84, 120-s rows. | Preserve its own UT1 epoch and printed width. DE406 is not available in this checkout; matched-source numerical reproduction is unavailable. |
| NASA 2044 web table | [Source](https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2044Feb28Apath.html): VSOP87/ELP2000-85, Delta-T=87.1 s, WGS84, 120-s rows. | Preserve independently of the EclipseWise scenario; no forced agreement. |
| EclipseWise 2044 | [Source](https://www.eclipsewise.com/solar/SEpath/2001-2100/SE2044Feb28Apath.html): DE406, Moon centre of mass, Delta-T=81.5 s, WGS84, 120-s rows; greatest eclipse is 20:23:18.0 UT1 with printed width 2237.9 km. | The event epoch differs from 20:24 and from NASA's scenario. Do not compare across those epochs as a matched-input width test. |

The NASA [table explanation](https://eclipse.gsfc.nasa.gov/SEmono/reference/explain.html)
and EclipseWise [column key](https://www.eclipsewise.com/solar/SEhelp/SEpathkey.html)
support the central-line/time association. The previously researched
Mucke–Meeus formula remains an explicitly approximate research comparator;
near-horizon repeatability does not establish geographic accuracy. The
-500 extrapolated value larger than Earth is never admitted as a geographic
width. Source limb/radius assumptions not recovered for a particular row stay
unverified; the sources are not silently assigned Moira's radii.

## Acceptance record

The passing acceptance includes the full 92-case event-domain and width-disposition
replay, the 2003/2044/-500 controls, independent moving/static sphere and
ellipsoid cases, exact tangent/shared junction/multiple-component and apex
controls, seam/pole/antimeridian checks, independent ellipse-series arc length,
source/precision/budget failures and preservation of Stage 4 and legacy
width contracts. The immutable final receipt supplies case-by-case statuses,
all unresolved counts and precision limits, test counts and source,
native binary and resource identities. The worst 92-case width-interval span
is approximately 3.515 km. For lunation -30916 (-500), the bounded interval is
approximately [142.734,143.962] km, explicitly precision-limited; it is never
the unbounded tangent-plane extrapolation from the earlier research.

The unit/analytic slice passes 31 checks, the real-source control slice passes
five, the four corpus shards pass 92, and the Stage 4/legacy preservation slice
passes 264. The corpus's mathematical implementation was unchanged by the
subsequent metric-identifier wording correction; the final control slice
verifies the corrected `WGS84_central_plane_cross_track_arc_length` identifier.
No byte-identical full-corpus attestation across that metadata-only edit is
claimed. Stage 5 changes remain local and uncommitted, nothing was pushed,
and Stage 6 has not begun.
