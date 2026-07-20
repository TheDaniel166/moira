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

The unified numbered-asteroid catalog is generated from JPL Horizons
heliocentric `VECTORS` states and materialized as Moira Type-13 shards. Its
ordered shard registration and per-body coverage exceptions are recorded in
`moira/kernels/asteroids/manifest.json`; the generated BSP files are separately
acquired runtime resources.

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
short topographic microcontact or any unreported tangency. The network-marked
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
feature guarantee. The network-marked comparison refreshes the
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

## Pancha Pakshi source-scoped witnesses

Moira admits one explicitly named Pancha Pakshi profile as a source-scoped
public product. Its private ingestion data records normalized computational
facts and locators from the 1879 Tamil print catalogued by Internet Archive as
[`dli.rmrl.000451_images`](https://archive.org/details/dli.rmrl.000451_images).
The source is traditionally attributed to Agastya; that attribution is
bibliographic metadata, not a verified historical-authorship claim. The print
is a research witness, not a package asset. Moira records independently
normalized computational rules and source locators; it never bundles archival
scans, PDFs, OCR, page images, copied table layouts, source prose, or
third-party translations.

Internet Archive metadata classifies `dli.rmrl.000451_images.zip` as the
original image archive and `dli.rmrl.000451.pdf` as a derivative PDF. The
source-scoped profile retains the archive MD5/SHA-1 identities of both, plus the
locally verified PDF SHA-256. Those hashes identify the exact witness used for
research; they do not import or redistribute either file. The same metadata
names Ti. Kandasami Pillai as having reviewed the edition. His exact
contribution and life dates remain unresolved bibliographic questions, but
they do not create a Moira distribution issue because no source expression is
copied into the package.

The public profile `agastya_madras_1879_akshara_fixed_clock` is restricted to
the witness's aksara/query-or-name-initial operating schedule, fixed-clock
timing, and directed relationship matrix. It must not be represented as a
natal-Moon canon. Exact source locators and archive file checksums are retained
in the machine-readable profile. The schema-v2 manifest owns its
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
Solar-proportional scaling remains a different, non-admitted capability.

The Stage 2B authority roles remain separate. The 1879 witness governs nominal
schedule facts; the *Tamil Lexicon* governs the fixed nazhigai unit; IERS
governs the TT/SI-second time-scale basis; and the frozen Stage 2A Horizons
comparison governs only the solar anchor. The additive
`pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json` decision binds
those roles, the unchanged profile hash, the frozen Stage 2A decision, and the
manifest-only capability transition. It is not an external Pancha Pakshi
current-cell oracle or independent-witness corroboration.

Later Bogar- and Uromarisi-attributed editions and Sarasvati Mahal Library
series 213 are retained only as metadata in a conflict ledger. The latter's
official catalog says sixth edition/2014 while its inspected internal title
page says fifth edition/September 2011; both records remain visible. Their
verse/commentary disagreements are not resolved or copied into runtime truth.
Archive rights or license labels are not runtime inputs and are not public
admission gates, because no modern scans, prose, layouts, or table
transcriptions are packaged.

Moira's MIT license covers Moira-authored code, schema, and prose. Archival
artifacts are outside the distributed product rather than materials Moira
attempts to relicense. Only independently normalized symbolic rules,
bibliographic facts, hashes, and locators are eligible for a profile. The
absence of competent-human Tamil review and independent-witness collation
limits the current claim to this named machine-reconciled witness; it prevents
a corroborated, generalized, or default-canon claim but does not block the
narrow source-scoped public product. A blank archive license field,
contributor biography, or separate archival-rights clearance step does not
govern admission. The standing non-bundling policy keeps protected source
expression outside Moira's distributed product.

The governing research boundary, admission tiers, conflicts, fail-closed
invariants, and public contract are documented in
[`PANCHA_PAKSHI_RESEARCH_STANDARD.md`](./wiki/02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md).
Public access is additive through `moira.pancha_pakshi`, package-root and
`moira.vedic` exports, five kernel-free and two kernel-backed `Moira` methods,
and seven explicit-profile `/v1/pancha-pakshi` routes. No API selects a default
profile or a current schedule cell.

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
evidence, not competent-human Tamil sign-off or an external authority oracle;
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
