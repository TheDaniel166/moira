# Fixed Stars Backend Standard

Version: 0.4 (draft)<br>
Date: 2026-10-29<br>
Status: Phases 0-4 implemented; Phase 5 (documentation and release evidence) planned
Scope: catalog-star positions from the sovereign star registry

This standard governs:

- `moira.stars.star_at`, `all_stars_at`, `star_light_time_split`, and the
  `FixedStar` result with its `FixedStarTruth`;
- the sovereign registry `moira/data/star_registry.csv` and its companion
  `star_provenance.json`;
- every module that propagates catalog astrometry: `moira/deep_sky.py`,
  `moira/lunar_occultation_contacts.py`, `moira/occultations.py`, and the
  interval enclosure in `moira/_gochara_window_astronomy.py`;
- the binary-component positions built from `moira/multiple_stars.py`.

It does not govern heliacal visibility doctrine, star lore, or astrological
technique rules that consume star positions.

## 1. Products

A catalog star has three distinct positions. Moira never collapses them, and
every result names which one it carries.

| Product | Meaning | Earth-based effects | Kernel |
|---|---|---|---|
| `astrometric` | The catalog direction propagated to the date: the direction from the solar-system barycenter along which the star's light arrives | none | not needed |
| `apparent` | Where the star is seen from Earth's center at the date | annual parallax, gravitational light deflection, annual aberration | DE441 Earth state |
| `geometric` | Where the star physically is at the date, ignoring that its light takes time to arrive | none | not needed |

An astrometric catalog (Hipparcos, Gaia, SIMBAD's adopted values) records the
observed direction and its rate of change. Propagating the catalog therefore
yields the `astrometric` product. The `geometric` position lies further along
the star's motion by the light-travel time; it is rarely needed and is
provided only through the light-time split.

Every product is expressed, unless a caller asks otherwise, in the true
ecliptic and equinox of date, as Moira's planets are.

## 2. One pipeline

All products come from one pipeline. A product is the stage at which the
pipeline stops, not a separate implementation.

1. **Space motion.** Catalog row to barycentric direction at the date,
   starting from the row's own reference epoch. Straight-line motion in three
   dimensions uses the proper motion, parallax and radial velocity. A binary
   component adds its orbital offset from the system barycenter (Section 6).
   This stage ends as `astrometric`, or as `geometric` when evaluated at the
   date shifted by the light-travel time.
2. **Earth-based effects** (`apparent` only). Parallax from Earth's
   barycentric position, then light deflection, then annual aberration, using
   `moira.corrections.apply_deflection` and `apply_aberration`, the same
   functions the planets use.
3. **Frame.** Rotation to the requested frame of date.

Rules:

- Stage 1 exists once, in `moira/_stellar_space_motion.py`. It is written over
  an arithmetic adapter so that the same expressions serve plain floats and
  the certified interval enclosures used by Gochara windows. A second
  implementation of space motion anywhere in the package is a review failure.
- Stage 2 uses only `moira.corrections`. A module that needs extra steps (for
  example topocentric diurnal aberration in occultations) applies them after
  the shared stages, never instead of them.
- No module reconstructs a catalog direction from an ecliptic longitude and
  latitude it was given; it asks stage 1 for the vector.

## 3. Catalog contract

Each registry row carries:

| Field | Meaning |
|---|---|
| `ra_deg`, `dec_deg` | ICRS position at the reference epoch |
| `pmra_mas_yr` | proper motion in right ascension times cos(declination) |
| `pmdec_mas_yr` | proper motion in declination |
| `parallax_mas` | trigonometric parallax |
| `radial_velocity_km_s` | radial velocity (Phase 2) |
| `radial_velocity_status` | `measured` or `unknown` (Phase 2) |
| `ref_epoch_jd` | reference epoch of the astrometry, as a TDB Julian date |
| `frame` | `ICRS` |

- The loader refuses a row whose frame is not `ICRS` or whose reference epoch
  is missing or not finite.
- An `unknown` radial velocity propagates as zero, and the result exposes
  that status. It is never written as a silent `0.0`.
- Per-field sources (SIMBAD bibliographic references for position, proper
  motion, parallax and radial velocity) live in `star_provenance.json`.
- Catalog rebuilds are reviewed before promotion and diffed against the
  previous registry.

### 3.1 Radial velocities (Phase 2)

`scripts/data_ingestion/augment_star_registry_astrometry.py` fetches SIMBAD's
adopted radial velocity for each row's recorded SIMBAD identifier into a
candidate file, which is reviewed before `apply-rv` writes it. A velocity is
admitted as `measured` only when SIMBAD reports a radial velocity (type `v`)
with quality grade A to D. Grade E, a missing value, or an unresolved
identifier leaves the status `unknown`.

The 2026-10-29 fetch (SIMBAD TAP through its CfA mirror, because the
Strasbourg service was unreachable from the build host) resolved 1,808 of
1,809 rows: 1,619 velocities admitted, 186 grade-E values and 3 missing values
left `unknown`, and one row ("Bodu") without a SIMBAD identifier. Each row's
`astrometry_sources` in `star_provenance.json` records the service, retrieval
time, SIMBAD identifier, the references of the adopted position, proper
motion, parallax and radial velocity, and the velocity's error and grade.

The same fetch compared the registry's astrometry with SIMBAD's current
values. All rows agree except two, which SIMBAD has re-solved since the
registry was built: δ Indi (0.31 arcsec in position, 10.8 mas/yr in proper
motion, 3.9 mas in parallax) and σ² Ursae Majoris (3.0 mas/yr in proper
motion). Their positions are not refreshed by Phase 2.

### 3.2 Declared residual: light time along the line of sight

ERFA `pmsafe` corrects the straight-line motion for the changing light-travel
time (the Rømer effect); Moira's stage 1 does not. Because a catalog proper
motion is already the observed rate, the effect is of second order. With the
catalog radial velocities it measured, over the whole registry on 2026-10-29:
at most 0.005 arcsec between 1800 and 2200, 0.11 arcsec at 1000 CE, and
0.82 arcsec at 1000 BCE, the largest in each case being Barnard's Star.

## 4. Result contract

`FixedStarTruth.position_product` names the product: `astrometric`,
`apparent`, or `geometric`.

`FixedStarTruth.motion_model` names the stage-1 model: `straight_line`, or
`binary_orbit` for a component placed about its system's barycentre
(Section 6).

`FixedStarTruth.true_position` is a legacy flag kept for REST compatibility.
It is `True` only for the `geometric` product. Earlier releases set it on the
`astrometric` product, which was a mislabel.

`star_light_time_split` returns `(observed, geometric)`: the observed
direction is the `astrometric` product at the date, and the geometric
position is stage 1 evaluated at the date plus the light-travel time. Earlier
releases propagated the observed position backward by the light-travel time,
which reversed the correction.

## 5. Default product and consumers

Open decision: whether `star_at` returns `apparent` (consistent with Moira's
apparent planets) or `astrometric` (kernel-free, current numbers) when no
product is requested. Until it is decided the default remains `astrometric`.

`star_at(name, jd_tt, product=..., reader=...)`, `all_stars_at(...)` and
`Moira.fixed_star(name, dt, product=...)` accept the product. The apparent
product needs a planetary reader (passed, active, or the facade's) and fails
closed without one.

Technique consumers state their product explicitly:

| Consumer | Product | Note |
|---|---|---|
| `moira/occultations.py` coarse search | `apparent` | compared with the observer-apparent Moon |
| `moira/occultations.py` star rays | stage 2 on the caller's direction | topocentric diurnal aberration follows; the physical ray omits aberration |
| `moira/astrocartography.py` | `astrometric` | current convention; open with the default decision |
| `moira/heliacal.py` solar elongation | `astrometric` | current convention; open with the default decision |
| `moira/primary_directions/fixed_stars.py` | `astrometric` | current convention; open with the default decision |

Catalog lookups (constellation and Behenian helpers) inherit the default.

### 5.1 Repairs made with Phase 3

- `star_light_time_split` previously moved the "observed" position backward
  by the light-travel time. It now returns the astrometric product as the
  observed position and the geometric product one light time ahead.
- `FixedStarTruth.true_position` is now `True` only for the geometric
  product, and `FixedStarClassification.observer_mode` is `barycentric`
  except for the apparent product.
- The occultation star rays passed a unit vector to light deflection, which
  treated the star as 1 km away and made the solar deflection vanish. The
  shared stage 2 places a direction-only star at effectively infinite
  distance. Measured on 80 star rays, the change is a median of 0.003 arcsec
  and at most 0.22 arcsec (Spica a few degrees from the Sun in October 2024).
- The occultation coarse search passed observer arguments that `star_at`
  silently ignored and compared an astrometric star with the apparent Moon.
  It now requests the apparent product.

### 5.2 Apparent product validation

Against ERFA `apcg` (with Moira's DE441 Earth state) and `atciq`, for 12
stars at 6 epochs from 1800 to 2100: median 0.000003 arcsec, worst 0.00014
arcsec (Barnard's Star, 2100). Gate: 0.001 arcsec, in
`tests/integration/test_stars_apparent_erfa.py`.

## 6. Binary components (Phase 4)

A component of a resolved binary with a published orbit is placed at the
system barycenter plus its share of the relative orbit:

- **barycenter:** straight-line space motion of the system's own astrometry
  (stage 1, the same core as every other star);
- **relative orbit:** the `moira.multiple_stars` elements, through Kepler's
  equation and the Thiele-Innes projection: the offset of B from A, toward
  east and north of J2000;
- **component offset:** with q = m_B / (m_A + m_B), A sits at −q times the
  relative offset and B at (1 − q) times it.

The offset is laid in the plane of the sky at the barycenter's reference
position, so the orbit stays fixed in space while the line of sight turns.
Its physical size follows from the reference parallax, so its angular size
changes with the system's distance. The orbit is evaluated at the date the
light is received, as its elements were fitted to observation dates.

The registry row of a component is unchanged: it records the astrometry its
source measured. `star_at` and every stage-1 consumer use the orbit model
for the components listed below; the result's `motion_model` is
`binary_orbit`. A component without an admitted orbit, including Proxima
Centauri, keeps straight-line propagation of its own row.

| Registry star | System, component | Orbit | Barycenter |
|---|---|---|---|
| Sirius | Sirius A | Bond et al. 2017, Table 4 (ORB6 BdH2017) | Hipparcos 1997 HIP 32349 orbital solution |
| Rigil Kentaurus | α Centauri A | Akeson et al. 2021, Table 8 (ORB6 Ake2021) | refit, Section 6.2 |
| Toliman | α Centauri B | Akeson et al. 2021, Table 8 | refit, Section 6.2 |

### 6.1 Sirius

The Hipparcos Catalogue solved Sirius with an orbital model (multiplicity
flag `O`, astrometric reference flag `+`): its position and proper motion at
J1991.25 already describe the centre of mass. The registry row, taken from
SIMBAD, is that same solution moved to J2000, so it is the barycenter, not
Sirius A. The barycenter uses Bond et al.'s adopted parallax (378.9 mas) and
their system radial velocity corrected for Sirius A's gravitational redshift
(−8.47 km/s); q = a_A / a = 2.4761 / 7.4957. Sirius A lies up to 3.9 arcsec
from the barycenter; at 2000 the orbit model moves it 1.5 arcsec from the
straight-line row.

The orbit elements `moira.multiple_stars` carried before Phase 4 were
labelled Bond et al. 2017 but were older values (P = 50.090 yr,
a = 7.56 arcsec, T = 1994.3); they are replaced by Bond's Table 4.

### 6.2 α Centauri barycenter refit

Akeson et al. (2021) fitted the barycenter position and proper motion to the
absolute Hipparcos and ALMA positions of A and B. Their machine-readable
ephemeris (Table 12) is reproduced to 0.3 mas at 2010 by moving the
barycenter at constant rates in right ascension and declination. Straight-line
motion in space, which ERFA `pmsafe`, astropy and Moira agree on to 0.01 mas,
departs from that path by 0.1-0.2 mas/yr²: with the published proper
motion it misses the Hipparcos position of A by 47 mas and Akeson's tabulated
barycenter by 94 mas at 2050.

Moira therefore refits the barycenter position and proper motion at J2019.5
to the same measurements (18 ALMA positions with Akeson's 3 mas systematic
uncertainty, 6 mas for October 2018; the van Leeuwen 2007 Hipparcos positions
of A and B with their catalog errors), with straight-line space motion and
Akeson's orbit, parallax, radial velocity and mass fraction held fixed. The
refit moves the proper motion by (−0.77, +1.53) mas/yr and the position by
2 mas. `tests/support/binary_star_barycentre.py` performs the fit and the
integration test re-derives the catalog values from
`tests/fixtures/binary_star_orbit_references_2026_10_29.json`.

### 6.3 Measured on 2026-10-29

| Check | Evidence class | Sample | Result | Gate |
|---|---|---|---|---|
| Relative orbits vs ORB6 ephemerides (position angle precessed to the equinox of date with ERFA `pmat06`) | authority validation | 2 systems × 5 years, 2025-2029 | 0.04° and 0.0004 arcsec worst | 0.06°, 0.0008 arcsec |
| Sirius B relative to A vs Bond et al. HST measures | authority validation | 17 epochs, 1997-2016 | median 0.006, worst 0.016 arcsec | 0.025 arcsec |
| α Cen B relative to A vs Akeson Table 12 | authority validation | 41 years, 2010-2050 | 0.0014 arcsec worst | 0.003 arcsec |
| α Cen A and B vs ALMA absolute positions (with Moira's DE441 parallax) | authority validation | 18 positions, 2018-2019 | RMS 7.1 mas, worst 14.6 mas | 10, 20 mas |
| α Cen A and B vs Hipparcos (J1991.25) | authority validation | 2 positions | A 1.4 mas; B 57 mas (2.7σ) | 3σ per coordinate |
| Barycenter motion vs ERFA `pmsafe` | authority validation | 2 systems × 1000, 1800, 2200, 3000 | below 0.01 arcsec | 0.01 arcsec |
| Offsets balance about the barycenter; component inside its orbit | invariant | −1000 to 3000, every 50 years | holds | — |
| Every other star unchanged | regression parity | 1,806 stars and 60 deep-sky objects at 7 epochs | bit-identical | exact |

Without the orbit model, straight-line propagation of the α Centauri rows
(instantaneous Hipparcos proper motions) strays from the orbit model by 50
arcsec (A) and 28 arcsec (B) at 1800 and by 234 and 114 arcsec at 1000 CE.

### 6.4 Other consumers

- The native heliacal evaluator moves a star in a straight line. For a
  binary component it receives the chord of the stage-1 track over the search
  window (position at the midpoint, proper motion joining the ends), which
  stays within 0.1 arcsec of the orbit over 400 days.
- The Gochara interval enclosure has no orbit enclosure; it refuses a binary
  component as a live sidereal anchor. No current ayanamsa anchor is one.

## 7. Validation

| Product | Authority | Evidence class |
|---|---|---|
| Stage 1 (`astrometric`, `geometric`) | ERFA `pmsafe` (rigorous space motion) | authority validation |
| `apparent` | ERFA `apcg` with Moira's DE441 Earth state, then `atciq`; ERFA `atci13` as an independent-Earth check | authority validation |
| Frame | ERFA `pnm06a` with the true obliquity | authority validation |
| Binary components | ORB6 ephemerides, Bond et al. 2017 HST measures, Akeson et al. 2021 ephemeris and ALMA/Hipparcos positions (Section 6.3) | authority validation |
| Refactors | the pre-change output for every registry star | regression parity |
| Swiss Ephemeris | any product | cross-engine corroboration only |

Invariants: annual aberration never exceeds 20.5 arcseconds; the parallax
shift never exceeds the catalog parallax; perspective acceleration vanishes
when radial velocity is zero; a binary component never strays from its
barycenter by more than its orbit allows.
