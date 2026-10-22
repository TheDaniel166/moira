# Geodetic Physical Horizon: Research Specification

Status: Research draft; no runtime or transport contract approved
Date: 2026-10-22
Owner: Moira engine
Scope: Possible future capability adjacent to `moira.geodetic`

## Purpose

Define the questions that must be settled before Moira adds an observer-site
physical-horizon calculation. This document does not change the existing
Geodetic astrology mapping, its spherical rising-ecliptic intersection, its
inputs, or its outputs.

The current `geodetic_asc` answers a specific algebraic question: which
ecliptic longitude is rising on the idealized local horizon for a supplied
geographic latitude and obliquity? It does not claim to model a survey-grade
observer's local vertical, a terrestrial reference frame at a coordinate
epoch, terrain, or atmospheric refraction.

## Terminology to preserve

- **Geodetic latitude** is defined relative to the normal of a reference
  ellipsoid. A datum/reference frame identifies the coordinate surface and
  realization; a height must state whether it is ellipsoidal or orthometric.
- **Astronomical latitude** follows the local gravity vertical (the plumb line).
  It can differ from geodetic latitude because of deflection of the vertical.
- **Geocentric latitude** is the direction from Earth's center to a surface
  point. It differs from geodetic latitude on an oblate ellipsoid.
- **Geometric horizon altitude** is an unrefracted topocentric direction
  relative to a declared local vertical.
- **Apparent horizon altitude** adds atmospheric refraction and may also need
  local terrain or an instrument/horizon convention.

The USNO altitude equation uses local hour angle, declination, and observer
latitude to compute altitude, but the implementation must state which
latitude/vertical convention its observer latitude represents. IERS topocentric
angle guidance also makes clear that celestial-to-local angles depend on the
terrestrial frame and Earth-orientation transformations. NOAA's datum guidance
supports treating frame/datum and coordinate epoch as explicit input context,
not labels from which the engine silently guesses a transformation.

## Input contract questions

Before implementation, product and astronomy owners must choose one supported
mode and define its input contract.

### Minimum geometric mode

- Observer geodetic latitude and longitude.
- Named datum/reference frame and coordinate epoch.
- Ellipsoidal height, with the frame/ellipsoid that defines it.
- Observation instant with separate UT1 and TT, plus the declared source and
  policy for Earth-orientation parameters and polar motion.
- A declared celestial input frame and apparent/astrometric state, with enough
  provenance to reproduce the local direction.
- A selected local-vertical policy: astronomical coordinates/observed
  vertical supplied by the caller, or a documented gravity model that derives
  it. Do not silently equate the ellipsoid normal with the gravity vertical.
- Geometric horizon only; no refraction or terrain correction in this mode.

### Optional apparent/terrain mode

This would be a separate mode, not a flag that quietly changes geometric
results. It must additionally specify:

- atmospheric pressure, temperature, wavelength, and refraction model/range;
- terrain or skyline profile, azimuth reference, elevation mask, and source;
- whether the result is an apparent topocentric direction or a corrected
  celestial coordinate;
- behavior when environmental or horizon data is absent, stale, or invalid.

## Result and provenance requirements

Any eventual result must identify the selected mode and retain enough
provenance to reproduce it:

- normalized input location plus datum/frame, coordinate epoch, height kind,
  and location source;
- UT1, TT, Earth-orientation input identity/version, and celestial frame;
- local-vertical realization or model identity;
- geometric/apparent mode and refraction/terrain inputs where applicable;
- returned horizon altitude, azimuth, and the relevant ecliptic intersection(s),
  with units and normalization rules;
- warnings for extrapolation or low-quality/missing source data.

The result should be immutable and typed. A mapping or bare numeric angle is
not sufficient provenance. The current `GeodeticChart` result and all existing
functions keep their current meanings.

## Calculation and validation gates

1. Select whether the new product is an observed local-horizon tool, a
   reference-frame topocentric calculation, or both. They are not interchangeable.
2. Choose the authoritative Earth-orientation, ellipsoid, gravity/local-vertical,
   refraction, and terrain data policies. Define offline behavior and refresh
   provenance; no hidden network retrieval is permitted.
3. Derive the coordinate transformations and equations from primary authority
   before implementation. Keep geodetic, astronomical, and geocentric latitude
   conversions explicit and test each direction separately.
4. Build independent reference cases for equator, both hemispheres, polar
   limits, date-line wrapping, nonzero height, nonzero vertical deflection,
   Earth-orientation variation, and refracted versus geometric horizons.
5. Verify frame, epoch, and units with round-trip/metamorphic invariants and
   published reference examples. Quantify the model/data contribution to each
   tolerance rather than asserting a universal precision.
6. Only after these gates, define a separate Python API and decide whether a
   service contract is warranted. No REST route is implied by this draft.

## Current module boundary

`moira.geodetic` continues to accept caller-supplied latitude without implicit
conversion. Its new typed location metadata records latitude kind and optional
datum/frame/epoch/height/source, but does not apply any of them. A typed
geocentric-latitude input is refused until a named conversion mode exists.

Astrocartography currently owns a different, explicit WGS-84 ellipsoid
conversion: it converts geodetic site latitude to geocentric latitude for its
horizon-sampling equation, and maps a fixed body's geocentric declination to a
matching WGS-84 geodetic zenith latitude. That behavior is confined to
`moira.astrocartography`; it is not a hidden shared Geodetic policy.

## Primary references

- U.S. Naval Observatory, [Computing Altitude and Azimuth from Local Hour
  Angle](https://aa.usno.navy.mil/faq/alt_az).
- U.S. Naval Observatory, [Astronomical Applications Glossary](https://aa.usno.navy.mil/faq/asa_glossary).
- U.S. Naval Observatory, [Explanatory Supplement / Kaplan report](https://aa.usno.navy.mil/downloads/reports/Kaplan2005b.pdf), discussion of
  astronomical versus geodetic latitude and vertical deflection.
- International Earth Rotation and Reference Systems Service, [Topocentric
  angles FAQ](https://www.iers.org/iers/en/service/faqs/theicrs/topocentriacanglesxyt).
- NOAA National Geodetic Survey, [Datums and reference frames](https://nweb.ngs.noaa.gov/datums/).
