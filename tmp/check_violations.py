from pathlib import Path
import sys
sys.path.insert(0, ".")
from tests.unit.test_docstring_governance import check_module_docstrings, check_class_docstrings, check_machine_contracts
for f in ["moira/cycles.py", "moira/bridges/harmograms.py", "moira/_spk_body_kernel.py", "moira/synastry.py", "moira/heliacal.py"]:
    p = Path(f)
    vs = check_module_docstrings(p) + check_class_docstrings(p) + check_machine_contracts(p)
    print(f"{f}: {len(vs)} violations")
    for v in vs:
        print(f"  [{v.rule}] {v.entity}: {v.detail}")
