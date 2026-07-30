from __future__ import annotations

import os
from pathlib import Path
import sys


if os.getenv("MOIRA_PYTEST_PLUGIN_AUTOLOAD", "0") != "1":
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")


def _install_inherited_test_network_policy() -> None:
    if "MOIRA_TEST_NETWORK_POLICY" not in os.environ:
        return

    try:
        tests_dir = Path(__file__).resolve().parent / "tests"
        tests_entry = str(tests_dir)
        if tests_entry not in sys.path:
            sys.path.insert(0, tests_entry)

        from support.network_policy import install_network_policy_from_environment

        install_network_policy_from_environment()
    except Exception as exc:
        raise SystemExit(
            "Moira cooperative-child network policy failed to install; "
            "aborting Python startup."
        ) from exc


_install_inherited_test_network_policy()
