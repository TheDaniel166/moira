# Eclipse Footprint Native Boundary

**Status:** admitted narrow native substrate

**Date:** 2026-07-22

**Governing doctrine:**
[Moira Python-Governed Native Strengthening](./MOIRA_PYTHON_GOVERNED_NATIVE_STRENGTHENING.md)

## Product boundary

The admitted public product is
`EclipseCalculator.solar_eclipse_footprint()`. Python owns its time policy,
Earth-fixed shadow construction, WGS-84 product meaning, north/south identity,
curvature and global-path admission, horizon incidences, component topology,
track assembly, and typed public vessels.

`src/native/include/eclipse_footprint.hpp` accelerates only two dense numeric
operations whose input states are explicitly constructed by Python:

1. repeated fixed-site penumbral-clearance scans over the fixed solver lattice;
2. cone-generator/WGS-84 intersections and deterministic azimuth-root candidate
   discovery for one current/before/after shadow triple.

Both bindings accept ordinary Python sequences and return pybind11-owned scalar
vessels. NumPy is neither imported nor required. Native availability is an
explicit acceleration boundary; the retained Python manuscript remains the
differential parity oracle.

## What is not admitted

`src/native/include/cartography.hpp` contains legacy observer-grid experiments.
It has no active caller or binding. Its raster maxima, local magnitude,
cross-track magnitude contour, and lunar visibility-grid products are not the
same computational object as the first-class swept penumbral footprint.

Those routines must not be rebound as an implementation shortcut. Any future
observer-grid or contour product requires its own public semantics, correction
policy, authority, validation corpus, units, tolerances, and sequence-or-buffer
boundary. Magnitude and duration contours remain separate prospective products;
they are not inferred from the footprint.

## Verification law

Admission requires all of the following without threshold relaxation:

- Python/native differential checks for candidate identity and coordinates;
- dated topology regressions covering horizon-adjacent branches and folds;
- existing eclipse footprint and public-boundary tests;
- explicit performance measurements reported as performance evidence, not
  astronomical validation;
- external authority and physical-invariant checks at the public product layer.

The native candidate solver may reduce repeated numerical work. It may not
decide which candidates become lawful public tracks.
