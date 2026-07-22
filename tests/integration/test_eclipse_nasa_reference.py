from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1, _ut1_to_ephemeris_tt
from moira.eclipse_contacts import find_lunar_contacts
from moira.eclipse_search import refine_minimum
from moira.julian import decimal_year_from_jd, julian_day, ut_to_tt_nasa_canon

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"
LUNAR_CENTURY_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "eclipse_nasa_lunar_1901_2000.json"
)
_MONTH_NUMBER = {
    name: index
    for index, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}

# Cross-authority regression envelopes, not accuracy or uncertainty bounds.
ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS = 360.0
FUTURE_TT_SEARCH_TOLERANCE_SECONDS = 60.0


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_lunar_century_fixture() -> dict:
    return json.loads(LUNAR_CENTURY_FIXTURE_PATH.read_text(encoding="utf-8"))


def _jd_from_iso_seconds(value: str) -> float:
    date_part, time_part = value.split("T", 1)
    year, month, day = (int(part) for part in date_part.split("-"))
    hour, minute, second = (int(part) for part in time_part.split(":"))
    return julian_day(year, month, day, hour + minute / 60.0 + second / 3600.0)


def test_nasa_solar_fixture_keeps_catalog_td_and_se_search_ut_explicit() -> None:
    fixture = _load_fixture()
    assert "TD/TDT" in fixture["source"]["maxima_date_note"]
    assert "se_search_ut_date" in fixture["source"]["solar_se_search_note"]

    sourced_rows = [row for row in fixture["solar_maxima"] if "source_url" in row]
    assert len(sourced_rows) >= 7
    for row in sourced_rows:
        source_url = str(row["source_url"])
        assert source_url.startswith(
            "https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl="
        )
        assert "+" not in source_url
        assert source_url.rsplit("=", 1)[1].isdigit()

        catalog_td_jd = _jd_from_iso_seconds(str(row["date"]))
        catalog_delta_t_s = (
            catalog_td_jd - float(row["ut_jd"])
        ) * 86400.0
        assert catalog_delta_t_s == pytest.approx(
            float(row["delta_t_s"]),
            abs=0.51,
        )

    path_rows = fixture["solar_path_products"]
    assert len(path_rows) == 4
    assert {str(row["kind"]) for row in path_rows} == {
        "partial",
        "total",
        "hybrid",
        "annular",
    }
    for row in path_rows:
        source_url = str(row["source_url"])
        assert source_url.startswith(
            "https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl="
        )
        assert "+" not in source_url
        assert source_url.rsplit("=", 1)[1].isdigit()

    se_search_rows = [row for row in sourced_rows if "se_search_ut_jd" in row]
    assert {str(row["type"]) for row in se_search_rows} == {"H", "T", "A", "P"}
    for row in se_search_rows:
        assert float(row["se_search_ut_jd"]) == pytest.approx(
            _jd_from_iso_seconds(str(row["se_search_ut_date"])),
            abs=1.0e-12,
        )
        se_search_delta_t_s = (
            _jd_from_iso_seconds(str(row["date"]))
            - float(row["se_search_ut_jd"])
        ) * 86400.0
        assert se_search_delta_t_s == pytest.approx(
            float(row["se_search_delta_t_s"]),
            abs=0.51,
        )


def test_nasa_solar_eclipse_maxima_classify_correctly_across_eras(eclipse_calculator) -> None:
    """
    Validate solar-eclipse classification at NASA catalog maxima over a wide era span.

    These cases come from the NASA Five Millennium Catalog and deliberately span:
    - ancient/BCE
    - classical/medieval
    - modern
    - far future
    """
    fixture = _load_fixture()
    failures: list[str] = []
    kind_map = {
        "H": "is_hybrid",
        "T": "is_total",
        "A": "is_annular",
        "P": "is_partial",
    }

    for row in fixture["solar_maxima"]:
        data = eclipse_calculator.calculate_jd(float(row["ut_jd"]))
        expected_attr = kind_map[str(row["type"])]
        if not data.is_solar_eclipse or not getattr(data.eclipse_type, expected_attr):
            failures.append(
                f"year={row['year']} type={row['type']} "
                f"jd={float(row['ut_jd']):.9f} got={data.eclipse_type}"
            )

    assert not failures, "NASA solar maxima mismatches:\n" + "\n".join(failures[:20])


@pytest.mark.slow
def test_modern_solar_search_matches_nasa_se_search_ut_within_one_second(
    eclipse_calculator,
) -> None:
    """Compare four event classes to NASA's separately published UT labels."""

    kind_map = {"H": "hybrid", "T": "total", "A": "annular", "P": "partial"}
    rows = [
        row
        for row in _load_fixture()["solar_maxima"]
        if 1999 <= int(row["year"]) <= 2005
    ]
    assert {str(row["type"]) for row in rows} == {"H", "T", "A", "P"}

    for row in rows:
        expected = float(row["se_search_ut_jd"])
        event = eclipse_calculator.next_solar_eclipse(
            expected - 40.0,
            kind=kind_map[str(row["type"])],
        )
        residual_seconds = abs(event.jd_ut - expected) * 86400.0
        assert residual_seconds <= 1.0, (
            f"{row['se_search_ut_date']} {row['type']} residual {residual_seconds:.6f}s"
        )


@pytest.mark.slow
def test_next_hybrid_search_crosses_the_former_private_lunation_horizon(
    eclipse_calculator,
) -> None:
    row = next(
        row
        for row in _load_fixture()["solar_maxima"]
        if int(row["year"]) == 2049 and str(row["type"]) == "H"
    )

    event = eclipse_calculator.next_solar_eclipse(
        julian_day(2032, 1, 1),
        kind="hybrid",
    )

    assert event.data.eclipse_type.is_hybrid
    # DE441 versus NASA's VSOP87/ELP2000-82 product: classification and search
    # identity are primary here; 30 s is the named cross-model timing envelope.
    assert abs(event.jd_ut - float(row["ut_jd"])) * 86400.0 <= 30.0


def test_nasa_lunar_eclipse_maxima_classify_correctly_across_eras(eclipse_calculator) -> None:
    """
    Validate lunar-eclipse classification at NASA catalog maxima over a wide era span.
    """
    fixture = _load_fixture()
    failures: list[str] = []

    for row in fixture["lunar_maxima"]:
        data = eclipse_calculator.calculate_jd(float(row["ut_jd"]))
        eclipse_type = str(row["type"])
        if eclipse_type == "T":
            ok = data.is_lunar_eclipse and data.eclipse_type.is_total
        elif eclipse_type == "P":
            ok = data.is_lunar_eclipse and data.eclipse_type.is_partial
        elif eclipse_type == "N":
            ok = (
                data.is_lunar_eclipse
                and str(data.eclipse_type) == "Penumbral"
                and data.eclipse_type.magnitude_penumbra > 0.0
            )
        else:
            ok = False

        if not ok:
            failures.append(
                f"year={row['year']} type={row['type']} "
                f"jd={float(row['ut_jd']):.9f} got={data.eclipse_type} "
                f"pen_mag={data.eclipse_type.magnitude_penumbra:.6f}"
            )

    assert not failures, "NASA lunar maxima mismatches:\n" + "\n".join(failures[:20])


def test_nasa_twentieth_century_lunar_catalog_classifies_at_every_tt_maximum(
    eclipse_calculator,
) -> None:
    """Classify all 229 official 1901-2000 catalog rows on one TT basis."""

    fixture = _load_lunar_century_fixture()
    source = fixture["source"]
    assert source["authority"] == "NASA/GSFC Five Millennium Catalog of Lunar Eclipses"
    assert source["catalog_time_scale"] == "TD/TT"
    assert source["shadow_enlargement"] == "Danjon"
    assert source["row_count"] == 229

    expected_counts = Counter({"N": 83, "P": 65, "T": 81})
    actual_counts: Counter[str] = Counter()
    failures: list[str] = []
    for row in fixture["rows"]:
        year_text, month_text, day_text = str(row["date"]).split("-")
        hour, minute, second = (
            int(part) for part in str(row["greatest_td"]).split(":")
        )
        expected_tt = julian_day(
            int(year_text),
            _MONTH_NUMBER[month_text],
            int(day_text),
            hour + minute / 60.0 + second / 3600.0,
        )
        native_ut1 = _ephemeris_tt_to_ut1(
            expected_tt,
            eclipse_calculator._reader,
        )
        data = eclipse_calculator.calculate_jd(native_ut1)
        if data.eclipse_type.is_total:
            actual_type = "T"
        elif data.eclipse_type.is_partial:
            actual_type = "P"
        elif data.is_lunar_eclipse and data.eclipse_type.magnitude_penumbra > 0.0:
            actual_type = "N"
        else:
            actual_type = "-"
        expected_type = str(row["type_code"])[0]
        actual_counts[actual_type] += 1
        if actual_type != expected_type:
            failures.append(
                f"catalog={row['catalog_number']} date={row['date']} "
                f"expected={expected_type} got={actual_type} data={data.eclipse_type}"
            )

    assert len(fixture["rows"]) == 229
    assert actual_counts == expected_counts
    assert not failures, "NASA lunar century classification mismatches:\n" + "\n".join(
        failures[:20]
    )


def test_1988_total_penumbral_boundary_keeps_search_and_geometry_consistent(
    eclipse_calculator,
) -> None:
    """Keep NASA's Danjon-classified 1988 Mar 03 boundary event penumbral.

    NASA/GSFC publishes this event as penumbral under the same Danjon shadow
    enlargement admitted by Moira, with umbral magnitude -0.0017.  The native
    public search, event geometry, and contact family must therefore agree that
    the Moon does not enter the umbra.

    Source: https://eclipse.gsfc.nasa.gov/LEcat5/LE1901-2000.html
    Shadow-policy cross-check: https://eclipse.gsfc.nasa.gov/LEcat5/shadow.html
    """

    expected_tt = julian_day(1988, 3, 3, 16.0 + 13.0 / 60.0 + 41.0 / 3600.0)
    event = eclipse_calculator.next_lunar_eclipse(
        julian_day(1988, 3, 1),
        kind="any",
    )

    event_tt = _ut1_to_ephemeris_tt(event.jd_ut, eclipse_calculator._reader)
    assert abs(event_tt - expected_tt) * 86400.0 <= 120.0
    assert event.data.is_lunar_eclipse
    assert str(event.data.eclipse_type) == "Penumbral"
    assert not event.data.eclipse_type.is_partial
    assert event.data == eclipse_calculator.calculate_jd(event.jd_ut)

    contacts = find_lunar_contacts(eclipse_calculator, event.jd_ut)
    assert contacts.p1 < contacts.greatest < contacts.p4
    assert contacts.u1 is None
    assert contacts.u2 is None
    assert contacts.u3 is None
    assert contacts.u4 is None

    partial = eclipse_calculator.next_lunar_eclipse(
        julian_day(1988, 3, 1),
        kind="partial",
    )
    assert partial.jd_ut - event.jd_ut > 20.0


@pytest.mark.parametrize(
    ("year", "month", "day", "td_hour", "td_minute", "td_second"),
    (
        pytest.param(1922, 3, 13, 11, 28, 48, id="1922 outer penumbral"),
        pytest.param(1940, 3, 23, 19, 48, 19, id="1940 outer penumbral"),
    ),
)
def test_outer_penumbral_events_are_not_cut_off_by_syzygy_discovery_bound(
    eclipse_calculator,
    year: int,
    month: int,
    day: int,
    td_hour: int,
    td_minute: int,
    td_second: int,
) -> None:
    """Admit physical penumbral overlap beyond the old 1.5-degree shortcut.

    NASA/GSFC classifies both rows as penumbral under Danjon enlargement.  The
    published greatest field is TD, so the snapshot check first maps it onto
    Moira's reader-bound UT1 clock before evaluating native geometry.

    Source: https://eclipse.gsfc.nasa.gov/LEcat5/LE1901-2000.html
    """

    expected_tt = julian_day(
        year,
        month,
        day,
        td_hour + td_minute / 60.0 + td_second / 3600.0,
    )
    expected_ut1 = _ephemeris_tt_to_ut1(
        expected_tt,
        eclipse_calculator._reader,
    )
    snapshot = eclipse_calculator.calculate_jd(expected_ut1)
    event = eclipse_calculator.next_lunar_eclipse(
        julian_day(year, month, day) - 2.0,
    )

    assert snapshot.is_lunar_eclipse
    assert str(snapshot.eclipse_type) == "Penumbral"
    assert abs(event.jd_ut - julian_day(year, month, day)) < 2.0
    assert str(event.data.eclipse_type) == "Penumbral"


@pytest.mark.slow
def test_native_lunar_physical_moon_policy_has_lower_tt_residual_across_reference_eras(
    eclipse_calculator,
) -> None:
    """Corroborate the physical-Moon doctrine against every admitted NASA row.

    This is cross-model timing evidence, not a claim that NASA defines Moira's
    vector policy.  The light-time-retarded Moon is retained here only as an
    explicitly named apparent-state comparator.
    """

    for row in _load_fixture()["lunar_maxima"]:
        expected_tt = float(row["ut_jd"]) + float(row["delta_t_s"]) / 86400.0
        physical_ut1 = eclipse_calculator._refine_lunar_maximum(float(row["ut_jd"]))
        apparent_ut1 = refine_minimum(
            lambda jd: eclipse_calculator._lunar_shadow_axis_distance_km(
                jd,
                retarded_moon=True,
            ),
            float(row["ut_jd"]),
            window_days=0.125,
            tol_days=1.0e-7,
            max_iter=100,
        )
        physical_residual_s = abs(
            _ut1_to_ephemeris_tt(physical_ut1, eclipse_calculator._reader)
            - expected_tt
        ) * 86400.0
        apparent_residual_s = abs(
            _ut1_to_ephemeris_tt(apparent_ut1, eclipse_calculator._reader)
            - expected_tt
        ) * 86400.0

        assert physical_residual_s < apparent_residual_s, (
            f"year={row['year']} type={row['type']} physical={physical_residual_s:.3f}s "
            f"apparent={apparent_residual_s:.3f}s"
        )


@pytest.mark.slow
def test_danjon_shadow_boundary_catalog_rows_do_not_flip_public_event_identity(
    eclipse_calculator,
) -> None:
    """Exercise NASA's post-reform Danjon/Chauvenet classification boundaries.

    The first corpus contains events that Chauvenet classifies partial but the
    admitted Danjon model classifies penumbral.  The second contains events that
    Chauvenet admits as shallow penumbral eclipses but Danjon excludes entirely.

    Source: https://eclipse.gsfc.nasa.gov/LEcat5/shadow.html
    """

    danjon_penumbral = (
        (1900, 6, 13),
        (1988, 3, 3),
        (2042, 9, 29),
        (2429, 12, 11),
        (2581, 10, 13),
        (2678, 8, 24),
        (2733, 8, 17),
    )
    danjon_no_eclipse = (
        (1864, 4, 22),
        (1872, 6, 21),
        (1882, 10, 26),
        (1951, 2, 21),
        (2016, 8, 18),
        (2042, 10, 28),
        (2194, 3, 7),
        (2219, 4, 30),
        (2288, 2, 18),
    )

    for year, month, day in danjon_penumbral:
        target = julian_day(year, month, day)
        forward = eclipse_calculator.next_lunar_eclipse(target - 2.0)
        backward = eclipse_calculator.previous_lunar_eclipse(target + 2.0)
        for event in (forward, backward):
            assert abs(event.jd_ut - target) < 2.0
            assert str(event.data.eclipse_type) == "Penumbral"
            assert event.data == eclipse_calculator.calculate_jd(event.jd_ut)

    for year, month, day in danjon_no_eclipse:
        target = julian_day(year, month, day)
        forward = eclipse_calculator.next_lunar_eclipse(target - 2.0)
        backward = eclipse_calculator.previous_lunar_eclipse(target + 2.0)
        assert forward.jd_ut - target > 20.0
        assert target - backward.jd_ut > 20.0


def test_nasa_eclipse_search_recovers_representative_ancient_and_future_cases(eclipse_calculator) -> None:
    """
    Compare representative searches in TT while preserving each time policy.

    The NASA reference TT is its catalog UT1 plus the catalog's published
    Delta-T value.  The Moira result TT is its event UT1 transformed by Moira's
    default Delta-T policy.  This keeps the comparison on a common dynamical
    scale without pretending that the two products share an Earth-rotation
    model.

    The ancient 360-second limit is a cross-authority regression envelope, not
    an accuracy or historical-uncertainty claim.  The post-2150 60-second TT
    search/geometry limit remains independently enforced; it does not validate
    Moira's future UT1 scenario.  Exact residuals are computed by this test and
    deliberately are not frozen in prose.
    """
    fixture = _load_fixture()
    failures: list[str] = []

    for family, method_name in (
        ("solar", "next_solar_eclipse"),
        ("lunar", "next_lunar_eclipse"),
    ):
        maxima = fixture[f"{family}_maxima"]
        search = getattr(eclipse_calculator, method_name)
        for row in fixture["search_cases"][family]:
            expected_ut1 = float(row["expected_ut_jd"])
            event = search(float(row["seed_jd"]), kind=str(row["kind"]))
            catalog_row = min(
                maxima,
                key=lambda candidate: abs(float(candidate["ut_jd"]) - expected_ut1),
            )
            assert float(catalog_row["ut_jd"]) == pytest.approx(
                expected_ut1,
                abs=1.0e-12,
            )

            catalog_delta_t_seconds = float(catalog_row["delta_t_s"])
            expected_tt = expected_ut1 + catalog_delta_t_seconds / 86400.0
            event_tt = _ut1_to_ephemeris_tt(
                event.jd_ut,
                eclipse_calculator._reader,
            )
            moira_delta_t_seconds = (event_tt - event.jd_ut) * 86400.0
            error_seconds = abs(event_tt - expected_tt) * 86400.0

            case_class = str(row["label"]).partition("_")[0]
            if case_class == "ancient":
                tolerance_seconds = ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS
                evidence_class = "ancient cross-authority regression"
            elif case_class == "future":
                assert int(catalog_row["year"]) > 2150, (
                    f"future case {row['label']!r} must remain beyond Moira's "
                    "2150 forecast-validation boundary"
                )
                tolerance_seconds = FUTURE_TT_SEARCH_TOLERANCE_SECONDS
                evidence_class = "post-2150 TT search/geometry"
            else:
                raise AssertionError(
                    f"search case {row['label']!r} has no admitted TT tolerance class"
                )

            if error_seconds > tolerance_seconds:
                failures.append(
                    f"{family} label={row['label']} kind={row['kind']} "
                    f"evidence={evidence_class!r} scale=TT "
                    f"got_tt={event_tt:.9f} expected_tt={expected_tt:.9f} "
                    f"got_ut1={event.jd_ut:.9f} expected_ut1={expected_ut1:.9f} "
                    f"moira_delta_t_s={moira_delta_t_seconds:.3f} "
                    f"catalog_delta_t_s={catalog_delta_t_seconds:.3f} "
                    f"err_s={error_seconds:.3f} limit_s={tolerance_seconds:.1f}"
                )

    assert not failures, "NASA search mismatches:\n" + "\n".join(failures[:20])


def test_ancient_lunar_total_native_and_nasa_compat_paths_use_declared_tt_bases(eclipse_calculator) -> None:
    """
    Keep native and NASA-compatible lunar timing on their declared TT bases.

    Raw UT1 residuals cannot rank these paths because each owns a different
    UT1-to-TT mapping.  This test therefore converts the native event with the
    default Moira policy and the compatibility event with NASA canon Delta-T,
    then compares both with catalog TT.  The shared 360-second limit is a
    regression/corroboration envelope, not a claim that either path is accurate
    to six minutes at this epoch.
    """
    fixture = _load_fixture()
    row = next(case for case in fixture["search_cases"]["lunar"] if case["label"] == "ancient_total")
    expected_ut1 = float(row["expected_ut_jd"])
    catalog_row = min(
        fixture["lunar_maxima"],
        key=lambda candidate: abs(float(candidate["ut_jd"]) - expected_ut1),
    )
    assert float(catalog_row["ut_jd"]) == pytest.approx(expected_ut1, abs=1.0e-12)

    expected_tt = expected_ut1 + float(catalog_row["delta_t_s"]) / 86400.0
    kind = str(row["kind"])
    seed = float(row["seed_jd"])

    native = eclipse_calculator.next_lunar_eclipse(seed, kind=kind)
    canon = eclipse_calculator.next_lunar_eclipse_canon(seed, kind=kind)

    native_error_seconds = abs(
        _ut1_to_ephemeris_tt(native.jd_ut, eclipse_calculator._reader)
        - expected_tt
    ) * 86400.0
    canon_error_seconds = abs(
        ut_to_tt_nasa_canon(
            canon.jd_ut,
            decimal_year_from_jd(canon.jd_ut),
        )
        - expected_tt
    ) * 86400.0

    assert native_error_seconds <= ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS, (
        f"ancient_total native TT residual {native_error_seconds:.3f}s exceeds "
        f"{ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS:.1f}s cross-authority "
        "regression envelope"
    )
    assert canon_error_seconds <= ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS, (
        f"ancient_total NASA-compatible TT residual {canon_error_seconds:.3f}s "
        f"exceeds {ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS:.1f}s "
        "cross-authority regression envelope"
    )


