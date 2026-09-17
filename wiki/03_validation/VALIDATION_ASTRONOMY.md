# Astronomy Validation: Methods, Results, and Limits

**Version:** 2.0

**Date:** 2026-08-13

**Engine:** Moira 6.1.0

**Calculation baseline:** `68544ae1403009e3b25c30554992acb48790487c`

**Validation runtime:** Python 3.14.3

**Planetary kernel:** JPL DE441

**Overall status:** partially validated; every result below is product-specific

## Abstract

Moira does not have one universal astronomy-accuracy number. Its astronomy
layer contains different products—reference-frame transformations, planetary
places, event searches, eclipse circumstances, occultation paths, rise/set
times, and visibility models—and each product has its own authority, frame,
time scale, correction regime, corpus, and acceptance envelope.

The strongest current numerical results are:

- 120 apparent geocentric major-body comparisons against JPL Horizons pass a
  `0.35 arcsecond` angular and `0.1 km` distance gate. The recorded maxima are
  `0.277781 arcsecond` and `0.066846 km`.
- 80 geometric ICRF vector comparisons against JPL Horizons pass a
  `0.001 arcsecond` angular and `0.01 km` vector-difference gate. The recorded
  maxima are `0.000021829 arcsecond` and `0.002937 km`.
- IAU 2006/2000A frame and Earth-rotation functions agree with their matching
  ERFA functions within `0.001 arcsecond` across the declared test epochs.
- NASA/GSFC, JPL Horizons, IOTA, USNO, and source-specific visibility corpora
  validate named eclipse, occultation, rise/set, and visibility slices. They do
  not establish universal event accuracy outside those slices.

The two planetary suites now enforce exact target identity and exact
ephemeris-epoch identity. Older planetary residuals that mixed planet centers
with system barycenters or sent a different time basis to Horizons are retired
and are not evidence about Moira's accuracy.

## 1. How to read this paper

The word **validated** means only that a named product satisfied a named gate
over a named corpus. It does not mean every body, epoch, observer, kernel, or
public API route has the same error bound.

Every quantitative claim should answer these questions:

1. What object was compared?
2. Which authority or independent evidence governed that object?
3. What body identity, origin, frame, time scale, and correction regime were
   used?
4. How many cases were exercised?
5. What units and acceptance threshold were enforced?
6. What remains outside the claim?

If one of those answers is absent, the statement is not a complete accuracy
claim.

### 1.1 Evidence classes

| Evidence class | What it establishes | What it does not establish |
|---|---|---|
| Authority validation | Agreement with a product-relevant primary standard or publication under matched semantics | Accuracy outside the named corpus or the authority's own model |
| Cross-model comparison | A bounded difference between two explicitly different models | Same-model parity or a physical uncertainty estimate |
| Cross-engine corroboration | Agreement with another implementation | Primary scientific authority |
| Physical or structural invariant | Required geometry, ordering, continuity, conservation, or topology | External numerical accuracy by itself |
| Regression evidence | A result remains stable after it has been admitted | Independent truth |
| Native/Python differential | Two implementations of the same admitted computation agree | A second scientific oracle |
| Release-artifact evidence | A named artifact installs and reproduces its declared checks | Publication, deployment, or downstream adoption |

An acceptance threshold is a test gate, not automatically an uncertainty bar.
Catalog rounding, model-basis differences, source resolution, numerical search
tolerances, atmosphere variability, and observational uncertainty remain
separate quantities.

## 2. System under test and reproducibility

The results in this revision were reviewed against Moira 6.1.0 at calculation
baseline `68544ae`, using Python 3.14.3 and the discovered DE441 resource with
downloads disabled. The repository's `tests/KNOWN_ISSUES.yml` contained no
active entries at review time.

The two major-body maxima quoted in the abstract and Section 5 are dated
receipts from the isolated live Horizons run on 2026-08-13. The acceptance
thresholds and comparison contracts are executable tests; the observed maxima
are not promoted to frozen golden truth and should be refreshed with a later
live-oracle run rather than copied forward unexamined.

DE441 is the kernel used for the numerical results in this paper. Moira can
open other compatible SPK kernels, but this paper does **not** transfer the
DE441 residuals to DE430, DE440, or any other kernel without a separate run.

The test environment distinguishes three kinds of evidence:

- **Live external comparisons** query an authority such as JPL Horizons and
  require the explicit `external_network` test boundary.
- **Frozen authority fixtures** retain source URLs, query semantics,
  retrieval dates, units, and tolerances so the admitted comparison can run
  offline.
- **Internal invariants and regressions** require no external network and are
  never relabelled as external truth.

The calculation path under test is the Python-governed engine with its required
native computational substrate. Native/Python agreement is reported only
where a dedicated differential exists; it is not assumed for every product.

## 3. Results at a glance

| Product | Evidence and corpus | Enforced gate | Claim status |
|---|---|---|---|
| IAU frames and Earth rotation | Official SOFA C 2023-10-11 frame fixture plus secondary ERFA parity | Matrix-specific binary64 gates | Authority-validated on the named epochs and declared frame-router boundaries |
| Apparent geocentric major bodies | JPL Horizons; 10 targets × 12 epochs = 120 | `<= 0.35 arcsecond`, `<= 0.1 km` | Cross-model angle; same-target/same-epoch distance |
| Geometric geocentric major-body vectors | JPL Horizons; 10 targets × 8 epochs = 80 | `<= 0.001 arcsecond`, `<= 0.01 km` | Authority comparison of matched ICRF vector geometry |
| Topocentric apparent RA/Dec | JPL Horizons; 18 cases | Per-case RA `15–30 arcseconds`, Dec `4–12 arcseconds` | Authority-validated on the named sites/epochs; not an azimuth/altitude claim |
| Osculating orbital elements | Frozen exact-JDTDB JPL Horizons VECTORS and ELEMENTS; 4 calibration, 7 planet holdout, 6 catalog holdout cases | State `1e-5 km`; element gates from `2e-14` to `5e-10 degree` | Stage 1 authority-validated on the installed kernel subset; full 10,522-body runtime inventory passed; catalog authority admission and live drift audit pending |
| Heliocentric distance extrema | JPL Horizons vectors; 8 bodies | `<= 1 day`, `<= 3e-4 AU` | Authority-validated for the next local extrema in each case |
| Asteroid apparent ecliptic positions | Frozen JPL Horizons fixture; 203 cases, 61 bodies | `0.5 arcsecond` default; four named TNO exceptions at `1.5` or `5.0 arcseconds` | Product-specific authority fixture; not the planetary threshold |
| Delta T policies | Source-priority, continuity, policy, and compatibility tests | Product-specific invariants and source envelopes | Documented/partially validated; no universal Delta-T accuracy claim |
| Solar and lunar eclipses | NASA/GSFC catalogs, detailed products, and geometric invariants | Product-specific classification, time, coordinate, and topology gates | Authority-validated only for named catalog/product slices |
| Lunar occultations | JPL Horizons, IOTA, LOLA, cached Swiss cases, and invariants | Product-specific time/path/topography gates | Mixed authority, corroboration, and invariant evidence |
| Rise, set, and transit | Four frozen JPL Horizons cases plus USNO checks | `<= 2 seconds` on the Horizons corpus | Authority-validated on the named bodies/sites/windows |
| Yallop lunar criterion | Yallop 1997 Table 4; 295 rows | `q`- and boundary-family gates | Criterion validation, not guaranteed human sighting |
| Physical point-source visibility | Independent equations, libRadtran holdouts, external event goldens, invariants | 16-cell release matrix; 12 timed cells within `60 seconds` | Admitted only inside the declared clear-sky model and data-pack domain |

## 4. Reference frames, Earth rotation, and time

### 4.1 ERFA/SOFA-aligned functions

`tests/integration/test_erfa_validation.py` compares Moira with the matching
ERFA functions for:

- Gregorian/Julian calendar identity at two BCE anchors;
- Greenwich Mean Sidereal Time (`erfa.gmst06`);
- Earth Rotation Angle (`erfa.era00`);
- IAU 2006 mean obliquity (`erfa.obl06`);
- IAU 2000A nutation with IAU 2006 adjustment (`erfa.nut06a`);
- IAU 2006 precession (`erfa.pmat06`);
- the combined precession-nutation matrix (`erfa.pnm06a`);
- true obliquity; and
- Greenwich Apparent Sidereal Time.

Most comparisons use 12 epochs from 500 BCE through 2100 CE and enforce
`< 0.001 arcsecond`. Full `erfa.gst06a` GAST parity is separately enforced at
eight modern epochs from J1500 through J2100.

Before J1000, Moira's equation-of-equinoxes construction and ERFA's
equation-of-origins construction can differ by about `1.1 arcseconds`. That is
a declared model-basis difference. It is not described as ERFA parity, and it
is not dismissed merely because historical Delta T may be larger.

### 4.2 Time-scale boundaries

Moira keeps civil or caller-facing time separate from ephemeris time. Tests
bind astronomy calculations to the reader that supplies the relevant
ephemeris clock, and external comparisons send the resulting epoch with an
explicit Horizons time type.

Orbital Core Stage 1 makes the SPK boundary explicit: public reader methods
accept TT, convert exactly once with the official NAIF `naif0012.tls` implicit
TDB-minus-TT equation, and pass only TDB to raw segment evaluation. The frozen
time fixture records the NAIF source URL, 5,257-byte artifact and SHA-256
`678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b`.
Round trips are bounded to one binary64 ULP and strict orbital results expose
both numerical epochs and the conversion receipt.

The principal Delta-T policies are:

| Policy | Intended use |
|---|---|
| `hybrid` | Default source-priority table/scenario policy |
| `physical` | Explicit source-priority/scenario surface with uncertainty and accounting vessels |
| `nasa_canon` | Compatibility with NASA eclipse-publication conventions |
| `fixed` | Controlled sensitivity and reproducibility experiments |

`tests/integration/test_delta_t_hybrid.py` and
`tests/integration/test_delta_t_model_comparison.py` enforce policy routing,
source-priority identity, continuity, finite extrapolation behavior, and the
distinction between the canonical and physical paths. Those tests do not use a
fabricated Horizons or IERS fixture and do not claim one universal historical
Delta-T error.

For ancient eclipse comparisons, NASA catalog TT and Moira TT retain their own
declared Delta-T bases. The `360-second` ancient gate is a cross-authority
regression envelope, not an estimate of ancient timing uncertainty.

## 5. Planetary and small-body validation

### 5.1 Target identity is part of the result

The DE441 routes exposed by Moira do not all terminate at planet centers. The
Horizons target must match the final SPK target exactly:

| Moira body | Horizons target used in the major-body suites |
|---|---|
| Sun | `10` — Sun center |
| Moon | `301` — Moon center |
| Mercury | `199` — Mercury center |
| Venus | `299` — Venus center |
| Mars | `4` — Mars system barycenter |
| Jupiter | `5` — Jupiter system barycenter |
| Saturn | `6` — Saturn system barycenter |
| Uranus | `7` — Uranus system barycenter |
| Neptune | `8` — Neptune system barycenter |
| Pluto | `9` — Pluto system barycenter |

Both major-body test files contain an executable identity assertion against
`NAIF_ROUTES`. A comparison to `499`, `599`, or another planet center would be
a different product and cannot be mixed into these residuals.

### 5.2 Apparent geocentric positions

**Test:** `tests/integration/test_horizons_planet_apparent.py`

**Corpus:** 10 bodies × 12 epochs from 1900-01-01 through 2025-09-01

**Origin:** geocentric

**Moira reduction:** ICRF geometry reduced with IAU 2006 precession and IAU
2000A nutation

**Horizons product:** Earth-based apparent RA/Dec, quantity 2

**Epoch contract:** reader-bound ephemeris JD sent as discrete `TLIST` with
`TIME_TYPE=TT`

All 120 cases pass:

- angular separation `<= 0.35 arcsecond`;
- distance difference `<= 0.1 km`;
- recorded maximum angular separation `0.277781 arcsecond` for the Saturn
  system barycenter at the 1900 epoch; and
- recorded maximum distance difference `0.066846 km` for Mercury at the 1933
  epoch.

The angle is a cross-reduction-model comparison. Moira uses IAU 2006/2000A
true-of-date reduction, while the Horizons manual describes apparent quantity
2 using its EOP-corrected IAU 1976/1980 true equator and equinox of date. The
distance comparison is same-target and same-epoch.

### 5.3 Geometric ICRF vectors

**Test:** `tests/integration/test_horizons_planet_vectors_wide.py`

**Corpus:** 10 bodies × 8 epochs from 1800-06-24 through 2150-01-01

**Product:** geometric, uncorrected geocentric ICRF vectors

**Horizons correction:** `VEC_CORR=NONE`

**Epoch contract:** the same numeric ephemeris JD sent as discrete `TLIST`
with `TIME_TYPE=TDB`

All 80 cases pass:

- angular vector difference `<= 0.001 arcsecond`;
- absolute vector difference `<= 0.01 km`;
- recorded maximum angular difference `0.000021829 arcsecond` for the Moon at
  J2000; and
- recorded maximum vector difference `0.002937 km` for Mercury at J2000.

This isolates target and vector geometry. Orbital Core Stage 1 separately
locks the public-TT/private-TDB conversion and compares strict orbital states
at an identical frozen JDTDB instant; the older vector corpus is no longer
used as evidence for the clock boundary.

### 5.4 Retired planetary results

Earlier versions of this report published apparent residuals of
`0.577850 arcsecond / 1684.977 km` and vector residuals of
`0.762685 arcsecond / 10201.934 km`. Those comparisons mixed Moira
system-barycenter routes with Horizons planet centers and did not hold the
ephemeris epoch contract constant. They are comparator-contract defects, not
measurements of DE441 or Moira, and must not be reused.

### 5.5 Topocentric sky positions

`tests/integration/test_horizons_sky.py` contains 18 live Horizons cases for
the Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, and Pluto at Greenwich
and New York epochs. It compares topocentric apparent right ascension and
declination. Per-case gates range from `15–30 arcseconds` in right ascension
and `4–12 arcseconds` in declination.

The current test does not assert its stored azimuth and altitude tolerances.
Therefore this section makes no azimuth/altitude parity claim from that file.

### 5.6 Osculating elements and distance extrema

Orbital Core Stage 1 uses three disjoint, frozen JPL Horizons corpora generated
with exact `TLIST` JDTDB and explicit `TIME_TYPE=TDB` for both uncorrected ICRF
VECTORS and J2000-ecliptic ELEMENTS:

- four calibration cases: Mercury, Earth, Jupiter, and Earth-centered Moon;
- seven planet holdouts: Venus, EMB, Mars, Saturn, Uranus, Neptune, and Pluto;
- six catalog holdouts: Ceres, Hektor, Atira, Apophis, 1P/Halley, and 2P/Encke.

`tests/integration/test_orbital_elements_kernels.py` proves raw state, TT-wrapper,
element, gravity, time, frame, and source-receipt parity against the installed
kernel subset. Planet state coordinates are gated at `1e-5 km`; tight
field-specific element gates range from `2e-14` for eccentricity to
`5e-10 degree` for angles. `tests/integration/test_horizons_orbits.py` retains
an isolated live-primary drift audit and never rewrites accepted fixtures.

Orbital Core Stage 2 replaces the older sampled-distance comparison with a
frozen official JPL Horizons passage corpus and an isolated live-primary drift
audit. Horizons requests use geometric uncorrected ICRF VECTORS, exact TDB
epochs, and radial velocity `dot(r, v) / |r|`; sign crossings are refined and
confirmed by distances on both sides. The frozen planet gates are `1e-4 day`
for event time and `1e-9 AU` for distance. The disjoint calibration/holdout set
covers Mercury through the Pluto system, Earth versus the Earth-Moon
barycenter, Eros, Chiron, 1P/Halley in 2061, 2P/Encke, Sedna near its 2076
pericenter, and Eris near its 2257 pericenter.

Deterministic synthetic tests separately cover forward/reverse and exact-start
inclusion, explicit windows, flat radius, initially hyperbolic motion, fixed
evaluation budget, route gaps, an admitted continuous seam with an extremum
on the seam, and a rejected discontinuous seam. Real DE441 checks prove TT in
legacy `DistanceExtremes`, verified inverse UT1 in `PhenomenonEvent`, the
Earth-centered Moon rule, and the immutable route/evaluation receipt.

The ten installed DE441 planet/system cases pass those gates. The current
`moira-asteroids-wheel@2026.08.14.1` and
`moira-comets@2026.07.28.1` manifests do not contain a reviewed Stage 2
apsidal-passage accuracy admission or an exact Horizons target-solution
binding, so their six numeric authority comparisons are `NOT RUN`, not silently
accepted under wider gates. A separate runnable Eros search proves catalog
routing without substituting that smoke test for authority parity. Diagnostic
differences against the current fixture are retained in the Stage 2 receipt;
they range from microdays for Eros/Chiron to `0.104 day` for Halley and
`0.195 day` for Encke and may combine release-solution and interpolation
effects. A catalog release must bind and pass the frozen fixture before those
cases become acceptance evidence.

The packaged 25-asteroid wheel remains a fallback implementation check. On the
release host, the verified `moira-asteroids@2026.08.12.1` and
`moira-comets@2026.07.28.1` releases pass the full 10,522-body orbital-element
inventory gate. That runtime result does not substitute for the catalog
Horizons authority admissions or the live-primary drift audit, which remain
release blockers.

### 5.7 Orbital Core Stage 3 geometric nodes

Stage 3 removes the independent state, gravity, frame, and conic pipeline from
`planetary_nodes.geometric_node`. The public signature and `OrbitalNode` vessel
remain unchanged, but every result now adapts one strict
`osculating_elements` computation with a Sun center and
`TRUE_ECLIPTIC_OF_DATE`. The perihelion field maps the projected pericenter
vector longitude rather than the inclined-orbit dogleg `Omega + omega`.

Deterministic adapter tests prove exact field mapping, one core call, canonical
identity, Boolean-input rejection, typed failure when a required legacy-vessel
field is undefined, preservation of frame-range errors, and absence of the old
duplicate pipeline. DE441 integration covers Mercury through Pluto including
Earth; all nine results map exactly to their independently requested strict-core
result. Requests on either side of JD(TT) `2415020.0`--`2488070.0` fail with
`OrbitalFrameUnavailableError`.

The loaded representative checks map Ceres, Hektor, Atira, Apophis,
1P/Halley, and 2P/Encke exactly to the same true-date core and their receipted
catalog routes. The six frozen catalog-Horizons numeric cases remain `NOT RUN`:
the installed catalog manifests contain no reviewed Stage 3 admission bound to
fixture SHA-256
`d666f24fdc85dbaa5221acdfd619454ec4cd2bf41be2a9b3b9f14a5d1dd321dd` and its
unchanged acceptance gates. This prevents a catalog-solution mismatch from
being disguised as a looser code tolerance.

The inventory-wide Stage 3 check passes all 10,025 bodies in the verified
`moira-asteroids@2026.08.12.1` release and all 497 bodies in
`moira-comets@2026.07.28.1`. All 10,522 sovereign bodies receive finite node
checks, exact true-date mapping, canonical resolution, manifest/kernel receipt
checks, and coverage checks. The packaged wheel is present as a fallback but is
not substituted for either full-release gate.

### 5.8 Measured Stage 1 compatibility shifts

The Stage 1 compatibility harness replays the pre-change baseline
`29dd164c80c2a6788aa598a832eff3d4fd8e727a` and the implementation worktree
against identical, path-free resource identities. All 19 required probes are
green in both captures. The corpus covers raw reader routes, `planet_at`,
native and Python `all_planets_at`, a packaged asteroid and comet, transit and
fixed-star searches, eclipses, lunar geometry, phase and phenomena products,
end-to-end Shadbala, and four protected frame-consumer families.

The reader-clock receipt proves, to `1e-12` in the recorded state units, that:

- the old public result is reproduced by the candidate's explicit-TDB
  operation when given the old numeric argument;
- every candidate public-TT adapter equals exactly one TT-to-TDB conversion;
- a second conversion is observably different on every sampled raw route; and
- admitted native and forced-Python planetary paths agree within `1e-9`.

Across the heterogeneous reader-clock probes, 84 of 137 shared numeric fields
move and the largest raw absolute delta is `0.0017674416303634644`. These fields
mix kilometres, kilometres per day, degrees, Julian days, and derived doctrine
units, so that maximum is a change detector, not one physical error measure or
accuracy threshold.

The frame receipt compares 188 shared fields, of which 121 move; its largest
heterogeneous raw delta is `0.00237959623336792`. The direct matrix probe is a
frame-only comparison at fixed TT epochs. Planetary, eclipse, and lunar-geometry
probes deliberately show the combined clock and frame correction; their clock
component is separately accounted for in the reader-clock receipt. Frame truth
itself remains governed by the frozen official IAU SOFA 2023-10-11 matrices.

The focused Stage 1 gate and isolated 52-case element audit pass on this
worktree. The Stage 2 live exact-TDB event audit passes its Earth and Neptune
sentinels, including Neptune's first perturbed local maximum that the retired
`period/100` sampled-distance validator skipped. At the Stage 1 checkpoint,
release readiness was blocked by the then-unresolved full-asteroid prerequisite
and by a repository-wide non-network command that terminated in pre-existing
harness-import, hybrid-eclipse-topology, and asteroid fixture/resource failures
reproduced on the untouched baseline. The Stage 3 release-host inventory gate
later satisfied the full-asteroid prerequisite; the remaining live-primary,
catalog-admission, and inherited repository gates stay explicit. The plan's
exact changed-file Ruff command also reports the same 66 inherited
findings on candidate and baseline; the new Stage 1 files are clean when
checked separately. None of these conditions is represented as orbital
validation.

### 5.9 SPK routing and kernel scope

Moira resolves each body's NAIF chain and selects a segment that covers the
requested epoch. The planetary validation suites exercise those routes over
historical and future epochs, but passing output comparisons do not replace
the dedicated resource, segment-selection, cache-ownership, and provenance
tests.

The numbers in this paper belong to DE441. Kernel compatibility is an API
capability; numerical transfer to another kernel requires a new corpus run.

### 5.10 Asteroid positions use a separate acceptance policy

`tests/integration/test_horizons_asteroid_apparent.py` uses a frozen,
provenance-bearing Horizons fixture containing 203 cases across 61 bodies.
The default longitude/latitude gate is `0.5 arcsecond` for 57 bodies. Four
named distant TNOs have explicit kernel-solution allowances:

- Varuna and Quaoar: `1.5 arcseconds`;
- Orcus and Ixion: `5.0 arcseconds`.

These are asteroid-product thresholds. They do not inherit the current
`0.35 arcsecond` major-body apparent-position threshold, and agreement within
a widened TNO gate must not be described as shared planetary-pipeline
accuracy.

## 6. Eclipse validation

Eclipse validation is split by product. Classification, greatest-event time,
Besselian elements, central-path geography, visibility footprints, and lunar
contact instants are not interchangeable claims.

### 6.1 Catalog classification and search

`tests/integration/test_eclipse_nasa_reference.py` binds NASA/GSFC catalog
time semantics explicitly:

- 23 solar maxima across ancient, modern, and future eras are classified by
  event family;
- 15 lunar maxima across eras are classified by event family;
- all 229 NASA/GSFC lunar catalog rows from 1901–2000 are classified at their
  published TD/TT maxima, preserving the Danjon shadow convention;
- four modern solar event classes are recovered against NASA's separately
  published UT labels within `1 second`;
- the 2049 hybrid event is recovered within a named `30-second` cross-model
  gate; and
- representative ancient and future searches use separate `360-second` and
  `60-second` cross-authority regression envelopes.

The ancient gate is not an ancient-eclipse accuracy claim. It keeps distinct
Delta-T and ephemeris models visible while preventing silent regression.

### 6.2 Besselian elements and central paths

`tests/integration/test_eclipse_besselian_nasa_reference.py` compares four
NASA events—partial, total, hybrid, and annular—at five time offsets. Each
Besselian field has its own unit and tolerance; for example, `x`, `y`, `l1`,
and `l2` use `0.0001` Earth equatorial radii, while `d` and `mu` use separate
angular gates.

`tests/integration/test_eclipse_path_nasa_reference.py` validates four named
NASA path products. The gates include:

- greatest latitude `0.25 degree`;
- greatest longitude `0.5 degree` unless a fixture row names another limit;
- central path width `2 km`;
- central duration `5 seconds`;
- magnitude `0.005`; and
- central-axis separation `0.001 degree`.

Those tests do not claim dense ingress-to-egress track parity where NASA does
not publish a matching numerical product.

### 6.3 Solar partial-visibility footprints

`tests/integration/test_eclipse_footprint_nasa_reference.py` validates two
NASA/GSFC total-eclipse penumbral products, including the one-limit/two-limit
topology, contact order, sparse boundary anchors, and WGS 84 surface
invariants. The external-comparison ceilings are `5 seconds` for anchor time
and `40 km` for surface position. They cover a named DE200/LE200-to-DE441/LE441
comparison and source rounding; they are not NASA uncertainty estimates.

### 6.4 Lunar contact instants

`tests/integration/test_eclipse_lunar_contacts_nasa_reference.py` compares the
14 applicable P1/U1/U2/U3/U4/P4 instants in four modern NASA/GSFC detailed
figures on a common TT basis. Ordinary native and NASA-compatibility gates are
`120 seconds` and `10 seconds`. A magnitude-`0.0014` limiting event has
separate `240-second` and `30-second` gates and an independent duration check.

These are named mean-limb/shadow-model comparisons. They do not validate
site-specific observed lunar-limb contacts.

## 7. Occultation validation

Moira keeps three occultation evidence tracks separate.

### 7.1 Local event corroboration

`tests/integration/test_occultations_external_reference.py` compares local
Venus and Regulus lunar-occultation midtimes with cached Swiss `t.exp` rows at
the fixture's sites and altitudes, using a `180-second` gate. This is
cross-engine corroboration, not primary authority validation.

### 7.2 Modern/future nominal path geometry

`tests/integration/test_eclipse_occultation_where_reference.py` exercises
named live IOTA graze/limit slices for El Nath, Spica north and south, epsilon
Ari, Alcyone, Merope, Asellus Borealis, and Regulus. The admitted
graze-boundary latitude gate is `0.18 degree`. Site altitude is used when the
source declares it.

The polar-safe topology has a separate primary-authority case: the
2026-10-05 lunar occultation of Mars at the geographic North Pole.
`tests/fixtures/jpl_horizons_polar_occultation_reference.json` preserves
airless JPL Horizons rows with two `0.5-second` contact brackets. Moira's DE441
contacts must fall no more than `2 seconds` outside each bracket.

That fixture validates pole containment and the two pole-boundary contacts.
It does not externally validate the complete left/right tracks or total path
width; those are covered by spherical zero-clearance, continuity, ordering,
and great-circle invariants. The frozen Horizons Earth-orientation prediction
must be refreshed after the 2026-10-05 event when measured EOP data are
available.

### 7.3 Topographic lunar contacts

The topographic contact product is a distinct observed/profile-conditioned
surface. Its named two-site Spica slice combines IOTA reductions with official
USGS LOLA assets and finite-resolution lunar-limb reconstruction. That evidence
characterizes the admitted sites and profile resolution; it is not a universal
topographic-contact accuracy statement. Release-specific details remain in
`wiki/03_validation/RELEASE_VALIDATION_5_1_TO_5_2.md`.

Ancient occultation reconstruction is a separate historical-reduction program
and is not validated by the modern IOTA or polar-path corpus.

## 8. Rise, set, transit, and visibility

### 8.1 Rise, set, upper transit, and lower transit

`tests/fixtures/horizons_rise_set_reference.json` contains four frozen JPL
Horizons cases:

- the Sun in New York at the March equinox;
- the Moon in New York;
- Venus in Sydney; and
- the Sun in Tromso at midsummer, including explicit no-rise/no-set behavior.

The source tables were sampled at one-minute cadence and crossings were
interpolated. Every expected event is the first matching event in the next
24 hours from `jd_start`. `tests/integration/test_horizons_rise_set_reference.py`
enforces `2 seconds` for the four cases. Published USNO tables provide
supplemental fixed-star checks; cached Swiss rows remain secondary
corroboration.

The `2-second` result belongs to these bodies, sites, dates, altitude
thresholds, and window semantics. It is not a universal rise/set bound.

### 8.2 Historical Sothic evidence

The Sirius/Sothic slice uses Censorinus's 139 CE record and declared
latitude-order expectations. It is a bounded historical corroboration under an
explicit visibility doctrine and calendar uncertainty, not an exact observed
timestamp oracle.

### 8.3 Yallop lunar-crescent criterion

`tests/integration/test_visibility_validation.py` uses the 295 rows extracted
from Yallop 1997 Table 4. The admitted audit reports:

- 293/295 rows within `±0.03` in `q`;
- 295/295 within `±0.05`;
- 289/295 exact class matches; and
- all six class mismatches are boundary-sensitive adjacent-class cases.

Non-boundary rows use a `±0.035` `q` gate with exact class agreement;
boundary-sensitive rows use `±0.03` without a false exact-class promise.
Criterion agreement does not guarantee a human observation under arbitrary
weather, terrain, optical aid, or observer conditions.

### 8.4 Opt-in physical point-source visibility

The current authority for the opt-in
`clear_sky_naked_eye_point_source_v1` model is
[Physical Heliacal-Visibility Validation and Admission](PHYSICAL_HELIACAL_VISIBILITY_VALIDATION_2026-08-05.md).
The model combines primary equation checks, independent libRadtran holdouts,
a bounded Tousey-Koomen comparison, property/invariant tests, external event
goldens, native/Python differential evidence, and offline artifact checks.

Its Phase 7 release matrix has 16 cells: 12 independently reconstructed event
times and four explicit no-event/domain regressions. All 12 timed cells pass a
fixed `60-second` external-grid limit; the largest recorded engine/oracle
difference is `5.8789461851119995 seconds`.

That is numerical event-geometry evidence inside the exact clear-sky,
point-source, target-profile, observer-protocol, and data-pack domain. It is
not second-level human-visibility truth. Clouds, live weather, optical aids,
extended objects, generic stellar inference, global site transfer, and
observer-population probability remain excluded.

## 9. Limits and non-claims

This paper deliberately does not claim:

1. one universal Moira accuracy figure;
2. that passing cases prove all supported bodies, epochs, observers, or
   kernels;
3. that DE441 residuals transfer unchanged to DE430 or DE440;
4. that cross-model residuals are uncertainty estimates;
5. that the apparent Horizons suite is same-model frame parity;
6. that the geometric vector suite independently validates TT-to-TDB;
7. that the topocentric RA/Dec suite validates azimuth and altitude;
8. minute- or second-level observational visibility truth outside each named
   model and corpus;
9. dense eclipse or occultation track parity where no matching external
   numerical product exists;
10. universal topographic lunar-contact accuracy from two sites;
11. precise ancient event timing beyond the admitted Delta-T/model envelope;
12. that regression snapshots, benchmarks, native/Python agreement, or a
    clean artifact install are independent scientific authorities; or
13. that an engine result has been published, deployed, or adopted merely
    because its local validation passed.

The absence of one of these broad claims is not a hidden failure. It is the
boundary that keeps a narrower result scientifically meaningful.

## 10. Reproducing the admitted checks

Use the repository's project environment and disable downloads. On Windows:

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
```

Small offline examples:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_erfa_validation.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_horizons_rise_set_reference.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_eclipse_nasa_reference.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_occultation_polar_topology_horizons_reference.py -q
```

Live Horizons validation must be isolated to explicitly selected external
tests:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\integration\test_horizons_planet_apparent.py `
  tests\integration\test_horizons_planet_vectors_wide.py `
  -m external_network --run-external-network -q
```

The live suite depends on the current Horizons service and should record its
date, target identities, query semantics, and result envelope. A later run can
legitimately differ if the authority data, EOP inputs, or service behavior
changes.

Documentation and publication guards:

```powershell
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --check
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py --check
```

These documentation checks verify consistency and generated mirrors. They do
not rerun the scientific oracles.

## 11. Authorities and evidence records

Primary or product-relevant authorities used by the named suites include:

- [IAU SOFA](https://www.iausofa.org/) and its ERFA implementation for
  reference-frame and Earth-rotation algorithms;
- [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/) for target-identified
  vectors, apparent places, observer tables, and named contact evidence;
- [NAIF SPK Required Reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html)
  for SPK object and segment semantics;
- [NASA/GSFC Eclipse Web Site](https://eclipse.gsfc.nasa.gov/) for the named
  solar and lunar catalog and detailed-product comparisons;
- [IOTA](https://occultations.org/) for named modern occultation limit and
  observed-contact products;
- [USGS Lunar Orbiter Laser Altimeter](https://astrogeology.usgs.gov/search/map/moon_lro_lola_dem_118m)
  for the admitted lunar topography assets;
- [U.S. Naval Observatory](https://aa.usno.navy.mil/) for supplemental
  rise/set tables and observational-visibility cautions; and
- Yallop 1997 Table 4 and the source ledger named by the physical-visibility
  validation record for criterion and point-source model evidence.

Repository evidence records with more detail include:

- `wiki/03_validation/RELEASE_VALIDATION_5_1_TO_5_2.md`;
- `wiki/03_validation/PHYSICAL_HELIACAL_VISIBILITY_VALIDATION_2026-08-05.md`;
- `wiki/03_validation/PHYSICAL_HELIACAL_VISIBILITY_CAPABILITY_MATRIX.generated.md`;
- `wiki/03_validation/PHYSICAL_HELIACAL_VISIBILITY_API_INVENTORY.generated.md`;
- `tests/fixtures/eclipse_nasa_reference.json`;
- `tests/fixtures/eclipse_nasa_lunar_1901_2000.json`;
- `tests/fixtures/nasa_solar_besselian_reference.json`;
- `tests/fixtures/nasa_solar_penumbral_footprint_reference.json`;
- `tests/fixtures/nasa_lunar_contact_instants_reference.json`;
- `tests/fixtures/jpl_horizons_polar_occultation_reference.json`;
- `tests/fixtures/horizons_rise_set_reference.json`; and
- `tests/fixtures/physical_visibility_phase7_evidence_registry.json`.

## 12. Current status

This revision replaces the former mixed bug ledger with a current,
product-owned validation account. Historical defects are retained only where
they change how a published number must be interpreted—most importantly, the
retired planetary target/time mismatches. Open work belongs in the roadmap or
a dedicated dated evidence record, not in the current-results table.

The overall report remains **partial** because its component products have
different evidence maturity and because no finite corpus can prove every
supported astronomical condition. That status is a truthful boundary, not a
failure of the validated slices above.
