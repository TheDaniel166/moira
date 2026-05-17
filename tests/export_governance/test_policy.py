"""
Unit tests for export policy engine.

Tests policy loading, export recommendations, validation rules,
and severity assignment.
"""

import pytest

from moira._export_governance.policy import ExportPolicyEngine
from moira._export_governance.models import (
    SymbolInfo,
    SymbolType,
    ModuleCategory,
    Severity,
)


@pytest.fixture
def policy_engine():
    """Create an ExportPolicyEngine instance."""
    engine = ExportPolicyEngine()
    engine.load_policy()  # Load default policy
    return engine


class TestPolicyLoading:
    """Test policy configuration loading."""

    def test_load_default_policy(self, policy_engine):
        """Test loading default policy configuration."""
        assert policy_engine.policy_config is not None
        assert "rules" in policy_engine.policy_config
        assert policy_engine.policy_config["rules"]["no_private_symbols"] is True

    def test_conservative_mode_default(self, policy_engine):
        """Test conservative mode is enabled by default."""
        assert policy_engine.policy_config["conservative_mode"] is True


class TestEngineModuleRecommendations:
    """Test export recommendations for engine modules."""

    def test_recommend_public_class(self, policy_engine):
        """Test recommending public class export."""
        symbols = [
            SymbolInfo("MyClass", SymbolType.CLASS, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.ENGINE,
            None
        )
        
        assert "MyClass" in recommended

    def test_recommend_public_function(self, policy_engine):
        """Test recommending public function export."""
        symbols = [
            SymbolInfo("my_function", SymbolType.FUNCTION, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.ENGINE,
            None
        )
        
        assert "my_function" in recommended

    def test_recommend_constant(self, policy_engine):
        """Test recommending constant export."""
        symbols = [
            SymbolInfo("MY_CONSTANT", SymbolType.CONSTANT, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.ENGINE,
            None
        )
        
        assert "MY_CONSTANT" in recommended

    def test_no_recommend_private_symbol(self, policy_engine):
        """Test not recommending private symbols."""
        symbols = [
            SymbolInfo("_PrivateClass", SymbolType.CLASS, False, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.ENGINE,
            None
        )
        
        assert "_PrivateClass" not in recommended

    def test_no_recommend_imported_in_engine(self, policy_engine):
        """Test not recommending imported symbols in engine modules."""
        symbols = [
            SymbolInfo("ImportedClass", SymbolType.CLASS, True, 1, True, "other.module"),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.ENGINE,
            None
        )
        
        assert "ImportedClass" not in recommended


class TestFacadeModuleRecommendations:
    """Test export recommendations for facade modules."""

    def test_recommend_imported_symbols(self, policy_engine):
        """Test recommending imported symbols in facade modules."""
        symbols = [
            SymbolInfo("ImportedClass", SymbolType.CLASS, True, 1, True, "other.module"),
            SymbolInfo("AnotherImport", SymbolType.FUNCTION, True, 2, True, "other.module"),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.FACADE,
            None
        )
        
        assert "ImportedClass" in recommended
        assert "AnotherImport" in recommended

    def test_recommend_public_symbols_in_facade(self, policy_engine):
        """Test recommending public symbols defined in facade."""
        symbols = [
            SymbolInfo("FacadeClass", SymbolType.CLASS, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.FACADE,
            None
        )
        
        assert "FacadeClass" in recommended


class TestConstantsModuleRecommendations:
    """Test export recommendations for constants modules."""

    def test_recommend_constants(self, policy_engine):
        """Test recommending constants."""
        symbols = [
            SymbolInfo("MY_CONSTANT", SymbolType.CONSTANT, True, 1),
            SymbolInfo("ANOTHER_CONSTANT", SymbolType.CONSTANT, True, 2),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.CONSTANTS,
            None
        )
        
        assert "MY_CONSTANT" in recommended
        assert "ANOTHER_CONSTANT" in recommended

    def test_recommend_enums(self, policy_engine):
        """Test recommending Enums in constants modules."""
        symbols = [
            SymbolInfo("MyEnum", SymbolType.ENUM, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.CONSTANTS,
            None
        )
        
        assert "MyEnum" in recommended

    def test_no_recommend_functions_in_constants(self, policy_engine):
        """Test not recommending functions in constants modules."""
        symbols = [
            SymbolInfo("helper_function", SymbolType.FUNCTION, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.CONSTANTS,
            None
        )
        
        assert "helper_function" not in recommended


class TestTypesModuleRecommendations:
    """Test export recommendations for types modules."""

    def test_recommend_dataclasses(self, policy_engine):
        """Test recommending dataclasses."""
        symbols = [
            SymbolInfo("MyDataClass", SymbolType.DATACLASS, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.TYPES,
            None
        )
        
        assert "MyDataClass" in recommended

    def test_recommend_protocols(self, policy_engine):
        """Test recommending Protocols."""
        symbols = [
            SymbolInfo("MyProtocol", SymbolType.PROTOCOL, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.TYPES,
            None
        )
        
        assert "MyProtocol" in recommended

    def test_recommend_type_aliases(self, policy_engine):
        """Test recommending type aliases."""
        symbols = [
            SymbolInfo("MyType", SymbolType.TYPE_ALIAS, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.TYPES,
            None
        )
        
        assert "MyType" in recommended


class TestConservativeMode:
    """Test conservative mode behavior."""

    def test_preserve_existing_exports(self, policy_engine):
        """Test that existing exports are preserved in conservative mode."""
        symbols = [
            SymbolInfo("NewClass", SymbolType.CLASS, True, 1),
        ]
        current_all = ["ExistingClass", "ExistingFunction"]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.ENGINE,
            current_all
        )
        
        # Should preserve existing exports
        assert "ExistingClass" in recommended
        assert "ExistingFunction" in recommended
        # Should also add new recommendations
        assert "NewClass" in recommended


class TestValidationRules:
    """Test policy validation rules."""

    def test_validate_no_private_symbols(self, policy_engine):
        """Test validation catches private symbols in __all__."""
        symbols = [
            SymbolInfo("_PrivateClass", SymbolType.CLASS, False, 1),
        ]
        current_all = ["_PrivateClass"]
        
        violations = policy_engine.validate_exports(
            current_all,
            symbols,
            ModuleCategory.ENGINE
        )
        
        assert len(violations) > 0
        assert any(v.rule_id == "NO_PRIVATE_SYMBOLS" for v in violations)
        assert any(v.severity == Severity.ERROR for v in violations)

    def test_validate_symbols_exist(self, policy_engine):
        """Test validation catches undefined symbols in __all__."""
        symbols = [
            SymbolInfo("ExistingClass", SymbolType.CLASS, True, 1),
        ]
        current_all = ["ExistingClass", "NonExistentClass"]
        
        violations = policy_engine.validate_exports(
            current_all,
            symbols,
            ModuleCategory.ENGINE
        )
        
        assert len(violations) > 0
        assert any(v.rule_id == "SYMBOL_MUST_EXIST" for v in violations)
        assert any(v.symbol_name == "NonExistentClass" for v in violations)

    def test_validate_missing_public_class(self, policy_engine):
        """Test validation catches missing public classes."""
        symbols = [
            SymbolInfo("MyClass", SymbolType.CLASS, True, 1),
            SymbolInfo("AnotherClass", SymbolType.CLASS, True, 2),
        ]
        current_all = ["MyClass"]  # Missing AnotherClass
        
        violations = policy_engine.validate_exports(
            current_all,
            symbols,
            ModuleCategory.ENGINE
        )
        
        assert len(violations) > 0
        assert any(v.rule_id == "MISSING_PUBLIC_CLASS" for v in violations)
        assert any(v.symbol_name == "AnotherClass" for v in violations)
        assert any(v.severity == Severity.WARNING for v in violations)

    def test_validate_missing_public_function(self, policy_engine):
        """Test validation catches missing public functions."""
        symbols = [
            SymbolInfo("my_function", SymbolType.FUNCTION, True, 1),
            SymbolInfo("another_function", SymbolType.FUNCTION, True, 2),
        ]
        current_all = ["my_function"]  # Missing another_function
        
        violations = policy_engine.validate_exports(
            current_all,
            symbols,
            ModuleCategory.ENGINE
        )
        
        assert len(violations) > 0
        assert any(v.rule_id == "MISSING_PUBLIC_FUNCTION" for v in violations)
        assert any(v.symbol_name == "another_function" for v in violations)

    def test_validate_facade_completeness(self, policy_engine):
        """Test validation catches incomplete facade re-exports."""
        symbols = [
            SymbolInfo("ImportedClass", SymbolType.CLASS, True, 1, True, "moira.other.module"),
            SymbolInfo("AnotherImport", SymbolType.FUNCTION, True, 2, True, "moira.other.module"),
        ]
        current_all = ["ImportedClass"]  # Missing AnotherImport
        
        violations = policy_engine.validate_exports(
            current_all,
            symbols,
            ModuleCategory.FACADE
        )
        
        assert len(violations) > 0
        assert any(v.rule_id == "INCOMPLETE_FACADE" for v in violations)
        assert any(v.symbol_name == "AnotherImport" for v in violations)

    def test_validate_clean_module(self, policy_engine):
        """Test validation passes for compliant module."""
        symbols = [
            SymbolInfo("MyClass", SymbolType.CLASS, True, 1),
            SymbolInfo("my_function", SymbolType.FUNCTION, True, 2),
        ]
        current_all = ["MyClass", "my_function"]
        
        violations = policy_engine.validate_exports(
            current_all,
            symbols,
            ModuleCategory.ENGINE
        )
        
        # Should have no violations
        assert len(violations) == 0


class TestPrivateAndTestModules:
    """Test recommendations for private and test modules."""

    def test_private_module_minimal_exports(self, policy_engine):
        """Test private modules have minimal exports."""
        symbols = [
            SymbolInfo("SomeClass", SymbolType.CLASS, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.PRIVATE,
            None
        )
        
        # Private modules don't auto-export
        assert len(recommended) == 0

    def test_private_module_preserves_existing(self, policy_engine):
        """Test private modules preserve existing exports."""
        symbols = [
            SymbolInfo("SomeClass", SymbolType.CLASS, True, 1),
        ]
        current_all = ["SomeClass"]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.PRIVATE,
            current_all
        )
        
        # Should preserve existing
        assert "SomeClass" in recommended

    def test_test_module_no_exports(self, policy_engine):
        """Test test modules don't export."""
        symbols = [
            SymbolInfo("TestClass", SymbolType.CLASS, True, 1),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.TEST,
            None
        )
        
        assert len(recommended) == 0


class TestPackageInitRecommendations:
    """Test recommendations for package __init__ files."""

    def test_recommend_public_symbols(self, policy_engine):
        """Test recommending public symbols from package init."""
        symbols = [
            SymbolInfo("PublicClass", SymbolType.CLASS, True, 1),
            SymbolInfo("public_function", SymbolType.FUNCTION, True, 2),
        ]
        
        recommended = policy_engine.recommend_exports(
            symbols,
            ModuleCategory.PACKAGE_INIT,
            None
        )
        
        assert "PublicClass" in recommended
        assert "public_function" in recommended
