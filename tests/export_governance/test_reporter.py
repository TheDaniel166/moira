"""
Unit tests for audit report generator.

Tests module report generation, summary statistics, and output formats.
"""

from datetime import datetime
from pathlib import Path
import tempfile
import json

import pytest

from moira._export_governance.reporter import AuditReporter
from moira._export_governance.models import (
    ModuleAuditReport,
    SymbolInfo,
    SymbolType,
    ModuleCategory,
    PolicyViolation,
    Severity,
)


@pytest.fixture
def reporter():
    """Create an AuditReporter instance."""
    return AuditReporter()


@pytest.fixture
def sample_report():
    """Create a sample module audit report."""
    return ModuleAuditReport(
        module_path="moira/test_module.py",
        has_all_declaration=True,
        current_all=["MyClass", "my_function"],
        defined_symbols=[
            SymbolInfo("MyClass", SymbolType.CLASS, True, 10),
            SymbolInfo("my_function", SymbolType.FUNCTION, True, 20),
            SymbolInfo("_private_func", SymbolType.FUNCTION, False, 30),
        ],
        recommended_exports=["MyClass", "my_function"],
        missing_exports=[],
        policy_violations=[],
        module_category=ModuleCategory.ENGINE,
        audit_timestamp=datetime(2024, 1, 15, 10, 30, 0)
    )


@pytest.fixture
def sample_report_with_violations():
    """Create a sample report with violations."""
    return ModuleAuditReport(
        module_path="moira/bad_module.py",
        has_all_declaration=True,
        current_all=["_PrivateClass", "NonExistent"],
        defined_symbols=[
            SymbolInfo("_PrivateClass", SymbolType.CLASS, False, 10),
            SymbolInfo("PublicClass", SymbolType.CLASS, True, 20),
        ],
        recommended_exports=["PublicClass"],
        missing_exports=["PublicClass"],
        policy_violations=[
            PolicyViolation(
                rule_id="NO_PRIVATE_SYMBOLS",
                severity=Severity.ERROR,
                message="Private symbol '_PrivateClass' should not be in __all__",
                symbol_name="_PrivateClass",
                lineno=10
            ),
            PolicyViolation(
                rule_id="SYMBOL_MUST_EXIST",
                severity=Severity.ERROR,
                message="Symbol 'NonExistent' in __all__ is not defined",
                symbol_name="NonExistent",
                lineno=None
            ),
        ],
        module_category=ModuleCategory.ENGINE,
        audit_timestamp=datetime(2024, 1, 15, 10, 30, 0)
    )


class TestModuleReportGeneration:
    """Test module-level report generation."""

    def test_generate_module_report(self, reporter, sample_report):
        """Test generating a module report."""
        report_dict = reporter.generate_module_report(sample_report)
        
        assert report_dict["module_path"] == "moira/test_module.py"
        assert report_dict["has_all_declaration"] is True
        assert report_dict["current_all"] == ["MyClass", "my_function"]
        assert len(report_dict["defined_symbols"]) == 3
        assert report_dict["module_category"] == "engine"

    def test_module_report_symbols(self, reporter, sample_report):
        """Test symbol information in module report."""
        report_dict = reporter.generate_module_report(sample_report)
        
        symbols = report_dict["defined_symbols"]
        assert len(symbols) == 3
        
        # Check first symbol
        assert symbols[0]["name"] == "MyClass"
        assert symbols[0]["type"] == "class"
        assert symbols[0]["is_public"] is True

    def test_module_report_violations(self, reporter, sample_report_with_violations):
        """Test violations in module report."""
        report_dict = reporter.generate_module_report(sample_report_with_violations)
        
        violations = report_dict["policy_violations"]
        assert len(violations) == 2
        
        assert violations[0]["rule_id"] == "NO_PRIVATE_SYMBOLS"
        assert violations[0]["severity"] == "error"
        assert violations[0]["symbol_name"] == "_PrivateClass"


class TestSummaryReportGeneration:
    """Test summary statistics generation."""

    def test_generate_summary_single_module(self, reporter, sample_report):
        """Test summary for single module."""
        summary = reporter.generate_summary_report([sample_report])
        
        assert summary["total_modules"] == 1
        assert summary["modules_with_all"] == 1
        assert summary["modules_without_all"] == 0
        assert summary["coverage_percentage"] == 100.0

    def test_generate_summary_multiple_modules(self, reporter, sample_report):
        """Test summary for multiple modules."""
        report_without_all = ModuleAuditReport(
            module_path="moira/no_all.py",
            has_all_declaration=False,
            current_all=[],
            defined_symbols=[],
            recommended_exports=[],
            missing_exports=[],
            policy_violations=[],
            module_category=ModuleCategory.ENGINE,
            audit_timestamp=datetime.now()
        )
        
        summary = reporter.generate_summary_report([sample_report, report_without_all])
        
        assert summary["total_modules"] == 2
        assert summary["modules_with_all"] == 1
        assert summary["modules_without_all"] == 1
        assert summary["coverage_percentage"] == 50.0

    def test_summary_violation_counts(self, reporter, sample_report_with_violations):
        """Test violation counting in summary."""
        summary = reporter.generate_summary_report([sample_report_with_violations])
        
        assert summary["violations"]["errors"] == 2
        assert summary["violations"]["warnings"] == 0
        assert summary["violations"]["info"] == 0
        assert summary["violations"]["total"] == 2

    def test_summary_category_counts(self, reporter, sample_report):
        """Test category counting in summary."""
        facade_report = ModuleAuditReport(
            module_path="moira/facade.py",
            has_all_declaration=True,
            current_all=[],
            defined_symbols=[],
            recommended_exports=[],
            missing_exports=[],
            policy_violations=[],
            module_category=ModuleCategory.FACADE,
            audit_timestamp=datetime.now()
        )
        
        summary = reporter.generate_summary_report([sample_report, facade_report])
        
        assert summary["by_category"]["engine"] == 1
        assert summary["by_category"]["facade"] == 1


class TestJSONFormat:
    """Test JSON output format."""

    def test_format_json(self, reporter, sample_report):
        """Test JSON formatting."""
        json_output = reporter.format_json([sample_report])
        
        # Should be valid JSON
        data = json.loads(json_output)
        
        assert "modules" in data
        assert "summary" in data
        assert len(data["modules"]) == 1

    def test_json_without_summary(self, reporter, sample_report):
        """Test JSON without summary."""
        json_output = reporter.format_json([sample_report], include_summary=False)
        
        data = json.loads(json_output)
        
        assert "modules" in data
        assert "summary" not in data


class TestMarkdownFormat:
    """Test Markdown output format."""

    def test_format_markdown(self, reporter, sample_report):
        """Test Markdown formatting."""
        markdown = reporter.format_markdown([sample_report])
        
        assert "# Export Governance Audit Report" in markdown
        assert "## Summary" in markdown
        assert "moira/test_module.py" in markdown
        assert "engine" in markdown

    def test_markdown_with_violations(self, reporter, sample_report_with_violations):
        """Test Markdown with violations."""
        markdown = reporter.format_markdown([sample_report_with_violations])
        
        assert "Violations:" in markdown
        assert "_PrivateClass" in markdown
        assert "❌" in markdown  # Error icon

    def test_markdown_without_summary(self, reporter, sample_report):
        """Test Markdown without summary."""
        markdown = reporter.format_markdown([sample_report], include_summary=False)
        
        assert "## Summary" not in markdown
        assert "## Module Reports" in markdown


class TestHTMLFormat:
    """Test HTML output format."""

    def test_format_html(self, reporter, sample_report):
        """Test HTML formatting."""
        html = reporter.format_html([sample_report])
        
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "Export Governance Audit Report" in html
        assert "moira/test_module.py" in html

    def test_html_with_violations(self, reporter, sample_report_with_violations):
        """Test HTML with violations."""
        html = reporter.format_html([sample_report_with_violations])
        
        assert "Violations:" in html
        assert "class='error'" in html
        assert "_PrivateClass" in html

    def test_html_styling(self, reporter, sample_report):
        """Test HTML includes styling."""
        html = reporter.format_html([sample_report])
        
        assert "<style>" in html
        assert ".error" in html
        assert ".warning" in html


class TestWriteReport:
    """Test writing reports to files."""

    def test_write_json_report(self, reporter, sample_report):
        """Test writing JSON report to file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            reporter.write_report([sample_report], output_path, format="json")
            
            assert output_path.exists()
            content = output_path.read_text()
            data = json.loads(content)
            assert "modules" in data
        finally:
            output_path.unlink(missing_ok=True)

    def test_write_markdown_report(self, reporter, sample_report):
        """Test writing Markdown report to file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            reporter.write_report([sample_report], output_path, format="markdown")
            
            assert output_path.exists()
            content = output_path.read_text()
            assert "# Export Governance Audit Report" in content
        finally:
            output_path.unlink(missing_ok=True)

    def test_write_html_report(self, reporter, sample_report):
        """Test writing HTML report to file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            reporter.write_report([sample_report], output_path, format="html")
            
            assert output_path.exists()
            content = output_path.read_text()
            assert "<!DOCTYPE html>" in content
        finally:
            output_path.unlink(missing_ok=True)

    def test_write_invalid_format(self, reporter, sample_report):
        """Test writing with invalid format raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported format"):
                reporter.write_report([sample_report], output_path, format="invalid")
        finally:
            output_path.unlink(missing_ok=True)


class TestEmptyReports:
    """Test handling of empty report lists."""

    def test_summary_empty_reports(self, reporter):
        """Test summary with no reports."""
        summary = reporter.generate_summary_report([])
        
        assert summary["total_modules"] == 0
        assert summary["coverage_percentage"] == 0.0

    def test_format_json_empty(self, reporter):
        """Test JSON format with empty reports."""
        json_output = reporter.format_json([])
        
        data = json.loads(json_output)
        assert data["modules"] == []
        assert data["summary"]["total_modules"] == 0
