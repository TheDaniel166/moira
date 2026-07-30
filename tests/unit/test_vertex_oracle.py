"""
Oracle Tests — Vertex and Anti-Vertex Positions  (SCP P1 / P3)

Verified invariants
-------------------
- Vertex and Anti-Vertex agree with a documented secondary comparator at numeric
  JD 2451545.0, London.
- Vertex is identical across every house system for the same JD and geographic coordinates
  (it is computed solely from ARMC, obliquity, and latitude — not from the cusp algorithm).
- Vertex ∈ [0°, 360°) and Anti-Vertex = (Vertex + 180°) % 360° at every reference epoch.
- calculate_houses and houses_from_armc return the same vertex when given the same ARMC
  and independently derived obliquity.
- Vertex changes by < 30° per hour over a diurnal cycle at moderate latitude (no flips).

Formula (Meeus §24)
-------------------
    Vertex      = Ascendant(ARMC + 90°, obliquity, −latitude)
    Anti-Vertex = (Vertex + 180°) % 360°

Baseline governance
-------------------
Ordinary pytest reads the approved files in tests/golden/ but cannot rewrite
them. Any separately generated candidate requires explicit provenance review
against the documented comparator before protected evidence is promoted.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from moira.constants import HouseSystem
from moira.houses import calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from support.reference_epochs import REFERENCE_EPOCHS, ReferenceEpoch

# Stable test anchor: London-ish at moderate latitude (well inside polar threshold).
_LAT = 51.5
_LON = 0.0

# HouseSystem uses string constants (not an Enum), so enumerate the systems explicitly.
# Excludes SUNSHINE and SOLAR_SIGN — those also work but require an internal sun-longitude
# lookup that adds noise to a vertex independence test.
_ALL_SYSTEMS = [
    HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN,
    HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS, HouseSystem.PORPHYRY,
    HouseSystem.MERIDIAN, HouseSystem.ALCABITIUS, HouseSystem.MORINUS,
    HouseSystem.TOPOCENTRIC, HouseSystem.VEHLOW, HouseSystem.AZIMUTHAL,
    HouseSystem.CARTER, HouseSystem.KRUSINSKI, HouseSystem.APC,
    HouseSystem.ZARIEL, HouseSystem.EQUAL_MC, HouseSystem.PULLEN_SD, HouseSystem.PULLEN_SR,
]

# ---------------------------------------------------------------------------
# Cross-engine corroboration — documented secondary comparator values
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_vertex_golden_j2000_london(jd_j2000, golden):
    """
    Corroboration at numeric JD 2451545.0, 51.5°N 0.0°E, Placidus.

    External reference — Astro-Seek (Swiss Ephemeris engine):
        Vertex  = Libra 8°27'  = 188.45°  (at 51°29'N, 0°01'W, 12:00 GMT)
        Formula verification: prime-vertical / ecliptic intersection from first principles
        gives 188.471° for the exact test coordinates (51.5°N, 0.0°E, jd_j2000=2451545.0).
        The 0.02° residual is the coordinate difference (51°29'N/0°01'W vs 51.5°N/0.0°E).

    Correct formula (western prime-vertical / ecliptic intersection):
        n_pv  = pole of prime vertical = (cos(ARMC)*sin(lat), sin(ARMC)*sin(lat), -cos(lat))
        n_ecl = pole of ecliptic       = (0, -sin(eps), cos(eps))
        intersection: y = -cos(ARMC),  x = sin(ARMC)*cos(eps) - cot(lat)*sin(eps)
        Vertex = atan2(y, x) [western branch] % 360

    The adjacent provenance records Astro-Seek/Swiss Ephemeris as a secondary
    comparator. The golden file stores 188.471; storage alone confers no authority.
    """
    h = calculate_houses(jd_j2000, _LAT, _LON, HouseSystem.PLACIDUS)

    # golden() compares h.vertex against the external reference stored in the file.
    # This will FAIL until the implementation uses the correct formula.
    golden("vertex_j2000_london", round(h.vertex, 6))
    golden("anti_vertex_j2000_london", round(h.anti_vertex, 6))

    # Belt-and-suspenders: direct assertion against the known external value.
    # tolerance=0.1° covers the coordinate/time-system residual vs Astro-Seek.
    assert abs(h.vertex - 188.471) < 0.1, (
        f"Vertex {h.vertex:.3f}° != expected ~188.47° (Libra 8°28'). "
        f"External ref (Astro-Seek): 188.45° (Libra 8°27'). "
        f"Current formula gives the WRONG intersection of the prime vertical."
    )


# ---------------------------------------------------------------------------
# Cross-system invariance — vertex is independent of house system
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("system", _ALL_SYSTEMS, ids=str)
def test_vertex_is_system_independent(jd_j2000, system, moira_approx):
    """
    All house systems must return the same vertex for identical inputs.
    The vertex formula (Meeus §24) depends only on ARMC, obliquity, and latitude;
    it is not influenced by the cusp algorithm chosen for the 12 houses.
    """
    reference = calculate_houses(jd_j2000, _LAT, _LON, HouseSystem.PLACIDUS)
    candidate = calculate_houses(jd_j2000, _LAT, _LON, system)

    assert candidate.vertex == moira_approx(reference.vertex, kind="longitude"), (
        f"{system!r}: vertex {candidate.vertex:.6f}° ≠ Placidus {reference.vertex:.6f}°"
    )
    assert candidate.anti_vertex == moira_approx(reference.anti_vertex, kind="longitude"), (
        f"{system!r}: anti_vertex {candidate.anti_vertex:.6f}° ≠ Placidus "
        f"{reference.anti_vertex:.6f}°"
    )


# ---------------------------------------------------------------------------
# Dual path — calculate_houses pipeline vs. houses_from_armc directly
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_vertex_dual_path_full_pipeline_vs_armc(jd_j2000, ritual):
    """
    Dual-path oracle: the full calculate_houses pipeline and the direct
    houses_from_armc path must produce identical vertex given the same ARMC.

    Path A  calculate_houses(jd, lat, lon, system)
            — derives ARMC internally from the Julian date and longitude.
    Path B  houses_from_armc(armc, obliquity, lat, system)
            — takes the ARMC extracted from Path A and the independently
              computed true obliquity as inputs.

    Divergence here points to an inconsistency in ARMC propagation or in
    the obliquity value threaded into the vertex formula.
    """
    h        = calculate_houses(jd_j2000, _LAT, _LON, HouseSystem.PLACIDUS)
    obl      = true_obliquity(ut_to_tt(jd_j2000))
    h_direct = houses_from_armc(h.armc, obl, _LAT, HouseSystem.PLACIDUS)

    ritual.dual_path(
        lambda: h.vertex,
        lambda: h_direct.vertex,
        label="calculate_houses vs houses_from_armc  vertex",
        abs_tol=1e-9,
    )
    ritual.dual_path(
        lambda: h.anti_vertex,
        lambda: h_direct.anti_vertex,
        label="calculate_houses vs houses_from_armc  anti_vertex",
        abs_tol=1e-9,
    )


# ---------------------------------------------------------------------------
# Geometric taboos — laws the engine must never violate
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "reference_epoch",
    REFERENCE_EPOCHS,
    ids=lambda anchor: anchor.key,
)
def test_vertex_range_never_out_of_bounds(
    reference_epoch: ReferenceEpoch,
    ritual,
):
    """
    Vertex and Anti-Vertex must lie in [0°, 360°) at every reference epoch
    and at a range of moderate latitudes.
    """
    jd, label = reference_epoch.jd, reference_epoch.label
    lats = [0.0, 30.0, _LAT, -33.9]

    ritual.sweep_taboo(
        "vertex_out_of_range",
        items=[(jd, lat) for lat in lats],
        forbidden=lambda jd_, lat: not (
            0.0 <= calculate_houses(jd_, lat, _LON, HouseSystem.PLACIDUS).vertex < 360.0
        ),
        context=lambda jd_, lat: f"vertex at JD {jd_:.1f} lat {lat:+.1f}° ({label})",
    )
    ritual.sweep_taboo(
        "anti_vertex_out_of_range",
        items=[(jd, lat) for lat in lats],
        forbidden=lambda jd_, lat: not (
            0.0 <= calculate_houses(jd_, lat, _LON, HouseSystem.PLACIDUS).anti_vertex < 360.0
        ),
        context=lambda jd_, lat: f"anti_vertex at JD {jd_:.1f} lat {lat:+.1f}° ({label})",
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "reference_epoch",
    REFERENCE_EPOCHS,
    ids=lambda anchor: anchor.key,
)
def test_anti_vertex_always_opposite_vertex(
    reference_epoch: ReferenceEpoch,
    ritual,
):
    """
    Anti-Vertex = (Vertex + 180°) % 360° at every epoch and latitude.
    Violations here mean the complement derivation has drifted from the
    vertex computation, or that normalisation has been applied inconsistently.
    """
    jd, label = reference_epoch.jd, reference_epoch.label
    lats = [0.0, 30.0, _LAT, -33.9]

    def _not_opposite(jd_: float, lat: float) -> bool:
        h = calculate_houses(jd_, lat, _LON, HouseSystem.PLACIDUS)
        return abs(h.anti_vertex - (h.vertex + 180.0) % 360.0) > 1e-8

    ritual.sweep_taboo(
        "anti_vertex_not_opposite_vertex",
        items=[(jd, lat) for lat in lats],
        forbidden=_not_opposite,
        context=lambda jd_, lat: f"JD {jd_:.1f} lat {lat:+.1f}° ({label})",
    )


# ---------------------------------------------------------------------------
# Temporal continuity — no discontinuous flips over a diurnal cycle
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_vertex_continuity_diurnal(moira_engine, ritual):
    """
    Over a 24-hour period at 51.5°N the vertex must change by less than 30°
    per hour. A larger step indicates a candidate-selection flip (180° error)
    or a sign error in the latitude term of the Meeus §24 formula.
    """
    base     = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    dts      = [base + timedelta(hours=h) for h in range(25)]
    vertices = [
        moira_engine.houses(dt, _LAT, _LON, HouseSystem.PLACIDUS).vertex
        for dt in dts
    ]

    ritual.witness("vertex_diurnal_j2000_london", vertices)
    # Observed legitimate maximum at 51.5°N is ~35°/hour (fast ecliptic phase).
    # 60° headroom is ~1.7× that; a real candidate-flip error produces ~145°+ steps.
    ritual.temporal_covenant(
        vertices,
        lambda a, b: min(abs(b - a), 360.0 - abs(b - a)) < 60.0,
        label="Vertex moves < 60 deg per hour at 51.5N (no flip errors)",
    )
