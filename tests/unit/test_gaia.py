from __future__ import annotations

import math
import struct
from pathlib import Path

import pytest

import moira.gaia as gaia


def _record(
    ra: float,
    dec: float,
    pmra: float = 0.0,
    pmdec: float = 0.0,
    parallax: float = 10.0,
    parallax_error: float = 0.1,
    rv: float = math.nan,
    gmag: float = 5.0,
    bp_rp: float = math.nan,
    teff: float = math.nan,
) -> tuple[float, ...]:
    return (ra, dec, pmra, pmdec, parallax, parallax_error, rv, gmag, bp_rp, teff)


def _write_catalog(path: Path, records: list[tuple[float, ...]]) -> None:
    payload = bytearray()
    payload.extend(struct.pack("<4sI", b"GAIA", len(records)))
    for rec in records:
        payload.extend(struct.pack("<10f", *rec))
    path.write_bytes(payload)


def test_bp_rp_to_quality_boundaries_and_nan() -> None:
    assert gaia.bp_rp_to_quality(math.nan) is None
    assert gaia.bp_rp_to_quality(0.0).planet == "Saturn"
    assert gaia.bp_rp_to_quality(0.5).planet == "Jupiter"
    assert gaia.bp_rp_to_quality(1.0).planet == "Sun"
    assert gaia.bp_rp_to_quality(1.5).planet == "Venus"
    assert gaia.bp_rp_to_quality(2.0).planet == "Mars"
    assert gaia.bp_rp_to_quality(2.5).planet == "Saturn"


def test_gaia_star_position_sign_degree_and_repr() -> None:
    pos = gaia.GaiaStarPosition(
        source_index=7,
        longitude=45.5,
        latitude=-1.25,
        magnitude=4.2,
        bp_rp=1.1,
        teff_k=5800.0,
        parallax_mas=10.0,
        distance_ly=326.156,
        quality=gaia.bp_rp_to_quality(1.1),
        is_topocentric=False,
        is_true_pos=False,
    )
    assert pos.sign == "Taurus"
    assert pos.sign_degree == pytest.approx(15.5)
    assert "Taurus" in repr(pos)
    assert "G=4.20" in repr(pos)


def test_load_gaia_catalog_and_catalog_info(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "gaia_test.bin"
    records = [
        _record(10.0, 5.0, gmag=4.2, bp_rp=0.8, teff=7000.0),
        _record(20.0, -3.0, gmag=6.1, bp_rp=1.4, teff=5800.0),
        _record(30.0, 7.5, gmag=2.5, bp_rp=math.nan, teff=math.nan),
    ]
    _write_catalog(path, records)

    monkeypatch.setattr(gaia, "_records", None)
    monkeypatch.setattr(gaia, "_lon_index", None)
    monkeypatch.setattr(gaia, "_catalog_path", None)

    gaia.load_gaia_catalog(path)

    assert gaia.catalog_size() == 3
    info = gaia.gaia_catalog_info()
    assert info["path"] == str(path)
    assert info["n_stars"] == 3
    assert info["mag_min"] == pytest.approx(2.5)
    assert info["mag_max"] == pytest.approx(6.1)
    assert info["n_with_color"] == 2
    assert info["n_with_teff"] == 2
    assert gaia._lon_index is not None
    assert len(gaia._lon_index) == 2


def test_lon_range_indices_handles_wraparound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gaia, "_lon_index", [(1.0, 10), (5.0, 20), (355.0, 30), (359.0, 40)])
    assert gaia._lon_range_indices(0.0, 3.0) == [40, 10]
    assert gaia._lon_range_indices(5.0, 0.5) == [20]


def test_gaia_star_at_validates_index_and_uses_local_sidereal_when_topocentric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gaia, "_records", [_record(10.0, 5.0)])
    monkeypatch.setattr(gaia, "_catalog_path", Path("dummy.bin"))

    with pytest.raises(IndexError):
        gaia.gaia_star_at(3, 2451545.0)

    calls: dict[str, object] = {}

    def fake_record_to_position(idx, rec, jd_tt, observer_lat=None, observer_lon=None, observer_elev_m=0.0, lst_deg=None, true_position=False):
        calls["args"] = (idx, jd_tt, observer_lat, observer_lon, observer_elev_m, lst_deg, true_position)
        return "sentinel"

    monkeypatch.setattr(gaia, "_record_to_position", fake_record_to_position)
    monkeypatch.setattr("moira.julian.local_sidereal_time", lambda jd_tt, lon: 123.45)

    result = gaia.gaia_star_at(0, 2451545.0, observer_lat=40.0, observer_lon=-74.0, observer_elev_m=12.0, true_position=True)
    assert result == "sentinel"
    assert calls["args"] == (0, 2451545.0, 40.0, -74.0, 12.0, 123.45, True)


def test_record_to_position_builds_semantic_vessel(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = _record(10.0, 20.0, parallax=10.0, gmag=4.5, bp_rp=1.1, teff=5800.0)

    monkeypatch.setattr(gaia, "_apply_proper_motion_gaia", lambda *args, **kwargs: (11.0, 21.0))
    monkeypatch.setattr(gaia, "_topocentric_stellar_parallax", lambda *args, **kwargs: (0.0, 0.0))
    monkeypatch.setattr(gaia, "equatorial_to_ecliptic", lambda ra, dec, obliq: (100.0, 5.0))
    monkeypatch.setattr(gaia, "_annual_parallax", lambda lon, lat, plx, sun_lon: (lon, lat))

    pos = gaia._record_to_position(
        7,
        rec,
        jd_tt=2451545.0,
        observer_lat=40.0,
        observer_lon=-74.0,
        observer_elev_m=0.0,
        lst_deg=120.0,
        true_position=True,
        _dpsi=0.2,
        _obl_mean=23.4,
        _prec=0.5,
        _sun_lon=0.0,
    )

    assert pos.source_index == 7
    assert pos.longitude == pytest.approx(100.7)
    assert pos.latitude == pytest.approx(5.0)
    assert pos.magnitude == pytest.approx(4.5)
    assert pos.quality is not None
    assert pos.quality.planet == "Sun"
    assert pos.distance_ly == pytest.approx((1000.0 / 10.0) * 3.26156)
    assert pos.is_topocentric is True
    assert pos.is_true_pos is True


def test_gaia_stars_near_filters_and_sorts_by_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    records = [
        _record(10.0, 0.0, gmag=4.0),
        _record(20.0, 0.0, gmag=6.0),
        _record(30.0, 0.0, gmag=5.0),
    ]
    monkeypatch.setattr(gaia, "_records", records)
    monkeypatch.setattr(gaia, "_catalog_path", Path("dummy.bin"))

    longitudes = {0: 100.2, 1: 101.7, 2: 98.8}

    def fake_record_to_position(idx, rec, jd_tt, **kwargs):
        return gaia.GaiaStarPosition(
            source_index=idx,
            longitude=longitudes[idx],
            latitude=0.0,
            magnitude=float(rec[gaia._F_GMAG]),
            bp_rp=math.nan,
            teff_k=math.nan,
            parallax_mas=10.0,
            distance_ly=326.156,
            quality=None,
            is_topocentric=False,
            is_true_pos=False,
        )

    monkeypatch.setattr(gaia, "_record_to_position", fake_record_to_position)

    results = gaia.gaia_stars_near(100.0, 2451545.0, orb=2.0, max_magnitude=5.5)
    assert [row.source_index for row in results] == [0, 2]


def test_gaia_stars_by_magnitude_returns_brightest_first(monkeypatch: pytest.MonkeyPatch) -> None:
    records = [
        _record(10.0, 0.0, gmag=4.5),
        _record(20.0, 0.0, gmag=2.0),
        _record(30.0, 0.0, gmag=6.5),
    ]
    monkeypatch.setattr(gaia, "_records", records)
    monkeypatch.setattr(gaia, "_catalog_path", Path("dummy.bin"))

    def fake_record_to_position(idx, rec, jd_tt, **kwargs):
        return gaia.GaiaStarPosition(
            source_index=idx,
            longitude=float(idx) * 10.0,
            latitude=0.0,
            magnitude=float(rec[gaia._F_GMAG]),
            bp_rp=math.nan,
            teff_k=math.nan,
            parallax_mas=10.0,
            distance_ly=326.156,
            quality=None,
            is_topocentric=False,
            is_true_pos=False,
        )

    monkeypatch.setattr(gaia, "_record_to_position", fake_record_to_position)

    results = gaia.gaia_stars_by_magnitude(2451545.0, max_magnitude=5.0)
    assert [row.source_index for row in results] == [1, 0]
