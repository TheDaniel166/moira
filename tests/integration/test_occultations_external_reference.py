from __future__ import annotations

import re
from pathlib import Path

from moira.constants import Body
from moira.fixed_stars import fixed_star_at
from moira.occultations import lunar_occultation, lunar_star_occultation


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def _parse_lunar_occultation_local_reference() -> list[dict[str, float | str]]:
    text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    start = text.find("section-descr: swe_lun_occult_when_loc( )")
    end = text.find("\n  TESTCASE", start + 1)
    section = text[start:end if end > 0 else len(text)]

    rows: list[dict[str, float | str]] = []
    for block in re.split(r"(?=\n\s+ITERATION\b)", section):
        def _get(key: str) -> str | None:
            match = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return match.group(1).strip() if match else None

        if _get("iephe") != "2":
            continue
        backward = _get("backward")
        if backward != "0":
            continue
        geolat = _get("geolat")
        geolon = _get("geolon")
        altitude = _get("altitude")
        mid = _get("xxtret[0]")
        ipl = _get("ipl")
        star = _get("star")
        if not all([geolat, geolon, altitude, mid]):
            continue
        if star == "Regulus" or ipl == "3":
            rows.append(
                {
                    "geolat": float(geolat),
                    "geolon": float(geolon),
                    "altitude": float(altitude),
                    "mid": float(mid),
                    "ipl": ipl or "",
                    "star": star or "",
                }
            )
    return rows


def test_lunar_occultations_match_offline_swiss_local_reference() -> None:
    rows = _parse_lunar_occultation_local_reference()
    failures: list[str] = []
    max_error_seconds = 180.0

    for row in rows:
        lat = float(row["geolat"])
        lon = float(row["geolon"])
        elev = float(row["altitude"])
        expected_mid = float(row["mid"])
        jd_start = expected_mid - 0.2
        jd_end = expected_mid + 0.2

        if row["star"]:
            name = str(row["star"])
            sp = fixed_star_at(name, expected_mid)
            events = lunar_star_occultation(
                sp.longitude,
                sp.latitude,
                name,
                jd_start,
                jd_end,
                observer_lat=lat,
                observer_lon=lon,
                observer_elev_m=elev,
            )
            label = name
        else:
            target = Body.VENUS
            events = lunar_occultation(
                target,
                jd_start,
                jd_end,
                observer_lat=lat,
                observer_lon=lon,
                observer_elev_m=elev,
            )
            label = target

        if not events:
            failures.append(f"{label}: no event found near {expected_mid:.9f}")
            continue

        event = min(events, key=lambda e: abs(e.jd_mid - expected_mid))
        err_seconds = abs(event.jd_mid - expected_mid) * 86400.0
        if err_seconds > max_error_seconds:
            failures.append(
                f"{label}: expected={expected_mid:.9f} got={event.jd_mid:.9f} "
                f"err_s={err_seconds:.3f}"
            )

    assert not failures, "Occultation mismatches:\n" + "\n".join(failures[:20])
