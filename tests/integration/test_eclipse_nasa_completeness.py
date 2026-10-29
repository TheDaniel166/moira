"""Eclipse range-search completeness against NASA's Five Millennium catalogs.

Authority: NASA/GSFC Five Millennium Catalogs of Solar (NASA/TP-2008-214170)
and Lunar (NASA/TP-2009-214173) Eclipses, 1901-2100 extract in
`tests/fixtures/nasa_five_millennium_eclipses_1901_2100.json`, built by
`scripts/build_nasa_eclipse_completeness_fixture.py` from catalog files whose
byte counts and SHA-256 the fixture records.

Product: the set of eclipses returned by `solar_eclipses_in_range` and
`lunar_eclipses_in_range` over a century. Each Moira event must pair with
exactly one catalog event, and each catalog event with exactly one Moira
event. 1901-2000 crosses DE441's 1969 internal segment boundary and so runs
the Python route; 2001-2100 runs the native candidate route.

This is a cross-model comparison. The catalog uses VSOP87/ELP2000-82, its own
Delta T, lunar radius and (lunar) Danjon shadow; Moira uses its DE441 physical
model. Pairing therefore uses a 0.5-day identity window, and the timing gate is
a named cross-model envelope, not an accuracy bound: catalog TD is converted to
UT with the catalog's own Delta T, and the largest measured difference over
1000-2100 CE was 2.7 minutes. Type families must agree except at the declared
classification limits below, where the two models fall on opposite sides of a
boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.julian import julian_day

pytestmark = pytest.mark.requires_ephemeris

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_five_millennium_eclipses_1901_2100.json"
)
PAIRING_WINDOW_DAYS = 0.5
CROSS_MODEL_TIMING_ENVELOPE_SECONDS = 300.0
_MONTH = {
    name: index
    for index, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}
_FAMILY = {
    "Partial": "P",
    "Annular": "A",
    "Total": "T",
    "Hybrid": "H",
    "Penumbral": "N",
}
# Moira's DE441 physical model and the catalog model classify these on
# opposite sides of a type boundary (see VALIDATION_ASTRONOMY.md Section 6.1).
DECLARED_TYPE_LIMITS = {
    ("solar", "1986-Oct-03"): ("A", "H"),  # native magnitude 0.99995; NASA 1.0000, 1 km path
    ("lunar", "2015-Apr-04"): ("P", "T"),  # NASA umbral magnitude 1.0008
}


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _catalog_ut(row: dict) -> float:
    year, month, day = row["date"].split("-")
    hour, minute, second = (int(part) for part in row["greatest_td"].split(":"))
    td = julian_day(int(year), _MONTH[month], int(day), hour + minute / 60.0 + second / 3600.0)
    return td - row["delta_t_s"] / 86400.0


def test_fixture_retains_source_identity_and_century_totals() -> None:
    fixture = _fixture()
    source = fixture["source"]
    assert source["solar"]["sha256"] == (
        "c07e7b5e13af61a1d74eb3bee1a1824a197dc1ca393a3ac2a91c9e73bc2e0c58"
    )
    assert source["lunar"]["sha256"] == (
        "d47586fc9c1c59338f234b3c6634c31744739887169f58d411ac766f3861fcf2"
    )
    assert source["catalog_time_scale"] == "TD/TT"
    assert source["span_td_years"] == [1901, 2100]
    for family, totals in (("solar", (228, 224)), ("lunar", (229, 228))):
        years = [int(row["date"][:4]) for row in fixture[family]]
        assert (sum(year <= 2000 for year in years), sum(year > 2000 for year in years)) == totals


def _assert_century_complete(eclipse_calculator, family: str, first_year: int) -> None:
    start = julian_day(first_year, 1, 1)
    end = julian_day(first_year + 100, 1, 1)
    catalog = [
        (_catalog_ut(row), row)
        for row in _fixture()[family]
        if start <= _catalog_ut(row) < end
    ]
    events = getattr(eclipse_calculator, f"{family}_eclipses_in_range")(start, end)

    unpaired_catalog = list(catalog)
    unpaired_events = []
    timing_failures = []
    type_failures = []
    for event in events:
        match = min(
            unpaired_catalog,
            key=lambda item: abs(item[0] - event.jd_ut),
            default=None,
        )
        if match is None or abs(match[0] - event.jd_ut) > PAIRING_WINDOW_DAYS:
            unpaired_events.append(event.jd_ut)
            continue
        unpaired_catalog.remove(match)
        catalog_ut, row = match
        difference_s = (event.jd_ut - catalog_ut) * 86400.0
        if abs(difference_s) > CROSS_MODEL_TIMING_ENVELOPE_SECONDS:
            timing_failures.append(f"{row['date']}: {difference_s:+.1f} s")
        pair = (_FAMILY[str(event.data.eclipse_type)], row["type_code"][0])
        if pair[0] != pair[1] and DECLARED_TYPE_LIMITS.get((family, row["date"])) != pair:
            type_failures.append(f"{row['date']}: Moira {pair[0]}, NASA {row['type_code']}")

    assert not unpaired_events, f"Moira-only {family} eclipses (UT JD): {unpaired_events}"
    assert not unpaired_catalog, "NASA-only {} eclipses: {}".format(
        family, [row["date"] for _, row in unpaired_catalog]
    )
    assert len(events) == len(catalog)
    assert not timing_failures, timing_failures
    assert not type_failures, type_failures


@pytest.mark.parametrize("family", ["solar", "lunar"])
def test_2001_2100_native_route_recovers_every_catalog_eclipse(eclipse_calculator, family):
    start, end = julian_day(2001, 1, 1), julian_day(2101, 1, 1)
    assert eclipse_calculator._native_eclipse_syzygy_candidates(family, start, end) is not None
    _assert_century_complete(eclipse_calculator, family, 2001)


@pytest.mark.slow
@pytest.mark.parametrize("family", ["solar", "lunar"])
def test_1901_2000_python_route_recovers_every_catalog_eclipse(eclipse_calculator, family):
    # Crossing DE441's 1969 segment boundary forces the Python manuscript,
    # the route that raised on 1986-10-03 before the greatest-point repair.
    start, end = julian_day(1901, 1, 1), julian_day(2001, 1, 1)
    assert eclipse_calculator._native_eclipse_syzygy_candidates(family, start, end) is None
    _assert_century_complete(eclipse_calculator, family, 1901)
