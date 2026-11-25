# Compatibility Notes - Moira 6.15.0

Moira supports Python 3.10 through 3.15 in this release.

## Type 13 files and asteroid installation

Install Moira 6.15.0 before activating the external asteroid catalog
`2026.11.24.1`. The catalog contains all 11,250 admitted bodies, including the
provisional JPL SPK IDs used for 27 trans-Neptunian objects. The bundled
manifest and identity receipt name the exact separately installed artifact.

The Type 13 writer now stores the number of window states minus one, as
specified by NAIF, and accepts windows up to 14 states, or degree 27. The
reader uses the SPK epochs in TDB seconds with the NAIF window-selection
rules. Known historical Moira file identifiers select the original decoding.
For an unmarked file created by the historical writer, pass
`legacy_type13=True` to `SmallBodyKernel`. Pass `legacy_type13=False` to force
NAIF decoding for a standard file with an ambiguous identifier.

## Public results

- Recalculate affected Pullen Sinusoidal Delta results for geometries near
  the narrow-quadrant collapse. The corrected law keeps cusps continuous
  through the 30° threshold.
- Eclipse next and previous results use their represented event maximum.
  Location-specific searches use the local maximum. Callers can use the
  dedicated availability and bounded-evidence routes to inspect geometric
  limitations and the separately defined geographic width.
- Asteroid family-resonance responses can return `null` for `mpc_number`
  when the target has an explicit JPL SPK ID and provisional designation.
  Use the returned NAIF ID or canonical designation for those targets.
- Geocentric planetary longitude-rate queries carry an explicit coverage
  flag on `OutOfRangeError` for a requested sample outside kernel coverage.
- The Galactic ayanamsa presets and planetary moon snapshots are additive.
  Planetary moon snapshots require the documented, verified satellite
  kernels in addition to DE441.
