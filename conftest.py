from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
TESTS_DIR = ROOT_DIR / "tests"


def _repo_owns_module(module) -> bool:
    module_file = getattr(module, "__file__", None)
    if module_file:
        try:
            return Path(module_file).resolve().is_relative_to(ROOT_DIR)
        except Exception:
            return False

    module_path = getattr(module, "__path__", None)
    if not module_path:
        return False

    try:
        return all(Path(entry).resolve().is_relative_to(ROOT_DIR) for entry in module_path)
    except Exception:
        return False


def _ensure_local_path(entry: Path, index: int) -> None:
    entry_str = str(entry)
    try:
        sys.path.remove(entry_str)
    except ValueError:
        pass
    sys.path.insert(index, entry_str)


def _sanitize_import_state() -> None:
    _ensure_local_path(ROOT_DIR, 0)
    _ensure_local_path(TESTS_DIR, 1)

    for name, module in list(sys.modules.items()):
        if not (name == "tests" or name.startswith("tests.") or name == "moira" or name.startswith("moira.") or name == "tools" or name.startswith("tools.")):
            continue
        if _repo_owns_module(module):
            continue
        sys.modules.pop(name, None)

    importlib.invalidate_caches()


_sanitize_import_state()
