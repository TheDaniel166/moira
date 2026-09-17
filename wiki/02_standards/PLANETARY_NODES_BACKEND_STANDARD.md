# Planetary And Small-Body Nodes Backend Standard

Version: 0.2
Date: 2026-09-16
Status: admitted backend standard through Orbital Core Stage 3

## Scope

This standard governs Moira's orbital node and apsides surface:

- `moira.planetary_nodes`

It covers:

- kernel-free mean planetary orbital nodes and apsides
- reader-backed osculating heliocentric nodes and apsides
- the `OrbitalNode` result vessel

It does not govern lunar true/mean node computation, chart node placement,
nodal aspects, nodal interpretation, or chart-backed node profiles.

## Authority Layers

Moira exposes two distinct node products.

Mean planetary nodes:

- use the Meeus / Simon et al. mean orbital element table in
  `moira.planetary_nodes`
- are kernel-free
- are documented by the engine as approximately valid from 2000 BCE to 3000 CE
- return slow mean orbital elements for Mercury, Venus, Earth, Mars, Jupiter,
  Saturn, Uranus, and Neptune

Geometric osculating nodes:

- are an exact adapter over `osculating_elements` with `center=SUN` and
  `frame=TRUE_ECLIPTIC_OF_DATE`
- derive the instantaneous heliocentric orbital plane from receipted reader
  state vectors using the strict orbital core's angular-momentum and
  eccentricity-vector geometry
- bind public UT1 to TT and exact TDB state evaluation once
- use the pinned JPL Horizons gravity policy and the core's singularity rules
- require a receiptable reader route covering the requested body and exact TDB
  epoch
- generalize to classical planets, Pluto, and loaded sovereign asteroid and
  comet catalogs
- are admitted only for JD(TT) `2415020.0` through `2488070.0`; requests
  outside that true-date frame interval fail explicitly
- reject Sun and Moon as heliocentric node targets for this frame

`OrbitalNode.perihelion` is the ecliptic longitude of the projected pericenter
vector. It is not the inclined-orbit dogleg `Omega + omega`.

## Governing Objects

The admitted backend object is:

- `OrbitalNode`

Required fields:

- `planet`
- `ascending_node`
- `descending_node`
- `perihelion`
- `aphelion`
- `inclination`
- `eccentricity`
- `semi_major_axis`

The admitted computations are:

- `planetary_node(planet, jd)`
- `all_planetary_nodes(jd)`
- `geometric_node(body, jd_ut, reader=None)`

## Required Transport Invariants

REST transport must preserve:

- requested body identity
- returned body identity
- computation method: `mean_elements` or `geometric_osculating`
- JD and JD scale semantics
- coordinate frame
- coordinate basis
- kernel requirement truth
- kernel source truth
- ascending and descending node longitudes
- perihelion and aphelion longitudes
- inclination, eccentricity, and semi-major axis
- method-specific validity note
- canonical body name, NAIF ID, and body kind for geometric results
- UT1, TT, and TDB epoch values and source-owned time-conversion receipt
- selected Horizons gravity rule and GM receipt
- true-date frame construction and admitted interval
- path-free SPK route identities, release identities, hashes, and exact
  coverage intervals
- singularity and undefined-element policies
- stage sequence

REST transport must not:

- collapse mean and osculating nodes into one generic result
- imply small-body availability from catalog identity alone
- expose chart-backed lunar-node doctrine through this family
- treat Sun or Moon as valid heliocentric-node targets for geometric nodes
- claim kernel-backed truth for mean-element results
- claim mean-element validity beyond the engine's documented envelope
- imply that an installed catalog has frozen-Horizons numerical admission when
  its manifest contains no reviewed Stage 3 admission bound to that fixture

## Validation Requirements

Transport admission must verify:

- catalog route declares distinct mean and geometric methods
- mean single route returns node and provenance
- mean bulk route returns the admitted mean planetary set
- mean routes reject non-finite JDs
- mean routes reject empty and unknown planet names
- mean bulk routes reject empty and oversized lists
- geometric route passes the server engine reader into the computation
- geometric route records strict-core time, gravity, frame, state-source,
  singularity, and undefined-element provenance without exposing local paths
- geometric route rejects non-finite `jd_ut`
- geometric route rejects Boolean epochs before transport coercion
- geometric route rejects empty body names
- geometric route rejects Sun and Moon as non-meaningful heliocentric-node
  targets
- all nine admitted planet targets map exactly to one Sun/true-date core result
- loaded representative asteroid/comet targets map exactly to the same core
- requests outside the admitted true-date interval retain the typed frame error
- every installed full-catalog member receives an inventory-wide finite-node and
  source-receipt check; a missing sovereign release is recorded as `NOT RUN`
- frozen Horizons catalog comparisons run only for releases whose manifests
  carry the reviewed fixture hash and acceptance-gate admission

## Non-Goals

This standard does not admit:

- lunar true-node or mean-node REST routes
- chart-backed node profiles
- natal, transit, or synastry nodal interpretation
- nodal aspect networks
- a catalog-wide node REST endpoint
- rendered node maps
- asteroid/comet position route changes
- small-body kernel manifest management
