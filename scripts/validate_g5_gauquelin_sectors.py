"""Validate Moira Gauquelin sectors against Thierry Graff's g5 tmp archive.

The supplied archive contains historical personal records.  This script reads
it in place and emits aggregate evidence only: no name, birth date, place, or
coordinate is copied into the repository or report.

CFEPP is compared from explicit UTC and coordinates; Muller's explicit-LMT
subset is converted from longitude; CSICOP retains two declared clock policies.
Ertel and Muller's non-LMT rows remain inventory-only until their missing joins
or correction semantics can be established.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from moira.facade import Moira
from moira_server.models.gauquelin import GauquelinChartSectorsRequest
from moira_server.services.gauquelin import compute_gauquelin_chart_sectors


EXPECTED_FILES: dict[str, tuple[str, int, int]] = {
    "cfepp-1120-nienhuys-raw.csv": ("S", 1, 12),
    "csicop-408-irving-raw.csv": ("MARS", 1, 36),
    "ertel-4384-sport-raw.csv": ("MARS", 1, 36),
    "muller5-1083-medics-raw.csv": ("MARS", 1, 36),
}
EXPECTED_WITNESS_ROWS: dict[str, int] = {
    "cfepp-1120-nienhuys-raw.csv": 1120,
    "csicop-408-irving-raw.csv": 408,
    "ertel-4384-sport-raw.csv": 4384,
    "muller5-1083-medics-raw.csv": 1083,
}
CSICOP_WITNESSED_TIMEZONES = frozenset({"5", "6", "7", "8", "0,5"})

CFEPP_REQUIRED_FIELDS = frozenset(
    {"UNIV_DATE", "UT", "LONG", "LAT", "S"}
)
CSICOP_REQUIRED_FIELDS = frozenset(
    {
        "GEBDAT",
        "GEBZEIT",
        "AMPM",
        "ZEITZONE",
        "LO1",
        "LO2",
        "LA1",
        "LA2",
        "MARS",
    }
)
MULLER_REQUIRED_FIELDS = frozenset(
    {"GEBDATUM", "GEBZEIT", "LAENGE", "BREITE", "MODE", "MARS"}
)


@dataclass(frozen=True, slots=True)
class CfeppRecord:
    instant_utc: datetime
    longitude_east_positive: float
    latitude: float
    source_sector_12: int


@dataclass(frozen=True, slots=True)
class CsicopRecord:
    instant_utc: datetime
    longitude_east_positive: float
    latitude: float
    source_sector_36: int


@dataclass(frozen=True, slots=True)
class MullerLmtRecord:
    instant_utc: datetime
    longitude_east_positive: float
    latitude: float
    source_sector_36: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_csv_entries(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    result: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        normalized = info.filename.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe archive member: {info.filename!r}")
        if info.is_dir() or not normalized.lower().endswith(".csv"):
            continue
        basename = path.name
        if basename.startswith(".~lock."):
            continue
        if basename in result:
            raise ValueError(f"duplicate CSV basename: {basename!r}")
        result[basename] = info
    return result


def _read_rows(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> tuple[list[str], list[dict[str, str]]]:
    text = archive.read(info).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if reader.fieldnames is None:
        raise ValueError(f"missing CSV header: {info.filename!r}")
    return list(reader.fieldnames), list(reader)


def inventory_archive(
    path: Path, *, enforce_witness_counts: bool = True
) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        entries = _safe_csv_entries(archive)
        missing = sorted(set(EXPECTED_FILES) - set(entries))
        unexpected = sorted(set(entries) - set(EXPECTED_FILES))
        if missing or unexpected:
            raise ValueError(
                f"archive CSV set mismatch: missing={missing}, unexpected={unexpected}"
            )

        files: dict[str, object] = {}
        for basename, (sector_field, minimum, maximum) in EXPECTED_FILES.items():
            fields, rows = _read_rows(archive, entries[basename])
            expected_rows = EXPECTED_WITNESS_ROWS[basename]
            if enforce_witness_counts and len(rows) != expected_rows:
                raise ValueError(
                    f"{basename}: expected {expected_rows} witness rows, "
                    f"found {len(rows)}"
                )
            if sector_field not in fields:
                raise ValueError(f"{basename}: missing field {sector_field!r}")
            sectors = [int(row[sector_field]) for row in rows]
            if not sectors or any(not minimum <= value <= maximum for value in sectors):
                raise ValueError(
                    f"{basename}: {sector_field} must be populated in "
                    f"[{minimum}, {maximum}]"
                )
            files[basename] = {
                "rows": len(rows),
                "sector_field": sector_field,
                "sector_min": min(sectors),
                "sector_max": max(sectors),
                "sector_populated": len(sectors),
            }

        ertel_fields, ertel_rows = _read_rows(
            archive, entries["ertel-4384-sport-raw.csv"]
        )
        if "MA12" not in ertel_fields:
            raise ValueError("ertel-4384-sport-raw.csv: missing field 'MA12'")
        mapping_errors = sum(
            int(row["MA12"]) != sector_36_to_12(int(row["MARS"]))
            for row in ertel_rows
        )
        files["ertel-4384-sport-raw.csv"]["mars_36_to_ma12_errors"] = (
            mapping_errors
        )

    return {
        "archive": {
            "basename": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        },
        "files": files,
        "source_rows_total": sum(item["rows"] for item in files.values()),
        "privacy": "aggregate_only_no_personal_records_emitted",
    }


def load_cfepp_records(path: Path) -> list[CfeppRecord]:
    with zipfile.ZipFile(path) as archive:
        entries = _safe_csv_entries(archive)
        try:
            info = entries["cfepp-1120-nienhuys-raw.csv"]
        except KeyError as exc:
            raise ValueError("archive does not contain the CFEPP tmp raw CSV") from exc
        fields, rows = _read_rows(archive, info)

    missing_fields = sorted(CFEPP_REQUIRED_FIELDS - set(fields))
    if missing_fields:
        raise ValueError(f"CFEPP CSV missing fields: {missing_fields}")

    records: list[CfeppRecord] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            instant = datetime.strptime(
                f"{row['UNIV_DATE']} {row['UT']}", "%Y %m %d %H %M"
            ).replace(tzinfo=UTC)
            source_sector = int(row["S"])
            # CFEPP/g5 raw longitude is west-positive (east is negative).
            longitude = -float(row["LONG"])
            latitude = float(row["LAT"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid CFEPP row {row_number}") from exc
        if not 1 <= source_sector <= 12:
            raise ValueError(f"invalid CFEPP sector at row {row_number}")
        if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
            raise ValueError(f"invalid CFEPP coordinates at row {row_number}")
        records.append(
            CfeppRecord(
                instant_utc=instant,
                longitude_east_positive=longitude,
                latitude=latitude,
                source_sector_12=source_sector,
            )
        )
    return records


def load_csicop_records(
    path: Path, *, conventional_noon_midnight: bool
) -> list[CsicopRecord]:
    with zipfile.ZipFile(path) as archive:
        entries = _safe_csv_entries(archive)
        try:
            info = entries["csicop-408-irving-raw.csv"]
        except KeyError as exc:
            raise ValueError("archive does not contain the CSICOP tmp raw CSV") from exc
        fields, rows = _read_rows(archive, info)

    missing_fields = sorted(CSICOP_REQUIRED_FIELDS - set(fields))
    if missing_fields:
        raise ValueError(f"CSICOP CSV missing fields: {missing_fields}")

    records: list[CsicopRecord] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            day, month, year = (int(value) for value in row["GEBDAT"].split())
            hour, minute = (int(value) for value in row["GEBZEIT"].split())
            marker = row["AMPM"]
            if marker not in {"A", "A1", "P", "P1"}:
                raise ValueError("unknown AM/PM marker")
            if conventional_noon_midnight:
                hour = hour % 12 + (12 if marker.startswith("P") else 0)
            elif marker in {"P", "P1"}:
                # Reproduce g5 raw2tmp.php literally, including its handling
                # of 12 A/P, so the alternative can be audited explicitly.
                hour += 12
            local = datetime(year, month, day) + timedelta(hours=hour, minutes=minute)
            timezone_text = row["ZEITZONE"]
            if timezone_text not in CSICOP_WITNESSED_TIMEZONES:
                raise ValueError(
                    f"unsupported CSICOP timezone {timezone_text!r}"
                )
            west_offset_hours = (
                10.5 if timezone_text == "0,5" else float(timezone_text)
            )
            instant = (local + timedelta(hours=west_offset_hours)).replace(tzinfo=UTC)
            longitude = -(float(row["LO1"]) + float(row["LO2"]) / 60.0)
            latitude = float(row["LA1"]) + float(row["LA2"]) / 60.0
            source_sector = int(row["MARS"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid CSICOP row {row_number}: {exc}") from exc
        if not 1 <= source_sector <= 36:
            raise ValueError(f"invalid CSICOP sector at row {row_number}")
        if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
            raise ValueError(f"invalid CSICOP coordinates at row {row_number}")
        records.append(
            CsicopRecord(
                instant_utc=instant,
                longitude_east_positive=longitude,
                latitude=latitude,
                source_sector_36=source_sector,
            )
        )
    return records


def _parse_degrees_direction_minutes(value: str) -> float:
    degrees_text, direction, minutes_text = value.split()
    coordinate = float(degrees_text) + float(minutes_text) / 60.0
    if direction in {"S", "W"}:
        coordinate = -coordinate
    elif direction not in {"N", "E"}:
        raise ValueError("unknown coordinate direction")
    return coordinate


def load_muller_lmt_records(path: Path) -> list[MullerLmtRecord]:
    with zipfile.ZipFile(path) as archive:
        entries = _safe_csv_entries(archive)
        try:
            info = entries["muller5-1083-medics-raw.csv"]
        except KeyError as exc:
            raise ValueError("archive does not contain the Muller tmp raw CSV") from exc
        fields, rows = _read_rows(archive, info)

    missing_fields = sorted(MULLER_REQUIRED_FIELDS - set(fields))
    if missing_fields:
        raise ValueError(f"Muller CSV missing fields: {missing_fields}")

    records: list[MullerLmtRecord] = []
    for row_number, row in enumerate(rows, start=2):
        if row["MODE"] != "LMT":
            continue
        try:
            day, month, year = (
                int(value) for value in row["GEBDATUM"].split(".")
            )
            hour, minute = (int(value) for value in row["GEBZEIT"].split("."))
            local = datetime(year, month, day) + timedelta(
                hours=hour, minutes=minute
            )
            longitude = _parse_degrees_direction_minutes(row["LAENGE"])
            latitude = _parse_degrees_direction_minutes(row["BREITE"])
            # Local mean solar time = UTC + east-positive longitude / 15.
            instant = (
                local - timedelta(hours=longitude / 15.0)
            ).replace(tzinfo=UTC)
            source_sector = int(row["MARS"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid Muller LMT row {row_number}") from exc
        if not 1 <= source_sector <= 36:
            raise ValueError(f"invalid Muller sector at row {row_number}")
        if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
            raise ValueError(f"invalid Muller coordinates at row {row_number}")
        records.append(
            MullerLmtRecord(
                instant_utc=instant,
                longitude_east_positive=longitude,
                latitude=latitude,
                source_sector_36=source_sector,
            )
        )
    return records


def sector_36_to_12(sector: int) -> int:
    if not 1 <= sector <= 36:
        raise ValueError("36-sector value must be in [1, 36]")
    return (sector - 1) // 3 + 1


def circular_sector_distance(a: int, b: int, sectors: int) -> int:
    raw = abs(a - b) % sectors
    return min(raw, sectors - raw)


def _distance_to_boundary(diurnal_position: float | None, width: float) -> float:
    if diurnal_position is None:
        raise RuntimeError(
            "defined Gauquelin sector is missing its diurnal position"
        )
    remainder = diurnal_position % width
    return min(remainder, width - remainder)


def compare_cfepp(
    records: Iterable[CfeppRecord],
    *,
    engine: Moira,
    limit: int | None = None,
) -> dict[str, object]:
    records = tuple(records)
    compared = exact = undefined = 0
    distance_counts: Counter[int] = Counter()
    source_counts: Counter[int] = Counter()
    moira_counts: Counter[int] = Counter()
    tranche_counts: dict[str, Counter[str]] = {
        "official_first_1066": Counter(),
        "supplementary_final_54": Counter(),
    }
    mismatch_boundary_distances: list[float] = []

    for record_index, record in enumerate(records, start=1):
        if limit is not None and compared >= limit:
            break
        result = compute_gauquelin_chart_sectors(
            engine,
            GauquelinChartSectorsRequest(
                dt=record.instant_utc,
                latitude=record.latitude,
                longitude=record.longitude_east_positive,
                bodies=["Mars"],
                horizon_altitude=0.0,
                sectors=36,
            ),
        )
        position = result.positions[0].position
        compared += 1
        tranche = (
            "official_first_1066"
            if record_index <= 1066
            else "supplementary_final_54"
        )
        tranche_counts[tranche]["compared"] += 1
        source_counts[record.source_sector_12] += 1
        if position.sector is None:
            undefined += 1
            tranche_counts[tranche]["undefined"] += 1
            continue
        moira_sector = sector_36_to_12(position.sector)
        moira_counts[moira_sector] += 1
        distance = circular_sector_distance(
            record.source_sector_12, moira_sector, 12
        )
        distance_counts[distance] += 1
        exact += distance == 0
        tranche_counts[tranche]["defined"] += 1
        if distance == 0:
            tranche_counts[tranche]["exact"] += 1
        else:
            mismatch_boundary_distances.append(
                _distance_to_boundary(position.diurnal_position, 30.0)
            )

    defined = compared - undefined
    tranches: dict[str, object] = {}
    for name, counts in tranche_counts.items():
        tranche_defined = counts["defined"]
        tranches[name] = {
            "compared": counts["compared"],
            "defined": tranche_defined,
            "undefined": counts["undefined"],
            "exact": counts["exact"],
            "exact_rate_defined": (
                counts["exact"] / tranche_defined if tranche_defined else None
            ),
        }
    return {
        "corpus": "CFEPP first 1066 official plus 54 supplementary",
        "rows_available": len(records),
        "rows_compared": compared,
        "defined": defined,
        "undefined": undefined,
        "exact": exact,
        "exact_rate_defined": exact / defined if defined else None,
        "tranches": tranches,
        "mismatch_distance_to_nearest_12_sector_boundary_degrees": {
            "count": len(mismatch_boundary_distances),
            "minimum": min(mismatch_boundary_distances)
            if mismatch_boundary_distances
            else None,
            "maximum": max(mismatch_boundary_distances)
            if mismatch_boundary_distances
            else None,
        },
        "circular_distance_counts_12": {
            str(key): distance_counts[key] for key in sorted(distance_counts)
        },
        "source_sector_counts_12": {
            str(key): source_counts[key] for key in sorted(source_counts)
        },
        "moira_sector_counts_12": {
            str(key): moira_counts[key] for key in sorted(moira_counts)
        },
        "computation": {
            "body": "Mars",
            "coordinates": "CFEPP explicit UTC and geographic coordinates",
            "longitude_conversion": "g5 west-positive negated to east-positive",
            "moira_coordinate_source": "chart_apparent_topocentric_ra_dec_lst",
            "horizon_altitude_degrees": 0.0,
            "mapping_36_to_12": "floor((sector_36 - 1) / 3) + 1",
        },
    }


def compare_csicop(
    records: Iterable[CsicopRecord],
    *,
    engine: Moira,
    time_policy: str,
    limit: int | None = None,
) -> dict[str, object]:
    records = tuple(records)
    compared = exact = undefined = 0
    distance_counts: Counter[int] = Counter()
    mismatch_boundary_distances: list[float] = []

    for record in records:
        if limit is not None and compared >= limit:
            break
        result = compute_gauquelin_chart_sectors(
            engine,
            GauquelinChartSectorsRequest(
                dt=record.instant_utc,
                latitude=record.latitude,
                longitude=record.longitude_east_positive,
                bodies=["Mars"],
                horizon_altitude=0.0,
                sectors=36,
            ),
        )
        position = result.positions[0].position
        compared += 1
        if position.sector is None:
            undefined += 1
            continue
        distance = circular_sector_distance(
            record.source_sector_36, position.sector, 36
        )
        distance_counts[distance] += 1
        exact += distance == 0
        if distance != 0:
            mismatch_boundary_distances.append(
                _distance_to_boundary(position.diurnal_position, 10.0)
            )

    defined = compared - undefined
    return {
        "corpus": "CSICOP 408 athletes",
        "time_policy": time_policy,
        "rows_available": len(records),
        "rows_compared": compared,
        "defined": defined,
        "undefined": undefined,
        "exact": exact,
        "exact_rate_defined": exact / defined if defined else None,
        "circular_distance_counts_36": {
            str(key): distance_counts[key] for key in sorted(distance_counts)
        },
        "mismatch_distance_to_nearest_36_sector_boundary_degrees": {
            "count": len(mismatch_boundary_distances),
            "minimum": min(mismatch_boundary_distances)
            if mismatch_boundary_distances
            else None,
            "maximum": max(mismatch_boundary_distances)
            if mismatch_boundary_distances
            else None,
        },
        "computation": {
            "body": "Mars",
            "coordinates": "CSICOP local clock, fixed offset, and geographic coordinates",
            "longitude_conversion": "west degrees/minutes converted to east-negative",
            "moira_coordinate_source": "chart_apparent_topocentric_ra_dec_lst",
            "horizon_altitude_degrees": 0.0,
        },
    }


def compare_muller_lmt(
    records: Iterable[MullerLmtRecord],
    *,
    engine: Moira,
    rows_available: int | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    records = tuple(records)
    total_rows = len(records) if rows_available is None else rows_available
    if total_rows < len(records):
        raise ValueError("Muller total rows cannot be smaller than LMT rows")
    compared = exact = undefined = 0
    distance_counts: Counter[int] = Counter()
    mismatch_boundary_distances: list[float] = []

    for record in records:
        if limit is not None and compared >= limit:
            break
        result = compute_gauquelin_chart_sectors(
            engine,
            GauquelinChartSectorsRequest(
                dt=record.instant_utc,
                latitude=record.latitude,
                longitude=record.longitude_east_positive,
                bodies=["Mars"],
                horizon_altitude=0.0,
                sectors=36,
            ),
        )
        position = result.positions[0].position
        compared += 1
        if position.sector is None:
            undefined += 1
            continue
        distance = circular_sector_distance(
            record.source_sector_36, position.sector, 36
        )
        distance_counts[distance] += 1
        exact += distance == 0
        if distance != 0:
            mismatch_boundary_distances.append(
                _distance_to_boundary(position.diurnal_position, 10.0)
            )

    defined = compared - undefined
    return {
        "corpus": "Muller 1083 medics, explicit LMT subset",
        "rows_available": total_rows,
        "rows_lmt": len(records),
        "rows_non_lmt_deferred": total_rows - len(records),
        "rows_compared": compared,
        "defined": defined,
        "undefined": undefined,
        "exact": exact,
        "exact_rate_defined": exact / defined if defined else None,
        "circular_distance_counts_36": {
            str(key): distance_counts[key] for key in sorted(distance_counts)
        },
        "mismatch_distance_to_nearest_36_sector_boundary_degrees": {
            "count": len(mismatch_boundary_distances),
            "minimum": min(mismatch_boundary_distances)
            if mismatch_boundary_distances
            else None,
            "maximum": max(mismatch_boundary_distances)
            if mismatch_boundary_distances
            else None,
        },
        "computation": {
            "body": "Mars",
            "time_conversion": "UTC = LMT - east_positive_longitude / 15 hours",
            "longitude_conversion": "directional degrees/minutes to east-positive",
            "moira_coordinate_source": "chart_apparent_topocentric_ra_dec_lst",
            "horizon_altitude_degrees": 0.0,
        },
    }


def build_report(path: Path, *, limit: int | None = None) -> dict[str, object]:
    inventory = inventory_archive(path)
    inventory_files = inventory["files"]
    engine = Moira()
    cfepp_records = load_cfepp_records(path)
    csicop_literal_records = load_csicop_records(
        path, conventional_noon_midnight=False
    )
    csicop_conventional_records = load_csicop_records(
        path, conventional_noon_midnight=True
    )
    muller_records = load_muller_lmt_records(path)
    comparison = compare_cfepp(cfepp_records, engine=engine, limit=limit)
    csicop_g5 = compare_csicop(
        csicop_literal_records,
        engine=engine,
        time_policy="literal_g5_2019_raw2tmp",
        limit=limit,
    )
    csicop_conventional = compare_csicop(
        csicop_conventional_records,
        engine=engine,
        time_policy="conventional_12_hour_noon_midnight",
        limit=limit,
    )
    muller_lmt = compare_muller_lmt(
        muller_records,
        engine=engine,
        rows_available=inventory_files["muller5-1083-medics-raw.csv"]["rows"],
        limit=limit,
    )
    return {
        "schema": "moira.gauquelin.g5_validation.v1",
        "inventory": inventory,
        "cfepp_numerical_comparison": comparison,
        "csicop_numerical_comparison": {
            "declared": csicop_g5,
            "sensitivity": csicop_conventional,
        },
        "muller_lmt_numerical_comparison": muller_lmt,
        "nonclaims": [
            "Historical source assignments are evidence, not an infallible oracle.",
            "No algorithm is changed to increase corpus agreement.",
            "CSICOP noon/midnight semantics remain an explicit sensitivity audit.",
            "Muller non-LMT rows await correction-code reconstruction.",
            "Ertel awaits joins to records containing birth place and time.",
            "The four source files contain overlapping people and are not 6995 independent cases.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    report = build_report(args.archive.resolve(), limit=args.limit)
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
