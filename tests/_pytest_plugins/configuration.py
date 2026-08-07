"""Fail-closed typed configuration for the Moira pytest harness."""

from __future__ import annotations

import math
import os
import re
import uuid

import pytest

from .determinism import activate_hypothesis_policy
from ._state import (
    _ARTIFACT_RUN_ID_RE,
    _HARNESS_CONFIG_KEY,
    _LEGACY_BASELINE_UPDATE_ENVIRONMENTS,
    _MAX_TEST_SEED,
    _WINDOWS_RESERVED_COMPONENTS,
    _HarnessConfig,
)


def _display_env_value(raw: str, *, limit: int = 80) -> str:
    if len(raw) <= limit:
        return ascii(raw)
    return f"{ascii(raw[:limit])}... ({len(raw)} characters)"


def _parse_bool_env(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if raw not in {"0", "1"}:
        raise pytest.UsageError(
            f"{name} must be exactly '0' or '1'; got {_display_env_value(raw)}."
        )
    return raw == "1"


def _parse_seed_env(name: str, *, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if len(raw) > 20 or re.fullmatch(r"[0-9]+", raw) is None:
        raise pytest.UsageError(
            f"{name} must be an integer from 0 through {_MAX_TEST_SEED}; "
            f"got {_display_env_value(raw)}."
        )
    try:
        value = int(raw)
    except ValueError as exc:
        raise pytest.UsageError(
            f"{name} must be an integer from 0 through {_MAX_TEST_SEED}; "
            f"got {_display_env_value(raw)}."
        ) from exc
    if value > _MAX_TEST_SEED:
        raise pytest.UsageError(
            f"{name} must be an integer from 0 through {_MAX_TEST_SEED}; "
            f"got {_display_env_value(raw)}."
        )
    return value


def _parse_nonnegative_finite_float_env(name: str, *, default: float = 0.0) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise pytest.UsageError(
            f"{name} must be a finite nonnegative number; "
            f"got {_display_env_value(raw)}."
        ) from exc
    if not math.isfinite(value) or value < 0:
        raise pytest.UsageError(
            f"{name} must be a finite nonnegative number; "
            f"got {_display_env_value(raw)}."
        )
    return value


def _parse_artifact_run_id(config) -> str:
    raw = os.environ.get("MOIRA_TEST_RUN_ID")
    if raw is None:
        workerinput = getattr(config, "workerinput", None)
        if isinstance(workerinput, dict):
            raw = workerinput.get("moira_test_run_id")
    if raw is None:
        return uuid.uuid4().hex
    if (
        type(raw) is not str
        or _ARTIFACT_RUN_ID_RE.fullmatch(raw) is None
        or raw.upper() in _WINDOWS_RESERVED_COMPONENTS
    ):
        raise pytest.UsageError(
            "MOIRA_TEST_RUN_ID must be one portable ASCII path component "
            "matching [A-Za-z0-9][A-Za-z0-9_-]{0,63}, and must not be a "
            f"reserved Windows device name; got {_display_env_value(str(raw))}."
        )
    return raw


def _parse_harness_config(config) -> _HarnessConfig:
    for environment_name in _LEGACY_BASELINE_UPDATE_ENVIRONMENTS:
        if _parse_bool_env(environment_name):
            raise pytest.UsageError(
                f"{environment_name}=1 is forbidden: ordinary pytest baseline "
                "access is read-only. Generate candidates separately and promote "
                "protected evidence only after review."
            )

    test_mode = _parse_bool_env("MOIRA_TEST_MODE")
    no_download_is_explicit = "MOIRA_NO_DOWNLOAD" in os.environ
    no_download = _parse_bool_env(
        "MOIRA_NO_DOWNLOAD",
        default=test_mode,
    )
    if test_mode and no_download_is_explicit and not no_download:
        raise pytest.UsageError(
            "MOIRA_TEST_MODE=1 requires MOIRA_NO_DOWNLOAD=1; the explicit "
            "MOIRA_NO_DOWNLOAD=0 override would weaken deterministic test mode."
        )

    artifacts_enabled = _parse_bool_env("MOIRA_TEST_ARTIFACTS")
    policy = _HarnessConfig(
        test_mode=test_mode,
        no_download=no_download,
        strict_known_issues=_parse_bool_env("MOIRA_STRICT_KNOWN_ISSUES"),
        external_network_enabled=bool(
            config.getoption("--run-external-network")
        ),
        seed=_parse_seed_env("MOIRA_TEST_SEED", default=1337),
        budget_total_s=_parse_nonnegative_finite_float_env(
            "MOIRA_TEST_BUDGET_TOTAL_S"
        ),
        budget_case_s=_parse_nonnegative_finite_float_env(
            "MOIRA_TEST_BUDGET_CASE_S"
        ),
        artifacts_enabled=artifacts_enabled,
        run_id=(
            _parse_artifact_run_id(config)
            if artifacts_enabled
            else ""
        ),
        hypothesis=activate_hypothesis_policy(config, test_mode=test_mode),
    )

    if test_mode and not no_download_is_explicit:
        # Engine acquisition code consumes this environment boundary directly.
        os.environ["MOIRA_NO_DOWNLOAD"] = "1"
    return policy


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config) -> None:
    config.stash[_HARNESS_CONFIG_KEY] = _parse_harness_config(config)
