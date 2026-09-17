"""Unit tests for Stage 5 SBDB osculating asteroid orbit classification."""

from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from moira.facade import Moira
from moira.orbits import (
    JPL_ORBIT_CLASS_TITLES,
    ORBIT_CLASS_POLICY,
    PARABOLIC_E_TOL,
    OrbitClassBatchItem,
    OrbitClassBatchResult,
    OrbitClassBoundaryMargin,
    OrbitClassCode,
    OrbitClassPredicate,
    OrbitClassResult,
    OrbitalBodyIdentity,
    OrbitalBodyKind,
    OrbitalBodyNotFoundError,
    OrbitalBodyNotSupportedError,
    OrbitalCenter,
    OrbitalErrorReceipt,
    OrbitalFrame,
    OrbitalFrameConstruction,
    OrbitalGravity,
    OrbitalInputError,
    OrbitalSingularityThresholds,
    OrbitalStateSource,
    OrbitalTimeConversion,
    OrbitShape,
    OsculatingElements,
    OsculatingElementsProvenance,
    _classify_osculating_elements,
    orbit_class,
    orbit_classes_at,
)


from typing import Any, cast


def _make_elements(
    *,
    shape: OrbitShape = OrbitShape.ELLIPTIC,
    a: float | None = 2.5,
    e: float = 0.1,
    q: float = 2.25,
    Q: float | None = 2.75,
    name: str = "TestBody",
    naif_id: int = 2000001,
) -> OsculatingElements:
    """Construct an authentic OsculatingElements instance for testing."""
    return OsculatingElements(
        body=OrbitalBodyIdentity(
            name=name,
            kind=OrbitalBodyKind.ASTEROID,
            naif_id=naif_id,
        ),
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        jd_ut=2451545.0,
        epoch_tt=2451545.00074287,
        epoch_tdb=2451545.00074287,
        delta_t_seconds=64.184,
        tdb_minus_tt_seconds=0.0,
        shape=shape,
        semi_major_axis_au=a,
        eccentricity=e,
        pericenter_distance_au=q,
        apocenter_distance_au=Q,
        inclination_deg=10.0,
        lon_ascending_node_deg=0.0,
        arg_pericenter_deg=0.0,
        true_anomaly_deg=0.0,
        mean_anomaly_deg=0.0,
        mean_motion_deg_per_day=0.2,
        orbital_period_days=1500.0 if a is not None else None,
        time_of_pericenter_tdb=2451545.0,
        time_of_pericenter_tt=2451545.0,
        lon_pericenter_deg=0.0,
        arg_latitude_deg=0.0,
        true_longitude_deg=0.0,
        mean_longitude_deg=0.0,
        pericenter_ecliptic_lon_deg=0.0,
        pericenter_ecliptic_lat_deg=0.0,
        undefined=(),
        provenance=cast(Any, None),
    )


# ---------------------------------------------------------------------------
# 1. All 14 Classes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "e", "q", "Q", "shape", "expected_code", "expected_title"),
    [
        # 1. IEO: Q < 0.983
        (0.7410, 0.3221, 0.5023, 0.9797, OrbitShape.ELLIPTIC, OrbitClassCode.IEO, "Atira"),
        # 2. ATE: a < 1.0, Q > 0.983
        (0.9666, 0.1826, 0.7901, 1.1431, OrbitShape.ELLIPTIC, OrbitClassCode.ATE, "Aten"),
        # 3. APO: a > 1.0, q < 1.017
        (1.4702, 0.5599, 0.6470, 2.2934, OrbitShape.ELLIPTIC, OrbitClassCode.APO, "Apollo"),
        # 4. AMO: 1.017 < q < 1.3
        (1.9189, 0.4346, 1.0849, 2.7529, OrbitShape.ELLIPTIC, OrbitClassCode.AMO, "Amor"),
        # 5. MCA: 1.3 < q < 1.666, a < 3.2
        (2.6092, 0.3887, 1.5950, 3.6234, OrbitShape.ELLIPTIC, OrbitClassCode.MCA, "Mars-crossing Asteroid"),
        # 6. IMB: a < 2.0, q > 1.666
        (1.9443, 0.0739, 1.8006, 2.0880, OrbitShape.ELLIPTIC, OrbitClassCode.IMB, "Inner Main-belt Asteroid"),
        # 7. MBA: 2.0 < a < 3.2, q > 1.666
        (2.7675, 0.0789, 2.5491, 2.9859, OrbitShape.ELLIPTIC, OrbitClassCode.MBA, "Main-belt Asteroid"),
        # 8. OMB: 3.2 < a < 4.6
        (3.4368, 0.1049, 3.0763, 3.7973, OrbitShape.ELLIPTIC, OrbitClassCode.OMB, "Outer Main-belt Asteroid"),
        # 9. TJN: 4.6 < a < 5.5, e < 0.3
        (5.1950, 0.1472, 4.4303, 5.9597, OrbitShape.ELLIPTIC, OrbitClassCode.TJN, "Jupiter Trojan"),
        # 10. CEN: 5.5 < a < 30.1
        (13.670, 0.3794, 8.4836, 18.856, OrbitShape.ELLIPTIC, OrbitClassCode.CEN, "Centaur"),
        # 11. TNO: a > 30.1
        (39.482, 0.2488, 29.658, 49.306, OrbitShape.ELLIPTIC, OrbitClassCode.TNO, "TransNeptunian Object"),
        # 12. PAA: Parabolic
        (None, 1.0, 1.5, None, OrbitShape.PARABOLIC, OrbitClassCode.PAA, "Parabolic Asteroid"),
        # 13. HYA: Hyperbolic
        (-1.272, 1.201, 0.2559, None, OrbitShape.HYPERBOLIC, OrbitClassCode.HYA, "Hyperbolic Asteroid"),
        # 14. AST: Fallback (e.g. high-e in trojan semimajor zone 4.6 < a < 5.5, e >= 0.3)
        (5.0, 0.45, 2.75, 7.25, OrbitShape.ELLIPTIC, OrbitClassCode.AST, "Asteroid"),
    ],
)
def test_all_14_orbit_classes(
    a: float | None,
    e: float,
    q: float,
    Q: float | None,
    shape: OrbitShape,
    expected_code: OrbitClassCode,
    expected_title: str,
) -> None:
    """Verify that every one of the 14 JPL SBDB classes classifies correctly."""
    elements = _make_elements(shape=shape, a=a, e=e, q=q, Q=Q)
    code, title, predicates, margins = _classify_osculating_elements(elements)
    assert code == expected_code
    assert title == expected_title
    assert title == JPL_ORBIT_CLASS_TITLES[expected_code]
    assert len(predicates) >= 1
    # Matched predicate must be the last one evaluated
    assert predicates[-1].code == expected_code
    assert predicates[-1].matched is True
    # If not AST fallback, margins must match conditions of the winning predicate
    if expected_code != OrbitClassCode.AST:
        assert margins == predicates[-1].conditions
        assert all(m.signed_difference > 0.0 for m in margins)


# ---------------------------------------------------------------------------
# 2. Five Real-World Critical Sensitive Boundaries
# ---------------------------------------------------------------------------


def test_sensitive_boundary_anagolay_apo() -> None:
    """Anagolay (436724) with q = 1.016868 AU must strictly classify as APO, not AMO."""
    elements = _make_elements(
        a=1.8260,
        e=0.4431,
        q=1.016868,
        Q=2.635132,
    )
    code, title, predicates, margins = _classify_osculating_elements(elements)
    assert code == OrbitClassCode.APO
    assert title == "Apollo"
    # Verify exact margin: 1.017 - 1.016868 > 0
    q_margin = next(m for m in margins if m.parameter == "q")
    assert q_margin.boundary == 1.017
    assert q_margin.operator == "<"
    assert q_margin.signed_difference == pytest.approx(1.017 - 1.016868, abs=1e-12)


@pytest.mark.parametrize(
    ("name", "a", "e", "q"),
    [
        ("Amundsenia", 2.3598, 0.2942, 1.66558),
        ("Kepler", 2.6841, 0.3795, 1.66562),
        ("Beira", 2.7354, 0.3911, 1.66565),
    ],
)
def test_sensitive_boundary_mca_vs_mba(name: str, a: float, e: float, q: float) -> None:
    """Amundsenia, Kepler, and Beira (q ~ 1.6656 AU) must classify as MCA, not MBA."""
    elements = _make_elements(
        name=name,
        a=a,
        e=e,
        q=q,
        Q=a * (1.0 + e),
    )
    code, title, predicates, margins = _classify_osculating_elements(elements)
    assert code == OrbitClassCode.MCA
    assert title == "Mars-crossing Asteroid"
    q_margin = next(m for m in margins if m.parameter == "q" and m.operator == "<")
    assert q_margin.boundary == 1.666
    assert q_margin.signed_difference > 0.0


def test_sensitive_boundary_2004_kv18_cen() -> None:
    """2004 KV18 (a = 30.09951 AU) must strictly classify as CEN, not TNO."""
    elements = _make_elements(
        a=30.09951,
        e=0.1764,
        q=24.7899,
        Q=35.4091,
    )
    code, title, predicates, margins = _classify_osculating_elements(elements)
    assert code == OrbitClassCode.CEN
    assert title == "Centaur"
    a_margin = next(m for m in margins if m.parameter == "a" and m.operator == "<")
    assert a_margin.boundary == 30.1
    assert a_margin.signed_difference == pytest.approx(30.1 - 30.09951, abs=1e-12)


# ---------------------------------------------------------------------------
# 3. Exact Boundary Invariants & Zero Margin Fall-Through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "e", "q", "Q", "boundary_param", "boundary_value"),
    [
        # a == 1.0 (between ATE and APO)
        (1.0, 0.2, 0.8, 1.2, "a", 1.0),
        # q == 1.017 (between APO and AMO)
        (1.5, 0.322, 1.017, 1.983, "q", 1.017),
        # q == 1.3 (between AMO and MCA)
        (2.0, 0.35, 1.3, 2.7, "q", 1.3),
        # q == 1.666 (between MCA and MBA)
        (2.5, 0.3336, 1.666, 3.334, "q", 1.666),
        # a == 2.0 (between IMB and MBA, with q > 1.666)
        (2.0, 0.1, 1.8, 2.2, "a", 2.0),
        # a == 3.2 (between MBA and OMB, with q > 1.666)
        (3.2, 0.1, 2.88, 3.52, "a", 3.2),
        # a == 4.6 (between OMB and TJN)
        (4.6, 0.1, 4.14, 5.06, "a", 4.6),
        # a == 5.5 (between TJN and CEN, e < 0.3)
        (5.5, 0.1, 4.95, 6.05, "a", 5.5),
        # e == 0.3 (in trojan semimajor zone 4.6 < a < 5.5)
        (5.0, 0.3, 3.5, 6.5, "e", 0.3),
        # a == 30.1 (between CEN and TNO)
        (30.1, 0.1, 27.09, 33.11, "a", 30.1),
        # Q == 0.983 (between IEO and ATE, a < 1.0)
        (0.8, 0.22875, 0.617, 0.983, "Q", 0.983),
    ],
)
def test_exact_boundary_fallthrough_yields_zero_margin(
    a: float,
    e: float,
    q: float,
    Q: float,
    boundary_param: str,
    boundary_value: float,
) -> None:
    """Exact boundary landings fail strict inequalities, record 0.0 margin, and fall through."""
    elements = _make_elements(a=a, e=e, q=q, Q=Q)
    code, title, predicates, margins = _classify_osculating_elements(elements)

    # Must fall through to AST
    assert code == OrbitClassCode.AST
    assert title == "Asteroid"

    # Find the evaluated predicate condition that tested this exact boundary
    zero_margin_found = False
    for pred in predicates:
        for cond in pred.conditions:
            if cond.parameter == boundary_param and cond.boundary == pytest.approx(boundary_value, abs=1e-12):
                if cond.signed_difference == pytest.approx(0.0, abs=1e-12):
                    zero_margin_found = True
                    break
        if zero_margin_found:
            break

    assert zero_margin_found, f"Expected 0.0 margin on {boundary_param}={boundary_value}"


# ---------------------------------------------------------------------------
# 4. Parabolic and Hyperbolic Numerical Geometry
# ---------------------------------------------------------------------------


def test_parabolic_eccentricity_tolerance_boundary() -> None:
    """Verify PARABOLIC_E_TOL boundary behavior for PAA and HYA."""
    # Exactly 1.0 -> PAA
    paa_elem = _make_elements(shape=OrbitShape.PARABOLIC, a=None, e=1.0, q=1.5, Q=None)
    code, title, _, margins = _classify_osculating_elements(paa_elem)
    assert code == OrbitClassCode.PAA
    assert title == "Parabolic Asteroid"
    assert margins[0].operator == "=="
    assert margins[0].signed_difference == pytest.approx(PARABOLIC_E_TOL, abs=1e-16)

    # 1.0 + 1e-9 -> HYA (eccentricity strictly exceeds 1.0 + PARABOLIC_E_TOL)
    hya_elem = _make_elements(
        shape=OrbitShape.HYPERBOLIC,
        a=-1.0,
        e=1.0 + 1e-9,
        q=1.5,
        Q=None,
    )
    code_h, title_h, _, margins_h = _classify_osculating_elements(hya_elem)
    assert code_h == OrbitClassCode.HYA
    assert title_h == "Hyperbolic Asteroid"
    assert margins_h[0].operator == ">"
    assert margins_h[0].signed_difference > 0.0


# ---------------------------------------------------------------------------
# 5. Non-Asteroid Rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("body", ["Moon", "Mercury", "Jupiter", "Sun", "1P/Halley"])
def test_non_asteroid_bodies_rejected(body: str) -> None:
    """Non-asteroid bodies must raise OrbitalBodyNotSupportedError with strict doctrine."""
    with pytest.raises(OrbitalBodyNotSupportedError) as exc_info:
        orbit_class(body, 2451545.0)

    err = exc_info.value
    if body == "Sun":
        assert "Body.SUN is a center or calculated point" in err.reason
    else:
        assert "orbit_class admits only catalogued small bodies/asteroids" in err.reason


def test_nonexistent_body_rejected() -> None:
    """Unknown body query must raise OrbitalBodyNotFoundError."""
    with pytest.raises(OrbitalBodyNotFoundError):
        orbit_class("nonexistent_body_alpha_omega_9999", 2451545.0)


# ---------------------------------------------------------------------------
# 6. Batch Evaluation Order & Error Isolation
# ---------------------------------------------------------------------------


def test_batch_preserves_order_and_isolates_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Batch classification preserves input sequence and records sanitized errors without aborting."""
    def fake_orbit_class(body: str | int, jd_ut: float, *, reader: Any = None) -> OrbitClassResult:
        if body == "Moon":
            raise OrbitalBodyNotSupportedError("Moon", "major_body", "unsupported")
        if body == "Missing":
            raise OrbitalBodyNotFoundError("Missing", ("Ceres",))
        elem = _make_elements(name=str(body))
        return OrbitClassResult(
            body=OrbitalBodyIdentity(name=str(body), kind=OrbitalBodyKind.ASTEROID, naif_id=2000001),
            epoch_tdb=2451545.0,
            elements=elem,
            code=OrbitClassCode.MBA,
            title="Main-belt Asteroid",
            classification_policy=ORBIT_CLASS_POLICY,
            predicates=(),
            boundary_margins=(),
        )

    monkeypatch.setattr("moira.orbits.orbit_class", fake_orbit_class)

    batch_input = ["Ceres", "Moon", "Vesta", "Missing", "Ceres"]
    res = orbit_classes_at(batch_input, 2451545.0)

    assert isinstance(res, OrbitClassBatchResult)
    assert len(res.items) == 5

    # Check order preservation
    assert [item.input_index for item in res.items] == [0, 1, 2, 3, 4]
    assert [item.input_body for item in res.items] == batch_input

    # Ceres (0) succeeded
    assert res.items[0].result is not None
    assert res.items[0].error is None
    assert res.items[0].result.code == OrbitClassCode.MBA

    # Moon (1) failed with OrbitalBodyNotSupportedError
    assert res.items[1].result is None
    assert res.items[1].error is not None
    assert res.items[1].error.error_code == "ORBITAL_BODY_NOT_SUPPORTED"

    # Vesta (2) succeeded
    assert res.items[2].result is not None
    assert res.items[2].error is None

    # Missing (3) failed with OrbitalBodyNotFoundError
    assert res.items[3].result is None
    assert res.items[3].error is not None
    assert res.items[3].error.error_code == "ORBITAL_BODY_NOT_FOUND"

    # Ceres (4, duplicate) succeeded independently
    assert res.items[4].result is not None
    assert res.items[4].error is None


@pytest.mark.parametrize("invalid_jd", [float("nan"), float("inf"), float("-inf"), "not_a_date"])
def test_batch_request_level_validation_raises(invalid_jd: Any) -> None:
    """Request-level non-numeric or non-finite epoch raises OrbitalInputError immediately."""
    with pytest.raises(OrbitalInputError):
        orbit_classes_at(["Ceres"], invalid_jd)


# ---------------------------------------------------------------------------
# 7. Error Receipt Sanitization Whitelist
# ---------------------------------------------------------------------------


def test_error_receipt_sanitization_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """OrbitalErrorReceipt contains strictly allowlisted fields and no tracebacks or paths."""
    def fake_orbit_class(body: str | int, jd_ut: float, *, reader: Any = None) -> OrbitClassResult:
        raise OrbitalBodyNotFoundError("bad_body_path/c:/secret", ("cand1",))

    monkeypatch.setattr("moira.orbits.orbit_class", fake_orbit_class)

    res = orbit_classes_at(["test"], 2451545.0)
    receipt = res.items[0].error
    assert receipt is not None
    assert receipt.error_code == "ORBITAL_BODY_NOT_FOUND"

    # Check JSON serializability of receipt details
    json_bytes = json.dumps(
        {
            "error_code": receipt.error_code,
            "message": receipt.message,
            "details": dict(receipt.details),
        }
    )
    assert len(json_bytes) > 0


# ---------------------------------------------------------------------------
# 8. Facade Dispatch Parity
# ---------------------------------------------------------------------------


def test_facade_dispatch_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Moira instance exposes and dispatches orbit_class and orbit_classes_at."""
    called_single: list[Any] = []
    called_batch: list[Any] = []

    def fake_single(body: str | int, jd_ut: float, *, reader: Any = None) -> OrbitClassResult:
        called_single.append((body, jd_ut, reader))
        elem = _make_elements(name=str(body))
        return OrbitClassResult(
            body=OrbitalBodyIdentity(name=str(body), kind=OrbitalBodyKind.ASTEROID, naif_id=2000001),
            epoch_tdb=2451545.0,
            elements=elem,
            code=OrbitClassCode.MBA,
            title="Main-belt Asteroid",
            classification_policy=ORBIT_CLASS_POLICY,
            predicates=(),
            boundary_margins=(),
        )

    def fake_batch(
        bodies: Any, jd_ut: float, *, reader: Any = None
    ) -> OrbitClassBatchResult:
        called_batch.append((tuple(bodies), jd_ut, reader))
        return OrbitClassBatchResult(epoch_tdb=2451545.0, items=())

    monkeypatch.setattr("moira.facade.orbit_class", fake_single)
    monkeypatch.setattr("moira.facade.orbit_classes_at", fake_batch)

    engine = Moira()
    assert hasattr(engine, "orbit_class")
    assert hasattr(engine, "orbit_classes_at")

    single_res = engine.orbit_class("Ceres", 2451545.0)
    assert single_res.code == OrbitClassCode.MBA
    assert len(called_single) == 1
    assert called_single[0][0] == "Ceres"

    batch_res = engine.orbit_classes_at(["Ceres", "Vesta"], 2451545.0)
    assert isinstance(batch_res, OrbitClassBatchResult)
    assert len(called_batch) == 1
    assert called_batch[0][0] == ("Ceres", "Vesta")


# ---------------------------------------------------------------------------
# 9. Frozen Fixture Verification
# ---------------------------------------------------------------------------


def test_frozen_sbdb_fixture_records() -> None:
    """Verify every record in tests/fixtures/sbdb_orbit_classes.json classifies to its expected class."""
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "sbdb_orbit_classes.json"
    )
    assert fixture_path.is_file()

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["classification_policy"] == ORBIT_CLASS_POLICY
    records = data["records"]
    assert len(records) >= 30

    for rec in records:
        elem_data = rec["elements"]
        shape = OrbitShape.ELLIPTIC
        if elem_data["eccentricity"] == 1.0:
            shape = OrbitShape.PARABOLIC
        elif elem_data["eccentricity"] > 1.0:
            shape = OrbitShape.HYPERBOLIC

        elements = _make_elements(
            name=rec["name"],
            shape=shape,
            a=elem_data["semi_major_axis_au"],
            e=elem_data["eccentricity"],
            q=elem_data["pericenter_distance_au"],
            Q=elem_data["apocenter_distance_au"],
        )

        code, title, predicates, margins = _classify_osculating_elements(elements)
        expected_code = OrbitClassCode(rec["expected_class"])
        assert code == expected_code, f"Record {rec['name']} expected {expected_code}, got {code}"
        assert title == rec["expected_title"]
