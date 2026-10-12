"""Complete candidate retention and bounded composition for Gochar windows."""
from dataclasses import replace
from functools import lru_cache
from math import floor, ulp
import json

from ._event_search.budgets import WorkMeter
from ._event_search.resources import borrow_reader
from ._event_search.intervals import EnclosureUnavailable, Interval as I
from ._event_search.isolation import isolate
from ._gochara_window_astronomy import GocharaWindowAstronomy
from ._gochara_window_partition import partition
from ._ephemeris_time import _EphemerisTimeBasisError
from .spk_reader import get_reader, use_reader_override, OutOfRangeError, MissingKernelError
from .gochara import GOCHARA_PLANETS
from .gochara_dated import _epoch, GocharaResourceError, GocharaCoverageError
from .gochara_windows import (
    GocharaWindowResult, GocharaNatalContext, GocharaWindowState,
    GocharaWindowSample, GocharaIngressEvent, GocharaExclusionEvidence,
    GocharaWindowUnresolvedError, GocharaWindowDomainError,
    _state_planets, _wire, window_json_bytes,
)


def _shift_signal(box, target):
    """Align a fresh periodic lift with the retained root's ray."""
    center = (box.value.lo+box.value.hi)/2
    return target+360*floor((center-target)/360+.5)


def classify_root(signal, root, start, end, tolerance, planet, index):
    """Existence by strict endpoint brackets, uniqueness by derivative sign.

    A narrow possible-root enclosure alone establishes neither. The certificate
    applies to each continuous surrogate branch of the declared roundoff model;
    it does not count discontinuous binary64 sign flips inside the retained band.
    """
    target = root.target % 360
    pad = max(4*max(ulp(root.lower), ulp(root.upper)),
              (tolerance/86400-(root.upper-root.lower))*.45)
    a, b = max(start, root.lower-pad), min(end, root.upper+pad)
    reason = "root_existence_or_multiplicity_unresolved"
    direction = None
    left = right = whole = None
    try:
        whole = signal(a,b,False)
        if whole.center is not None and whole.rate is not None:
            # Keep the FULL interval's rounding/early-stop branch family at
            # both endpoints. Fresh point calls have smaller guards and can
            # drop branches; they cannot establish this family's existence.
            mid = (a+b)/2
            left = whole.center+whole.rate*(I.point(a)-mid)
            right = whole.center+whole.rate*(I.point(b)-mid)
            ray = _shift_signal(whole,target)
            if whole.rate.lo > 0 and left.hi < ray and right.lo > ray:
                direction = 1
            elif whole.rate.hi < 0 and left.lo > ray and right.hi < ray:
                direction = -1
        if (b-a)*86400 > tolerance:
            # Existence and unique direction are independent of whether the
            # merged numerical uncertainty meets the requested time width.
            reason = "boundary_width_exceeds_requested_tolerance"
    except EnclosureUnavailable as exc:
        reason = str(exc)
    return GocharaIngressEvent(index, planet, target, a, b,
        "crossing" if direction is not None else "possible_contact", direction,
        1 if direction is not None else None,
        () if direction is not None and (b-a)*86400 <= tolerance else (reason,),
        a == start, b == end,
        None if left is None else (left.lo,left.hi),
        None if right is None else (right.lo,right.hi),
        None if whole is None or whole.rate is None else (whole.rate.lo,whole.rate.hi),
        whole is not None and whole.center is not None)


def search_windows(natal_jd, start, end, location, policy, search, subjects, reader):
    """One request's readers, caches, natal context, proofs and final wire size."""
    kinds = ("evaluations", "reader_calls", "root_iterations", "subdivisions",
             "events", "cells", "samples", "evidence", "output_bytes")
    from .gochara_windows import GocharaWindowBudgetError
    meter = WorkMeter(search.limits, budget_error=GocharaWindowBudgetError, kinds=kinds)
    def account(value):
        # Each retained record is charged before appending it. These disjoint
        # record bytes are a lower bound on the final payload; the completed
        # canonical encoding supplies the final check, without double charging.
        meter.tick("output_bytes", len(json.dumps(_wire(value), ensure_ascii=False,
            allow_nan=False,separators=(",", ":")).encode("utf-8")))
    stage = "reader"
    try:
        owner = get_reader() if reader is None else reader
        with borrow_reader(owner, meter) as bound, use_reader_override(bound):
            stage = meter.stage = "natal"
            natal = GocharaNatalContext(_epoch(natal_jd,bound,policy),policy,location)
            account(natal)
            stage = meter.stage = "astronomy_preflight"
            astronomy = GocharaWindowAstronomy(bound,meter,policy,start,end)
            # Point preflight verifies both ends against required apparent-place
            # retarded epochs; interior holes remain explicit during isolation.
            sample_epoch = lru_cache(maxsize=4096)(lambda t: _epoch(t,bound,policy))
            sample_epoch(start)
            sample_epoch(end)
            events, gaps, evidence = [], [], []
            for planet in GOCHARA_PLANETS:
                stage = meter.stage = "isolation:"+planet
                def signal(a,b,coarse):
                    return astronomy.signal(planet,a,b,coarse)
                def exclude(a,b,method,box,proof):
                    meter.tick("evidence")
                    item = GocharaExclusionEvidence(planet,a,b,method,
                        box.value.lo,box.value.hi,
                        None if box.rate is None else box.rate.lo,
                        None if box.rate is None else box.rate.hi,
                        *((None,)*5 if proof is None else proof))
                    account(item)
                    evidence.append(item)
                def retain(kind,a,b):
                    # Cap retained candidates before the solver allocates an
                    # arbitrarily large list; merged events may be fewer.
                    meter.tick("events" if kind == "candidate" else "evidence")
                found = isolate(signal,start,end,targets=tuple(float(n*30) for n in range(12)),
                    period=360.,step=1.,tolerance=search.boundary_tolerance_seconds*.5,
                    meter=meter,on_exclude=exclude,on_retain=retain)
                gaps.extend((a,b,planet+":"+reason) for a,b,reason in found.unresolved)
                for root in found.roots:
                    event = classify_root(signal,root,start,end,
                        search.boundary_tolerance_seconds,planet,len(events))
                    account(event)
                    events.append(event)
            events = tuple(replace(e,id=i) for i,e in enumerate(sorted(events,
                key=lambda e:(e.lower_jd_ut1, GOCHARA_PLANETS.index(e.planet), e.boundary_degrees))))
            state_ids, states, samples = {}, [], []
            def state_at(t):
                meter.tick("samples")
                epoch = sample_epoch(t)
                signs = tuple(p.position.rashi_index for p in epoch.positions)
                if signs not in state_ids:
                    state_ids[signs] = len(states)
                    item = GocharaWindowState(len(states), signs,
                        _state_planets(natal.snapshot(tuple(p.position.sidereal_longitude for p in epoch.positions))))
                    account(item)
                    states.append(item)
                state = state_ids[signs]
                sample = len(samples)
                item = GocharaWindowSample(sample,state,epoch)
                account(item)
                samples.append(item)
                return state,sample
            stage = meter.stage = "partition"
            regions = partition(start,end,events,gaps,state_at,meter)
            result = GocharaWindowResult(start,end,natal,search,subjects,tuple(states),tuple(samples),
                events,regions,tuple(evidence),astronomy.receipts(),
                tuple((k,v) for k,v in meter.counts.items() if k != "output_bytes"))
            if search.require_resolved and not result.coverage.events_resolved:
                raise GocharaWindowUnresolvedError(
                    tuple(reason for r in regions for reason in r.reasons),
                    result.coverage.unresolved_regions,result.coverage.maximum_band_width_seconds)
            stage = meter.stage = "serialization"
            meter.counts["output_bytes"] = 0
            meter.tick("output_bytes",len(window_json_bytes(result)))
            return result
    except OutOfRangeError as exc:
        raise GocharaCoverageError(f"{stage} is outside planetary kernel coverage") from exc
    except (MissingKernelError,_EphemerisTimeBasisError,LookupError,FileNotFoundError) as exc:
        raise GocharaResourceError(f"required Gochar {stage} resource unavailable") from exc
    except EnclosureUnavailable as exc:
        if "outside_1900_2100" in str(exc):
            raise GocharaWindowDomainError(str(exc)) from exc
        raise GocharaResourceError(f"Gochar interval resource unavailable: {exc}") from exc
