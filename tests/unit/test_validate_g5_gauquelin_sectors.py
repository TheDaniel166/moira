from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from scripts.validate_g5_gauquelin_sectors import (
    circular_sector_distance,
    inventory_archive,
    load_cfepp_records,
    load_csicop_records,
    load_muller_lmt_records,
    sector_36_to_12,
)


def _csv_bytes(fields: list[str], rows: list[list[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def _write_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "g5-tmp-g-sectors/cfepp-1120-nienhuys-raw.csv",
            _csv_bytes(
                ["UNIV_DATE", "UT", "LONG", "LAT", "S"],
                [["1900 01 02", "03 04", "-06.92", "+45.97", 1]],
            ),
        )
        archive.writestr(
            "g5-tmp-g-sectors/csicop-408-irving-raw.csv",
            _csv_bytes(
                [
                    "GEBDAT",
                    "GEBZEIT",
                    "AMPM",
                    "ZEITZONE",
                    "LO1",
                    "LO2",
                    "LA1",
                    "LA2",
                    "MARS",
                ],
                [
                    ["2 5 1934", "8 25", "P", "6", "88", "3", "30", "41", 36],
                    ["1 1 2000", "12 0", "P", "5", "75", "0", "40", "0", 1],
                ],
            ),
        )
        archive.writestr(
            "g5-tmp-g-sectors/ertel-4384-sport-raw.csv",
            _csv_bytes(["MARS", "MA12"], [[4, 2]]),
        )
        archive.writestr(
            "g5-tmp-g-sectors/muller5-1083-medics-raw.csv",
            _csv_bytes(
                ["GEBDATUM", "GEBZEIT", "LAENGE", "BREITE", "MODE", "MARS"],
                [["23.02.1817", "02.00", "000 E 05", "43 N 14", "LMT", 33]],
            ),
        )
        archive.writestr("g5-tmp-g-sectors/.~lock.muller.csv#", b"ignored")


def test_inventory_is_aggregate_and_proves_ertel_mapping(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    result = inventory_archive(archive_path)

    assert result["source_rows_total"] == 5
    assert result["privacy"] == "aggregate_only_no_personal_records_emitted"
    ertel = result["files"]["ertel-4384-sport-raw.csv"]
    assert ertel["mars_36_to_ma12_errors"] == 0
    assert "UNIV_DATE" not in str(result)


def test_cfepp_parser_uses_explicit_utc_and_converts_west_positive_longitude(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    records = load_cfepp_records(archive_path)

    assert len(records) == 1
    assert records[0].instant_utc.isoformat() == "1900-01-02T03:04:00+00:00"
    assert records[0].longitude_east_positive == pytest.approx(6.92)
    assert records[0].latitude == pytest.approx(45.97)
    assert records[0].source_sector_12 == 1


def test_csicop_parser_reproduces_g5_offset_and_longitude(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    records = load_csicop_records(
        archive_path, conventional_noon_midnight=False
    )

    assert len(records) == 2
    assert records[0].instant_utc.isoformat() == "1934-05-03T02:25:00+00:00"
    assert records[0].longitude_east_positive == pytest.approx(-88.05)
    assert records[0].latitude == pytest.approx(30.6833333333)
    assert records[0].source_sector_36 == 36


def test_csicop_parser_keeps_noon_midnight_policy_explicit(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    literal = load_csicop_records(
        archive_path, conventional_noon_midnight=False
    )
    conventional = load_csicop_records(
        archive_path, conventional_noon_midnight=True
    )

    assert literal[1].instant_utc.isoformat() == "2000-01-02T05:00:00+00:00"
    assert conventional[1].instant_utc.isoformat() == "2000-01-01T17:00:00+00:00"


def test_muller_lmt_parser_converts_mean_solar_time(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    records = load_muller_lmt_records(archive_path)

    assert len(records) == 1
    assert records[0].longitude_east_positive == pytest.approx(5 / 60)
    assert records[0].latitude == pytest.approx(43 + 14 / 60)
    assert records[0].instant_utc.isoformat() == "1817-02-23T01:59:40+00:00"
    assert records[0].source_sector_36 == 33


@pytest.mark.parametrize(
    ("sector_36", "sector_12"),
    [(1, 1), (3, 1), (4, 2), (34, 12), (36, 12)],
)
def test_sector_36_to_12(sector_36: int, sector_12: int) -> None:
    assert sector_36_to_12(sector_36) == sector_12


def test_circular_sector_distance_wraps() -> None:
    assert circular_sector_distance(12, 1, 12) == 1
    assert circular_sector_distance(1, 7, 12) == 6


def test_inventory_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../cfepp-1120-nienhuys-raw.csv", b"S\n1\n")

    with pytest.raises(ValueError, match="unsafe archive member"):
        inventory_archive(archive_path)
