# Release Notes - Moira 6.12.1

**Release date:** 3 November 2026.

This patch restores use of the existing native apparent-position evaluator in
transit longitude searches. The shared fixed-target scanner introduced during
the Geodetic expansion retains its connected orb windows, stationary and tangent
contacts, inclusive study bounds, finite budgets and incomplete-search failures.

Canonical apparent longitude samples now seed the same scan memo. Planetary
lookups omit unused speed evaluation and full PlanetData assembly; True Node
lookups omit only its unused finite-difference rate. Native admission keeps the
existing correction, frame, TT/TDB, reader and neighbouring-epoch checks. Readers
that cannot use that evaluator retain the scalar planetary provider.

The REST endpoints and response schemas are unchanged. Both the natal-aspect
endpoint and the batch event kind benefit from the common repair. Backward
frozen-longitude grids now return reverse chronological order as requested.

No C++ astronomical algorithm, angular tolerance, time tolerance, scan budget,
kernel or package dependency is changed. Performance depends on the selected
window, mover and target set, reader layout and host; benchmark measurements
are not a universal latency guarantee.

See [compatibility notes](COMPATIBILITY_NOTES_6.12.1.md).
