#!/usr/bin/env python

import json
import sys
from dataclasses import asdict, dataclass
from math import asin, degrees, sqrt
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.asteroids import ASTEROID_NAIF, _asteroid_geocentric, _kernel_for, asteroid_at
from moira.julian import ut_to_tt
from moira.planets import _geocentric, planet_at, sky_position_at
from moira.spk_reader import get_reader
from tools.benchmark_matrix import (
    EXPLORATORY_POSITION_ASTEROID_CASES,
    EXPLORATORY_POSITION_PLANET_CASES,
    POSITION_ASTEROID_CASES,
    POSITION_PLANET_CASES,
    STRICT_SKY_PLANET_CASES,
    STRICT_POSITION_ASTEROID_CASES,
    STRICT_POSITION_PLANET_CASES,
    VECTOR_ASTEROID_CASES,
    VECTOR_PLANET_CASES,
)
from tools.horizons import (
    observer_ecliptic_position,
    observer_sky_position,
    signed_arcminutes,
    vector_state,
)


@dataclass(frozen=True)
class PositionResult:
    category: str
    body: str
    label: str
    jd_ut: float
    ref_command: str
    lon_error_arcmin: float
    lat_error_arcmin: float
    lon_tolerance_arcmin: float
    lat_tolerance_arcmin: float
    passed: bool


@dataclass(frozen=True)
class VectorResult:
    category: str
    body: str
    label: str
    jd_ut: float
    ref_command: str
    diff_km: float
    angular_error_arcsec: float
    tolerance_arcsec: float
    passed: bool


@dataclass(frozen=True)
class SkyResult:
    category: str
    body: str
    label: str
    jd_ut: float
    ref_command: str
    site_latitude_deg: float
    site_longitude_deg: float
    ra_error_arcsec: float
    dec_error_arcsec: float
    az_error_arcsec: float
    alt_error_arcsec: float
    ra_tolerance_arcsec: float
    dec_tolerance_arcsec: float
    az_tolerance_arcsec: float
    alt_tolerance_arcsec: float
    passed: bool


def _angular_error_arcsec(moira_xyz: tuple[float, float, float], ref_xyz) -> tuple[float, float]:
    dx = moira_xyz[0] - ref_xyz.x
    dy = moira_xyz[1] - ref_xyz.y
    dz = moira_xyz[2] - ref_xyz.z
    diff_km = sqrt(dx * dx + dy * dy + dz * dz)
    dist_km = sqrt(
        moira_xyz[0] * moira_xyz[0]
        + moira_xyz[1] * moira_xyz[1]
        + moira_xyz[2] * moira_xyz[2]
    )
    ratio = min(1.0, diff_km / dist_km) if dist_km > 1e-12 else 0.0
    return diff_km, degrees(asin(ratio)) * 3600.0


def _position_results() -> list[PositionResult]:
    return _position_results_from_matrices(POSITION_PLANET_CASES, POSITION_ASTEROID_CASES)


def _position_results_from_matrices(
    planet_cases: dict[str, list],
    asteroid_cases: dict[str, list],
) -> list[PositionResult]:
    results: list[PositionResult] = []

    for body, cases in planet_cases.items():
        for case in cases:
            moira = planet_at(body, case.jd_ut)
            ref = observer_ecliptic_position(case.command, case.jd_ut)
            lon_error = signed_arcminutes(moira.longitude, ref.longitude)
            lat_error = (moira.latitude - ref.latitude) * 60.0
            results.append(
                PositionResult(
                    category="planet_position",
                    body=body,
                    label=case.label,
                    jd_ut=case.jd_ut,
                    ref_command=case.command,
                    lon_error_arcmin=lon_error,
                    lat_error_arcmin=lat_error,
                    lon_tolerance_arcmin=case.lon_tolerance_arcmin,
                    lat_tolerance_arcmin=case.lat_tolerance_arcmin,
                    passed=(
                        abs(lon_error) <= case.lon_tolerance_arcmin
                        and abs(lat_error) <= case.lat_tolerance_arcmin
                    ),
                )
            )

    for body, cases in asteroid_cases.items():
        for case in cases:
            moira = asteroid_at(body, case.jd_ut)
            ref = observer_ecliptic_position(case.command, case.jd_ut)
            lon_error = signed_arcminutes(moira.longitude, ref.longitude)
            lat_error = (moira.latitude - ref.latitude) * 60.0
            results.append(
                PositionResult(
                    category="asteroid_position",
                    body=body,
                    label=case.label,
                    jd_ut=case.jd_ut,
                    ref_command=case.command,
                    lon_error_arcmin=lon_error,
                    lat_error_arcmin=lat_error,
                    lon_tolerance_arcmin=case.lon_tolerance_arcmin,
                    lat_tolerance_arcmin=case.lat_tolerance_arcmin,
                    passed=(
                        abs(lon_error) <= case.lon_tolerance_arcmin
                        and abs(lat_error) <= case.lat_tolerance_arcmin
                    ),
                )
            )

    return results


def _vector_results() -> list[VectorResult]:
    results: list[VectorResult] = []
    reader = get_reader()

    for body, cases in VECTOR_PLANET_CASES.items():
        for case in cases:
            moira_xyz = _geocentric(body, ut_to_tt(case.jd_ut), reader)
            ref = vector_state(case.command, case.jd_ut)
            diff_km, angular_error = _angular_error_arcsec(moira_xyz, ref)
            results.append(
                VectorResult(
                    category="planet_vector",
                    body=body,
                    label=case.label,
                    jd_ut=case.jd_ut,
                    ref_command=case.command,
                    diff_km=diff_km,
                    angular_error_arcsec=angular_error,
                    tolerance_arcsec=case.tolerance_arcsec,
                    passed=angular_error <= case.tolerance_arcsec,
                )
            )

    for body, cases in VECTOR_ASTEROID_CASES.items():
        naif_id = ASTEROID_NAIF[body]
        kernel = _kernel_for(naif_id)
        for case in cases:
            moira_xyz = _asteroid_geocentric(
                naif_id, ut_to_tt(case.jd_ut), kernel, reader, apparent=False
            )
            ref = vector_state(case.command, case.jd_ut)
            diff_km, angular_error = _angular_error_arcsec(moira_xyz, ref)
            results.append(
                VectorResult(
                    category="asteroid_vector",
                    body=body,
                    label=case.label,
                    jd_ut=case.jd_ut,
                    ref_command=case.command,
                    diff_km=diff_km,
                    angular_error_arcsec=angular_error,
                    tolerance_arcsec=case.tolerance_arcsec,
                    passed=angular_error <= case.tolerance_arcsec,
                )
            )

    return results


def _signed_arcsec(a_deg: float, b_deg: float) -> float:
    return ((a_deg - b_deg + 180.0) % 360.0 - 180.0) * 3600.0


def _sky_results() -> list[SkyResult]:
    results: list[SkyResult] = []
    for body, cases in STRICT_SKY_PLANET_CASES.items():
        for case in cases:
            moira = sky_position_at(
                body,
                case.jd_ut,
                observer_lat=case.latitude_deg,
                observer_lon=case.longitude_deg,
                observer_elev_m=case.elevation_km * 1000.0,
            )
            ref = observer_sky_position(
                case.command,
                case.jd_ut,
                longitude_deg=case.longitude_deg,
                latitude_deg=case.latitude_deg,
                elevation_km=case.elevation_km,
            )
            ra_error = _signed_arcsec(moira.right_ascension, ref.right_ascension)
            dec_error = (moira.declination - ref.declination) * 3600.0
            az_error = _signed_arcsec(moira.azimuth, ref.azimuth)
            alt_error = (moira.altitude - ref.altitude) * 3600.0
            results.append(
                SkyResult(
                    category="planet_sky",
                    body=body,
                    label=case.label,
                    jd_ut=case.jd_ut,
                    ref_command=case.command,
                    site_latitude_deg=case.latitude_deg,
                    site_longitude_deg=case.longitude_deg,
                    ra_error_arcsec=ra_error,
                    dec_error_arcsec=dec_error,
                    az_error_arcsec=az_error,
                    alt_error_arcsec=alt_error,
                    ra_tolerance_arcsec=case.ra_tolerance_arcsec,
                    dec_tolerance_arcsec=case.dec_tolerance_arcsec,
                    az_tolerance_arcsec=case.az_tolerance_arcsec,
                    alt_tolerance_arcsec=case.alt_tolerance_arcsec,
                    passed=(
                        abs(ra_error) <= case.ra_tolerance_arcsec
                        and abs(dec_error) <= case.dec_tolerance_arcsec
                    ),
                )
            )
    return results


def main() -> None:
    strict_position_results = _position_results_from_matrices(
        STRICT_POSITION_PLANET_CASES, STRICT_POSITION_ASTEROID_CASES
    )
    exploratory_position_results = _position_results_from_matrices(
        EXPLORATORY_POSITION_PLANET_CASES, EXPLORATORY_POSITION_ASTEROID_CASES
    )
    position_results = strict_position_results + exploratory_position_results
    vector_results = _vector_results()
    sky_results = _sky_results()

    summary = {
        "strict_position_case_count": len(strict_position_results),
        "exploratory_position_case_count": len(exploratory_position_results),
        "position_case_count": len(position_results),
        "vector_case_count": len(vector_results),
        "sky_case_count": len(sky_results),
        "strict_passed": all(result.passed for result in strict_position_results + vector_results + sky_results),
        "exploratory_passed": all(result.passed for result in exploratory_position_results),
        "all_passed": all(result.passed for result in position_results + vector_results + sky_results),
        "max_abs_lon_error_arcmin": max(abs(r.lon_error_arcmin) for r in position_results),
        "max_abs_lat_error_arcmin": max(abs(r.lat_error_arcmin) for r in position_results),
        "strict_max_abs_lon_error_arcmin": max(abs(r.lon_error_arcmin) for r in strict_position_results),
        "strict_max_abs_lat_error_arcmin": max(abs(r.lat_error_arcmin) for r in strict_position_results),
        "exploratory_max_abs_lon_error_arcmin": max(abs(r.lon_error_arcmin) for r in exploratory_position_results),
        "exploratory_max_abs_lat_error_arcmin": max(abs(r.lat_error_arcmin) for r in exploratory_position_results),
        "max_vector_error_arcsec": max(r.angular_error_arcsec for r in vector_results),
        "max_sky_ra_error_arcsec": max(abs(r.ra_error_arcsec) for r in sky_results),
        "max_sky_dec_error_arcsec": max(abs(r.dec_error_arcsec) for r in sky_results),
        "max_sky_az_error_arcsec": max(abs(r.az_error_arcsec) for r in sky_results),
        "max_sky_alt_error_arcsec": max(abs(r.alt_error_arcsec) for r in sky_results),
    }

    payload = {
        "summary": summary,
        "strict_position_results": [asdict(result) for result in strict_position_results],
        "exploratory_position_results": [asdict(result) for result in exploratory_position_results],
        "position_results": [asdict(result) for result in position_results],
        "vector_results": [asdict(result) for result in vector_results],
        "sky_results": [asdict(result) for result in sky_results],
    }

    out_dir = _ROOT / "tests" / "artifacts" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print("Moira benchmark suite")
    print(f"strict observer cases:      {summary['strict_position_case_count']}")
    print(f"exploratory observer cases: {summary['exploratory_position_case_count']}")
    print(f"vector cases:               {summary['vector_case_count']}")
    print(f"strict sky cases:           {summary['sky_case_count']}")
    print(f"strict max |lon error|: {summary['strict_max_abs_lon_error_arcmin']:.4f} arcmin")
    print(f"strict max |lat error|: {summary['strict_max_abs_lat_error_arcmin']:.4f} arcmin")
    print(f"exploratory max |lon error|: {summary['exploratory_max_abs_lon_error_arcmin']:.4f} arcmin")
    print(f"exploratory max |lat error|: {summary['exploratory_max_abs_lat_error_arcmin']:.4f} arcmin")
    print(f"max vector err:             {summary['max_vector_error_arcsec']:.4f} arcsec")
    print(f"max sky RA err:             {summary['max_sky_ra_error_arcsec']:.4f} arcsec")
    print(f"max sky Dec err:            {summary['max_sky_dec_error_arcsec']:.4f} arcsec")
    print(f"max sky Az err:             {summary['max_sky_az_error_arcsec']:.4f} arcsec")
    print(f"max sky Alt err:            {summary['max_sky_alt_error_arcsec']:.4f} arcsec")
    print(f"strict passed:              {summary['strict_passed']}")
    print(f"exploratory passed: {summary['exploratory_passed']}")
    print(f"wrote:           {out_path}")


if __name__ == "__main__":
    main()
