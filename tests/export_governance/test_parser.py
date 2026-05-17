"""
Unit tests for AST parser.

Tests symbol extraction, __all__ declaration parsing, import tracking,
and error handling for malformed files.
"""

from pathlib import Path
import tempfile

import pytest

from moira._export_governance.parser import ModuleParser, ParsedModule
from moira._export_governance.models import SymbolType


@pytest.fixture
def parser():
    """Create a ModuleParser instance."""
    return ModuleParser()


@pytest.fixture
def temp_module():
    """Create a temporary Python module file."""
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    temp_file.close()  # Close the file before yielding
    yield Path(temp_file.name)
    # Use missing_ok=True to avoid errors if file is already deleted
    Path(temp_file.name).unlink(missing_ok=True)


class TestSymbolExtraction:
    """Test symbol extraction from various Python constructs."""

    def test_extract_class(self, parser, temp_module):
        """Test extracting a simple class definition."""
        temp_module.write_text("class MyClass:\n    pass\n")
        
        result = parser.parse_module(temp_module)
        
        assert len(result.symbols) == 1
        symbol = result.symbols[0]
        assert symbol.name == "MyClass"
        assert symbol.symbol_type == SymbolType.CLASS
        assert symbol.is_public is True
        assert symbol.lineno == 1

    def test_extract_private_class(self, parser, temp_module):
        """Test extracting a private class (leading underscore)."""
        temp_module.write_text("class _PrivateClass:\n    pass\n")
        
        result = parser.parse_module(temp_module)
        
        assert len(result.symbols) == 1
        symbol = result.symbols[0]
        assert symbol.name == "_PrivateClass"
        assert symbol.is_public is False

    def test_extract_function(self, parser, temp_module):
        """Test extracting a function definition."""
        temp_module.write_text("def my_function():\n    pass\n")
        
        result = parser.parse_module(temp_module)
        
        assert len(result.symbols) == 1
        symbol = result.symbols[0]
        assert symbol.name == "my_function"
        assert symbol.symbol_type == SymbolType.FUNCTION
        assert symbol.is_public is True

    def test_extract_async_function(self, parser, temp_module):
        """Test extracting an async function definition."""
        temp_module.write_text("async def async_function():\n    pass\n")
        
        result = parser.parse_module(temp_module)
        
        assert len(result.symbols) == 1
        symbol = result.symbols[0]
        assert symbol.name == "async_function"
        assert symbol.symbol_type == SymbolType.FUNCTION

    def test_extract_constant(self, parser, temp_module):
        """Test extracting uppercase constant."""
        temp_module.write_text("MY_CONSTANT = 42\n")
        
        result = parser.parse_module(temp_module)
        
        assert len(result.symbols) == 1
        symbol = result.symbols[0]
        assert symbol.name == "MY_CONSTANT"
        assert symbol.symbol_type == SymbolType.CONSTANT
        assert symbol.is_public is True

    def test_extract_enum(self, parser, temp_module):
        """Test extracting Enum class."""
        code = """
from enum import Enum

class MyEnum(Enum):
    VALUE1 = 1
    VALUE2 = 2
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        # Should find the Enum class
        enum_symbols = [s for s in result.symbols if s.name == "MyEnum"]
        assert len(enum_symbols) == 1
        assert enum_symbols[0].symbol_type == SymbolType.ENUM

    def test_extract_dataclass(self, parser, temp_module):
        """Test extracting dataclass."""
        code = """
from dataclasses import dataclass

@dataclass
class MyDataClass:
    field: str
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        # Should find the dataclass
        dataclass_symbols = [s for s in result.symbols if s.name == "MyDataClass"]
        assert len(dataclass_symbols) == 1
        assert dataclass_symbols[0].symbol_type == SymbolType.DATACLASS

    def test_extract_protocol(self, parser, temp_module):
        """Test extracting Protocol class."""
        code = """
from typing import Protocol

class MyProtocol(Protocol):
    def method(self) -> None: ...
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        # Should find the Protocol
        protocol_symbols = [s for s in result.symbols if s.name == "MyProtocol"]
        assert len(protocol_symbols) == 1
        assert protocol_symbols[0].symbol_type == SymbolType.PROTOCOL

    def test_extract_type_alias(self, parser, temp_module):
        """Test extracting type alias."""
        code = """
MyType: type[str] = str
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        # Should find the type alias
        type_symbols = [s for s in result.symbols if s.name == "MyType"]
        assert len(type_symbols) == 1
        assert type_symbols[0].symbol_type == SymbolType.TYPE_ALIAS

    def test_extract_multiple_symbols(self, parser, temp_module):
        """Test extracting multiple symbols from one module."""
        code = """
class MyClass:
    pass

def my_function():
    pass

MY_CONSTANT = 42

class _PrivateClass:
    pass
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert len(result.symbols) == 4
        names = {s.name for s in result.symbols}
        assert names == {"MyClass", "my_function", "MY_CONSTANT", "_PrivateClass"}


class TestAllDeclaration:
    """Test __all__ declaration extraction."""

    def test_extract_all_list(self, parser, temp_module):
        """Test extracting __all__ as list literal."""
        code = """
__all__ = ["MyClass", "my_function"]

class MyClass:
    pass

def my_function():
    pass
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.all_declaration is not None
        assert result.all_declaration == ["MyClass", "my_function"]

    def test_extract_all_tuple(self, parser, temp_module):
        """Test extracting __all__ as tuple literal."""
        code = """
__all__ = ("MyClass", "my_function")

class MyClass:
    pass
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.all_declaration is not None
        assert result.all_declaration == ["MyClass", "my_function"]

    def test_extract_all_multiline(self, parser, temp_module):
        """Test extracting multi-line __all__ declaration."""
        code = """
__all__ = [
    "MyClass",
    "my_function",
    "MY_CONSTANT",
]
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.all_declaration is not None
        assert len(result.all_declaration) == 3
        assert "MyClass" in result.all_declaration

    def test_no_all_declaration(self, parser, temp_module):
        """Test module without __all__ declaration."""
        code = """
class MyClass:
    pass
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.all_declaration is None

    def test_empty_all_declaration(self, parser, temp_module):
        """Test empty __all__ declaration."""
        code = """
__all__ = []
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.all_declaration is not None
        assert result.all_declaration == []


class TestImportExtraction:
    """Test import statement extraction."""

    def test_extract_from_import(self, parser, temp_module):
        """Test extracting 'from X import Y' statements."""
        code = """
from moira.aspects import AspectData, find_aspects
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert "AspectData" in result.imports
        assert result.imports["AspectData"] == "moira.aspects"
        assert "find_aspects" in result.imports
        assert result.imports["find_aspects"] == "moira.aspects"

    def test_extract_import_with_alias(self, parser, temp_module):
        """Test extracting imports with aliases."""
        code = """
from moira.aspects import AspectData as AD
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert "AD" in result.imports
        assert result.imports["AD"] == "moira.aspects"

    def test_extract_direct_import(self, parser, temp_module):
        """Test extracting 'import X' statements."""
        code = """
import moira.aspects
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert "moira.aspects" in result.imports
        assert result.imports["moira.aspects"] == "moira.aspects"

    def test_extract_direct_import_with_alias(self, parser, temp_module):
        """Test extracting 'import X as Y' statements."""
        code = """
import moira.aspects as aspects
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert "aspects" in result.imports
        assert result.imports["aspects"] == "moira.aspects"

    def test_star_import_resolved_from_module_all(self, parser, temp_module):
        """Test that star imports are expanded from the delegate __all__."""
        delegate = temp_module.parent / "delegate.py"
        delegate.write_text(
            '__all__ = ["PublicClass", "public_function"]\n'
            "class PublicClass:\n    pass\n\n"
            "def public_function():\n    pass\n",
            encoding="utf-8",
        )
        temp_module.write_text("from delegate import *\n", encoding="utf-8")

        result = parser.parse_module(temp_module)

        assert result.imports["PublicClass"] == "delegate"
        assert result.imports["public_function"] == "delegate"

    def test_relative_import_resolved_to_absolute_module_name(self, parser, temp_module):
        """Test that relative imports are normalized for facade analysis."""
        package_dir = temp_module.parent / f"moira_{temp_module.stem}"
        package_dir.mkdir(exist_ok=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "facade.py").write_text(
            '__all__ = ["Moira"]\nclass Moira:\n    pass\n',
            encoding="utf-8",
        )
        module = package_dir / "essentials.py"
        module.write_text("from .facade import Moira\n", encoding="utf-8")

        result = parser.parse_module(module)

        assert result.imports["Moira"] == f"{package_dir.name}.facade"

    def test_multiple_imports(self, parser, temp_module):
        """Test extracting multiple import statements."""
        code = """
from moira.aspects import AspectData
from moira.houses import HouseSystem
import moira.constants
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert len(result.imports) == 3
        assert result.imports["AspectData"] == "moira.aspects"
        assert result.imports["HouseSystem"] == "moira.houses"
        assert result.imports["moira.constants"] == "moira.constants"


class TestErrorHandling:
    """Test error handling for malformed files."""

    def test_syntax_error(self, parser, temp_module):
        """Test handling of syntax errors."""
        code = """
def broken_function(
    # Missing closing parenthesis
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.parse_error is not None
        assert "Syntax error" in result.parse_error
        assert len(result.symbols) == 0

    def test_empty_file(self, parser, temp_module):
        """Test parsing an empty file."""
        temp_module.write_text("")
        
        result = parser.parse_module(temp_module)
        
        assert result.parse_error is None
        assert len(result.symbols) == 0
        assert result.all_declaration is None

    def test_comments_only(self, parser, temp_module):
        """Test parsing a file with only comments."""
        code = """
# This is a comment
# Another comment
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        assert result.parse_error is None
        assert len(result.symbols) == 0


class TestComplexModule:
    """Test parsing a complex realistic module."""

    def test_realistic_module(self, parser, temp_module):
        """Test parsing a module with various constructs."""
        code = """
'''Module docstring.'''

from typing import Protocol
from dataclasses import dataclass
from enum import Enum

__all__ = ["MyClass", "my_function", "MY_CONSTANT", "MyEnum"]

MY_CONSTANT = 42
_PRIVATE_CONSTANT = 99

class MyEnum(Enum):
    VALUE1 = 1
    VALUE2 = 2

@dataclass
class MyClass:
    field: str

class _PrivateClass:
    pass

def my_function():
    pass

def _private_function():
    pass
"""
        temp_module.write_text(code)
        
        result = parser.parse_module(temp_module)
        
        # Check symbols
        assert len(result.symbols) > 0
        public_symbols = [s for s in result.symbols if s.is_public]
        private_symbols = [s for s in result.symbols if not s.is_public]
        
        assert len(public_symbols) >= 4
        assert len(private_symbols) >= 2
        
        # Check __all__
        assert result.all_declaration is not None
        assert len(result.all_declaration) == 4
        
        # Check imports
        assert "Protocol" in result.imports
        assert "dataclass" in result.imports
        assert "Enum" in result.imports
