"""Merge artifacts from parallel pytest-xdist workers into a single directory."""
from __future__ import annotations

import json
from pathlib import Path


def merge_durations(artifact_base: Path) -> dict[str, float]:
    """Merge durations.json from all worker sub-directories."""
    merged: dict[str, float] = {}
    for worker_dir in artifact_base.iterdir():
        if worker_dir.is_dir() and worker_dir.name.startswith("worker_"):
            path = worker_dir / "durations.json"
            if path.exists():
                try:
                    merged.update(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    pass
    return merged


def merge_failures(artifact_base: Path) -> list[str]:
    """Merge failures.txt from all worker sub-directories."""
    merged: list[str] = []
    for worker_dir in artifact_base.iterdir():
        if worker_dir.is_dir() and worker_dir.name.startswith("worker_"):
            path = worker_dir / "failures.txt"
            if path.exists():
                try:
                    merged.extend(path.read_text(encoding="utf-8").splitlines())
                except Exception:
                    pass
    return merged
