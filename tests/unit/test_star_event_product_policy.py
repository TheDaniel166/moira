"""Star rise/set, transit and paran events: the explicit star-product policy.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 5.
The default is the astrometric star (kernel-free, unchanged results); the
apparent star is an explicit opt-in that needs a planetary kernel.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from moira import parans
from moira.rise_set import (
    DEFAULT_STAR_EVENT_PRODUCT,
    RiseSetPolicy,
    find_phenomena,
    get_transit,
    horizon_crossing_availability,
)
from moira.spk_reader import use_reader_override

JD_DAY = 2460600.5          # 2024-10-14 0h UT
LAT, LON = 51.5, -0.1


def test_default_is_astrometric_and_unknown_products_are_refused() -> None:
    assert DEFAULT_STAR_EVENT_PRODUCT == "astrometric"
    assert RiseSetPolicy().star_product == "astrometric"
    with pytest.raises(ValueError, match="star_product"):
        RiseSetPolicy(star_product="geometric")
    with pytest.raises(ValueError, match="star_product"):
        get_transit("Regulus", JD_DAY, LAT, LON, star_product="true")
    with pytest.raises(ValueError, match="star_product"):
        horizon_crossing_availability("Regulus", JD_DAY, LAT, LON, star_product="true")


def test_default_star_events_need_no_kernel_and_match_explicit_astrometric() -> None:
    default = find_phenomena("Regulus", JD_DAY, LAT, LON)
    explicit = find_phenomena("Regulus", JD_DAY, LAT, LON, policy=RiseSetPolicy(star_product="astrometric"))
    assert default == explicit
    assert {"Rise", "Set", "Transit"} <= set(default)


@pytest.mark.requires_ephemeris
def test_apparent_star_events_shift_by_seconds(planetary_reader) -> None:
    astrometric = find_phenomena("Regulus", JD_DAY, LAT, LON)
    with use_reader_override(planetary_reader):
        apparent = find_phenomena("Regulus", JD_DAY, LAT, LON, policy=RiseSetPolicy(star_product="apparent"))
    for event in ("Rise", "Set", "Transit"):
        shift_seconds = abs(apparent[event] - astrometric[event]) * 86400.0
        # Up to ~20 arcsec of aberration at 15 arcsec per second, more on a
        # slow horizon crossing; never zero for a star 20 deg from the apex.
        assert 0.0 < shift_seconds < 10.0, (event, shift_seconds)


@pytest.mark.requires_ephemeris
def test_paran_cache_keeps_products_apart(planetary_reader) -> None:
    bodies = ["Regulus", "Capella"]
    with use_reader_override(planetary_reader), parans._paran_crossing_cache_scope():
        astrometric = parans.find_parans(bodies, JD_DAY, LAT, LON, orb_minutes=30.0)
        apparent = parans.find_parans(bodies, JD_DAY, LAT, LON, orb_minutes=30.0, star_product="apparent")
        again = parans.find_parans(bodies, JD_DAY, LAT, LON, orb_minutes=30.0)
    assert astrometric and len(astrometric) == len(apparent)
    assert [p.jd1 for p in again] == [p.jd1 for p in astrometric]
    assert any(abs(a.jd1 - b.jd1) > 0.0 for a, b in zip(astrometric, apparent))
    assert max(abs(a.jd1 - b.jd1) for a, b in zip(astrometric, apparent)) * 86400.0 < 10.0


@pytest.mark.loopback
def test_apparent_star_parans_without_a_kernel_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from moira_server.app import create_app
    from moira_server.config import ServerConfig

    monkeypatch.setattr("moira_server.app.create_engine", lambda config: SimpleNamespace(_reader=None))
    app = create_app(ServerConfig(docs_enabled=False))
    body = {"bodies": ["Regulus", "Capella"], "jd_day": JD_DAY, "lat": LAT, "lon": LON, "orb_minutes": 4.0}
    with TestClient(app) as client:
        kernel_free = client.post("/v1/parans/search", json=body)
        apparent = client.post("/v1/parans/search", json={**body, "star_product": "apparent"})
        unknown = client.post("/v1/parans/search", json={**body, "star_product": "true"})
        transit = client.post(
            "/v1/rise-set/transit",
            json={"body": "Regulus", "jd_day": JD_DAY, "lat": LAT, "lon": LON, "star_product": "apparent"},
        )
    assert kernel_free.status_code == 200
    assert apparent.status_code == 503
    assert apparent.json()["error_code"] == "kernel_not_ready"
    assert unknown.status_code == 422
    assert transit.status_code == 503
