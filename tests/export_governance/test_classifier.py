"""
Unit tests for symbol classifier.

Tests public/private classification, symbol type detection, and
module-category-specific classification rules.
"""

import pytest

from moira._export_governance.classifier import SymbolClassifier
from moira._export_governance.models import SymbolInfo, SymbolType, ModuleCategory


@pytest.fixture
def classifier():
    """Create a SymbolClassifier instance."""
    return SymbolClassifier()


class TestPublicPrivateClassification:
    """Test public/private symbol classification."""

    def test_is_public_symbol(self, classifier):
        """Test public symbol identification."""
        assert classifier.is_public_symbol("MyClass") is True
        assert classifier.is_public_symbol("my_function") is True
        assert classifier.is_public_symbol("MY_CONSTANT") is True

    def test_is_private_symbol(self, classifier):
        """Test private symbol identification."""
        assert classifier.is_public_symbol("_PrivateClass") is False
        assert classifier.is_public_symbol("_private_function") is False
        assert classifier.is_public_symbol("__dunder__") is False


class TestConstantIdentification:
    """Test constant identification."""

    def test_is_constant_uppercase(self, classifier):
        """Test uppercase constant identification."""
        assert classifier.is_constant("MY_CONSTANT") is True
        assert classifier.is_constant("ANOTHER_CONSTANT") is True
        assert classifier.is_constant("X") is True

    def test_is_not_constant(self, classifier):
        """Test non-constant identification."""
        assert classifier.is_constant("MyClass") is False
        assert classifier.is_constant("my_function") is False
        assert classifier.is_constant("My_Mixed_Case") is False
        assert classifier.is_constant("") is False


class TestConstantsModuleClassification:
    """Test classification rules for constants modules."""

    def test_uppercase_constant_public(self, classifier):
        """Test uppercase constants are public in constants modules."""
        symbol = SymbolInfo(
            name="MY_CONSTANT",
            symbol_type=SymbolType.CONSTANT,
            is_public=False,  # Will be overridden
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.CONSTANTS)
        
        assert classified.is_public is True
        assert classified.symbol_type == SymbolType.CONSTANT

    def test_enum_public_in_constants(self, classifier):
        """Test Enums are public in constants modules."""
        symbol = SymbolInfo(
            name="MyEnum",
            symbol_type=SymbolType.ENUM,
            is_public=True,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.CONSTANTS)
        
        assert classified.is_public is True

    def test_private_enum_stays_private(self, classifier):
        """Test private Enums stay private even in constants modules."""
        symbol = SymbolInfo(
            name="_PrivateEnum",
            symbol_type=SymbolType.ENUM,
            is_public=False,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.CONSTANTS)
        
        assert classified.is_public is False


class TestTypesModuleClassification:
    """Test classification rules for types modules."""

    def test_dataclass_public_in_types(self, classifier):
        """Test dataclasses are public in types modules."""
        symbol = SymbolInfo(
            name="MyDataClass",
            symbol_type=SymbolType.DATACLASS,
            is_public=True,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.TYPES)
        
        assert classified.is_public is True

    def test_protocol_public_in_types(self, classifier):
        """Test Protocols are public in types modules."""
        symbol = SymbolInfo(
            name="MyProtocol",
            symbol_type=SymbolType.PROTOCOL,
            is_public=True,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.TYPES)
        
        assert classified.is_public is True

    def test_type_alias_public_in_types(self, classifier):
        """Test type aliases are public in types modules."""
        symbol = SymbolInfo(
            name="MyType",
            symbol_type=SymbolType.TYPE_ALIAS,
            is_public=True,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.TYPES)
        
        assert classified.is_public is True

    def test_private_type_stays_private(self, classifier):
        """Test private types stay private in types modules."""
        symbol = SymbolInfo(
            name="_PrivateType",
            symbol_type=SymbolType.TYPE_ALIAS,
            is_public=False,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.TYPES)
        
        assert classified.is_public is False


class TestPrivateModuleClassification:
    """Test classification rules for private modules."""

    def test_public_symbol_in_private_module(self, classifier):
        """Test public symbols in private modules."""
        symbol = SymbolInfo(
            name="PublicClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.PRIVATE)
        
        assert classified.is_public is True

    def test_private_symbol_in_private_module(self, classifier):
        """Test private symbols in private modules."""
        symbol = SymbolInfo(
            name="_PrivateClass",
            symbol_type=SymbolType.CLASS,
            is_public=False,
            lineno=1
        )
        
        classified = classifier.classify_symbol(symbol, ModuleCategory.PRIVATE)
        
        assert classified.is_public is False


class TestShouldExport:
    """Test should_export decision logic."""

    def test_export_public_class_in_engine(self, classifier):
        """Test public classes should be exported from engine modules."""
        symbol = SymbolInfo(
            name="MyClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.ENGINE) is True

    def test_export_public_function_in_engine(self, classifier):
        """Test public functions should be exported from engine modules."""
        symbol = SymbolInfo(
            name="my_function",
            symbol_type=SymbolType.FUNCTION,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.ENGINE) is True

    def test_export_constant_in_engine(self, classifier):
        """Test constants should be exported from engine modules."""
        symbol = SymbolInfo(
            name="MY_CONSTANT",
            symbol_type=SymbolType.CONSTANT,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.ENGINE) is True

    def test_no_export_private_symbol(self, classifier):
        """Test private symbols should never be exported."""
        symbol = SymbolInfo(
            name="_PrivateClass",
            symbol_type=SymbolType.CLASS,
            is_public=False,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.ENGINE) is False

    def test_no_export_imported_in_engine(self, classifier):
        """Test imported symbols should not be exported from engine modules."""
        symbol = SymbolInfo(
            name="ImportedClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1,
            is_imported=True,
            import_source="other.module"
        )
        
        assert classifier.should_export(symbol, ModuleCategory.ENGINE) is False

    def test_export_imported_in_facade(self, classifier):
        """Test imported symbols should be exported from facade modules."""
        symbol = SymbolInfo(
            name="ImportedClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1,
            is_imported=True,
            import_source="other.module"
        )
        
        assert classifier.should_export(symbol, ModuleCategory.FACADE) is True

    def test_export_constant_in_constants_module(self, classifier):
        """Test constants should be exported from constants modules."""
        symbol = SymbolInfo(
            name="MY_CONSTANT",
            symbol_type=SymbolType.CONSTANT,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.CONSTANTS) is True

    def test_export_enum_in_constants_module(self, classifier):
        """Test Enums should be exported from constants modules."""
        symbol = SymbolInfo(
            name="MyEnum",
            symbol_type=SymbolType.ENUM,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.CONSTANTS) is True

    def test_no_export_function_in_constants_module(self, classifier):
        """Test functions should not be exported from constants modules."""
        symbol = SymbolInfo(
            name="helper_function",
            symbol_type=SymbolType.FUNCTION,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.CONSTANTS) is False

    def test_export_dataclass_in_types_module(self, classifier):
        """Test dataclasses should be exported from types modules."""
        symbol = SymbolInfo(
            name="MyDataClass",
            symbol_type=SymbolType.DATACLASS,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.TYPES) is True

    def test_export_protocol_in_types_module(self, classifier):
        """Test Protocols should be exported from types modules."""
        symbol = SymbolInfo(
            name="MyProtocol",
            symbol_type=SymbolType.PROTOCOL,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.TYPES) is True

    def test_no_export_from_private_module(self, classifier):
        """Test symbols should not be exported from private modules."""
        symbol = SymbolInfo(
            name="SomeClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.PRIVATE) is False

    def test_no_export_from_test_module(self, classifier):
        """Test symbols should not be exported from test modules."""
        symbol = SymbolInfo(
            name="TestClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.TEST) is False

    def test_export_public_from_package_init(self, classifier):
        """Test public symbols should be exported from package __init__."""
        symbol = SymbolInfo(
            name="PublicClass",
            symbol_type=SymbolType.CLASS,
            is_public=True,
            lineno=1
        )
        
        assert classifier.should_export(symbol, ModuleCategory.PACKAGE_INIT) is True


class TestEngineModuleExports:
    """Test export decisions for engine modules."""

    def test_export_all_public_types(self, classifier):
        """Test all public symbol types are exported from engine modules."""
        symbol_types = [
            SymbolType.CLASS,
            SymbolType.FUNCTION,
            SymbolType.CONSTANT,
            SymbolType.TYPE_ALIAS,
            SymbolType.ENUM,
            SymbolType.DATACLASS,
            SymbolType.PROTOCOL,
            SymbolType.TYPED_DICT,
        ]
        
        for symbol_type in symbol_types:
            symbol = SymbolInfo(
                name="PublicSymbol",
                symbol_type=symbol_type,
                is_public=True,
                lineno=1
            )
            assert classifier.should_export(symbol, ModuleCategory.ENGINE) is True
