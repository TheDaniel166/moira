"""Independent altitude and forward-branch covenants for inverse loci."""

import math

import pytest

from moira.geodetic import _armc_from_mc, _circular_delta, geodetic_asc, geodetic_mc
from moira.geodetic_curves import GeodeticCurvePolicy, geodetic_angular_loci
from moira.geodetic_inputs import geodetic_snapshot_from_positions


@pytest.mark.parametrize("longitude", [0, 1, 45, 90, 137, 180, 270, 359])
@pytest.mark.parametrize("offset", [0, 24])
def test_inverse_loci_forward_and_independent_altitude(longitude, offset):
    snapshot = geodetic_snapshot_from_positions({"comet:Halley": longitude}, source_frame="ecliptic",
                                               zodiac="sidereal" if offset else "tropical", ayanamsa_deg=offset)
    result = geodetic_angular_loci(snapshot, obliquity=23.44, policy=GeodeticCurvePolicy(latitude_step_deg=5))
    assert result.complete
    for locus in result.loci:
        assert locus.segments
        ra, dec = map(math.radians, (locus.right_ascension_deg, locus.declination_deg))
        for segment in locus.segments:
            assert all((a.latitude_deg, a.longitude_deg) != (b.latitude_deg, b.longitude_deg) for a, b in zip(segment, segment[1:]))
            assert all(abs(b.longitude_deg - a.longitude_deg) <= 180 for a, b in zip(segment, segment[1:]))
            for vertex in segment:
                if locus.angle in ("MC", "IC"):
                    value = geodetic_mc(vertex.longitude_deg + (180 if locus.angle == "IC" else 0), offset)
                else:
                    value = geodetic_mc(geodetic_asc(vertex.longitude_deg, vertex.latitude_deg, 23.44, offset), -180 if locus.angle == "DSC" else 0)
                    phi = math.radians(vertex.latitude_deg)
                    h = math.radians(_armc_from_mc(geodetic_mc(vertex.longitude_deg), 23.44)) - ra
                    altitude_sine = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h)
                    assert abs(altitude_sine) < 1e-9
                    assert vertex.rising_rate > 0 if locus.angle == "ASC" else vertex.rising_rate < 0
                assert abs(_circular_delta(value, snapshot.positions[0].selected_longitude_deg)) < 1e-7


def test_degenerate_latitudes_segments_and_work_limit():
    snapshot = geodetic_snapshot_from_positions({"External": 0}, source_frame="ecliptic")
    result = geodetic_angular_loci(snapshot, obliquity=23.44)
    asc = next(locus for locus in result.loci if locus.angle == "ASC")
    assert any(e.reason == "coincident_planes" for e in asc.exclusions)
    tiny = geodetic_angular_loci(snapshot, obliquity=23.44, policy=GeodeticCurvePolicy(max_evaluations=3))
    assert not tiny.complete
    assert tiny.evaluations <= 3
    extreme = geodetic_angular_loci(snapshot, obliquity=23.44, angles=("ASC",),
                                    policy=GeodeticCurvePolicy(latitude_step_deg=1e-310, max_evaluations=3))
    assert not extreme.complete
    assert extreme.evaluations <= 3
    finite_dense = geodetic_angular_loci(snapshot, obliquity=23.44, angles=("ASC",),
                                        policy=GeodeticCurvePolicy(latitude_step_deg=1e-300, max_evaluations=3))
    assert not finite_dense.complete and finite_dense.evaluations <= 3
