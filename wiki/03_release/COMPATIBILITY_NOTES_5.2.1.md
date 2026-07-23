# Compatibility Notes - Moira 5.2.1

Date: 2026-07-23

Moira 5.2.1 is backward compatible with 5.2.0. Existing eclipse and cusp-only
house calls retain their established signatures and result semantics. Spatial
house geometry is additive and opt-in.

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

## Upgrade action

Upgrade to `moira-astro==5.2.1` and restart every process that imports Moira.
Applications adopting spatial house geometry should request it only on
surfaces that render or inspect the additional objects and should preserve the
engine's explicit availability state.
