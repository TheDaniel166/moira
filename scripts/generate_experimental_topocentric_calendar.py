from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from moira.experimental_topocentric import (
    ExperimentalTopocentricStatus,
    search_experimental_topocentric,
)
from moira.houses import _asc_from_armc, _mc_from_armc
from moira.julian import jd_from_datetime, local_sidereal_time, ut_to_tt
from moira.obliquity import true_obliquity


UTC = timezone.utc
START = datetime(2000, 1, 1, 0, 0, tzinfo=UTC)
END = datetime(2000, 12, 31, 22, 0, tzinfo=UTC)
STEP = timedelta(hours=2)
LONGITUDE = 0.0
LATITUDE_START = 66.6
LATITUDE_END = 89.9
LATITUDE_STEP = 0.1
REPORTS_DIR = Path("reports/validation")
BY_LATITUDE_CSV = REPORTS_DIR / "experimental_topocentric_greenwich_2000_2h_by_latitude.csv"
SUMMARY_JSON = REPORTS_DIR / "experimental_topocentric_greenwich_2000_2h_summary.json"
CALENDAR_CSV = REPORTS_DIR / "experimental_topocentric_greenwich_2000_2h_daily_calendar.csv"
CALENDAR_SUMMARY_JSON = REPORTS_DIR / "experimental_topocentric_greenwich_2000_2h_daily_calendar_summary.json"
SLOT_LABELS = tuple(f"{hour:02d}" for hour in range(0, 24, 2))
STATUS_ORDER = (
    ExperimentalTopocentricStatus.UNIQUE_ORDERED_SOLUTION,
    ExperimentalTopocentricStatus.ASSEMBLY_FAILED,
    ExperimentalTopocentricStatus.UNORDERED_CUSP_CYCLE,
)
STATUS_CODE = {
    ExperimentalTopocentricStatus.UNIQUE_ORDERED_SOLUTION: "U",
    ExperimentalTopocentricStatus.ASSEMBLY_FAILED: "A",
    ExperimentalTopocentricStatus.UNORDERED_CUSP_CYCLE: "O",
}


@dataclass(frozen=True, slots=True)
class TimestampMeta:
    dt: datetime
    jd_ut: float
    armc: float
    obliquity: float
    slot_label: str


def _status_count_fields() -> list[str]:
    return [f"{status.value}_count" for status in STATUS_ORDER]


def _frange(start: float, end: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= end + 1e-12:
        values.append(round(current, 1))
        current += step
    return values


def _build_latitudes() -> list[float]:
    north = _frange(LATITUDE_START, LATITUDE_END, LATITUDE_STEP)
    south = [-value for value in reversed(north)]
    return south + north


def _build_timestamps() -> list[TimestampMeta]:
    timestamps: list[TimestampMeta] = []
    current = START
    while current <= END:
        jd_ut = jd_from_datetime(current)
        timestamps.append(
            TimestampMeta(
                dt=current,
                jd_ut=jd_ut,
                armc=local_sidereal_time(jd_ut, LONGITUDE),
                obliquity=true_obliquity(ut_to_tt(jd_ut)),
                slot_label=f"{current.hour:02d}",
            )
        )
        current += STEP
    return timestamps


def _evaluate(
    latitude: float,
    ts: TimestampMeta,
) -> tuple[ExperimentalTopocentricStatus, tuple[float, ...] | None]:
    asc = _asc_from_armc(ts.armc, ts.obliquity, latitude)
    mc = _mc_from_armc(ts.armc, ts.obliquity, latitude)
    result = search_experimental_topocentric(
        ts.armc,
        ts.obliquity,
        latitude,
        asc=asc,
        mc=mc,
    )
    return result.status, result.cusps


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    latitudes = _build_latitudes()
    timestamps = _build_timestamps()
    dates = sorted({ts.dt.date().isoformat() for ts in timestamps})

    by_latitude_rows: list[dict[str, object]] = []
    sample_first_success_by_latitude: list[dict[str, object]] = []
    calendar_summaries: list[dict[str, object]] = []

    with CALENDAR_CSV.open("w", newline="", encoding="utf-8") as calendar_handle:
        calendar_writer = csv.DictWriter(
            calendar_handle,
            fieldnames=[
                "latitude",
                "date",
                "pass_count",
                "fail_count",
                "success_fraction",
                "any_pass",
                "all_pass",
                "all_fail",
                "first_pass_utc",
                "last_pass_utc",
                *_status_count_fields(),
                *[f"slot_{label}" for label in SLOT_LABELS],
            ],
        )
        calendar_writer.writeheader()

        for latitude in latitudes:
            success_count = 0
            total_count = 0
            status_counts = {status: 0 for status in STATUS_ORDER}
            first_success_datetime: str | None = None
            last_success_datetime: str | None = None
            first_success_payload: dict[str, object] | None = None

            total_pass_days = 0
            total_fail_days = 0
            total_mixed_days = 0
            first_success_date: str | None = None
            last_success_date: str | None = None

            current_date: str | None = None
            day_slots: dict[str, str] = {}
            day_status_counts = {status: 0 for status in STATUS_ORDER}
            day_pass_count = 0
            day_fail_count = 0
            day_first_pass: str | None = None
            day_last_pass: str | None = None

            def flush_day() -> None:
                nonlocal total_pass_days
                nonlocal total_fail_days
                nonlocal total_mixed_days
                nonlocal first_success_date
                nonlocal last_success_date
                if current_date is None:
                    return

                row = {
                    "latitude": f"{latitude:.1f}",
                    "date": current_date,
                    "pass_count": day_pass_count,
                    "fail_count": day_fail_count,
                    "success_fraction": day_pass_count / len(SLOT_LABELS),
                    "any_pass": day_pass_count > 0,
                    "all_pass": day_fail_count == 0,
                    "all_fail": day_pass_count == 0,
                    "first_pass_utc": day_first_pass or "",
                    "last_pass_utc": day_last_pass or "",
                }
                for status in STATUS_ORDER:
                    row[f"{status.value}_count"] = day_status_counts[status]
                for label in SLOT_LABELS:
                    row[f"slot_{label}"] = day_slots.get(label, "")
                calendar_writer.writerow(row)

                if day_pass_count == len(SLOT_LABELS):
                    total_pass_days += 1
                elif day_pass_count == 0:
                    total_fail_days += 1
                else:
                    total_mixed_days += 1

                if day_pass_count > 0:
                    first_success_date = first_success_date or current_date
                    last_success_date = current_date

            for ts in timestamps:
                ts_date = ts.dt.date().isoformat()
                if current_date is None:
                    current_date = ts_date
                elif ts_date != current_date:
                    flush_day()
                    current_date = ts_date
                    day_slots = {}
                    day_status_counts = {status: 0 for status in STATUS_ORDER}
                    day_pass_count = 0
                    day_fail_count = 0
                    day_first_pass = None
                    day_last_pass = None

                status, cusps = _evaluate(latitude, ts)
                succeeded = status == ExperimentalTopocentricStatus.UNIQUE_ORDERED_SOLUTION
                total_count += 1
                status_counts[status] += 1
                day_status_counts[status] += 1
                day_slots[ts.slot_label] = STATUS_CODE[status]

                if succeeded:
                    success_count += 1
                    success_iso = ts.dt.isoformat()
                    first_success_datetime = first_success_datetime or success_iso
                    last_success_datetime = success_iso
                    day_pass_count += 1
                    if day_first_pass is None:
                        day_first_pass = success_iso
                    day_last_pass = success_iso
                    if first_success_payload is None and cusps is not None:
                        first_success_payload = {
                            "datetime_utc": success_iso,
                            "jd_ut": ts.jd_ut,
                            "latitude": latitude,
                            "longitude": LONGITUDE,
                            "armc": ts.armc,
                            "cusps": [round(value, 12) for value in cusps],
                        }
                else:
                    day_fail_count += 1

            flush_day()

            success_fraction = success_count / total_count if total_count else 0.0
            by_latitude_row = {
                "latitude": f"{latitude:.1f}",
                "success_count": success_count,
                "total_count": total_count,
                "success_fraction": success_fraction,
                "first_success_datetime_utc": first_success_datetime or "",
                "last_success_datetime_utc": last_success_datetime or "",
            }
            for status in STATUS_ORDER:
                by_latitude_row[f"{status.value}_count"] = status_counts[status]
            by_latitude_rows.append(by_latitude_row)

            if first_success_payload is not None:
                sample_first_success_by_latitude.append(first_success_payload)

            calendar_summary = {
                "latitude": latitude,
                "day_count": len(dates),
                "all_pass_days": total_pass_days,
                "all_fail_days": total_fail_days,
                "mixed_days": total_mixed_days,
                "first_success_date_utc": first_success_date,
                "last_success_date_utc": last_success_date,
            }
            for status in STATUS_ORDER:
                calendar_summary[f"{status.value}_count"] = status_counts[status]
            calendar_summaries.append(calendar_summary)

    with BY_LATITUDE_CSV.open("w", newline="", encoding="utf-8") as by_latitude_handle:
        writer = csv.DictWriter(
            by_latitude_handle,
            fieldnames=[
                "latitude",
                "success_count",
                "total_count",
                "success_fraction",
                "first_success_datetime_utc",
                "last_success_datetime_utc",
                *_status_count_fields(),
            ],
        )
        writer.writeheader()
        writer.writerows(by_latitude_rows)

    latitudes_with_any_success = sum(1 for row in by_latitude_rows if int(row["success_count"]) > 0)
    best_row = max(by_latitude_rows, key=lambda row: float(row["success_fraction"]))
    worst_row = min(by_latitude_rows, key=lambda row: float(row["success_fraction"]))

    SUMMARY_JSON.write_text(
        json.dumps(
            {
                "sweep": {
                    "system": "Topocentric experimental",
                    "date_start_utc": START.isoformat(),
                    "date_end_utc": END.isoformat(),
                    "cadence_hours": 2,
                    "longitude_deg": LONGITUDE,
                    "latitudes_deg": {
                        "min": -LATITUDE_END,
                        "max": LATITUDE_END,
                        "step": LATITUDE_STEP,
                        "sampled_polar_band_start": LATITUDE_START,
                        "count": len(latitudes),
                    },
                    "timestamp_count": len(timestamps),
                    "evaluation_count": len(latitudes) * len(timestamps),
                },
                "aggregate": {
                    "latitudes_with_any_success": latitudes_with_any_success,
                    "status_totals": {
                        status.value: sum(int(row[f"{status.value}_count"]) for row in by_latitude_rows)
                        for status in STATUS_ORDER
                    },
                    "best_latitude_by_fraction": {
                        "latitude": float(best_row["latitude"]),
                        "success_count": int(best_row["success_count"]),
                        "total_count": int(best_row["total_count"]),
                        "success_fraction": float(best_row["success_fraction"]),
                        "first_success_datetime_utc": best_row["first_success_datetime_utc"],
                        "last_success_datetime_utc": best_row["last_success_datetime_utc"],
                        **{
                            f"{status.value}_count": int(best_row[f"{status.value}_count"])
                            for status in STATUS_ORDER
                        },
                    },
                    "worst_latitude_by_fraction": {
                        "latitude": float(worst_row["latitude"]),
                        "success_count": int(worst_row["success_count"]),
                        "total_count": int(worst_row["total_count"]),
                        "success_fraction": float(worst_row["success_fraction"]),
                        "first_success_datetime_utc": worst_row["first_success_datetime_utc"],
                        "last_success_datetime_utc": worst_row["last_success_datetime_utc"],
                        **{
                            f"{status.value}_count": int(worst_row[f"{status.value}_count"])
                            for status in STATUS_ORDER
                        },
                    },
                },
                "sample_first_success_by_latitude": sample_first_success_by_latitude,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    CALENDAR_SUMMARY_JSON.write_text(
        json.dumps(
            {
                "calendar": {
                    "system": "Topocentric experimental",
                    "date_start_utc": START.isoformat(),
                    "date_end_utc": END.isoformat(),
                    "cadence_hours": 2,
                    "longitude_deg": LONGITUDE,
                    "latitude_range_deg": {
                        "min": -LATITUDE_END,
                        "max": LATITUDE_END,
                        "step": LATITUDE_STEP,
                        "sampled_polar_band_start": LATITUDE_START,
                        "count": len(latitudes),
                    },
                    "dates": len(dates),
                    "slots_per_day": len(SLOT_LABELS),
                    "calendar_rows": len(latitudes) * len(dates),
                    "output_csv": str(CALENDAR_CSV).replace("\\", "/"),
                },
                "latitude_summaries": calendar_summaries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"wrote {BY_LATITUDE_CSV}")
    print(f"wrote {SUMMARY_JSON}")
    print(f"wrote {CALENDAR_CSV}")
    print(f"wrote {CALENDAR_SUMMARY_JSON}")


if __name__ == "__main__":
    main()
