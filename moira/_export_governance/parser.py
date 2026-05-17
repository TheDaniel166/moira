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
            
            imports = self.extract_imports(tree, module_path)
            symbols = self.extract_symbols(tree)
            all_declaration = self.extract_all_declaration(tree, module_path, imports)
            
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

    def extract_all_declaration(
        self,
        tree: ast.Module,
        module_path: Path,
        imports: dict[str, str],
    ) -> list[str] | None:
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
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value is not None:
                    name_map[node.target.id] = node.value
        
        for node in tree.body:
            # Look for __all__ = [...]
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        return self._extract_list_from_value(
                            node.value,
                            name_map,
                            imports,
                            module_path,
                        )
        
        return None

    def _extract_list_from_value(
        self, 
        value: ast.expr, 
        name_map: dict[str, ast.expr] | None = None,
        imports: dict[str, str] | None = None,
        module_path: Path | None = None,
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
        imports = imports or {}
        
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
                result.extend(
                    self._extract_list_from_value(
                        value.args[0],
                        name_map,
                        imports,
                        module_path,
                    )
                )
        
        # Handle binary addition (list + list)
        elif isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
            result.extend(
                self._extract_list_from_value(
                    value.left,
                    name_map,
                    imports,
                    module_path,
                )
            )
            result.extend(
                self._extract_list_from_value(
                    value.right,
                    name_map,
                    imports,
                    module_path,
                )
            )
            
        # Handle name references (resolve locally)
        elif isinstance(value, ast.Name) and value.id in name_map:
            # Pop to prevent infinite recursion
            orig_value = name_map.pop(value.id)
            result.extend(
                self._extract_list_from_value(
                    orig_value,
                    name_map,
                    imports,
                    module_path,
                )
            )
            name_map[value.id] = orig_value
        elif (
            isinstance(value, ast.Name)
            and value.id in imports
            and imports[value.id].endswith(".__all__")
            and module_path is not None
        ):
            target_module = imports[value.id][: -len(".__all__")]
            target_file = self._resolve_module_file(target_module, module_path)
            if target_file is not None and target_file.exists():
                target_source = target_file.read_text(encoding="utf-8")
                target_tree = ast.parse(target_source, filename=str(target_file))
                target_imports = self.extract_imports(target_tree, target_file)
                target_all = self.extract_all_declaration(
                    target_tree,
                    target_file,
                    target_imports,
                )
                result.extend(target_all or [])

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
                module = self._resolve_module_name(node.module or "", node.level, module_path)
                for alias in node.names:
                    if alias.name == "*":
                        # Star imports - resolve by reading target module's __all__
                        star_imports = self._resolve_star_import(module, module_path)
                        for symbol_name in star_imports:
                            imports[symbol_name] = module
                        continue
                    imported_name = alias.asname if alias.asname else alias.name
                    if alias.name == "__all__":
                        imports[imported_name] = f"{module}.__all__"
                    else:
                        imports[imported_name] = module
            
            # Handle "import X" statements
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_name = alias.asname if alias.asname else alias.name
                    imports[imported_name] = alias.name
        
        return imports

    def _resolve_module_name(
        self,
        module: str,
        level: int,
        current_module_path: Path,
    ) -> str:
        """
        Resolve an import target into a best-effort absolute module path.

        Relative imports inside the Moira package are normalized to ``moira.*``
        paths so facade analysis can reason about layered surfaces truthfully.
        """
        if level == 0:
            return module

        package_parts = self._module_parts_for_path(current_module_path)
        if package_parts is None:
            return ("." * level) + module

        if current_module_path.name == "__init__.py":
            anchor_parts = package_parts
        else:
            anchor_parts = package_parts[:-1]

        if level > len(anchor_parts):
            return ("." * level) + module

        base_parts = anchor_parts[: len(anchor_parts) - level + 1]
        if module:
            base_parts.extend(module.split("."))
        return ".".join(base_parts)

    def _module_parts_for_path(self, module_path: Path) -> list[str] | None:
        """
        Derive the dotted module path from a filesystem path when possible.
        """
        module_path = module_path.resolve()

        package_root: Path | None = None
        for parent in [module_path.parent, *module_path.parents]:
            if (parent / "__init__.py").exists():
                package_root = parent
                continue
            break

        if package_root is None:
            return None

        relative = module_path.relative_to(package_root.parent)
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        return parts

    def _package_root_dir(self, module_path: Path) -> Path | None:
        """Return the filesystem directory of the top-level package."""
        module_parts = self._module_parts_for_path(module_path)
        if module_parts is None:
            return None

        module_path = module_path.resolve()
        root = module_path.parent if module_path.name == "__init__.py" else module_path.with_suffix("")
        for _ in range(len(module_parts) - 1):
            root = root.parent
        return root

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
            target_file = self._resolve_module_file(module, current_module_path)

            # Check if target file exists
            if target_file is None or not target_file.exists():
                return []
            
            # Parse the target module to get its __all__
            target_source = target_file.read_text(encoding="utf-8")
            target_tree = ast.parse(target_source, filename=str(target_file))
            target_imports = self.extract_imports(target_tree, target_file)
            target_all = self.extract_all_declaration(target_tree, target_file, target_imports)
            
            return target_all or []
            
        except Exception:
            # If we can't resolve, return empty list
            return []

    def _resolve_module_file(self, module: str, current_module_path: Path) -> Path | None:
        """
        Resolve a module path to its source file when possible.
        """
        current_dir = current_module_path.parent

        if module.startswith("moira."):
            package_root = self._package_root_dir(current_module_path)
            if package_root is None:
                return None
            repo_root = package_root.parent
            module_parts = module.split(".")
            base = repo_root.joinpath(*module_parts)
            package_init = base / "__init__.py"
            module_file = base.with_suffix(".py")
            if package_init.exists():
                return package_init
            if module_file.exists():
                return module_file
            return None

        if module == "moira":
            package_root = self._package_root_dir(current_module_path)
            if package_root is None:
                return None
            package_init = package_root / "__init__.py"
            if package_init.exists():
                return package_init

        module_file = current_dir / f"{module}.py"
        if module_file.exists():
            return module_file

        package_init = current_dir / module / "__init__.py"
        if package_init.exists():
            return package_init

        return None


__all__ = ["ModuleParser", "ParsedModule"]
