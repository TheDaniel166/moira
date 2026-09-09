"""Deliberate additive export and kernel-free facade contracts."""

import moira
import moira.facade as facade
import moira.stelliums as owner


def test_all_stellium_exports_have_one_owner():
    for name in owner.__all__:
        assert getattr(moira, name) is getattr(owner, name)
        assert getattr(facade, name) is getattr(owner, name)
        assert name in moira.__all__
        assert name in facade.__all__


def test_facade_delegates_without_initializing_a_kernel():
    engine = object.__new__(moira.Moira)
    engine._reader_obj = None
    positions = {"Sun": 0, "Moon": 2, "Mercury": 4, "Venus": 6}
    assert engine.analyze_stelliums(positions) == owner.analyze_stelliums(positions)
