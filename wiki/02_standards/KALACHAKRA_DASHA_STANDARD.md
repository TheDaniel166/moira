# Kalachakra Dasha backend contract

VED-014 implements the selected `bphs_santhanam_longitude_row_cycle_v1`
profile under the [implementation plan](../06_roadmap/VEDIC_KALACHAKRA_IMPLEMENTATION_PLAN_2026-10-12.md)
and [source ledger](../06_roadmap/VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md).
The selected scope is locally implemented and validated as of 12 October 2026;
see the [execution receipt](../03_validation/VEDIC_KALACHAKRA_VALIDATION_2026-10-12.md)
and [Python/REST contract](../02_services/KALACHAKRA_DASHA_API.md). Publication is separate.

BPHS 46.93 governs longitude balance. The reconciled sixteen nine-occurrence
rows, Santhanam's row-repetition examples and chapter 64 govern continuation
and antardashas. KC-01 through KC-14 retain source corrections, competing
schools and unresolved evidence. No generic classical default is admitted.

Source arithmetic uses exact ratios of the admitted binary64 longitude, with
half-open rational pada and occurrence boundaries and no epsilon snapping.
Nine MDs include the birth residual. Optional level two partitions full MDs
before clipping, preserves all nine child identities, and returns null visible
spans for wholly pre-birth ADs. The product contains 9 or 90 period nodes.

Projection requires an explicit 360-day or 365.25-day clock, using UTC-derived
JD endpoints from a common exact origin. Astronomical UT1/TT provenance remains
separate. Unrepresentable positive intervals cause a typed error, never silent
deletion. Active lookup uses returned half-open endpoints and bounded coverage.

The same owner governs Python and REST. Supplied and derived provenance remain
distinct. Eligibility is not evaluated; natal-row Deha/Jeeva and bounded gati
evidence do not predict lifespan or events. Research candidates are discoverable
but not executable. The plan specifies all public contracts and acceptance gates.
