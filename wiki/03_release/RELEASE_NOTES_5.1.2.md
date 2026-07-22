# Moira 5.1.2 - Eclipse Geometry and Native Footprint Hardening

**Release date:** 2026-07-22

**Public upgrade path:** 5.1.1 to 5.1.2

Moira 5.1.2 strengthens the solar-footprint solver and corrects the governing
geometry used to search, classify, and time lunar eclipses. It is a patch
release with no public API schema changes and no new Python runtime dependency.

## Solar eclipse footprints

The event-swept solar footprint now closes difficult penumbral components at
their exact sunrise and sunset incidences. Close horizon-root pairs and
junctions that previously produced malformed components or an incidence-count
exception are retained and assembled under explicit Python-owned topology
rules. Regression coverage includes the affected 2027-2031 events, including
the reported 2031 hybrid footprint.

Dense, stable numerical work is now selectively strengthened by the C++17
extension through three bounded products:

- a reusable penumbral-clearance scanner;
- lawful penumbral-generator azimuth intervals; and
- penumbral envelope-candidate discovery on WGS 84.

Python remains the governing layer for shadow construction, branch doctrine,
root refinement, component assembly, ambiguity handling, fallback, and public
`SolarEclipseFootprint` semantics. The native path consumes plain numeric
buffers and vectors, has an exact Python fallback, and introduces no NumPy
dependency. The older native cartography header remains quarantined from the
public bindings rather than being revived as a second eclipse doctrine.

On the bounded 2028 footprint benchmark used during development, the admitted
native helper path completed in 12.186 seconds versus 21.443 seconds for the
Python fallback, a 1.760x speedup with identical public output for that case.
This is performance evidence only, not astronomical validation.

## Lunar eclipse event geometry

Global lunar eclipse identity now uses one physical event model throughout
greatest-eclipse refinement, exact classification, and contact timing:

- the incoming reception-light-time-corrected solar direction defines Earth's
  physical shadow axis at the event TT epoch;
- the Moon is evaluated at its physical geocentric state at that same epoch;
- a light-time-retarded Moon remains available only to explicitly named
  apparent diagnostic and observer-facing products.

The candidate-discovery latitude gate is now a conservative two-degree
opposition neighborhood. It is only a discovery superset; exact shadow-cone and
lunar-disk geometry still performs classification. This restores two shallow
penumbral events that the former 1.5-degree gate missed and eliminates a false
partial classification caused by mixing apparent and physical Moon semantics.

The observable corrections are:

- 1922-03-13 is discovered and classified as penumbral;
- 1940-03-23 is discovered and classified as penumbral; and
- 1988-03-03 is classified as penumbral rather than partial.

## Validation evidence

The release adds a static, provenance-recorded transcription of all 229 rows
in the official NASA/GSFC 1901-2000 lunar eclipse catalog. Against that corpus:

- all 229 events have the correct eclipse type family at NASA's published
  greatest-eclipse TD/TT time;
- forward search recovers all 229 events in exact order and type family;
- backward search recovers the same complete sequence; and
- bulk range search recovers the same 229-event sequence.

Across those century searches, the largest greatest-eclipse TT residual from
the published NASA catalog time was less than 55 seconds. This is a named
cross-model authority comparison under NASA's catalog semantics, not a claim
that one corpus proves the entire eclipse subsystem fault-free.

The release also exercises the solar topology regressions, native/Python
footprint parity and fallback, dedicated eclipse suites, and the kernel-free
native parity baseline. The runtime engine continues to use its independently
evaluated, content-identified DE441/LE441 geometry.

Pushing the `v5.1.2` tag triggers the repository's GitHub Actions publication
workflow, which builds the supported source distribution and platform/Python
wheels and publishes them to PyPI.
