# Kalachakra Dasha backend contract

VED-014 implements `bphs_santhanam_longitude_row_cycle_v1` and
`rao_2000_longitude_continuous_v1`. The first profile follows the
[implementation plan](../06_roadmap/VEDIC_KALACHAKRA_IMPLEMENTATION_PLAN_2026-10-12.md)
and [source ledger](../06_roadmap/VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md).
The original selected scope was locally validated on 12 October 2026;
see the [execution receipt](../03_validation/VEDIC_KALACHAKRA_VALIDATION_2026-10-12.md)
and [Python/REST contract](../02_services/KALACHAKRA_DASHA_API.md). Publication is separate.

For Santhanam, BPHS 46.93 governs longitude balance. The reconciled sixteen nine-occurrence
rows, Santhanam's row-repetition examples and chapter 64 govern continuation
and antardashas. KC-01 through KC-14 retain source corrections, competing
schools and unresolved evidence. No generic classical default is admitted.

The Rao extension, authorized on 26 October 2026, uses the inspected 2000
textbook's chapter 24 rules 1-5 and sections 24.3.2-3. It advances through the
eight source rows of one family, recomputes the nine-child denominator, and
uses the birth nine-MD window for Deha/Jeeva. `R2000-01` through `R2000-09`
record membership correction, source choices, clock and product-bound decisions.
Rao's own gati classification does not overwrite the Santhanam conflict record.
The 2018 Rao reformulation is a separate research candidate.

Rao 24.3.3(2) defines Markati by temporary reversal, so a sign pair alone is
insufficient. The occurrence's full source neighbors must establish
`Vi Cn Le Ge` (Savya) or `Ge Le Cn Vi` (Apasavya); ordinary progression through
the same central pair remains unclassified by this rule. Row position, not
the visible window's endpoints, determines that context. The separate frozen
Markati supplement and ring-position oracle validate both readings and their
absence in ordinary progression. Santhanam's KC-10 remains unresolved.

`_kalachakra_recipes.py` owns immutable admitted recipe identities and occurrence
progression. Namespace-free rows belong to Santhanam; `R2000/` rows belong to
Rao. Both constructors and aggregate validators enforce that ownership, weights,
parent windows and metadata. Caller-editable hybrids are not accepted. Exact
interval assembly, clipping, projection, astronomy and active lookup remain
shared. The five existing REST operations invoke the same engine owners.

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
distinct. Eligibility is not evaluated; profile-owned Deha/Jeeva and bounded gati
evidence do not predict lifespan or events. Research candidates are discoverable
but not executable. The plan specifies all public contracts and acceptance gates.
