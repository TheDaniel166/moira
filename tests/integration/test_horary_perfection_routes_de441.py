"""P4 trace and route invariants on DE441 with independently projected vectors.

Each exact contact is re-verified from the equatorial Cartesian product (not the
ecliptic longitude the scanner consumed); each station is checked for a change
of longitude rate. These are geometric/search invariants, not an external
engine comparison or a certificate against unsampled roots.
"""
import math

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.horary_moon import LillyCoverageState
from moira.horary_perfection_routes import (
    LillyBeholdingReading, LillyCollectionReading, LillyDwellingReading, LillyFrustrationReading,
    LillyHeavinessReading, LillyRefranationReading, LillyMalevolentReading, LillyPerfectionReadings,
    LillyPerfectionSearchPolicy, LillyProhibitionReading, LillyRouteState, LillyTranslationReading,
    LILLY_BOOK_II_PRACTICE, lilly_perfection_routes, lilly_perfection_routes_at,
)
from moira.horary_reception import LillySnapshotContext
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from moira.planets import planet_at
from moira.spk_reader import SpkReader

pytestmark = pytest.mark.requires_ephemeris
READINGS = LillyPerfectionReadings(LillyTranslationReading.P126_FULL, LillyProhibitionReading.INTERPOSITION_TO_EITHER,
                                   LillyMalevolentReading.HARD_ASPECT, LillyBeholdingReading.NO_CURRENT_ASPECT,
                                   LillyHeavinessReading.TRADITIONAL_ORDER, LillyRefranationReading.APPLYING_PRINCIPAL,
                                   LillyFrustrationReading.CONJUNCTION_ONLY,
                                   LillyCollectionReading.P126_PRINCIPALS_RECEIVE,
                                   LillyDwellingReading.P126_REJECTED_EXCEPT_LUNAR)
POLICY = LillyPerfectionSearchPolicy(past_days=10., future_days=20.)


@pytest.fixture(scope="module", params=[2451545., 2460310.5], ids=["J2000", "2024"])
def routes(request):
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        result = lilly_perfection_routes_at(LillySnapshotContext(f"DE441-P4-{request.param}", True, request.param),
                                     "Mars", "Venus", reader=reader, readings=READINGS, policy=POLICY)
        yield result, reader


def ecliptic_longitude(body, t, reader):
    # Independent projection of the equatorial Cartesian result.
    p = planet_at(body, t, reader=reader, frame="cartesian")
    eps = math.radians(true_obliquity(ut_to_tt(t)))
    x, y = p.x, p.y * math.cos(eps) + p.z * math.sin(eps)
    return math.degrees(math.atan2(y, x)) % 360.


def test_trace_coverage_and_provenance(routes):
    result, _ = routes
    trace = result.trace
    assert trace.coverage.state is LillyCoverageState.COMPLETE, trace.coverage.reasons
    assert dict(trace.provenance.source_identity)["query_jd_ut1"] == repr(trace.context.jd_ut)
    assert trace.contacts and trace.ingresses
    assert result.verdict is None and result.summary.verdict is None


def test_every_contact_is_exact_in_an_independent_projection(routes):
    result, reader = routes
    worst = 0.
    for c in result.trace.contacts:
        t = c.time.midpoint
        rel = ecliptic_longitude(c.body_a, t, reader) - ecliptic_longitude(c.body_b, t, reader)
        worst = max(worst, abs((rel - c.directed_angle_deg + 180.) % 360. - 180.))
    # Measured 2026-10-30: at most 0.0004 arcsec over 61-62 contacts per epoch.
    assert worst < .01 / 3600.


def test_every_station_changes_the_rate_sign(routes):
    result, reader = routes
    for s in result.trace.stations:
        t, h = s.time.midpoint, .5
        before = (ecliptic_longitude(s.body, t, reader) - ecliptic_longitude(s.body, t - h, reader) + 180.) % 360. - 180.
        after = (ecliptic_longitude(s.body, t + h, reader) - ecliptic_longitude(s.body, t, reader) + 180.) % 360. - 180.
        assert before * after < 0, s
        assert (after < 0) == (s.direction == "retrograde")


def test_route_records_are_consistent(routes):
    result, _ = routes
    ids = {c.event_id for c in result.trace.contacts} | {s.event_id for s in result.trace.stations}
    q = result.trace.context.jd_ut
    for key, record in result.routes:
        if record.state is LillyRouteState.COMPLETE and record.completion is not None:
            assert record.completion.low > q, key
        for leg in record.leg_ids:
            assert leg in ids, (key, leg)
    assert any(key == "mutual_reception" for key, _ in result.routes)


def test_book_ii_readings_on_the_same_trace(routes):
    # The Book II selection re-derives routes from the identical trace; its
    # legs are trace events and nothing completes in the past.
    result, _ = routes
    book = lilly_perfection_routes(result.trace, "Mars", "Venus", readings=LILLY_BOOK_II_PRACTICE)
    assert book.trace is result.trace and book.verdict is None and book.summary.verdict is None
    ids = {c.event_id for c in result.trace.contacts}
    q = result.trace.context.jd_ut
    for key, record in book.routes:
        assert all(leg in ids for leg in record.leg_ids), key
        if record.completion is not None:
            assert record.completion.low > q, key
        if key.startswith("translation:"):
            assert record.reading == "book_ii_practice" and "Book II" in record.source_reference
    assert {k for k, _ in result.routes if not k.startswith(("translation:", "collection:"))} <= dict(book.routes).keys()
