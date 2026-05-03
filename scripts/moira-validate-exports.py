#!/usr/bin/env python3
"""
Moira Export Governance Validation CLI.

Validates __all__ declarations across the Moira package.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from moira._export_governance.validator import ValidationEngine
from moira._export_governance.reporter import AuditReporter
from moira._export_governance.models import Severity


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate __all__ declarations in Moira package"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (warnings become errors)"
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with error code if warnings found"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        help="Glob pattern to filter modules (e.g., 'houses*.py')"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path for report"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    # Determine package root (moira directory)
    script_dir = Path(__file__).parent
    moira_root = script_dir.parent / "moira"
    
    if not moira_root.exists():
        print(f"Error: Moira package not found at {moira_root}", file=sys.stderr)
        return 1
    
    # Create validator
    validator = ValidationEngine(moira_root)
    
    # Run validation
    print(f"Validating Moira package at {moira_root}...")
    if args.pattern:
        print(f"Pattern filter: {args.pattern}")
    if args.strict:
        print("Strict mode: enabled")
    
    result = validator.validate_package(
        pattern=args.pattern,
        strict_mode=args.strict
    )
    
    # Generate summary
    summary = validator.get_violation_summary(result)
    
    # Print results
    print(f"\n{'='*60}")
    print("VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"Total modules: {result.total_modules}")
    print(f"Valid modules: {result.valid_modules}")
    print(f"Invalid modules: {result.invalid_modules}")
    print(f"\nViolations:")
    print(f"  Errors: {summary['by_severity']['errors']}")
    print(f"  Warnings: {summary['by_severity']['warnings']}")
    print(f"  Info: {summary['by_severity']['info']}")
    print(f"  Total: {summary['by_severity']['total']}")
    
    if summary['by_rule']:
        print(f"\nViolations by rule:")
        for rule_id, count in sorted(summary['by_rule'].items()):
            print(f"  {rule_id}: {count}")
    
    # Show sample violations
    if result.total_violations > 0:
        print(f"\n{'='*60}")
        print("SAMPLE VIOLATIONS (first 10)")
        print(f"{'='*60}")
        
        violation_count = 0
        for module_result in result.module_results:
            if violation_count >= 10:
                break
            
            if module_result.violations:
                print(f"\n{module_result.module_path}:")
                for violation in module_result.violations[:3]:  # Max 3 per module
                    severity_icon = {
                        Severity.ERROR: "❌",
                        Severity.WARNING: "⚠️",
                        Severity.INFO: "ℹ️",
                    }.get(violation.severity, "•")
                    print(f"  {severity_icon} {violation.message}")
                    violation_count += 1
                    if violation_count >= 10:
                        break
    
    # Write output file if requested
    if args.output:
        if args.format == "json":
            # Convert to audit reports for JSON output
            from moira._export_governance.models import ModuleAuditReport
            from datetime import datetime
            
            audit_reports = []
            for module_result in result.module_results:
                # Create minimal audit report for JSON output
                audit_report = ModuleAuditReport(
                    module_path=str(module_result.module_path),
                    has_all_declaration=module_result.has_all_declaration,
                    current_all=[],
                    defined_symbols=[],
                    recommended_exports=[],
                    missing_exports=[],
                    policy_violations=module_result.violations,
                    module_category=validator.scanner.categorize_module(module_result.module_path),
                    audit_timestamp=datetime.now()
                )
                audit_reports.append(audit_report)
            
            reporter = AuditReporter()
            reporter.write_report(audit_reports, args.output, format="json")
            print(f"\nReport written to {args.output}")
        
        elif args.format == "markdown":
            # Write markdown summary
            lines = []
            lines.append("# Export Governance Validation Report\n")
            lines.append(f"**Total modules**: {result.total_modules}\n")
            lines.append(f"**Valid modules**: {result.valid_modules}\n")
            lines.append(f"**Invalid modules**: {result.invalid_modules}\n")
            lines.append(f"\n## Violations\n")
            lines.append(f"- **Errors**: {summary['by_severity']['errors']}\n")
            lines.append(f"- **Warnings**: {summary['by_severity']['warnings']}\n")
            lines.append(f"- **Total**: {summary['by_severity']['total']}\n")
            
            args.output.write_text("\n".join(lines))
            print(f"\nReport written to {args.output}")
    
    # Determine exit code
    has_errors = summary['by_severity']['errors'] > 0
    has_warnings = summary['by_severity']['warnings'] > 0
    
    if has_errors:
        print(f"\n{'='*60}")
        print("VALIDATION FAILED: Errors found")
        print(f"{'='*60}")
        return 1
    
    if args.fail_on_warning and has_warnings:
        print(f"\n{'='*60}")
        print("VALIDATION FAILED: Warnings found (--fail-on-warning)")
        print(f"{'='*60}")
        return 1
    
    print(f"\n{'='*60}")
    print("VALIDATION PASSED")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
