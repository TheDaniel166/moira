# Moira 6.9.8 - Relationship Charts, Draconic Frames and Classical Sources

Release date: 2026-09-29. Upgrade path: 6.9.0 to 6.9.8.

Moira 6.9.8 corrects the synastry, composite and draconic surfaces found while
building consumer tools on them, adds an explicit unknown-birth-time contract,
and admits several classical techniques from their sources: al-Biruni's
star-based mansions, Hellenistic rays, the D60 deities, Sayanadi avasthas and
the BPHS Ashtottari start. It also tightens light deflection, heliacal
apparition selection and Sothic chronology, and exposes new REST surfaces for
lunar orientation and the Sothic cycle.

## Key Changes

### Relationship Charts

- Synastry aspects no longer compare two unrelated natal speeds as applying or
  separating, and count one node (the True Node) instead of doubling every
  node contact.
- The composite route now defaults to the `reference_place` method.
- Five internal synastry bookkeeping routes were removed from the REST
  surface (see the compatibility notes).

### Draconic Charts

- Draconic positions keep their source body's speed and retrograde state.
- Draconic charts carry the source chart's house cusps and angles rotated
  into the draconic frame, and state whether they are geocentric or
  topocentric.

### Unknown Birth Time

- Chart, houses and relationship requests accept `time_unknown`. The Moon is
  left out and houses and observer-dependent angles are refused, so a guessed
  noon time can no longer pass as a real one.

### Classical Techniques

- al-Biruni star-based lunar mansions with unequal boundaries at each
  mansion's marker star for the date.
- Hellenistic rays (aktinobolia) are now evaluated.
- Named Shashtiamsha (D60) deities from BPHS chapter 6.
- Sayanadi avasthas and sub-states from BPHS chapter 45, with the classical
  effects.
- Ashtottari Dasha start and balance per BPHS 46.17-22, with Abhijit counted.
- Jaimini Chara Dasha can continue into a second cycle.
- Antiscion contacts can report their motion state.
- A Sabian Symbols degree lookup.

### Astronomy and Validation

- Gravitational light deflection follows the IAU SOFA Ld / ERFA `eraLd`
  formulation in Python and in the native evaluator.
- Heliacal and acronychal risings require a real transition from invisible to
  visible, with daily scans anchored to local mean solar midnight.
- Sothic results distinguish found and not-found years, name calendars
  explicitly, and no longer present schematic projections as observed epochs.
- Uranian hypothetical bodies use receipted source orbits and return apparent
  geocentric positions with speed.
- Midpoint dials fold longitude by the dial modulus; the previous projection
  folded twice.
- The current small-body element and node catalog validation is closed for
  11,223 asteroids and 497 comets; apsidal-passage accuracy remains a named
  frontier.

### REST Service

- New `POST /v1/phase/lunar-orientation` and `POST /v1/sothic/*` routes.
- Batch requests are capped at 128 items, and costly eclipse, occultation and
  Sade Sati responses are cached per process.
- Longitude returns accept admitted asteroids and comets.

## Compatibility Highlights

- Five `/v1/synastry/*` bookkeeping routes were removed.
- The composite route's default `method` changed from `midpoint` to
  `reference_place`, which in 6.9.8 requires `reference_latitude`; `midpoint`
  is rejected. (Correction: an earlier version of these notes said
  `midpoint` could still be requested. 6.9.9 defaults the reference latitude
  to the mean of the two birthplaces.)
- Synastry aspects between two charts carry no applying/separating motion.
- Midpoint dial coordinates and planetary-picture orbs change for every chart
  (the former values were wrong).
- Ashtottari Dasha periods can change for births where the former start rule
  differed from BPHS.

## Install

```text
pip install --upgrade moira-astro==6.9.8
```

For the optional REST service:

```text
pip install --upgrade "moira-astro[server]==6.9.8"
```
