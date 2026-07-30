"""Install Moira's inherited test-network policy in cooperative Python children.

This bootstrap is not a sandbox. ``python -S``, a replaced ``PYTHONPATH``,
native networking, or a hostile child can bypass it. Runner-level egress
denial is the only complete process containment boundary and is separately
scoped from this bootstrap.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


def _install_inherited_policy() -> None:
    if "MOIRA_TEST_NETWORK_POLICY" not in os.environ:
        return

    try:
        tests_dir = Path(__file__).resolve().parents[2]
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


_install_inherited_policy()
