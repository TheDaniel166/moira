from __future__ import annotations

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from moira._eclipse_solar_geometry import _circle_overlap_fraction
from moira.julian import julian_day
from moira.eclipse_global import EclipseEpoch
from moira.solar_eclipse_global import SolarEclipseUmbralContact, SolarEclipseUmbralContacts
import moira.eclipse as eclipse


def test_circle_overlap_fraction_covers_all_geometric_branches() -> None:
    assert _circle_overlap_fraction(1.0, 1.0, 2.0) == 0.0
    assert _circle_overlap_fraction(1.0, 1.0, 0.0) == 1.0
    assert _circle_overlap_fraction(1.0, 0.5, 0.0) == pytest.approx(0.25)
    assert _circle_overlap_fraction(1.0, 2.0, 0.5) == 1.0
    partial = _circle_overlap_fraction(1.0, 1.0, 1.0)
    assert 0.0 < partial < 1.0
    assert partial == pytest.approx(
        2.0 / 3.0 - math.sqrt(3.0) / (2.0 * math.pi)
    )


def _ucontact(kind, jd):
    return SolarEclipseUmbralContact(kind, EclipseEpoch(jd, jd, 0.0, "unit-test clock"), 0.0, 0.0)


def test_umbral_contact_vessel_accepts_optional_internal_pair():
    outer = SolarEclipseUmbralContacts(_ucontact("u1", 1.0), None, None, _ucontact("u4", 4.0))
    full = replace(outer, u2=_ucontact("u2", 2.0), u3=_ucontact("u3", 3.0))
    assert full.u2.epoch.jd_ut1 < full.u3.epoch.jd_ut1
    with pytest.raises(ValueError, match="paired"):
        replace(outer, u2=full.u2)
    with pytest.raises(ValueError, match="ordered"):
        replace(full, u3=_ucontact("u3", 1.5))
    with pytest.raises(ValueError, match="named U kind"):
        replace(outer, u1=_ucontact("u4", 1.0))
    with pytest.raises(ValueError, match="required"):
        replace(outer, u4=None)


def test_internal_contact_interval_is_discovered_away_from_greatest_epoch(monkeypatch):
    """Synthetic discriminants: U2/U3 exist entirely after the GE seed."""
    anchor = 2451545.0
    monkeypatch.setattr(eclipse, "_earth_fixed_solar_shadow",
                        lambda calc, epoch: SimpleNamespace(offset=epoch-anchor))
    monkeypatch.setattr(eclipse, "_central_generator_extrema", lambda state: (
        (0.0, 1.0-(state.offset/0.04)**2),
        (1.0, 0.5-((state.offset-0.015)/0.004)**2),
    ))
    monkeypatch.setattr(eclipse, "_central_generator_tangent_point", lambda *args: (0.0, 0.0))
    monkeypatch.setattr(eclipse, "_ut1_to_ephemeris_tt", lambda epoch, reader: epoch+0.001)
    contacts = eclipse._solve_solar_umbral_contacts(SimpleNamespace(_reader=None), anchor)
    assert contacts.u1.epoch.jd_ut1 < anchor < contacts.u2.epoch.jd_ut1
    assert contacts.u2.epoch.jd_ut1 < contacts.u3.epoch.jd_ut1 < contacts.u4.epoch.jd_ut1
    assert contacts.u2.epoch.jd_ut1 == pytest.approx(anchor+0.015-0.004*math.sqrt(0.5), abs=1e-9, rel=0.0)
    assert contacts.u3.epoch.jd_ut1 == pytest.approx(anchor+0.015+0.004*math.sqrt(0.5), abs=1e-9, rel=0.0)


@pytest.mark.parametrize(
    "values",
    [
        (0.0, 1.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, -0.1),
        (float("nan"), 1.0, 0.0),
    ],
)
def test_circle_overlap_fraction_rejects_invalid_geometry(
    values: tuple[float, float, float],
) -> None:
    with pytest.raises(ValueError):
        _circle_overlap_fraction(*values)


@pytest.mark.slow
def test_total_solar_global_circumstances_promote_existing_products(
    eclipse_calculator,
) -> None:
    result = eclipse_calculator.solar_global_circumstances(
        julian_day(2027, 7, 20),
        kind="total",
    )
    assert result.ephemeris == "DE-0441LE-0441"
    assert result.event == result.footprint.event
    assert result.greatest.epoch.jd_ut1 == pytest.approx(result.event.jd_ut)
    assert result.greatest.local_class == "total"
    assert result.greatest.magnitude > 1.0
    assert result.greatest.obscuration == 1.0
    assert result.greatest.path_width_km > 0.0
    assert result.greatest.central_duration_seconds > 0.0
    assert result.equatorial_conjunction.kind.value == "equatorial"
    assert result.ecliptic_conjunction.kind.value == "ecliptic"
    assert (
        result.equatorial_conjunction.epoch.jd_ut1
        < result.ecliptic_conjunction.epoch.jd_ut1
        < result.greatest.epoch.jd_ut1
    )
    assert result.first_central_line_limit is not None
    assert result.last_central_line_limit is not None
    assert (
        result.first_central_line_limit.epoch.jd_ut1
        < result.event.jd_ut
        < result.last_central_line_limit.epoch.jd_ut1
    )
    assert result.gamma_earth_radii == pytest.approx(
        math.copysign(
            math.hypot(result.besselian.x, result.besselian.y),
            result.besselian.y,
        )
    )
    assert result.umbral_contacts_admitted is True
    contacts = result.umbral_contacts
    assert contacts is not None
    assert (
        contacts.u1.epoch.jd_ut1
        < contacts.u2.epoch.jd_ut1
        < result.event.jd_ut
        < contacts.u3.epoch.jd_ut1
        < contacts.u4.epoch.jd_ut1
    )
    assert result.greatest_duration_admitted is True
    assert result.greatest_duration is not None
    assert (
        result.first_central_line_limit.epoch.jd_ut1
        < result.greatest_duration.epoch.jd_ut1
        < result.last_central_line_limit.epoch.jd_ut1
    )
    assert (
        result.greatest_duration.central_duration_seconds
        >= result.greatest.central_duration_seconds
    )


@pytest.mark.slow
def test_partial_solar_global_circumstances_do_not_invent_central_products(
    eclipse_calculator,
) -> None:
    result = eclipse_calculator.solar_global_circumstances(
        julian_day(2029, 6, 1),
        kind="partial",
    )
    assert result.greatest.local_class == "partial"
    assert 0.0 < result.greatest.magnitude < 1.0
    assert 0.0 < result.greatest.obscuration < 1.0
    assert result.greatest.path_width_km == 0.0
    assert result.greatest.central_duration_seconds == 0.0
    assert result.first_central_line_limit is None
    assert result.last_central_line_limit is None
    assert result.umbral_contacts_admitted is True
    assert result.umbral_contacts is None
    assert result.greatest_duration_admitted is True
    assert result.greatest_duration is None


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_solar_global_circumstances_reject_invalid_seed(
    eclipse_calculator,
    value: object,
) -> None:
    error = TypeError if value is True else ValueError
    with pytest.raises(error):
        eclipse_calculator.solar_global_circumstances(value)
