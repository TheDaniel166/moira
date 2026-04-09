from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import moira.facade as facade


def test_moira_initializes_without_kernel_and_reports_status(monkeypatch) -> None:
    monkeypatch.setattr(
        facade,
        "SpkReader",
        lambda path: (_ for _ in ()).throw(FileNotFoundError("missing de441")),
    )

    engine = facade.Moira()

    assert engine.is_kernel_available() is False
    assert "No planetary kernel is configured" in engine.get_kernel_status()


def test_kernel_dependent_calls_raise_moira_specific_error_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        facade,
        "SpkReader",
        lambda path: (_ for _ in ()).throw(FileNotFoundError("missing de441")),
    )

    engine = facade.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(facade.MissingEphemerisKernelError) as exc:
        engine.chart(dt)

    assert "moira-download-kernels" in str(exc.value)


def test_configure_kernel_path_recovers_when_kernel_becomes_available(monkeypatch) -> None:
    configured_paths: list[Path] = []

    def fake_reader(path):
        configured_paths.append(Path(path))
        if Path(path) == Path("good.bsp"):
            return SimpleNamespace(path=Path("good.bsp"))
        raise FileNotFoundError("missing de441")

    monkeypatch.setattr(facade, "SpkReader", fake_reader)

    engine = facade.Moira()
    assert engine.is_kernel_available() is False

    engine.configure_kernel_path("good.bsp")

    assert configured_paths[-1] == Path("good.bsp")
    assert engine.is_kernel_available() is True
    assert "Kernel ready" in engine.kernel_status
