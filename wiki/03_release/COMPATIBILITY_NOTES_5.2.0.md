# Compatibility Notes - Moira 5.2.0

Date: 2026-07-23

Moira 5.2.0 is backward compatible with 5.1.2. Existing eclipse search, local
circumstances, path, footprint, visibility-map, Besselian, and cusp-only house
calls retain their established result semantics. The new global and
cartography methods, spatial house-boundary opt-in, and REST additions are
additive.

## New public products

Python consumers may opt into:

- `EclipseCalculator.solar_global_circumstances(...)`;
- `EclipseCalculator.solar_eclipse_cartography(...)`;
- `EclipseCalculator.lunar_global_circumstances(...)`; and
- the corresponding `Moira` facade methods and package-root result exports.

REST consumers may opt into:

- `/v1/eclipses/solar/global-circumstances`;
- `/v1/eclipses/solar/cartography`; and
- `/v1/eclipses/lunar/global-circumstances`.

No existing caller is redirected automatically to these more expensive
products.

## Optional spatial house geometry

Python consumers may pass `include_boundary_geometry=True` to
`calculate_houses(...)`, `houses_from_armc(...)`, or `Moira.houses(...)`. REST
consumers may pass the same field to `POST /v1/houses`.

The default remains `False`. Existing callers therefore receive
`boundary_geometry=None` and incur no event-curve sampling or enlarged
transport payload.

When enabled:

- `boundary_geometry.effective_system` follows the effective system after any
  fallback;
- `availability="complete"` means exactly twelve ordered spatial boundaries
  are present;
- `availability="cusp_intersections_only"` means no off-ecliptic spatial
  object is admitted and `reason` explains the limitation; and
- `zodiac_offset_deg` relabels cusp longitudes but does not rotate the physical
  equatorial directions or plane normals.

Consumers must branch on `availability`. They must not infer or synthesize a
full 3D boundary from the requested system name when the engine reports cusp
intersections only.

## Corrected output

The existing solar-footprint result changes for the 2032 annular event, the
2049 hybrid event, and numerically equivalent horizon junctions: the exact
sunrise/sunset incidence is retained and a bounded numerical micro-branch is
no longer allowed to displace it. Applications that cached a failure or
malformed footprint for such events should regenerate that record.

## Computational cost

Global solar circumstances include event search, footprint construction,
U-contact solving, conjunction solving, and a separate greatest-duration
optimization. Adaptive cartography additionally solves observer-visible
maxima at mesh vertices and tested edge midpoints. These are intentionally
more expensive than ordinary event search.

Interactive and web consumers should use background work, bounded refinement,
request deduplication, and result caching. `converged=False` with a positive
`unresolved_edge_count` is a valid explicit result when the requested
`mesh_depth` budget is exhausted; callers must not relabel it as converged.

## Preserved boundaries

- The base engine has no Python runtime dependencies.
- NumPy is not required by global circumstances or cartography.
- Python owns policy, topology, ambiguity handling, result semantics, and
  fallback.
- The native extension remains the required bounded computational substrate
  for admitted native paths and SPK access.
- Duration contours, terrain, refraction, weather, and lunar-limb topography
  remain unavailable rather than inferred.
- External NASA and EclipseWise fixtures are validation evidence only and are
  never consulted by runtime computation.

## Upgrade action

Upgrade to `moira-astro==5.2.0` and restart every process that imports Moira.
Applications adopting the new cartography route should add background/caching
handling before exposing high refinement budgets to interactive requests.
Applications adopting spatial house geometry should request it only on
surfaces that render or inspect the additional objects and should preserve the
engine's explicit availability state.
