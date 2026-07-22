import math

import pytest

from moira import moira_native


def _shadow_row(clearance_at_origin: float) -> tuple[float, ...]:
    # With a +Z unit cone axis, zero slope, and the site at the origin,
    # clearance is radius minus the plane point's XY distance.
    return (
        10.0 - clearance_at_origin,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        10.0,
        0.0,
    )


def test_penumbral_clearance_scanner_matches_python_lattice_semantics() -> None:
    epochs = (0.0, 1.0, 2.0, 3.0, 4.0)
    sampled_clearances = (0.0, 2.0, 1.0, 3.0, 0.0)
    scanner = moira_native.PenumbralClearanceScanner(
        epochs,
        tuple(_shadow_row(value) for value in sampled_clearances),
    )

    result = scanner.scan((0.0, 0.0, 0.0), 1.5, _shadow_row(4.0))

    assert scanner.size == len(epochs)
    assert result.sampled_maximum == pytest.approx(4.0, abs=1.0e-15)
    assert result.local_maximum_brackets == [
        pytest.approx((1.0, 1.5, 2.0), abs=0.0),
        pytest.approx((2.0, 3.0, 4.0), abs=0.0),
    ]


def test_penumbral_clearance_scanner_uses_lattice_state_for_existing_witness() -> None:
    epochs = (0.0, 1.0, 2.0)
    scanner = moira_native.PenumbralClearanceScanner(
        epochs,
        (_shadow_row(0.0), _shadow_row(5.0), _shadow_row(0.0)),
    )

    result = scanner.scan((0.0, 0.0, 0.0), 1.0, _shadow_row(-100.0))

    assert result.sampled_maximum == pytest.approx(5.0, abs=1.0e-15)
    assert result.local_maximum_brackets == [
        pytest.approx((0.0, 1.0, 2.0), abs=0.0)
    ]


@pytest.mark.parametrize(
    ("epochs", "rows", "message"),
    (
        ((0.0, 1.0), (_shadow_row(0.0), _shadow_row(0.0)), "at least three"),
        (
            (0.0, 1.0, 1.0),
            (_shadow_row(0.0),) * 3,
            "strictly increasing",
        ),
        (
            (0.0, 1.0, 2.0),
            (_shadow_row(0.0), _shadow_row(0.0), (0.0,) * 8),
            "unit length",
        ),
    ),
)
def test_penumbral_clearance_scanner_rejects_invalid_lattices(
    epochs: tuple[float, ...],
    rows: tuple[tuple[float, ...], ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        moira_native.PenumbralClearanceScanner(epochs, rows)


def test_penumbral_clearance_scanner_rejects_invalid_scan_inputs() -> None:
    epochs = (0.0, 1.0, 2.0)
    rows = (_shadow_row(0.0),) * 3
    scanner = moira_native.PenumbralClearanceScanner(epochs, rows)

    with pytest.raises(ValueError, match="inside the scanner interval"):
        scanner.scan((0.0, 0.0, 0.0), 3.0, _shadow_row(0.0))
    with pytest.raises(ValueError, match="site must be finite"):
        scanner.scan((math.nan, 0.0, 0.0), 1.0, _shadow_row(0.0))


def test_penumbral_envelope_candidates_reject_nonorthogonal_basis() -> None:
    clearance_row = (0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 10.0, 0.0)
    envelope_row = (
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        -384_000.0,
        10.0,
        0.0,
        1.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
    )

    with pytest.raises(ValueError, match="basis must be orthogonal"):
        moira_native.penumbral_envelope_candidates(
            envelope_row,
            clearance_row,
            clearance_row,
        )
