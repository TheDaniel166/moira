"""
Unit tests for export governance data models.

Tests dataclass instantiation, field validation, enum value access,
and serialization/deserialization for JSON-compatible models.
"""

from datetime import datetime

import pytest

from moira._export_governance.models import (
    AuditDecision,
    AuditLogEntry,
    AuditStatus,
    FacadeAnalysisReport,
    ModuleAuditReport,
    ModuleCategory,
    PolicyViolation,
    Severity,
    SymbolInfo,
    SymbolType,
)


class TestEnumerations:
    """Test enum value access and string conversion."""

    def test_module_category_values(self):
        """Test ModuleCategory enum has expected values."""
        assert ModuleCategory.ENGINE.value == "engine"
        assert ModuleCategory.FACADE.value == "facade"
        assert ModuleCategory.CONSTANTS.value == "constants"
        assert ModuleCategory.TYPES.value == "types"
        assert ModuleCategory.PRIVATE.value == "private"
        assert ModuleCategory.PACKAGE_INIT.value == "package_init"
        assert ModuleCategory.TEST.value == "test"
        assert ModuleCategory.UNKNOWN.value == "unknown"

    def test_symbol_type_values(self):
        """Test SymbolType enum has expected values."""
        assert SymbolType.CLASS.value == "class"
        assert SymbolType.FUNCTION.value == "function"
        assert SymbolType.CONSTANT.value == "constant"
        assert SymbolType.TYPE_ALIAS.value == "type_alias"
        assert SymbolType.ENUM.value == "enum"
        assert SymbolType.DATACLASS.value == "dataclass"
        assert SymbolType.PROTOCOL.value == "protocol"
        assert SymbolType.TYPED_DICT.value == "typed_dict"

    def test_audit_status_values(self):
        """Test AuditStatus enum has expected values."""
        assert AuditStatus.PENDING.value == "pending"
        assert AuditStatus.AUDITED.value == "audited"
        assert AuditStatus.SKIPPED.value == "skipped"
        assert AuditStatus.EXEMPTED.value == "exempted"

    def test_severity_values(self):
        """Test Severity enum has expected values."""
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_audit_decision_values(self):
        """Test AuditDecision enum has expected values."""
        assert AuditDecision.APPROVED.value == "approved"
        assert AuditDecision.MODIFIED.value == "modified"
        assert AuditDecision.EXEMPTED.value == "exempted"


class TestSymbolInfo:
    """Test SymbolInfo dataclass."""

    def test_basic_instantiation(self):
        """Test creating a basic SymbolInfo instance."""
        symbol = SymbolInfo(
            name="MyClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=10
        )
        assert symbol.name == "MyClass"
        assert symbol.symbol_type == SymbolType.CLASS
        assert symbol.is_public is True
        assert symbol.lineno == 10
        assert symbol.is_imported is False
        assert symbol.import_source is None

    def test_imported_symbol(self):
        """Test creating an imported symbol."""
        symbol = SymbolInfo(
            name="imported_func",
            symbol_type=SymbolType.FUNCTION,
            is_public=True,
            lineno=5,
            is_imported=True,
            import_source="moira.other_module"
        )
        assert symbol.is_imported is True
        assert symbol.import_source == "moira.other_module"

    def test_private_symbol(self):
        """Test creating a private symbol."""
        symbol = SymbolInfo(
            name="_private_func",
            symbol_type=SymbolType.FUNCTION,
            is_public=False,
            lineno=20
        )
        assert symbol.is_public is False


class TestPolicyViolation:
    """Test PolicyViolation dataclass."""

    def test_basic_violation(self):
        """Test creating a basic policy violation."""
        violation = PolicyViolation(
            rule_id="RULE_001",
            severity=Severity.ERROR,
            message="Private symbol in __all__"
        )
        assert violation.rule_id == "RULE_001"
        assert violation.severity == Severity.ERROR
        assert violation.message == "Private symbol in __all__"
        assert violation.symbol_name is None
        assert violation.lineno is None

    def test_violation_with_details(self):
        """Test creating a violation with symbol and line details."""
        violation = PolicyViolation(
            rule_id="RULE_002",
            severity=Severity.WARNING,
            message="Missing export",
            symbol_name="MyClass",
            lineno=15
        )
        assert violation.symbol_name == "MyClass"
        assert violation.lineno == 15


class TestModuleAuditReport:
    """Test ModuleAuditReport dataclass."""

    def test_basic_report(self):
        """Test creating a basic audit report."""
        timestamp = datetime.now()
        symbols = [
            SymbolInfo("MyClass", SymbolType.CLASS, True, 10),
            SymbolInfo("my_func", SymbolType.FUNCTION, True, 20),
        ]
        violations = [
            PolicyViolation("RULE_001", Severity.WARNING, "Test violation")
        ]
        
        report = ModuleAuditReport(
            module_path="moira/test_module.py",
            has_all_declaration=False,
            current_all=[],
            defined_symbols=symbols,
            recommended_exports=["MyClass", "my_func"],
            missing_exports=["MyClass", "my_func"],
            policy_violations=violations,
            module_category=ModuleCategory.ENGINE,
            audit_timestamp=timestamp
        )
        
        assert report.module_path == "moira/test_module.py"
        assert report.has_all_declaration is False
        assert len(report.defined_symbols) == 2
        assert len(report.recommended_exports) == 2
        assert len(report.policy_violations) == 1
        assert report.module_category == ModuleCategory.ENGINE

    def test_report_with_existing_all(self):
        """Test report for module with existing __all__."""
        timestamp = datetime.now()
        report = ModuleAuditReport(
            module_path="moira/existing.py",
            has_all_declaration=True,
            current_all=["ExistingClass"],
            defined_symbols=[],
            recommended_exports=["ExistingClass", "NewClass"],
            missing_exports=["NewClass"],
            policy_violations=[],
            module_category=ModuleCategory.ENGINE,
            audit_timestamp=timestamp
        )
        
        assert report.has_all_declaration is True
        assert report.current_all == ["ExistingClass"]
        assert "NewClass" in report.missing_exports


class TestAuditLogEntry:
    """Test AuditLogEntry dataclass."""

    def test_basic_entry(self):
        """Test creating a basic audit log entry."""
        timestamp = datetime.now()
        entry = AuditLogEntry(
            module_path="moira/aspects.py",
            status=AuditStatus.AUDITED,
            timestamp=timestamp,
            auditor="maintainer@example.com",
            decision=AuditDecision.APPROVED
        )
        
        assert entry.module_path == "moira/aspects.py"
        assert entry.status == AuditStatus.AUDITED
        assert entry.decision == AuditDecision.APPROVED
        assert entry.rationale is None
        assert entry.applied_exports == []

    def test_entry_with_rationale(self):
        """Test entry with rationale and applied exports."""
        timestamp = datetime.now()
        entry = AuditLogEntry(
            module_path="moira/_internal.py",
            status=AuditStatus.EXEMPTED,
            timestamp=timestamp,
            auditor="maintainer@example.com",
            decision=AuditDecision.EXEMPTED,
            rationale="Private implementation module",
            applied_exports=[]
        )
        
        assert entry.status == AuditStatus.EXEMPTED
        assert entry.rationale == "Private implementation module"

    def test_entry_with_applied_exports(self):
        """Test entry with applied exports list."""
        timestamp = datetime.now()
        entry = AuditLogEntry(
            module_path="moira/aspects.py",
            status=AuditStatus.AUDITED,
            timestamp=timestamp,
            auditor="maintainer@example.com",
            decision=AuditDecision.MODIFIED,
            applied_exports=["AspectData", "find_aspects"]
        )
        
        assert len(entry.applied_exports) == 2
        assert "AspectData" in entry.applied_exports


class TestFacadeAnalysisReport:
    """Test FacadeAnalysisReport dataclass."""

    def test_basic_facade_report(self):
        """Test creating a basic facade analysis report."""
        report = FacadeAnalysisReport(
            facade_module="moira/facade.py",
            imported_symbols={"AspectData": "moira.aspects", "find_aspects": "moira.aspects"},
            exported_symbols=["AspectData"],
            missing_exports=["find_aspects"],
            stale_exports=[],
            delegate_modules=["moira.aspects"]
        )
        
        assert report.facade_module == "moira/facade.py"
        assert len(report.imported_symbols) == 2
        assert "find_aspects" in report.missing_exports
        assert len(report.stale_exports) == 0

    def test_facade_with_stale_exports(self):
        """Test facade report with stale exports."""
        report = FacadeAnalysisReport(
            facade_module="moira/essentials.py",
            imported_symbols={"CurrentClass": "moira.current"},
            exported_symbols=["CurrentClass", "OldClass"],
            missing_exports=[],
            stale_exports=["OldClass"],
            delegate_modules=["moira.current"]
        )
        
        assert "OldClass" in report.stale_exports
        assert len(report.missing_exports) == 0

    def test_facade_aligned(self):
        """Test facade report with perfect alignment."""
        report = FacadeAnalysisReport(
            facade_module="moira/classical.py",
            imported_symbols={"ClassicalData": "moira.classical_impl"},
            exported_symbols=["ClassicalData"],
            missing_exports=[],
            stale_exports=[],
            delegate_modules=["moira.classical_impl"]
        )
        
        assert len(report.missing_exports) == 0
        assert len(report.stale_exports) == 0
