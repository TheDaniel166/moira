# Pancha Pakshi Implementation Handoff — 2026-07-19

> **Superseded checkpoint.** Resume from
> [`PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md`](./PANCHA_PAKSHI_ADMISSION_EVIDENCE_2026-07-20.md)
> and the live
> [`research and admission standard`](../02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md).
> This file preserves the pre-admission resting state. Phase 0 subsequently
> established a source-scoped public tier and Phase 1 admitted the named 1879
> aksara/fixed-clock product without selecting a default canon. Competent-human
> Tamil review and independent-witness collation remain evidence upgrades and
> broader-claim gates, not blockers for that narrow public product.

## Historical Resting State

The working tree is intentionally uncommitted and coherent. The Pancha Pakshi
work has reached an internal research checkpoint; no package-root export,
`moira.vedic` export, `Moira` facade method, FastAPI route, OpenAPI schema, or
native/C++ path was added.

The public engine remains unchanged. Do not begin tomorrow by adding a route.
Begin by re-running the checkpoint tests and reviewing the admission gate in
`wiki/02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md`.

## Completed Work

### Shared astronomical boundary

- Added `moira/_local_solar_day.py`.
- Refactored `moira/planetary_hours.py` to consume the same resolved
  sunrise-to-sunrise window, UTC/UT1 civil-noon anchoring, geographic
  validation, polar failure, and local-mean-solar weekday.
- Preserved all existing Planetary Hours public vessels, signatures, FastAPI
  schemas, numerical behavior, and error semantics.

### Private Pancha Pakshi foundation

- Added `moira/_pancha_pakshi.py`.
- Added the research-only profile
  `agastya_madras_1879_akshara_fixed_clock`.
- Added a hash-bearing manifest and source/conflict metadata.
- Used exact `Fraction` arithmetic for the fixed thirty-nazhigai halves,
  five six-nazhigai samams, and all activity durations.
- Generated all 28 regime/weekday schedules from the current 1879 rule
  reading; the printed grids are non-executable review evidence because their
  table axes and night assembly remain unreconciled.
- Preserved source locators on every generated schedule cell.
- Kept the source identity as aksara/query-or-name initial. It is explicitly
  not natal-Moon or birth-nakshatra identity.
- Added the current source-scoped 20-cell directed relationship reading with
  no reciprocal inference; it remains contested pending competent
  transcription of every governing edge.
- Explicitly omitted natal mapping, scoring, padu, vinadi, astronomical
  paksha routing, seasonal scaling, and cross-witness relationship
  normalization.

### Documentation

- Added `wiki/02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md`.
- Updated `PROVENANCE.md`, `CHANGELOG.md`, and the Planetary Hours backend
  standard.
- Recorded the Sarasvati Mahal catalog/title-page discrepancy rather than
  selecting one edition claim silently.

## Evidence Boundary

The governing 1879 witness is:

- Internet Archive ID: `dli.rmrl.000451_images`
- URL: <https://archive.org/details/dli.rmrl.000451_images>
- publication: Madras, 1879, Mattoovar Colalumbal Press
- traditional attribution: Agastya; authorship is not asserted
- original image ZIP MD5: `823f14099d376ac86a358349de292e1f`
- original image ZIP SHA-1: `5e3dcda52dcd87f9d5a91d23f22de605cfbd01ce`
- PDF MD5: `0736b952fb587132c2181a383ff10cfb`
- PDF SHA-1: `d41ff5c2d569de6422435b20135b58be82a68560`
- locally verified PDF SHA-256:
  `ed52945ee141faa3f6967b8f043077b95abef9ff674ffb83eaba633417c669c9`

The print is a research witness, not a package asset. Moira never packages its
scan, PDF, OCR, prose, typography, or layout; it stores independently
normalized computational facts, checksums, and locators. Later witnesses
remain metadata-only because their computational and verse/commentary
conflicts are unresolved, not because archival rights are an admission gate.

## Verified Checkpoint

Environment:

- project runtime: `.venv` Python 3.14.3
- `MOIRA_TEST_MODE=1`
- `MOIRA_STRICT_KNOWN_ISSUES=1`
- `tests/KNOWN_ISSUES.yml`: empty
- DE441 discovered with downloads disabled before protected work

Final combined command:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_local_solar_day.py `
  tests\unit\test_planetary_hours_api.py `
  tests\unit\test_facade_clock_boundaries.py `
  tests\unit\test_pancha_pakshi_internal.py `
  tests\unit\test_pancha_pakshi_data_integrity.py -q
```

Result: **66 passed**. The two real solar tests exercised the DE441-backed
topocentric `-0.833°` sunrise/sunset path, common-location window invariants,
Sydney weekday behavior, and explicit polar failure.

Additional checks:

- `py_compile` for `_local_solar_day.py`, `_pancha_pakshi.py`, and
  `planetary_hours.py`: passed
- `scripts/check_doc_consistency.py`: passed
- `git diff --check`: passed
- Python 3.10 syntax parse: passed
- all five JSON records parsed
- manifest/reconciliation/profile normalized SHA-256 matched at
  `5a63ee007a32ec242fd47b91a4b22ff22c6c59d87c0b4716f0c0c562260a98ae`
- the source-reading reconciliation distinguishes two-record duration
  agreement, a scope-limited displayed-half match, and one-record/profile
  matches; it remains explicitly non-executable

## Historical Resume Sequence

1. Run `git status --short --branch`; preserve this exact uncommitted scope.
2. Re-run the 66-test checkpoint above.
3. Inspect the private module/data diff and decide whether to commit this
   research checkpoint as its own change before any further work.
4. Do not expose it publicly until one profile has:
   - independent double transcription;
   - review by a competent Tamil reader;
   - cross-witness collation;
   - explicit verse/commentary precedence;
   - source-owned worked cases or equivalent external examples.
5. Keep these later products separate even after admission:
   - operating schedule;
   - natal-bird assignment;
   - directed relationships;
   - padu/adhikara;
   - sukshma/vinadi timing;
   - scoring or electional interpretation.

The next task is therefore an admission-evidence decision, not facade or REST
implementation.
