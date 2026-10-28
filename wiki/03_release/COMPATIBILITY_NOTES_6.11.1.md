# Compatibility Notes - Moira 6.11.1

Python 3.10 through 3.14, dependencies, native bindings and existing REST
request/response shapes remain unchanged from 6.11.0.

ASC/DSC coordinates and their sampled latitude domains intentionally change
where the old horizon geometry was wrong. Lunar corrections can restore
previously omitted samples as well as remove impossible samples. MC/IC
longitude conventions and the configured latitude grid are unchanged.

Refraction is still opt-in at the engine boundary. The website's existing
refraction-on request retains its declared -0.5667 degree geometric centre
horizon. The unrefracted `90 - abs(declination)` limit must not be applied
unchanged to that refracted product or to a finite-distance lunar direction.

The existing sampling product remains a list of vertices. This patch does
not introduce curve-cap connectors, a different map projection, or an exact
endpoint materialization contract.
