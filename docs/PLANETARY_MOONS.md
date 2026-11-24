# Planetary moons

`moira.planetary_moons` computes a chart-time snapshot for Io, Europa, Ganymede, Callisto, Mimas, Enceladus, Tethys, Dione, Rhea, Titan, Hyperion, and Iapetus. The entry point is an explicitly opened, reusable context.

## Prepare the ephemeris data

Download the two pinned JPL files and prepare a local asset directory with the project Python. CSPICE is used by the preparation tool. [JUP365](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup365.bsp) · [SAT441](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat441.bsp)

```powershell
.\.venv\Scripts\python.exe scripts\prepare_planetary_moons.py --jup365 C:\data\jup365.bsp --sat441 C:\data\sat441.bsp --output C:\data\moira-moons-v1
```

The tool checks the input hashes, retains the original local SPK segments for the twelve satellites and two physical planet centers, and writes an integrity and coverage manifest. It creates the output directory after both extracts and the manifest have been written. The astronomy runtime uses Moira’s existing native SPK reader and an explicitly supplied DE441 for the solar-system trajectories. [NAIF SPK subset operation](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spksub_c.html)

Both primary extracts cover a joint state range of about 1750–2200. Use `coverage_tdb()` for the actual closed intervals of the installed data. A reception-time snapshot also needs each retarded state to lie inside its supplying segment. An unavailable route raises `OutOfRangeError`. A missing manifest, file, or requested system raises `FileNotFoundError`, and invalid inputs or receipts raise `ValueError`.

## Query at a chart time

```python
from moira.planetary_moons import PlanetaryMoons

with PlanetaryMoons.open(
    de441_path=r"C:\data\de441.bsp",
    manifest_path=r"C:\data\moira-moons-v1\manifest.json",
) as moons:
    snapshot = moons.at(2451545.0)  # Julian day in TT
    for moon in snapshot.moons:
        print(
            moon.planet,
            moon.name,
            moon.earth_view.side,
            f"{moon.phase.illuminated_fraction:.1%}",
            moon.earth_view.event,
            moon.eclipse,
        )
```

Pass `planet="Jupiter"` or `planet="Saturn"` to request one system. A directory prepared with one source supports that explicit system query. A complete snapshot requires both sources. The returned snapshot includes kernel hashes and the TT and TDB epochs.

| Field | Meaning |
|---|---|
| `position_km` and `velocity_km_per_day` | Simultaneous geometric ICRF state relative to Jupiter’s or Saturn’s physical center. |
| `earth_view` | Earth-center reception view, with positive east/north sky offsets and a positive range offset for the far side. Planet and moon light times are solved independently. |
| `phase` | Sun–moon–parent angle and nominal spherical illuminated fraction at parent-center reception. Full-like phase occurs near 0° and new-like phase near 180°. |
| `earth_view.event` and `overlap` | Overlapping disks are a transit when the moon is nearer and an occultation when it is farther. The overlap status distinguishes clear, contact, partial overlap, and a moon disk fully within the planet’s projected silhouette. |
| `eclipse` | Coverage of the finite solar disk seen from the moon center at the epoch of the light arriving at Earth. Clear, contact, partial, and total coverage are distinct. Geometric phase and eclipse can coexist. |

Emission offsets use TDB days relative to the snapshot epoch. The model uses converged one-way Newtonian light time, the NAIF PCK00011 oblate reference limbs for the planets, and JPL mean-radius spherical limbs for the moons. Eclipse geometry samples the moon’s center. The result describes parent–moon events with their nominal limbs. Ring opacity, mutual events, local visibility, and shadow footprints have separate geometry. [NAIF light-time conventions](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/abcorr.html) · [NAIF reference ellipsoids](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/pck.html) · [JPL satellite radii](https://ssd.jpl.nasa.gov/sats/phys_par/)

## Focused verification

The unit tests exercise analytic sphere and ellipsoid contacts, east/north signs, manifest failures, and retarded state selection. The integration tests additionally use local CSPICE with a matched DE441 source, the two output SPKs, and PCK00011. They cover state and phase, finite-disk events on both sides of ingress and egress, and the original SPK coverage and state of the extracted segments.

Set `MOIRA_TEST_PLANETARY_MOONS_MANIFEST`, `MOIRA_TEST_DE441_CSPICE`, `MOIRA_TEST_PLANETARY_MOONS_PCK`, and `MOIRA_TEST_PLANETARY_MOONS_JPL` to the manifest, CSPICE-readable DE441 file, PCK00011, and directory holding the original satellite SPKs. Use the official `de441_part-2.bsp` for the CSPICE comparison and set `MOIRA_TEST_DE441_CSPICE_EARLY` to `de441_part-1.bsp` for the earlier epochs. Moira’s combined DE441 file supplies the engine query through its usual local discovery.

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_planetary_moons.py tests\integration\test_planetary_moons_cspice.py -m "not external_network" -q
```

The reference verifies the same SPK and nominal shape model and does not estimate observational timing uncertainty near a graze. Hubble’s 2009 Saturn sequence supplies an observed multi-moon case. [Hubble Saturn transits](https://science.nasa.gov/missions/hubble/quadruple-saturn-moon-transit-snapped-by-hubble/) · [NAIF finite-disk classifications](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/occult_c.html)
