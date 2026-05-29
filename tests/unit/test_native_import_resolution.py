from pathlib import Path

import pytest

from moira import moira_native


def test_public_native_module_is_python_shim_over_private_backend() -> None:
    module_path = Path(moira_native.__file__)
    backend_path = Path(moira_native.__backend_file__)

    assert module_path.name == "moira_native.py"
    assert backend_path.name.startswith("_moira_native")
    assert hasattr(moira_native, "spk_chebyshev_record")


def test_legacy_native_evaluator_helpers_accept_plain_python_sequences() -> None:
    assert moira_native.horner([1.0, 2.0, 3.0], 2.0) == 17.0

    lagrange_value = moira_native.lagrange_interpolate([0.0, 1.0, 2.0], [0.0, 1.0, 4.0], 1.5)
    assert abs(lagrange_value - 2.25) < 1e-12

    coeff_record = [
        [1.0, 2.0, 3.0],
        [0.0, 1.0, 0.0],
    ]
    record_value = moira_native.spk_chebyshev_record(coeff_record, 0.25)
    assert isinstance(record_value, list)
    assert len(record_value) == 2

    type13_value = moira_native.spk_type13_record(
        [2451545.0, 2451546.0, 2451547.0, 2451548.0],
        [
            [0.0, 1.0, 4.0, 9.0],
            [0.0, 1.0, 4.0, 9.0],
            [0.0, 1.0, 4.0, 9.0],
            [0.0, 2.0 / 86400.0, 4.0 / 86400.0, 6.0 / 86400.0],
            [0.0, 2.0 / 86400.0, 4.0 / 86400.0, 6.0 / 86400.0],
            [0.0, 2.0 / 86400.0, 4.0 / 86400.0, 6.0 / 86400.0],
        ],
        4,
        2451546.5,
    )
    assert type13_value[:3] == [pytest.approx(2.25)] * 3
    assert type13_value[3:] == [pytest.approx(3.0)] * 3
