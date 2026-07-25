# Moira 5.2.2 - Lunar Node Frame Corrections And Asteroid Family Catalog Refresh

**Release date:** 2026-07-25

**Public upgrade path:** 5.2.1 to 5.2.2

Moira 5.2.2 is an astronomy-correction and catalog-provenance patch release.
It repairs the coordinate-frame construction of the true lunar node, makes
the output equinox of analytical mean points explicit, and publishes the
current Proper25-backed asteroid-family catalog with complete overlap
visibility.

## True lunar node: one frame before intersection

The true lunar node is the intersection between the Moon's instantaneous
geocentric osculating orbital plane and the true ecliptic plane of date.
Earlier releases constructed the orbital-plane normal from ICRF/J2000 state
vectors but intersected it with an ecliptic pole expressed in the true frame
of date. Rotating the resulting intersection afterward could not repair that
mixed-frame construction.

`true_node(...)` now:

1. obtains simultaneous Moon and Earth position and velocity states;
2. constructs the instantaneous geocentric orbital normal as `r x v`;
3. applies ICRF frame bias, IAU 2006 precession, and IAU 2000A nutation to
   that normal;
4. intersects it with the true ecliptic pole in the same frame; and
5. projects the ascending direction into true ecliptic longitude of date.

At independently solved northbound zero-latitude crossings, the corrected
node longitude agrees with the Moon's geometric ecliptic longitude to better
than 0.001 arcsecond. The shipped Swiss Ephemeris fixture is retained only as
secondary corroboration, not as the governing derivation.

## Mean node and Mean Lilith: explicit equinox policy

`mean` describes the averaged lunar orbital solution; it does not by itself
select a mean coordinate frame. Moira now keeps those two policies separate:

```python
mean_node(jd_ut, nutation=True)
mean_lilith(jd_ut, nutation=True)
```

With the default `nutation=True`, both results are expressed in the true
ecliptic and equinox of date, matching Moira's default planetary, chart,
transit, synastry, batch, and draconic longitudes. Callers requiring the raw
mean-equinox product can request `nutation=False`.

The mean node now reuses Moira's admitted IERS 2003 lunar fundamental
argument. Its raw mean-frame result was validated against ERFA `faom03`, and
its true-frame result is derived by adding Moira's IAU 2000A nutation in
longitude. The default frame correction varies with epoch and can approach
about 19 arcseconds in magnitude.

Chart reduction responses now report `nutation` and
`frame="true_ecliptic_and_equinox_of_date"` for node products. Mean-node and
mean-Lilith stage sequences expose the analytical solution and nutation
conversion rather than hiding the frame policy.

## Proper25-backed asteroid family catalog

The bundled asteroid-family layer now uses:

- the 2026 Proper25 machine-readable distribution for main-belt families; and
- NASA PDS `ast.nesvorny.families` V2.0 only for the Hilda and Jupiter
  Trojan populations explicitly excluded by Proper25.

The normalized catalog contains:

- 342 admitted families;
- 200,726 unique numbered asteroids;
- 221,095 membership rows;
- 18,185 asteroids with multiple memberships; and
- up to four preserved memberships for one asteroid.

Nested and overlapping HCM classifications are no longer flattened into one
exclusive family. Compatibility surfaces retain a deterministic
display-primary family, while complete memberships remain available to
grouping, resonance, and REST consumers.

`moira/data/asteroid_families.metadata.json` records source URLs, archive and
tree hashes, exclusions, aliases, normalization semantics, counts, and the
final CSV hash. New build and refresh scripts reproduce the catalog and
annotate the unified asteroid catalog without altering BSP kernels.

## Validation evidence

The release exercises:

- IERS/ERFA mean-node authority comparisons at historical and modern epochs;
- exact mean-to-true equinox conversion through IAU 2000A nutation;
- first-principles true-node crossing and common-frame invariants;
- shipped Swiss mean/true node fixture cases under named tolerances;
- node-dependent chart, transit, synastry, batch, draconic, and REST paths;
- asteroid-family source counts, metadata integrity, aliases, overlaps,
  primary-display selection, bounded member transport, and annotation refresh;
  and
- release identity, public doctrine, documentation, packaging, and supported
  Python-version gates.

No NumPy, SciPy, Swiss Ephemeris, jplephem, or other runtime dependency is
introduced. Asteroid-family membership remains catalog evidence, not a claim
that every listed body is genetically related, and absent membership means
only that a body is absent from the admitted source catalogs.
