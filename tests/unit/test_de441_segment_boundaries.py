import math

import pytest

from moira.constants import Body
from moira.julian import tt_to_ut
from moira.planets import planet_at, sky_position_at
from moira.spk_reader import get_reader

_ONE_SECOND_JD = 1.0 / 86400.0
_RAW_JOIN_TOLERANCE_KM = 1e-5
_MAX_LONGITUDE_STEP_DEG = 1e-3
_MAX_LONGITUDE_STEP_MISMATCH_DEG = 1e-5
_MAX_RA_DEC_STEP_DEG = 1e-3
_MAX_RA_DEC_STEP_MISMATCH_DEG = 1e-5
_OBSERVER_LAT = 51.5
_OBSERVER_LON = -0.1
_PUBLIC_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)


def _adjacent_split_boundaries(reader):
    boundaries = []
    for pair, segments in sorted(reader._segments_by_pair.items()):
        ordered_segments = tuple(sorted(segments, key=lambda segment: segment.start_jd))
        for left, right in zip(ordered_segments, ordered_segments[1:]):
            if math.isclose(left.end_jd, right.start_jd, abs_tol=1e-12):
                boundaries.append((pair, left, right, float(left.end_jd)))
    if not boundaries:
        pytest.skip("The active planetary kernel does not expose adjacent shared segment boundaries")
    return tuple(boundaries)


def _shared_boundary_jds(reader):
    return tuple(dict.fromkeys(boundary_jd for _, _, _, boundary_jd in _adjacent_split_boundaries(reader)))


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


@pytest.mark.requires_ephemeris
def test_de441_raw_split_pairs_join_continuously() -> None:
    reader = get_reader()
    failures = []

    for pair, left, right, boundary_jd in _adjacent_split_boundaries(reader):
        left_xyz = left.compute(boundary_jd)
        right_xyz = right.compute(boundary_jd)
        delta_norm_km = math.sqrt(
            sum((float(right_value) - float(left_value)) ** 2 for left_value, right_value in zip(left_xyz, right_xyz))
        )
        if delta_norm_km >= _RAW_JOIN_TOLERANCE_KM:
            failures.append(
                f"pair={pair} boundary_tt={boundary_jd:.1f} delta_norm_km={delta_norm_km:.12g}"
            )

    assert not failures, "DE441 raw split-pair discontinuities detected:\n" + "\n".join(failures)


@pytest.mark.requires_ephemeris
def test_public_longitudes_are_smooth_across_de441_split_boundaries() -> None:
    reader = get_reader()
    failures = []

    for boundary_tt in _shared_boundary_jds(reader):
        boundary_ut = tt_to_ut(boundary_tt)
        for body in _PUBLIC_BODIES:
            before = planet_at(body, boundary_ut - _ONE_SECOND_JD, reader=reader)
            at_boundary = planet_at(body, boundary_ut, reader=reader)
            after = planet_at(body, boundary_ut + _ONE_SECOND_JD, reader=reader)

            before_step_deg = _signed_angle_delta(before.longitude, at_boundary.longitude)
            after_step_deg = _signed_angle_delta(at_boundary.longitude, after.longitude)
            step_mismatch_deg = after_step_deg - before_step_deg

            if (
                abs(before_step_deg) >= _MAX_LONGITUDE_STEP_DEG
                or abs(after_step_deg) >= _MAX_LONGITUDE_STEP_DEG
                or abs(step_mismatch_deg) >= _MAX_LONGITUDE_STEP_MISMATCH_DEG
            ):
                failures.append(
                    f"body={body} boundary_tt={boundary_tt:.1f} "
                    f"step_before_deg={before_step_deg:.12g} "
                    f"step_after_deg={after_step_deg:.12g} "
                    f"step_mismatch_deg={step_mismatch_deg:.12g}"
                )

    assert not failures, "Public longitude discontinuities detected across DE441 split boundaries:\n" + "\n".join(failures)


@pytest.mark.requires_ephemeris
def test_moon_ra_dec_are_smooth_across_de441_split_boundaries() -> None:
    reader = get_reader()
    failures = []

    for boundary_tt in _shared_boundary_jds(reader):
        boundary_ut = tt_to_ut(boundary_tt)
        before = sky_position_at(Body.MOON, boundary_ut - _ONE_SECOND_JD, _OBSERVER_LAT, _OBSERVER_LON, reader=reader)
        at_boundary = sky_position_at(Body.MOON, boundary_ut, _OBSERVER_LAT, _OBSERVER_LON, reader=reader)
        after = sky_position_at(Body.MOON, boundary_ut + _ONE_SECOND_JD, _OBSERVER_LAT, _OBSERVER_LON, reader=reader)

        ra_before_step_deg = _signed_angle_delta(before.right_ascension, at_boundary.right_ascension)
        ra_after_step_deg = _signed_angle_delta(at_boundary.right_ascension, after.right_ascension)
        dec_before_step_deg = at_boundary.declination - before.declination
        dec_after_step_deg = after.declination - at_boundary.declination

        if (
            abs(ra_before_step_deg) >= _MAX_RA_DEC_STEP_DEG
            or abs(ra_after_step_deg) >= _MAX_RA_DEC_STEP_DEG
            or abs(ra_after_step_deg - ra_before_step_deg) >= _MAX_RA_DEC_STEP_MISMATCH_DEG
            or abs(dec_before_step_deg) >= _MAX_RA_DEC_STEP_DEG
            or abs(dec_after_step_deg) >= _MAX_RA_DEC_STEP_DEG
            or abs(dec_after_step_deg - dec_before_step_deg) >= _MAX_RA_DEC_STEP_MISMATCH_DEG
        ):
            failures.append(
                f"boundary_tt={boundary_tt:.1f} "
                f"ra_before_deg={ra_before_step_deg:.12g} "
                f"ra_after_deg={ra_after_step_deg:.12g} "
                f"dec_before_deg={dec_before_step_deg:.12g} "
                f"dec_after_deg={dec_after_step_deg:.12g}"
            )

    assert not failures, "Moon RA/Dec discontinuities detected across DE441 split boundaries:\n" + "\n".join(failures)