"""Replay a short DE441 native lunar contact-solver convergence control."""

import pytest

from moira.eclipse_contacts import find_lunar_contacts


@pytest.mark.requires_ephemeris
def test_native_lunation_minus_40729_short_penumbral_contacts(eclipse_calculator):
    """Replay the preserved Stage 7 same-model control, not an eclipse proof.

    Lunation -40729, astronomical year -1293, uses the native retarded-Sun,
    simultaneous-Moon lunar geometry and the DE441 kernel. Its approximately
    13.9-second native penumbral contact pair was recorded in
    ``work/lunar_stage7/contact_convergence.json`` and
    ``work/lunar_stage7/INVESTIGATION.md``. The separately selected Danjon and
    finite-cone candidate models have different threshold behavior.
    Repeated step-size agreement does not certify that every phase was found.
    """
    seed_ut1 = 1248813.0916963164
    steps = (120.0, 60.0, 30.0, 10.0)
    results = [find_lunar_contacts(eclipse_calculator, seed_ut1, coarse_step_seconds=step)
               for step in steps]
    reference = results[-1]
    for contacts in results:
        assert contacts.p1 is not None and contacts.p4 is not None
        assert contacts.p1 < contacts.greatest < contacts.p4
        assert 13.8 < (contacts.p4 - contacts.p1) * 86400 < 14.0
        for name in ("p1", "u1", "u2", "u3", "u4", "p4"):
            actual, expected = getattr(contacts, name), getattr(reference, name)
            assert (actual is None) == (expected is None)
            if expected is not None:
                assert abs(actual - expected) * 86400 < 0.02
