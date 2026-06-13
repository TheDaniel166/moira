# Planetary And Small-Body Nodes Backend Standard

Version: 0.1
Date: 2026-06-13
Status: admitted backend standard for Phase 11 REST transport

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

- derive the instantaneous heliocentric orbital plane from reader state vectors
- use angular momentum and eccentricity-vector geometry
- require a loaded reader that covers the requested body
- generalize to classical planets, Pluto, and small bodies only when the
  active reader has the needed state-vector coverage
- reject Sun and Moon as heliocentric node targets for this frame

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
- stage sequence

REST transport must not:

- collapse mean and osculating nodes into one generic result
- imply small-body availability from catalog identity alone
- expose chart-backed lunar-node doctrine through this family
- treat Sun or Moon as valid heliocentric-node targets for geometric nodes
- claim kernel-backed truth for mean-element results
- claim mean-element validity beyond the engine's documented envelope

## Validation Requirements

Transport admission must verify:

- catalog route declares distinct mean and geometric methods
- mean single route returns node and provenance
- mean bulk route returns the admitted mean planetary set
- mean routes reject non-finite JDs
- mean routes reject empty and unknown planet names
- mean bulk routes reject empty and oversized lists
- geometric route passes the server engine reader into the computation
- geometric route records osculating state-vector provenance
- geometric route rejects non-finite `jd_ut`
- geometric route rejects empty body names
- geometric route rejects Sun and Moon as non-meaningful heliocentric-node
  targets

## Non-Goals

This standard does not admit:

- lunar true-node or mean-node REST routes
- chart-backed node profiles
- natal, transit, or synastry nodal interpretation
- nodal aspect networks
- catalog-wide small-body node sweeps
- rendered node maps
- asteroid/comet position route changes
- small-body kernel manifest management
