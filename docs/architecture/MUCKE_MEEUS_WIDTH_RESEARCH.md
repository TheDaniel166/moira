# Research: central-path width approximation

**Status: research only.** This note describes a published tangent-plane
approximation and an independent numerical experiment. It does not establish
NASA or EclipseWise's internal width algorithm and does not admit a numeric
geographic path width for an otherwise unavailable Moira path.

## Source and mathematical contract

Hermann Mucke's 1999 Vienna seminar paper, presented on behalf of himself and
Jean Meeus, gives a width perpendicular to the central-line motion in §14:
[Astronomische Finsternisse](https://web.astroverein.at/downloads/astroverein.at/SFS1999_AstronomischeFinsternisse.pdf).
The equation and example 9 appear under the paper's eighth and ninth
continuation headings; the collection's contents places the paper on pages
49–74. The continuation numbering implies pages 57–58, although page images
could not be independently inspected. Example 11 appears under the eleventh
and twelfth continuation headings. The paper explicitly calls the width
formula approximate and cautions that it is less reliable at low solar
altitudes.

For its instantaneous Besselian elements, let X, Y, and L₂ be measured in
Earth equatorial radii, D and μ in degrees, X₁ and Y₁ in Earth radii per
hour, μ₁ in degrees per hour, and tan F₂ dimensionless. With angles converted
to radians inside trigonometric functions, the equations can be written:

```text
ω  = 1 / sqrt(1 − 0.006694385 cos² D)
p  = μ₁ π / 180
b  = Y₁ − p X sin D
c  = X₁ + p Y sin D
B  = sqrt(1 − X² − (ωY)²)
L′ = L₂ − B tan F₂
a  = c − p B cos D
n² = a² + b²
K² = B² + (Xa + Yb)² / n²
W  = 12756 L′ / sqrt(K²) km
```

The paper uses a signed width: negative for total, positive for annular.
Magnitude is `abs(W)`. The 12,756 km factor is its nominal equatorial Earth
diameter, not a measured extent of a shadow on the globe. The method requires
an admitted visible central-axis intersection and nonzero motion and
denominator; no-axis, horizon-limiting, invalid or non-finite inputs must not
be given a numeric result. Close to these boundaries, a finite number alone
does not establish useful accuracy.

The 1992 [Explanatory Supplement to the Astronomical Almanac, §8.3553](https://archive.org/stream/131123ExplanatorySupplementAstronomicalAlmanac/131123-explanatory-supplement-astronomical-almanac_djvu.txt)
also describes a perpendicular-to-motion estimate and attributes its
equation 8.3553-5 to Mikhailov (1931), but the available OCR of that equation
is damaged. NASA's [2010 eclipse publication](https://eclipse.gsfc.nasa.gov/SEpubs/2010/TP214171a.pdf)
points to the Supplement and Meeus for calculation details. Its
[2006 publication](https://eclipse.gsfc.nasa.gov/SEpubs/20060329/text/section1.html)
identifies the published width with the central-line location while listing
instantaneous shadow major and minor axes separately. These references do not
prove that a specific NASA or EclipseWise table used this precise equation.

## Independent worked examples

A scratch implementation of the §14 equations was tested against the
paper's 1963 July 20 examples. For example 9 at 21:44 ET, using its rounded
input elements yields B = 0.419335, L′ = −0.00433905, n = 0.516151 per hour,
K² = 0.459935, and signed W = −81.613 km, which rounds to the published
82 km total-eclipse width. Example 11 gives independently derived auxiliaries
X = 0.68764, Y = 0.59231, B = 0.41744, L′ = −0.00433, a = 0.50334, and
b = −0.11795; their direct substitution gives −81.455 km, rounding to the
published 81 km. Its auxiliary-rate method is not identical to simply applying
example 9's approximate rate formula to the same nominal epoch.

The scratch suite also checks the overhead symmetric limit, computed zero at
an apex, absence of a central-axis intersection, zero relative motion, horizon
and non-finite input. Ten tests passed. The scratch code is not shipped as a
runtime product.

## Moira comparison and limitations

Moira's public instantaneous `SolarBesselianElements` exposes X, Y, D, μ,
L₂, tan F₂, UT1 and TT, but not the hourly rates. A research adapter estimates
rates with symmetric evaluations at UT1 offsets, uses the corresponding TT
separation as the denominator, and unwraps μ. These rates are numerical
estimates; step-size agreement is not an independent accuracy bound and no
whole-event root or model uncertainty is certified.

The following values use Moira 6.14.1, native DE441, zero-elevation WGS84,
native light-time/radius policy and nominal 30-second finite-difference steps.
They are cross-model comparisons, not matched-input or exact validations:

| Epoch UT1 | Native Sun altitude | Research approximation | Published reference |
| --- | ---: | ---: | ---: |
| 2003-05-31 04:08 | 2.93° | 4,457.82 km | [EclipseWise 4,654 km](https://eclipsewise.com/solar/SEpath/2001-2100/SE2003May31Apath.html); [NASA web table 4,678 km](https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2003May31Apath.html) |
| 2044-02-28 20:24 | 3.67° | 2,241.69 km | [EclipseWise 2,273 km](https://www.eclipsewise.com/solar/SEpath/2001-2100/SE2044Feb28Apath.html) |
| 2017-08-21 18:26 | 63.90° | 114.50 km | Different epoch/model conventions apply |

For the 92 previously investigated events, a fresh native greatest-eclipse
sample found all 92 had native central-axis intersections, with Sun-centre
altitudes approximately 0.026°–12.941° and median 5.663°. This is a different
statement from an external catalog's noncentral classification. The native
−500-05-29 short-axis case produces an extrapolated approximately 549,566 km
at a 0.026° solar altitude. That number exceeds Earth's size many times over;
it is not a possible geographic path width. Across the 92 samples, 2–60 second
derivative-step spread had median about 0.0000033 km and maximum about 0.425 km
for that same case. Numerical repeatability does not repair the approximation's
geometric breakdown.

The approximation therefore remains research only. A future explicitly named
diagnostic would need provenance, a verified rate policy and conditioning
status, separate handling of omitted and undefined values, and conspicuous
disclosure of the small-Sun-altitude/extrapolation limitation. It must not
replace Moira's legacy geometric width, identify the instantaneous footprint
with the event-wide union, or claim NASA/EclipseWise compatibility without
matched model inputs and a verified source definition.
