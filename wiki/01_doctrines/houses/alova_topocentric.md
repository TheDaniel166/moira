# Alova-Topocentric

[Alova's 2010 paper](https://www.astrowisdom.net/articles/astrology-for-all-latitudes-new-topocentric-house-system.php) specifies a modified latitude for the Topocentric figure. Moira exposes it as `AT`.

Let `L` be the absolute geographic latitude and `ε` the chart obliquity. Up to `90° − 2ε` the construction uses the geographic latitude. Above that threshold the signed construction latitude has magnitude `90° − ε − (90° − L)²/(4ε)`. This is algebraically equivalent to Alova's formula and keeps the distance to the critical latitude explicit. The sign follows the hemisphere.

At that latitude use the rising ecliptic intersection as cusp 1. The 11th and 3rd cusps use one third of the tangent of the construction latitude, with sidereal-time offsets of −4 and +4 hours. The 12th and 2nd cusps use two thirds, at −2 and +2 hours. The arctangent gives the respective pole latitude. Cusp 10 is the hour-angle-zero meridian intersection. The opposite six cusps follow by antipodal symmetry. Optional spatial geometry uses the construction horizon and pole-height planes, with geographic latitude retained as observer metadata.

`cusps[0]` is the Alova first cusp and `effective_latitude` is its construction latitude. `asc` retains Moira's ordinary astronomical angle convention. When `astronomical_asc_defined` is false, the physical Ascendant is undefined and the numeric `asc` is the engine's conventional angle value. The model itself has a singular phase at each exact geographic pole. It can also produce crossed cusps despite a well-defined model Ascendant. At 80° N and ARMC 236°, for instance, cusp 12 passes cusp 1. Moira raises on a singular or unordered figure.

The source's 50° N example rounds to the printed values. The 70° N example gives cusp 2 as 19°31′ Virgo in print, while the formula gives about 19°27′40″ Virgo. The regression preserves both the printed table and the independently calculated result.
