# Source-qualified hypothetical constructions

`moira.hypothetical` adds opt-in mathematical constructions and explicitly
qualified historical models. Admission here means a reproducible calculation
under the recorded choices. It does not assert the existence of a body or
validate an astrological interpretation. Default chart bodies and the Hamburg
catalog remain unchanged. The earlier [derived-point models](DERIVED_POINTS.md)
remain available separately.

## Supported products and required choices

| Model ID | Product | Required realization choices |
|---|---|---|
| `arta_timashev_four_points` | All four equivalent Arta points | Supplied node/apogee longitudes, their model and common frame |
| `arta_timashev_osculating_set` | Arta from Moira geometric osculating Moon/Earth | UT1 epoch, output orbital frame and planetary kernel |
| `selena_seven_year_anchored` | Uniform seven-year symbolic longitude | Anchor epoch and longitude, year length, clock, frame |
| `abramov_calendar` | Literal rounded annual-plus-daily approximation | Epoch, clock, source-frame interpretation |
| `abramov_julian_year` | Continuous annual-increment approximation | Epoch, clock, source-frame interpretation |
| `waldemath_koch_quoted_2006` | Prescribed ellipse from Koch's quoted elements | Source equinox and Berlin-local-minus-UT1 clock offset |
| `weston_stahl_1968` | Explicit Weston/Stahl revision | Source equinox and year length |
| `harrington_1988` | Printed nominal Planet X example | Historical frame/clock/date-hour/year policy |
| `adams_1846_second_hypothesis` | Adams's second planar Neptune prediction | Historical policy and historical Uranus distance/period scales |
| `leverrier_1846_gould_1850` | Le Verrier prediction as transcribed by Gould | Historical frame/clock/date-hour/year policy |
| `planet_nine_fienga_2016_scenario` | Selected point on Fienga's trial ellipse | True anomaly and source-equinox realization; no phase epoch |

Discover these with `hypothetical_catalog()` and
`GET /v1/hypothetical/catalog`. Exact IDs select exact products. An unspecified
`Vulcan`, `Proserpina`, `White Moon`, `Lilith`, or `Planet X` does not select one
of them. No new physical NAIF identity or default orb is assigned.

Required policy fields are deliberate. A source that specifies only a period
does not establish an absolute phase; a historical date does not establish a
time of day or TT/UT1 convention; an element table without a verified equinox
does not establish J2000 axes. Callers supply those choices and results retain
them. This supports reviewable realizations without inventing source facts.

## Arta: the full fourfold construction

[Albert Timashev's original explanation](https://astrologer.ru/book/light_moon/index.html.en)
defines the construction

```text
L = lunar_node + 7/4 * (lunar_apogee - solar_apogee + 180 degrees)
```

Changing an input's angular lift by 360 degrees changes the result by a
multiple of 90 degrees. `arta_four_points()` therefore returns the complete
sorted set, never a privileged single branch. The sorted indices do not name
persistent points across time. No distance or speed is fabricated. The Arta
symbol is `U+2BDF` (⯟), used here for the construction as a whole.

`arta_osculating_set_at(jd_ut, frame=..., reader=...)` uses strict orbital
elements of the Moon relative to Earth and Earth relative to Sun, in the same
requested frame and at identical bound TT/TDB epochs. The lunar apogee is
opposite the lunar pericenter. The geocentric **solar apogee is along Earth's
heliocentric pericenter direction**: reversing the Earth-Sun vector swaps the
apsidal directions. Confusing that point with Earth's aphelion would shift
the fourfold construction.

Both source orbits and their complete provenance survive transport. Undefined
nodes, undefined apsides, non-elliptic input orbits, or mismatched clocks/frames
fail explicitly. These are geometric inputs, without apparent-place
corrections. This modern Moira realization does not certify Timashev's original
DE403 tables or solve the unresolved canonical single-point branch.

## Selena: anchored uniform seven-year motion

[Velichko and Larin, pp.17-18](https://djvu.online/file/lBJKQiKf9n4Gd)
describe uniform seven-year motion and distinguish the separate
seven-years-minus-fifteen-days version. The admitted construction is

```text
longitude = anchor_longitude + 360 * (epoch - anchor_epoch) / (7 * year_days)
```

The result is normalized to a full turn. `selena_seven_year_at()` requires the
anchor, `year_days` (365 through 366 days), `ConventionClock.TT` or `UT1`, and a
frame label. It does not silently borrow a phase or fictitious distance from
another engine. Selecting 365.25 means exactly seven Julian years; selecting
365.2425 is a different realization and remains visible in the receipt.
The anchor and requested epoch must use the same selected clock. The symbol is
`U+2BDD` (⯝). Selena is separate from every lunar-perigee product.

There is no automatic canonical-phase ephemeris in this product. Frame labels
describe the selected symbolic longitude convention; they do not request a
precession, nutation, or apparent-place transform of a physical object.

## Abramov Proserpina: two named approximations

[Valentin Abramov's own specification](https://www.geocities.ws/rognavaldre/proserpina.html)
gives a 170.73-degree heliocentric anchor on 1 January 1900, a 0.5105-degree
annual increment, and a 0.0014-degree daily increment. These rounded increments
are inconsistent if interpreted as one exact continuous uniform orbit.

- `ProserpinaRule.CALENDAR` uses proleptic Gregorian years after 1900 and
  zero-based days since January 1, preserving the declared January 1 anchor.
  It preserves the literal annual-plus-daily formula, including small jumps
  at year boundaries (0.0005 degrees after a common year and 0.0019 after a
  leap year).
  Calendar evaluation uses Moira's admitted long-term epoch interval, keeping
  the shared native calendar conversion within its supported numerical domain.
- `ProserpinaRule.JULIAN_YEAR` uses only the 0.5105-degree annual increment,
  with continuous 365.25-day years measured from the same anchor.

The selected clock and source-frame interpretation are required; the source
does not supply a verified equinox or time scale. The output is a heliocentric
longitude approximation, with no generated radius or geocentric reduction.
Choosing a frame label does not transform the formula's longitude. The symbol
is hypothetical Proserpina `U+2BD8` (⯘), separate from asteroid (26) Proserpina
and the 665-year Avestan convention.

## Prescribed orbital geometry

`PrescribedHypotheticalOrbit` holds named scalar elements, independent angular
rates, origin, epoch, clock, source equinox, source URL and location, and the
realization choices. No legacy external-engine element array is used.

`hypothetical_orbit_at(orbit, epoch_jd, frame=...)` solves
`E - e sin(E) = M` for an ellipse (`a > 0`, `0 <= e < 1`). Since the derivative
is positive, bounded bisection has a unique solution. Orbital-plane coordinates
are `a(cos E - e)` and `a sqrt(1-e²) sin E`. The ordinary inclination/node/
perihelion rotation gives the source vector. Moira's admitted frame matrices
then transform that vector through ICRF into the explicitly requested frame.
Source and target frame-model receipts are returned.
Identical source and target axes use the identity map directly, preserving
singular directions without a numeric frame round trip.

All coordinates are **geometric, central-focus-relative AU**, with no
light-time, aberration, gravitational deflection, observer translation, or
physical-state claim. A Sun-relative orbit does not become geocentric because
its output frame is true ecliptic of date. Frame validity limits and clock
conversion errors remain visible. UT1 source motion uses the source's UT1
clock, while frame evaluation uses its converted TT epoch.

### Koch's quoted Waldemath elements

[Dieter Koch's May 2006 explanation](https://groups.io/g/swisseph/messages?after=1149253069000000000&index=979&page=588&subsort=1)
quotes a table supplied through Graham Dawson and David Walters. Koch states
that he had not inspected Waldemath's original publication. This API therefore
identifies itself as **Koch quoted-elements realization**, not an independently
verified 1898 reconstruction or a replica of Swiss Ephemeris output.

The source gives sidereal, anomalistic and draconitic periods of 119.227434,
120.5915 and 118.003952 days. The admitted prescription is

```text
M_rate     = 360 / anomalistic_period
peri_rate  = 360 / sidereal_period - M_rate
node_rate  = 360 / sidereal_period - 360 / draconitic_period
```

The quoted rounded daily mean motion is retained in the receipt; the sidereal
period has priority when the two differ slightly. The quoted synodic period
177.005093 days is retained as source information, not independently imposed
as an extra angular rate.

Perigee is anchored at Greenwich noon on 8 April 1898; the descending node
315°13′ is anchored on 3 February 1898 at 18:27 Greenwich and converted to the
ascending node by 180 degrees. Mean longitude is 214.73 degrees at Berlin noon
on 1 January 1898. `berlin_local_minus_ut1_hours` is required: zero selects a
Greenwich-clock reading, while approximately 0.893333 hours selects Berlin
local mean time at 13°24′ east. Source equinox is also required.

The selected distance is 1,026,000 km (the quoted approximately 2.67 lunar
distances), eccentricity 0.1587, inclination 2.5 degrees. This is a prescribed
Earth-centered ellipse; its period is not recomputed from that distance and a
physical Earth GM. It does not denote lunar-apogee Lilith or asteroid Lilith.

### Weston/Stahl Vulcan

[Carl Stahl's 1968 revision](https://www.innergarden.org/spagyria/vulcan/vulcan.html)
provides the selected source variant. It is kept separate from Weston's other
editions, later software realizations, Baker's longitude rule and Hamburg
Vulkanus. The relevant source locations are the elements on p.16 and revised
tables on p.19 onward.

The selected mean longitude is 265°34′27″ on January 0, 1900. This realization
uses Greenwich astronomical noon (JD 2415020.0 UT1). The refined prescribed
daily increment is 19°22′17.1138″. The model keeps `a=0.13744 AU`, `e=0.019`,
inclination 7.5 degrees and fixed perihelion longitude 10 degrees. The descending
node 92°55′ on 25 June 1907 is realized at noon and regresses 18°42′21″ per
selected year. Source equinox and year length are explicit inputs.

The numerical reconstruction reproduces Stahl's 1907 worked-example **mean
longitude** within the rounding of the printed 1900 anchor. It does not claim
to reproduce every tabular geocentric longitude or every Weston edition. The
prescribed rate is retained instead of substituting a Keplerian rate derived
from the semimajor axis.

### Historical predictions

`HistoricalRealization` requires source equinox JD(TT), source clock, epoch
hour, and year length. Historical date-only anchors are realized under this
policy and the result records it.

- **Harrington 1988:** original [AJ paper, p.1478](https://articles.adsabs.harvard.edu/pdf/1988AJ.....96.1476H).
  Perihelion date 6 August 1789; `a=101.2 AU`, `e=.411`, inclination 32.4°, node
  275.4°, argument of perihelion 208.5°. The printed 1019-year period controls
  motion; it is not replaced from `a`. This is the author's nominal example,
  not a unique recovered orbit or a present discovery claim.
- **Adams 1846, second hypothesis:** [original paper, p.25, section 48](https://archive.org/download/anexplanationob00adamgoog/anexplanationob00adamgoog.pdf).
  `a_Uranus/a=.515`, eccentricity .120615, mean longitude 323°02′ and perihelion
  299°11′ on 6 October 1846. This is explicitly planar. Historical Uranus
  semimajor axis and sidereal period are required, rather than silently
  substituting modern values; the rate ratio is `.515**(3/2)`. These supplied
  period days determine its motion, so the policy year length is not used to
  rescale that period.
- **Le Verrier 1846:** [Gould's 1850 Smithsonian report, p.21](https://www.e-rara.ch/download/pdf/29059152.pdf)
  is the explicitly named contemporary transcription used here. It gives
  `a=36.1539 AU`, `e=.10761`, period 217.387 years, and mean anomaly 34°01′56″
  on 1 January 1847. The 1800 perihelion 284°05′48″ is advanced by the table's
  39′20″ precession, giving a consistent 1847 mean longitude 318°47′04″.
  This is a planar historical prediction, not the modern Neptune orbit.

### Planet Nine scenario

[Fienga et al. 2016, arXiv v3, Table 1](https://arxiv.org/pdf/1602.06116v3)
gives a trial ellipse with `a=700 AU`, `e=.6`, inclination 30°, argument of
perihelion 150°, and node 113°. The paper samples different positions around
that ellipse. `fienga_2016_planet_nine_scenario()` requires a selected true
anomaly and source-equinox realization and evaluates
`r = a(1-e²)/(1+e cos(nu))`. It returns no epoch or propagation law and does not
present a selected scenario as a current Planet Nine ephemeris.

## Python and REST access

All types and functions are exported from `moira`, `moira.facade` and their
owning module. `Moira` supplies datetime wrappers `arta_osculating_set()`,
`selena()`, `abramov_proserpina()` and `hypothetical_orbit()`. The wrappers
convert UTC into the selected TT/UT1 clock; Arta uses the instance-owned kernel.

```python
from moira import (
    ConventionClock, HistoricalRealization, OrbitalFrame,
    harrington_1988_orbit, hypothetical_orbit_at,
)

# The equinox, clock, date hour and year length below are selected policies,
# not claims that Harrington specified them in the printed nominal table.
policy = HistoricalRealization(2451545.0, ConventionClock.TT, 0.0, 365.25)
orbit = harrington_1988_orbit(policy)
geometry = hypothetical_orbit_at(orbit, 2451545.0, frame=OrbitalFrame.J2000_ECLIPTIC)
```

| Method | Path | Boundary |
|---|---|---|
| GET | `/v1/hypothetical/catalog` | Eleven explicit products; kernel-free |
| POST | `/v1/hypothetical/arta/from-longitudes` | Full supplied four-point construction |
| POST | `/v1/hypothetical/arta/osculating` | Geometric Moon/Earth inputs; kernel required |
| POST | `/v1/hypothetical/selena` | All anchor/year/frame/clock fields required |
| POST | `/v1/hypothetical/proserpina` | Explicit rule, frame and clock |
| POST | `/v1/hypothetical/orbit` | Discriminated five-model union; per-model policy fields |
| POST | `/v1/hypothetical/planet-nine-scenario` | Selected anomaly, without a fabricated epoch |

Requests reject extra fields, Boolean numeric inputs, nonfinite numbers,
unknown selectors, and omitted policy choices. OpenAPI retains the model
union and every required field. Existing validation and kernel-readiness error
envelopes are preserved. Source-qualified orbit responses retain the full
prescription and source/target frame model receipts.

## Validation and remaining exclusions

The tests check source anchors and the printed Stahl worked example, source
period/rate relations, the Gould equinox transcription, Adams's distance/rate
ratios, independent Kepler residuals including high eccentricities, elliptic
distance extrema, Arta's angular-lift invariance, true-clock geometric Arta
with actual DE441, API serialization, strict policies, and public exports.
No existing scientific fixture or tolerance is changed. No Swiss runtime or
cross-engine agreement is used as the primary numerical proof.

The source values and interpretations were reviewed on 26 October 2026.
Lowell and Pickering's particular historical solutions, the 665-year Avestan
Proserpina family, unspecified Waldemath/Sepharial/Jay variants, and the other
previously held bodies remain outside this calculation catalog. They require
their own source admission. A canonical single-point Arta, a universal Selena
phase, and a generic current Planet Nine position remain unclaimed.
