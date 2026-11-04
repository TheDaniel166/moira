# Savard-A

[John J. G. Savard's *Astrological House Systems*, section “Albategnus”](https://web.archive.org/web/20120527104330id_/http://www.quadibloc.com/other/as01.htm) supplies the declination division and tentatively describes great circles through the north and south points of the horizon. Moira adopts that projection as a reconstruction under the name Savard-A (`SA`). The section does not establish medieval authorship or supply a numerical cusp table.

## Construction

The governing objects are twelve oriented half great circles through the north–south horizon axis. The prime vertical runs from east through nadir, west and zenith, in house order. Divide the signed declination change of each quadrant into thirds. If `a` is the prime-vertical angle from east toward nadir, then the direction `p = E cos(a) − Z sin(a)` has declination `−asin(sin(φ) sin(a))`, where `φ` is geographic latitude. Consequently the first two cuts satisfy `sin(a) = sin(jφ/3)/sin(φ)` for `j = 1, 2`. Reflect the cuts about the nadir and use antipodes for the second semicircle.

The plane for a cut contains `p` and the north horizon direction `N`. Let `K` be the ecliptic pole and `D = N · K`. For positive `D`, the vector `D p − (K · p) N` lies in both planes and has positive component along `p`. Its ecliptic longitude is the cusp on the selected half great circle. The east cut is the rising horizon cusp and the nadir cut is the below-horizon meridian cusp. Opposite cusps differ by 180°. The Python and REST house results use their standard opening cusp representation. Optional spatial geometry gives the boundary planes.

## Domain conventions

At the geographic equator use the unique two-sided limit `sin(a) = j/3`. At an exact geographic pole the horizon has no rising intersection under diurnal rotation, so Moira rejects the figure. At other latitudes `D = cos(φ) cos(ε) + sin(φ) sin(θ) sin(ε)` with obliquity `ε` and ARMC `θ`. Zero collapses the projection and negative `D` reverses its orientation. Moira rejects those cases and requires a numerically resolved forward cusp cycle. These are explicit domain conventions for this reconstruction.

## Derived witness

At latitude 45° N, ARMC 0° and obliquity 23.44°, the two prime-vertical cuts are 21.470701432° and 45°. The first four ecliptic cusps are 111.692094194°, 132.243356743°, 149.465043814°, and 180°. The regression independently checks the source construction through a scalar plane equation in a meridian-aligned frame and verifies the spatial boundary incidence. These are geometric witnesses derived from Savard's description.
