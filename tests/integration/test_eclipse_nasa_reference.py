from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.julian import decimal_year_from_jd, julian_day, ut_to_tt_nasa_canon

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"

# Cross-authority regression envelopes, not accuracy or uncertainty bounds.
ANCIENT_TT_REGRESSION_TOLERANCE_SECONDS = 360.0
FUTURE_TT_SEARCH_TOLERANCE_SECONDS = 60.0


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


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


