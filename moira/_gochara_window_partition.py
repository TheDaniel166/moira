"""Closed boundary bands and disjoint certain regions for whole-sign Gochar."""
from .gochara_windows import GocharaWindowRegion


def partition(start, end, events, unresolved, state_at, meter):
    """Every instant is owned exactly once; uncertainty is never bridged."""
    bands = [(e.lower_jd_ut1, e.upper_jd_ut1, (e.id,), e.reasons) for e in events]
    bands.extend((a, b, (), (reason,)) for a, b, reason in unresolved)
    merged = []
    for a, b, ids, reasons in sorted(bands):
        a, b = max(start, a), min(end, b)
        if a > b:
            continue
        # An open gap can be positive mathematically yet contain no binary64
        # epoch. Retain it as uncertainty rather than sample a band endpoint.
        no_witness = bool(merged and a > merged[-1][1] and
            not merged[-1][1] < (merged[-1][1]+a)/2 < a)
        if merged and (a <= merged[-1][1] or no_witness):
            old_a, old_b, old_ids, old_reasons = merged.pop()
            ids = tuple(sorted(set((*old_ids, *ids))))
            # Overlap is not a proof that distinct events are simultaneous.
            combined = tuple(sorted(set((*old_reasons, *reasons))))
            if len(ids) > 1 and a <= old_b:
                combined = tuple(sorted(set((*combined, "event_order_unresolved"))))
            if no_witness:
                combined = tuple(sorted(set((*combined, "no_representable_interior_witness"))))
            merged.append((old_a, max(b, old_b), ids, combined))
        else:
            merged.append((a, b, ids, reasons))
    regions = []

    def append(a, b, include_a, include_b, kind, state=None, sample=None, ids=(), reasons=()):
        meter.tick("cells")
        regions.append(GocharaWindowRegion(len(regions), a, b, include_a, include_b,
                                          kind, state, sample, ids, reasons))

    def witness(a, b, include_a, include_b):
        mid = (a+b)/2
        if a < mid < b:
            return mid
        if include_a:
            return a
        if include_b:
            return b
        raise ValueError("open interval has no representable witness")

    cursor, include_start = start, True
    for a, b, ids, reasons in merged:
        if cursor < a:
            state, sample = state_at(witness(cursor,a,include_start,False))
            append(cursor, a, include_start, False, "certain", state, sample)
        append(a, b, True, True, "unresolved_band" if reasons else "boundary_band",
               ids=ids, reasons=reasons)
        cursor, include_start = b, False
    if cursor < end:
        state, sample = state_at(witness(cursor,end,include_start,True))
        append(cursor, end, include_start, True, "certain", state, sample)
    return tuple(regions)
