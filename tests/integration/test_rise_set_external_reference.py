from __future__ import annotations

from pathlib import Path

import pytest

from moira.rise_set import find_phenomena


_IFLTYPE_TO_EVENT = {
    1: "Rise",
    2: "Set",
    4: "Transit",
    8: "AntiTransit",
}

_MAX_TIMING_ERROR_SECONDS = 10.0
_JD_SECONDS = 86400.0


def _load_swiss_rise_set_cases() -> list[dict[str, object]]:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    in_section = False
    current: dict[str, str] = {}
    cases: list[dict[str, object]] = []

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("section-descr: swe_rise_trans( )"):
            in_section = True
            continue
        if line.startswith("section-descr: swe_rise_trans_true_hor( )"):
            break
        if not in_section:
            continue

        if line == "ITERATION":
            current = {}
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current[key] = value

        if key == "initialize":
            ifltype = int(current["ifltype"].split()[0])
            if ifltype not in _IFLTYPE_TO_EVENT:
                continue

            body_name: str
            if "star" in current:
                body_name = current["star"]
            else:
                ipl_token = current["ipl"].split("#", 1)[1].strip()
                body_name = ipl_token

            cases.append(
                {
                    "body": body_name,
                    "event": _IFLTYPE_TO_EVENT[ifltype],
                    "jd_start": float(current["jd"].split()[0]),
                    "lat": float(current["geolat"].split()[0]),
                    "lon": float(current["geolon"].split()[0]),
                    "expected_jd": float(current["tret"].split()[0]),
                    "altitude": -0.5667,
                }
            )

    return cases


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("case", _load_swiss_rise_set_cases())
def test_rise_set_and_transit_match_swiss_reference(case: dict[str, object]) -> None:
    """
    Legacy regression cross-check against the offline Swiss fixture corpus.

    The cached section covers:
    - Regulus (fixed star)
    - Venus
    - rise, set, upper transit, lower transit

    This test is retained as a regression/sanity suite. The primary truth
    oracle for rise/set/transit timing is the Horizons-based fixture suite,
    with published tables used as supplemental spot checks where available.
    """
    results = find_phenomena(
        str(case["body"]),
        float(case["jd_start"]),
        float(case["lat"]),
        float(case["lon"]),
        altitude=float(case["altitude"]),
    )
    actual = results[str(case["event"])]
    error_seconds = abs(actual - float(case["expected_jd"])) * _JD_SECONDS

    assert error_seconds <= _MAX_TIMING_ERROR_SECONDS
