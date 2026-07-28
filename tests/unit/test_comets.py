"""Regression tests for comet catalog exception containment."""

from __future__ import annotations

import pytest

from moira import comets
from moira.spk_reader import MissingKernelError


def test_all_comets_skips_a_missing_kernel_without_name_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing shard is an unavailable result, not an undefined-name crash."""

    def missing_kernel(*args, **kwargs):
        raise MissingKernelError("missing test comet shard")

    monkeypatch.setattr(comets, "comet_at", missing_kernel)

    assert comets.all_comets_at(2451545.0, names={"Halley"}) == {}
