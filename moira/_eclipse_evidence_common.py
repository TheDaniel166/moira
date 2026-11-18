"""Conversions and failure semantics shared by bounded eclipse adapters."""
from pathlib import Path
from contextlib import contextmanager,ExitStack
from dataclasses import replace

from .eclipse_evidence import (RationalBound as B,EvidenceTimeDomain,EvidenceSource,
    EvidenceBudget,EvidenceQuantity,EvidenceSurfaceRegion,EvidenceCell,EclipseProductEvidence)
from ._eclipse_interval import IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable
from .spk_reader import OutOfRangeError,SpkReader,KernelPool


@contextmanager
def borrow_evidence_reader(reader):
    """Hold pool generation/lifetime while proving one unshadowed direct spine.

    Another reader mentioning any required target (or reversed required pair)
    is conservatively rejected even if its coverage might be disjoint. Unknown
    pair inventories and conflicting planetary identities are not ignored.
    The existing direct type-2 adapters still prove bounded descriptor/record
    coverage after admission. No reader is reopened or silently substituted.
    """
    if type(reader) is not KernelPool:
        yield reader,None
        return
    required = ((0,3),(3,399),(3,301),(0,10))
    targets = {target for _,target in required}
    with ExitStack() as leases:
        try:
            snapshot = leases.enter_context(reader._read_lease())
        except RuntimeError as exc:
            raise EnclosureUnavailable('kernel_pool_closed_or_closing') from exc
        if snapshot is not None:
            inventories = []
            for item in snapshot.readers:
                getter = getattr(item,'_coverage_pairs_tdb',None)
                if not callable(getter):
                    raise EnclosureUnavailable('kernel_pool_pair_inventory_unavailable')
                try:
                    pairs = tuple(getter())
                except Exception as exc:
                    raise EnclosureUnavailable('kernel_pool_pair_inventory_unavailable') from exc
                if any(not isinstance(pair,tuple) or len(pair)!=2 or
                       any(type(x) is not int for x in pair) for pair in pairs):
                    raise EnclosureUnavailable('kernel_pool_pair_inventory_invalid')
                inventories.append((item,pairs))
            candidates = [item for item,pairs in inventories
                          if type(item) is SpkReader and all(pair in pairs for pair in required)]
            if len(candidates) != 1:
                raise EnclosureUnavailable('kernel_pool_requires_one_unambiguous_planetary_spine')
            candidate = candidates[0]
            for item,pairs in inventories:
                if item is candidate:
                    continue
                if any(target in targets or (target,center) in required for center,target in pairs):
                    raise EnclosureUnavailable('kernel_pool_competing_eclipse_target_route')
                identity = getattr(item,'_kernel_identity',None)
                if identity is not None and identity != candidate._kernel_identity:
                    raise EnclosureUnavailable('kernel_pool_conflicting_planetary_identity')
            yield candidate,snapshot.generation


def annotate_pool(bundle,admitted):
    if admitted is None:
        return bundle
    return replace(bundle,products=tuple(replace(p,source=replace(p.source,
        reader_route='unambiguous_pool_snapshot',pool_generation=admitted),notes=(*p.notes,
        'Unambiguous direct planetary spine admitted under a kernel-pool read lease.')) for p in bundle.products))


def reader_admission_failure(bundle,selected,exc):
    return replace(bundle,products=tuple(replace(p,state='unsupported',cause=str(exc),
        source=replace(p.source,reader_route='unadmitted_pool'),
        values=(),cells=(),witnesses=(),coverage_complete=False) if p.product in selected else p
        for p in bundle.products))


def domain(scale,epoch,box):
    return EvidenceTimeDomain(scale,epoch,B.from_interval(box))


def quantity(name,value,unit='dimensionless'):
    return EvidenceQuantity(name,unit,None if value is None else B.from_interval(value),
                            'not_computed' if value is None else 'bounded')


def surface(patch):
    if patch is None:
        return None
    return EvidenceSurfaceRegion(patch.axis,patch.sign,B.from_interval(patch.u),B.from_interval(patch.v))


def source(reader,model,records=None,tables=(), *, clock=None,source_domain=None,tt_domain=None):
    identity = getattr(reader,'_source_identity',None)
    path = getattr(reader,'path',None)
    return EvidenceSource(model,Path(path).name if path else None,
        getattr(identity,'sha256',None),
        tuple(r.sha256 for r in records.records) if records is not None else (),
        tuple(tables),bool(records is not None and records.raw_record_words_verified),
        reader_route='unavailable_input' if reader is None else
            'not_resolved_pool_input' if type(reader) is KernelPool else 'direct_input',
        clock_policy=clock,source_domain=source_domain,
        tt_offset_days_from_anchor=None if tt_domain is None else B.from_interval(tt_domain))


def unavailable(name,time,src,limit,unit,state,cause):
    return EclipseProductEvidence(name,state,cause,time,src,EvidenceBudget(limit,0,unit,state=='unresolved' and limit==0),
        cells=(EvidenceCell(time.offset_days,'unresolved',cause),) if state == 'unresolved' else ())


def failed(name,time,src,limit,unit,exc):
    if isinstance(exc,(EnclosureUnavailable,IntervalBudgetError,OutOfRangeError,FileNotFoundError)):
        state = 'unsupported'
    else:
        state = 'error'
    # A failing callback may already have consumed work before raising. Its
    # missing counter is unknown, not an invented zero evaluation result.
    return replace(unavailable(name,time,src,limit,unit,state,type(exc).__name__+': '+str(exc)),
                   budget=EvidenceBudget(limit,None,unit))
