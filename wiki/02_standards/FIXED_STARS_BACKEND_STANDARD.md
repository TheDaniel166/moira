# Fixed Stars Backend Standard

Version: 0.1 (draft)<br>
Date: 2026-10-29<br>
Status: Phases 0-1 in progress; Phases 2-4 planned
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

## 5. Default product

Open decision: whether `star_at` returns `apparent` (consistent with Moira's
apparent planets) or `astrometric` (kernel-free, current numbers) when no
product is requested. Until it is decided the default remains `astrometric`,
and every internal consumer states its product explicitly.

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
