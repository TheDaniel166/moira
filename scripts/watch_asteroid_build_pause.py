"""Post-process asteroid-family JSON after a timed shard build exits."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.refresh_asteroid_family_annotations import refresh


def _windows_process_is_running(process_id: int) -> bool:
    synchronize = 0x00100000
    wait_timeout = 0x00000102
    handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, process_id)
    if not handle:
        return False
    try:
        return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == wait_timeout
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _process_is_running(process_id: int) -> bool:
    if os.name == "nt":
        return _windows_process_is_running(process_id)
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    args = parser.parse_args()
    if args.pid <= 0:
        parser.error("--pid must be positive")
    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be positive")

    started_at = datetime.now(timezone.utc).isoformat()
    while _process_is_running(args.pid):
        time.sleep(args.poll_seconds)

    refresh_receipt = args.metadata_dir / "family_annotation_receipt.json"
    refresh(args.targets, args.metadata_dir, refresh_receipt)
    watcher_receipt = {
        "started_at_utc": started_at,
        "detected_build_exit_at_utc": datetime.now(timezone.utc).isoformat(),
        "watched_process_id": args.pid,
        "action": "family_annotation_refresh_after_timed_build_exit",
        "refresh_receipt": str(refresh_receipt.resolve()),
        "automatic_restart": False,
    }
    (args.metadata_dir / "pause_postprocess_receipt.json").write_text(
        json.dumps(watcher_receipt, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
