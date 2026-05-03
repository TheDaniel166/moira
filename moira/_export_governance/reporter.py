"""
Report generator for export governance audit results.

This module generates audit reports in multiple formats (JSON, Markdown, HTML)
and provides summary statistics across all modules.

Boundary: Owns report generation and formatting logic.
Dependencies: models module, json, datetime.
Public surface: AuditReporter class.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from moira._export_governance.models import (
    ModuleAuditReport,
    ModuleCategory,
    Severity,
)


class AuditReporter:
    """
    Generates audit reports in multiple formats.
    
    Produces module-level reports and summary statistics, with output
    in JSON, Markdown, and HTML formats.
    """

    def generate_module_report(
        self,
        report: ModuleAuditReport
    ) -> dict[str, Any]:
        """
        Generate a structured report for a single module.
        
        Args:
            report: Module audit report
            
        Returns:
            Dictionary containing report data
        """
        return {
            "module_path": str(report.module_path),
            "has_all_declaration": report.has_all_declaration,
            "current_all": report.current_all,
            "defined_symbols": [
                {
                    "name": s.name,
                    "type": s.symbol_type.value,
                    "is_public": s.is_public,
                    "lineno": s.lineno,
                    "is_imported": s.is_imported,
                }
                for s in report.defined_symbols
            ],
            "recommended_exports": report.recommended_exports,
            "missing_exports": report.missing_exports,
            "policy_violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity.value,
                    "message": v.message,
                    "symbol_name": v.symbol_name,
                    "lineno": v.lineno,
                }
                for v in report.policy_violations
            ],
            "module_category": report.module_category.value,
            "audit_timestamp": report.audit_timestamp.isoformat(),
        }

    def generate_summary_report(
        self,
        reports: list[ModuleAuditReport]
    ) -> dict[str, Any]:
        """
        Generate summary statistics across all modules.
        
        Args:
            reports: List of module audit reports
            
        Returns:
            Dictionary containing summary statistics
        """
        total_modules = len(reports)
        modules_with_all = sum(1 for r in reports if r.has_all_declaration)
        modules_without_all = total_modules - modules_with_all
        
        # Calculate coverage percentage
        coverage_percentage = (
            (modules_with_all / total_modules * 100) if total_modules > 0 else 0.0
        )
        
        # Count violations by severity
        error_count = sum(
            sum(1 for v in r.policy_violations if v.severity == Severity.ERROR)
            for r in reports
        )
        warning_count = sum(
            sum(1 for v in r.policy_violations if v.severity == Severity.WARNING)
            for r in reports
        )
        info_count = sum(
            sum(1 for v in r.policy_violations if v.severity == Severity.INFO)
            for r in reports
        )
        
        # Count by category
        category_counts = {}
        for category in ModuleCategory:
            count = sum(1 for r in reports if r.module_category == category)
            if count > 0:
                category_counts[category.value] = count
        
        return {
            "total_modules": total_modules,
            "modules_with_all": modules_with_all,
            "modules_without_all": modules_without_all,
            "coverage_percentage": round(coverage_percentage, 2),
            "violations": {
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
                "total": error_count + warning_count + info_count,
            },
            "by_category": category_counts,
            "generated_at": datetime.now().isoformat(),
        }

    def format_json(
        self,
        reports: list[ModuleAuditReport],
        include_summary: bool = True
    ) -> str:
        """
        Format reports as JSON.
        
        Args:
            reports: List of module audit reports
            include_summary: Whether to include summary statistics
            
        Returns:
            JSON string
        """
        output: dict[str, Any] = {
            "modules": [self.generate_module_report(r) for r in reports]
        }
        
        if include_summary:
            output["summary"] = self.generate_summary_report(reports)
        
        return json.dumps(output, indent=2)

    def format_markdown(
        self,
        reports: list[ModuleAuditReport],
        include_summary: bool = True
    ) -> str:
        """
        Format reports as Markdown.
        
        Args:
            reports: List of module audit reports
            include_summary: Whether to include summary statistics
            
        Returns:
            Markdown string
        """
        lines: list[str] = []
        
        lines.append("# Export Governance Audit Report")
        lines.append("")
        
        if include_summary:
            summary = self.generate_summary_report(reports)
            lines.append("## Summary")
            lines.append("")
            lines.append(f"- **Total Modules**: {summary['total_modules']}")
            lines.append(f"- **Modules with `__all__`**: {summary['modules_with_all']}")
            lines.append(f"- **Modules without `__all__`**: {summary['modules_without_all']}")
            lines.append(f"- **Coverage**: {summary['coverage_percentage']}%")
            lines.append("")
            lines.append("### Violations")
            lines.append(f"- **Errors**: {summary['violations']['errors']}")
            lines.append(f"- **Warnings**: {summary['violations']['warnings']}")
            lines.append(f"- **Info**: {summary['violations']['info']}")
            lines.append("")
        
        lines.append("## Module Reports")
        lines.append("")
        
        for report in reports:
            lines.append(f"### {report.module_path}")
            lines.append("")
            lines.append(f"- **Category**: {report.module_category.value}")
            lines.append(f"- **Has `__all__`**: {'Yes' if report.has_all_declaration else 'No'}")
            
            if report.current_all:
                lines.append(f"- **Current exports**: {', '.join(report.current_all)}")
            
            if report.missing_exports:
                lines.append(f"- **Missing exports**: {', '.join(report.missing_exports)}")
            
            if report.policy_violations:
                lines.append("")
                lines.append("**Violations:**")
                for violation in report.policy_violations:
                    severity_icon = {
                        Severity.ERROR: "❌",
                        Severity.WARNING: "⚠️",
                        Severity.INFO: "ℹ️",
                    }.get(violation.severity, "•")
                    lines.append(f"- {severity_icon} {violation.message}")
            
            lines.append("")
        
        return "\n".join(lines)

    def format_html(
        self,
        reports: list[ModuleAuditReport],
        include_summary: bool = True
    ) -> str:
        """
        Format reports as HTML.
        
        Args:
            reports: List of module audit reports
            include_summary: Whether to include summary statistics
            
        Returns:
            HTML string
        """
        lines: list[str] = []
        
        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append("<title>Export Governance Audit Report</title>")
        lines.append("<style>")
        lines.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        lines.append("h1 { color: #333; }")
        lines.append("h2 { color: #666; margin-top: 30px; }")
        lines.append("h3 { color: #888; margin-top: 20px; }")
        lines.append(".summary { background: #f5f5f5; padding: 15px; border-radius: 5px; }")
        lines.append(".module { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }")
        lines.append(".error { color: #d32f2f; }")
        lines.append(".warning { color: #f57c00; }")
        lines.append(".info { color: #1976d2; }")
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")
        
        lines.append("<h1>Export Governance Audit Report</h1>")
        
        if include_summary:
            summary = self.generate_summary_report(reports)
            lines.append("<div class='summary'>")
            lines.append("<h2>Summary</h2>")
            lines.append(f"<p><strong>Total Modules:</strong> {summary['total_modules']}</p>")
            lines.append(f"<p><strong>Modules with __all__:</strong> {summary['modules_with_all']}</p>")
            lines.append(f"<p><strong>Coverage:</strong> {summary['coverage_percentage']}%</p>")
            lines.append("<h3>Violations</h3>")
            lines.append(f"<p class='error'><strong>Errors:</strong> {summary['violations']['errors']}</p>")
            lines.append(f"<p class='warning'><strong>Warnings:</strong> {summary['violations']['warnings']}</p>")
            lines.append(f"<p class='info'><strong>Info:</strong> {summary['violations']['info']}</p>")
            lines.append("</div>")
        
        lines.append("<h2>Module Reports</h2>")
        
        for report in reports:
            lines.append("<div class='module'>")
            lines.append(f"<h3>{report.module_path}</h3>")
            lines.append(f"<p><strong>Category:</strong> {report.module_category.value}</p>")
            lines.append(f"<p><strong>Has __all__:</strong> {'Yes' if report.has_all_declaration else 'No'}</p>")
            
            if report.missing_exports:
                lines.append(f"<p><strong>Missing exports:</strong> {', '.join(report.missing_exports)}</p>")
            
            if report.policy_violations:
                lines.append("<h4>Violations:</h4>")
                lines.append("<ul>")
                for violation in report.policy_violations:
                    css_class = violation.severity.value
                    lines.append(f"<li class='{css_class}'>{violation.message}</li>")
                lines.append("</ul>")
            
            lines.append("</div>")
        
        lines.append("</body>")
        lines.append("</html>")
        
        return "\n".join(lines)

    def write_report(
        self,
        reports: list[ModuleAuditReport],
        output_path: Path,
        format: str = "json"
    ) -> None:
        """
        Write report to file in specified format.
        
        Args:
            reports: List of module audit reports
            output_path: Path to output file
            format: Output format ("json", "markdown", "html")
            
        Side effects:
            Writes file to filesystem
        """
        if format == "json":
            content = self.format_json(reports)
        elif format == "markdown":
            content = self.format_markdown(reports)
        elif format == "html":
            content = self.format_html(reports)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        output_path.write_text(content, encoding="utf-8")


__all__ = ["AuditReporter"]
