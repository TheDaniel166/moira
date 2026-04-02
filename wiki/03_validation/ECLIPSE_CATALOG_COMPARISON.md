# Eclipse Catalog Comparison

This report compares Moira's eclipse calculations against the local NASA catalog fixture already used in the test suite. It is intended as a readable cross-era summary, not as a replacement for the tests themselves.

## Maxima Snapshots

### Solar

| NASA date | NASA type | Moira native type at NASA maximum | Notes |
|---|---|---|---|
| -1797-02-01T21:25:34 | H | hybrid | classification at catalog maximum |
| 0500-02-15T11:06:27 | H | hybrid | classification at catalog maximum |
| 0500-08-11T00:35:02 | A | annular | classification at catalog maximum |
| 2005-04-08T20:36:51 | H | hybrid | classification at catalog maximum |
| 2809-02-05T21:20:58 | H | hybrid | classification at catalog maximum |

### Lunar

| NASA date | NASA type | Moira native type at NASA maximum | Notes |
|---|---|---|---|
| -1801-04-30T07:38:52 | T | total | classification at catalog maximum |
| -1801-10-23T22:49:56 | P | partial | classification at catalog maximum |
| 0499-03-13T12:12:02 | T | total | classification at catalog maximum |
| 2000-01-21T04:44:34 | T | total | classification at catalog maximum |
| 2800-02-01T23:47:11 | T | total | classification at catalog maximum |

## Search Timing

These are the more meaningful comparison rows, because they compare the catalog's reported greatest-eclipse instant against Moira's own searched maximum.

### Solar Search Cases

| Case | NASA expected | Moira native | Residual |
|---|---|---|---:|
| ancient_hybrid (hybrid) | -1797-02-01T09:51:13.000029Z | -1797-02-01T09:49:52.939670Z | -80.06 s |

### Lunar Search Cases

| Case | NASA expected | Moira native | Native residual | `nasa_compat` | Compat residual |
|---|---|---|---:|---|---:|
| ancient_total (total) | -1801-04-29T20:03:04.999996Z | -1801-04-29T20:02:15.346372Z | -49.65 s | -1801-04-29T20:08:07.632251Z | +302.63 s |
| future_penumbral (penumbral) | 2801-06-17T19:00:54.999930Z | 2801-06-17T19:01:15.757170Z | +20.76 s | 2801-06-17T19:01:25.031833Z | +30.03 s |

## Interpretation

- At catalog maxima, Moira's native classifier agrees cleanly across the representative ancient, classical, modern, and future rows in this local fixture slice.
- The meaningful timing differences appear in searched greatest-eclipse instants, not in simple at-instant classification.
- For lunar ancient cases, the largest single contributor is the Delta T branch choice. In the diagnosed `ancient_total` case, switching the same native shadow-axis objective from native Delta T to NASA-canon Delta T moves the answer by about 387 seconds.
- Moon treatment matters too. In that same case, switching from a retarded Moon to a geometric Moon inside the native branch moves the result by about 35 seconds.
- Once Delta T branch and Moon treatment are aligned, Moira's native shadow-axis minimum and the canon gamma-minimum objective collapse to essentially the same instant. That means the remaining difference is primarily model basis, not an unstable search algorithm.
- Practical reading: modern and near-modern comparisons are tight; deep ancient and far-future timing comparisons should be read through the lens of Delta T doctrine and event-definition choice, not just raw residual size.

