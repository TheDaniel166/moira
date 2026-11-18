# Stage 7 solar occurrence, boundary and width proofs

The scientific scope is the continuous real DE441/LE441 policy from Stages
3–6 with the explicit source clocks, represented radii, geometric horizon
and WGS84 surface. Each case uses the supplied closed eight-hour UT1
interval. The native catalog generation remains tied to its frozen
five-millennium source. The closure adds independently reproducible
dispositions and path and width certificates for the selected cases.

## Whole-Earth penumbral exclusion

Let S and M be the geocentric Sun and Moon centres. Let e point from S to M
and let w be the unit projection of M perpendicular to e. With
`sin(f)=(Rs+Rm)/|M-S|`, the unit normal `n=-cos(f)w-sin(f)e` defines a
plane tangent to both source spheres. Its level is
`n·M+Rm=n·S-Rs`. The entire Sun lies on or above this level and the
entire Moon lies on or below it.

The minimum Earth support along n is
`-sqrt(a²-(a²-b²)(n·k)²)`, where a and b are the equatorial and polar
radii and k is Earth's unit polar axis in the celestial frame. When that
minimum strictly exceeds the tangent plane's level, every segment from
Earth to the solar sphere lies above the plane before reaching the Sun.
It cannot intersect the lunar sphere on the way. The source depth guards
ensure the required Earth–Moon–Sun ordering. The proof therefore excludes
all candidate visible rays at once, including tangent rays and every
surface chart.

The interval provider computes the support and source jets over whole
time cells. A mean-value enclosure may tighten a cell when the source
is continuous there. Time partitions retain every endpoint. A positive
separation lower bound certifies a cell, and a nonpositive or unavailable
bound retains uncertainty. This is the product currently implemented by
`cover_penumbra_exclusion`. The earlier two constructive same-ray
witnesses remain the presence controls.

## Event-wide boundary enclosure

For the central region the spheres have common external tangents. Define
`s=(Rs-Rm)/|M-S|` and `c²=1-s²`. For a site P let
`z=(P-M)·e` and `rho=|(P-M)×e|`. In a plane through P and the two centres,
the two spherical caps touch internally only on those tangents. Their
cross-section equation at depth z is
`c² rho²=(Rm-s z)²`. At zero transverse distance the two caps have a
common centre, so at least one contains the other. As transverse distance
increases without bound the two caps become disjoint because the spheres
have separated centres with `|M-S|>Rs+Rm`. This determines the containment
sign on both sides of the only nonnegative radial root. At the apex it
includes the degenerate zero-radius case. The forward-depth guard keeps
every point of the Earth behind the Moon, on the acute branch, with
separated foreground depths.

The central predicate is `(Rm-s z)²-c² rho² >= 0`. The daylight predicate
is `S·Q P-1 >= 0` with Q the WGS84 ellipsoid metric. The computation
rotates the cone axis and its transverse moment using the same bounded
rotation. The two signs are evaluated on the six closed surface charts.
Each chart point has `P = D q / |q|` for `D=diag(a,a,b)`. Multiplying the
predicates by positive powers of `|q|` gives the corresponding bounded
chart expressions.

The validation runner first covers the full time interval with active or
strictly excluded tiles. Active tiles retain raw DE441 words, clock and
orientation identities and enclosing state jets. A smooth tile can use
Taylor bounds. A source or policy seam uses direct value bounds. Openings
and horizon equalities are retained through subdivision. A child inherits
the complete list of possible times from its parent. Its strict interior
proof supplies a common time for its full surface rectangle. Its strict
exterior proof excludes all remaining times for the full rectangle. The
binary64 operations in the offline validation script round interval
endpoints outward, and the frozen source intervals use rational arithmetic.

Every boundary point must occur in a retained band cell because strict
inclusion and strict exclusion cannot contain a boundary point. Each
retained cell also carries the guarantee that its points are within a
measured geodesic distance of both an interior and an exterior witness.
The scaled-sphere chart bounds certify these distances. A geodesic to the
opposite side must meet a boundary, which gives a two-sided Hausdorff
bound between the band and the actual boundary. The nearest-neighbour
search only proposes witnesses. The certificate bounds the distance to
each chosen witness independently of the search's numerical accuracy.
This boundary product has a measured spatial resolution. Instantaneous
cone and horizon arrangements and time-stamped section limits have their
own evidence.

Replay the validation from `C:\dev\moira` with the project's interpreter,
the accepted solar discovery index and the pinned DE441 file. NumPy and
SciPy are confined to the offline validation command.

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:MOIRA_KERNEL_PATH = $de441Path
$stage7Arguments = @(
    '--solar-discovery', $solarDiscoveryCsv,
    '--out', $newEvidenceDirectory,
    '--kernel-sha256', '9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5'
)
.\.venv\Scripts\python.exe -B scripts/eclipse_catalog/solar_path_enclosures.py @stage7Arguments
```

## Geographic width and publication conventions

The geographic section uses the differentiated WGS84 near-axis
intersection and the central plane perpendicular to its local track at
the reference point. Differentiating the implicit TT/TDB clock gives
`d(TDB)/d(TT)=1/(1-F'(TDB))`, where F is the pinned NAIF periodic
correction. The converged interval already encloses both arguments needed
to bound F'. This local rate tightens the direction of the geographic
plane without changing positions or using a rounded finite difference.
When the nominal section resolution is too coarse, the solver refines
the two limit bands inside the same budget and intersects the resulting
width enclosures. Strict signs and an enclosed arc integral give the
reported bounds.

Espenak and Meeus give the catalog's width at the axis intersection and
the greatest-eclipse epoch. The path keys associate widths with the
central-line entry and its UT1. For off-axis circumstances the NASA 2009
bulletin uses the width with a perpendicular distance from the central
line. The plotted event limits and the instantaneous shadow axes have
separate definitions. [NASA catalog, §1.2.15](https://ntrs.nasa.gov/api/citations/20080040150/downloads/20080040150.pdf),
[NASA path and physical tables](https://eclipse.gsfc.nasa.gov/SEmono/reference/explain.html),
[NASA 2009 bulletin, §1.7–1.8](https://eclipse.gsfc.nasa.gov/SEpubs/20090722/TP214169a.pdf),
[EclipseWise path key](https://www.eclipsewise.com/solar/SEhelp/SEpathkey.html).

Michailov derives the local linearized support width of the translating
shadow ellipse perpendicular to the central-line direction. In Besselian
units put `u=x'-xi'`, `v=y'-eta'`, `n²=u²+v²` and
`L=l2-zeta*tan(f2)`. The absolute width in kilometres is
`2 a |L| / sqrt(zeta²+(x u+y v)²/n²)`. The derivation locally holds the
geocentric radius constant and distinguishes the ellipse's supporting
line from a chord through its centre. Mucke and Meeus give a related
approximation and explain its loss of reliability at low altitude.
The physical meaning of the table's central-line cross-track quantity
and the numerical compatibility of its published values can therefore be
checked separately. [Michailov 1931, pp. 49–52](https://articles.adsabs.harvard.edu/pdf/1931AN....243...49M),
[Mucke §14 and Example 9](https://web.astroverein.at/downloads/astroverein.at/SFS1999_AstronomischeFinsternisse.pdf),
[Explanatory Supplement §8.3553](https://archive.org/stream/131123ExplanatorySupplementAstronomicalAlmanac/131123-explanatory-supplement-astronomical-almanac_djvu.txt).

The printed-input comparison covers 424 NASA widths across six events
and 17 EclipseWise widths across the 2003 and 2044 one-limit events. It
treats printed coefficients, times and widths as rounded to the nearest
last printed digit. Each published value's rounding interval overlaps
the interval calculated from its published inputs.
Both tested declination-rate treatments fit the available printed
resolution. The comparison uses the publisher's own time conversion,
including the midnight crossing in 2012, distinguishes greatest-eclipse
and greatest-duration rows, and retains two rounded near-horizon inputs
whose boxes include possible loss of the axis. This evidence supports the
documented convention within the tested publications and precision.

The 2003 NASA bulletin explicitly describes a terminator limit and leaves
its table widths blank. The later NASA web table prints 4,678 km at
04:08 UT. Its two printed limit coordinates have a straight latitude and
longitude route of under 3,140 km even using an upper bound for both
geodetic scales. The web width consequently cannot be the geographic
distance between those same-row limits. The bounded Moira metric, the
printed source values, and an omitted bulletin field each keep their
original semantics. [NASA 2003 bulletin](https://eclipse.gsfc.nasa.gov/SEpubs/20030000/text/section1.html),
[NASA bulletin Table 1.3](https://eclipse.gsfc.nasa.gov/SEpubs/20030000/tables/table_1.3.html),
[NASA web path table](https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2003May31Apath.html),
[EclipseWise 2003 path](https://eclipsewise.com/solar/SEpath/2001-2100/SE2003May31Apath.html),
[EclipseWise 2044 path](https://www.eclipsewise.com/solar/SEpath/2001-2100/SE2044Feb28Apath.html).
