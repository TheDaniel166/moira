# Compatibility Notes - Moira 6.13.1

Python 3.10 through 3.15 are supported. Version 6.13.0 was tagged but never
published, so upgrades from 6.12.1 take every change listed in the
[6.13.0 compatibility notes](COMPATIBILITY_NOTES_6.13.0.md). In brief:

- Zariel cusps change, so stored Zariel charts need recalculating.
- Generated harmonic layouts report family names, and `pattern.name` changes for
  code that compares the old numbered forms.
- Patterns that returned `Not assessed` now receive a band, unless they are
  Stelliums or caller-supplied templates.
- The coherence policy identifier is
  `moira.pattern_coherence.qualitative.v2-draft`.

6.13.1 adds no behaviour of its own beyond 6.13.0.
