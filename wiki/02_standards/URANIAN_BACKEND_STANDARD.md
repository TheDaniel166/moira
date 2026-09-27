# Uranian Backend Standard

**Subsystem:** `moira/uranian.py`
**Computational Domain:** Uranian / Hamburg School hypothetical-body positions
**Status:** Source-orbit and apparent-place standard

## 1. Scope

This standard governs `UranianBody`, `UranianPosition`, `uranian_at()`,
`all_uranian_at()`, and `list_uranian()`.

The subsystem computes conventional positions for the Hamburg eight plus
Transpluto. These are hypothetical orbits used by an astrological school, not
physical-body states, discovered trans-Neptunian objects, or JPL targets.

## 2. Source Families

The Hamburg eight use James Neely's revised orbital elements published as
"Orbital Elements for the Transneptunians" in *Matrix Journal* VII (1980).
Transpluto is separate and uses the Sevin/Strubell element lineage published
in *Die Sterne* 3/1952. They must not be merged into one provenance claim.

Source receipts:

- [Alexandria iBase archive record for Matrix Magazine VII](https://alexandriaibase.org/matrix-magazine-issue-vii-1980/)
- [Swiss Ephemeris programming guide element-file specification](https://www.astro.com/ftp/swisseph/doc/swephprg.2.10.htm)
- [Swiss Ephemeris discussion of hypothetical bodies and Transpluto](https://www.astro.com/ftp/swisseph/doc/swisseph.pdf)

The current conventional element values and operational naming are
cross-checked against Astrodienst's official Swiss Ephemeris documentation and
`swetest` service. Swiss Ephemeris is validation-only: it is neither Moira's
runtime substrate nor the primary proof of Keplerian dynamics.

The Kronos semimajor axis is `64.81690 AU`, matching the established
`seorbel`/live-`swetest` output convention. The current Swiss programming-guide
table prints `64.81960 AU`; Moira does not silently mix those variants. The
selected operational convention is pinned by the frozen position matrix, and
any switch is a reviewed model change rather than a rounding substitution.

## 3. Governing Computation

For each source element set Moira:

1. converts the requested finite `jd_ut` (UT1) to the TT coordinate consumed
   by the bound planetary kernel;
2. advances mean anomaly with Gaussian two-body mean motion;
3. solves Kepler's equation and materializes the heliocentric orbital vector
   in the source mean ecliptic/equinox;
4. rotates that vector into ICRF;
5. adds the kernel-derived Sun barycentric state;
6. reduces the result to apparent geocentric true-ecliptic-of-date longitude,
   latitude, and distance using the engine's light-time, deflection,
   aberration, precession, and nutation pipeline; and
7. differentiates the complete returned longitude product symmetrically to
   obtain signed degrees per day and the retrograde state.

The DE kernel supplies only real Earth/Sun observer geometry. It does not
contain, discover, or physically validate the hypothetical body.

## 4. Admitted Names and Result

`UranianBody.HAMBURG` contains exactly:

`Cupido`, `Hades`, `Zeus`, `Kronos`, `Apollon`, `Admetos`, `Vulkanus`, and
`Poseidon`.

`UranianBody.ALL` appends `Transpluto`, for nine public names in total.

`UranianPosition` is immutable and preserves:

- `name`
- `longitude` and `latitude` in degrees
- geocentric `distance_au`
- signed longitude `speed` in degrees per day
- `retrograde`
- derived `sign`, `sign_symbol`, and `sign_degree`
- `body_group` and `source_family`
- `model = "fixed_keplerian_orbit_apparent_geocentric"`
- `frame = "apparent_geocentric_true_ecliptic_of_date"`

## 5. Public Behavior

`uranian_at(name, jd_ut, reader=None)` returns one position.
`all_uranian_at(jd_ut, reader=None)` returns all nine in canonical order.
`list_uranian()` is kernel-free and returns only the canonical names.

Names are case-sensitive. Unknown names raise `KeyError`; non-finite dates
raise `ValueError`. Position calls require an explicit or active planetary
reader. Missing resources fail with the standard `MissingKernelError` rather
than falling back to a linear approximation.

## 6. REST Contract

The `/v1/uranian/position` and `/v1/uranian/bulk` routes must use the
startup-bound engine reader. Responses expose the complete position vessel and
truthful provenance. `spk_kernel_used` is `true` for computed positions and
`false` for the kernel-free catalog call.

Transport must retain these identifiers:

- `body_kind = "hypothetical_body"`
- `school = "Hamburg_Uranian_plus_Transpluto"`
- `model = "fixed_keplerian_orbit_apparent_geocentric"`
- `frame = "apparent_geocentric_true_ecliptic_of_date"`
- `epoch = "per_body_source_epoch"`
- `physical_ephemeris = "DE_kernel_for_Earth_and_Sun_observer_geometry_only"`

It must never imply that the DE kernel provides hypothetical-body states.

## 7. Validation

`tests/unit/test_uranian.py` owns element-family, period-scale, Kepler-equation,
immutability, motion-sign, and public-path invariants.

`tests/artifacts/oracle/uranian_reference_matrix.json` freezes five official
Astrodienst `swetest` snapshots from 1900 through 2026. The corresponding
oracle test covers all nine bodies and longitude, latitude, distance, speed,
and retrograde state. This is explicitly cross-engine corroboration.

The matrix tolerances are product-owned and declared in the artifact:

- longitude: `1e-5°`
- latitude: `1e-6°`
- distance: `2e-7 AU`
- longitude speed: `1e-6°/day`

## 8. Non-Goals and Change Policy

This surface does not provide topocentric positions, sidereal reduction,
midpoint trees, dial interpretation, cosmobiology networks, or physical TNO
ephemerides.

Changes to names, elements, source epochs/equinoxes, orbit propagation,
apparent-place stages, derivative convention, or provenance are
doctrine-sensitive. They require source review and renewal of both invariant
and external-comparator evidence.
