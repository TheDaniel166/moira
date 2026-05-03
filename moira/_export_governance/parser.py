"""
AST parser for extracting symbol information from Python modules.

This module provides functionality to parse Python source code using the AST
module, extract symbol definitions, identify __all__ declarations, and track
import statements for facade analysis.

Boundary: Owns AST parsing and symbol extraction logic.
Dependencies: Python ast module, pathlib.
Public surface: ModuleParser class and ParsedModule dataclass.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moira._export_governance.models import SymbolInfo, SymbolType


@dataclass
class ParsedModule:
    """
    Complete parsed representation of a Python module.
    
    Contains all extracted information from AST parsing including symbols,
    __all__ declaration, and import statements.
    """
    module_path: Path
    symbols: list[SymbolInfo]
    all_declaration: list[str] | None
    imports: dict[str, str]  # symbol_name -> source_module
    parse_error: str | None = None


class ModuleParser:
    """
    Parses Python modules and extracts symbol information using AST.
    
    This parser handles various Python constructs including classes, functions,
    constants, type aliases, enums, dataclasses, and protocols. It also extracts
    __all__ declarations and import statements.
    """

    def parse_module(self, module_path: Path) -> ParsedModule:
        """
        Parse a Python module and extract all relevant information.
        
        Args:
            module_path: Path to the Python module file
            
        Returns:
            ParsedModule containing extracted symbols, __all__, and imports
            
        Side effects:
            Reads file from filesystem
        """
        try:
            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(module_path))
            
            symbols = self.extract_symbols(tree)
            all_declaration = self.extract_all_declaration(tree)
            imports = self.extract_imports(tree, module_path)
            
            return ParsedModule(
                module_path=module_path,
                symbols=symbols,
                all_declaration=all_declaration,
                imports=imports,
                parse_error=None
            )
        except SyntaxError as e:
            # Handle malformed Python files
            return ParsedModule(
                module_path=module_path,
                symbols=[],
                all_declaration=None,
                imports={},
                parse_error=f"Syntax error: {e}"
            )
        except Exception as e:
            # Handle other parsing errors
            return ParsedModule(
                module_path=module_path,
                symbols=[],
                all_declaration=None,
                imports={},
                parse_error=f"Parse error: {e}"
            )

    def extract_symbols(self, tree: ast.Module) -> list[SymbolInfo]:
        """
        Extract symbol definitions from AST.
        
        Identifies classes, functions, constants, type aliases, enums,
        dataclasses, and protocols defined at module level.
        
        Args:
            tree: Parsed AST module
            
        Returns:
            List of SymbolInfo objects for all defined symbols
        """
        symbols: list[SymbolInfo] = []
        
        for node in ast.walk(tree):
            # Only process top-level definitions (direct children of Module)
            if not isinstance(node, ast.Module):
                continue
            
            for item in node.body:
                symbol_info = self._extract_symbol_from_node(item)
                if symbol_info:
                    symbols.append(symbol_info)
        
        return symbols

    def _extract_symbol_from_node(self, node: ast.stmt) -> SymbolInfo | None:
        """
        Extract symbol information from a single AST node.
        
        Args:
            node: AST statement node
            
        Returns:
            SymbolInfo if node defines a symbol, None otherwise
        """
        # Class definitions
        if isinstance(node, ast.ClassDef):
            symbol_type = self._determine_class_type(node)
            is_public = not node.name.startswith("_")
            return SymbolInfo(
                name=node.name,
                symbol_type=symbol_type,
                is_public=is_public,
                lineno=node.lineno,
                is_imported=False,
                import_source=None
            )
        
        # Function definitions (including async)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_public = not node.name.startswith("_")
            return SymbolInfo(
                name=node.name,
                symbol_type=SymbolType.FUNCTION,
                is_public=is_public,
                lineno=node.lineno,
                is_imported=False,
                import_source=None
            )
        
        # Variable assignments (constants and type aliases)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbol_type = self._determine_assignment_type(target.id, node.value)
                    is_public = not target.id.startswith("_")
                    return SymbolInfo(
                        name=target.id,
                        symbol_type=symbol_type,
                        is_public=is_public,
                        lineno=node.lineno,
                        is_imported=False,
                        import_source=None
                    )
        
        # Annotated assignments (type aliases with annotations)
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                is_public = not node.target.id.startswith("_")
                return SymbolInfo(
                    name=node.target.id,
                    symbol_type=SymbolType.TYPE_ALIAS,
                    is_public=is_public,
                    lineno=node.lineno,
                    is_imported=False,
                    import_source=None
                )
        
        return None

    def _determine_class_type(self, node: ast.ClassDef) -> SymbolType:
        """
        Determine the specific type of a class (Enum, dataclass, Protocol, etc.).
        
        Args:
            node: ClassDef AST node
            
        Returns:
            Appropriate SymbolType for the class
        """
        # Check for Enum base class
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ("Enum", "IntEnum", "Flag", "IntFlag"):
                    return SymbolType.ENUM
                if base.id in ("Protocol", "typing.Protocol"):
                    return SymbolType.PROTOCOL
                if base.id in ("TypedDict", "typing.TypedDict"):
                    return SymbolType.TYPED_DICT
        
        # Check for dataclass decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "dataclass":
                    return SymbolType.DATACLASS
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr == "dataclass":
                    return SymbolType.DATACLASS
        
        # Default to regular class
        return SymbolType.CLASS

    def _determine_assignment_type(self, name: str, value: ast.expr) -> SymbolType:
        """
        Determine if an assignment is a constant or type alias.
        
        Args:
            name: Variable name
            value: Assignment value expression
            
        Returns:
            SymbolType.CONSTANT for uppercase names, TYPE_ALIAS otherwise
        """
        # Uppercase names are constants
        if name.isupper():
            return SymbolType.CONSTANT
        
        # Check if value looks like a type alias
        if isinstance(value, (ast.Subscript, ast.Name, ast.Attribute)):
            # Could be a type alias, but default to constant for now
            # More sophisticated type alias detection could be added
            return SymbolType.TYPE_ALIAS
        
        return SymbolType.CONSTANT

    def extract_all_declaration(self, tree: ast.Module) -> list[str] | None:
        """
        Extract __all__ declaration from module AST.
        
        Parses list or tuple literals assigned to __all__ at module level.
        
        Args:
            tree: Parsed AST module
            
        Returns:
            List of exported symbol names, or None if no __all__ found
        """
        for node in tree.body:
            # Look for __all__ = [...]
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        return self._extract_list_from_value(node.value)
        
        return None

    def _extract_list_from_value(self, value: ast.expr) -> list[str]:
        """
        Extract string list from AST value (list or tuple literal).
        
        Args:
            value: AST expression node
            
        Returns:
            List of string values
        """
        result: list[str] = []
        
        # Handle list literals
        if isinstance(value, ast.List):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    result.append(elt.value)
        
        # Handle tuple literals
        elif isinstance(value, ast.Tuple):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    result.append(elt.value)
        
        return result

    def extract_imports(self, tree: ast.Module, module_path: Path) -> dict[str, str]:
        """
        Extract import statements from module AST.
        
        Tracks symbols imported from other modules for facade analysis.
        Resolves star imports by reading the target module's __all__.
        
        Args:
            tree: Parsed AST module
            module_path: Path to the current module (for resolving relative imports)
            
        Returns:
            Dictionary mapping imported symbol names to source modules
        """
        imports: dict[str, str] = {}
        
        for node in tree.body:
            # Handle "from X import Y" statements
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        # Star imports - resolve by reading target module's __all__
                        star_imports = self._resolve_star_import(module, module_path)
                        for symbol_name in star_imports:
                            imports[symbol_name] = module
                        continue
                    imported_name = alias.asname if alias.asname else alias.name
                    imports[imported_name] = module
            
            # Handle "import X" statements
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_name = alias.asname if alias.asname else alias.name
                    imports[imported_name] = alias.name
        
        return imports

    def _resolve_star_import(self, module: str, current_module_path: Path) -> list[str]:
        """
        Resolve a star import by reading the target module's __all__.
        
        Args:
            module: Module path (e.g., ".dignities_types", "dignities_types", or "moira.constants")
            current_module_path: Path to the current module (for resolving relative imports)
            
        Returns:
            List of symbol names exported by the module, or empty list if cannot resolve
        """
        try:
            # Resolve relative imports
            if module.startswith("."):
                # Explicit relative import - resolve based on current module's location
                current_dir = current_module_path.parent
                # Count leading dots
                level = len(module) - len(module.lstrip("."))
                module_name = module.lstrip(".")
                
                # Go up 'level' directories
                target_dir = current_dir
                for _ in range(level - 1):
                    target_dir = target_dir.parent
                
                # Construct target file path
                if module_name:
                    target_file = target_dir / f"{module_name}.py"
                else:
                    # from . import * - import from __init__.py
                    target_file = target_dir / "__init__.py"
            else:
                # Implicit relative import (same directory) or absolute import
                # Try same directory first
                current_dir = current_module_path.parent
                target_file = current_dir / f"{module}.py"
                
                if not target_file.exists():
                    # Not in same directory - could be absolute import
                    # For now, skip absolute imports that aren't in same directory
                    return []
            
            # Check if target file exists
            if not target_file.exists():
                return []
            
            # Parse the target module to get its __all__
            target_source = target_file.read_text(encoding="utf-8")
            target_tree = ast.parse(target_source, filename=str(target_file))
            target_all = self.extract_all_declaration(target_tree)
            
            return target_all or []
            
        except Exception:
            # If we can't resolve, return empty list
            return []


__all__ = ["ModuleParser", "ParsedModule"]
