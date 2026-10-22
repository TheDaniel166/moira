"""Installed-resource integration across every requested body family.

Positions are compared with the canonical apparent geocentric provider at
JD UT1 2451545.0, using its TT/TDB conversion. This is integration/regression
parity, not independent certification of the installed orbit solutions.
"""

import hashlib
import json
import os
from pathlib import Path

import pytest

from moira.aspects import AspectPolicy
from moira.constants import HouseSystem
from moira.geodetic import GeodeticLocation, geodetic_chart
from moira.geodetic_analysis import GeodeticNamedLocation, compare_geodetic_locations
from moira.geodetic_curves import geodetic_angular_loci
from moira.geodetic_inputs import geodetic_snapshot_at
from moira.geodetic_timing import GeodeticFixedReference, GeodeticTimingPolicy, find_geodetic_transits
from moira.obliquity import true_obliquity
from moira.planets import planet_at


@pytest.fixture(scope="module")
def geodetic_comet_reader(small_body_reader_pool):
    """Explicit hash-verified released shard; no download or ambient install.

    Only this shard is certified by the receipt here, not the entire comet
    release. Reuse the separately admitted planetary/asteroid pool unchanged.
    """
    from moira._spk_body_kernel import SmallBodyKernel
    from moira.spk_reader import KernelPool
    configured = os.environ.get("MOIRA_TEST_GEODETIC_COMET_SPK")
    if not configured:
        pytest.skip("explicit released Halley shard not configured")
    path = Path(configured)
    manifest = json.loads((Path(__file__).resolve().parents[2] / "moira/kernels/comets/manifest.json").read_bytes())
    shard = next(s for s in manifest["shards"] if 1000001 in s["bodies"])
    assert path.stat().st_size == shard["bytes"]
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    assert hasher.hexdigest() == shard["sha256"]
    comet = SmallBodyKernel(path)
    try:
        assert comet.has_body(1000001)
        yield KernelPool((*small_body_reader_pool._readers, comet))
    finally:
        comet.close()


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", ["Sun", "asteroid:Ceres", "asteroid:Chiron", "asteroid:Eris", "comet:1P/Halley"])
def test_resource_backed_body_cross_feature_contracts(small_body_reader_context, jd_j2000, body, request):
    pool = request.getfixturevalue("geodetic_comet_reader") if body.startswith("comet:") else small_body_reader_context
    snapshot = geodetic_snapshot_at(jd_j2000, [body], reader=pool)
    position = planet_at(body, jd_j2000, reader=pool)
    assert snapshot.complete
    assert snapshot.positions[0].tropical_longitude_deg == position.longitude
    eps = true_obliquity(snapshot.jd_tt)
    longitude = (position.longitude + 180) % 360 - 180
    places = [GeodeticNamedLocation("reference", GeodeticLocation(35, longitude)),
              GeodeticNamedLocation("other", GeodeticLocation(-35, 10))]
    comparisons = compare_geodetic_locations(places, snapshot, obliquity=eps, system=HouseSystem.EQUAL, aspect_policy=AspectPolicy(tier=0))
    assert len(comparisons.results) == 2
    assert all(r.overlay.snapshot is snapshot for r in comparisons.results)
    assert any(c.aspect == "Conjunction" and c.body2 == "MC" for c in comparisons.results[0].overlay.contacts)
    loci = geodetic_angular_loci(snapshot, obliquity=eps)
    assert loci.complete and all(locus.segments for locus in loci.loci)
    reference = GeodeticFixedReference(geodetic_chart(longitude, 35, eps), jd_j2000, snapshot.jd_tt, ("MC",))
    result = find_geodetic_transits(reference, body, jd_j2000 - 2, jd_j2000 + 2, aspects=((0, 1),),
                                    policy=GeodeticTimingPolicy(step_days=.5), reader=pool)
    assert result.complete, result.reasons
    assert result.resources
    assert all(r.source_sha256 and r.intervals_tdb for r in result.resources)
    assert any(abs(e.jd_ut1 - jd_j2000) <= 2e-6 for e in result.events)
    for event in result.events:
        check = planet_at(body, event.jd_ut1, reader=pool).longitude
        residual = abs((check - position.longitude + 180) % 360 - 180)
        assert residual <= 1e-6


@pytest.mark.loopback
@pytest.mark.requires_ephemeris
def test_existing_comet_return_route_with_explicit_released_resource(geodetic_comet_reader, monkeypatch):
    """Rerun the unchanged legacy route covenant with its required comet data."""
    from tests.server.test_server_transit_routes import test_planet_return_route_accepts_catalogued_small_body
    test_planet_return_route_accepts_catalogued_small_body("comet:2P/Encke", geodetic_comet_reader, monkeypatch)
