"""DE441 edge cases retain honest next/previous coverage failures."""

import math

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1
from moira.julian import tdb_to_tt
from moira.phenomena import _sun_moon_phase_angle
from moira.spk_reader import OutOfRangeError


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("backward", [False, True])
def test_de441_opposite_probe_outside_coverage_is_explicit(
    planetary_reader, eclipse_calculator, backward,
):
    """An available start is not evidence for an unavailable phase window.

    The query is 0.10 TDB day inside the real source coverage. At this epoch
    even the request-point phase is evaluable, while the 0.125-day opposite
    probe exceeds coverage. The method must not silently call this unknown
    neighborhood eclipse-free. A second query, 0.20 day inside, demonstrates
    that a same-direction result can be computed after the window is covered.
    The latter alone does not prove that it is nearest to the first query.
    """
    limits = planetary_reader.coverage()[(0, 3)]
    edge = limits[1 if backward else 0]
    sign = -1.0 if backward else 1.0

    def ut1_for_tdb_offset(offset):
        return _ephemeris_tt_to_ut1(tdb_to_tt(edge + sign * offset), planetary_reader)

    query = ut1_for_tdb_offset(0.10)
    assert math.isfinite(_sun_moon_phase_angle(query, planetary_reader))
    search = (eclipse_calculator.previous_solar_eclipse if backward
              else eclipse_calculator.next_solar_eclipse)
    with pytest.raises(OutOfRangeError):
        search(query)

    interior = ut1_for_tdb_offset(0.20)
    result = search(interior)
    assert result.jd_ut < interior if backward else result.jd_ut > interior


@pytest.mark.requires_ephemeris
def test_de441_upper_edge_uses_available_one_sided_longitude_rate(
    planetary_reader, eclipse_calculator,
):
    """A covered phase and inward rate stencil must not fail with TypeError."""
    upper = planetary_reader.coverage()[(0, 3)][1]
    near = _ephemeris_tt_to_ut1(tdb_to_tt(upper - 0.127), planetary_reader)
    reference = _ephemeris_tt_to_ut1(tdb_to_tt(upper - 0.130), planetary_reader)
    result = eclipse_calculator.previous_solar_eclipse(near)
    assert result.jd_ut < near
    assert result.jd_ut == eclipse_calculator.previous_solar_eclipse(reference).jd_ut
