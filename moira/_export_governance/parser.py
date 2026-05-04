"""
Moira — AST Symbol Extraction
==============================

Archetype: Governance Logic (Logic Actor)

Purpose
-------
Governs the extraction of symbol metadata from Python source code via 
AST analysis. Identifies classes, functions, constants, and complex 
types, while tracking import provenance and __all__ declarations to 
support export governance verification.

Boundary
--------
Owns:
    - AST parsing and symbol taxonomy logic.
    - Export declaration (__all__) extraction logic.
    - Import provenance tracking.
Delegates:
    - Symbol metadata models to moira._export_governance.models.

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- Standard library ast module.
- Filesystem access for reading module source code.

Public surface
--------------
ModuleParser class and ParsedModule dataclass.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moira._export_governance.models import SymbolInfo, SymbolType


@dataclass
class ParsedModule:
    """
    Vessel: Complete parsed representation of a Python module.
    
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
    RITE: The Seer of Structure

    THEOREM: ModuleParser governs the translation of Python source 
        into a structured symbol registry for governance analysis.

    RITE OF PURPOSE:
        This engine exists to provide a truthful, structured 
        representation of the engine's internal implementation. It 
        serves as the primary lens through which governance policies 
        observe and verify the integrity of the sovereign boundary.

    LAW OF OPERATION:
        Responsibilities:
            - Parse Python source into AST.
            - Extract top-level symbol metadata.
            - Resolve import provenance and star-import exports.
            - Detect and extract __all__ declarations.
        Non-responsibilities:
            - Does not classify symbols (delegates to Classifier).
            - Does not enforce logic policies (delegates to Auditor).
        
    Canon: Moira Export Governance Protocol v1.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._export_governance.parser.ModuleParser",
      "risk": "medium",
      "api": {
        "frozen": ["parse_module", "extract_symbols", "extract_all_declaration"]
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": ["filesystem read"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "return_error_vessel"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["parsing_logic_change"]}
    }
    [/MACHINE_CONTRACT]
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
        
        Parses list or tuple literals, binary additions, and local name
        references assigned to __all__ at module level.
        
        Args:
            tree: Parsed AST module
            
        Returns:
            List of exported symbol names, or None if no __all__ found
        """
        # Create map of top-level assignments for resolution
        name_map: dict[str, ast.expr] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_map[target.id] = node.value
        
        for node in tree.body:
            # Look for __all__ = [...]
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        return self._extract_list_from_value(node.value, name_map)
        
        return None

    def _extract_list_from_value(
        self, 
        value: ast.expr, 
        name_map: dict[str, ast.expr] | None = None
    ) -> list[str]:
        """
        Extract string list from AST value.
        
        Handles list literals, tuple literals, list() calls, binary 
        additions, and local name references.
        
        Args:
            value: AST expression node
            name_map: Optional map of local assignments for resolution
            
        Returns:
            List of string values
        """
        result: list[str] = []
        name_map = name_map or {}
        
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
        
        # Handle list() calls
        elif (isinstance(value, ast.Call) and 
              isinstance(value.func, ast.Name) and 
              value.func.id == "list"):
            if value.args:
                result.extend(self._extract_list_from_value(value.args[0], name_map))
        
        # Handle binary addition (list + list)
        elif isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
            result.extend(self._extract_list_from_value(value.left, name_map))
            result.extend(self._extract_list_from_value(value.right, name_map))
            
        # Handle name references (resolve locally)
        elif isinstance(value, ast.Name) and value.id in name_map:
            # Pop to prevent infinite recursion
            orig_value = name_map.pop(value.id)
            result.extend(self._extract_list_from_value(orig_value, name_map))
            name_map[value.id] = orig_value
        
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
