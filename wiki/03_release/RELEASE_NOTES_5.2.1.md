# Moira 5.2.1 - Spatial House Boundary Geometry

**Release date:** 2026-07-23

**Public upgrade path:** 5.2.0 to 5.2.1

Moira 5.2.1 preserves the actual spatial objects behind admitted house
boundaries. It is an additive patch release over the 5.2.0 Eclipse release and
does not alter existing cusp-only calls unless the new geometry is requested.

## Frame-explicit house boundaries

`calculate_houses(...)`, `houses_from_armc(...)`, and `Moira.houses(...)` now
accept `include_boundary_geometry=True`. The returned `HouseCusps` then carries
an immutable `HouseBoundaryGeometrySet` for the effective house system:

- Campanus and Azimuthal preserve their local-frame great-circle planes;
- Regiomontanus, Topocentric, Koch, and Alcabitius preserve their admitted
  pole-height or equatorial-sector planes; and
- Placidus preserves four cardinal great-circle planes plus eight sampled
  semi-arc event curves, each including its exact ecliptic cusp incidence.

The geometry is expressed in the declared
`true_equator_and_equinox_of_date` frame. A sidereal offset changes the zodiac
labels and `zodiac_offset_deg`; it does not rotate the physical directions or
plane normals.

Systems whose current public product admits only ecliptic cusp intersections
return `availability="cusp_intersections_only"` with an explicit reason and no
fabricated 3D walls. Polar and unknown-system fallback follow the effective
system, never the originally requested label.

The house REST request accepts the same opt-in flag and serializes the geometry
without reconstructing it in the transport layer.

## Validation evidence

The release exercises frame-explicit great-circle and event-curve house
boundaries, southern and high-latitude cases, effective-system fallback,
sidereal label separation, exact cusp incidences, public exports, and REST
serialization.

No NumPy, SciPy, Swiss Ephemeris, or jplephem runtime dependency is introduced.
