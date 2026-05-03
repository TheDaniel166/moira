#!/usr/bin/env python3
"""
Moira Export Governance Audit CLI.

Interactive tool for auditing __all__ declarations module-by-module.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from moira._export_governance.scanner import ModuleScanner
from moira._export_governance.parser import ModuleParser
from moira._export_governance.policy import ExportPolicyEngine
from moira._export_governance.audit_log import AuditLog
from moira._export_governance.models import AuditStatus, AuditDecision


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Audit __all__ declarations in Moira package"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        help="Glob pattern to filter modules"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last audited module"
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Show progress summary and exit"
    )
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).parent
    moira_root = script_dir.parent / "moira"
    log_path = script_dir.parent / ".kiro" / "specs" / "moira-export-governance" / "audit-log.json"
    
    if not moira_root.exists():
        print(f"Error: Moira package not found at {moira_root}", file=sys.stderr)
        return 1
    
    # Initialize components
    scanner = ModuleScanner(moira_root)
    parser_engine = ModuleParser()
    policy_engine = ExportPolicyEngine()
    policy_engine.load_policy()
    audit_log = AuditLog(log_path)
    
    # Show progress if requested
    if args.show_progress:
        summary = audit_log.get_progress_summary()
        print("=" * 60)
        print("AUDIT PROGRESS")
        print("=" * 60)
        print(f"Total modules: {summary['total_modules']}")
        print(f"Audited: {summary['audited']}")
        print(f"Pending: {summary['pending']}")
        print(f"Exempted: {summary['exempted']}")
        print(f"Coverage: {summary['coverage_percentage']}%")
        print("=" * 60)
        return 0
    
    # Scan for modules
    modules = scanner.scan_package(pattern=args.pattern, recursive=True)
    
    print(f"Found {len(modules)} modules to audit")
    print(f"Audit log: {log_path}")
    print()
    
    # Initialize pending modules in log
    for module in modules:
        if audit_log.get_status(str(module)) is None:
            audit_log.add_entry(
                module_path=str(module),
                status=AuditStatus.PENDING,
                auditor="system",
                decision=AuditDecision.APPROVED,
                rationale="Initialized"
            )
    
    # Show summary
    summary = audit_log.get_progress_summary()
    print(f"Audit Status:")
    print(f"  Audited: {summary['audited']}/{summary['total_modules']} ({summary['coverage_percentage']}%)")
    print(f"  Pending: {summary['pending']}")
    print()
    
    # Get next module to audit
    if args.resume:
        last_module = audit_log.resume_from_last()
        if last_module:
            print(f"Last audited: {last_module}")
    
    next_module = audit_log.get_next_pending()
    if next_module:
        print(f"Next to audit: {next_module}")
        print()
        print("Run with interactive mode to begin auditing (not yet implemented)")
        print("For now, use the validation tool: python scripts/moira-validate-exports.py")
    else:
        print("All modules have been audited!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
