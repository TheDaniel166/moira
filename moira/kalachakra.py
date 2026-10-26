"""Source-owned Kalachakra profiles: exact years, bounded periods and explicit clocks.

The independent source ledger is VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md.
This owner implements longitude balance (46.93), the translator's row repetition,
and chapter 64 natal-row AD rotations. Rao 2000 has its own continuous source
rows, AD windows, Deha/Jeeva and gati decisions; interval materialization is shared.
"""
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from fractions import Fraction as F
import math

from .kalachakra_policy import (
    PROFILE_ID, GROUPS, WEIGHTS, RULERS, CLOCKS,
    KalachakraSource, KalachakraRule, KalachakraConflict, KalachakraProfile,
    KalachakraCatalogue, kalachakra_profiles,
)
from ._kalachakra_recipes import RECIPES, source_row, window, birth_window, transition_reading
from ._kalachakra_types import (
    KalachakraInputError, KalachakraProjectionError, KalachakraCoverageError,
    KalachakraResourceError, KalachakraInvariantError, KalachakraEpoch,
    KalachakraSeed, KalachakraProjection, KalachakraSourceSpan, KalachakraDateSpan,
    KalachakraAstronomy, KalachakraProvenance, KalachakraBirth, KalachakraPeriod,
    KalachakraTransition, KalachakraProjectionReceipt, KalachakraSequence,
    KalachakraActivePeriod, KalachakraCurrent, admit, angle, epoch_jd, number,
    named_ayanamsa, astronomical_epoch,
)

__all__ = [
    "KalachakraSource", "KalachakraRule", "KalachakraConflict", "KalachakraProfile",
    "KalachakraCatalogue", "KalachakraInputError", "KalachakraProjectionError",
    "KalachakraCoverageError", "KalachakraResourceError", "KalachakraInvariantError",
    "KalachakraEpoch", "KalachakraSeed", "KalachakraProjection", "KalachakraSourceSpan",
    "KalachakraDateSpan", "KalachakraAstronomy", "KalachakraProvenance",
    "KalachakraBirth", "KalachakraPeriod", "KalachakraTransition",
    "KalachakraProjectionReceipt", "KalachakraSequence", "KalachakraActivePeriod",
    "KalachakraCurrent", "kalachakra_profiles", "kalachakra_sequence",
    "kalachakra_for_datetime", "project_kalachakra_sequence", "current_kalachakra_periods",
]


def _birth(longitude, profile_id=PROFILE_ID):
    recipe = RECIPES[profile_id]
    lon = F(angle(longitude))
    k = int(lon * F(3,10))
    fraction = (lon-F(10*k,3))*F(3,10)
    nakshatra, pada = k//4+1, k%4+1
    group = next(g for g, members in GROUPS.items() if nakshatra in members)
    row_id = f"{recipe.namespace}{group}/{pada}"
    row = source_row(row_id)
    total = sum(WEIGHTS[s] for s in row)
    elapsed = fraction * total
    cumulative = 0
    for i,sign in enumerate(row):
        right = cumulative + WEIGHTS[sign]
        if elapsed < right:
            remaining = right-elapsed
            full_coverage,deha,jeeva,reference = birth_window(row_id,i)
            return KalachakraBirth(nakshatra,pada,group,row_id,row,fraction,total,
                elapsed,total-elapsed,i,WEIGHTS[sign],remaining,
                full_coverage-(elapsed-cumulative),deha,jeeva,reference)
        cumulative = right
    raise KalachakraInvariantError("uncovered Kalachakra source interval")


def _project_boundary(t, receipt):
    try:
        value = float(F(receipt.birth_jd_utc)+t*receipt.year_days)
    except (OverflowError, ValueError) as exc:
        raise KalachakraProjectionError("projected boundary is not finite") from exc
    if not math.isfinite(value):
        raise KalachakraProjectionError("projected boundary is not finite")
    return value


def _components(birth, levels, projection):
    """Build the bounded source assembly before any clipping or binary projection."""
    i = birth.birth_row_position
    cursor = birth.birth_md_remaining_years-birth.birth_md_full_years
    boundary_cache = {}

    def dates(span, path=None):
        if projection is None or span is None:
            return None
        try:
            for t in (span.start,span.end):
                if t not in boundary_cache:
                    boundary_cache[t] = _project_boundary(t,projection)
            return KalachakraDateSpan(boundary_cache[span.start],boundary_cache[span.end])
        except KalachakraProjectionError as exc:
            raise KalachakraProjectionError(str(exc),path=path) from exc

    periods = []
    for m,(row_id,pos,cycle,sign) in enumerate(window(birth.row_id,i)):
        weight = WEIGHTS[sign]
        full = KalachakraSourceSpan(cursor,cursor+weight)
        visible = KalachakraSourceSpan(max(F(0),cursor),full.end)
        children = []
        if levels == 2:
            child_cursor = full.start
            child_window = window(row_id,pos)
            total = sum(WEIGHTS[s] for _,_,_,s in child_window)
            for a,(child_row,child_pos,_,child_sign) in enumerate(child_window):
                child_weight = WEIGHTS[child_sign]
                child_full = KalachakraSourceSpan(child_cursor,child_cursor+F(weight*child_weight,total))
                child_visible = (KalachakraSourceSpan(max(child_cursor,visible.start),child_full.end)
                    if child_full.end > visible.start else None)
                children.append(KalachakraPeriod((m,a),(m,),child_row,child_pos,cycle,
                    child_sign,RULERS[child_sign],weight,child_weight,total,child_full,child_visible,
                    dates(child_full,(m,a)),dates(child_visible,(m,a)),
                    "visible" if child_visible else "clipped_before_birth","maximum_depth",()))
                child_cursor = child_full.end
            if child_cursor != full.end:
                raise KalachakraInvariantError("AD source partition does not conserve its parent")
        periods.append(KalachakraPeriod((m,),None,row_id,pos,cycle,sign,RULERS[sign],
            1,weight,1,full,visible,dates(full,(m,)),dates(visible,(m,)),"visible",
            "generated" if levels == 2 else "not_requested",tuple(children)))
        cursor = full.end
    coverage = KalachakraSourceSpan(F(0),birth.coverage_years)
    transitions = []
    for siblings in (periods,*(p.children for p in periods)):
        for left,right in zip(siblings,siblings[1:]):
            pair = (left.sign_index,right.sign_index)
            seam = left.row_position == 8 and right.row_position == 0
            status,label,conflicts,rule = transition_reading(left.row_id,left.row_position,pair,seam)
            boundary = left.full_years.end
            transitions.append(KalachakraTransition(left.path,right.path,*pair,
                left.row_position,right.row_position,len(left.path),boundary,
                boundary_cache.get(boundary),seam,F(0) <= boundary < coverage.end,
                status,label,conflicts,rule))
    nodes = tuple(periods)+tuple(c for p in periods for c in p.children)
    return (tuple(periods),tuple(transitions),coverage,dates(coverage),len(nodes),
        sum(p.visible_years is not None for p in nodes))


def _strict_equal(actual,expected):
    """Compare against a bounded expected structure; never recurse along caller shape."""
    if type(actual) is not type(expected):
        return False
    if is_dataclass(expected):
        return all(_strict_equal(getattr(actual,f.name,None),getattr(expected,f.name)) for f in fields(expected))
    if type(expected) is tuple:
        return len(actual) == len(expected) and all(_strict_equal(a,b) for a,b in zip(actual,expected))
    return actual == expected


def _validate_provenance(p):
    if type(p) is not KalachakraProvenance:
        raise KalachakraInputError("invalid seed provenance")
    lon = angle(p.moon_sidereal_lon)
    if type(p.moon_sidereal_lon) is not float:
        raise KalachakraInputError("noncanonical sidereal provenance")
    if p.birth_jd_utc is not None:
        number(p.birth_jd_utc,"birth_jd_utc")
    if p.normalized_datetime_utc is not None:
        if type(p.normalized_datetime_utc) is not str or len(p.normalized_datetime_utc)>40:
            raise KalachakraInputError("invalid civil epoch provenance")
        try:
            dt = datetime.fromisoformat(p.normalized_datetime_utc)
            ep = KalachakraEpoch("datetime",dt)
            if ep.value.isoformat() != p.normalized_datetime_utc or epoch_jd(ep) != p.birth_jd_utc:
                raise KalachakraInputError("inconsistent civil epoch provenance")
        except (ValueError,TypeError) as exc:
            raise KalachakraInputError("invalid civil epoch provenance") from exc
    if p.input_origin == "supplied_sidereal":
        if p.astronomy is not None or p.moon_tropical_lon is not None:
            raise KalachakraInputError("supplied sidereal seed cannot claim astronomical provenance")
        return
    if p.input_origin not in ("supplied_tropical","derived_moon") or p.birth_jd_utc is None:
        raise KalachakraInputError("invalid supplied/derived provenance")
    a = p.astronomy
    if type(a) is not KalachakraAstronomy:
        raise KalachakraInputError("astronomical provenance is required")
    named_ayanamsa(a.ayanamsa_system)
    for name in ("jd_ut1","jd_tt","jd_tdb","delta_t_seconds","delta_t_correction_seconds",
                 "tdb_minus_tt_seconds","lunar_tidal_acceleration","ayanamsa_offset"):
        number(getattr(a,name),name)
    for name in ("delta_t_source","ephemeris_identity","planetary_ephemeris","lunar_ephemeris"):
        value = getattr(a,name)
        if type(value) is not str or not 0 < len(value) <= 256:
            raise KalachakraInputError("missing astronomical resource identity")
    from .sidereal import _STAR_ANCHORED
    expected_anchor = _STAR_ANCHORED.get(a.ayanamsa_system,(None,None))[0]
    if a.anchor != expected_anchor or (a.longitude_frame,a.longitude_origin,a.ayanamsa_mode,a.corrections) != (
        "true_ecliptic_of_date","apparent_geocentric","true",("light_time","aberration","gravitational_deflection","nutation")):
        raise KalachakraInputError("invalid astronomical frame or anchor provenance")
    if (angle(p.moon_tropical_lon,"moon_tropical_lon")-a.ayanamsa_offset)%360 != lon:
        raise KalachakraInputError("inconsistent tropical/sidereal reduction")
    from .julian import utc_to_ut1
    if utc_to_ut1(p.birth_jd_utc) != a.jd_ut1:
        raise KalachakraInputError("UTC and UT1 provenance disagree")
    tolerance = 4*max(math.ulp(a.jd_tt),math.ulp(a.jd_ut1),math.ulp(a.jd_tdb))*86400
    if abs((a.jd_tt-a.jd_ut1)*86400-a.delta_t_seconds) > tolerance or abs((a.jd_tdb-a.jd_tt)*86400-a.tdb_minus_tt_seconds) > tolerance:
        raise KalachakraInputError("astronomical timescale receipt is inconsistent")


def _validate_sequence(result):
    if type(result) is not KalachakraSequence:
        raise KalachakraInputError("result must be KalachakraSequence")
    admit(result.profile_id,result.levels)
    recipe = RECIPES[result.profile_id]
    _validate_provenance(result.provenance)
    birth = _birth(result.provenance.moon_sidereal_lon,result.profile_id)
    receipt = result.projection
    if receipt is not None:
        if type(receipt) is not KalachakraProjectionReceipt:
            raise KalachakraInputError("invalid projection receipt")
        basis = KalachakraProjection(receipt.year_basis).year_basis
        jd = number(receipt.birth_jd_utc,"birth_jd_utc")
        if not _strict_equal(receipt,KalachakraProjectionReceipt(jd,basis,CLOCKS[basis])):
            raise KalachakraInputError("inconsistent projection clock")
        if result.provenance.birth_jd_utc != jd:
            raise KalachakraInputError("projection origin differs from natal provenance")
    expected = _components(birth,result.levels,receipt)
    actual = (result.periods,result.transitions,result.coverage,result.coverage_dates,
              result.generated_node_count,result.visible_node_count)
    metadata = (result.profile_version,result.source_ids,result.rule_ids,result.conflict_ids,
        result.eligibility_status,result.projection_status)
    if not _strict_equal(result.birth,birth) or not _strict_equal(actual,expected) or not _strict_equal(metadata,
        (recipe.version,recipe.source_ids,recipe.rule_ids,recipe.conflict_ids,"not_evaluated",
         "projected" if receipt is not None else "not_requested")):
        raise KalachakraInputError("inconsistent Kalachakra result identity, partition or lineage")


def _assemble(provenance, levels, projection, profile_id):
    try:
        recipe = RECIPES[profile_id]
        birth = _birth(provenance.moon_sidereal_lon,profile_id)
        receipt = None if projection is None else KalachakraProjectionReceipt(
            provenance.birth_jd_utc,projection.year_basis,CLOCKS[projection.year_basis])
        periods,edges,coverage,dates,total,visible = _components(birth,levels,receipt)
        return KalachakraSequence(profile_id,levels,birth,provenance,periods,edges,
            coverage,dates,receipt,total,visible,"projected" if receipt else "not_requested",
            recipe.version,recipe.source_ids,recipe.rule_ids,recipe.conflict_ids)
    except KalachakraProjectionError:
        raise
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        raise KalachakraInvariantError("invalid generated Kalachakra result") from exc


def kalachakra_sequence(seed, *, profile_id, levels=2, birth_epoch=None, projection=None, reader=None):
    """Calculate the selected nine-MD profile from a strictly tagged supplied Moon."""
    jd = admit(profile_id,levels,seed,birth_epoch,projection)
    if seed is None:
        raise KalachakraInputError("seed must be KalachakraSeed")
    normalized = (KalachakraEpoch(birth_epoch.kind,birth_epoch.value).value.isoformat()
        if birth_epoch is not None and birth_epoch.kind == "datetime" else None)
    if seed.basis == "sidereal":
        provenance = KalachakraProvenance("supplied_sidereal",float(seed.moon_longitude),jd,normalized)
    else:
        from ._kalachakra_astronomy import derive
        provenance = derive(birth_epoch,seed.ayanamsa_system,seed.moon_longitude,reader)
    return _assemble(provenance,levels,projection,profile_id)


def kalachakra_for_datetime(birth_dt, *, profile_id, ayanamsa_system, levels=2, projection=None, reader=None):
    """Derive one Moon and one true ayanamsa, then compute the same bounded profile."""
    epoch = KalachakraEpoch("datetime",birth_dt)
    admit(profile_id,levels,birth_epoch=epoch,projection=projection)
    named_ayanamsa(ayanamsa_system)
    astronomical_epoch(epoch)
    from ._kalachakra_astronomy import derive
    return _assemble(derive(epoch,ayanamsa_system,None,reader),levels,projection,profile_id)


def project_kalachakra_sequence(sequence, *, birth_epoch, year_basis):
    """Project a revalidated source sequence; never change an already bound birth."""
    _validate_sequence(sequence)
    jd = epoch_jd(birth_epoch)
    projection = KalachakraProjection(year_basis)
    old = sequence.provenance
    if old.birth_jd_utc is not None and old.birth_jd_utc != jd:
        raise KalachakraInputError("cannot change the natal epoch of a bound seed")
    normalized = (KalachakraEpoch(birth_epoch.kind,birth_epoch.value).value.isoformat()
        if birth_epoch.kind == "datetime" else old.normalized_datetime_utc)
    return _assemble(replace(old,birth_jd_utc=jd,normalized_datetime_utc=normalized),sequence.levels,projection,sequence.profile_id)


def current_kalachakra_periods(schedule, query_epoch):
    """Return the unique active line, or an explicit bounded outside-coverage state."""
    _validate_sequence(schedule)
    query = epoch_jd(query_epoch)
    if schedule.projection is None:
        raise KalachakraInputError("current lookup requires a projected schedule")
    try:
        status,line = _active_line(schedule.periods,schedule.coverage_dates,schedule.levels,query)
        return KalachakraCurrent(schedule.profile_id,schedule.profile_version,schedule.levels,
            schedule.birth,schedule.provenance,schedule.projection,schedule.coverage,
            schedule.coverage_dates,query,status,line,schedule.source_ids,schedule.rule_ids,schedule.conflict_ids)
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        raise KalachakraInvariantError("invalid generated Kalachakra active line") from exc


def _active_line(periods, coverage, levels, query):
    status = "before_birth" if query < coverage.start_jd_utc else "after_coverage" if query >= coverage.end_jd_utc else "active"
    active = []
    if status == "active":
        for p in periods:
            d = p.visible_dates
            if d.start_jd_utc <= query < d.end_jd_utc:
                active.append(p)
                for c in p.children:
                    cd = c.visible_dates
                    if cd is not None and cd.start_jd_utc <= query < cd.end_jd_utc:
                        active.append(c)
                break
        if len(active) != levels:
            raise KalachakraInvariantError("active line does not match generated depth")
    line = tuple(KalachakraActivePeriod(p.path,p.sign_index,p.full_years,p.visible_years,
        p.full_dates,p.visible_dates) for p in active)
    return status,line


def _validate_current(result):
    if type(result) is not KalachakraCurrent:
        raise KalachakraInputError("result must be KalachakraCurrent")
    admit(result.profile_id,result.levels)
    recipe = RECIPES[result.profile_id]
    _validate_provenance(result.provenance)
    if type(result.projection) is not KalachakraProjectionReceipt:
        raise KalachakraInputError("active lookup requires projection provenance")
    receipt = result.projection
    receipt.__post_init__()
    if receipt.birth_jd_utc != result.provenance.birth_jd_utc:
        raise KalachakraInputError("active lookup origin differs from seed origin")
    query = number(result.query_jd_utc,"query_jd_utc")
    birth = _birth(result.provenance.moon_sidereal_lon,result.profile_id)
    periods,_,coverage,dates,_,_ = _components(birth,result.levels,receipt)
    status,line = _active_line(periods,dates,result.levels,query)
    if not _strict_equal((result.birth,result.coverage,result.coverage_dates,result.status,result.active_line,
        result.profile_version,result.source_ids,result.rule_ids,result.conflict_ids,result.eligibility_status),
        (birth,coverage,dates,status,line,recipe.version,recipe.source_ids,recipe.rule_ids,recipe.conflict_ids,"not_evaluated")):
        raise KalachakraInputError("inconsistent active period identity, interval or lineage")
