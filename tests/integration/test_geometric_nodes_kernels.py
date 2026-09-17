"""Stage 3 kernel validation for geometric nodes on the orbital core."""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from moira._ephemeris_time import _bind_ephemeris_time
from moira._kernel_paths import find_all_small_body_manifests
from moira._orbital_errors import (
    OrbitalBodyNotLoadedError,
    OrbitalCoverageError,
    OrbitalFrameUnavailableError,
    OrbitalKernelMissingError,
)
from moira.constants import Body
from moira.julian import tdb_to_tt
from moira.orbits import OrbitalCenter, OrbitalFrame, OrbitShape, osculating_elements
from moira.planetary_nodes import geometric_node
from moira.spk_reader import KernelPool
from moira_server.models.nodes import GeometricNodeRequest
from moira_server.services.nodes import compute_geometric_node


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "horizons_orbital_elements_catalog_holdout.json"
)
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
FIXTURE = json.loads(FIXTURE_BYTES)
CATALOG_RECORDS = tuple(FIXTURE["records"])
STAGE3_ACCEPTANCE_GATES = {
    "semi_major_axis_absolute_au": 2.0e-13,
    "eccentricity_absolute": 2.0e-14,
    "inclination_absolute_deg": 2.0e-12,
    "node_angular_absolute_deg": 5.0e-10,
    "arg_pericenter_angular_absolute_deg": 5.0e-10,
}
PLANET_BODIES = (
    Body.MERCURY,
    Body.VENUS,
    Body.EARTH,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)


def _ut1_for_exact_tdb(epoch_tdb: float, reader) -> float:
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


def _catalog_node_admission(record) -> dict | None:
    """Return a governed release's Stage 3 numeric admission, if present."""

    target = record["body_naif_id"]
    for manifest_path in find_all_small_body_manifests():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        body_ids = {
            body_id
            for shard in manifest.get("shards", ())
            for body_id in shard.get("bodies", ())
        }
        if target not in body_ids:
            continue
        admission = manifest.get("validation", {}).get("geometric_nodes")
        return admission if isinstance(admission, dict) else None
    return None


def _assert_node_maps_true_date_core(node, elements) -> None:
    assert elements.frame is OrbitalFrame.TRUE_ECLIPTIC_OF_DATE
    assert elements.center is OrbitalCenter.SUN
    assert node.planet == elements.body.name
    assert node.ascending_node == elements.lon_ascending_node_deg
    assert node.perihelion == elements.pericenter_ecliptic_lon_deg
    assert node.aphelion == pytest.approx((node.perihelion + 180.0) % 360.0)
    assert node.inclination == elements.inclination_deg
    assert node.eccentricity == elements.eccentricity
    assert node.semi_major_axis == elements.semi_major_axis_au
    assert elements.provenance.frame_construction.router_branch == "modern_true"
    assert elements.provenance.frame_model_interval_tt == (2415020.0, 2488070.0)
    assert elements.provenance.gravity.planetary_ephemeris == "DE441"
    assert elements.provenance.state_source.legs


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", PLANET_BODIES)
def test_planetary_geometric_nodes_are_exact_true_date_core_adapters(
    body,
    planetary_reader,
) -> None:
    pool = KernelPool((planetary_reader,))
    jd_ut = 2460676.5
    node = geometric_node(body, jd_ut, pool)
    elements = osculating_elements(
        body,
        jd_ut,
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
        reader=pool,
    )
    _assert_node_maps_true_date_core(node, elements)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_ut",
    (2415018.5, 2488071.5),
    ids=("before-1900", "after-2100"),
)
def test_geometric_node_fails_explicitly_outside_true_date_model(
    jd_ut,
    planetary_reader,
) -> None:
    with pytest.raises(OrbitalFrameUnavailableError) as caught:
        geometric_node(Body.MARS, jd_ut, planetary_reader)

    assert caught.value.frame == OrbitalFrame.TRUE_ECLIPTIC_OF_DATE.value
    assert caught.value.supported_intervals_tt == ((2415020.0, 2488070.0),)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_geometric_node_service_serializes_the_real_core_receipt(
    planetary_reader,
) -> None:
    response = compute_geometric_node(
        SimpleNamespace(_reader=planetary_reader),
        GeometricNodeRequest(body="Mars", jd_ut=2460676.5),
    )
    payload = response.model_dump()

    assert payload["node"]["body"] == "Mars"
    provenance = payload["provenance"]
    assert provenance["center"] == "SUN"
    assert provenance["frame"] == "TRUE_ECLIPTIC_OF_DATE"
    assert provenance["time"]["input_time_scale"] == "UT1_JD"
    assert provenance["time"]["state_evaluation_scale"] == "TDB_JD"
    assert provenance["gravity"]["rule"] == "SUN_PLUS_PLANET_SYSTEM"
    assert provenance["frame_construction"]["router_branch"] == "modern_true"
    assert provenance["state_source"]["legs"]
    assert all("path" not in leg for leg in provenance["state_source"]["legs"])


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "record",
    CATALOG_RECORDS,
    ids=[record["body"] for record in CATALOG_RECORDS],
)
def test_loaded_catalog_geometric_nodes_are_exact_true_date_core_adapters(
    record,
    receipted_small_body_reader_pool,
) -> None:
    pool = receipted_small_body_reader_pool
    epoch_tdb = record["jd_tdb"]
    jd_ut = _ut1_for_exact_tdb(epoch_tdb, pool)
    body_id = record["body_naif_id"]

    try:
        node = geometric_node(body_id, jd_ut, pool)
    except (
        OrbitalBodyNotLoadedError,
        OrbitalCoverageError,
        OrbitalKernelMissingError,
    ) as exc:
        pytest.skip(
            f"governed runtime prerequisite unavailable for "
            f"{record['body']}: {type(exc).__name__}"
        )
    true_date = osculating_elements(
        body_id,
        jd_ut,
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
        reader=pool,
    )
    _assert_node_maps_true_date_core(node, true_date)
    assert true_date.epoch_tdb == epoch_tdb
    assert any(
        leg.catalog_id
        in {"moira-asteroids", "moira-asteroids-wheel", "moira-comets"}
        for leg in true_date.provenance.state_source.legs
    )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "record",
    CATALOG_RECORDS,
    ids=[record["body"] for record in CATALOG_RECORDS],
)
def test_catalog_geometric_nodes_match_frozen_horizons_when_admitted(
    record,
    receipted_small_body_reader_pool,
) -> None:
    admission = _catalog_node_admission(record)
    if admission is None:
        pytest.skip(
            f"the governed catalog containing {record['body']} has no "
            "reviewed Stage 3 geometric-node accuracy admission"
        )
    assert admission["reference_fixture_sha256"] == FIXTURE_SHA256
    assert admission["acceptance_gates"] == STAGE3_ACCEPTANCE_GATES

    pool = receipted_small_body_reader_pool
    epoch_tdb = record["jd_tdb"]
    jd_ut = _ut1_for_exact_tdb(epoch_tdb, pool)
    body_id = record["body_naif_id"]

    # The frozen official Horizons holdout is J2000 ecliptic. Validate the
    # admitted release's bound state and gravity route at the identical TDB
    # instant.  The independent adapter test above proves true-date mapping.
    try:
        j2000 = osculating_elements(
            body_id,
            jd_ut,
            center=OrbitalCenter.SUN,
            frame=OrbitalFrame.J2000_ECLIPTIC,
            reader=pool,
        )
    except (
        OrbitalBodyNotLoadedError,
        OrbitalCoverageError,
        OrbitalKernelMissingError,
    ) as exc:
        pytest.skip(
            f"governed runtime prerequisite unavailable for "
            f"{record['body']}: {type(exc).__name__}"
        )
    expected = record["elements_j2000_ecliptic_au_day"]
    assert j2000.shape is OrbitShape.ELLIPTIC
    assert j2000.semi_major_axis_au == pytest.approx(
        expected["semi_major_axis_au"],
        abs=STAGE3_ACCEPTANCE_GATES["semi_major_axis_absolute_au"],
    )
    assert j2000.eccentricity == pytest.approx(
        expected["eccentricity"],
        abs=STAGE3_ACCEPTANCE_GATES["eccentricity_absolute"],
    )
    assert j2000.inclination_deg == pytest.approx(
        expected["inclination_deg"],
        abs=STAGE3_ACCEPTANCE_GATES["inclination_absolute_deg"],
    )
    assert _angle_error(
        j2000.lon_ascending_node_deg,
        expected["lon_ascending_node_deg"],
    ) < STAGE3_ACCEPTANCE_GATES["node_angular_absolute_deg"]
    assert _angle_error(
        j2000.arg_pericenter_deg,
        expected["arg_perihelion_deg"],
    ) < STAGE3_ACCEPTANCE_GATES[
        "arg_pericenter_angular_absolute_deg"
    ]
