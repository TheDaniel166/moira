import sys
import json
from pathlib import Path

# Add the root to sys.path so we can import the test checker logic
sys.path.append(str(Path.cwd()))

from tests.unit.test_docstring_governance import (
    MOIRA_ROOT, 
    check_module_docstrings, 
    check_class_docstrings, 
    check_machine_contracts
)

def run_full_audit():
    all_violations = []
    
    # Collect all files
    py_files = sorted(MOIRA_ROOT.rglob("*.py"))
    
    for path in py_files:
        # Module checks
        all_violations.extend(check_module_docstrings(path))
        # Class checks
        all_violations.extend(check_class_docstrings(path))
        # Machine Contract checks
        all_violations.extend(check_machine_contracts(path))
        
    # Group by file/importance
    report = []
    for v in all_violations:
        report.append({
            "file": v.file,
            "entity": v.entity,
            "rule": v.rule,
            "detail": v.detail
        })
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_full_audit()
