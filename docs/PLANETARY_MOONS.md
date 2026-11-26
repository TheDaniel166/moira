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

## REST API

Set `MOIRA_SERVER_PLANETARY_MOONS_MANIFEST` to the prepared `manifest.json` before starting Moira Server. The satellite extracts stay beside the manifest. The routes use `MOIRA_SERVER_KERNEL_PATH` when set and otherwise look for `de441.bsp` in Moira’s standard kernel directories.

| Method and route | Result |
|---|---|
| `POST /v1/planetary-moons/snapshot` | TT and TDB epochs, moon states and phenomena, and source receipts. |
| `GET /v1/planetary-moons/coverage` | Installed systems and their closed geometric state intervals, expressed as TDB Julian days. |
| `POST /v1/planetary-moons/events` | Bounded finite-disk windows or the first new event, with TT contacts, TDB epochs, and source receipts. |

For example, request Jupiter at J2000 TT with this JSON body:

```json
{"jd_tt": 2451545.0, "planet": "Jupiter"}
```

Use `"Saturn"` for Saturn’s eight moons. Omit `planet` for all twelve, which requires both installed systems. The state, phase, and event fields have the same meanings as the Python snapshot. `earth_view.event` is `null` when there is no active transit or occultation. `earth_view.side` reports the moon’s range ordering relative to the planet.

Coverage returns a `systems` array with one entry per installed planet. Each entry contains `planet` and `intervals_tdb`, an array of objects with `start_jd_tdb` and `end_jd_tdb`. Keep separate intervals if there are gaps. A snapshot near the start of an interval can still fail when a required retarded epoch falls before coverage begins.

The routes return the standard Moira error envelope. Invalid request bodies return HTTP 422 with `validation_error`. Unavailable reception or light-time coverage returns HTTP 422 with `planetary_moons_epoch_out_of_coverage`. Missing configuration returns HTTP 503 with `server_not_configured`. Unavailable or invalid kernels and missing requested systems return HTTP 503 with `kernel_not_ready`.

### Search finite-disk events

```json
{"jd_start_tt": 2461369.0, "jd_end_tt": 2461371.0, "planet": "Jupiter",
 "moon_ids": [503], "kinds": ["transit"], "mode": "next"}
```

Use `mode: "window"` to receive the selected event windows in the supplied interval.
`next` returns at most one event that starts in the interval. Windows already in progress at the start are marked `start_clipped` in window mode. The start of the search owns ingress and grazes at its boundary. The end can close an active window or supply its exact egress. A contact at either boundary may require a geometry evaluation just outside the window to determine its direction.

The search limits the window to 90 TT days and applies a shared evaluation budget to the 30-minute TDB scan, extremum checks, and contact refinement. Every result names its `status` and `resolution`. An empty `complete` result refers to the admitted sampled and refined search. An incomplete next search returns no event and includes unresolved intervals. `result_limit` indicates that the window-mode result was truncated after chronological sorting.

Contacts use an Earth-reception TT/TDB epoch, so the viewer can pass a contact's `jd_tt` directly to the snapshot route. The observer offset is zero for a transit or occultation. For an eclipse it is the moon's Earth-directed emission offset. Internal contacts describe containment and eclipse totality. Contact times use nominal model limbs, and the search resolution is numerical.

## Focused verification

The unit tests exercise analytic sphere and ellipsoid contacts, same-sign grazes and short windows, east/north signs, manifest failures, and retarded state selection. The integration tests use local CSPICE with matched DE441, satellite SPKs, and PCK00011. They compare the original segment states and coverage and the boundaries of 36 finite-disk transit, occultation, and eclipse windows with a one-second contact tolerance.

Set `MOIRA_TEST_PLANETARY_MOONS_MANIFEST`, `MOIRA_TEST_DE441_CSPICE`, `MOIRA_TEST_PLANETARY_MOONS_PCK`, and `MOIRA_TEST_PLANETARY_MOONS_JPL` to the manifest, CSPICE-readable DE441 file, PCK00011, and directory holding the original satellite SPKs. Use the official `de441_part-2.bsp` for the CSPICE comparison and set `MOIRA_TEST_DE441_CSPICE_EARLY` to `de441_part-1.bsp` for the earlier epochs. Moira’s combined DE441 file supplies the engine query through its usual local discovery.

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_planetary_moons.py tests\unit\test_planetary_moon_event_search.py tests\integration\test_planetary_moons_cspice.py tests\server\test_server_planetary_moons_routes.py -m "not external_network" -q
```

The reference verifies the same SPK and nominal shape model and does not estimate observational timing uncertainty near a graze. Hubble’s 2009 Saturn sequence supplies an observed multi-moon case. [Hubble Saturn transits](https://science.nasa.gov/missions/hubble/quadruple-saturn-moon-transit-snapped-by-hubble/) · [NAIF finite-disk classifications](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/occult_c.html)
