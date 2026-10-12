# VED-017 primary comparison receipts

Produced on 11 October 2026 with `scripts/validate_gochara_windows.py` against
the frozen `tests/fixtures/gochara_windows_validation_spec.json`.

- `matrix`: 84 body/system crossings, final run3.
- `retrograde`: 15 same-ray direct/retrograde/direct crossings, final retro2.
- `wrap`: Sun and Moon zero-ray crossings, wrap1.

Each directory retains candidate inputs, exact Horizons requests, raw returned
text, raw-text SHA-256 hashes and the computed comparison/event receipt. The
final matrix and retrograde runs reuse checksum-verified primary responses
where exact parameters match. These are 101 comparisons, not 101 independently
new network observations on every rerun. Script point scans select fixtures;
they do not establish search completeness.

Numerical tolerances, model/frame differences, failures repaired before
acceptance, and the bounded interpretation are documented in
`wiki/03_validation/GOCHARA_WINDOWS_VALIDATION_2026-10-11.md`.
This evidence is not a baseline to regenerate to match a failing candidate.
