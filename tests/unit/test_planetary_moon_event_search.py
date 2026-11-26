"""Analytic finite-contact search witnesses independent of SPK samples."""

import pytest

from moira.planetary_moon_events import _UnresolvedContact, _scan_contacts, _windows


def test_same_sign_scan_cell_still_resolves_both_short_event_contacts():
    centre = 0.035
    width = 0.001

    def signal(day):
        return (day - centre) ** 2 - width**2

    roots = _scan_contacts(signal, (0.0, 0.02, 0.04, 0.06, 0.08))
    assert [direction for _, direction in roots] == ["enter", "exit"]
    assert [epoch for epoch, _ in roots] == pytest.approx([0.034, 0.036], abs=2e-9)


def test_graze_without_a_sign_change_and_window_endpoint_ownership():
    def signal(day):
        return (day - 0.035) ** 2

    contacts = _scan_contacts(signal, (0.0, 0.02, 0.04, 0.06, 0.08))
    assert len(contacts) == 1
    assert contacts[0][0] == pytest.approx(0.035, abs=2e-9)
    assert contacts[0][1] == "touch"
    epoch = contacts[0][0]
    assert _windows(0.0, 0.08, False, contacts) == [(epoch, epoch, False, False)]
    assert _windows(0.0, 0.08, False, [(0.08, "touch")]) == []
    assert _windows(0.0, 0.08, True, [(0.04, "exit")]) == [(0, 0.04, True, False)]


def test_exterior_probe_distinguishes_boundary_grazes_from_crossings():
    epochs = (0.0, 0.02, 0.04)
    start_egress = _scan_contacts(lambda day: day, epochs)
    start_ingress = _scan_contacts(lambda day: -day, epochs)
    start_graze = _scan_contacts(lambda day: day**2, epochs)
    end_egress = _scan_contacts(lambda day: day - 0.04, epochs)

    assert start_egress == [(0.0, "exit")]
    assert start_ingress == [(0.0, "enter")]
    assert start_graze == [(0.0, "touch")]
    assert end_egress == [(0.04, "exit")]
    assert _windows(0.0, 0.04, True, start_egress) == []
    assert _windows(0.0, 0.04, False, start_ingress) == [(0.0, 0.04, False, True)]
    assert _windows(0.0, 0.04, False, start_graze) == [(0.0, 0.0, False, False)]
    assert _windows(0.0, 0.04, True, end_egress) == [(0.0, 0.04, True, False)]


def test_discontinuous_sign_jump_is_not_returned_as_a_contact():
    def jump(day):
        return 1.0 if day < 0.035 else -1.0

    with pytest.raises(_UnresolvedContact, match="discontinuity"):
        _scan_contacts(jump, (0.0, 0.02, 0.04, 0.06))
