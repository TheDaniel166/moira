from __future__ import annotations

import re
from pathlib import Path

from moira.eclipse import EclipseCalculator
from moira.julian import datetime_from_jd


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def _parse_when_maxima(section_name: str) -> list[dict[str, float | int]]:
    text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    start = text.find(f"section-descr: {section_name}( )")
    if start < 0:
        raise ValueError(f"Could not find fixture section {section_name!r}")

    end = text.find("\n  TESTCASE", start + 1)
    if end < 0:
        end = text.find("\nTESTSUITE", start + 1)
    section = text[start:end if end > 0 else len(text)]

    results: list[dict[str, float | int]] = []
    for block in re.split(r"(?=\n\s+ITERATION\b)", section):
        def _get(key: str) -> str | None:
            match = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return match.group(1).strip() if match else None

        iephe = _get("iephe")
        if iephe != "2":
            continue

        ifltype = _get("ifltype")
        max_jd = _get("xxtret[0]")
        if ifltype is None or max_jd is None:
            continue

        results.append({
            "ifltype": int(ifltype),
            "jd_ut": float(max_jd),
        })

    return results


def test_solar_eclipse_maxima_match_offline_swiss_reference() -> None:
    """
    Validate solar-eclipse maxima against cached Swiss reference instants.

    The current Moira eclipse model is geocentric/global rather than a full
    Swiss-style contact solver, so this test anchors the classifier at the
    official maxima times.
    """
    calc = EclipseCalculator()
    failures: list[str] = []

    for row in _parse_when_maxima("swe_sol_eclipse_when_glob"):
        jd_ut = float(row["jd_ut"])
        ifltype = int(row["ifltype"])
        data = calc.calculate(datetime_from_jd(jd_ut))

        if not data.is_solar_eclipse:
            failures.append(f"solar jd={jd_ut:.9f} expected solar eclipse, got {data}")
            continue

        if ifltype == 16 and not data.eclipse_type.is_partial:
            failures.append(
                f"solar jd={jd_ut:.9f} expected partial, got {data.eclipse_type}"
            )
        if ifltype == 4 and not data.eclipse_type.is_total:
            failures.append(
                f"solar jd={jd_ut:.9f} expected total, got {data.eclipse_type}"
            )
        if ifltype == 32 and not data.eclipse_type.is_hybrid:
            failures.append(
                f"solar jd={jd_ut:.9f} expected hybrid, got {data.eclipse_type}"
            )
        if ifltype in {4, 32} and data.eclipse_type.is_partial:
            failures.append(
                f"solar jd={jd_ut:.9f} expected central/non-partial, got {data.eclipse_type}"
            )

    assert not failures, "Solar eclipse mismatches:\n" + "\n".join(failures[:20])


def test_lunar_eclipse_maxima_match_offline_swiss_reference() -> None:
    """
    Validate lunar-eclipse maxima against cached Swiss reference instants.

    Swiss fixture codes used here:
    - 4   = total lunar eclipse
    - 16  = partial lunar eclipse
    - 64  = penumbral lunar eclipse
    """
    calc = EclipseCalculator()
    failures: list[str] = []

    for row in _parse_when_maxima("swe_lun_eclipse_when"):
        jd_ut = float(row["jd_ut"])
        ifltype = int(row["ifltype"])
        data = calc.calculate(datetime_from_jd(jd_ut))

        if ifltype == 4:
            if not (data.is_lunar_eclipse and data.eclipse_type.is_total):
                failures.append(
                    f"lunar jd={jd_ut:.9f} expected total, got {data.eclipse_type}"
                )
        elif ifltype == 16:
            if not (data.is_lunar_eclipse and data.eclipse_type.is_partial):
                failures.append(
                    f"lunar jd={jd_ut:.9f} expected partial, got {data.eclipse_type}"
                )
        elif ifltype == 64:
            if data.is_lunar_eclipse or data.eclipse_type.magnitude_penumbra <= 0.0:
                failures.append(
                    f"lunar jd={jd_ut:.9f} expected penumbral-only, got {data.eclipse_type}"
                )

    assert not failures, "Lunar eclipse mismatches:\n" + "\n".join(failures[:20])


def test_lunar_eclipse_search_matches_offline_swiss_when_reference() -> None:
    """
    Validate next/previous lunar-eclipse search against Swiss `when()` maxima.

    This is the first real event-search validation for Moira's eclipse engine:
    the search starts from the Swiss seed JD, walks by exact full moons, and
    must recover the corresponding Swiss eclipse maximum within the current
    native-model envelope.

    Unlike the solar search path, the native lunar search is intentionally not
    tuned to reproduce Swiss maxima exactly. The current DE441-centric lunar
    model stays within about 90 seconds on this Swiss reference slice while
    still recovering the correct event and classification.
    """
    calc = EclipseCalculator()
    failures: list[str] = []
    kind_map = {4: "total", 16: "partial", 64: "penumbral"}
    max_error_seconds = 90.0

    text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    start = text.find("section-descr: swe_lun_eclipse_when( )")
    end = text.find("\n  TESTCASE", start + 1)
    section = text[start:end]

    rows: list[dict[str, float | int]] = []
    for block in re.split(r"(?=\n\s+ITERATION\b)", section):
        def _get(key: str) -> str | None:
            match = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return match.group(1).strip() if match else None

        if _get("iephe") != "2":
            continue
        jd = _get("jd")
        backward = _get("backward")
        ifltype = _get("ifltype")
        max_jd = _get("xxtret[0]")
        if not all([jd, backward, ifltype, max_jd]):
            continue
        rows.append({
            "jd": float(jd),
            "backward": int(backward),
            "ifltype": int(ifltype),
            "expected": float(max_jd),
        })

    for row in rows:
        kind = kind_map[int(row["ifltype"])]
        if int(row["backward"]):
            event = calc.previous_lunar_eclipse(float(row["jd"]), kind=kind)
        else:
            event = calc.next_lunar_eclipse(float(row["jd"]), kind=kind)

        err_seconds = abs(event.jd_ut - float(row["expected"])) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"kind={kind} backward={int(row['backward'])} "
                f"expected={float(row['expected']):.9f} got={event.jd_ut:.9f} "
                f"err_s={err_seconds:.3f}"
            )

    assert not failures, "Lunar eclipse search mismatches:\n" + "\n".join(failures[:20])


def test_solar_eclipse_search_matches_offline_swiss_when_reference() -> None:
    """
    Validate solar-eclipse search against Swiss `when_glob()` maxima.

    Swiss fixture codes used here:
    - 32  = annular-total (hybrid) solar eclipse
    - 4   = total solar eclipse
    - 16  = partial solar eclipse
    """
    calc = EclipseCalculator()
    failures: list[str] = []
    kind_map = {32: "hybrid", 4: "total", 16: "partial"}
    max_error_seconds = 10.0

    text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    start = text.find("section-descr: swe_sol_eclipse_when_glob( )")
    end = text.find("\n  TESTCASE", start + 1)
    section = text[start:end]

    rows: list[dict[str, float | int]] = []
    for block in re.split(r"(?=\n\s+ITERATION\b)", section):
        def _get(key: str) -> str | None:
            match = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return match.group(1).strip() if match else None

        if _get("iephe") != "2":
            continue
        ifltype = _get("ifltype")
        if ifltype is None or int(ifltype) not in kind_map:
            continue
        jd = _get("jd")
        backward = _get("backward")
        max_jd = _get("xxtret[0]")
        if not all([jd, backward, max_jd]):
            continue
        rows.append({
            "jd": float(jd),
            "backward": int(backward),
            "ifltype": int(ifltype),
            "expected": float(max_jd),
        })

    for row in rows:
        kind = kind_map[int(row["ifltype"])]
        if int(row["backward"]):
            event = calc.previous_solar_eclipse(float(row["jd"]), kind=kind)
        else:
            event = calc.next_solar_eclipse(float(row["jd"]), kind=kind)

        err_seconds = abs(event.jd_ut - float(row["expected"])) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"kind={kind} backward={int(row['backward'])} "
                f"expected={float(row['expected']):.9f} got={event.jd_ut:.9f} "
                f"err_s={err_seconds:.3f}"
            )

    assert not failures, "Solar eclipse search mismatches:\n" + "\n".join(failures[:20])
