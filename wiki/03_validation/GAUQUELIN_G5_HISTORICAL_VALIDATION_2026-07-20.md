# Gauquelin g5 Historical-Sector Validation — 2026-07-20

## Decision

The supplied g5 temporary-sector archive is admitted as an **external,
non-bundled validation witness**, not as runtime truth and not as an algorithm
oracle.  Moira's current Gauquelin algorithm is unchanged.

The clean numerical tranches are CFEPP and the explicit-LMT subset of Müller.
CFEPP has UTC date/time and coordinates; Müller LMT converts to UTC directly
from longitude.  CSICOP is retained as a two-policy sensitivity audit because
its g5 conversion path has ambiguous 12-hour-clock semantics.  Ertel and the
167 non-LMT Müller rows remain inventoried but not yet admitted for numerical
comparison.

## Source identity and custody

- User-supplied archive: `g5-tmp-g-sectors.zip`
- Bytes: `243939`
- SHA-256: `889B27999D787574F9CE0771BEB8BA41AC91D1B1362D6A03D12442022821B0BC`
- g5 repository inspected at commit
  `bf0db345b58127a438121b74ebf4ad843243a573`
- g5's source code is GPL-3.0.  No g5 source code is copied into Moira.
- Written correspondence supplied with the archive states that CC-BY-SA is
  acceptable for g5 and Open Gauquelin attribution.  Because the archive
  contains personal records and an exact redistribution attribution line has
  not been fixed, the CSVs remain outside this MIT repository.

The committed fixture contains only aggregate counts and the source hash.  It
does not contain names, dates, places, or coordinates.

## Archive inventory

| File | Actual rows | Sector field | Range | Status |
|---|---:|---|---:|---|
| `cfepp-1120-nienhuys-raw.csv` | 1120 | `S` | 1–12 | numerically compared |
| `csicop-408-irving-raw.csv` | 408 | `MARS` | 1–36 | two-policy sensitivity audit |
| `ertel-4384-sport-raw.csv` | 4384 | `MARS`, `MA12` | 1–36, 1–12 | joins pending |
| `muller5-1083-medics-raw.csv` | 1083 | `MARS` | 1–36 | 916 explicit LMT compared; 167 deferred |

The archive therefore contains 6,995 source rows, not the 6,648 implied by the
counts in the accompanying email.  These are not 6,995 independent people or
experiments: Ertel includes records from Gauquelin and skeptic-test groups,
including CFEPP and CSICOP.

The g5 source definitions resolve the CFEPP discrepancy.  Rows 1–1066 are the
official 1996 CFEPP group; rows 1067–1120 are 54 supplementary Nienhuys cases.
The g5 Ertel definition and conversion code both identify 4,384 rows.  The
email's “4091” is retained as an unresolved likely count typo, not used as a
filter.  Ertel's `MA12` equals `floor((MARS - 1) / 3) + 1` for all 4,384 rows.

The archive also contains a LibreOffice lock file.  The harness ignores it and
never treats it as evidence.

## CFEPP computation

For every CFEPP row, the harness:

1. parses `UNIV_DATE` plus `UT` as an aware UTC instant;
2. negates g5's west-positive `LONG` into Moira's east-positive longitude;
3. computes apparent topocentric Mars RA/declination and local sidereal time
   through the same chart service used by the public Gauquelin route;
4. computes Moira's canonical geometric-horizon 36-sector position; and
5. maps it to 12 sectors with `floor((sector36 - 1) / 3) + 1`.

No source sector is supplied to the computation, and no matching rule can
change Moira's output.

## Results

| Tranche | Compared | Exact | Exact rate | Undefined |
|---|---:|---:|---:|---:|
| Official CFEPP first 1066 | 1066 | 1053 | 98.7805% | 0 |
| Nienhuys supplementary final 54 | 54 | 54 | 100% | 0 |
| **Total** | **1120** | **1107** | **98.8393%** | **0** |

All 13 non-exact results differ by exactly one adjacent 12-sector bin.  Their
Moira positions lie between `0.009740°` and `0.534203°` of the nearest
12-sector boundary.  This localizes the disagreement to boundary-sensitive
cases.  It is consistent with differences in source time precision,
ephemeris, reference frame, or historical calculation method, but this pass
does not adjudicate which cause applies to any record.

The result corroborates the current numbering, longitude convention, and
diurnal-sector implementation.  It does not justify changing the algorithm to
force 100% agreement with a source whose maintainer explicitly warns that some
original sectors may be erroneous.

## Müller explicit-LMT result

For 916 rows, `MODE=LMT` explicitly identifies local mean solar time.  The
harness parses directional longitude and applies
`UTC = LMT - east-positive-longitude / 15 hours`.  It also normalizes source
times written as `24.xx` into the following civil day.  The 167 rows with a
blank mode are excluded; their `KORR` codes are not interpreted.

| Compared | Exact | Adjacent bin | Larger difference | Undefined |
|---:|---:|---:|---:|---:|
| 916 | 904 (98.6900%) | 7 | 5 | 0 |

The five larger circular differences are 7, 8, 13, 14, and 16 of 36 sectors.
They remain source-adjudication cases rather than inputs to an algorithm
change.  Of the seven adjacent differences, the aggregate report retains
continuous boundary distance without exposing personal records.

## CSICOP sensitivity result

The 2019 g5 `raw2tmp.php` converter constructs local time by adding 12 hours
for `P` and `P1` but leaving `A` and `A1` unchanged.  Applied literally, that
turns `12 P` into 24:xx and leaves `12 A` at 12:xx.  The archive has 32 records
at hour 12, so the harness reports both the literal g5 rule and conventional
12-hour-clock semantics.  The special g5 `ZEITZONE=0,5` rule is preserved as
UTC-10:30 under both policies.

| CSICOP time policy | Exact | Within 1 bin | Within 2 bins | Large outliers |
|---|---:|---:|---:|---:|
| Literal g5 2019 conversion | 304/408 | 336/408 | 374/408 | 34 |
| Conventional noon/midnight | 326/408 | 363/408 | 406/408 | 2 |

The conventional policy removes every half-wheel discrepancy caused by the
hour-12 reversal.  It is still a sensitivity result, not an admitted authority
choice: confirmation from the data maintainer or an original CSICOP codebook
is needed before selecting it.  The remaining two outliers differ by 8 and 10
of the 36 sectors and should be checked against the original records.  The
other 80 non-exact conventional results differ by one or two narrow 10-degree
diurnal bins, which can reflect clock/zone precision as well as calculation
method.  No tolerance is used to relabel them exact.

## Reproduction

With the external archive present and a DE441 kernel installed:

```powershell
$env:MOIRA_AUTO_DOWNLOAD = '0'
.\.venv\Scripts\python.exe scripts\validate_g5_gauquelin_sectors.py `
  'C:\Users\nilad\Downloads\g5-tmp-g-sectors.zip' `
  --output .\tmp\gauquelin-g5-full.json
```

The committed aggregate result is
`tests/fixtures/gauquelin_g5_aggregate_2026_07_20.json`.

## Deferred tranches

- **CSICOP:** obtain an authority decision for hour-12 AM/PM semantics and
  inspect the two large outliers against the original records/codebook.
- **Müller:** adjudicate the 167 non-LMT correction codes and inspect the five
  large explicit-LMT outliers against the original booklet/list.
- **Ertel:** join its source identifiers to records that carry birth time and
  place.  Many Ertel rows omit time and the raw sector file has no coordinates.

Each deferred tranche needs a separate, tested adapter.  No guessed conversion
may be admitted merely to improve agreement.
