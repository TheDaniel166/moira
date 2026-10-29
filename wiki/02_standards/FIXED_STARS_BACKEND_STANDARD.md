# Fixed Stars Backend Standard

Version: 0.3 (draft)<br>
Date: 2026-10-29<br>
Status: Phases 0-3 implemented; Phase 4 planned
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

- barycenter: straight-line space motion of the system;
- relative orbit: `moira.multiple_stars` elements and its Kepler solution;
- component offset: the relative offset times the component's mass fraction.

A component without an admitted orbit keeps straight-line propagation of its
own catalog values, and its result records that.

## 7. Validation

| Product | Authority | Evidence class |
|---|---|---|
| Stage 1 (`astrometric`, `geometric`) | ERFA `pmsafe` (rigorous space motion) | authority validation |
| `apparent` | ERFA `apcg` with Moira's DE441 Earth state, then `atciq`; ERFA `atci13` as an independent-Earth check | authority validation |
| Frame | ERFA `pnm06a` with the true obliquity | authority validation |
| Binary components | ORB6 ephemerides and the source orbit papers; separation and position angle | authority validation |
| Refactors | the pre-change output for every registry star | regression parity |
| Swiss Ephemeris | any product | cross-engine corroboration only |

Invariants: annual aberration never exceeds 20.5 arcseconds; the parallax
shift never exceeds the catalog parallax; perspective acceleration vanishes
when radial velocity is zero; a binary component never strays from its
barycenter by more than its orbit allows.
