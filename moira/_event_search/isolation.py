"""Interval exclusion and Newton contraction; possible roots are not existence proofs."""
from dataclasses import dataclass
from math import ceil, floor, nextafter, inf
from .intervals import Interval as I, EnclosureUnavailable

@dataclass(frozen=True,slots=True)
class Signal:
    """Closed value and derivative enclosures, with an optional tighter point-value evaluator."""
    value: I
    rate: I | None
    center: I | None = None


@dataclass(frozen=True,slots=True)
class PossibleRoot:
    """Closed time box and angular target that interval exclusion could not eliminate."""
    target: float
    lower: float
    upper: float


@dataclass(frozen=True,slots=True)
class Isolation:
    """Retained possible roots, excluded-domain count and explicit unresolved regions."""
    roots: tuple[PossibleRoot,...]
    unresolved: tuple[tuple[float,float,str],...]
    excluded_intervals: int


def isolate(signal,start,end,*,targets=(0.,),period=None,step=1.,tolerance=.1,meter,on_exclude=None,on_retain=None):
    """Cover a finite range by proved zero-free intervals and retained boxes."""
    if not start<end or step<=0 or tolerance<=0:
        raise ValueError('positive isolation domain, step and tolerance required')
    roots,unresolved=[],[]
    excluded=0
    stack=[]
    a=start
    while a<end:
        b=min(end,a+step)
        stack.append((a,b,None,0))
        a=b
    stack.reverse()
    minimum=tolerance/86400
    while stack:
        a,b,pinned,depth=stack.pop()
        meter.tick('evaluations')
        meter.tick('root_iterations')
        mid=(a+b)/2
        candidates=()
        reason='event_interval_resolution_exhausted'
        try:
            box=signal(a,b,True)
            # Periodic signals may choose a different continuous lift after
            # subdivision (359..361 becomes -1..1). A numeric target pinned
            # in the parent's lift must never exclude that same child ray.
            if pinned is None or period is not None:
                candidates=tuple(t+turn*period for t in targets for turn in
                    range(ceil((box.value.lo-t)/period),floor((box.value.hi-t)/period)+1)) if period else tuple(t for t in targets if box.value.lo<=t<=box.value.hi)
            else:
                candidates=(pinned,) if box.value.lo<=pinned<=box.value.hi else ()
            if not candidates:
                excluded+=1
                if on_exclude is not None:
                    on_exclude(a,b,'value',box,None)
                continue
            # Precision only where the coefficient-norm enclosure overlaps a
            # requested ray. No native sampled value establishes exclusion.
            if len(candidates)==1:
                target=candidates[0]
                box=signal(a,b,False)
                if period is not None:
                    # Refinement itself can choose another angular lift (for
                    # example +180 becomes -180 after precise nutation). Keep
                    # the same ray, not the coarse numerical representation.
                    target += period*floor(((box.value.lo+box.value.hi)/2-target)/period+.5)
                if not box.value.lo<=target<=box.value.hi:
                    excluded+=1
                    if on_exclude is not None:
                        on_exclude(a,b,'value',box,None)
                    continue
                if b-a<=minimum:
                    if on_retain is not None:
                        on_retain('candidate',a,b)
                    roots.append(PossibleRoot(target,a,b))
                    continue
                if box.center is not None and box.rate is not None and (box.rate.lo>0 or box.rate.hi<0):
                    # The FULL domain's branch-center hull is essential. A
                    # fresh point call can discard early-stop branches that
                    # are selected elsewhere in this interval.
                    newton=mid-(box.center-target)/box.rate
                    lo,hi=max(a,newton.lo),min(b,newton.hi)
                    if lo>hi:
                        excluded+=1
                        if on_exclude is not None:
                            on_exclude(a,b,'newton_empty',box,(a,b,target,box.center.lo,box.center.hi))
                        continue
                    if hi-lo<.75*(b-a):
                        # Newton gives a necessary possible-root enclosure,
                        # not an existence proof. Re-evaluate even a small
                        # contracted cell: its fresh value enclosure can
                        # exclude a false candidate from the parent's wider
                        # center/branch family.
                        stack.append((lo,hi,target,depth+1))
                        if on_exclude is not None:
                            if a<lo:
                                on_exclude(a,lo,'newton_left_open',box,(a,b,target,box.center.lo,box.center.hi))
                            if hi<b:
                                on_exclude(hi,b,'newton_right_open',box,(a,b,target,box.center.lo,box.center.hi))
                        continue
        except EnclosureUnavailable as exc:
            reason=str(exc)
            if not any(x in reason for x in ('subdivision','requires_split','norm_','denominator')):
                if on_retain is not None:
                    on_retain('unresolved',a,b)
                unresolved.append((a,b,reason))
                continue
        except ValueError as exc:
            if not any(x in str(exc) for x in ('interval denominator','square-root interval','inverse cosine interval')):
                raise
            reason='singular_interval_geometry'
        if b-a<=minimum or depth>=64 or mid in (a,b):
            if on_retain is not None:
                on_retain('unresolved',a,b)
            unresolved.append((a,b,reason))
            continue
        pin=candidates[0] if len(candidates)==1 else pinned
        if 'subdivisions' in meter.counts:
            meter.tick('subdivisions')
        stack.append((mid,b,pin,depth+1))
        stack.append((a,mid,pin,depth+1))
    merged=[]
    if period is not None:
        roots=[PossibleRoot(root.target%period,root.lower,root.upper) for root in roots]
    for root in sorted(roots,key=lambda x:(x.target,x.lower)):
        if merged and merged[-1].target==root.target and root.lower<=nextafter(merged[-1].upper,inf):
            old=merged.pop()
            merged.append(PossibleRoot(root.target,old.lower,max(old.upper,root.upper)))
        else:
            merged.append(root)
    return Isolation(tuple(sorted(merged,key=lambda r:r.lower)),tuple(unresolved),excluded)
