from pathlib import Path

from moira import moira_native


def test_public_native_module_is_python_shim_over_private_backend() -> None:
    module_path = Path(moira_native.__file__)
    backend_path = Path(moira_native.__backend_file__)

    assert module_path.name == "moira_native.py"
    assert backend_path.name.startswith("_moira_native")
    assert hasattr(moira_native, "spk_chebyshev_record")
