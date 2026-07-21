from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.validate_g5_gauquelin_sectors as validation
from scripts.validate_g5_gauquelin_sectors import (
    _distance_to_boundary,
    build_report,
    circular_sector_distance,
    inventory_archive,
    load_cfepp_records,
    load_csicop_records,
    load_muller_lmt_records,
    main,
    sector_36_to_12,
)


_CFEPP_FIELDS = ["UNIV_DATE", "UT", "LONG", "LAT", "S"]
_CSICOP_FIELDS = [
    "GEBDAT",
    "GEBZEIT",
    "AMPM",
    "ZEITZONE",
    "LO1",
    "LO2",
    "LA1",
    "LA2",
    "MARS",
]
_MULLER_FIELDS = ["GEBDATUM", "GEBZEIT", "LAENGE", "BREITE", "MODE", "MARS"]

_DEFAULT_CFEPP_ROWS = [["1900 01 02", "03 04", "-06.92", "+45.97", 1]]
_DEFAULT_CSICOP_ROWS = [
    ["2 5 1934", "8 25", "P", "6", "88", "3", "30", "41", 36],
    ["1 1 2000", "12 0", "P", "5", "75", "0", "40", "0", 1],
]
_DEFAULT_ERTEL_ROWS = [[4, 2]]
_DEFAULT_MULLER_ROWS = [
    ["23.02.1817", "02.00", "000 E 05", "43 N 14", "LMT", 33]
]


def _csv_bytes(fields: list[str], rows: list[list[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def _write_fixture(
    path: Path,
    *,
    cfepp_rows: list[list[object]] | None = None,
    csicop_rows: list[list[object]] | None = None,
    ertel_rows: list[list[object]] | None = None,
    muller_rows: list[list[object]] | None = None,
    omitted: frozenset[str] = frozenset(),
    include_extra: bool = False,
) -> None:
    members = {
        "cfepp-1120-nienhuys-raw.csv": (
            _CFEPP_FIELDS,
            _DEFAULT_CFEPP_ROWS if cfepp_rows is None else cfepp_rows,
        ),
        "csicop-408-irving-raw.csv": (
            _CSICOP_FIELDS,
            _DEFAULT_CSICOP_ROWS if csicop_rows is None else csicop_rows,
        ),
        "ertel-4384-sport-raw.csv": (
            ["MARS", "MA12"],
            _DEFAULT_ERTEL_ROWS if ertel_rows is None else ertel_rows,
        ),
        "muller5-1083-medics-raw.csv": (
            _MULLER_FIELDS,
            _DEFAULT_MULLER_ROWS if muller_rows is None else muller_rows,
        ),
    }
    with zipfile.ZipFile(path, "w") as archive:
        for basename, (fields, rows) in members.items():
            if basename not in omitted:
                archive.writestr(
                    f"g5-tmp-g-sectors/{basename}", _csv_bytes(fields, rows)
                )
        archive.writestr("g5-tmp-g-sectors/.~lock.muller.csv#", b"ignored")
        if include_extra:
            archive.writestr(
                "g5-tmp-g-sectors/unexpected.csv", _csv_bytes(["S"], [[1]])
            )


def _allow_synthetic_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validation,
        "EXPECTED_WITNESS_ROWS",
        {
            "cfepp-1120-nienhuys-raw.csv": 1,
            "csicop-408-irving-raw.csv": 2,
            "ertel-4384-sport-raw.csv": 1,
            "muller5-1083-medics-raw.csv": 1,
        },
    )


def _fake_compute(_engine: object, request: object) -> object:
    sector = {1817: 33, 1900: 1, 1934: 36, 2000: 1}[request.dt.year]
    position = SimpleNamespace(
        sector=sector,
        diurnal_position=(sector - 1) * 10.0 + 1.0,
    )
    return SimpleNamespace(
        positions=[SimpleNamespace(position=position)]
    )


def _install_fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validation, "Moira", lambda: object())
    monkeypatch.setattr(validation, "compute_gauquelin_chart_sectors", _fake_compute)


def test_inventory_is_aggregate_and_proves_ertel_mapping(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    result = inventory_archive(archive_path, enforce_witness_counts=False)

    assert result["source_rows_total"] == 5
    assert result["privacy"] == "aggregate_only_no_personal_records_emitted"
    ertel = result["files"]["ertel-4384-sport-raw.csv"]
    assert ertel["mars_36_to_ma12_errors"] == 0
    assert "UNIV_DATE" not in str(result)


def test_inventory_enforces_sanctioned_witness_row_counts(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)

    with pytest.raises(ValueError, match="expected 1120 witness rows, found 1"):
        inventory_archive(archive_path)


@pytest.mark.parametrize(
    ("omitted", "include_extra"),
    [
        (frozenset({"cfepp-1120-nienhuys-raw.csv"}), False),
        (frozenset(), True),
    ],
)
def test_inventory_rejects_missing_or_extra_csvs(
    tmp_path: Path, omitted: frozenset[str], include_extra: bool
) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path, omitted=omitted, include_extra=include_extra)

    with pytest.raises(ValueError, match="archive CSV set mismatch"):
        inventory_archive(archive_path, enforce_witness_counts=False)


def test_inventory_rejects_out_of_range_sector(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(
        archive_path,
        cfepp_rows=[["1900 01 02", "03 04", "-06.92", "+45.97", 13]],
    )

    with pytest.raises(ValueError, match=r"must be populated in \[1, 12\]"):
        inventory_archive(archive_path, enforce_witness_counts=False)


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


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (["bad date", "03 04", "-06.92", "+45.97", 1], "invalid CFEPP row"),
        (["1900 01 02", "03 04", "200", "+45.97", 1], "invalid CFEPP coordinates"),
        (["1900 01 02", "03 04", "-06.92", "+45.97", 13], "invalid CFEPP sector"),
    ],
)
def test_cfepp_parser_rejects_invalid_rows(
    tmp_path: Path, row: list[object], message: str
) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path, cfepp_rows=[row])

    with pytest.raises(ValueError, match=message):
        load_cfepp_records(archive_path)


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


def test_csicop_parser_preserves_special_g5_offset(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    row = ["2 5 1934", "8 25", "A", "0,5", "157", "50", "21", "18", 1]
    _write_fixture(archive_path, csicop_rows=[row])

    records = load_csicop_records(
        archive_path, conventional_noon_midnight=False
    )

    assert records[0].instant_utc.isoformat() == "1934-05-02T18:55:00+00:00"


@pytest.mark.parametrize(("ampm", "timezone"), [("X", "6"), ("A", "9")])
def test_csicop_parser_rejects_unknown_clock_semantics(
    tmp_path: Path, ampm: str, timezone: str
) -> None:
    archive_path = tmp_path / "sectors.zip"
    row = ["2 5 1934", "8 25", ampm, timezone, "88", "3", "30", "41", 36]
    _write_fixture(archive_path, csicop_rows=[row])

    with pytest.raises(
        ValueError,
        match=(
            "invalid CSICOP row 2: unknown AM/PM marker"
            if ampm == "X"
            else "invalid CSICOP row 2: unsupported CSICOP timezone '9'"
        ),
    ):
        load_csicop_records(archive_path, conventional_noon_midnight=False)


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
    assert literal[1].longitude_east_positive == pytest.approx(
        conventional[1].longitude_east_positive
    )
    assert literal[1].latitude == pytest.approx(conventional[1].latitude)
    assert literal[1].source_sector_36 == conventional[1].source_sector_36


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
    ("longitude", "latitude", "message"),
    [
        ("000 Q 05", "43 N 14", "invalid Muller LMT row"),
        ("181 E 00", "43 N 14", "invalid Muller coordinates"),
    ],
)
def test_muller_lmt_parser_rejects_invalid_coordinates(
    tmp_path: Path, longitude: str, latitude: str, message: str
) -> None:
    archive_path = tmp_path / "sectors.zip"
    row = ["23.02.1817", "02.00", longitude, latitude, "LMT", 33]
    _write_fixture(archive_path, muller_rows=[row])

    with pytest.raises(ValueError, match=message):
        load_muller_lmt_records(archive_path)


def test_muller_parser_ignores_non_lmt_rows_before_parsing(tmp_path: Path) -> None:
    archive_path = tmp_path / "sectors.zip"
    row = ["bad", "bad", "bad", "bad", "", 33]
    _write_fixture(archive_path, muller_rows=[row])

    assert load_muller_lmt_records(archive_path) == []


@pytest.mark.parametrize(
    ("sector_36", "sector_12"),
    [(1, 1), (3, 1), (4, 2), (34, 12), (36, 12)],
)
def test_sector_36_to_12(sector_36: int, sector_12: int) -> None:
    assert sector_36_to_12(sector_36) == sector_12


@pytest.mark.parametrize("sector", [0, 37])
def test_sector_36_to_12_rejects_invalid_value(sector: int) -> None:
    with pytest.raises(ValueError, match=r"36-sector value must be in \[1, 36\]"):
        sector_36_to_12(sector)


def test_circular_sector_distance_wraps() -> None:
    assert circular_sector_distance(12, 1, 12) == 1
    assert circular_sector_distance(1, 7, 12) == 6


def test_boundary_distance_requires_defined_position() -> None:
    with pytest.raises(RuntimeError, match="missing its diurnal position"):
        _distance_to_boundary(None, 10.0)


def test_build_report_exercises_all_comparison_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = tmp_path / "sectors.zip"
    _write_fixture(archive_path)
    _allow_synthetic_counts(monkeypatch)
    _install_fake_engine(monkeypatch)

    report = build_report(archive_path, limit=1)

    assert report["schema"] == "moira.gauquelin.g5_validation.v1"
    assert report["inventory"]["source_rows_total"] == 5
    assert report["cfepp_numerical_comparison"]["exact"] == 1
    assert report["cfepp_numerical_comparison"]["rows_available"] == 1
    assert report["csicop_numerical_comparison"]["declared"]["exact"] == 1
    assert report["csicop_numerical_comparison"]["sensitivity"]["exact"] == 1
    assert report["muller_lmt_numerical_comparison"]["exact"] == 1
    assert report["muller_lmt_numerical_comparison"]["rows_available"] == 1
    assert report["muller_lmt_numerical_comparison"]["rows_lmt"] == 1
    assert report["muller_lmt_numerical_comparison"]["rows_non_lmt_deferred"] == 0


def test_main_writes_json_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = tmp_path / "sectors.zip"
    output_path = tmp_path / "report.json"
    _write_fixture(archive_path)
    _allow_synthetic_counts(monkeypatch)
    _install_fake_engine(monkeypatch)

    result = main(
        [str(archive_path), "--limit", "1", "--output", str(output_path)]
    )

    assert result == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["schema"] == "moira.gauquelin.g5_validation.v1"
    assert report["inventory"]["privacy"] == "aggregate_only_no_personal_records_emitted"


def test_inventory_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../cfepp-1120-nienhuys-raw.csv", b"S\n1\n")

    with pytest.raises(ValueError, match="unsafe archive member"):
        inventory_archive(archive_path, enforce_witness_counts=False)
