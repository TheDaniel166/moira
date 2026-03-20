from __future__ import annotations

import json
from pathlib import Path

from moira.eclipse import EclipseCalculator


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_nasa_solar_eclipse_maxima_classify_correctly_across_eras() -> None:
    """
    Validate solar-eclipse classification at NASA catalog maxima over a wide era span.

    These cases come from the NASA Five Millennium Catalog and deliberately span:
    - ancient/BCE
    - classical/medieval
    - modern
    - far future
    """
    calc = EclipseCalculator()
    fixture = _load_fixture()
    failures: list[str] = []
    kind_map = {
        "H": "is_hybrid",
        "T": "is_total",
        "A": "is_annular",
        "P": "is_partial",
    }

    for row in fixture["solar_maxima"]:
        data = calc.calculate_jd(float(row["ut_jd"]))
        expected_attr = kind_map[str(row["type"])]
        if not data.is_solar_eclipse or not getattr(data.eclipse_type, expected_attr):
            failures.append(
                f"year={row['year']} type={row['type']} "
                f"jd={float(row['ut_jd']):.9f} got={data.eclipse_type}"
            )

    assert not failures, "NASA solar maxima mismatches:\n" + "\n".join(failures[:20])


def test_nasa_lunar_eclipse_maxima_classify_correctly_across_eras() -> None:
    """
    Validate lunar-eclipse classification at NASA catalog maxima over a wide era span.
    """
    calc = EclipseCalculator()
    fixture = _load_fixture()
    failures: list[str] = []

    for row in fixture["lunar_maxima"]:
        data = calc.calculate_jd(float(row["ut_jd"]))
        eclipse_type = str(row["type"])
        if eclipse_type == "T":
            ok = data.is_lunar_eclipse and data.eclipse_type.is_total
        elif eclipse_type == "P":
            ok = data.is_lunar_eclipse and data.eclipse_type.is_partial
        elif eclipse_type == "N":
            ok = (not data.is_lunar_eclipse) and data.eclipse_type.magnitude_penumbra > 0.0
        else:
            ok = False

        if not ok:
            failures.append(
                f"year={row['year']} type={row['type']} "
                f"jd={float(row['ut_jd']):.9f} got={data.eclipse_type} "
                f"pen_mag={data.eclipse_type.magnitude_penumbra:.6f}"
            )

    assert not failures, "NASA lunar maxima mismatches:\n" + "\n".join(failures[:20])


def test_nasa_eclipse_search_recovers_representative_ancient_and_future_cases() -> None:
    """
    Validate representative ancient/future search cases against NASA maxima.

    These are not treated the same as the Swiss 1900-era corpus. Over very long
    timescales, timing sensitivity to Delta T grows, so this test uses a looser
    tolerance while still requiring the search to land on the right event.
    """
    calc = EclipseCalculator()
    fixture = _load_fixture()
    failures: list[str] = []
    # The current native DE441 eclipse path is materially tighter than the old
    # exploratory envelope. Keep the long-range search slice honest: the ancient
    # cases are now sub-minute, and the future cases are substantially tighter.
    max_error_seconds = 60.0

    for row in fixture["search_cases"]["solar"]:
        event = calc.next_solar_eclipse(float(row["seed_jd"]), kind=str(row["kind"]))
        err_seconds = abs(event.jd_ut - float(row["expected_ut_jd"])) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"solar label={row['label']} kind={row['kind']} "
                f"got={event.jd_ut:.9f} expected={float(row['expected_ut_jd']):.9f} "
                f"err_s={err_seconds:.3f}"
            )

    for row in fixture["search_cases"]["lunar"]:
        event = calc.next_lunar_eclipse(float(row["seed_jd"]), kind=str(row["kind"]))
        err_seconds = abs(event.jd_ut - float(row["expected_ut_jd"])) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"lunar label={row['label']} kind={row['kind']} "
                f"got={event.jd_ut:.9f} expected={float(row['expected_ut_jd']):.9f} "
                f"err_s={err_seconds:.3f}"
            )

    assert not failures, "NASA search mismatches:\n" + "\n".join(failures[:20])
