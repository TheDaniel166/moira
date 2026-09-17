"""Layer-2 kernel validation for Orbital Core Stage 1."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _bind_ephemeris_time
from moira.julian import tdb_to_tt
from moira.orbits import (
    OrbitalCenter,
    OrbitalFrame,
    OrbitShape,
    osculating_elements,
)
from moira.spk_reader import KernelPool


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures"
PLANET_RECORDS = tuple(
    record
    for name in (
        "horizons_orbital_elements_calibration.json",
        "horizons_orbital_elements_holdout.json",
    )
    for record in json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))[
        "records"
    ]
)
WHEEL_MANIFEST_PATH = (
    Path(__file__).parents[2]
    / "moira"
    / "kernels"
    / "asteroids_wheel"
    / "manifest.json"
)
WHEEL_MANIFEST = json.loads(WHEEL_MANIFEST_PATH.read_text(encoding="utf-8"))
WHEEL_BODY_IDS = tuple(
    body_id
    for shard in WHEEL_MANIFEST["shards"]
    for body_id in shard["bodies"]
)
ADMITTED_ASTEROID_RELEASES = {
    "moira-asteroids": "2026.08.12.1",
    WHEEL_MANIFEST["catalog_id"]: WHEEL_MANIFEST["catalog_version"],
}


def _ut1_for_exact_tdb(epoch_tdb: float, reader) -> float:
    """Invert the governed bound clock without introducing another model."""

    jd_ut1 = tdb_to_tt(epoch_tdb)
    for _ in range(8):
        bound = _bind_ephemeris_time(jd_ut1, reader)
        residual = epoch_tdb - bound.epoch_tdb
        if abs(residual) <= math.ulp(epoch_tdb):
            return jd_ut1
        jd_ut1 += residual
    raise AssertionError(f"could not bind exact JD(TDB) {epoch_tdb:.12f}")


def _angle_error(left: float, right: float) -> float:
    return abs(((left - right + 180.0) % 360.0) - 180.0)


def _assert_horizons_elements(actual, expected) -> None:
    assert actual.shape is OrbitShape.ELLIPTIC
    assert actual.semi_major_axis_au == pytest.approx(
        expected["semi_major_axis_au"], abs=2.0e-13
    )
    assert actual.eccentricity == pytest.approx(
        expected["eccentricity"], abs=2.0e-14
    )
    assert actual.inclination_deg == pytest.approx(
        expected["inclination_deg"], abs=2.0e-12
    )
    assert _angle_error(
        actual.lon_ascending_node_deg, expected["lon_ascending_node_deg"]
    ) < 5.0e-10
    assert _angle_error(
        actual.arg_pericenter_deg, expected["arg_perihelion_deg"]
    ) < 5.0e-10
    assert _angle_error(
        actual.mean_anomaly_deg, expected["mean_anomaly_deg"]
    ) < 5.0e-10
    assert actual.pericenter_distance_au == pytest.approx(
        expected["perihelion_distance_au"], abs=2.0e-13
    )
    assert actual.apocenter_distance_au == pytest.approx(
        expected["aphelion_distance_au"], abs=2.0e-13
    )
    assert actual.mean_motion_deg_per_day == pytest.approx(
        expected["mean_motion_deg_per_day"], abs=2.0e-12
    )
    assert actual.orbital_period_days == pytest.approx(
        expected["orbital_period_days"], abs=2.0e-8
    )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "record", PLANET_RECORDS, ids=[record["body"] for record in PLANET_RECORDS]
)
def test_frozen_horizons_planet_holdouts_at_identical_tdb(
    record, planetary_reader
) -> None:
    pool = KernelPool((planetary_reader,))
    epoch_tdb = record["jd_tdb"]
    center_id = record["center_naif_id"]
    body_id = record["body_naif_id"]
    state = pool.position_and_velocity_tdb_with_receipt(
        center_id, body_id, epoch_tdb
    )
    vector = record["vector_icrf_km_km_s"]

    assert state.position_km == pytest.approx(
        (vector["x"], vector["y"], vector["z"]), abs=1.0e-5
    )
    assert state.velocity_km_per_day == pytest.approx(
        (
            vector["vx"] * 86400.0,
            vector["vy"] * 86400.0,
            vector["vz"] * 86400.0,
        ),
        abs=1.0e-5,
    )
    assert state.legs
    assert all(leg.source.planetary_ephemeris == "DE441" for leg in state.legs)

    position_tt, velocity_tt = pool.position_and_velocity(
        center_id, body_id, tdb_to_tt(epoch_tdb)
    )
    assert position_tt == pytest.approx(state.position_km, abs=1.0e-8)
    assert velocity_tt == pytest.approx(state.velocity_km_per_day, abs=1.0e-8)

    center = (
        OrbitalCenter.EARTH if center_id == 399 else OrbitalCenter.SUN
    )
    result = osculating_elements(
        body_id,
        _ut1_for_exact_tdb(epoch_tdb, pool),
        center=center,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        reader=pool,
    )
    assert result.epoch_tdb == epoch_tdb
    _assert_horizons_elements(
        result, record["elements_j2000_ecliptic_au_day"]
    )
    assert result.provenance.gravity.planetary_ephemeris == "DE441"
    assert result.provenance.frame_construction.router_branch == "fixed_j2000"
    assert result.provenance.time_conversion.tt_tdb_version == "naif0012"
    assert result.provenance.state_source.legs


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_packaged_twenty_five_asteroids_have_strict_receipted_elements(
    receipted_small_body_reader_pool,
) -> None:
    small_body_reader_pool = receipted_small_body_reader_pool
    assert len(WHEEL_BODY_IDS) == WHEEL_MANIFEST["body_count"] == 25
    epoch_tdb = 2460676.5
    jd_ut1 = _ut1_for_exact_tdb(epoch_tdb, small_body_reader_pool)

    for body_id in WHEEL_BODY_IDS:
        state = small_body_reader_pool.position_and_velocity_tdb_with_receipt(
            10, body_id, epoch_tdb
        )
        assert all(math.isfinite(value) for value in state.position_km)
        assert all(math.isfinite(value) for value in state.velocity_km_per_day)
        assert state.covered_intervals_tdb

        reverse = small_body_reader_pool.position_and_velocity_tdb_with_receipt(
            body_id, 10, epoch_tdb
        )
        assert reverse.position_km == pytest.approx(
            tuple(-value for value in state.position_km), abs=1.0e-8
        )
        assert reverse.velocity_km_per_day == pytest.approx(
            tuple(-value for value in state.velocity_km_per_day), abs=1.0e-8
        )

        result = osculating_elements(
            body_id,
            jd_ut1,
            center=OrbitalCenter.SUN,
            frame=OrbitalFrame.J2000_ECLIPTIC,
            reader=small_body_reader_pool,
        )
        assert result.epoch_tdb == epoch_tdb
        assert math.isfinite(result.eccentricity)
        assert math.isfinite(result.pericenter_distance_au)
        source_legs = [
            leg
            for leg in result.provenance.state_source.legs
            if leg.catalog_id in ADMITTED_ASTEROID_RELEASES
        ]
        assert source_legs, (
            f"NAIF {body_id} provenance omitted an admitted asteroid release: "
            f"{result.provenance.state_source.legs!r}"
        )
        assert all(
            leg.catalog_version == ADMITTED_ASTEROID_RELEASES[leg.catalog_id]
            and leg.manifest_sha256
            and leg.kernel_sha256
            for leg in source_legs
        )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_real_kernel_coverage_endpoints_are_inclusive(planetary_reader) -> None:
    intervals = planetary_reader.coverage_intervals_tdb(0, 10)
    assert intervals
    for boundary in intervals[0]:
        state = planetary_reader.position_and_velocity_tdb_with_receipt(
            0, 10, boundary
        )
        assert state.epoch_tdb == boundary
        assert all(math.isfinite(value) for value in state.position_km)
