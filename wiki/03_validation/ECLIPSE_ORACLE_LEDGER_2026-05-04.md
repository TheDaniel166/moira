# Eclipse Oracle Validation Ledger

## 1. Record status

- **Original audit date:** 2026-05-04
- **Evidence correction:** 2026-07-17
- **Target subsystems:** `moira.eclipse`, `moira.eclipse_geometry`,
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
- grazing and anti-solar limiting cases behave consistently; and
- a hand-derived representative calculation has the expected Besselian cone
  signs and ordering.

These are physical and geometric invariant checks. The representative
Besselian calculation is performed inside the test; it does not call the
runtime Besselian implementation and is not an external NASA comparison.

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
It does **not** compare runtime Besselian `l1`, `l2`, `tan f1`, or `tan f2`
fields with NASA Besselian elements. Solar path-product evidence is recorded
separately below.

### C. Named NASA solar path products

`tests/integration/test_eclipse_path_nasa_reference.py` compares Moira's public
solar-path vessel with three named NASA/GSFC products stored with source URLs
in `tests/fixtures/eclipse_nasa_reference.json`:

- 1999-08-11 total;
- 2031-11-14 hybrid; and
- 2032-05-09 annular.

For each row, the executable comparison covers searched greatest-event timing,
global eclipse type, greatest latitude and longitude, central-path width,
central duration at the solved greatest site, and magnitude. The native solar
search uses one Earth-reception light-time Sun/Moon shadow-axis policy; the
NASA products retain their own stated model and Delta-T basis. The named
tolerances are cross-model regression envelopes, not claims of identical
models or atlas-wide parity.

This three-row slice does not validate partial or non-central products, polar
events, observer-elevation sensitivity, every sampled central-line point,
full-track ingress/egress geography, or exact grazing/tangent boundaries.

### D. Swiss cross-engine corroboration

`tests/integration/test_eclipse_external_reference.py` uses the cached
`tests/fixtures/swe_t.exp` corpus for classification and searched-maximum
corroboration. `tests/integration/test_eclipse_occultation_where_reference.py`
checks one cached Swiss solar `where` row at a one-degree latitude/longitude
envelope.

Swiss is a secondary comparator. These checks do not establish primary-authority
Besselian parity, and the one-row `where` check does not validate atlas-grade
track shape, path width, magnitude, or central duration.

## 3. Corrected findings

### A. NASA Besselian alignment is not yet proven

The previous ledger claimed numerical parity for `l1`, `l2`, and the cone
angles for the 2017-08-21 and 2024-04-08 eclipses. It cited
`tests/integration/test_eclipse_besselian_audit.py`; that file does not exist in
the repository. No current fixture records the corresponding NASA Besselian
elements with named semantics and tolerances.

Accordingly, the former residual, constant-basis, and sign-transform claims
are withdrawn from the validation record. They may be restored only after an
executable comparison names the NASA source rows, runtime surface, frame,
timescale, units, sample, and per-field tolerances.

### B. Small-angle precision was not fixed by the recorded audit

At the 2026-07-17 audit boundary, `moira/eclipse_geometry.py::angular_separation`
still used the spherical law of cosines followed by `acos`. Direct probes at
`1e-8` degrees and `7.6e-8` degrees collapsed to zero. The previous statement
that the runtime had been upgraded to Haversine, including the stated
`7e-15`-degree residual, was false.

The 2026-07 remediation requires a numerically stable runtime formula plus
direct regression tests at ordinary, wraparound, coincident, antipodal, and
sub-microdegree separations. This ledger does not record that remediation as
passing until its exact test command and outcome are attached to the change's
completion receipt.

### C. Invariants do not prove temporal continuity

The invariant suite proves the bounded properties listed in section 2A. It
does not currently sample a runtime Besselian series through time, so the
former claims about smooth shadow-axis motion and absence of solver jitter are
not admitted as validated facts.

## 4. Bounded 2026-07 remediation

The July audit admitted a bounded repair program covering:

- small-angle separation stability;
- eclipse-contact root deduplication, search-window containment, and positive
  step validation;
- penumbral eclipse identity and `kind="any"` admission;
- signed NASA-compatible gamma and compatibility-model separation;
- explicit UT1-to-UTC reporting boundaries;
- local solar-eclipse overlap admission, including observer elevation;
- truthful central-duration semantics; and
- deterministic solar-path search behavior.

These items describe the remediation boundary, not a passing receipt. The
facade method names and REST endpoint paths are compatibility constraints, but
unchanged transport shape is not astronomical proof. The implementation must
be judged by the targeted tests and external evidence actually reported when
the repair is complete.

## 5. Current validation statement

The supportable statement is:

> Moira's eclipse subsystem has native geometric-invariant coverage, selected
> NASA catalog classification and TT search-regression coverage, three named
> NASA solar path-product comparisons spanning total, hybrid, and annular
> events, and bounded cached-Swiss cross-engine corroboration. Runtime NASA
> Besselian-element parity and atlas-grade solar-path validation remain
> unproven.

## 6. Remaining evidence work

- Add a provenance-bearing NASA Besselian fixture for representative total,
  annular, hybrid, and partial solar eclipses.
- Exercise the runtime Besselian implementation rather than reproducing its
  formulas inside a test.
- Name per-field semantics and tolerances for `x`, `y`, `d`, `mu`, `l1`, `l2`,
  `tan f1`, and `tan f2` before claiming parity.
- Extend path-product evidence to partial and polar events, observer elevation,
  full sampled tracks, ingress/egress geography, and grazing/tangent cases.
- Keep mean-limb geometry distinct from lunar-profile-conditioned Baily's Bead
  or graze products; no bound limb-topography dataset is established here.
