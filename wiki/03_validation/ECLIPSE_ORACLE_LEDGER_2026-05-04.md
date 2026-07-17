# Eclipse Oracle Validation Ledger

## 1. Record status

- **Original audit date:** 2026-05-04
- **Evidence correction:** 2026-07-17
- **Correctness and evidence update:** 2026-07-17
- **Besselian admission update:** 2026-07-17
- **Polar central-path admission update:** 2026-07-17
- **Target subsystems:** `moira.eclipse`, `moira.eclipse_besselian`,
  `moira.eclipse_geometry`,
  `moira.eclipse_canon`, solar path geometry, and the eclipse-facing portion of
  `moira.occultations`
- **Purpose:** Record exactly what the repository proves about eclipse
  geometry, catalog comparison, and numerical stability.

This correction supersedes the earlier blanket claim of "absolute physical and
mathematical sovereignty." That language exceeded the executable evidence.
The native model remains Moira's DE441-backed physical model in TT;
compatibility and external-reference checks are evidence about specified
products, not substitutes for native doctrine.

## 2. Evidence classes and current coverage

### A. Native geometric invariants

`tests/unit/test_shadow_oracle.py` exercises internal geometric invariants:

- penumbral radius exceeds umbral radius for the sampled geometry;
- cone radii respond monotonically to the sampled lunar distances;
- lunar magnitude increases as the shadow-axis offset decreases;
- grazing and anti-solar limiting cases behave consistently;
- runtime Besselian `x`/`y` projection reproduces the native shadow-axis
  distance;
- the east/north orientation, field ranges, cone ordering, and total/annular
  `l2` signs are explicit;
- the cone slopes and plane radii satisfy exact common-tangent geometry;
- the runtime Besselian vessel is immutable; and
- opposite-phase geometry fails instead of extending the solar shadow ray
  backwards through Earth.

These are physical and geometric invariant checks against the first-class
runtime surface. Dedicated primary-authority per-field evidence is recorded in
section 2E.

`tests/unit/test_eclipse_numerical_edges.py`,
`tests/unit/test_eclipse_contact_solver.py`, and
`tests/unit/test_eclipse_helpers.py` add numerical covenants for stable tiny
and antipodal separations, off-grid mean-limb tangencies, phase intervals
shorter than the coarse scan, truncated contact windows, exact-pole
canonicalization, pole crossing, and solar greatest-location refinement above
`89.5` degrees. These are invariant and adversarial tests. External polar-path
accuracy is established only for the named 2015 product in section 2C.1.

### B. NASA Five Millennium catalog comparison

`tests/fixtures/eclipse_nasa_reference.json` identifies its sources as the NASA
Five Millennium solar and lunar catalogs. The executable coverage is in
`tests/integration/test_eclipse_nasa_reference.py`:

- classification is checked at selected NASA catalog maxima across ancient,
  modern, and future epochs;
- representative searched events are compared on a common TT scale while each
  product retains its declared Delta-T basis; and
- the ancient 360-second and post-2150 60-second limits are explicitly
  cross-authority regression envelopes, not uncertainty or accuracy claims.

This slice validates catalog classification and bounded greatest-event timing.
It does **not** perform the runtime Besselian comparison; that dedicated
per-field evidence is recorded in section 2E. Solar path-product evidence is
recorded separately below.

### C. Named NASA solar path products

`tests/integration/test_eclipse_path_nasa_reference.py` compares Moira's public
solar-path vessel with four named NASA/GSFC products stored with source URLs
in `tests/fixtures/eclipse_nasa_reference.json`:

- 1999-08-11 total;
- 2000-02-05 partial;
- 2031-11-14 hybrid; and
- 2032-05-09 annular.

For each row, the executable comparison covers searched greatest-event timing,
global eclipse type, greatest latitude and longitude, and magnitude. The three
central rows additionally compare central-path width and central duration at
the solved greatest site. The native solar
search uses one Earth-reception light-time Sun/Moon shadow-axis policy; the
NASA products retain their own stated model and Delta-T basis. The named
tolerances are cross-model regression envelopes, not claims of identical
models or atlas-wide parity. The partial row validates the existing one-point
greatest-eclipse product, partial disk-overlap invariant, and a separately
named `0.6`-degree horizon-longitude envelope. NASA's displayed `0.0 km` and
`00m00s` are recorded as non-applicable display sentinels, not physical
central-path measurements; Moira's shape-stable zero fields are checked
separately as public-vessel invariants. No central line is invented for a
non-central eclipse.

This four-row slice does not validate a partial-eclipse footprint,
observer-elevation sensitivity, every sampled central-line point, full-track
ingress/egress geography, or exact solar grazing/tangent boundaries. The
separate polar product below does not widen those four rows implicitly.

### C.1 Authoritative polar central-path product

`tests/fixtures/nasa_solar_polar_path_reference.json` binds the official
NASA/GSFC 2015-03-20 total-eclipse WGS 84 path table to its paired Besselian
page under one declared lineage: JPL DE405, `Delta T = 67.6 s`, the published
`k1`/`k2` constants, and center-of-mass mean-limb geometry without lunar
topography. `tests/integration/test_eclipse_polar_path_nasa_reference.py`
compares Moira's independent DE441 result with that product.

The executable authority slice covers searched greatest time (`1 s`),
greatest and five named central-axis positions (`3 km`), both axis/ellipsoid
tangency endpoints (`3 km`), greatest path width (`3 km`), local central
durations (`3 s`), greatest magnitude (`0.005`), and cone clearance at each
available published north/south limit (`3 km`). The fixture preserves NASA's
missing north limit at 10:16 and 10:18 as `null`; the engine test proves those
epochs are not a closed two-limit width product and must fail explicitly
rather than publish an incomplete cone-arc span.

This closes the named authoritative polar-central fixture gap. It does not
establish full-atlas path parity, per-row width parity away from greatest,
observer-elevation behavior, lunar-topography timing, or the separate
one-limit/terminator-closure width product.

### D. Named NASA lunar contact-duration products

`tests/integration/test_eclipse_lunar_contacts_nasa_reference.py` compares the
native mean-limb contact solver with four named rows from NASA's 2001-2100
lunar catalog:

- 2023-05-05 penumbral;
- 2024-09-18 partial;
- 2025-03-14 total; and
- 2027-07-18 limiting penumbral.

The executable fields are greatest-event timing and the applicable P1-P4,
U1-U4, and U2-U3 phase durations. NASA publishes durations rounded to `0.1`
minute under VSOP87/ELP2000-82, Danjon enlargement, and catalog Delta-T; Moira
retains DE441 and its native clock policy. All four greatest-event comparisons
use a `120`-second cross-model timing envelope. The ordinary rows use a
`1.0`-minute cross-model duration envelope. The `0.0014`-magnitude 2027
limiting case uses a separately declared `5.0`-minute envelope: it proves that
the short penumbral pair remains resolved, not close timing parity at a
model-sensitive limit.

These rows validate phase durations, not the six individual published contact
instants. Mean-limb contacts remain distinct from topography-conditioned graze
or Baily's Beads products.

### E. NASA/GSFC solar Besselian per-field comparison

`tests/fixtures/nasa_solar_besselian_reference.json` records provenance-bearing
NASA/GSFC Besselian rows for representative partial, total, hybrid, and annular
solar eclipses. `tests/integration/test_eclipse_besselian_nasa_reference.py`
evaluates `EclipseCalculator.solar_besselian_elements(jd_ut1)` at five TT
epochs per event and compares every published runtime field: `x`, `y`, `d`,
`mu`, `l1`, `l2`, `tan_f1`, and `tan_f2`.

The named cross-model residual envelopes are:

- `x`, `y`, `l1`, and `l2`: `1.0e-4` Earth equatorial radii;
- `d`: `0.003` degrees;
- circular `mu`: `0.007` degrees; and
- `tan_f1` and `tan_f2`: `3.0e-6`, dimensionless.

This is primary-authority per-field cross-model validation, not exact model
parity and not an uncertainty budget. NASA's rows use VSOP87/ELP2000-82 and
their published `k1`/`k2` lunar-radius conventions. Moira retains DE441,
Earth-reception light-time Sun/Moon center-of-mass geometry, no stellar
aberration, and its physical mean-limb radii. The comparison therefore
measures the bounded residual between two declared models rather than tuning
the native model to the catalog.

### F. Swiss cross-engine corroboration

`tests/integration/test_eclipse_external_reference.py` uses the cached
`tests/fixtures/swe_t.exp` corpus for classification and searched-maximum
corroboration. `tests/integration/test_eclipse_occultation_where_reference.py`
checks one cached Swiss solar `where` row at a one-degree latitude/longitude
envelope.

Swiss is a secondary comparator. These checks do not establish primary-authority
Besselian parity, and the one-row `where` check does not validate atlas-grade
track shape, path width, magnitude, or central duration.

## 3. Corrected findings

### A. NASA Besselian evidence is bounded cross-model validation

The previous ledger claimed numerical parity for `l1`, `l2`, and the cone
angles for the 2017-08-21 and 2024-04-08 eclipses. It cited
`tests/integration/test_eclipse_besselian_audit.py`; that file does not exist in
the repository. Those unsupported residual, constant-basis, and sign-transform
claims remain withdrawn from the validation record.

The replacement evidence is the explicitly named surface, fixture, sample,
semantics, units, and per-field envelopes in section 2E. It validates the
DE441-native result against NASA/GSFC as a primary external authority under
declared model differences. It does not restore a claim of exact NASA model
parity, atlas-wide coverage, or field uncertainty.

### B. Small-angle precision is now covered by executable remediation

The earlier audit correctly withdrew an unsupported small-angle claim. The
current runtime uses a stable vector separation, and direct unit tests now
cover coincident, antipodal, longitude-offset, latitude-offset, and
sub-microdegree cases. This is numerical invariant evidence for the exercised
inputs; it is not a general external angular-position oracle.

### C. Five-epoch samples do not prove general temporal continuity

The invariant suite proves the bounded properties listed in section 2A. It
now has companion runtime evidence at five TT epochs for each of four named
events. Those discrete samples bound the published fields at the exercised
epochs; they do not by themselves prove smooth shadow-axis motion between the
samples, absence of solver jitter over arbitrary intervals, or continuity
across DE441 coverage boundaries.

## 4. Bounded 2026-07 remediation

The July repair now implements and exercises:

- small-angle separation stability;
- eclipse-contact root deduplication, search-window containment, positive-step
  validation, off-grid tangent admission, and sub-step phase recovery through
  an explicit signed-clearance pair solver;
- penumbral eclipse identity and `kind="any"` admission;
- signed NASA-compatible gamma and compatibility-model separation;
- explicit UT1-to-UTC reporting boundaries;
- local solar-eclipse overlap admission, including observer elevation;
- truthful central-duration semantics;
- deterministic, pole-safe observer-location search behavior on the closed
  geographic surface;
- DE441 shadow-axis/WGS 84 central-line and closed-footprint width geometry,
  including polar tangency endpoints, fail-closed spherical/WGS 84 centrality
  divergence, and explicit rejection of incomplete one-limit footprint spans;
- legal-latitude stellar-graze bracketing and directed north/south occultation
  band boundaries;
- named NASA partial-path and lunar phase-duration comparisons;
- the first-class instantaneous `SolarBesselianElements` vessel and
  `EclipseCalculator.solar_besselian_elements(jd_ut1)` engine method; and
- NASA/GSFC per-field Besselian comparisons for partial, total, hybrid, and
  annular events at five TT epochs each, plus the paired 2015 polar event.

The `Moira` facade, existing eclipse event and path vessels, REST endpoint
paths, request/response schemas, and native C++ substrate remain unchanged.
Their unchanged shape is a compatibility fact, not astronomical proof.

## 5. Current validation statement

The supportable statement is:

> Moira's eclipse subsystem has native geometric-invariant coverage, selected
> NASA catalog classification and TT search-regression coverage, four named
> NASA solar path-product comparisons spanning partial, total, hybrid, and
> annular events, one named NASA polar central-path comparison, four named NASA
> lunar phase-duration comparisons, and bounded cached-Swiss cross-engine
> corroboration. The instantaneous DE441-native Besselian surface has
> primary-authority per-field cross-model evidence for four representative
> event classes plus the paired 2015 polar event at five TT epochs each. Exact
> NASA model parity, full-atlas path validation, per-row polar width parity,
> and one-limit path-width closure are not claimed.

## 6. Remaining evidence work

- Extend Besselian evidence beyond the four named rows and five TT epochs before
  making broader temporal or coverage claims. The current residual envelopes
  are cross-model regression bounds, not exact parity or uncertainties.
- Extend path-product evidence to observer elevation, full sampled tracks,
  ingress/egress geography, solar grazing/tangent cases, and a governed
  one-limit/terminator-closure width product. The named 2015 polar central
  product and one-point partial product are covered; a full penumbral footprint
  requires a separately designed vessel.
- Compare individual P1/P4, U1/U4, and U2/U3 instants, not only phase
  durations, under matching timescale and mean-limb semantics.
- Keep model-sensitive limiting classifications visible. A local diagnostic
  found a classification difference at the 2015-04-04 near-limit event, but
  that observation is not yet a fixture-backed covenant. Do not force catalog
  type agreement unless an internal geometry defect is independently
  demonstrated.
- Keep mean-limb geometry distinct from lunar-profile-conditioned Baily's Bead
  or graze products; no bound limb-topography dataset is established here.
