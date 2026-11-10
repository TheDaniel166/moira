# Asteroid catalog 2026.11.10.2 and Swiss Ephemeris comparison

This external catalog extends ten near-Earth asteroid trajectories from the
October release. The 11,223 identities span 449 Type-13 BSP shards. The rebuild
replaced seven shards, preserving the 165 other asteroid records within them
byte for byte. The other 442 BSPs retain their October hashes. The release
contains 944 files. The checksum ledger covers the manifest, shards, and
supporting records.

| Release file | SHA-256 |
| --- | --- |
| [Manifest](https://moira-astro.com/kernels/asteroids/2026.11.10.2/manifest.json) | `0021b645f3db6847e1b3d6a120a8eb4a39cf60fb8298e391aef676affdd2ab4b` |
| [Checksum ledger](https://moira-astro.com/kernels/asteroids/2026.11.10.2/SHA256SUMS) | `c3900823fd7d8e699735b6459f24d3f77630305535199c196232fbcacde42b77` |

The old Apophis record ended on March 31, 2022 TDB. The new JPL#220 record
covers 1600-01-01 through 2500-01-01 TDB. Adaptive sampling controlled
interpolation within the old source interval. Extending coverage required
qualifying a continuous source trajectory beyond that interval. The rebuild
used CSPICE evaluations of Horizons Type-21 trajectories and bounded Horizons
VECTORS replacements where the source required repair. The coverage decisions
and the bounds for each asteroid are in the release notes. [Build and coverage notes](https://moira-astro.com/kernels/asteroids/2026.11.10.2/README.md)

Across the ten rebuilt bodies, 2,519,096 interpolation holdouts and
12,721 apsidal events were checked. The largest apsidal discrepancies were
0.0875 seconds and 0.00520 km, within the existing gates of 8.64 seconds and
0.1495978707 km. Across 115 matched Horizons epochs, the worst geocentric
residuals were 0.386 mas geometric and 2.449 mas with reception light time.
These are residuals against nominal JPL trajectories.

## Comparison method

The November 10, 2026 run used Moira 6.13.1 with DE441 and catalog candidate
`2026.11.10.1`. Its BSP bytes and per-shard metadata are identical to those of
`2026.11.10.2`. Swiss Ephemeris 2.10.03 returned the `SWIEPH` flag with its
compressed DE441 planetary data and public small-body files. Both engines
were evaluated at matched epochs in geocentric ICRF for geometric and
reception-light-time vectors. Horizons supplied the nominal trajectories,
including the mission product `ORX_merged_DE424` for Bennu.

## Apophis on April 13, 2029

The nominal reference was Horizons solution JPL#220 at JD 2462240.407091969 TDB. The sweep used 259 points from six hours before to six hours after the JPL closest-approach epoch, at five-minute spacing and 15-second spacing within 15 minutes. Six additional samples extend out to 30 days on either side.

| Engine | Geometric geocentric range at JPL closest approach (km) | Light-time angular separation from JPL |
| --- | ---: | ---: |
| JPL Horizons | 38,011.344 | Reference |
| Moira | 38,011.344 | 0.397 mas |
| Swiss Ephemeris | 29,053.669 | 14.0810° |

At that instant the Swiss heliocentric asteroid vector differs by 12,108.9 km, while the heliocentric Earth vectors differ by 0.448 km. The heliocentric asteroid vector accounts for the dominant discrepancy in this comparison. The Swiss calculation's local minimum is 27,823.5 km about 22.94 minutes before the JPL epoch.

Astrodienst's hosted calculation agrees with the local Swiss apparent angles. [Hosted Swiss result](https://www.astro.com/cgi/swetest.cgi?b=j2462240.407091950066&p=s&n=1&s=1&e=-eswe&f=PLBRS&arg=-xs99942+-head)

The tested Swiss Apophis file was `se99942s.se1`, created 2026-11-01. The public mirror returned 404 for the separate long file and the alternate downloads timed out.

| Hours from JPL closest approach | Moira light-time error (arcseconds) | Swiss light-time error (arcseconds) |
| ---: | ---: | ---: |
| -720 | 1.5261e-06 | 0.00237961 |
| -168 | 5.4353e-06 | 1.21753 |
| -24 | 0.00011855 | 409.919 |
| -6 | 1.1671e-05 | 2240.88 |
| -1 | 0.0011416 | 23375.8 |
| +0 | 0.00039683 | 50691.4 |
| +1 | 0.0019664 | 34514.7 |
| +6 | 0.00044301 | 12625.2 |
| +24 | 6.3683e-05 | 1008.32 |
| +168 | 1.5134e-05 | 0.0213171 |
| +720 | 6.9231e-06 | 0.00728027 |

## Asteroid sample

200 matched samples across 19 targets, including all ten rebuilt asteroids. Moira has the smaller median light-time error on 17 targets in this sample. Phaethon and Ryugu favor Swiss on both median and maximum error. Swiss also leads on Bennu at the sampled September 1999 encounter.

| Body | Samples | Moira median (″) | Swiss median (″) | Moira max (″) | Swiss max (″) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Icarus | 12 | 6.3092e-07 | 0.0014674 | 1.615e-05 | 0.035057 |
| Apollo | 12 | 1.2483e-06 | 0.0017366 | 5.2199e-05 | 0.05108 |
| Oljato | 7 | 6.5249e-08 | 0.00019747 | 2.0063e-06 | 0.00044437 |
| Asclepius | 12 | 7.0419e-07 | 0.0016088 | 0.00038521 | 16.451 |
| Nereus | 12 | 1.1905e-06 | 0.0034404 | 9.94e-05 | 1.2625 |
| Itokawa | 12 | 4.9446e-07 | 0.0014169 | 0.0001677 | 0.64518 |
| YORP | 12 | 1.9375e-06 | 0.0023908 | 5.5528e-05 | 1.4799 |
| Hermes | 12 | 5.3436e-07 | 0.00086396 | 0.00016963 | 40.888 |
| Apophis | 12 | 2.3251e-06 | 0.0013869 | 0.00044301 | 50691 |
| Duende | 12 | 3.1999e-06 | 0.0025288 | 0.002449 | 15370 |
| Ceres | 8 | 0.0070549 | 0.30377 | 0.016325 | 0.59691 |
| Chiron | 8 | 9.1388e-05 | 0.25052 | 0.00094235 | 0.77857 |
| Phaethon | 12 | 0.02209 | 0.00048816 | 0.62741 | 0.032059 |
| Damocles | 9 | 6.9841e-05 | 0.00017619 | 0.0025503 | 0.0028574 |
| Sedna | 8 | 0.00019295 | 0.44679 | 0.00029135 | 2.5924 |
| Bennu | 12 | 3.4294e-07 | 0.00073057 | 32.748 | 0.019637 |
| Eris | 8 | 0.00042137 | 0.24152 | 0.00083065 | 2.9843 |
| Ryugu | 11 | 0.0052994 | 0.00066884 | 0.45872 | 0.0025973 |
| Ka'epaoka'awela | 9 | 0.00026966 | 0.26975 | 0.0013615 | 0.68935 |

## Comets available through Swiss

Of the 26 documented or previously listed pseudo-MPC IDs probed on Astrodienst's live service, Tsuchinshan–ATLAS (999054) returned a position. The service reported missing files for the other 25, including Halley, 67P, NEOWISE, Hale–Bopp, West and ʻOumuamua. These are availability results for the tested service and files.

Swiss's s999054.se1 was created in November 2024 and identifies DE431. For the comparison, Moira's comet reducer used a local Type-13 test kernel sampled from Horizons JPL#113. The 15 comparison epochs cover August 2024 through February 2025. The Greenwich observer check uses the working-tree comet topocentric reducer with refraction off.

| Comparison | Moira maximum (″) | Swiss maximum (″) |
| --- | ---: | ---: |
| Geocentric geometric ICRF | 3.7453e-08 | 10.989 |
| Geocentric light-time ICRF | 3.0057e-06 | 10.99 |
| Geocentric apparent ecliptic | 0.061156 | 11.037 |
| Greenwich apparent RA/Dec | 0.050956 | 11.039 |

## Dual asteroid and comet designations

Four of the nine dual-status objects listed by the Minor Planet Center have asteroid entries in both tested catalogs. The comparison used those asteroid numbers and eight matched epochs per object.

| Object | Moira maximum light-time error (″) | Swiss maximum light-time error (″) |
| --- | ---: | ---: |
| 95P Chiron | 0.00094235 | 0.77857 |
| 107P Wilson-Harrington | 0.014839 | 0.0020701 |
| 133P Elst-Pizarro | 0.013428 | 0.9117 |
| 174P Echeclus | 0.00044844 | 0.25534 |

## Evidence and installation

The JSON evidence records matched TT and TDB epochs, residuals for both
engines, the Swiss data file hashes and availability probes, and the
reference solutions. The comet rows record the test-kernel identity and the
hashes of the local reducer sources exercised by the run.
[Per-epoch comparison](../../tests/artifacts/oracle/asteroid_comet_swiss_comparison_2026-11-10.json)

The catalog release tool sealed the final files and verified their sizes
and hashes. To replay the full verification locally, run
`python -m moira.small_body_catalog_release verify <release-directory>`. The byte-exact manifest is archived
alongside prior releases.
[Archived November manifest](../../tests/fixtures/small_body_release_manifests/asteroids-2026.11.10.2.json)

To use this external catalog, download the manifest and shards together.
For full verification also download every support file listed in
`SHA256SUMS`, preserving subdirectories. Set
`MOIRA_SOVEREIGN_SMALL_BODY_MANIFEST` to the absolute path of the downloaded
manifest before starting Moira. The benchmark used DE441.

- [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html)
- [Astrodienst Swiss Ephemeris documentation and comet notes](https://www.astro.com/swisseph/swisseph.htm)
- [Astrodienst Swiss Ephemeris downloads](https://www.astro.com/swisseph/swedownload_e.htm)
- [Minor Planet Center dual-status list API](https://docs.minorplanetcenter.net/mpc-ops-docs/apis/list/)
