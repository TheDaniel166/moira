# Eclipse Stage 7 readiness

November 18, 2026

**Stage 7 is accepted for the declared computational models.** The
catalog regeneration, scientific dispositions and final verification are
complete. The solar closure uses certified boundary bands with individual
spatial error bounds and the named, time-stamped geographic width.

The generating revision is `b6d2ad89ef38f88ca71d03bc50f5a9543d465150`.
The freeze binds 3,578 source and resource files, the existing native
binary, DE441, and the runner and model configurations. The three searches
independently cover the TT interval `[990923.5, 2817152.5)`.

| Model | Discovery rows | Detail rows |
| --- | ---: | ---: |
| Native solar | 11,898 | 11,898 |
| Native lunar | 12,068 | 12,068 |
| NASA-compatible lunar | 12,069 | 12,069 |

All rows passed the merged identity, time-scale, contact-order and
availability checks. Each model has the same identities, broad labels
and Saros numbers as its prior provisional catalog. The largest discovery
TT shifts were 26.514 ms, 3.259 ms and 29.974 ms respectively. The archive
contains the pre-change and prior provisional comparisons separately,
including every recorded field delta and missing value.

The focused verification passed 368 tests and nine real loopback HTTP
checks. It repeated 1,104 snapshots, 552 endpoint checks and 92 continuous
event-domain replays. The original Stage 3 interval proofs carry forward
under checked numerical source equivalence and identical computational
resources. The rebind also passed 55,533 fresh native input checks. The
legacy response and selector contracts pass. Canon durations use TT and
the corresponding catalog contact epochs use UT1. All 95 differences
between the duration and its UT1 endpoint span reconcile under the
month-midpoint Delta-T rule.

The individual ledger includes the 20 solar type disputes, five presence
anomalies, 26 lunar discrepancies, 92 solar paths and four timing probes.
It also includes the additional source-specific discrepancies from the
NASA, EclipseWise, Skyfield and available OPALE comparisons. The original
five-millennium NASA identity extracts were reproduced from the century
tables with the published numerical fields. Source-specific dates, model
conventions and precision are retained. [NASA solar catalog key](https://eclipse.gsfc.nasa.gov/SEcat5/SEcatkey.html),
[NASA lunar catalog key](https://eclipse.gsfc.nasa.gov/LEcat5/LEcatkey.html),
[EclipseWise path table key](https://www.eclipsewise.com/solar/SEhelp/SEpathkey.html).

## Closing verification

Lunations −47467, −45765 and −24109 are excluded over their entire
closed eight-hour UT1 intervals and the full WGS84 surface. Their
minimum certified Earth-to-plane separations exceed 2.878 km, 1.177 km
and 0.178 km, respectively. The two constructive presence witnesses
pass for −33903 and −32201.

All 92 event domains have complete central-footprint boundary enclosures.
Every retained band cell has certified distances to interior and
exterior witnesses. The maximum two-sided spatial error bound is
73.303 km at lunation −25769. The separately time-stamped Moira
geographic widths have interval spans below 0.201 km in the detailed
replay. All 92 requests to the evidence API achieve its default 1 km
span with the 4,096-predicate budget, with a maximum span below 0.942 km.

The width audit checked 424 NASA widths and 17 EclipseWise widths against
the published Besselian inputs and the historical perpendicular-to-track
estimate. Every interval overlaps at the printed precision. The support
widths in the source tables, omissions in the original bulletin and
Moira's geographic arc have individual semantics and provenance. The
[solar closure](ECLIPSE_STAGE7_CLOSURE.md) records the derivations and the
scope of the publication check.

The closing tree passed 60 distinct tests and ten loopback HTTP checks.
A further 41 selected detail rows reproduced every deterministic field
from the frozen catalogs. The boundary audit replayed 3,033 full-cell
interior witnesses and separately checked 54 interior sites using the
native angular geometry. The regenerated catalog bytes retain their
original generating revision and resource identities.

The local `stage7_catalog_and_evidence_20261118.zip` archive contains the
catalogs, source and shard receipts, comparison rows, individual
dispositions and verification scripts. Its SHA-256 is
`f6a77082fe12e90df6d428d540bb2f0bed2c450abcfb90f336145bb52d32af1c`.
All 665 entries listed in its manifest were checked against their hashes.
The closing archive `stage7_acceptance_evidence_20261118.zip` records the
final case ledger, proof replays, closing source, and verification
receipts. The acceptance receipt identifies both archives.
