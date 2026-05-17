"""
Moira — Audit Result Presentation
=================================

Archetype: Governance Logic (Logic Actor)

Purpose
-------
Governs the presentation and persistence of export governance audit 
results. Translates raw analysis reports into structured summaries 
and formatted documents (JSON, Markdown, HTML) to provide visibility 
into the engine's sovereign boundary status.

Boundary
--------
Owns:
    - Report formatting logic for all supported formats.
    - Summary statistic calculation across audit populations.
    - Report persistence (writing to filesystem).
Delegates:
    - Audit result models to moira._export_governance.models.

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- Filesystem write access to the output path.
- UTF-8 encoding support.

Public surface
--------------
AuditReporter class.
"""

from __future__ import annotations

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
    RITE: The Voice of Governance

    THEOREM: AuditReporter governs the transformation of audit data 
        into human-legible and machine-parseable artifacts for 
        sovereign verification.

    RITE OF PURPOSE:
        This engine exists to provide transparent visibility into the 
        state of the engine's export alignment. It serves as the 
        canonical source of truth for governance coverage metrics, 
        violation summaries, and historical audit artifacts.

    LAW OF OPERATION:
        Responsibilities:
            - Generate summary statistics for audit populations.
            - Format module-level reports into multiple dialects.
            - Persist reports to the filesystem safely.
        Non-responsibilities:
            - Does not perform audits (delegates to the Auditor).
            - Does not analyze facades (delegates to the Analyzer).
        
    Canon: Moira Export Governance Protocol v1.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._export_governance.reporter.AuditReporter",
      "risk": "low",
      "api": {
        "frozen": ["generate_summary_report", "format_markdown", "write_report"]
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": ["filesystem write"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["formatting_change"]}
    }
    [/MACHINE_CONTRACT]
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
