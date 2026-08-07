# Moira — Provenance & License Clarity

*This document answers, in one place, the questions a downstream developer or commercial user should be able to settle without reading source history: what Moira is licensed under, whether its implementation is independent, and how to read its earlier releases.*

---

## License

Moira is released under the **MIT License**, and will remain so. MIT permits commercial use, modification, and distribution — including building closed-source or paid products on top of Moira — with no copyleft and no AGPL obligations.

Moira was built deliberately as an independent, AGPL-free foundation, so that commercial builders can use it without the licensing entanglements that accompany Swiss Ephemeris–based stacks. That is the point of the project: a clean, permissively licensed engine you can ship commercially without contamination concerns.

## Independence of the implementation

Moira's astronomical and house-calculation code is **independently derived from primary sources** — spherical trigonometry, the defining geometric construction of each house system, and primary astronomical references (JPL DE441, IAU 2000A/2006) — and is validated against primary authorities (JPL Horizons, SOFA/ERFA, IERS). It does not incorporate Swiss Ephemeris source code.

A per-system account of the derivation basis, and of where Moira's discretionary choices diverge from convention, is published in [`HOUSE_SYSTEM_DIVERGENCE.md`](./wiki/01_doctrines/houses/HOUSE_SYSTEM_DIVERGENCE.md).

Note on resemblance: house geometry is mathematically forced — there is one correct way to trisect a semi-arc — so Moira's cusp values converge with any correct engine, including Swiss Ephemeris, at admissible latitudes. That convergence follows from shared mathematics and is **not** evidence of derivation.

## Astronomical data sources

### Atmospheric visibility model provenance

Moira's legacy component visibility family is independently implemented from
published equations and keeps each computational object separate:

- relative optical air mass uses Kasten and Young, *Applied Optics* 28
  (1989), 4735-4738, DOI `10.1364/AO.28.004735`;
- clear-air Rayleigh, aerosol, and ozone extinction air masses and
  coefficients, plus directional cloudless-sky twilight brightness, use
  Schaefer, *Vistas in Astronomy* 36 (1993), 311-361,
  DOI `10.1016/0083-6656(93)90113-X`;
- moonlight and directional dark-sky brightness use Krisciunas and Schaefer,
  *PASP* 103 (1991), 1033-1039, DOI `10.1086/132921`;
- the scotopic naked-eye point-source threshold uses Crumey, *MNRAS* 442
  (2014), 2600-2619, DOI `10.1093/mnras/stu992`.

The separately named opt-in composite model
`clear_sky_naked_eye_point_source_v1` uses offline libRadtran 2.0.6/REPTRAN
reference products for directional clear-sky transmission and twilight
radiance, the CIE MES2 response system, the full-range Blackwell-Crumey
point-source threshold, source-owned planetary or stellar photometry and
spectral profiles, and the Tousey-Koomen 1953 Table I twilight observations as
a bounded observational comparison. libRadtran is a reference generator, not
a runtime dependency or hidden ephemeris/visibility backend.

The implementation was derived from those papers and their tabulated or
equation-level reference points. No executable code from LibEphemeris or any
other AGPL implementation was copied or adapted. The
Krisciunas-Schaefer scattering function preserves the paper's piecewise aerosol
doctrine: its exponential Mie term applies from 10 through 180 degrees, while
the source-defined inverse-square aureole term applies below 10 degrees. Exact
zero separation is singular in that point-source model and is rejected rather
than silently clamped.

These models are not represented as universal atmosphere or vision truth.
Kasten-Young is evaluated only for apparent directions from the horizon
through the zenith. Schaefer's twilight term is treated as an approximate
cloudless-sky contribution from solar altitude 0 through -18 degrees; Moira
does not extrapolate it into daylight. Schaefer's component model keeps its
scotopic direct-target coefficient distinct from the visual-band coefficient
used by the nanolambert sky-brightness equations; the public result exposes
both rather than silently applying one spectral regime to both objects.
Crumey's point-source relation is
admitted only for naked-eye scotopic backgrounds from `1e-5` through
`3.426e-2 cd/m2`; it is not used for the Sun, Moon, extended objects, optical
aids, or out-of-range backgrounds. The Krisciunas-Schaefer moonlight term is
an optional V-band empirical model, not an all-site spectral radiative-transfer
solution. A measured zenith sky surface brightness and measured broadband
extinction coefficient are preferred when available; Bortle-derived darkness
remains an explicit approximate fallback and requires the table derivation
mode rather than reusing a limiting-magnitude interpolation as luminance.

The existing limiting-magnitude/arcus-visionis criterion remains the default
for compatibility. The physical chain must be requested explicitly. It now
supports both a single-epoch assessment and a separately admitted four-phase
first/last event search without routing either result through the legacy
threshold and relabelling it physical. The complete assessment and event
receipts expose direct extinction, atmosphere and background components,
threshold, margin, horizon, ephemeris, event ownership, solver tolerances,
validity, and typed failure reasons.

The physical event contract admits Mars, Jupiter, Saturn, and Sirius for all
four physical phases. Mercury and Venus remain single-epoch-only because a
guard day can leave their source-owned phase-angle domains; unsupported event
requests fail closed as `body_phase_not_admitted`. Other fixed stars and target
families require separate photometric and spectral admission.

Crumey's published field factor explicitly includes the target, medium,
laboratory scaling, and observer. Moira therefore does not apply its separately
reported target extinction again by default. A caller may opt into separate
target extinction only by declaring that its supplied field factor was
calibrated without atmospheric transmission; the response records which
magnitude governed the verdict. Source-solver/Monte Carlo uncertainty, binary
storage error, interpolation error, root residual/time tolerance,
limiting-magnitude envelopes, and deterministic event-time sensitivity remain
separate; Moira does not collapse them into an aggregate accuracy or confidence
score.

The admitted runtime resource is the separately distributed CC BY-SA 4.0 pack
`moira-physical-heliacal-visibility` `1.2.0`, manifest SHA-256
`cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c`.
The MIT wheel contains only compatibility contracts, the release identity, and
the resource notice; it contains no libRadtran/REPTRAN/CIE source material or
external numerical payload. A caller or server operator supplies the pack
directory explicitly. Normal execution performs no download and requires no
network access.

Phase 6 admits two private, differential-tested native numerical kernels for
response-weight resolution and direct-extinction interpolation. Python still
owns the model identity, doctrine, domain and resource admission, typed errors,
event semantics, and result construction. The Jones/Paranal moonlight
experiment is quarantined research. It has no runtime module, public contract,
packaged resource, release gate, or active-roadmap dependency.

The unified numbered-asteroid catalog is generated from JPL Horizons
heliocentric `VECTORS` states and materialized as Moira Type-13 shards. Moira
writes the resulting DAF/SPK bytes through its own Type-13 writer, interpolation
layout, shard assembly, metadata, and manifest pipeline; these are
Moira-generated artifacts, not BSP files supplied by JPL. Horizons remains the
trajectory-sample authority. Ordered shard registration and per-body coverage
exceptions are recorded in `moira/kernels/asteroids/manifest.json`; the
generated BSP files are separately acquired runtime resources.

Published small-body catalog releases are immutable, versioned artifacts.
`manifest.json` records SHA-256 and byte length for every kernel and its
per-shard build evidence, while `SHA256SUMS` covers the manifest and every
distributed file. The separately published archive has its own adjacent
SHA-256 receipt. Changed membership, policy, metadata, or bytes require a new
catalog version rather than replacement under an existing identity. The
distribution includes the MIT license for Moira-authored software and
packaging plus a notice that preserves JPL Horizons provenance without implying
NASA, JPL, or Caltech endorsement.

The bundled asteroid identity registry is bound to catalog
`moira-asteroids`, version `2026.07.27.1`, through
`moira/data/asteroid_catalog_naif.metadata.json`. That receipt identifies
9,974 canonical names, the 399-shard 10-day/7-node external release, source
revision, admitted-target and unified-ledger hashes, and manifest SHA-256
`0560302f877a46cebc550376ae70665fefab84801078181cf3c4199ce86d49d0`.
The wheel contains this identity registry, receipt, and metadata-only manifest,
not the external BSP shards; known identity therefore remains distinct from
installed position capability.

The numbered-periodic-comet identity registry is derived from one verified
release rather than maintained as an independent handwritten name table.
Numbered designations such as `1P/Halley` are canonical. The five historical
short inputs are stored in a separately receipted alias policy and remain
comet-family scoped; they do not claim global uniqueness against asteroid,
stellar, calculated-point, or other namespaces. The packaged
`moira/data/comet_catalog_naif.metadata.json` binds the canonical registry and
alias policy to the exact release manifest, master ledger, Horizons query
policy, source revision, and SHA-256 identities. That receipt names catalog
version `2026.07.28.1`: 497 comets in 20 shards under a 30-day/5-node sampling
policy, with manifest SHA-256
`31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1`.
The metadata-only asteroid and comet manifests retained in the wheel are
byte-identical to these immutable release receipts and remain excluded from
automatic reader discovery until a referenced BSP shard is installed.

Asteroid dynamical-family annotations are generated by
`scripts/build_asteroid_family_catalog.py`. The current main-belt authority is
David Nesvorny's Proper25 machine-readable distribution accompanying the 2026
family census. Proper25 explicitly excludes Hilda and Jupiter Trojan families,
so Moira retains only those eight excluded-population families from NASA PDS
`ast.nesvorny.families` V2.0 (2015 tables). Source URLs, input hashes, exclusions,
normalization policy, aliases, and output counts are recorded in
`moira/data/asteroid_families.metadata.json`. Membership is many-to-many:
nested and overlapping HCM classifications remain visible. A missing
membership means "not present in the admitted catalogs," not proof that an
asteroid has no collisional family.

Icarus (1566) and Apollo (1862) are limited to their observational arcs because
their chaotic long-range solutions depend materially on the requested Horizons
interval. JPL SBDB is the authority only for those arc bounds and orbit-solution
identifiers; Horizons remains the authority for the vector samples. The exact
SBDB solution metadata used by a build is preserved in the manifest and unified
catalog metadata. Offline apparent-position fixtures use JPL Horizons
`OBSERVER`, center `500@399`, quantity 31, and are external authority evidence,
not self-generated Moira parity.

### NASA/GSFC solar Besselian validation corpus

`tests/fixtures/nasa_solar_besselian_reference.json` contains a bounded,
validation-only transcription of published NASA/GSFC solar Besselian elements.
It records the official field definitions, polynomial semantics, stated
VSOP87/ELP2000-82 ephemerides, `k1`/`k2` lunar-radius convention, and four named
event rows (2000 partial, 2024 total, 2031 hybrid, and 2032 annular), retrieved
on 2026-07-17. The exact source URLs are embedded beside the fixture metadata
and each event row.

This corpus is primary external validation evidence for the meanings and
bounded per-field comparison of `x`, `y`, `d`, `mu`, `l1`, `l2`, `tan_f1`, and
`tan_f2`. It is not a runtime ephemeris, coefficient source, uncertainty model,
or substitute for Moira's content-identified DE441/LE441 geometry. NASA's
requested acknowledgment is retained verbatim in the fixture:
`Eclipse Predictions by Fred Espenak, NASA's GSFC`.

### NASA/GSFC lunar eclipse catalog validation corpus

`tests/fixtures/eclipse_nasa_lunar_1901_2000.json` contains a complete,
validation-only transcription of the 229 entries in the official NASA/GSFC
[Five Millennium Catalog of Lunar Eclipses, 1901-2000](https://eclipse.gsfc.nasa.gov/LEcat5/LE1901-2000.html),
retrieved on 2026-07-22. The fixture records the catalog number, calendar date,
greatest-eclipse time in TD/TT, published Delta T, and NASA type code for each
event. Its metadata preserves the catalog's Danjon shadow-enlargement
convention and the exact source URL.

This corpus is primary external evidence for century-scale event identity,
ordering, greatest-eclipse timing, and eclipse type family under NASA's stated
catalog semantics. It is not a runtime ephemeris, a coefficient or discovery
source, or a substitute for Moira's independently evaluated DE441/LE441
geometry. Timing residuals measure the difference between those named products
and are not NASA uncertainty estimates. Tests use the static fixture without
network access and do not import catalog values into engine computation.

### NASA/GSFC polar central-path validation corpus

`tests/fixtures/nasa_solar_polar_path_reference.json` is a bounded,
validation-only transcription of the official NASA/GSFC 2015-03-20 total
[eclipse path](https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2015Mar20Tpath.html)
and its paired [Besselian-elements page](https://eclipse.gsfc.nasa.gov/SEbeselm/SEbeselm2001/SE2015Mar20Tbeselm.html).
The fixture keeps that product lineage coherent: JPL DE405,
`Delta T = 67.6 s`, WGS 84 geodetic
coordinates sampled at the published 120-second cadence, the published
`k1 = 0.272508` and `k2 = 0.272281` lunar-radius constants, and
center-of-mass mean-limb predictions without lunar topography. It records the
initial and terminal central-line products, five late-track rows approaching
the North Pole, and the greatest-eclipse product. Exact official source URLs
and the requested NASA acknowledgment are embedded in the fixture.

The corpus is primary external evidence for a specifically named geographic
product. It does not supply runtime coefficients or replace Moira's
content-identified DE441/LE441 geometry. Its tolerances measure the residual
between NASA's declared DE405 product and Moira's independently evaluated
DE441 path; they are not NASA uncertainty estimates and do not establish
full-atlas, lunar-topography, or one-limit/terminator-closure validation.

### JPL Horizons polar occultation validation corpus

`tests/fixtures/jpl_horizons_polar_occultation_reference.json` contains a
bounded, validation-only JPL Horizons observer-table extract for the
2026-10-05 lunar occultation of Mars as seen from the geographic North Pole.
The fixture records the exact Horizons API parameters and returned signature,
airless apparent right ascension and declination, equatorial angular
diameters, `UT1-UTC`, and the Moon/Earth DE441 and Mars `mar099` source labels.
It also preserves the credit `NASA/JPL-Caltech, Solar System Dynamics Group`
and links the official Horizons API documentation. The separately linked IOTA
2026 lunar-occultation publication corroborates the event's high-Arctic
identity; it does not provide the pole contacts or path width.

The four bounded rows place each outer contact in a `0.5 s` UTC bracket by the
signed airless clearance
`(Moon diameter + Mars diameter) / 2 - angular separation`. Because the event
was still in the future when the fixture was retrieved on 2026-07-18, Horizons
used predictive Earth-orientation data. The fixture therefore requires a
post-event refresh when measured EOP replaces that prediction. Moira's
independent DE441 result is admitted under a separate `2 s` cross-model
contact gate; neither number is an uncertainty estimate.

This corpus establishes only North-Pole outside/inside/outside containment and
the two pole-boundary contact instants. It does not publish an external
left/right limit-track corpus or a scalar path width. Those detailed topology
products are tested instead through independent spherical geometry,
zero-clearance, distance, ordering, and vessel invariants. The admitted public
topology uses a spherical mean lunar limb. Finite planetary target disks use
the equatorial solid-body radii published in JPL Solar System Dynamics'
[Planetary Physical Parameters](https://ssd.jpl.nasa.gov/planets/phys_par.html);
the Sun is not in that table and is therefore excluded from this planetary
topology product in favor of Moira's eclipse surfaces. Saturn's rings are
explicitly excluded. Profile-conditioned lunar-limb graze
products and their IOTA evidence remain a separate computational and
validation surface.

The topology observer is a WGS 84 geodetic level surface with equatorial
radius `6378.137 km` and flattening `1/298.257223563`, matching Moira's
topocentric substrate. Its admitted height floor is the negative WGS 84
semi-minor axis,
`-6378.137 * (1 - 1/298.257223563) * 1000 m`. This is a computational-domain
bound that preserves the parallax-envelope proof; it does not assert that
deep negative level surfaces are realistic observing sites. Positive height
has no invented observational ceiling. For the extreme computational case in
which the observer radius reaches a body's geocentric distance, the envelope
uses the geometric `180 degree` direction-reversal bound; the ordinary
`asin(R/d)` horizontal-parallax bound applies only while `R < d`.

### IOTA observed-contact and official lunar-topography corpus

Moira keeps three lunar-graze products distinct. An IOTA graze or limit-line
publication is a predicted geographic path product. A Moira
topography-conditioned contact sequence is a model prediction from an admitted
lunar profile at one observing site. An observed IOTA disappearance or
reappearance is a reduced timing measurement. Agreement among those products
must be tested explicitly; none is relabeled as another.

`tests/fixtures/iota_spica_2024_observed_contacts.json` preserves the ordered
2024-11-27 Spica disappearance/reappearance chronologies reported by IOTA for
the two Dunham observing sites. The fixture identifies IOTA as the authority,
retains the source's GPS-referenced UTC realization, site and height semantics,
reported 95-percent timing errors, document URLs, byte lengths, and SHA-256
digests. It is authority evidence for the observed chronology. The source
errors remain observational reduction errors, not Moira model tolerances, and
the fixture does not assert that the published list resolves every possible
short topographic microcontact or any unreported tangency. The
`external_network`-marked
test verifies source-document identity and fails closed on byte drift; it does
not silently regenerate the fixture.

IOTA/ES GRAZPREP uses a separately derived, precomputed `LUNLIMB` product from
LRO/LOLA source data. Its public manuals describe recalculation across
libration and position angle but do not publish the current reconstruction,
interpolation policy, or profile grid. Moira therefore does not label its RDR
spot reconstruction as GRAZPREP- or LUNLIMB-equivalent. Exact-site GRAZPREP
contact tables and identified LUNLIMB inputs would form a separate
product-to-product corpus.

The contact-facing profile builder in `moira.lunar_limb` obtains a physical
Moon-to-observer reception light cone from the caller's explicitly
content-identified DE441/LE441 reader. Observer-motion aberration is not folded
into that surface-intersection ray, and SPICE does not supply a second DE440
translation for this product. NAIF's `moon_pa_de440_200625.bpc` and
`moon_de440_250416.tf` supply only the retarded-emission-epoch transformation
to `MOON_ME_DE440_ME421`. Surface radii come from official USGS Astrogeology
LOLA assets in the `lunar_orbiter_laser_altimeter` STAC collection, admitted as
IAU 2015 Moon-centred Cartesian data on the `1737.4 km` reference sphere.
Source asset URLs and the translation/orientation labels are retained in the
immutable profile provenance.

The resulting finite-resolution profile uses the finite-distance tangent locus
and an explicit maximum perspective-equivalent radius per half-open
position-angle bin. Each maximum is assigned to its bin centre, and adjacent
admitted centres and event epochs are reconstructed linearly. This preserves
the declared bin-scale extrema without claiming exact sub-bin topography. It
is consumed by
the direct-import engine function
`moira.lunar_occultation_contacts.lunar_star_topographic_contacts`. Contact
targets are named records from Moira's sovereign `star_registry.csv` and
`star_provenance.json`, propagated in ICRS to an explicit TT reference epoch.
For positive catalog parallax, the observer-to-star ray subtracts the complete
reception-epoch observer SSB vector in kilometres. A contact-private
Klioner-equation light-deflection path uses DE441 Sun, Jupiter, and Saturn
position/velocity states, closest-passage backtracking, declared SOFA `Ldn`
limiters, and the exact finite-star deflector-to-source direction. Deflection is applied to the incoming
stellar photon ray; the lunar light cone remains the retarded geometric
location of the blocking surface, rather than being reinterpreted as the
apparent direction of photons emitted by the Moon. Curvature over the final
Earth-Moon segment is not modeled. Contact admission is airless:
observer-motion aberration and atmospheric refraction change apparent
coordinates or observing circumstances but are not part of whether the
stellar photon ray is blocked by the lunar surface. This engine-only surface
is not exported through `Moira` and has no FastAPI route or REST schema.

`tests/fixtures/iota_spica_2024_moira_lola_model.json` admits the named
DE441/LE441 plus raw-LOLA-RDR comparison at both Dunham sites. All ten Dunham1
and all eight Dunham2 published contacts have a unique optimum under the
declared monotone same-kind matcher. The maximum absolute timing residuals are
respectively `0.381008 s` and `0.337355 s`, inside a Moira-owned `0.5 s`
cross-model regression envelope.
That envelope is not an IOTA uncertainty, an absolute accuracy tolerance, or
evidence of GRAZPREP/LUNLIMB equivalence. Dunham1 has no model-only contacts.
Dunham2 retains a leading model-only disappearance/reappearance pair about
`1.529 ms` wide; it is required because it exceeds the declared `1 ms` scan
feature guarantee. The `external_network`-marked comparison refreshes the
official STAC cell mapping and admits all sixteen COPC resources by exact URL,
byte length, and SHA-256 before decode.

### Earth rotation and Delta T

Moira keeps the computational products below distinct. A source that measures
total Earth rotation does not thereby identify a causal core, atmospheric,
oceanic, or cryospheric contribution. Machine-readable coverage, hashes,
units, transformation lineage, and runtime-admission status are recorded in
`moira/data/delta_t_manifest.json`.

| Packaged artifact | Source and product | Runtime status |
|---|---|---|
| `iers_eop.txt` | IERS `finals2000A` snapshot; daily DUT1 (`UT1-UTC`) | Admitted for UTC-to-UT1 and UT1-to-TT conversion. The packaged transformation does not retain the source observed/predicted flag, so admitted rows are not all described as measured or definitive observations. At each outer edge, the EOP-to-year-model correction is C0 at the boundary and tapers to zero over one Julian year rather than becoming a remote constant offset. Internal gaps interpolate only their two admitted boundary corrections and are not relabelled as measured data. |
| `delta_t_hpiers_2016.txt` | Stephenson, Morrison, and Hohenkerk (2016) / HPIERS tabulation; Delta T and quoted error columns, stated by HPIERS for DE430/LE430 at lunar tidal acceleration `-25.85 arcsec/cy²` | HPIERS declares the 1950–2016 block half-yearly even though its HTML DATE display rounds epochs to integers. The packaged artifact materializes that source-owned `0.5`-year cadence and preserves exact duplicate rows. Conflicting published rows at `-1600` and `1850` retain an explicit later-row compatibility choice; only `1850` is a precision/regime join. Generic `delta_t()` preserves the DE430/LE430 source basis and does not ambiently retarget to DE441. HPIERS owns the runtime mean through its final distinct knot before the modern aggregate bridge. An explicit 100-year C0 bridge joins the earlier polynomial at `-2100` to the first HPIERS row at `-2000`; the physical surface still begins at `-2000`. |
| `core_angular_momentum.txt` | Annual means of total IERS EOP C04 LOD | Quarantined research proxy. Despite the historical filename, this is not a core-angular-momentum inversion and is not admitted as a causal component. |
| `grace_lod_contribution.txt` | Historical derivative of GRACE/GRACE-FO TN-14 C20 | Quarantined. The historical integration has a factor-of-86.4 unit defect and the C20-to-inertia/cryosphere attribution lacks a source-owned derivation. The values are retained only for audit reproduction. |
| `aam_glaam_annual.txt` | NOAA PSL global atmospheric angular momentum annual means | Diagnostic research proxy only; not admitted to the public Delta-T mean. |
| `oam_ecco_annual.txt` | IERS ECCO annual-mean oceanic LOD proxy | Diagnostic research proxy only; not admitted to the public Delta-T mean. |

Reader-bound historical Delta-T translation admits lunar tidal acceleration
only for exact, content-derived DE/LE identities. DE440/LE440 and DE441/LE441
are separately admitted at `-25.936 arcsec/cy²`. The primary JPL
[DE440/DE441 release paper](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf)
establishes the shared release family, source fit, and the distinct lunar
core/mantle damping policy, while the official
[Horizons release record](https://ssd.jpl.nasa.gov/horizons/news.html) states
the `-25.936 arcsec/cy²` historical-Delta-T adjustment for that generation.
This is an explicit two-product admission, not a rule for inferring the basis
of DE431, another adjacent release, or a kernel whose summary identity is
unknown.

The admitted Delta-T mean is source-priority total truth through the final
aggregate product (currently the Jan–Apr 2026 partial mean). Full-year means
are placed at the mean epoch of their twelve first-of-month USNO samples; the
partial mean is placed at the mean epoch of its four samples. Product labels
are not treated as January 1 point epochs. The final two representative epochs
own the scenario handoff coordinate, total, and provisional slope; that
quotient is policy, not an observed instantaneous derivative. Beyond the handoff, Moira
exposes an explicit bounded scenario. Values beyond 2150 are scenario
extrapolations, not authority-validated forecasts. Its future `sigma` field is
an uncalibrated policy scale, not a stated-coverage uncertainty. The modern
bridge/aggregate scale is `0.06 s`, covering the verified `0.052808 s` maximum
daily residual against the bundled EOP snapshot; the legacy future
scenario coefficients lack a complete traceable calibration record, and
uncertainty in the handoff value and slope is not propagated. The compatibility fields
named `core`, `cryo`, `fluid`, and `residual` remain public, but are zero while
their candidate datasets are quarantined.

JD-aware hybrid and physical transforms use a private exact fraction between
successive proleptic-Gregorian January 1 boundaries. The public
NASA-compatible decimal-year helper deliberately retains its month-midpoint
convention. NASA catalog compatibility passes that coordinate explicitly;
general no-hint NASA time transforms use a continuous year and expose raw
polynomial boundary seams through a fail-closed inverse. EOP-backed private
UT1-to-UTC formatting inverts the within-day
UT1-TAI relation, so a positive UTC leap is not distributed across the prior
civil day. Before the atomic era, Moira retains the historical UT1-proxy
policy; over the final civil day before `1972-01-01`, a monotonic smoothstep
joins that proxy to the atomic rule, and the private inverse solves the same
handoff by bisection.

`DeltaTBreakdown.era` retains the compatibility labels `pre-1840`,
`historical`, `measured`, and `future`; those categories are not source-row
provenance, and the legacy word `measured` does not override the status of an
admitted source row. Computational guards admit finite Delta-T years only in
`[-100000, +100000]` and time-transform JDs only in
`[-40000000, +40000000]`. These binary64 representability bounds are not
scientific-validity or source-coverage claims.

## Gauquelin historical-sector validation witness

The 2026-07-20 historical-sector audit uses a user-supplied g5 temporary-data
archive only as a non-bundled validation witness.  Its SHA-256 is
`889B27999D787574F9CE0771BEB8BA41AC91D1B1362D6A03D12442022821B0BC`.
The archive contains CFEPP, CSICOP, Ertel, and Müller personal records and is
not distributed in Moira.  The committed aggregate fixture contains counts,
comparison results, and the archive hash only.

The g5 import definitions and conversion code were inspected at commit
`bf0db345b58127a438121b74ebf4ad843243a573`.  g5 source code is GPL-3.0 and is
not copied or adapted into Moira.  Accompanying written correspondence states
that CC-BY-SA attribution is acceptable for g5 and Open Gauquelin data, but
Moira does not rely on that statement to bundle the archive.  The validation
harness is independently written MIT-licensed Moira code.

The CFEPP tranche is treated as a clean numerical comparison because it
contains explicit UTC and coordinates.  The 1,120 rows comprise the official
first 1,066 plus 54 Nienhuys supplements.  Moira matches 1,107 assignments
exactly; the 13 differences are adjacent 12-sector bins within `0.535°` of a
boundary.  Historical assignments remain fallible evidence and do not rewrite
the engine algorithm.  The explicit-LMT Müller subset independently produces
904/916 exact 36-sector assignments, with seven adjacent differences and five
larger source-adjudication cases; its remaining 167 correction-coded rows are
deferred.  Ertel requires joins to birth time and place records.
CSICOP is retained only as a sensitivity audit: the literal g5 converter's
hour-12 AM/PM behavior gives 304/408 exact assignments, while conventional
noon/midnight semantics give 326/408 exact and 406/408 within two 36-sector
bins.  No policy is silently selected; two large outliers remain for source
adjudication.
The complete custody, method, limitations, and reproduction command are in
[`GAUQUELIN_G5_HISTORICAL_VALIDATION_2026-07-20.md`](./wiki/03_validation/GAUQUELIN_G5_HISTORICAL_VALIDATION_2026-07-20.md).

## Pancha Pakshi source-scoped witnesses

Moira admits four explicitly named Pancha Pakshi profiles as source-scoped
public products. Their private ingestion data records normalized computational
facts and locators from the 1879 Tamil print catalogued by Internet Archive as
[`dli.rmrl.000451_images`](https://archive.org/details/dli.rmrl.000451_images)
and the 2024 Tamil edition catalogued as
[`acc.-no.-44757-panjapatchi-sashthiram-2024`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024).
The sources are traditionally attributed to Agastya and Bogamuni respectively;
those attributions are bibliographic metadata, not verified
historical-authorship claims. Both editions are research witnesses, not package
assets. Moira records independently normalized computational rules and source
locators; it never bundles archival scans, PDFs, OCR, page images, copied table
layouts, source prose, or third-party translations.

Internet Archive metadata classifies `dli.rmrl.000451_images.zip` as the
original image archive and `dli.rmrl.000451.pdf` as a derivative PDF. The
source-scoped profile retains the archive MD5/SHA-1 identities of both, plus the
locally verified PDF SHA-256. Those hashes identify the exact witness used for
research; they do not import or redistribute either file. The same metadata
names Ti. Kandasami Pillai as having reviewed the edition. His exact
contribution and life dates remain unresolved bibliographic questions, but
they do not create a Moira distribution issue because no source expression is
copied into the package.

Internet Archive metadata classifies
`Acc.No.44757-PanjapatchiSashthiram-2024.pdf` as the original 2024 PDF. Its
recorded MD5 is `abe489a832ac38a0270335b7429776f3`, its recorded SHA-1 is
`6ddad8f2577883f6859829f534e8ee7b8330ade8`, and the locally verified SHA-256
is `035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`.
The edition names R. C. Mohan as editor; Moira preserves that as editorial
metadata and does not convert it into authorship. The hashes identify the
research witness without importing or redistributing the file.

The public profile `agastya_madras_1879_akshara_fixed_clock` is restricted to
the witness's aksara/query-or-name-initial operating schedule, fixed-clock
timing, directed relationship matrix, and directly attested mapping from waxing
and waning lunar halves to its Purva and Amara source labels. It must not be
represented as a natal-Moon canon. Exact source locators and archive file
checksums are retained in the machine-readable profile. Profile schema 3 owns
the normalized lunar-half mapping; the schema-v2 manifest owns its
`source_scoped_public` decision, admitted capabilities, and explicit
`default_selection_allowed=false` policy; the runtime loader rejects a
data/manifest hash mismatch or capability/product disagreement.

Stage 2A adds `astronomical_context` through the explicitly modern Moira policy
`local_solar_day_explicit_paksha_v1`; it does not attribute that composition to
the 1879 witness. The low-level engine accepts a UT1 instant and location,
while datetime-facing facade and REST callers supply a timezone-aware instant
that is normalized to UTC through the established civil-anchor conversion.
The policy uses the existing configured-reader-backed topocentric
`-0.833`-degree solar-altitude crossings to resolve the governing sunrise,
sunset, and next sunrise. The observer elevation is explicitly fixed at `0 m`;
the altitude signal is unrefracted, while the threshold incorporates
conventional standard refraction and solar semidiameter. It derives the
day/night half and the local-mean-solar weekday at the governing sunrise, then
selects the unchanged nominal source schedule using an explicit caller-supplied
Purva or Amara label.

This context product does not infer paksha from lunar geometry, proportionally
stretch nominal durations, convert nazhigai offsets to Julian Days or
datetimes, or assert a current activity. The underlying profile document and
its canonical SHA-256 remain unchanged. The additive
`pancha_pakshi_1879_local_solar_context_2026_07_20.json` decision chains the
modern capability to the earlier source-scoped admission without raising its
evidence status to `corroborated_public`.

Stage 2B separately adds `fixed_clock_materialization` through the explicitly
modern Moira policy
`fixed_24_minute_nazhigai_from_local_solar_half_start_v1`. The underlying 1879
profile remains unchanged: it continues to own the exact nominal
thirty-nazhigai schedule, rational offsets, and source locators, but it is not
credited with the modern astronomical/time-scale composition. The University
of Madras [*Tamil Lexicon*, page 2231](https://dsal.uchicago.edu/cgi-bin/app/tamil-lex_query.py?qs=%E0%AE%A8%E0%AE%BE%E0%AE%B4%E0%AE%BF%E0%AE%95%E0%AF%88&searchhws=yes&matchtype=exact)
supplies the lexical unit definition that one nazhigai is sixty vinadi or
twenty-four minutes. The [IERS TT glossary](https://www.iers.org/SharedDocs/Glossareintraege/EN/T/tt)
states that TT is conventionally realized as `TAI + 32.184 s`, and
[IERS Technical Note 29](https://www.iers.org/SharedDocs/Publikationen/EN/IERS/Publications/tn/TechnNote29/tn29.pdf?__blob=publicationFile&v=1)
states that the TT unit agrees with the SI second on the geoid.

The policy selects the unchanged nominal schedule through Stage 2A, anchors a
day schedule at governing topocentric sunrise or a night schedule at governing
topocentric sunset, and converts each exact offset using
`1 nazhigai = 1,440 SI seconds`. The offset is added on reader-bound TT and each
endpoint is projected to UT1. Thirty nazhigai therefore always spans exactly
`43,200` SI seconds on TT. The fixed end is never clipped or stretched to the
astronomical sunset or next sunrise. Instead, the signed
`fixed_end_jd_tt - solar_end_jd_tt` residual and its
`before`/`coalescent`/`after` relation remain visible; absolute residuals no
greater than `0.0001 s` are coalescent under an explicitly numerical policy.
The result deliberately does not select a current cell, so an instant can
remain inside the astronomical half while lying outside the fixed schedule.
Solar-proportional scaling remains a different capability from this fixed-clock
product and is admitted only through the separately named Stage 2D policy
below.

The Stage 2B authority roles remain separate. The 1879 witness governs nominal
schedule facts; the *Tamil Lexicon* governs the fixed nazhigai unit; IERS
governs the TT/SI-second time-scale basis; and the frozen Stage 2A Horizons
comparison governs only the solar anchor. The additive
`pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json` decision binds
those roles, the unchanged profile hash, the frozen Stage 2A decision, and the
manifest-only capability transition. It is not an external Pancha Pakshi
current-cell oracle or independent-witness corroboration.

Stage 2C separately adds `fixed_clock_current_cell_selection` through the
explicitly modern Moira policy
`fixed_clock_current_cell_half_open_solar_precedence_v1`. It composes the
unchanged Stage 2B materialization rather than rewriting the source profile or
its fixed-clock policy. The governing local-solar half is resolved first; the
requested instant is then represented on the same reader-bound TT coordinate
as the materialized cells and tested against their exact half-open intervals
with `0.0 s` membership tolerance. Shared endpoints belong to the following
cell and the fixed endpoint is excluded. The separate Stage 2B `0.0001 s`
topology coalescence remains descriptive and never changes ownership.

This solar-half-first precedence prevents cells from a prior short half from
remaining current after sunset or sunrise. When a long solar half outlasts the
fixed span, the uncovered interval is not repaired: the public result reports
`unmaterialized_solar_half_tail` with `current_cell=None`. Clipping, wrapping,
repeating, stretching, borrowing, solar-proportional scaling, and astronomical
paksha inference remain unperformed. Paksha remains an explicit caller-supplied
source label.

The additive
`pancha_pakshi_1879_fixed_clock_current_cell_2026_07_20.json` decision binds the
unchanged profile hash, frozen Stage 2B decision and manifest, manifest-only
capability transition, policy, selection statuses, and structural validation
boundary. The 1879 witness still governs only the nominal schedule facts; the
selection policy is Moira-owned composition. There is no external Pancha
Pakshi current-cell oracle or independent-witness corroboration, and the
bounded deterministic membership result does not raise the profile above
`source_scoped_public`.

Stage 2D separately adds `solar_proportional_materialization` through the
explicitly modern Moira policy
`solar_proportional_nominal_offsets_over_governing_half_tt_v1`. It preserves
the source-owned nominal schedule and treats every exact nominal endpoint as a
reduced fraction of its complete thirty-nazhigai span. The governing sunrise or
sunset anchor and solar-half end are converted through the same configured
reader to TT. Each interior endpoint is derived independently from the common
anchor and complete TT span, then projected to UT1; the outer TT and UT1
endpoints are the exact governing solar-half bounds. The result therefore has
25 positive contiguous half-open cells and needs no clipping, wrapping,
repetition, fixed-span borrowing, or tail fabrication.

This proportional mapping is a modern Moira composition, not a rule attributed
to the 1879 witness. The witness continues to govern the unchanged nominal
schedule, exact rational offsets, bird/activity assignments, chronology, and
source locators. The fixed `1,440 s` nazhigai conversion is not used. Paksha
remains caller supplied, and current-cell selection and astronomical paksha
inference remain unperformed. To avoid contradictory provenance, the Stage 2D
result replaces the source-profile `seasonal_scaling` omission with
`source_attested_solar_proportional_materialization`: the performed modern
operation is visible while its absence from the historical witness remains
equally explicit. Earlier profile, context, and fixed-clock results remain
unchanged.

The additive
`pancha_pakshi_1879_solar_proportional_materialization_2026_07_20.json`
decision binds the unchanged profile hash, frozen Stage 2C decision and
manifest, exact proportional policy, route-specific provenance resolution, and
structural validation boundary. The existing JPL Horizons evidence governs
only the inherited topocentric solar anchors; there is no external Pancha
Pakshi proportional-timing oracle or independent-witness corroboration.

Stage 2E separately adds `solar_proportional_current_cell_selection` through
the modern Moira policy
`solar_proportional_current_cell_half_open_solar_precedence_v1`. It composes the
unchanged Stage 2D materialization. Stage 2A resolves the governing solar half
first, then the requested instant is converted once to the same reader-bound TT
coordinate used by the proportional cells. Membership is exact and half-open,
with `0.0 s` tolerance: the anchor belongs to cell zero, every shared endpoint
belongs to the following cell, and the old half's final endpoint is excluded.
Exact sunrise or sunset therefore belongs to the newly governing half.

Unlike the fixed-clock selector, the proportional selector has no uncovered
solar-half tail. Stage 2D covers the complete governing half exactly once, so a
lawful Stage 2E result is always `selected` with one non-null member of that
materialization. Zero or multiple matches fail closed; no null state,
fixed-clock borrowing, clipping, wrapping, repetition, tolerance, or fallback
is admitted. Paksha remains caller supplied, while astronomical paksha
inference and natal identity remain unperformed. Stage 2E preserves the Stage
2D route-specific omission `source_attested_solar_proportional_materialization`
and changes only the astronomical routing status to
`solar_proportional_current_cell_selection_performed_paksha_caller_supplied_no_fixed_clock_mixing_or_inference`.

The additive
`pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json` decision
binds the unchanged profile hash, frozen Stage 2D decision and manifest,
manifest-only capability transition, exact selection policy, provenance
transformation, and structural validation boundary. DE441 and the existing JPL
Horizons evidence govern only the reader-bound clock path and inherited solar
anchors; neither is an external Pancha Pakshi current-cell oracle.

Stage 2F separately adds `astronomical_paksha_inference` and one normalized
source mapping to the same named profile. Machine-assisted visual reading of
the exact 1879 derivative PDF found direct waxing-to-Purva wording at IA leaf
[`n16`](https://archive.org/details/dli.rmrl.000451_images/page/n16/mode/1up)
and direct waning-to-Amara wording at leaf
[`n26`](https://archive.org/details/dli.rmrl.000451_images/page/n26/mode/1up).
The frozen reading record
`pancha_pakshi_1879_lunar_paksha_mapping_reading_2026_07_20.json` binds those
locators to the exact archive witness and has canonical SHA-256
`9ce3686a90a41af916a370b8d4ec04637f22a1d32f872180c6d8a1b790e25a0e`.
Its status remains
`machine_assisted_visual_reading_pending_competent_tamil_review` as a frozen
legacy label; it records the original evidence classification and creates no
human-review dependency. The live profile now uses
`machine_reconciled_source_assignment_with_declared_uncertainty`; its current
SHA-256 is
`d80d205716eb9f24a2a23949c6df241a1aba251749efa94d3b20fa36be0258f4`.
The two normalized mapping facts are public only for
this source-scoped profile; they are not independent-witness corroboration or a
universal terminology claim.

The modern computational policy is
`apparent_geocentric_moon_sun_longitude_paksha_half_open_v1`. From one explicit
UT1 instant it derives one reader-bound TT coordinate, evaluates apparent
geocentric Sun and Moon longitudes in the true ecliptic of date on that shared
coordinate, and normalizes `Moon - Sun` into `[0, 360)` degrees. Exact half-open
ownership assigns `[0, 180)` to Shukla/waxing/Purva and `[180, 360)` to
Krishna/waning/Amara, so `0` belongs to Shukla/Purva and `180` to
Krishna/Amara. The boundary tolerance is zero and there is no snapping,
topocentric or civil-day override. No ayanamsa is applied because the same
longitude offset would cancel in the difference; Panchanga now likewise uses
the direct tropical Moon-Sun difference for exact tithi and karana boundary
stability rather than subtracting two separately rounded sidereal values.

The low-level, facade, and transport surfaces are respectively
`pancha_pakshi_astronomical_paksha_at(...)`,
`Moira.pancha_pakshi_astronomical_paksha(...)`, and
`POST /v1/pancha-pakshi/context/astronomical-paksha`. The transport request
accepts only an explicit `profile_id`, timezone-aware `dt`, and the exact policy
ID; it accepts no location or caller-supplied paksha. The result exposes the
UT1/TT witnesses, policy, both longitudes, normalized elongation, astronomical
and profile labels, the selected mapping locator, and route-specific
provenance. It does not select or materialize a schedule, choose a current cell,
feed its result automatically into another route, or infer natal identity.

The chained
`pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20.json` decision has
canonical SHA-256
`1020b28d5da8d0e823cadd352ea2236c69cbb636660a573eb5d74b8c131bc5d8`.
It freezes the Stage 2E decision at
`4ddf0a5fa5b680fa83a7bb3052ecbc5d1a9c2f685c466290f22121dd02724d18`,
the prior manifest at
`d2b5f8f1ae7e067d257eeb24b533be1d33349446d56d361ea59f4a71472eca70`,
and the prior profile at
`876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4`.
The admitted profile and manifest digests become respectively
`4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`
and `a4fdceee4089c2812d9d77be763c1738152a63231b3f06847ea93383e4a3b327`.
Admission remains `source_scoped_public`; product kind and the no-default rule
do not change. Neither source artifact nor copied source expression enters the
package.

Stage 2G admits the separate profile
`bogamuni_chennai_2024_nakshatra_natal_identity` with product kind
`natal_moon_bird_identity` and capabilities `nakshatra_bird_mapping` and
`natal_identity`. Rendered-page inspection of the original Internet Archive PDF
established the complete Purva nakshatra-bird partition at leaf
[`n52`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n52/mode/1up),
the complete Amara verse partition at leaf
[`n64`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n64/mode/1up),
and the source phase-to-Purva/Amara binding at leaf
[`n167`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n167/mode/1up).
The Amara commentary adjacent to the governing verse duplicates Shravana and
omits Revati. The declared assembly policy
`verse_precedence_for_nakshatra_partition` therefore admits the complete verse
and preserves the malformed commentary as rejected conflict evidence; it does
not silently repair the commentary. The Uromarisi-attributed 1934 witness at
[`kvc-0354-vinaadi-pajasapatchi-mulamum-1934`](https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934)
corroborates the Purva grouping at leaf `n18` and independently exhibits a
malformed Amara commentary at leaf `n61`, but its table is not imported into
runtime truth.

The source witnesses attest phase labels and nakshatra-to-bird associations;
they do not explicitly state a birth-Moon computation or an ayanamsa. The
separate fixed policy
`bogamuni_2024_apparent_lahiri_natal_moon_identity_v1` is therefore labelled
`modern_moira_policy_not_source_claim`. It evaluates apparent geocentric Sun
and Moon longitudes in the true ecliptic of date on one reader-bound TT epoch,
uses half-open Moon-minus-Sun phase ownership, applies Lahiri true ayanamsa,
and assigns the sidereal Moon to 27 equal half-open `40/3`-degree sectors.
Exact internal boundaries belong to the following nakshatra; a maximum
one-ULP-below recovery exists only to restore the mathematically exact boundary
after binary representation, not as a tolerance band. The result exposes both
source mappings, every astronomical and sidereal intermediate, and the modern
composition status. It performs no schedule selection, materialization,
current-cell selection, scoring, or forecast.

The public surfaces are `pancha_pakshi_nakshatra_bird_mapping(...)` for the pure
source-table product, `pancha_pakshi_natal_moon_identity_at(...)` for the UT1
composition, `Moira.pancha_pakshi_natal_moon_identity(...)` for aware civil
instants, and `POST /v1/pancha-pakshi/identity/natal-moon`. The REST request
accepts only explicit `profile_id`, timezone-aware `dt`, and the exact policy
ID; location, supplied paksha or nakshatra, bird, ayanamsa selection, schedule,
current-cell, scoring, and forecast inputs are rejected. The profile remains
`source_scoped_public`, never becomes a default canon, and does not change the
1879 aksara-only identity ontology.

Stage 2H admits a third, separate source-scoped profile,
`bogamuni_chennai_2024_padu_bird_mapping`, with product kind
`padu_bird_mapping` and only the matching `padu_bird_mapping` capability.
Rendered-page inspection of the same exact Bogamuni 2024 original PDF, locally
identified by SHA-256
`035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`, found
the Purva weekday Padu stanza and commentary at leaf
[`n52`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n52/mode/1up),
the corresponding Amara material at
[`n60`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n60/mode/1up),
the repeated combined table at
[`n157`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n157/mode/1up),
and its restating commentary at
[`n158`](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024/page/n158/mode/1up).
The two Paksha stanzas govern; the repeated combined table and commentary
confirm them. The normalized product therefore has exactly fourteen
Paksha-by-weekday cells, one for each explicit Purva/Amara and Sunday-through-
Saturday pair, and no day/night axis.

This product preserves Padu as the source's death-or-inoperative bird. It does
not convert Padu into the schedule's instantaneous `RULE` activity, an
authority-day label, or the separately labelled eating bird. In particular,
the primary witnesses label an eating-bird table and authority days but do not
present an independently governed `Adhikara Pakshi` table. `Bharana` occurs as
secondary terminology rather than a primary source-table label. Moira
therefore admits neither `Adhikara Pakshi` nor `Bharana Pakshi` as an alias or
separate product, and it does not relabel the existing `first_eat_bird` field.
Uromarisi 1934 and the additional Bogar material remain separately observed,
unbound research context. Neither the Stage 2H profile nor its decision binds
them, and they supply neither runtime cells nor admission proof.

The Stage 2H lookup requires the explicit profile, source Paksha, and weekday.
It performs no astronomical or civil-day routing, natal identity, day/night or
schedule selection, materialization, current-cell judgment, condition or
score, or forecast. The profile is `source_scoped_public`, has no default, and
does not alter either prior profile.

The public surfaces are `pancha_pakshi_padu_bird_mapping(...)`,
`Moira.pancha_pakshi_padu_bird_mapping(...)`, and
`POST /v1/pancha-pakshi/roles/padu`. The canonical Stage 2H profile, manifest,
and admission-decision SHA-256 values are respectively
`5de0d1e28d47fad8be6a2a1ab648f2ed71eaf742be2775d166ea44981e96ff10`,
`eae9fc471da08eccf24515ef12cdaf59330aa1b7ad7f9d43432c7a1482704a03`, and
`9ea7c871643bb8fc68d420223d0090ca91699154c761c67ccaf9201f401906cd`.

Stage 2I adds `first_eat_bird_mapping` to the unchanged 1879 profile. The
source-owned object is one named schedule generator's first-samam EAT seed,
selected only by explicit profile Paksha, day/night half, and weekday. Rendered
inspection binds Purva day to
[`n16`](https://archive.org/details/dli.rmrl.000451_images/page/n16/mode/1up),
Purva night to
[`n21`](https://archive.org/details/dli.rmrl.000451_images/page/n21/mode/1up),
Amara day to
[`n26`](https://archive.org/details/dli.rmrl.000451_images/page/n26/mode/1up),
and Amara night to
[`n31`](https://archive.org/details/dli.rmrl.000451_images/page/n31/mode/1up).
The 28 cells already reside in the hash-bound schedule profile, so Stage 2I is
a manifest-only capability transition: profile SHA-256 remains
`4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64`,
while the manifest SHA-256 becomes
`d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8`
and the admission-decision SHA-256 is
`83c9bc0a423c09ccc113007625fee4a7d6b9ee1e890827f71595c96c3f826807`.

The Uromarisi-attributed 1934 publication corroborates all 28 cells at
[`n6`](https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934/page/n6/mode/1up)
and
[`n36`-`n37`](https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934/page/n36/mode/1up).
Its inspected PDF SHA-256 is
`e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`.
This is separate-publication corroboration; independent textual lineage is not
established, it supplies no runtime cell, and it does not justify a universal
canon or `corroborated_public` status. The result is not an ambient whole-day
eating bird, Padu, authority/Adhikara/Bharana bird, current activity,
condition, strength, score, electional judgment, or forecast. The public
surfaces are `pancha_pakshi_first_eat_bird_mapping(...)`,
`Moira.pancha_pakshi_first_eat_bird_mapping(...)`, and strict
`POST /v1/pancha-pakshi/schedule/first-eat-bird`.

Stage 2J is a research-only recovery from three Uromarisi-attributed
publications plus one separately scoped selector comparator. The
[official Tamil Digital Library catalog](https://tamildigitallibrary.in/book-details/TWpFNU1EST1BdG9aYXRvejB0bzk-/TkE9PUF0b1phdG96MHRvOQ--/TWpBPUF0b1phdG96MHRvOQ--/)
identifies the 1932 *Vinadi Pancha Pakshi* publication and Sarasvati Mahal
Library holding; its
inspected 197-page PDF has SHA-256
`dbd12d7e26f39ca7f9650a17311b5483eb478844144544a2cbb11aac7c3d6243`.
Rendered review of PDF pages 5, 88, and 89 establishes a five-position vinadi
ordinal axis beneath the named activities and multiple context-specific result
families. The 1922 Karunanidhi Pillai commentary witness has inspected PDF
SHA-256
`51b4b34890412fd57011aebe0c1ab22ab1800e5035a84bbbb9330ea0f6597741`;
rendered pages 115 and 116 require accurate vinadi and nazhigai division but
supply no arithmetic selector. The
[separate 1934 publication at Internet Archive](https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934)
has inspected PDF
SHA-256
`e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`;
rendered PDF pages 115 through 117 preserve the same governing verse numbers
and ordinal organization. Textual-lineage independence is not established.

The separately scoped
[Bogamuni-attributed 2024 comparator](https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024)
has inspected PDF SHA-256
`035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990`.
Rendered pages 157 and 158 attest a weighted Sūkṣma vector EAT `3/2`, WALK
`5/4`, RULE `2`, SLEEP `3/4`, and DIE `1/2` nazhigai, closing exactly to six;
page 169 separately attests an Eka Sūkṣma division into five equal parts. The
two selectors are incompatible, neither is a default, and neither is
automatically bound to Uromarisi ordinal outcomes. Machine-assisted reading is
not sufficient to normalize prognostic prose, but no human-language reviewer
is required. The Stage 2J decision records the bibliographic facts, hashes,
locators, bounded structural finding, exact rational selector candidates, and
fail-closed no-default/no-cross-witness-binding policy. Its SHA-256 is
`d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243`.
No source artifact is bundled, no manifest or runtime data changes, and no
engine, facade, or REST surface is created.

Stage 2K subsequently admits only the two Bogamuni 2024 editorial selectors
through the separate
`bogamuni_chennai_2024_sookshma_temporal_selector` profile. The weighted
policy binds rendered IA leaves `n156` and `n157`; the equal-fifths policy
binds `n156` and `n168`. Every call explicitly names one policy, a parent
activity, and an exact elapsed rational offset in `[0, 6)`. No default or
automatic selector exists. The weighted vector closes exactly to six
nazhigai; the equal policy creates five exact `6/5`-nazhigai ordinal cells and
does not invent activity assignments. Neither policy is attributed to the
Uromarisi lineage or bound to its ordinal outcomes. Civil-clock routing,
astronomy, schedule composition, outcome interpretation, condition, scoring,
electional search, and forecasting are not performed. The profile, current
manifest, and admission decision SHA-256 values are
`596c003c62ebbda913ca28aef318d77cb7b1cf42d92d3b1b7a20a44a01dd6526`,
`584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955`, and
`10bcfbd70dda28fd399e5c95b8bfa237b8e48f3b2cb20901fc21e0261a73cf70`.
No human-language reviewer is a runtime, admission, or maintenance dependency.

Stage 2L performs an independent-witness collation gate without changing that
public state. The hash-bound research decision records rendered inspection of
the Sarasvati Mahal Library's 574-page 2014 sixth edition of *Valaiyarul
Patinen Siddhargal Panchapakshi Sastram*, SHA-256
`894f88c3381f026aa1963861dd30e1f74039aa32a89fd84015efb3a098dc5366`,
and the two user-supplied modern guides. The institutional edition says that
its verses derive chiefly from Sarasvati Mahal palm-leaf manuscripts and a
minor share of printed books, while its explanations, mathematical notes, and
tables include editorial contributions. It identifies Agastya manuscript
`777`, Kumbamuni manuscript `7015`, Bogar and Uromarisi layers, and explicitly
preserves different Agastya/Bogar and Uromarisi activity-order doctrines.

The collation finds exact agreement for the seven Purva-day first-EAT seeds
and the Purva-day duration vector. It also finds material disagreement: the
2014 compilation uses distinct duration vectors for waxing night, waning day,
and waning night, whereas the admitted 1879 profile owns one uniform vector.
G. R. Narasimhan's 2018 secondary guide reproduces all four regime vectors but
provides no bibliography or primary-text lineage. The second supplied guide is
rejected because its AI-marked Canva artifact contains unrelated tarot
material. The institutional compilation is separately published and
multi-source, but it supplies no manuscript stemma or copying history;
textual-lineage independence from the admitted witnesses is therefore not
established. Stage 2L keeps every profile `source_scoped_public`, creates no
runtime data or public surface, and does not admit a default or universal
canon. Its research-decision SHA-256 is
`5534ddde1c0b87fa5fc3332112d02fd1c48c38e0a79f45f4a75a3e3c728a4c34`.

Stage 2M follows the Ramadevar candidate without treating a similar title as
content. The exact Commissionerate of Indian Medicine and Homoeopathy catalog,
SHA-256
`8bf4541aa46e3526d3218b1c35ae7bf174298ff6e29e86d9e10e7389dd5b5e4b`,
identifies serial `859`, manuscript `A5`, as `Ramadevar Panchapakshi` on PDF
page 52. It supplies no leaf images, transcription, physical description,
date, incipit, explicit, colophon, acquisition chain, copying history, or
computational rules for that item. Content and textual independence are
therefore not assessable.

The investigation separately excludes name-adjacent works. G.O.M.L. manuscript
`R.8978`, catalogued on PDF pages 93-94 of the 1999 volume with SHA-256
`4ff7f72891c6d53c3eaac502f1f1217a0cb950b60611524bfaff854d38b03ec4`,
is a complete old and injured `Ramadevar Patchini` work on gnana, breath, and
yoga. British Library EAP shelfmark `EAP1217/1/2851`, original Tamil University
reference `TU_TAMIL_2058-01_2661`, is an eighteenth-century 108-poem Patchani
work expressly classified as philosophy and ashtanga yoga. The Commissionerate
catalog also lists a separate `Ramadevar Patchani - 108` inside manuscript
`27`, while the 1991 Sarasvati Mahal *Ramadevar Sutiram: Ashtanga Patchini,
Valai Pujai* is a medicine, alchemy, yoga, and ritual publication. Shared
Ramadevar attribution, `Patchani` wording, or a 108-poem count does not make
any of these the `A5` Panchapakshi witness. Stage 2M remains research-only,
changes no public or runtime state, and has decision SHA-256
`921e604bcd81298aa6eb903acc967e68cfcf6e743c7d1379788ff9996212c6db`.

Stage 2N resumes the admitted implementation path without making acquisition
of `A5` a blocker. The separately named
`explicit_schedule_samam_subject_bird_sookshma_v1` modern policy composes the
admitted 1879 nominal schedule with the admitted Bogamuni 2024 selector only
when every profile, schedule axis, subject bird, selector policy, and exact
elapsed samam offset is supplied by the caller. It derives the parent activity
from the subject bird's unique cell in the selected schedule samam and then
applies the unchanged Stage 2K selector. Both nested source provenances remain
visible; the cross-profile join itself is not attributed to either witness.
No clock, astronomy, Uromarisi outcome, interpretation, condition, score,
election, or forecast is performed. The profiles, capability ledger, and
manifest remain unchanged. The Stage 2N decision fixture has canonical
SHA-256
`084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9`.

Stage 2O adds a second, explicitly modern composition without changing either
profile or the manifest. The caller must name the fixed-clock or
solar-proportional materialization policy and one Stage 2K selector policy.
The selected materialized cell supplies the samam, and the stored requested,
start, and end TT binary64 values are lifted exactly to rational numbers before
normalization to the samam's six nazhigai span. This arithmetic is Moira-owned
routing policy, not a historical-source claim. The fixed-clock long-half tail
remains explicit and never falls through to proportional timing. Paksha remains
caller supplied; no lunar inference, Uromarisi outcome, condition, score,
election, or forecast is composed. The Stage 2O decision fixture has canonical
SHA-256
`2ea686e774ba4468c0515f621771b8a142c79f04d89b69839f482e05c37b40df`.

Stage 2P returns to the primary Uromarisi-attributed 1934 witness for a bounded
research-only structural recovery. The Archive.org PDF was locally verified
at SHA-256
`e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0`
and PDF pages `115–126` were rendered and reviewed. Stage 2P indexed a
provisional five-activity by five-vinadi-ordinal locator grid: verses `230–239`
and `241–255`, with transition verse `240` excluded and the separate duration
section beginning at verse `256`. Stage 2T later refines verse `250` to a
blocked text-layer identity conflict rather than an unconflicted SLEEP cell.
The Stage 2P decision preserves only structure,
bibliographic identity, hashes, and repeatable page/verse locators. It copies
no source expression and performs no translation, outcome normalization,
medical or prognostic interpretation, scoring, or selector binding. The
profile, manifest, engine, facade, and REST state remain unchanged. The Stage
2P decision fixture has canonical SHA-256
`449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2`.

Stage 2Q pilots a source-owned semantic vocabulary on only the five EAT cells,
verses `230–234` on PDF pages `116–118`. Rendered-page review controls the
reading and Archive.org OCR supplies navigation alignment only. The bounded
record preserves source-stated resolution and exact duration alternatives,
distinct prescribed-response categories, medicine and `prithivi` term
references, unresolved relation clauses, and cell-local uncertainty. It does
not distribute Tamil source expression or a full translation and does not
assert that any historical illness statement is medically true. Generic
favorable/unfavorable labels, condition or numeric scoring, diagnosis, advice,
selector binding, and runtime exposure remain forbidden. The profile,
manifest, engine, facade, and REST state remain unchanged, with no
human-language reviewer dependency. The Stage 2Q decision fixture has
canonical SHA-256
`7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9`.

Stage 2R extends that vocabulary to the five WALK cells, verses `235–239` on
PDF pages `118–120`. It preserves exact-day, upper-bound-day, and
upper-bound-month expressions rather than coercing them into one numerical
unit. Resolution, abatement, and timed progression without explicit resolution
remain distinct. Source deity titles, explicit responses, medicine or
physician references, water-clause roles, the Navagraha-dosha reference, and
unresolved activity relations remain cell-local with uncertainty. The record
does not distribute Tamil source expression or a full translation and does not
assert that any historical illness statement is medically true. No selector,
runtime profile, manifest, engine, facade, or REST state changes, and there is
no human-language reviewer dependency. The Stage 2R decision fixture has
canonical SHA-256
`361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6`.

Stage 2S extends the bounded vocabulary to the five RULE cells, verses
`241–245` on PDF pages `120–122`. All five state resolution, but the record
preserves exact-day expressions separately from the third cell's upper bound.
Source deity titles, explicit actions, fire-clause roles, Saturn-dosha
references, historical effect language, and the fourth cell's surface
no-enmity statement remain cell-local and uncertainty-bearing. They are not
accepted as diagnoses, medical causes, symptoms, scores, or runtime relation
doctrine. The record distributes no Tamil source expression or full
translation and changes no selector, runtime profile, manifest, engine,
facade, or REST state. No human-language reviewer is required. The Stage 2S
decision fixture has canonical SHA-256
`85142480188a00ddec3de6f192a36025f282ca0eefa4643a6f1d74da4cec811d`.

Stage 2T reviews the five Stage 2P SLEEP locators on PDF pages `122–124` but
admits semantic records for only verses `246–249`. Verse `250` has a direct
text-layer identity conflict: its heading and verse identify DIE ordinal 5,
while its commentary identifies SLEEP ordinal 5. The prior hash-bound Stage 2P
fixture remains unchanged as historical locator evidence, but its five-cell
SLEEP claim is refined to four unconflicted cells plus one blocked candidate.
The four records preserve resolution difficulty, recurrence, exact and
upper-bound time, conditional mortality-or-resolution language, deity and
ritual references, treatment mediation, wind-dosha, harm, distress, and
surface activity relations with cell-local uncertainty. None becomes medical
truth, prediction, diagnosis, cause, symptom, score, advice, or runtime
doctrine. No selector, profile, manifest, engine, facade, or REST state
changes, and no human-language reviewer is required. The Stage 2T decision
fixture has canonical SHA-256
`09f7651325cdac058d9816b85b031ef528f514ae91fb8cd9636452b8d7fb302a`.

Stage 2U reviews the five unconflicted DIE cells, verses `251–255` on PDF pages
`124–126`, and carries verse `250` only as the blocked Stage 2T precursor. The
first cell preserves a rule-enmity mortality branch within two months and a
separate six-month source `tanmai` branch that is not normalized. The second
preserves both an instantaneous marker and a one-year marker without inventing
a harmonization. The remaining three cells state no numeric duration. All
mortality, body-destruction, nonresolution, space/void, fate, deity, activity
relation, and unclear source-branch language remains historical and cell-local;
none becomes prediction, medical truth, diagnosis, prognosis, cause, symptom,
score, advice, deterministic fate, calendar doctrine, or runtime relation.
Verse `256` begins a separate illness-duration section and is outside the
bounded record. No selector, profile, manifest, engine, facade, or REST state
changes, and no human-language reviewer is required. The Stage 2U decision
fixture has canonical SHA-256
`4954c13c33aa755bc0e8c6f47b7825d6ddb8346a2b6df39edf804872e81cbf70`.

The constitutional Phase 2 closure consumes the hash-bound Stage 2Q–2U
semantic records without moving their source expressions or data into the
published runtime. The private, data-free module
`moira._pancha_pakshi_classification` defines typed historical disposition,
time-expression, and semantic-marker classes plus immutable cell, conflict,
and complete-corpus vessels. The closure fixture contains `24` classifications
in exact EAT/WALK/RULE/SLEEP/DIE counts `5/5/5/4/5`; every classification
retains its source decision ID and SHA-256 and at least one cell-local
uncertainty. Tests derive every class directly from the prior semantic atom
rather than accepting a hand-authored classification independently.

Verse `250` remains a separate conflict vessel: heading and verse say DIE
ordinal 5 while commentary says SLEEP ordinal 5. It has no classification
payload and cannot also occupy the classified corpus. The closure adds no
runtime profile, data manifest entry, capability, package export, facade
method, or REST route. It authorizes only private Phase 3 inspectability over
existing fields and malformed-vessel hardening; it authorizes no new doctrine,
medical prognosis, score, advice, temporal selector binding, or runtime
relation. Human Tamil review, the separate illness-duration section beginning
at verse `256`, and the Commissionerate `A5` manuscript are not Phase 3 entry
requirements. `A5` content and copying history remain required only for a
future independent-corroboration claim. The Phase 2 closure fixture has
canonical SHA-256
`a5cd64696d4c040554f2c235056dfd28477fd0796fc82306f44ae43473d434e2`.

Constitutional Phase 3 adds inspectability only to those private Phase 2
vessels. Cell properties return already-stored identity and source binding,
lexically ordered marker values, and exact presence tests for mortality
language and stated, conditional, or unreconciled time shapes. Conflict
properties return all heading, verse, and commentary activity assignments,
their distinct set, their exact agreement relation, and the existing source
binding. Corpus properties and lookups expose deterministic verses, counts,
source bindings, marker-filtered subsets, activity groups, and exact
activity/ordinal or verse identity without fallback.

Vessel hardening now requires immutable tuple containers, the exact bounded
verse/ordinal matrix, activity-compatible Phase 2 time classes, one source
decision binding per activity, and the Stage 2T source binding for the verse
`250` conflict. Consequently SLEEP ordinal 5 and verse `250` return no
classification while conflict lookup for verse `250` remains present. These
are derived structural facts, not an outcome or repair. Phase 3 changes no
source semantics, doctrine, data, profile, manifest, capability, package
export, facade method, or REST route. Its completion opens Phase 4 only for a
separate explicit policy decision; it selects no default and attributes no
Stage 2K selector to Uromarisi. The Phase 3 decision fixture has canonical
SHA-256
`2fd93585f8d2d439882ee77cdeb28e5509e916cd752357d60caaa003cc9fb2ca`.

Constitutional Phase 4 admits one policy only within the private research
layer: `moira_explicit_uromarisi_activity_ordinal_lookup_research_v1`. The
policy vessel requires its typed ID and makes its derivation visible as a
modern Moira research rule over the source-owned activity/ordinal axis. It
records caller-supplied activity and ordinal, no source-attested or admitted
temporal selector binding, no Stage 2K composition, no outcome interpretation,
forbidden medical use, and `research_only` admission.

The policy-governed operation requires the corpus, policy, activity, and
ordinal as explicit arguments and delegates to the unchanged Phase 3
`classification_at` lookup. It neither accepts elapsed time nor selects a
Sookshma interval. Absence remains absence: SLEEP ordinal 5 still returns no
classification and verse `250` remains only a separate conflict. The two
Bogamuni 2024 selector IDs remain recorded as unadmitted cross-witness
candidates; neither is attributed to or composed with Uromarisi.

Phase 4 adds no runtime data, profile, manifest entry, capability, package
export, facade method, or REST route. It does not create prediction, prognosis,
diagnosis, advice, condition, score, or relation doctrine. Phase 4 completion
opens Phase 5 only for explicit relational formalization; it does not resolve
the existing source relation clauses in advance. The Phase 4 decision fixture
has canonical SHA-256
`4a444c91bab9a4949664e6bca4e64ad0ee341b439019db831429e4548bd2c4f9`.

Constitutional Phase 5 formalizes one private relation record for each of the
`24` unconflicted Phase 2 classifications. The governing object is a
classified-cell-owned source relation record, not a favorable/unfavorable
judgment. It binds the Phase 4 decision, Phase 2 closure, unchanged manifest,
and exact Stage 2Q through Stage 2U source decisions by canonical digest.

The relation corpus preserves `17` present clauses and `7` clauses explicitly
not recorded. Ten EAT/WALK clauses remain `unresolved_clause`, retaining their
source confidence without normalized meaning. Seven RULE/SLEEP/DIE clauses
retain only the bounded surface categories `no_enmity`,
`rule_enmity_disallowed`, `rule_enmity_branch`,
`earth_rule_enmity_disallowed`, and `rule_enmity_required`; their source atoms
state no relation-specific confidence, so Phase 5 records none. Surface labels
do not establish endpoints, direction, semantics, condition, or score. Verse
`250` remains excluded as the existing text-layer identity conflict.

Phase 5 adds no runtime data, profile, manifest entry, capability, package
export, facade method, REST route, selector binding, prediction, prognosis,
diagnosis, advice, condition, score, or medical claim. Completion opens Phase 6
only for relational hardening and inspectability. The Phase 5 decision fixture
has canonical SHA-256
`e8e189f75418cc96bc6930e2e93d2cfcebc849cb4080001ee4b4b07b158908d1`.

Constitutional Phase 6 hardens the private relation corpus and exposes only
derived inspectability. Each record now reports its stored identity and whether
it is detected, admitted, scored, unresolved, or a named bounded surface
category. The corpus exposes deterministic identities, unique source bindings,
presence counts, exact detected/not-recorded/unresolved/named/admitted/scored
subsets, typed activity filtering, and exact activity/ordinal and verse
lookups.

Detection means only that the source clause is present. The Phase 6 admitted
and scored subsets are both empty; neither is inferred from detection or a
named surface category. The views preserve `17` detected, `7` not recorded,
`10` unresolved, and `7` named-surface records. SLEEP ordinal `5` and verse
`250` return no relation record without fallback or conflict repair. Corpus
construction also rejects non-record members before attempting identity or
source-binding inspection.

Phase 6 adds no source atom, resolved relation meaning, endpoint, direction,
condition, score, selector binding, runtime data, profile, manifest entry,
package export, facade method, REST route, prediction, prognosis, diagnosis,
advice, or medical claim. Completion opens Phase 7 only for an integrated local
condition whose doctrine must be separately established. The Phase 6 decision
fixture has canonical SHA-256
`b175bcd1e537fb551cd26b18d6e6caa37f7a574b7e0a96b336d6fbb97eff9b12`.

Constitutional Phase 7 creates one private integrated local-condition profile
for each of the `24` unconflicted cells. The governing unit pairs an exact
Phase 2 classification with its exact Phase 5 relation record under the
mandatory Phase 4 explicit activity/ordinal policy. Classification and relation
identity and source binding must match, canonical order is preserved, and each
relation record has exactly one profile.

The integration is structural, not evaluative. All profiles carry
`not_evaluable_no_admitted_condition_doctrine`, `not_assigned` favorability, a
null condition score, no prognosis, forbidden medical use, and research-only
admission. Relation detection remains visible, but Phase 6 establishes zero
admitted and zero scored relations; Phase 7 rejects any attempted admission or
scoring drift rather than turning detection or a surface category into a
condition judgment.

Phase 7 adds no source truth, resolved relation meaning, favorable/unfavorable
label, numeric score, selector binding, runtime data, profile, manifest entry,
package export, facade method, REST route, prediction, prognosis, diagnosis,
advice, or medical claim. Completion opens Phase 8 only for aggregate
structural intelligence over the stored local profiles. The Phase 7 decision
fixture has canonical SHA-256
`401c90b7d7c15663427e034a527f983054800f948019cf12b404a0086b3203be`.

Constitutional Phase 8 creates one private immutable structural aggregate over
the complete Phase 7 local-condition corpus. It counts `24` profiles with
activity coverage EAT `5`, WALK `5`, RULE `5`, SLEEP `4`, and DIE `5`; all `24`
remain `not_evaluable_no_admitted_condition_doctrine`. Relation counts remain
`17` detected, `7` not recorded, `10` unresolved, `7` named-surface, `0`
admitted, and `0` scored. Verse `250` remains the sole blocked conflict.

The aggregate validates that activity and evaluation counts cover all profiles,
detected plus not-recorded covers the corpus, unresolved plus named-surface
covers detected relations, and scored remains a subset of admitted and
detected. Aggregation is repeatable and immutable. Counts are not rankings,
weights, favorable/unfavorable judgments, condition scores, prognoses, or
medical evidence.

Phase 8 adds no source truth, relation meaning, evaluative doctrine, selector
binding, runtime data, profile, manifest entry, package export, facade method,
REST route, prediction, prognosis, diagnosis, advice, or medical claim. It
closes the agreed eight-phase private research sequence. There is no automatic
Phase 9 transition and no public admission; any network work or admission review
requires a new explicit decision. The Phase 8 decision fixture has canonical
SHA-256
`b193b3ba62d1c5eb57d526777310fa16f29c81fa999e69b813670c680ba2fd13`.

The later explicit SCP transition authorizes Phases 9-12 without expanding
source truth. Phase 9 projects the same 24 profiles into canonical nodes and
attaches the 17 detected clauses as candidate annotations. Because the bounded
records establish neither endpoints nor direction, it admits zero edges and
marks topology metrics not evaluable. Its decision SHA-256 is
`49935df6e96595b5cd365dbea12acabcf862eb81a120c3d9122d29ad4962872b`.

Phase 10 freezes the complete cross-layer identity, source-binding, ordering,
absence, conflict, and failure contract. Its canonical structural fingerprint
is `2133ad1c72ea5209facbb83ff8f40cfd09c1efea5340df7943fe08ff599cface`
and its decision SHA-256 is
`9ef977585ad1dc9dc517316eb864a8de26f462fb852977bfef936d8756ef64a0`.
This is regression integrity for the bounded structure, not an external
historical or medical authority claim.

Phase 11 freezes the executable architecture in
`PANCHA_PAKSHI_UROMARISI_BACKEND_STANDARD.md`, including its validation codex,
private boundaries, and explicit nonclaims. Its decision SHA-256 is
`697eecaf22cf4e8d42ca9b7044633e6407ca8d5577dd4407180029cfc00055c0`.

Phase 12 admits only immutable constitutional-status metadata through the
package and `Moira` facade. The historical corpus, local profiles, aggregate,
network, hardening receipt, manifest, and REST transport remain private or
unchanged. The status truthfully reports `research_only`, no admitted relation
semantics or graph metrics, no prognosis, and forbidden medical use. Its
decision SHA-256 is
`581c137bbbd0fdfe11f61dbb43bfb6cc6e1dafd420f52dd80c2413a4a59ada03`.

The remaining Uromarisi-attributed edition and Sarasvati Mahal Library series
213 are retained as conflict or bibliographic evidence. The exact inspected
series 213 artifact identifies itself as the sixth edition of August 2014;
its front matter also preserves the earlier fifth-edition foreword and its
1991 first-edition history. Their unadmitted verse/commentary disagreements
are not copied into runtime truth.
Archive rights or license labels are not runtime inputs and are not public
admission gates, because no modern scans, prose, layouts, or table
transcriptions are packaged.

Moira's MIT license covers Moira-authored code, schema, and prose. Archival
artifacts are outside the distributed product rather than materials Moira
attempts to relicense. Only independently normalized symbolic rules,
bibliographic facts, hashes, and locators are eligible for a profile. The
absence of independent-witness collation limits the current claim to this
named machine-reconciled witness; it prevents a corroborated, generalized, or
default-canon claim but does not block the narrow source-scoped public product.
The source-reading uncertainty remains explicit, with no human-review
dependency. A blank archive license field,
contributor biography, or separate archival-rights clearance step does not
govern admission. The standing non-bundling policy keeps protected source
expression outside Moira's distributed product.

The governing research boundary, admission tiers, conflicts, fail-closed
invariants, and public contract are documented in
[`PANCHA_PAKSHI_RESEARCH_STANDARD.md`](./wiki/02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md).
Public access is additive through `moira.pancha_pakshi`, package-root and
`moira.vedic` exports, ten kernel-free and eight kernel-backed `Moira`
methods, and seventeen explicit-profile `/v1/pancha-pakshi` routes. No API
selects a default profile. The 1879 astronomical-paksha route occurs only
through its explicit geocentric policy and never supplies an inferred label to
another operation.
Fixed-clock and solar-proportional current-cell selection occur only through
their separate explicit solar-half-precedence policies; the former may return
an uncovered-tail status, while the latter always selects one cell from
complete-half coverage. Natal identity occurs only through the separate 2024
profile and fixed modern composition. Padu lookup occurs only through the
separate 2024 Padu profile and explicit Paksha/weekday labels. First-EAT lookup
occurs only through the separate Stage 2I route and never materializes or
selects a current schedule. Stage 2J Uromarisi outcome evidence remains
research-only; Stage 2K exposes only the two separately sourced explicit
Bogamuni temporal selectors and cannot route a clock instant or compose an
outcome. Stage 2L adds only witness-collation evidence and leaves
`corroborated_public` unassigned. Stage 2M disambiguates the title-only `A5`
Ramadevar Panchapakshi candidate from non-Panchapakshi `Patchani` witnesses and
also leaves `corroborated_public` unassigned. Stage 2N separately permits only
the explicit modern schedule-to-Sookshma join described above; it does not
change either source profile or bind an outcome. Stage 2O permits civil-time
routing into that join only when both timing and selector policies are named;
it provides no automatic policy selection or outcome interpretation. Stage 2P
adds only the page-and-verse locator structure of the 1934 Uromarisi illness
grid. Stage 2Q adds a research-only semantic-atom pilot for its five EAT cells,
and Stage 2R extends the same boundary to five WALK cells. Both retain per-cell
uncertainty. Stage 2S continues it through five RULE cells while keeping fire,
dosha, effect, and relation clauses non-runtime. None makes a medical-truth
claim or runtime binding. Stage 2T adds four unconflicted SLEEP records and
blocks verse `250` because its heading and verse disagree with its commentary
about parent activity identity.
Condition, scoring, automatic policy fallback, and forecasting remain outside
the admitted surface.

The 2026-07-20 blind, representative-grid, and later adjudicating reviews are
recorded in
[`PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md`](./wiki/05_research/PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md).
The original two records remain frozen with their disagreements intact. The
later multi-pass page-image adjudication established the full `30/5/6`
day/night scope and table axes, confirmed the Amara-night schedule and complete
directed relationship matrix, and demonstrated that the prior Pūrva-night
generator was wrong. The corrected source-scoped profile treats identified grids as
bird/activity assignment evidence while taking chronology only from explicit
prose and verse. That reconciliation remains machine-assisted historical
evidence, not a linguistic-authority claim or an external authority oracle;
it cannot silently rewrite either earlier source record. The additive
`pancha_pakshi_1879_public_admission_2026_07_20.json` decision links the former
and current profile hashes and records the narrower source-scoped public claim,
capabilities, nonclaims, evidence limits, and unchanged computational
projection. Admission and provenance metadata are deliberately outside that
projection because the migration changes them.

## Provenance history

Earlier in Moira's release history, during a licensing discussion with the Swiss Ephemeris authors, the house module carried — as a conservative precaution — an attribution notice referencing `swehouse.c`, and written permission was obtained from the authors. Moira's house implementation is independently derived from the mathematical definitions; the precautionary attribution was therefore determined to be unnecessary and was removed.

**Version timeline:**

| Releases | `swehouse.c` attribution notice | Status |
|---|---|---|
| 2.1.2 – 3.2.3 | Present (precautionary) | Available; retained for reproducibility |
| 3.2.4 and later | Removed | Independently derived; recommended for new work |

Earlier releases are intentionally left available rather than withdrawn, so that any pinned dependency continues to resolve. All releases are MIT-licensed.

## Guidance for downstream and commercial users

- **For new commercial or downstream work, build on 3.2.4 or later.** This line is independently derived and carries no third-party attribution.
- Moira is MIT-licensed across all releases; you may use, modify, and ship it commercially without copyleft obligations.
- The written permission referenced above was personal, precautionary diligence during the licensing discussion. The current implementation neither contains the referenced code nor relies on that permission.
- For license-scope questions about a specific use, use the project contact channel listed in the package or repository metadata.

---

*This document is the authoritative, standard-path record of Moira's license and provenance. It is intended to be discoverable without recourse to commit history.*
