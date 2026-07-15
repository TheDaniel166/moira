# Ptolemaic and Chaldaean Bounds Validation — 2026-07-15

## Scope

This record validates the tables selected by the non-Egyptian members of
`EgyptianBoundsDoctrine`. It repairs two pre-existing label/data defects:

- `PTOLEMAIC_BOUNDS` duplicated `EGYPTIAN_BOUNDS`;
- `CHALDEAN_BOUNDS` did not implement the stated Chaldaean construction and
  concealed its day/night dependency.

The default Egyptian table and its lookup semantics are unchanged.

## Authority and product semantics

The table authority is Claudius Ptolemy, *Tetrabiblos* I.20/I.21, translated
by F. E. Robbins, Loeb Classical Library 435 (1940):

- "Terms according to the Egyptians," printed pp. 96-97;
- Chaldaean order, widths, and sect distinction, printed pp. 100-103;
- "Terms according to Ptolemy," printed pp. 108-109.

Online witnesses:

- [LacusCurtius Robbins transcription](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Ptolemy/Tetrabiblos/1B*.html)
- [Wikisource scan of Loeb 435](https://en.wikisource.org/wiki/File:Loeb_435_-_Ptolemy_-_Tetrabiblos_by_Robbins_(1940).pdf)

This is authority validation of a historical doctrinal table, not empirical
validation of astrological effects.

## Ptolemaic reconstruction decision

The admitted Ptolemaic table follows the five ruler/width pairs printed for
each sign. The transcription displays Saturn twice in Libra, ending with a
second six-degree Saturn segment. The chapter's immediately following totals
resolve that transmitted symbol error: Saturn totals 57° and Mars 66° only
when Libra's final six degrees belong to Mars. Moira therefore records Libra
as:

1. Saturn `[0, 6)`
2. Venus `[6, 11)`
3. Mercury `[11, 16)`
4. Jupiter `[16, 24)`
5. Mars `[24, 30)`

The resulting global totals are:

| Ruler | Degrees |
|---|---:|
| Saturn | 57 |
| Jupiter | 79 |
| Mars | 66 |
| Venus | 82 |
| Mercury | 76 |

They sum to 360° and match the source's stated totals.

## Chaldaean construction decision

Ptolemy states a repeated triplicity order and assigns widths of 8°, 7°, 6°,
5°, and 4° in descending order. Saturn precedes Mercury by day; Mercury
precedes Saturn by night. A single `chaldean` doctrine is therefore
semantically incomplete.

Moira admits two explicit variants:

- `chaldean_day`
- `chaldean_night`

Their source-stated planetary totals are:

| Ruler | Day | Night |
|---|---:|---:|
| Saturn | 78 | 66 |
| Jupiter | 72 | 72 |
| Mars | 69 | 69 |
| Venus | 75 | 75 |
| Mercury | 66 | 78 |

Each column sums to 360°. The former ambiguous string `chaldean` is rejected
by engine/transport enum validation rather than mapped to a hidden sect.

## Boundary law

All four admitted tables use left-closed, right-open intervals `[start, end)`.
Every sign has exactly five positive-width segments covering `[0, 30)` with no
gap or overlap. Longitudes are normalized modulo 360 before lookup.

## Public visibility

The corrected doctrines are selectable through:

- `moira.egyptian_bounds.EgyptianBoundsPolicy`
- `GET /v1/egyptian-bounds/table`
- all `/v1/egyptian-bounds/*` requests that accept `policy.doctrine`

Table and bound-truth REST envelopes include the selected primary-source
citation.

## Validation commands

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_egyptian_bounds.py tests\unit\test_egyptian_bounds_public_api.py tests\server\test_server_egyptian_bounds_routes.py -q
```

The targeted slice validates:

- the complete literal Ptolemaic table;
- all four 12-sign × 5-segment coverage invariants;
- Ptolemaic and Chaldaean planetary totals;
- Chaldaean day/night Saturn/Mercury reversal;
- exact left-closed/right-open boundaries;
- curated module exports;
- REST table and lookup serialization;
- source-citation visibility;
- rejection of the ambiguous legacy doctrine value.
