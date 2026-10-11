"""VV1.23/17.2's two actual Moon traversals; no elapsed-month substitute."""
from ._muhurta_marriage_traditions import row
from ._muhurta_marriage_tradition_sources import VV
from ._muhurta_marriage_rules import measure,_eq,_and,_or,_nnot
from ._muhurta_marriage_context import _history_bands,_band_possibilities,_possibly_malefic
from .muhurta_lagna import _nature
from .panchanga_shuddhi import _sector


def _clearances(history,target,end,jd,*,possible=False):
    return sum(p.planet=='Moon' and p.star_index==target and
        (p.entry.upper_jd_ut1>end.lower_jd_ut1 and p.exit.lower_jd_ut1<=jd if possible else
         p.entry.lower_jd_ut1>end.upper_jd_ut1 and p.exit.upper_jd_ut1<=jd)
        for p in history.passages)


def _mercury(history,passage,jd):
    future=passage.entry.lower_jd_ut1>jd
    start=passage.entry.lower_jd_ut1
    end=passage.exit.upper_jd_ut1 if future else min(jd,passage.exit.upper_jd_ut1)
    target=passage.star_index
    completed=[p for p in history.passages if p.planet=='Moon' and p.star_index==target and p.exit.upper_jd_ut1<=jd]
    if not future and len(completed)>=2:
        start=max(start,completed[-2].entry.lower_jd_ut1)
    if start>=end:
        return False
    spans=history.vedha_spans
    complete=bool(spans and spans[0].interval.start.upper_jd_ut1<=start and spans[-1].interval.end.lower_jd_ut1>=end)
    hits=[]
    for span in spans:
        a,b=span.interval.start,span.interval.end
        if b.upper_jd_ut1<=start or a.lower_jd_ut1>=end or _clearances(history,target,b,jd)>=2:
            continue
        sky={p.planet:p.sidereal_longitude for p in span.planets}
        match=None if 'Mercury' not in sky else _sector(sky['Mercury'],27)==target
        hit=_and((match,_nnot(_nature(sky)['Mercury'])))
        certain=max(a.upper_jd_ut1,start)<min(b.lower_jd_ut1,end) and _clearances(history,target,b,jd,possible=True)<2
        hits.append(_and((hit,True if certain else None)))
    for edge,band in _history_bands(history):
        if edge.upper_jd_ut1<=start or edge.lower_jd_ut1>=end or _clearances(history,target,edge,jd)>=2:
            continue
        samples,signs,moon_bad=_band_possibilities(band)
        if ('Mercury' not in samples or any(_sector(x,27)==target for x in samples['Mercury'])) and _possibly_malefic('Mercury',signs,moon_bad):
            hits.append(None)
    return _or((*hits,False if complete else None))


def findings(e,positions):
    history,jd=e.star_history,e.jd_ut1
    target=None if 'Moon' not in positions else _sector(positions['Moon'],27)
    for planet in ('Sun','Mars','Mercury','Saturn','Rahu','Ketu'):
        passages=[] if history is None else [p for p in history.passages if p.planet==planet]
        before=[p for p in passages if p.exit.upper_jd_ut1<=jd]
        current=[p for p in passages if p.entry.lower_jd_ut1<=jd<=p.exit.upper_jd_ut1]
        after=[p for p in passages if p.entry.lower_jd_ut1>jd]
        selected=before[-1:]+current+after[:1]
        complete=bool(before and current and after and all(a.exit==b.entry for a,b in zip(selected,selected[1:])))
        hits=[]
        values=[]
        for i,passage in enumerate(selected):
            match=_eq(target,passage.star_index)
            trigger=passage.exit if passage.exit.upper_jd_ut1<=jd else passage.entry
            clears=_clearances(history,passage.star_index,trigger,jd)
            possible=_clearances(history,passage.star_index,trigger,jd,possible=True)
            active=passage.entry.upper_jd_ut1<=jd<passage.exit.lower_jd_ut1
            state=True if active else False if clears>=2 else None if possible>=2 else True
            hit=_mercury(history,passage,jd) if planet=='Mercury' and match is not False else state
            hits.append(_and((match,hit)))
            values.extend((measure(f'passage_{i}_star',passage.star_index,'zero_based27'),
                measure(f'passage_{i}_completed_moon_traversals',clears,'count')))
        yield row(VV,'star_history',_or((*hits,False if complete else None)),
            'VV1.23;17.2: nearest previous/current/next passage adapter; two complete Moon traversals',suffix=planet.lower(),values=values)
    # Persistent four-maleﬁc Latta contamination in17.2. Two preceding Moon
    # traversals bound the necessary history; uncertain bands remain possible.
    passages=[] if history is None else [p for p in history.passages if p.planet=='Moon' and p.star_index==target and p.exit.upper_jd_ut1<=jd]
    spans=() if history is None else history.vedha_spans
    complete=bool(len(passages)>=2 and spans and spans[0].interval.start.upper_jd_ut1<=passages[-2].entry.lower_jd_ut1 and spans[-1].interval.end.lower_jd_ut1>=jd)
    for planet,count in (('Mars',3),('Saturn',8),('Sun',12),('Rahu',20)):
        hits=[]
        for span in spans:
            if span.interval.start.lower_jd_ut1>=jd or _clearances(history,target,span.interval.end,jd)>=2:
                continue
            position=next((p.sidereal_longitude for p in span.planets if p.planet==planet),None)
            hit=None if position is None or target is None else (_sector(position,27)+count-1)%27==target
            certain=span.interval.start.upper_jd_ut1<jd and _clearances(history,target,span.interval.end,jd,possible=True)<2
            hits.append(_and((hit,True if certain else None)))
        for edge,band in (() if history is None else _history_bands(history)):
            if edge.lower_jd_ut1>=jd or _clearances(history,target,edge,jd)>=2:
                continue
            samples,_,_=_band_possibilities(band)
            if target is None or planet not in samples or any((_sector(x,27)+count-1)%27==target for x in samples[planet]):
                hits.append(None)
        yield row(VV,'latta_history',_or((*hits,False if complete else None)),
            'VV17.2: four projected stars retain contamination until two complete traversals',suffix=planet.lower(),
            values=(measure('required_clearances',2,'complete_moon_star_passages'),),
            reasons=() if complete else ('two_complete_Moon_traversals_and_full_history_required',))
