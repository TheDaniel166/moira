# Moira 5.1.1 — DE440 Historical Delta-T Repair

**Release date:** 2026-07-22

**Public upgrade path:** 5.1.0 to 5.1.1

Moira 5.1.1 fixes reader-backed historical chart computation when the active
planetary kernel is the content-identified JPL DE440/LE440 product.

Moira's historical Delta-T source is expressed on a declared lunar tidal
acceleration basis. Before evaluating a reader-backed ephemeris, the engine
translates that clock product to the active kernel's admitted DE/LE basis.
Version 5.1.0 admitted DE430/LE430 and DE441/LE441 but omitted DE440/LE440, so
historical DE440 chart requests could raise `_EphemerisTimeBasisError` even
though the kernel itself covered the requested epoch.

This release explicitly admits DE440/LE440 at `-25.936 arcsec/cy²`, based on
the JPL DE440/DE441 release record and the official Horizons historical
Delta-T policy for that ephemeris generation. The mapping remains keyed by
the SPK summary identity read from kernel content. Filenames do not establish
identity, and no adjacent or unknown DE/LE release is inferred.

The behavioral scope is narrow:

- historical, basis-sensitive DE440 chart paths now reach TT normally;
- modern direct-EOP epochs are unchanged;
- DE430/LE430 and DE441/LE441 behavior is unchanged;
- unknown or unadmitted kernel identities still fail closed.

Regression coverage exercises content-derived DE440 identity, historical
Delta-T binding, UT1-to-TT conversion, and the retained refusal for an
unadmitted coherent DE/LE identity.

Pushing the `v5.1.1` tag triggers the repository's GitHub Actions publication
workflow, which builds the supported source distribution and platform/Python
wheels and publishes them to PyPI.
