"""Contract tests for resumable provisional solar evidence."""

from __future__ import annotations

import csv
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "scripts" / "eclipse_catalog"))
    return importlib.import_module("solar_supplement")


class _Reader:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_failed_row_retries_without_erasing_previous_chunk(
    module, monkeypatch, tmp_path
):
    kernel = tmp_path / "kernel.bsp"
    kernel.write_bytes(b"test kernel")
    detail = tmp_path / "detail.csv"
    with detail.open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, ["lunation_number", "jd_ut1", "status"])
        writer.writeheader()
        writer.writerow({"lunation_number": 300, "jd_ut1": 2460409.0, "status": "ok"})
    discovery = tmp_path / "discovery.json"
    discovery.write_text(
        json.dumps({"source_fingerprint_sha256": "discovery"}), encoding="utf8"
    )
    source = {
        "engine_package_sha256": "engine",
        "native_source_sha256": "native",
        "runner_sha256": "generator",
    }
    detail_receipt = tmp_path / "detail.metadata.json"
    detail_receipt.write_text(
        json.dumps(
            {
                "merged_sha256": module.sha256(detail),
                "kernel_sha256": module.sha256(kernel),
                "row_count": 1,
                "common": {
                    **source,
                    "event_index_receipt": str(discovery),
                    "event_index_receipt_sha256": module.sha256(discovery),
                },
            }
        ),
        encoding="utf8",
    )
    monkeypatch.setattr(module, "find_planetary_kernel", lambda: kernel)
    monkeypatch.setattr(module, "source_fingerprint", lambda: source)
    monkeypatch.setattr(module, "discovery_fingerprint", lambda: "discovery")
    monkeypatch.setattr(module, "SpkReader", _Reader)
    monkeypatch.setattr(module, "EclipseCalculator", lambda **kwargs: object())
    attempts = []

    def inspect(calc, row, arc_samples, max_evaluations):
        attempts.append(1)
        return {
            "lunation_number": int(row["lunation_number"]),
            "status": "error" if len(attempts) == 1 else "ok",
        }

    monkeypatch.setattr(module, "inspect_event", inspect)
    out = tmp_path / "result"
    args = [
        "--detail",
        str(detail),
        "--detail-receipt",
        str(detail_receipt),
        "--directory",
        str(out),
        "--kernel-sha256",
        module.sha256(kernel),
    ]
    with pytest.raises(RuntimeError, match="evidence rows have computation errors"):
        module.main(args)
    assert json.loads((out / "chunk_00000.json").read_text())[0]["status"] == "error"
    assert module.main(args + ["--resume", "--retry-errors"]) == 0
    assert json.loads((out / "chunk_00000.json").read_text())[0]["status"] == "error"
    assert (
        json.loads((out / "chunk_00000.retry_00001.json").read_text())[0]["status"]
        == "ok"
    )
    assert len(attempts) == 2
    assert json.loads((out / "receipt.json").read_text())["status"] == "provisional"


def test_new_json_never_overwrites(module, tmp_path):
    path = tmp_path / "record.json"
    module.write_new_json(path, {"status": "unresolved"})
    with pytest.raises(FileExistsError):
        module.write_new_json(path, {"status": "success"})
    assert json.loads(path.read_text())["status"] == "unresolved"


def test_bulk_output_guard_before_kernel_access(module, tmp_path):
    with pytest.raises(ValueError, match="outside the source checkout"):
        module.main(
            [
                "--detail",
                str(tmp_path / "detail"),
                "--detail-receipt",
                str(tmp_path / "receipt"),
                "--directory",
                str(module.REPO_ROOT / "scratch" / "should-not-exist"),
                "--kernel-sha256",
                "unused",
            ]
        )
