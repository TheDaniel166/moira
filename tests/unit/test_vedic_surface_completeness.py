"""Identity and curation gates for existing Vedic subsystem imports."""
import importlib
import pytest
import moira
import moira.facade as facade
import moira.vedic as vedic

_FAMILIES = (
    "varga", "ashtakavarga", "shadbala", "yogas", "avasthas",
    "jaimini_extended", "muhurta", "muhurta_search", "upagrahas", "sade_sati", "gochara", "gochara_dated",
)


@pytest.mark.parametrize("family", _FAMILIES)
def test_vedic_covers_every_already_curated_family_name(family):
    owner = importlib.import_module("moira." + family)
    admitted = set(owner.__all__) & (set(moira.__all__) | set(facade.__all__))
    assert admitted <= set(vedic.__all__)
    for name in admitted:
        assert getattr(vedic, name) is getattr(owner, name)


def test_varga_root_and_facade_share_all_existing_curated_names():
    owner = importlib.import_module("moira.varga")
    for name in set(owner.__all__) & set(facade.__all__):
        assert name in moira.__all__
        assert getattr(moira, name) is getattr(facade, name)


def test_vedic_star_import_is_unique_and_excludes_unadmitted_sayanadi():
    assert len(vedic.__all__) == len(set(vedic.__all__))
    namespace = {}
    exec("from moira.vedic import *", {}, namespace)
    assert set(namespace) == set(vedic.__all__)
    assert "sayanadi_avastha" not in namespace
    assert "FiniteNumber" not in namespace
