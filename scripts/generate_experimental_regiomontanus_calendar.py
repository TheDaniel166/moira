from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from moira.experimental_regiomontanus import (
    ExperimentalRegiomontanusStatus,
    search_experimental_regiomontanus,
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
CALENDAR_CSV = REPORTS_DIR / "experimental_regiomontanus_greenwich_2000_2h_daily_calendar.csv"
SUMMARY_JSON = REPORTS_DIR / "experimental_regiomontanus_greenwich_2000_2h_daily_calendar_summary.json"
SLOT_LABELS = tuple(f"{hour:02d}" for hour in range(0, 24, 2))


@dataclass(frozen=True, slots=True)
class TimestampMeta:
    dt: datetime
    jd_ut: float
    armc: float
    obliquity: float
    slot_label: str


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


def _evaluate_slot(latitude: float, ts: TimestampMeta) -> bool:
    asc = _asc_from_armc(ts.armc, ts.obliquity, latitude)
    mc = _mc_from_armc(ts.armc, ts.obliquity, latitude)
    result = search_experimental_regiomontanus(
        ts.armc,
        ts.obliquity,
        latitude,
        asc=asc,
        mc=mc,
    )
    return result.status == ExperimentalRegiomontanusStatus.UNIQUE_ORDERED_SOLUTION


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    latitudes = _build_latitudes()
    timestamps = _build_timestamps()
    dates = sorted({ts.dt.date().isoformat() for ts in timestamps})

    with CALENDAR_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
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
                *[f"slot_{label}" for label in SLOT_LABELS],
            ],
        )
        writer.writeheader()

        latitude_summaries: list[dict[str, object]] = []
        total_day_rows = 0

        for latitude in latitudes:
            total_pass_days = 0
            total_fail_days = 0
            total_mixed_days = 0
            first_success_date: str | None = None
            last_success_date: str | None = None

            current_date: str | None = None
            day_slots: dict[str, str] = {}
            pass_count = 0
            fail_count = 0
            first_pass_utc: str | None = None
            last_pass_utc: str | None = None

            def flush_day() -> None:
                nonlocal total_day_rows
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
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "success_fraction": pass_count / len(SLOT_LABELS),
                    "any_pass": pass_count > 0,
                    "all_pass": fail_count == 0,
                    "all_fail": pass_count == 0,
                    "first_pass_utc": first_pass_utc or "",
                    "last_pass_utc": last_pass_utc or "",
                }
                for label in SLOT_LABELS:
                    row[f"slot_{label}"] = day_slots.get(label, "")
                writer.writerow(row)
                total_day_rows += 1

                if pass_count == len(SLOT_LABELS):
                    total_pass_days += 1
                elif pass_count == 0:
                    total_fail_days += 1
                else:
                    total_mixed_days += 1

                if pass_count > 0:
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
                    pass_count = 0
                    fail_count = 0
                    first_pass_utc = None
                    last_pass_utc = None

                succeeded = _evaluate_slot(latitude, ts)
                day_slots[ts.slot_label] = "P" if succeeded else "F"
                if succeeded:
                    pass_count += 1
                    if first_pass_utc is None:
                        first_pass_utc = ts.dt.isoformat()
                    last_pass_utc = ts.dt.isoformat()
                else:
                    fail_count += 1

            flush_day()

            latitude_summaries.append(
                {
                    "latitude": latitude,
                    "day_count": len(dates),
                    "all_pass_days": total_pass_days,
                    "all_fail_days": total_fail_days,
                    "mixed_days": total_mixed_days,
                    "first_success_date_utc": first_success_date,
                    "last_success_date_utc": last_success_date,
                }
            )

    summary = {
        "calendar": {
            "system": "Regiomontanus experimental",
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
            "calendar_rows": total_day_rows,
            "output_csv": str(CALENDAR_CSV).replace("\\", "/"),
        },
        "latitude_summaries": latitude_summaries,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"wrote {CALENDAR_CSV}")
    print(f"wrote {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
