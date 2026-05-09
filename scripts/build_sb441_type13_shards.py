from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from moira.asteroids import ASTEROID_NAIF
from moira._kernel_paths import find_kernel
from moira._spk_body_kernel import SmallBodyKernel
from moira.daf_writer import write_spk_type13
from moira.julian import julian_day
from moira.spk_reader import SpkReader

SOURCE_KERNEL_NAME = "sb441-n373s.bsp"
DEFAULT_OUTPUT_DIR = ROOT / "tests" / "artifacts" / "kernels" / "sb441_type13_shards"
DEFAULT_SHARD_SIZE = 25
SECONDS_PER_DAY = 86400.0


def _naif_to_name_map() -> dict[int, str]:
    return {naif_id: name for name, naif_id in ASTEROID_NAIF.items()}


def _generate_epochs(start_jd: float, end_jd: float, step_days: int) -> list[float]:
    if end_jd <= start_jd:
        raise ValueError("end_jd must be greater than start_jd")
    if step_days <= 0:
        raise ValueError("step_days must be positive")

    epochs: list[float] = []
    jd = start_jd
    while jd < end_jd:
        epochs.append(float(jd))
        jd += step_days
    if not epochs or epochs[-1] != float(end_jd):
        epochs.append(float(end_jd))
    return epochs


def _sample_body(reader: SpkReader, naif_id: int, epochs_jd: list[float]) -> list[list[float]]:
    states = [[] for _ in range(6)]
    for jd in epochs_jd:
        pos, vel_km_day = reader.position_and_velocity(10, naif_id, jd)
        states[0].append(float(pos[0]))
        states[1].append(float(pos[1]))
        states[2].append(float(pos[2]))
        states[3].append(float(vel_km_day[0] / SECONDS_PER_DAY))
        states[4].append(float(vel_km_day[1] / SECONDS_PER_DAY))
        states[5].append(float(vel_km_day[2] / SECONDS_PER_DAY))
    return states


def _verify_shard(path: Path, shard_bodies: list[dict]) -> dict[str, dict[str, float]]:
    kernel = SmallBodyKernel(path)
    try:
        out: dict[str, dict[str, float]] = {}
        for body in shard_bodies:
            naif_id = int(body["naif_id"])
            epochs_jd = body["epochs_jd"]
            states = body["states"]
            max_node_error_km = 0.0
            for i, jd in enumerate(epochs_jd):
                got = kernel.position(naif_id, jd)
                want = (states[0][i], states[1][i], states[2][i])
                err = max(abs(a - b) for a, b in zip(got, want))
                max_node_error_km = max(max_node_error_km, err)
            out[str(naif_id)] = {
                "max_node_error_km": max_node_error_km,
                "epoch_count": float(len(epochs_jd)),
            }
        return out
    finally:
        kernel.close()


def _chunk(items: list[int], size: int) -> list[list[int]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcode sb441 small-body states into sharded Moira-owned type-13 kernels."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start-date", default="2020-01-01", help="Gregorian UTC date, YYYY-MM-DD.")
    parser.add_argument("--end-date", default="2030-01-01", help="Gregorian UTC date, YYYY-MM-DD.")
    parser.add_argument("--step-days", type=int, default=30)
    parser.add_argument("--window-size", type=int, default=5)
    parser.add_argument("--shard-size", type=int, default=DEFAULT_SHARD_SIZE)
    parser.add_argument("--body", action="append", default=[], help="Repeatable asteroid name or NAIF ID.")
    parser.add_argument("--limit-bodies", type=int, default=0, help="Optional body-count cap for smoke builds.")
    args = parser.parse_args()
    args.output_dir = args.output_dir if args.output_dir.is_absolute() else (ROOT / args.output_dir)

    source_path = find_kernel(SOURCE_KERNEL_NAME)
    if not source_path.exists():
        raise FileNotFoundError(f"Source kernel not found: {source_path}")

    start_y, start_m, start_d = map(int, args.start_date.split("-"))
    end_y, end_m, end_d = map(int, args.end_date.split("-"))
    global_start_jd = julian_day(start_y, start_m, start_d, 0.0)
    global_end_jd = julian_day(end_y, end_m, end_d, 0.0)

    reader = SpkReader(source_path)
    try:
        covered_ids = sorted(
            naif_id for naif_id in reader.covered_bodies()
            if reader.has_segment(10, naif_id)
        )
        name_by_id = _naif_to_name_map()

        if args.body:
            selected_ids: list[int] = []
            for raw in args.body:
                raw = str(raw).strip()
                if raw.isdigit():
                    selected_ids.append(int(raw))
                else:
                    selected_ids.append(ASTEROID_NAIF[raw])
        else:
            selected_ids = [naif_id for naif_id in covered_ids if naif_id in name_by_id]

        if args.limit_bodies > 0:
            selected_ids = selected_ids[:args.limit_bodies]
        if not selected_ids:
            raise RuntimeError("No bodies selected for transcode.")

        args.output_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "source_kernel": str(source_path),
            "source_kernel_name": SOURCE_KERNEL_NAME,
            "global_sampling": {
                "start_date": args.start_date,
                "end_date": args.end_date,
                "step_days": args.step_days,
                "window_size": args.window_size,
                "shard_size": args.shard_size,
            },
            "body_count": len(selected_ids),
            "shards": [],
        }

        for shard_index, shard_ids in enumerate(_chunk(selected_ids, args.shard_size), start=1):
            shard_bodies: list[dict] = []
            shard_summary: list[dict] = []
            for naif_id in shard_ids:
                coverage = reader.epoch_range(10, naif_id)
                if coverage is None:
                    continue
                start_jd = max(global_start_jd, float(coverage[0]))
                end_jd = min(global_end_jd, float(coverage[1]))
                if end_jd <= start_jd:
                    continue

                epochs_jd = _generate_epochs(start_jd, end_jd, args.step_days)
                states = _sample_body(reader, naif_id, epochs_jd)
                name = name_by_id.get(naif_id, f"NAIF-{naif_id}")

                shard_bodies.append({
                    "naif_id": naif_id,
                    "name": name,
                    "center": 10,
                    "frame": 1,
                    "states": states,
                    "epochs_jd": epochs_jd,
                    "window_size": args.window_size,
                })
                shard_summary.append({
                    "name": name,
                    "naif_id": naif_id,
                    "start_jd": epochs_jd[0],
                    "end_jd": epochs_jd[-1],
                    "epoch_count": len(epochs_jd),
                })

            if not shard_bodies:
                continue

            shard_path = args.output_dir / f"sb441_type13_shard_{shard_index:03d}.bsp"
            write_spk_type13(
                shard_path,
                shard_bodies,
                locifn=f"MOIRA SB441 TYPE13 SHARD {shard_index:03d}",
            )
            verification = _verify_shard(shard_path, shard_bodies)

            manifest["shards"].append({
                "index": shard_index,
                "path": str(shard_path.relative_to(ROOT)),
                "body_count": len(shard_bodies),
                "bodies": shard_summary,
                "verification": verification,
            })

        manifest_path = args.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({
            "manifest": str(manifest_path.relative_to(ROOT)),
            "shard_count": len(manifest["shards"]),
            "body_count": manifest["body_count"],
        }, indent=2))
    finally:
        reader.close()


if __name__ == "__main__":
    main()
