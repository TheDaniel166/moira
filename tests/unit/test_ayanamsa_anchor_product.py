"""Star-anchored ayanamsas: the explicit anchor product.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 5.
The base systems (True Chitrapaksha, True Revati, Aldebaran 15 Tau, True
Pushya, True Mula) anchor on the astrometric star; their ``(apparent)``
variants anchor on the apparent star, as the planets are computed.
"""

from __future__ import annotations

import pytest

from moira.sidereal import (
    Ayanamsa,
    _STAR_ANCHORED,
    _anchor_product,
    _ayanamsa_truth_at_tt,
    ayanamsa_with_truth,
)
from moira.spk_reader import MissingKernelError, use_reader_override
from moira.stars import star_at

PAIRS = [
    (Ayanamsa.TRUE_CHITRAPAKSHA, Ayanamsa.TRUE_CHITRAPAKSHA_APPARENT),
    (Ayanamsa.ALDEBARAN_15_TAU, Ayanamsa.ALDEBARAN_15_TAU_APPARENT),
    (Ayanamsa.TRUE_REVATI, Ayanamsa.TRUE_REVATI_APPARENT),
    (Ayanamsa.TRUE_PUSHYA, Ayanamsa.TRUE_PUSHYA_APPARENT),
    (Ayanamsa.TRUE_MULA, Ayanamsa.TRUE_MULA_APPARENT),
]
JD_TT = 2460600.5


@pytest.mark.parametrize("base,apparent", PAIRS)
def test_variants_share_star_and_target_and_name_their_product(base, apparent) -> None:
    assert _STAR_ANCHORED[apparent] == _STAR_ANCHORED[base]
    assert _anchor_product(base) == "astrometric"
    assert _anchor_product(apparent) == "apparent"
    assert base in Ayanamsa.ALL and apparent in Ayanamsa.ALL


@pytest.mark.parametrize("base,_apparent", PAIRS)
def test_base_systems_are_kernel_free_and_report_astrometric(base, _apparent) -> None:
    truth = ayanamsa_with_truth(2451545.0, base)
    assert truth.effective_path == "live_star_anchor"
    assert truth.anchor_product == "astrometric"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("base,apparent", PAIRS)
def test_apparent_anchor_places_the_apparent_star_on_its_target(base, apparent, planetary_reader) -> None:
    star_name, target = _STAR_ANCHORED[apparent]
    with use_reader_override(planetary_reader):
        truth = _ayanamsa_truth_at_tt(JD_TT, apparent)
        apparent_star = star_at(star_name, JD_TT, product="apparent", reader=planetary_reader)
        base_value = _ayanamsa_truth_at_tt(JD_TT, base).ayanamsa_unwrapped_deg
    assert truth.anchor_product == "apparent"
    sidereal = (apparent_star.longitude - truth.ayanamsa_unwrapped_deg) % 360.0
    assert sidereal == pytest.approx(target, abs=1e-9)
    # The two products differ by the star's aberration and deflection only.
    difference_arcsec = abs(truth.ayanamsa_unwrapped_deg - base_value) * 3600.0
    assert 0.0 < difference_arcsec < 30.0


def test_apparent_anchor_without_a_kernel_fails_closed(monkeypatch) -> None:
    import moira.spk_reader as spk_reader

    monkeypatch.setattr(spk_reader, "get_active_reader", lambda: None)
    with pytest.raises(MissingKernelError):
        _ayanamsa_truth_at_tt(JD_TT, Ayanamsa.TRUE_CHITRAPAKSHA_APPARENT)
