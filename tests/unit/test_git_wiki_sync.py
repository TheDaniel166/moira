from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "sync_git_wiki.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "_moira_sync_git_wiki_test_module",
    _SCRIPT_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
_SYNC = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SYNC)


def test_canonical_files_only_admit_git_tracked_markdown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    wiki_root = tmp_path / "wiki"
    tracked = wiki_root / "tracked.md"
    ignored = wiki_root / "ignored-local-research.md"
    wiki_root.mkdir()
    tracked.write_text("# Tracked\n", encoding="utf-8")
    ignored.write_text("# Local only\n", encoding="utf-8")

    monkeypatch.setattr(_SYNC, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(_SYNC, "WIKI_ROOT", wiki_root)

    def fake_run(
        arguments: list[str],
        *,
        check: bool,
        capture_output: bool,
    ) -> SimpleNamespace:
        assert arguments == [
            "git",
            "-C",
            str(tmp_path),
            "ls-files",
            "-z",
            "--",
            "wiki",
        ]
        assert check is True
        assert capture_output is True
        return SimpleNamespace(stdout=b"wiki/tracked.md\0")

    monkeypatch.setattr(_SYNC.subprocess, "run", fake_run)

    assert _SYNC._canonical_files() == [tracked]
