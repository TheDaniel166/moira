"""Canary proving that the serial harness lane is an ordinary local process."""

from __future__ import annotations

import os

import pytest


@pytest.mark.serial(reason="lane_canary")
def test_serial_lane_runs_without_an_xdist_worker() -> None:
    assert "PYTEST_XDIST_WORKER" not in os.environ
