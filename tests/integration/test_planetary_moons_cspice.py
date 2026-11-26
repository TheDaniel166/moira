"""Matched DE441, JPL satellite, and NAIF figure fixtures for moon snapshots.

Event seed epochs are TDB seconds from the 2000–2039 center-crossing study.
CSPICE computes the finite-disk contacts and classifications live. No seed
contains an expected classification from Moira or a rounded published contact.
"""

import json
from math import atan2, cos, degrees, dist, sin
import os
from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira._planetary_moon_data import SYSTEMS
from moira.constants import J2000
from moira.julian import tdb_to_tt
from moira.planetary_moon_events import find_planetary_moon_events
from moira.planetary_moons import PlanetaryMoons
from moira.spk_reader import OutOfRangeError, S_PER_DAY

SEEDS = {
    501: (332681303, 332758121, 345290578),
    502: (327659163, 327811267, 334248586),
    503: (284180414, 284490957, 284492529),
    504: (284221001, 284955613, 284960096),
    601: (333378514, 333989398, 284066339),
    602: (291484528, 291425265, 284080873),
    603: (292792942, 292874479, 315220717),
    604: (288762099, 288644255, 284145117),
    605: (287847792, 288042822, 284131651),
    606: (284628460, 285322860, 292198773),
    607: (284551828, 285526744, 292903799),
    608: (704544634, 701150402, 721775742),
}
COVERED_MOONS = tuple(SEEDS)
LABELS = {0: (None, "clear"), 1: ("transit", "partial"), 2: ("transit", "contained"),
          -1: ("occultation", "partial"), -3: ("occultation", "contained")}
ECLIPSES = {0: "clear", -1: "partial", -3: "total"}


def _data_path(variable):
    value = os.getenv(variable)
    if not value:
        pytest.skip(f"Set {variable} for the local satellite authority fixtures")
    return Path(value)


def _sphere(spice, body, radius):
    frame = f"MOIRA_TEST_SPHERE_{body}"
    code = 1500000 + body
    spice.pipool(f"FRAME_{frame}", [code])
    spice.pcpool(f"FRAME_{code}_NAME", [frame])
    spice.pipool(f"FRAME_{code}_CLASS", [4])
    spice.pipool(f"FRAME_{code}_CLASS_ID", [code])
    spice.pipool(f"FRAME_{code}_CENTER", [body])
    spice.pcpool(f"TKFRAME_{code}_RELATIVE", ["J2000"])
    spice.pcpool(f"TKFRAME_{code}_SPEC", ["MATRIX"])
    spice.pdpool(f"TKFRAME_{code}_MATRIX", [1, 0, 0, 0, 1, 0, 0, 0, 1])
    spice.pdpool(f"BODY{body}_RADII", [radius] * 3)


@pytest.fixture(scope="module")
def authority():
    spice = pytest.importorskip("spiceypy")
    reference = _data_path("MOIRA_TEST_DE441_CSPICE")
    early_reference = _data_path("MOIRA_TEST_DE441_CSPICE_EARLY")
    manifest_path = _data_path("MOIRA_TEST_PLANETARY_MOONS_MANIFEST")
    pck = _data_path("MOIRA_TEST_PLANETARY_MOONS_PCK")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        spice.furnsh([str(early_reference), str(reference), str(pck), *[
            str(manifest_path.parent / row["filename"]) for row in manifest["systems"].values()
        ]])
        for system in SYSTEMS:
            for moon in system.moons:
                _sphere(spice, moon.naif_id, moon.radius_km)
        with PlanetaryMoons.open(
            de441_path=find_planetary_kernel(), manifest_path=manifest_path,
        ) as engine:
            yield spice, engine, manifest_path
    finally:
        spice.kclear()


def _moon_shape(body):
    return str(body), "ELLIPSOID", f"MOIRA_TEST_SPHERE_{body}"


def _planet_shape(system):
    return str(system.center), "ELLIPSOID", f"IAU_{system.name.upper()}"


def _state_at(engine, et, planet=None):
    snapshot = engine.at(tdb_to_tt(J2000 + et / S_PER_DAY), planet=planet)
    return snapshot, (snapshot.jd_tdb - J2000) * S_PER_DAY


def _match_state(spice, snapshot, actual_et):
    for row in snapshot.moons:
        body, center = str(row.naif_id), str(row.planet_naif_id)
        state, _ = spice.spkezr(body, actual_et, "J2000", "NONE", center)
        # Same ephemeris identity, ICRF and represented TDB epoch. The
        # millimeter-scale position allowance is for reader arithmetic.
        assert dist(row.position_km, state[:3]) < 1e-6
        assert dist(row.velocity_km_per_day, state[3:] * S_PER_DAY) < 1e-5
        parent_ray, parent_delay = spice.spkpos(center, actual_et, "J2000", "CN", "399")
        moon_ray, moon_delay = spice.spkpos(body, actual_et, "J2000", "CN", "399")
        parent_range, ra, dec = spice.recrad(parent_ray)
        east = (-sin(ra), cos(ra), 0.0)
        north = (-sin(dec) * cos(ra), -sin(dec) * sin(ra), cos(dec))
        depth = spice.vdot(moon_ray, spice.vhat(parent_ray))
        for basis, observed in ((east, row.earth_view.east_arcsec), (north, row.earth_view.north_arcsec)):
            expected_offset = degrees(atan2(spice.vdot(basis, moon_ray), depth)) * 3600.0
            assert observed == pytest.approx(expected_offset, abs=1e-6)
        assert row.earth_view.range_offset_km == pytest.approx(spice.vnorm(moon_ray) - parent_range, abs=1e-4)
        assert row.earth_view.moon_emission_offset_days * S_PER_DAY == pytest.approx(-moon_delay, abs=1e-6)
        assert row.earth_view.planet_emission_offset_days * S_PER_DAY == pytest.approx(-parent_delay, abs=1e-6)
        phase = spice.phaseq(actual_et, body, "10", center, "CN") * spice.dpr()
        assert row.phase.angle_deg == pytest.approx(phase, abs=1e-7)
        expected = (1.0 + spice.vdot(
            spice.vhat(spice.spkpos("10", actual_et + row.phase.emission_offset_days * S_PER_DAY,
                                    "J2000", "CN", body)[0]),
            spice.vhat(-spice.spkpos(body, actual_et, "J2000", "CN", center)[0]),
        )) / 2.0
        assert row.phase.illuminated_fraction == pytest.approx(expected, abs=1e-8)


def _check_events(spice, row, et):
    system = next(system for system in SYSTEMS if system.name == row.planet)
    shape = _planet_shape(system)
    body = str(row.naif_id)
    earth_code = spice.occult(*_moon_shape(row.naif_id), *shape, "CN", "399", et)
    shadow_et = et - spice.spkpos(body, et, "J2000", "CN", "399")[1]
    eclipse_code = spice.occult("10", "ELLIPSOID", "IAU_SUN", *shape, "CN", body, shadow_et)
    assert (row.earth_view.event, row.earth_view.overlap) == LABELS[earth_code]
    assert row.eclipse == ECLIPSES[eclipse_code]
    assert et + row.eclipse_epoch_offset_days * S_PER_DAY == pytest.approx(shadow_et, abs=1e-5)
    return earth_code, eclipse_code


@pytest.mark.parametrize("et", [-7.8e9, -3.0e9, 0.0, 288757566.1853102, 848908869.1829523, 6.25e9])
def test_states_and_phase_with_same_ephemeris_and_epochs(authority, et):
    spice, engine, _ = authority
    result, actual_et = _state_at(engine, et)
    assert tuple(row.naif_id for row in result.moons) == COVERED_MOONS
    _match_state(spice, result, actual_et)


@pytest.mark.parametrize("body", COVERED_MOONS)
def test_transit_occultation_and_eclipse_contacts(authority, body):
    spice, engine, _ = authority
    system = next(system for system in SYSTEMS if any(m.naif_id == body for m in system.moons))
    moon, planet = _moon_shape(body), _planet_shape(system)
    cases = (
        (moon, planet, "399", 0),
        (planet, moon, "399", 1),
        (planet, ("10", "ELLIPSOID", "IAU_SUN"), str(body), 2),
    )
    for front, back, observer, index in cases:
        seed = SEEDS[body][index]
        confinement = spice.cell_double(2)
        spice.wninsd(seed - 43200, seed + 43200, confinement)
        windows = spice.gfoclt("ANY", *front, *back, "CN", observer, 120.0, confinement)
        start, stop = next(
            (a, b) for a, b in (spice.wnfetd(windows, i) for i in range(spice.wncard(windows)))
            if a < seed < b
        )
        active = []
        for time in (start - 1.0, start + 1.0, (start + stop) / 2, stop - 1.0, stop + 1.0):
            if index == 2:
                time += spice.spkpos("399", time, "J2000", "XCN", str(body))[1]
            result, epoch = _state_at(engine, time, system.name)
            row = next(row for row in result.moons if row.naif_id == body)
            codes = _check_events(spice, row, epoch)
            active.append(codes[1 if index == 2 else 0] != 0)
        assert active == [False, True, True, True, False]

        # Expected contacts are finite-disk GF roots. Convert an eclipse's
        # moon-centre observation epoch to the corresponding Earth reception.
        expected_contacts = [start, stop]
        if index == 2:
            expected_contacts = [
                time + spice.spkpos("399", time, "J2000", "XCN", str(body))[1]
                for time in expected_contacts
            ]
        kind = ("transit", "occultation", "eclipse")[index]
        search = find_planetary_moon_events(
            engine,
            tdb_to_tt(J2000 + (expected_contacts[0] - 1800) / S_PER_DAY),
            tdb_to_tt(J2000 + (expected_contacts[1] + 1800) / S_PER_DAY),
            moon_ids=(body,), kinds=(kind,),
        )
        assert search.status == "complete", (body, kind, search.unresolved_intervals)
        assert len(search.events) == 1
        event = search.events[0]
        assert not event.start_clipped and not event.end_clipped
        found_contacts = [
            (contact.jd_tdb - J2000) * S_PER_DAY
            for contact in event.contacts if contact.kind in ("ingress", "egress")
        ]
        # The earlier matched-state checks classify opposite signs one second
        # from each reference root. Apply the same tolerance to both times.
        assert found_contacts == pytest.approx(expected_contacts, abs=1.0, rel=0)
        if index == 2:
            for contact in event.contacts:
                assert contact.observer_offset_days == contact.moon_emission_offset_days < 0
                assert contact.sun_emission_offset_days < contact.observer_offset_days


def test_hubble_and_ganymede_cases(authority):
    spice, engine, _ = authority
    # TDB J2000 seconds for 2009-02-24 14:25 UTC, and the 2026-11-25
    # and 2026-11-29 Ganymede passages from the study's Earth view.
    observed, epoch = _state_at(engine, 288757566.1853102)
    saturn = {r.naif_id for r in observed.moons if r.planet == "Saturn" and r.earth_view.event == "transit"}
    assert saturn == {601, 602, 604, 606}
    centre = tdb_to_tt(J2000 + epoch / S_PER_DAY)
    search = find_planetary_moon_events(
        engine, centre - 0.15, centre + 0.15, moon_ids=tuple(sorted(saturn)), kinds=("transit",),
    )
    assert search.status == "complete"
    assert {event.naif_id for event in search.events if event.start_jd_tt < centre < event.end_jd_tt} == saturn
    for row in observed.moons:
        _check_events(spice, row, epoch)
    for et, expected in ((848908869.1829523, "transit"), (849214869.1830335, "occultation")):
        snap, epoch = _state_at(engine, et, "Jupiter")
        row = next(row for row in snap.moons if row.naif_id == 503)
        assert row.earth_view.event == expected
        _check_events(spice, row, epoch)


def test_coverage_and_repeatability(authority):
    _, engine, _ = authority
    coverage = engine.coverage_tdb()
    earliest, _ = coverage["Saturn"][0]
    with pytest.raises(OutOfRangeError):
        engine.at(tdb_to_tt(earliest + 1.0 / S_PER_DAY), planet="Saturn")
    with pytest.raises(OutOfRangeError):
        find_planetary_moon_events(
            engine, tdb_to_tt(earliest + 1.0 / S_PER_DAY), tdb_to_tt(earliest + 2.0 / S_PER_DAY),
            planet="Saturn",
        )
    exhausted = find_planetary_moon_events(
        engine, J2000, J2000 + 2.0, moon_ids=(501,), max_evaluations=1, mode="next",
    )
    assert exhausted.status == "evaluation_budget"
    assert exhausted.evaluations == 1
    assert exhausted.events == ()
    assert exhausted.unresolved_intervals[0].naif_id == 501
    first = engine.at(tdb_to_tt(J2000), planet="Jupiter")
    assert engine.at(tdb_to_tt(J2000), planet="Jupiter") == first
    assert tuple(row.naif_id for row in first.moons) == COVERED_MOONS[:4]


def test_eclipse_status_is_independent_of_phase_and_disk_occultation(authority):
    spice, engine, _ = authority
    io_shadow_epoch = float(SEEDS[501][2])
    time = io_shadow_epoch + spice.spkpos("399", io_shadow_epoch, "J2000", "XCN", "501")[1]
    jupiter, epoch = _state_at(engine, time, "Jupiter")
    io = jupiter.moons[0]
    assert io.eclipse == "total" and io.phase.illuminated_fraction > 0.98
    _check_events(spice, io, epoch)

    saturn, epoch = _state_at(engine, 849214869.1830335, "Saturn")
    mimas = saturn.moons[0]
    assert mimas.earth_view.event == "occultation" and mimas.eclipse == "total"
    _check_events(spice, mimas, epoch)
    centre = tdb_to_tt(J2000 + epoch / S_PER_DAY)
    search = find_planetary_moon_events(
        engine, centre - 0.08, centre + 0.08, moon_ids=(601,), kinds=("occultation", "eclipse"),
    )
    assert search.status == "complete"
    assert {event.kind for event in search.events if event.start_jd_tt < centre < event.end_jd_tt} == {
        "occultation", "eclipse",
    }


def test_open_receipts_and_lifecycle(authority, monkeypatch):
    import moira.planetary_moons as module

    _, _, path = authority
    base = find_planetary_kernel()
    records = json.loads(path.read_text(encoding="utf-8"))["systems"]
    monkeypatch.setattr(module, "_read_manifest", lambda _: {"Jupiter": records["Jupiter"]})
    with PlanetaryMoons.open(de441_path=base, manifest_path=path) as only_jupiter:
        assert tuple(only_jupiter.coverage_tdb()) == ("Jupiter",)
        with pytest.raises(FileNotFoundError, match="Saturn"):
            only_jupiter.at(J2000)
        assert len(only_jupiter.at(J2000, planet="Jupiter").moons) == 4
    with pytest.raises(RuntimeError, match="closed"):
        only_jupiter.at(J2000, planet="Jupiter")

    corrupt = dict(records["Jupiter"], sha256="0" * 64)
    monkeypatch.setattr(module, "_read_manifest", lambda _: {"Jupiter": corrupt})
    with pytest.raises(ValueError, match="hash"):
        PlanetaryMoons.open(de441_path=base, manifest_path=path)


def test_extracts_preserve_source_coverage_and_state(authority):
    spice, _, manifest = authority
    directory = _data_path("MOIRA_TEST_PLANETARY_MOONS_JPL")
    records = json.loads(manifest.read_text(encoding="utf-8"))["systems"]
    for system in SYSTEMS:
        record = records[system.name]
        raw, extract = directory / system.source, manifest.parent / record["filename"]
        for body in (system.center, *(m.naif_id for m in system.moons)):
            assert list(spice.spkcov(str(extract), body)) == list(spice.spkcov(str(raw), body))
        # Compare both sides of each internal descriptor seam with the
        # original source, preserving CSPICE's latest-segment precedence.
        probes = {
            (row["target"], epoch)
            for row in record["segments"]
            for start, stop in ((row["start_tdb_s"], row["end_tdb_s"]),)
            for epoch in (start, start + 1, (start + stop) / 2.0, stop - 1, stop)
        }
        extracted = {
            (body, epoch): tuple(spice.spkgeo(body, epoch, "J2000", system.barycenter)[0])
            for body, epoch in probes
        }
        spice.furnsh(str(raw))
        try:
            for (body, epoch), state in extracted.items():
                assert state == tuple(spice.spkgeo(body, epoch, "J2000", system.barycenter)[0])
        finally:
            spice.unload(str(raw))
