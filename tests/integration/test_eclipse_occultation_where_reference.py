from __future__ import annotations

import re
from pathlib import Path

import requests
import pytest

from moira.eclipse import EclipseCalculator
from moira.julian import julian_day, ut_to_tt
from moira.occultations import (
    _star_topocentric_target_geometry,
    lunar_star_graze_latitude,
    lunar_star_practical_graze_latitude,
    lunar_star_graze_product_at,
    lunar_star_graze_product_track,
    lunar_star_graze_table,
    lunar_star_graze_circumstances,
    lunar_star_occultation_path_at,
)
from moira.stars import star_at
from moira.lunar_limb import official_lunar_limb_profile_adjustment


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def _parse_where_rows(section_name: str) -> list[dict[str, float | str]]:
    text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    start = text.find(f"section-descr: {section_name}( )")
    if start < 0:
        raise ValueError(f"Could not find fixture section {section_name!r}")

    end = text.find("\n  TESTCASE", start + 1)
    if end < 0:
        end = text.find("\nTESTSUITE", start + 1)
    section = text[start:end if end > 0 else len(text)]

    rows: list[dict[str, float | str]] = []
    for block in re.split(r"(?=\n\s+ITERATION\b)", section):
        def _get(key: str) -> str | None:
            match = re.search(rf"^\s+{re.escape(key)}:\s*([^\n#]+)", block, re.M)
            return match.group(1).strip() if match else None

        if _get("iephe") != "2":
            continue

        jd = _get("jd")
        lon = _get("xxgeopos[0]")
        lat = _get("xxgeopos[1]")
        if not all([jd, lon, lat]):
            continue

        row: dict[str, float | str] = {
            "jd": float(jd),
            "lon": float(lon),
            "lat": float(lat),
        }
        star = _get("star")
        if star is not None:
            row["star"] = star
        rows.append(row)

    return rows


def _lon_error_deg(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def _parse_iota_graze_rows(url: str) -> list[dict[str, float]]:
    return _parse_iota_graze_rows_for_date(url, 2025, 3, 7)


def _parse_iota_graze_rows_for_date(
    url: str,
    year: int,
    month: int,
    day: int,
) -> list[dict[str, float]]:
    raw_text = requests.get(url, timeout=30).text
    elev_match = re.search(r"Nominal site altitude\s+([\d.]+)\s*m", raw_text)
    nominal_elev_m = float(elev_match.group(1)) if elev_match else 0.0
    text = raw_text.splitlines()
    rows: list[dict[str, float]] = []
    for line in text:
        match = re.match(
            r"^\s*([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+([+-]?)\s*(\d+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)",
            line,
        )
        if match is None:
            continue

        lon_sign, lon_deg, lon_min, lon_sec, lat_sign, lat_deg, lat_min, lat_sec, hh, mm, ss = match.groups()
        lon = int(lon_deg) + int(lon_min) / 60.0 + int(lon_sec) / 3600.0
        if lon_sign == "-":
            lon = -lon
        lat = int(lat_deg) + int(lat_min) / 60.0 + float(lat_sec) / 3600.0
        if lat_sign == "-":
            lat = -lat
        jd = julian_day(year, month, day, int(hh) + int(mm) / 60.0 + int(ss) / 3600.0)
        rows.append({"jd": jd, "lon": lon, "lat": lat, "observer_elev_m": nominal_elev_m})
    return rows


def _parse_iota_graze_circumstance_rows_for_date(
    url: str,
) -> list[dict[str, float | str]]:
    raw_text = requests.get(url, timeout=30).text
    rows: list[dict[str, float | str]] = []
    for line in raw_text.splitlines():
        match = re.match(
            r"^\s*([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+([+-]?)\s*(\d+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([+-]?\d+)?\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([+-]?[\d.]+)([NS])",
            line,
        )
        if match is None:
            continue

        (
            lon_sign,
            lon_deg,
            lon_min,
            lon_sec,
            lat_sign,
            lat_deg,
            lat_min,
            lat_sec,
            hh,
            mm,
            ss,
            sun_alt,
            moon_alt,
            moon_az,
            tanz,
            pa,
            aa,
            ca,
            cusp_pole,
        ) = match.groups()

        lon = int(lon_deg) + int(lon_min) / 60.0 + int(lon_sec) / 3600.0
        if lon_sign == "-":
            lon = -lon
        lat = int(lat_deg) + int(lat_min) / 60.0 + float(lat_sec) / 3600.0
        if lat_sign == "-":
            lat = -lat
        rows.append(
            {
                "jd": julian_day(2024, 11, 27, int(hh) + int(mm) / 60.0 + int(ss) / 3600.0),
                "lon": lon,
                "lat": lat,
                "sun_alt": float(sun_alt) if sun_alt is not None else float("nan"),
                "moon_alt": float(moon_alt),
                "moon_az": float(moon_az),
                "tanz": float(tanz),
                "pa": float(pa),
                "aa": float(aa),
                "ca": float(ca),
                "cusp_pole": cusp_pole,
            }
        )
    if not rows:
        raise AssertionError(f"No graze circumstance rows parsed from {url}")
    return rows


def _parse_iota_annual_graze_section(
    url: str,
    star_label: str,
) -> list[dict[str, float]]:
    text = requests.get(url, timeout=30).text
    sections = [s for s in re.split(r"(?=^#\s*\d+:)", text, flags=re.M) if s.strip().startswith("#")]

    section = next(
        (s for s in sections if star_label.lower() in s.splitlines()[0].lower()),
        None,
    )
    if section is None:
        raise AssertionError(f"Could not find annual IOTA section for {star_label!r}")

    header = section.splitlines()[0]
    date_match = re.search(r":\s*([A-Z]+)\.?\s+(\d{1,2}),\s+(\d{4})", header)
    if date_match is None:
        raise AssertionError(f"Could not parse IOTA annual section date for {star_label!r}")

    month_token, day_text, year_text = date_match.groups()
    month_map = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "JULY": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    month = month_map[month_token.upper()]
    day = int(day_text)
    year = int(year_text)

    elev_match = re.search(r"Nominal site altitude\s+([\d.]+)\s*m", section)
    nominal_elev_m = float(elev_match.group(1)) if elev_match else 0.0

    rows: list[dict[str, float]] = []
    for line in section.splitlines():
        match = re.match(
            r"^\s*([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)",
            line,
        )
        if match is None:
            continue

        lon_sign, lon_deg, lon_min, lon_sec, lat_sign, lat_deg, lat_min, lat_sec, hh, mm, ss = match.groups()
        lon = int(lon_deg) + int(lon_min) / 60.0 + int(lon_sec) / 3600.0
        if lon_sign == "-":
            lon = -lon
        lat = int(lat_deg) + int(lat_min) / 60.0 + int(lat_sec) / 3600.0
        if lat_sign == "-":
            lat = -lat
        jd = julian_day(year, month, day, int(hh) + int(mm) / 60.0 + float(ss) / 3600.0)
        rows.append({"jd": jd, "lon": lon, "lat": lat, "observer_elev_m": nominal_elev_m})

    if not rows:
        raise AssertionError(f"No annual IOTA graze rows parsed for {star_label!r}")
    return rows


def test_solar_eclipse_path_matches_offline_swiss_where_reference() -> None:
    calc = EclipseCalculator()
    row = _parse_where_rows("swe_sol_eclipse_where")[0]

    path = calc.solar_eclipse_path(float(row["jd"]) - 5.0, kind="any", sample_count=1)

    assert abs(path.max_eclipse_lat - float(row["lat"])) <= 1.0
    assert _lon_error_deg(path.max_eclipse_lon, float(row["lon"])) <= 1.0
    assert len(path.central_line_lats) == 1
    assert len(path.central_line_lons) == 1
    assert path.eclipse_data.is_solar_eclipse


def test_lunar_star_occultation_path_matches_offline_swiss_where_reference() -> None:
    row = _parse_where_rows("swe_lun_occult_where")[0]
    star_name = str(row["star"])
    star = star_at(star_name, ut_to_tt(float(row["jd"])))

    path = lunar_star_occultation_path_at(
        star.longitude,
        star.latitude,
        star_name,
        float(row["jd"]),
        sample_count=1,
    )

    assert abs(path.jd_greatest_ut - float(row["jd"])) <= 0.05
    assert abs(path.central_line_lats[0] - float(row["lat"])) <= 1.0
    assert _lon_error_deg(path.central_line_lons[0], float(row["lon"])) <= 1.0
    assert path.occulting_body == "Moon"
    assert path.occulted_body == star_name
    assert path.path_width_km > 0.0
    assert path.duration_at_greatest_s > 0.0


@pytest.mark.network
def test_lunar_star_occultation_graze_path_matches_iota_text_reference() -> None:
    rows = _parse_iota_graze_rows(
        "https://occultations.org/publications/rasc/2025/20250307ElNath.txt"
    )
    sample_rows = [rows[0], rows[20], rows[40], rows[60]]
    star = star_at("Elnath", ut_to_tt(float(sample_rows[0]["jd"])))

    for row in sample_rows:
        graze_lat = lunar_star_graze_latitude(
            star.longitude,
            star.latitude,
            float(row["jd"]),
            float(row["lon"]),
            float(row["lat"]),
            observer_elev_m=float(row["observer_elev_m"]),
        )
        assert abs(graze_lat - float(row["lat"])) <= 0.18


@pytest.mark.network
def test_lunar_star_occultation_graze_limits_match_iota_spica_text_references() -> None:
    north_rows = _parse_iota_graze_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt",
        2024,
        11,
        27,
    )
    south_rows = _parse_iota_graze_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt",
        2024,
        11,
        27,
    )
    north_sample = [north_rows[0], north_rows[len(north_rows) // 3], north_rows[(2 * len(north_rows)) // 3], north_rows[-1]]
    south_sample = [south_rows[0], south_rows[len(south_rows) // 3], south_rows[(2 * len(south_rows)) // 3], south_rows[-1]]
    star = star_at("Spica", ut_to_tt(float(north_sample[0]["jd"])))

    for row in north_sample + south_sample:
        graze_lat = lunar_star_graze_latitude(
            star.longitude,
            star.latitude,
            float(row["jd"]),
            float(row["lon"]),
            float(row["lat"]),
            observer_elev_m=float(row["observer_elev_m"]),
        )
        assert abs(graze_lat - float(row["lat"])) <= 0.18


@pytest.mark.network
def test_lunar_star_graze_circumstances_match_iota_spica_table_columns() -> None:
    north_rows = _parse_iota_graze_circumstance_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt"
    )
    south_rows = _parse_iota_graze_circumstance_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt"
    )
    sample_rows = [
        north_rows[0],
        north_rows[len(north_rows) // 2],
        south_rows[0],
        south_rows[len(south_rows) // 2],
    ]

    for row in sample_rows:
        star = star_at("Spica", ut_to_tt(float(row["jd"])))
        circumstances = lunar_star_graze_circumstances(
            star.longitude,
            star.latitude,
            float(row["jd"]),
            float(row["lat"]),
            float(row["lon"]),
        )
        assert abs(circumstances.tan_z - float(row["tanz"])) <= 1.6
        assert abs(circumstances.position_angle_deg - float(row["pa"])) <= 1.2
        assert abs(circumstances.axis_angle_deg - float(row["aa"])) <= 1.2
        assert abs(circumstances.cusp_angle_deg - float(row["ca"])) <= 1.2
        assert circumstances.cusp_pole == str(row["cusp_pole"])


@pytest.mark.network
def test_lunar_star_graze_table_matches_iota_spica_sample_rows() -> None:
    rows = _parse_iota_graze_circumstance_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt"
    )
    sample_rows = [rows[0], rows[len(rows) // 2], rows[-1]]
    star = star_at("Spica", ut_to_tt(float(sample_rows[0]["jd"])))

    table = lunar_star_graze_table(
        star.longitude,
        star.latitude,
        [float(row["jd"]) for row in sample_rows],
        [float(row["lon"]) for row in sample_rows],
        [float(row["lat"]) for row in sample_rows],
    )

    for built, row in zip(table, sample_rows):
        assert abs(built.latitude_deg - float(row["lat"])) <= 0.18
        assert abs(built.tan_z - float(row["tanz"])) <= 1.6
        assert abs(built.position_angle_deg - float(row["pa"])) <= 1.2
        assert abs(built.axis_angle_deg - float(row["aa"])) <= 1.2
        assert abs(built.cusp_angle_deg - float(row["ca"])) <= 1.2
        assert built.cusp_pole == str(row["cusp_pole"])


@pytest.mark.network
def test_lunar_star_graze_product_nominal_limit_matches_iota_spica_row() -> None:
    rows = _parse_iota_graze_circumstance_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt"
    )
    row = rows[-1]
    star = star_at("Spica", ut_to_tt(float(row["jd"])))
    product = lunar_star_graze_product_at(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
    )

    assert product.product_kind == "nominal_limit"
    assert product.has_profile_conditioned_band is False
    assert abs(product.nominal_limit_latitude_deg - float(row["lat"])) <= 0.18


@pytest.mark.network
def test_lunar_star_graze_product_track_nominal_limit_matches_iota_spica_rows() -> None:
    rows = _parse_iota_graze_circumstance_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt"
    )
    sample_rows = [rows[0], rows[len(rows) // 2], rows[-1]]
    star = star_at("Spica", ut_to_tt(float(sample_rows[0]["jd"])))
    track = lunar_star_graze_product_track(
        star.longitude,
        star.latitude,
        [float(row["jd"]) for row in sample_rows],
        [float(row["lon"]) for row in sample_rows],
        [float(row["lat"]) for row in sample_rows],
    )

    assert track.product_kind == "nominal_limit"
    assert track.has_profile_conditioned_band is False
    assert track.profile_band_south_latitude_deg is None
    assert track.profile_band_north_latitude_deg is None
    for built_lat, row in zip(track.nominal_limit_latitude_deg, sample_rows):
        assert abs(built_lat - float(row["lat"])) <= 0.18


@pytest.mark.network
def test_lunar_star_occultation_path_matches_iota_epsilon_ari_text_reference() -> None:
    rows = _parse_iota_graze_rows_for_date(
        "https://occultations.org/publications/rasc/2025/20250401epsAriPath.txt",
        2025,
        4,
        1,
    )
    sample_rows = [rows[0], rows[len(rows) // 3], rows[(2 * len(rows)) // 3], rows[-1]]
    star = star_at("eps Ari A", ut_to_tt(float(sample_rows[0]["jd"])))

    for row in sample_rows:
        graze_lat = lunar_star_graze_latitude(
            star.longitude,
            star.latitude,
            float(row["jd"]),
            float(row["lon"]),
            float(row["lat"]),
            observer_elev_m=float(row["observer_elev_m"]),
        )
        assert abs(graze_lat - float(row["lat"])) <= 0.18


@pytest.mark.network
@pytest.mark.parametrize(
    ("star_label", "registry_name"),
    [
        ("Alcyone", "Alcyone"),
        ("Merope", "Merope"),
        ("Asellus Borealis", "Asellus Borealis"),
        ("Regulus", "Regulus"),
    ],
)
def test_lunar_star_occultation_path_matches_iota_annual_graze_sections(
    star_label: str,
    registry_name: str,
) -> None:
    rows = _parse_iota_annual_graze_section(
        "https://occultations.org/publications/rasc/2025/nam25grz.txt",
        star_label,
    )
    sample_rows = [rows[0], rows[len(rows) // 3], rows[(2 * len(rows)) // 3], rows[-1]]
    star = star_at(registry_name, ut_to_tt(float(sample_rows[0]["jd"])))

    for row in sample_rows:
        graze_lat = lunar_star_graze_latitude(
            star.longitude,
            star.latitude,
            float(row["jd"]),
            float(row["lon"]),
            float(row["lat"]),
            observer_elev_m=float(row["observer_elev_m"]),
        )
        assert abs(graze_lat - float(row["lat"])) <= 0.18


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize(
    ("star_label", "registry_name"),
    [
        ("Alcyone", "Alcyone"),
        ("Merope", "Merope"),
    ],
)
def test_lunar_star_practical_graze_line_matches_profile_sensitive_iota_sections(
    star_label: str,
    registry_name: str,
) -> None:
    rows = _parse_iota_annual_graze_section(
        "https://occultations.org/publications/rasc/2025/nam25grz.txt",
        star_label,
    )
    row = rows[0]
    star = star_at(registry_name, ut_to_tt(float(row["jd"])))

    nominal_lat = lunar_star_graze_latitude(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
        observer_elev_m=float(row["observer_elev_m"]),
    )
    practical_lat = lunar_star_practical_graze_latitude(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
        observer_elev_m=float(row["observer_elev_m"]),
        limb_profile_provider=official_lunar_limb_profile_adjustment,
    )

    nominal_err = abs(nominal_lat - float(row["lat"]))
    practical_err = abs(practical_lat - float(row["lat"]))

    assert practical_err < nominal_err
    assert practical_err <= 0.003
