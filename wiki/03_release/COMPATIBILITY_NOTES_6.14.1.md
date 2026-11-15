# Compatibility Notes - Moira 6.14.1

Python 3.10 through 3.15 are supported. Version 6.14.0 was tagged but never
published, so upgrades from 6.13.1 take every change listed in the
[6.14.0 compatibility notes](COMPATIBILITY_NOTES_6.14.0.md). In brief:

- **Topocentric comet positions change value.** The observer was previously
  absent from the comet light-time solution. Recalculate any stored
  topocentric comet right ascension or declination; geocentric comet positions
  and all asteroid positions are unchanged.
- The out-of-bounds declination solver, Sothic drift fitting and their REST
  routes are new surfaces and change no existing result.
- The lunar nodes and apogees are not admitted to the out-of-bounds surface,
  and the same four names are now refused by the shared declination primitive
  with a named error.

## What 6.14.1 adds over 6.14.0

**macOS arm64 wheels now import.** If you obtained a 6.14.0 arm64 wheel from a
source other than PyPI — none was published there — it cannot load, and this
release is the fix. x86 wheels on any platform are unaffected and behave
identically.

**No computed result changes.** The AVX2 guard is a build-time correction: the
dispatch branch it guards was already unreachable at runtime on non-x86, since
`runtime_avx2_available()` returns false there. x86 codegen is untouched,
because the preprocessor keeps the blocks verbatim wherever the macro is
defined.

**One new facade export pair.** `moira.facade` re-exports `SothicDriftSample`
and `SothicDriftFit`, so a facade caller can name the type
`SothicRisingSeries.fit_drift()` returns. Additive.

**Sothic documentation changes meaning without changing numbers.** Three
statements were wrong or absent and are corrected; no computed value moves:

- The documented drift rate was 0.242 days/year and is about 0.25. If you
  relied on the documented figure rather than the computed one, your
  expectations shift by 3.7 per cent — the computation never did.
- `sothic_epochs` returns one entry per year within tolerance, not one per
  realignment. Consecutive years are a single window; counting the list length
  as a number of epochs overcounts by roughly `2 * tolerance / 0.25`.
- `predicted_sothic_epoch_year` is schematic and falls progressively earlier
  than the computed window — two years at one cycle back from AD 139, five at
  two. Use `sothic_epochs` when the computed realignment is what matters.
