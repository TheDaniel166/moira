import importlib
import sys
from pathlib import Path


pytest_plugins = ("pytester",)


ROOT_DIR = Path(__file__).resolve().parent
TESTS_DIR = ROOT_DIR / "tests"
_REPO_OWNED_IMPORT_PREFIXES = ("tests", "moira", "tools", "support")


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
    # Keep this repo's root and tests package ahead of any sibling checkout on
    # sys.path. This prevents pytest from reusing same-named engine or
    # test-support modules from another checkout during collection.
    _ensure_local_path(ROOT_DIR, 0)
    _ensure_local_path(TESTS_DIR, 1)

    for name, module in list(sys.modules.items()):
        if not any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in _REPO_OWNED_IMPORT_PREFIXES
        ):
            continue
        if _repo_owns_module(module):
            continue
        sys.modules.pop(name, None)

    importlib.invalidate_caches()


_sanitize_import_state()

_network_policy = importlib.import_module("support.network_policy")
_network_policy.install_network_audit_hook()
_network_policy.reset_network_mode(nodeid="<root-conftest>")
