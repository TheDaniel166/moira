"""Contract tests for the provisional, resumable solar catalog runner."""

from __future__ import annotations

import csv
import importlib
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def runner(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "scripts" / "eclipse_catalog"))
    return importlib.import_module("solar_generate")


class _Reader:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _setup(monkeypatch, tmp_path, runner, row_status="ok", contact_status="available"):
    kernel = tmp_path / "kernel.bsp"
    kernel.write_bytes(b"test kernel")
    index = tmp_path / "index.csv"
    with index.open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(
            stream,
            [
                "family",
                "year_astronomical",
                "jd_tt",
                "jd_ut1",
                "eclipse_type",
                "saros_series",
                "lunation_number",
            ],
        )
        writer.writeheader()
        writer.writerow(
            dict(
                family="solar",
                year_astronomical=2024,
                jd_tt=2460409.0,
                jd_ut1=2460409.0,
                eclipse_type="Total",
                saros_series=139,
                lunation_number=300,
            )
        )
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            dict(
                status="provisional",
                family="solar",
                row_count=1,
                merged_sha256=runner.sha256(index),
                kernel_sha256=runner.sha256(kernel),
                source_fingerprint_sha256="discovery-fingerprint",
            )
        ),
        encoding="utf8",
    )
    output = tmp_path / "result.csv"
    monkeypatch.setattr(runner, "find_planetary_kernel", lambda: kernel)
    monkeypatch.setattr(runner, "SpkReader", _Reader)
    monkeypatch.setattr(runner.eclipse, "EclipseCalculator", lambda **kwargs: object())
    monkeypatch.setattr(
        runner,
        "source_fingerprint",
        lambda: {
            "engine_package_sha256": "engine",
            "native_source_sha256": "native",
            "runner_sha256": "runner",
        },
    )
    monkeypatch.setattr(
        runner, "discovery_fingerprint", lambda: "discovery-fingerprint"
    )
    monkeypatch.setattr(
        runner,
        "compute",
        lambda *args, **kwargs: dict(
            lunation_number=300,
            status=row_status,
            penumbral_contacts_status=contact_status,
            umbral_contacts_status="available",
            width_status="available",
            elapsed_seconds=0,
        ),
    )
    argv = [
        "solar_generate.py",
        "--index",
        str(index),
        "--index-receipt",
        str(receipt),
        "--output",
        str(output),
        "--kernel-sha256",
        runner.sha256(kernel),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    return output, receipt, index


def test_fresh_run_and_explicit_resume(monkeypatch, tmp_path, runner):
    output, _, _ = _setup(monkeypatch, tmp_path, runner)
    runner.main()
    with output.open(newline="", encoding="utf8") as stream:
        assert len(list(csv.DictReader(stream))) == 1
    with pytest.raises(RuntimeError, match="explicitly request resume"):
        runner.main()
    monkeypatch.setattr(sys, "argv", sys.argv + ["--resume"])
    runner.main()
    with output.open(newline="", encoding="utf8") as stream:
        assert len(list(csv.DictReader(stream))) == 1


@pytest.mark.parametrize("status,contact", [("error", "available"), ("ok", "error")])
def test_errors_remain_visible_and_fail_resume(
    monkeypatch, tmp_path, runner, status, contact
):
    output, _, _ = _setup(monkeypatch, tmp_path, runner, status, contact)
    with pytest.raises(RuntimeError, match="computation errors"):
        runner.main()
    with output.open(newline="", encoding="utf8") as stream:
        assert runner.has_error(next(csv.DictReader(stream)))
    monkeypatch.setattr(sys, "argv", sys.argv + ["--resume"])
    with pytest.raises(RuntimeError, match="computation errors"):
        runner.main()


def test_receipt_mismatch_never_creates_output(monkeypatch, tmp_path, runner):
    output, receipt, _ = _setup(monkeypatch, tmp_path, runner)
    data = json.loads(receipt.read_text(encoding="utf8"))
    data["merged_sha256"] = "wrong"
    receipt.write_text(json.dumps(data), encoding="utf8")
    with pytest.raises(RuntimeError, match="discovery receipt"):
        runner.main()
    assert not output.exists()


def test_package_fingerprint_includes_data_and_excludes_bytecode(tmp_path, runner):
    (tmp_path / "module.py").write_text("x = 1", encoding="utf8")
    (tmp_path / "data.json").write_text("{}", encoding="utf8")
    before = runner.package_digest(tmp_path)
    (tmp_path / "data.json").write_text('{"x": 1}', encoding="utf8")
    assert runner.package_digest(tmp_path) != before
    changed = runner.package_digest(tmp_path)
    (tmp_path / "cache.pyc").write_bytes(b"not relevant")
    assert runner.package_digest(tmp_path) == changed
