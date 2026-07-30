# Physical Heliacal Visibility Source Ledger

Date: 2026-07-30
Status: Phase 0 source disposition and Phases 1-2 closed
Doctrine:
[PHYSICAL_HELIACAL_VISIBILITY_ADMISSION_DOCTRINE.md](../../01_doctrines/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_ADMISSION_DOCTRINE.md)

## Purpose

This ledger identifies the sources allowed to govern the physical
heliacal-visibility project, the role of each source, its validity boundary,
and whether any code or data may cross into Moira artifacts.

It prevents formulas, coefficients, event meanings, or data identities from
being reconstructed from memory.

Access date for every online source below: 2026-07-29 unless separately
stated. The REPTRAN module was accessed on 2026-07-30.

## Governing Sources

| Source | Exact identity | Project role | Validity and use boundary | License or distribution disposition |
|---|---|---|---|---|
| Kasten and Young, “Revised optical air mass tables and approximation formula” | Applied Optics 28 (1989), 4735–4738, DOI [10.1364/AO.28.004735](https://doi.org/10.1364/AO.28.004735) | Preserve and regression-test the current relative-air-mass option | Apparent above-horizon optical air mass; not the new directional radiance generator | Equation reference only; no table or figure redistribution |
| Schaefer, “Telescopic Limiting Magnitudes” | PASP 102 (1990), 212–229, DOI [10.1086/132629](https://doi.org/10.1086/132629) | Preserve the lineage of the current named limiting-magnitude and extinction family | Historical composite visibility family; not silently promoted to the new physical baseline | Equation/reference use only; no copied paper content |
| Schaefer, “Astronomy and the Limits of Vision” | Vistas in Astronomy 36 (1993), 311–361, DOI [10.1016/0083-6656(93)90113-X](https://doi.org/10.1016/0083-6656(93)90113-X) | Preserve the current named directional twilight and component lineage as a regression family | Review/model family spanning multiple applications; every retained equation keeps its existing admitted domain | Equation/reference use only; no copied paper content |
| Krisciunas and Schaefer, “A Model of the Brightness of Moonlight” | PASP 103 (1991), 1033–1039, DOI [10.1086/132921](https://doi.org/10.1086/132921) | Preserve the current named legacy moonlight option | Empirical photometric moonlight model; outside the new moonless twilight baseline | Equation/reference use only; any replacement receives a new identifier |
| Schironi, “The Language of Astronomy” | 2024, DOI [10.1515/9783111314532-002](https://doi.org/10.1515/9783111314532-002), especially pp. 30–31 | Names and first/last semantics of the four visible phases summarized from Ptolemy | Terminology and event doctrine only; not a numerical visibility model | Article CC BY 4.0; cite, do not copy extended text |
| Knoll, Tousey, and Hulburt, “Visual Thresholds of Steady Point Sources of Light in Fields of Brightness from Dark to Daylight” | JOSA 36 (1946), 480–482, DOI [10.1364/JOSA.36.000480](https://doi.org/10.1364/JOSA.36.000480) | Independent point-source threshold evidence across dark-to-daylight fields | One-arcminute steady sources, five young experienced observers, unaided binocular natural-pupil viewing; not an observer-population probability | Bibliographic/equation reference only; no table or figure redistribution |
| Blackwell, “Contrast Thresholds of the Human Eye” | JOSA 36 (1946), 624–643, DOI [10.1364/JOSA.36.000624](https://doi.org/10.1364/JOSA.36.000624) | Underlying contrast-threshold experiment fitted by Crumey | Detection data under the paper's stimulus, adaptation, and probability conditions; not itself an astronomical atmosphere model | Bibliographic/equation reference only; no source table redistribution without separate permission |
| Crumey, “Human Contrast Threshold and Astronomical Visibility” | MNRAS 442 (2014), 2600–2619, arXiv [1405.4209](https://arxiv.org/abs/1405.4209), DOI [10.1093/mnras/stu992](https://doi.org/10.1093/mnras/stu992) | Mathematical bridge from contrast-threshold data to astronomical point-source visibility | The paper presents a dark-to-daylight achromatic model, but its astronomical verification is mainly dark-sky/scotopic; twilight use requires separate validation | Transcribe equations with equation-number receipts; do not copy prose, figures, or tables |
| Tousey and Koomen, “The Visibility of Stars and Planets During Twilight” | JOSA 43 (1953), 177–183, DOI [10.1364/JOSA.43.000177](https://doi.org/10.1364/JOSA.43.000177) | Independent twilight observational validation | Historical Washington, D.C. star cases and stated observing conditions; validation evidence, not a universal coefficient table | Bibliographic observations may be encoded as source-owned fixtures with citation; no figure reproduction |
| Previc, Kosnik, McLin, Dennis, and Goettl, “The Visibility of Point Sources as a Function of Background Luminance, Target Luminance, Eccentricity, Wavelength, and Flicker Rate” | AFRL-HE-BR-TR-2005-0138, October 2005, DOI [10.21236/ADA442029](https://doi.org/10.21236/ADA442029) | Independent literature-synthesis envelope for observer protocol and sensitivity checks | Synthesis of 14 studies after a broader literature review; shows that eccentricity and background matter strongly; not an astronomical event formula | Approved for public release/distribution unlimited, but used as reference-only; no tables or figures copied |
| CIE 191:2010 / CIE TN 004:2016 | CIE 191:2010 MES2 system; free technical note [CIE TN 004:2016](https://files.cie.co.at/841_CIE_TN_004-2016.pdf) | Named transition between photopic and scotopic spectral weighting | A spectral luminous-efficiency system, not a point-source detection threshold; adaptation field and S/P assumptions must be receipted | Implement formula from the standard/note; the note itself is not redistributed |
| CIE photopic spectral luminous efficiency | Dataset DOI [10.25039/CIE.DS.dktna2s3](https://doi.org/10.25039/CIE.DS.dktna2s3), `CIE_sle_photopic.csv` | `V(lambda)` response data | 360–830 nm at 1 nm, linear interpolation, zero extrapolation; the composite uses only the 380–780 nm overlap with the scotopic table | Dataset CC BY-SA 4.0; permitted only in the separately licensed data pack with attribution/share-alike notice |
| CIE scotopic spectral luminous efficiency | Dataset DOI [10.25039/CIE.DS.gr6w4b5g](https://doi.org/10.25039/CIE.DS.gr6w4b5g), `CIE_sle_scotopic.csv` | `V'(lambda)` response data | Metadata column domain 380–780 nm at 1 nm, linear interpolation, zero extrapolation | Dataset CC BY-SA 4.0; permitted only in the separately licensed data pack with attribution/share-alike notice |
| libRadtran | Version 2.0.6, released 2024-12-24, [official download](https://www.libradtran.org/doku.php?id=download), [manual](https://www.libradtran.org/doc/libRadtran.pdf) | Offline reference generator for spectral direct transmission and directional twilight radiance | MYSTIC fully spherical reference cases for low Sun and near-horizon lines of sight; runtime use is prohibited | GPL; external build tool only, with no source, binary, binding, or runtime dependency copied into Moira |
| Shettle aerosol model family | E. P. Shettle, “Models of aerosols, clouds and precipitation for atmospheric propagation studies,” AGARD Conference Proceedings 454 (1989), as implemented by the pinned libRadtran 2.0.6 source and data | Named rural, maritime, urban, and tropospheric aerosol profiles in summer and winter | Checkpoint 5 binds all eight supported haze/season optical-depth files and fixes vulcan code 1; the direct-extinction oracle and directional-radiance uses remain distinct | Source/data remain inside the external GPL research laboratory; no libRadtran profile file enters Moira or the future data pack |
| libRadtran REPTRAN module | `reptran_2024_all.tar.gz`, accessed 2026-07-30 from the [official download page](https://www.libradtran.org/doku.php?id=download) | Full-spectral molecular-absorption research input for libRadtran 2.0.6 | REPTRAN fine is the admitted 380-780 nm reference; medium is characterization only | External operator-supplied research data; the archive has no embedded notice or license file and is not redistributed by Moira |
| ESO Advanced Cerro Paranal Sky Model | [ESO project page](https://www.eso.org/sci/software/pipelines/skytools/skymodel) | Component comparison and validation reference | Explicitly developed for Cerro Paranal; adapting it to other sites is not straightforward | Code GPLv2; no copying or runtime integration; reference-only |
| Jones et al., “An advanced scattered moonlight model for Cerro Paranal” | A&A 560 (2013), A91, DOI [10.1051/0004-6361/201322433](https://doi.org/10.1051/0004-6361/201322433) | Candidate later moonlight model | Site and model assumptions must remain explicit; not part of the clear-sky twilight baseline | Paper-derived new component only after a separate equation and licensing audit |
| PALACE v1.0 | GMD 18 (2025), 4353–4389, DOI [10.5194/gmd-18-4353-2025](https://doi.org/10.5194/gmd-18-4353-2025), data/code DOI [10.5281/zenodo.14064022](https://doi.org/10.5281/zenodo.14064022) | Later airglow comparison and component-validation reference | Paranal model built from site-specific X-shooter/UVES evidence; not a global default | Data CC BY 4.0, code GPLv3; reference-only in the current project |

## Source Conclusions

### Legacy regression boundary

Kasten-Young, Schaefer, and Krisciunas-Schaefer remain authorities for the
existing named components only. Their formulas and outputs remain regression
protected. They are not blended into
`clear_sky_naked_eye_point_source_v1`, and newer evidence does not mutate
their identifiers.

### Event doctrine

Schironi records Ptolemy's four visible configurations as:

- morning rising: first seen rising before sunrise;
- morning setting: first seen setting before sunrise;
- evening rising: last seen rising after sunset; and
- evening setting: last seen setting after sunset.

That exact four-part language is the authority for the new physical enum.
Legacy `heliacal`, `acronychal`, and `cosmic` strings are preserved only as
existing software contracts.

### Detection criterion

Crumey supplies the selected mathematical family because it:

- is derived systematically from human contrast-threshold evidence;
- covers achromatic target/background conditions from darkness to daylight;
- distinguishes point-source behavior; and
- is already part of Moira's admitted single-epoch visibility lineage.

However, the current `CRUMEY_2014_POINT_SOURCE` identifier is not widened.
The new `blackwell_crumey_full_range_point_source_v1` component must be
implemented separately and admitted only after:

1. equation-by-equation transcription receipts;
2. Blackwell/Knoll threshold checks;
3. Tousey-Koomen twilight comparisons;
4. modern independent cases where obtainable; and
5. explicit residual and validity-domain reporting.

CIE MES2 supplies spectral weighting across adaptation states. It does not
replace the detection threshold. The receipt must name the effective
weighting and adaptation coefficient.

The AFRL synthesis prevents an implicit “generic observer” claim. The first
model therefore fixes a known-location directed-observation protocol and does
not extrapolate to peripheral discovery, flicker, casual scanning, or an
observer population.

### Atmosphere

libRadtran 2.0.6 is selected as an offline reference laboratory, not an engine
dependency. Fully spherical MYSTIC cases are selected for difficult low-Sun
directional sky radiance. Double-precision DISORT with pseudo-spherical
geometry is selected for deterministic direct transmission, with its
documented horizontal-irradiance projection removed explicitly. Phase 1 pins
all solver, atmosphere, aerosol, absorption, surface, wavelength, random-seed,
normalization, and convergence settings.

Phase 1 checkpoint 3 binds the governing libRadtran radiative-transfer
theory and `cdisort.c` implementation receipts. It distinguishes the
continuous Chapman integral from the selected surface flux implementation,
which applies the bottom-layer midpoint Chapman factor to the full surface
vertical optical depth. Independent controlled-atmosphere reconstruction now
passes over the admitted 0.25-45 degree true-altitude domain.

Phase 1 checkpoint 4 binds the official external REPTRAN module and validates
the 290-level candidate against 579- and 1,157-level controls across all six
AFGL named atmospheres. REPTRAN fine is admitted as the clear molecular
full-spectral research reference. The result is surface-only and does not
itself admit environmental interpolation, response integration, or a runtime
table.

Phase 1 checkpoint 5 binds the libRadtran aerosol, pressure, ozone, humidity,
Beer-Lambert/Chapman, and delta-M implementation surfaces plus all eight
Shettle haze/season optical-depth files. AOD is authoritative at 550 nm with
`beta = AOD550 * 0.55 ** alpha`; aerosol visibility is not a second public
control. Default pressure is named-profile-derived, while a measured override
is admitted only inside both the 500-1,100 hPa absolute range and a 0.85-1.08
ratio to the profile pressure at observer altitude. Gray ground albedo is
radiance-only. Temperature and relative humidity remain profile-derived.

The direct-extinction oracle preserves total aerosol optical depth and uses
`aerosol_modify ssa set 0` only to prevent delta-M phase-function bookkeeping
from contaminating the physical Beer-Lambert line-of-sight extinction
quantity. Directional-radiance runs retain physical aerosol scattering. The
73-run evidence also rejects linear unit-AOD scaling over the entire
near-horizon domain. These decisions freeze parameter roles and candidate
nodes, not interpolation accuracy or a runtime table.

Phase 1 checkpoint 6 closes the observer-altitude and pressure-ratio
interpolation study for direct extinction. It uses site-relative 290-level
atmospheres, eight altitude nodes from 0 through 5,000 m, five
profile-relative pressure nodes, all six named molecular profiles, and
bilinear interpolation in extinction magnitude. Across 12,636 withheld
spectral values, maximum extinction error is `0.0124663582904496` mag and
95th-percentile error is `0.00404537460338972` mag. The law does not
extrapolate and requires all four training corners to pass the existing
absolute-pressure and pressure-ratio bounds.

The final Phase 1 radiance artifact uses REPTRAN-fine ALIS over 380-780 nm and
the exact CIE photopic and scotopic datasets. A training-only diagnostic
selected 531 nm as the common spectral-importance, normalization, and
independent-anchor wavelength without executing any holdout. The admitted
64-node response grid has nine untouched off-grid response cases.
Photopic/scotopic maximum interpolation errors are `0.354270166272975` and
`0.25296630532828035` mag; their 95th-percentile errors remain below the
unchanged `0.3`-mag ceiling.

The separately licensed `moira-physical-heliacal-visibility` data pack
version `1.0.0` contains only generated response-integrated products,
per-cell solver uncertainty, direct-extinction values, error receipts,
provenance, and notices. Its root-manifest SHA-256 is
`49ac2b68ea105a8e055b27e8d4d70f6cbfe9533f971ef5e6000f0bdd95d6771b`.
The same immutable pack passed independent Linux and Windows validation.
It contains no CIE source table or libRadtran/REPTRAN source, profile, data
file, binary, or engine dependency.

The first pack is explicitly a fixed U.S. Standard, rural-summer, sea-level
baseline. Earlier environmental and altitude/pressure evidence does not
silently create absent pack axes. Requests outside the pack's exact manifest
domain must be typed `not_evaluable`; broader environmental coverage requires
new versioned data-pack evidence.

The initial baseline excludes moonlight and site-specific airglow. Jones, the
ESO model, and PALACE remain named comparison or later-component sources.
They do not enter the baseline merely because they are newer.

## Immutable Source Identities

### libRadtran archive

```text
URL:
  https://www.libradtran.org/download/libRadtran-2.0.6.tar.gz
Version:
  2.0.6
Release date:
  2024-12-24
Retrieved bytes:
  154147176
SHA-256:
  64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840
Observed Last-Modified:
  Sat, 18 Jan 2025 10:28:42 GMT
Observed ETag:
  "9301968-62bf87dcdc4c9"
```

Phase 1 checkpoint 1 independently acquired and verified this identity before
the first generator build. Both offline builders re-verify byte count and
SHA-256 before every authorized profile. A future hash mismatch stops the
build and requires a source-ledger amendment.

### REPTRAN module

```text
Official download page:
  https://www.libradtran.org/doku.php?id=download
Direct archive:
  https://www.libradtran.org/lib/exe/fetch.php?media=download%3Areptran_2024_all.tar.gz
Access date:
  2026-07-30
Retrieved bytes:
  698709957
SHA-256:
  55893c80bcc999651bac3bf014ee64aaf602653ba640eb5bebe787a5d8eacce7
Regular archive files:
  292
```

The 260 files overlapping the libRadtran 2.0.6 source data are byte-identical;
the module supplies 32 official files absent from that tree. The separately
constructed data root is bound by 1,478 per-file checksums and canonical
receipt SHA-256
`68f1817782e424ef617dab03ad985a3fbcb91fa2ed0239a8c2de1e8cb6855b59`.

No notice, license, README, or citation file is embedded in the REPTRAN
archive. The module remains an external research input and is not copied into
the repository, engine wheel, or future visibility data pack without a
separate distribution decision.

Checkpoint 2 additionally binds the exact libRadtran 2.0.6 implementation
files governing altitude insertion, vertical interpolation, molecular-profile
combination, and spherical MYSTIC elevation:

```text
src/atmosphere.c
  b900ade7e603260a47fec3efa305577ab6806bbf539021ec028a0c1360099cf8
src/uvspec_lex.l
  174755190e50ecc3099c80a29cb71627c0a33a5e2009d1869c23140095658d89
src/ancillary.c
  97dc576d1cb8f54c40d733cea3d5a56b49a0e7f8f39aa812e55ba7fbe1a7665f
libsrc_c/mystic.c
  d1d981e0dd2e961f7f8991368b92e2179c382bab81c8ae72ed17cd31dbcab87b
```

Those sources establish why the spherical Monte Carlo probe uses a
source-derived atmosphere with the site as its bottom level and a separately
bound O4 companion profile. The resulting construction matched all 45
supported deterministic-altitude oracle cases at emitted precision.

Checkpoint 5 additionally binds ten governing libRadtran manual/source files,
all eight Shettle `tau550` profile files, and the exact `uvspec` executable
used by the 73-run environmental artifact. The admitted root-manifest
SHA-256 is
`e79a250b01f00783f272bae409fa323a94b5c7811375760bf536eaa7de6b0580`;
the source-owned parameter and holdout contract is recorded in
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ENVIRONMENT_CONTRACT_CHECKPOINT_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ENVIRONMENT_CONTRACT_CHECKPOINT_2026-07-30.md).

Checkpoint 6 binds 5,037 libRadtran runs, 50,768 files, and four preserved
failed-design receipts. Its admitted root-manifest SHA-256 is
`2264727cf4d1a74bb747aa51cc44e4ba9e703e09c132ab57eb2c0afef863c727`.
The same immutable bytes passed the independent validator under Linux and
Windows; the latter used an immutable tar transport to local NTFS to avoid
the WSL UNC per-file traversal penalty. The compact receipt is recorded in
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md).

### CIE photopic table

```text
Data DOI:
  10.25039/CIE.DS.dktna2s3
File:
  https://files.cie.co.at/CIE_sle_photopic.csv
Metadata:
  https://files.cie.co.at/CIE_sle_photopic.csv_metadata.json
SHA-256:
  ee5d5d17922ae645d4af52cacf6a50bdb9385749f9d2181ca312eb2b08febac2
MD5:
  f389958555461a7d9a7562145e8ca9c0
License:
  CC BY-SA 4.0
```

The official dataset landing page displayed a different MD5 during the
2026-07-29 audit. The downloaded bytes and the official metadata JSON agreed
on the values above. Moira binds SHA-256 plus metadata identity and records
the discrepancy; it does not use the stale displayed MD5 as authority.

### CIE scotopic table

```text
Data DOI:
  10.25039/CIE.DS.gr6w4b5g
File:
  https://files.cie.co.at/CIE_sle_scotopic.csv
Metadata:
  https://files.cie.co.at/CIE_sle_scotopic.csv_metadata.json
SHA-256:
  6a75d3fdbcbf5e9e9a07478511933eefeda953f3e2cc14b74459e5a099ec3759
MD5:
  3e45714a429d02e5d1f2a752226d7698
License:
  CC BY-SA 4.0
```

The scotopic metadata description says 360–830 nm, while its column metadata
and file coverage are 380–780 nm. The runtime composite uses the actual
380–780 nm overlap and records the metadata inconsistency.

## Licensing and Artifact Boundary

The engine source and wheel remain MIT and contain no copied GPL code.

The physical visibility table is a separate artifact:

```text
Artifact:
  Moira visibility data pack
License:
  CC BY-SA 4.0
Runtime acquisition:
  explicit caller action only
Engine dependency:
  optional caller-supplied path
Network during calculation:
  prohibited
```

The admitted pack attributes the CIE datasets, preserves their DOI, includes
the share-alike notice, and identifies the generated libRadtran numerical
products and exact generator configuration.

The repository now contains a metadata-only compatibility contract and
independent validator, but not the CIE tables or physical LUT. A future
release review must still inspect the completed external artifact and notices
before distribution. This is an engineering disposition, not legal advice.

## Formula Admission Inventory

No formula is admitted merely by appearing in this ledger.

| Planned calculation | Governing source | Phase that must capture exact equation/section | Current state |
|---|---|---|---|
| Blackwell/Crumey point-source threshold | Crumey 2014 with Blackwell 1946 lineage | Phase 2 | Implemented from Crumey equations 28 and 34 with fixed `F=2`; independently checked against all eight public Tousey-Koomen Table I rows |
| MES2 spectral response | CIE 191:2010, CIE TN 004:2016, and CIE TN 007:2017 | Phase 2 | Implemented with fixed-point solution and same-equation bracketed fallback; both official TN 007 worked examples pass |
| Spectral radiance to named photometric quantity | CIE TN 004:2016 | Phase 1/2 | Phase 1 source-locks the official CIE tables and admits response-integrated photopic/scotopic data-pack products; Phase 2 owns single-epoch composition and limiting-magnitude propagation |
| Direct transmission | libRadtran 2.0.6 DISORT pseudo-spherical configuration with external REPTRAN fine data | Phase 1 | Deterministic smoke and exact repeat reproduced; elevated-site construction matched 45 oracle cases; the surface midpoint-Chapman implementation is source-traced; the 290-level clear molecular grid is bounded across all six AFGL profiles; REPTRAN fine is the full-spectral research reference; Checkpoint 5 source-binds AOD550, Angstrom, ozone, pressure, albedo, and all eight Shettle profiles and admits a delta-M-safe aerosol direct-extinction oracle; Checkpoint 6 admits site-relative altitude/pressure interpolation against 12,636 withheld spectral values; the first pack admits a 57-node, 400-bin direct surface with 22,400 untouched holdout bins |
| Directional twilight radiance | libRadtran 2.0.6 MYSTIC configuration | Phase 1 | The final v9 artifact admits adaptive 531 nm anchored REPTRAN-fine response products over a 4-by-4-by-4 grid, nine untouched response holdouts, per-cell uncertainty, and a typed boundary below -9 degrees |
| Physical event root | Moira-defined margin law and admission doctrine | Phase 3 | Semantic law fixed; numerical solver pending |
| Moonlight | Jones 2013 or existing named legacy option | Phase 4 | Excluded from baseline |
| Airglow | measured local background; ESO/PALACE comparison | Phase 4 | Excluded from baseline |

Phase implementation documents must quote no more source text than needed,
name exact equation or section identifiers, and attach independent numerical
fixtures.

## Phase 2 Exact Equation Admission - 2026-07-30

The Phase 2 implementation binds the following exact source artifacts:

| Artifact | Engine use | Local source receipt |
|---|---|---|
| [Crumey 2014](https://arxiv.org/abs/1405.4209) | Full-range point-source threshold from equations 28 and 34; equation-28 coefficients `a1=5.949e-8`, `a2=-2.389e-7`, `a3=2.459e-7`, `a4=4.120e-4`, `a5=-4.225e-4`; fixed field factor `F=2` | PDF SHA-256 `fa6ef183f9402be4d321bff5fa2c112510f89ca683b534e33c63fdb6538e50a4` |
| [CIE TN 004:2016](https://files.cie.co.at/841_CIE_TN_004-2016.pdf) | MES2 governing equations and photopic/scotopic quantity definitions | PDF SHA-256 `a549fcf5f98ae5fdd959b331dbb91eae99f5fd397bd288ad6b59c43723a4494f` |
| [CIE TN 007:2017](https://files.cie.co.at/934_CIE_TN_007-2017.pdf) | Two official MES2 calculation examples and the task-applicability restriction in clause 6 | PDF SHA-256 `efdd11f4bdf7d77ab3b1fb8e6b94ac89599521eba7425e474bbc82cf34c7877a` |
| [Tousey and Koomen 1953](https://opg.optica.org/josa/abstract.cfm?uri=josa-43-3-177) | Independent eight-row threshold validation, not coefficient fitting | Public HTML SHA-256 `4e50f748c6c0de310ceeadcbbcd0a6626a3fccd74fe1063f9cc91640ad3212ef` |

CIE TN 007 restricts MES2 use to peripheral visual tasks. The admitted
observer protocol is therefore
`known_location_directed_averted_observation_v1`: the target position is known
and attention is deliberate, but fixation is averted/peripheral after
adaptation to the immediate directional field. The engine does not claim
foveal equivalence.

[CIE 257:2026](https://www.cie.co.at/publications/recommendations-practical-application-cie-system-mesopic-photometry-outdoor-lighting)
is recorded as a current follow-on publication. Its full report was not
inspected for this admission, so it is not an equation or coefficient
authority for Phase 2.

The source-owned numerical fixture is
`tests/fixtures/physical_visibility_phase2_equations_v1.json`. The Crumey
implementation reproduces the public Tousey-Koomen Table I threshold values
with a maximum absolute residual of `0.03572` in log10 illuminance
(`0.0893` magnitude), within the declared fixture acceptance bound.

## Phase 2 Planetary Target-Data Admission

The first-candidate planetary audit is complete for Mercury, Venus, Mars,
Jupiter, and Saturn:

- the source and effective band of apparent visual magnitude;
- phase-angle and distance dependence for planets;
- color or spectral-profile source identity;
- transformation equations and their validity range;
- treatment of missing or ambiguous photometry; and
- serialization of the target receipt.

The separately distributed physical-visibility pack version 1.1 binds:

| Source | Admitted role | Exact identity |
|---|---|---|
| [Payne et al. planetary spectra](https://zenodo.org/records/17470005) | Full-phase geometric-albedo spectra used with the locked extraterrestrial solar spectrum to derive each planet's base photopic and scotopic response integrands | Versioned record `10.5281/zenodo.17470005`, publication `10.3847/PSJ/ae2feb`, CC BY 4.0; five per-file SHA-256 receipts are recorded in the Phase 2 checkpoint artifact |
| [Mallama et al. 2017](https://arxiv.org/abs/1609.05048) | Source-domain UBVRI phase/color laws; Mercury remains gray, Venus/Mars/Jupiter use phase-polynomial color, and Saturn uses phase plus effective ring sub-latitude | PDF SHA-256 `7feb8edb372502cee5dc9c6a7656205e3279353bb38f9a98cbecbe8e8d733f91`; DOI `10.1016/j.icarus.2016.09.023` |
| CIE photopic and scotopic datasets | Response integration and S/P ratio | Dataset DOIs `10.25039/CIE.DS.dktna2s3` and `10.25039/CIE.DS.gr6w4b5g`; exact CSV receipts remain source-locked |
| libRadtran 2.0.6 `atlas_plus_modtran` | Extraterrestrial solar spectral shape used only during offline pack derivation | SHA-256 `432600ef415706c401a4c0e17c6b733a631f1556a78c3da32e936830288b414b` |

The 400-bin response weights remain external pack products; no planetary
source spectrum or CIE table enters the MIT engine wheel. The engine resolves
phase angle and Saturn ring geometry from the same ephemeris context as
apparent magnitude. It refuses profile extrapolation beyond the source-owned
domains and does not accept caller-supplied planetary response weights.

The exact profile specification is
`scripts/visibility_reference_lab/phase2_planetary_target_profile_pack_spec.json`.
The compact source-controlled receipt is
`tests/artifacts/visibility_reference_lab/phase2_planetary_target_profiles_checkpoint_2026-07-30.json`.
The admitted 1.1 manifest SHA-256 is
`f594fd12058cc7f5c7bc9de7f2b06652bef3c0604ef7b0a05a069e54e4026c87`.

The current fixed-star field named `color_index` is not sufficient evidence of
a particular color system. Fixed-star admission remains outside Phase 2; no
implementation may silently interpret that field.

## Phase 2 Numerical-Error Propagation Receipt

Phase 1 assigns limiting-magnitude propagation to Phase 2. The admitted
single-epoch implementation now consumes the exact downstream error contract
from `error-envelope.json`:

- per-cell solver relative standard error is bounded by the maximum
  contributing interpolation corner and must remain below one;
- photopic and scotopic maximum interpolation errors are applied in
  surface-brightness magnitude;
- direct-extinction maximum interpolation error is applied in magnitude;
- binary32 storage error is combined separately with both paths; and
- P95 values are retained as diagnostics and may not exceed their declared
  maxima.

For modeled twilight, the numerical bounds perturb the twilight response while
holding the source-identified dark-sky anchor nominal. CIE MES2 adaptation and
the Crumey threshold are evaluated across all four photopic/scotopic bound
corners. The resulting limiting-magnitude extrema are combined conservatively
with the direct-extinction target-magnitude bound to produce the final margin
envelope.

The method receipt is
`phase2_data_pack_declared_numerical_error_envelope_v1`. The solver term is
propagated at exactly plus or minus one reported relative standard error; it
is not relabeled as a hard maximum. The method is explicitly not a
scientific-confidence interval. Input-measurement, target photometry and
spectral-source, observer-population, model-form, and actual-atmosphere
uncertainties remain named but unquantified.

## Phase 0 Source Disposition

Every candidate source now has one of four explicit roles:

- doctrine authority;
- implementation equation/data authority;
- independent validation authority; or
- later reference-only candidate.

No GPL code enters the engine, no site-specific model becomes a global
default, no CIE data enters the MIT wheel, and no unidentified coefficient is
approved. The source gate is closed for Phase 0. Phase 1 implementation
evidence, the external fixed-domain data packs, and Phase 2 engine-side
single-epoch truth are complete. Phase 3 owns physical event-time solving.
