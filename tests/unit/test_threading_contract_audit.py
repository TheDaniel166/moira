from __future__ import annotations

from pathlib import Path


def test_public_threading_contract_document_exists_and_names_admitted_and_forbidden_patterns() -> None:
    source = Path("docs/threading.md").read_text(encoding="utf-8")

    assert "# Moira Threading And GIL Contract" in source
    assert "Concurrent read calls on an already-open `SpkReader`" in source
    assert "Calling `close()` while other threads are actively reading" in source
    assert "`set_kernel_path()`" in source
    assert "`swap_reader()`" in source
    assert "`reset_singleton()`" in source
    assert "worker processes" in source


def test_threading_contract_links_gil_release_to_pure_native_work() -> None:
    source = Path("docs/threading.md").read_text(encoding="utf-8")

    assert "py::gil_scoped_release" in source
    assert "release it on" in source
    assert "pure-native work" in source
