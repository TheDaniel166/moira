# Compatibility Notes - Moira 6.12.1

Python 3.10 through 3.15 remain supported. No REST request/response schema,
public function signature, native extension signature or dependency changes.

Transit search longitudes continue to use default apparent geocentric tropical
positions with the existing UT1-to-TT/TDB policy. The existing native planetary
admission governs acceleration; other readers retain the scalar provider.
True Node retains its geometric osculating-plane definition and frame.

The connected orb-window, stationary/tangent contact, range-endpoint,
completeness and finite-budget checks are retained. Scientific comparison
tolerances are unchanged. Native/scalar floating-point residuals remain governed
by the existing native planetary validation; this patch does not declare a new
accuracy envelope.

Frozen-longitude aspect grids requested with `search_motion="backward"` now
return reverse chronological order. Their event fields and forward ordering
are unchanged. Legacy geometric candidate-series helpers remain available for
their existing internal callers; they are not substituted for canonical apparent
samples in the bounded fixed-target scanner.
