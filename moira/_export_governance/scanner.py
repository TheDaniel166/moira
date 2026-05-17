"""
Moira — Module Discovery and Taxonomy
=====================================

Archetype: Governance Logic (Logic Actor)

Purpose
-------
Governs the discovery and categorization of Python modules within the 
Moira package. Recursively scans the package structure, identifies 
Python source files, and assigns architectural roles based on naming 
conventions, directory structure, and pattern matching.

Boundary
--------
Owns:
    - Module discovery logic (filesystem traversal).
    - Architectural categorization rules (facade, engine, constants, etc.).
    - Pattern matching for architectural identification.
Delegates:
    - Category definitions to moira._export_governance.models.

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- Filesystem read access to the package root.

Public surface
--------------
ModuleScanner class.
"""

from __future__ import annotations

from pathlib import Path
from fnmatch import fnmatch
from typing import Iterator

from moira._export_governance.models import ModuleCategory


class ModuleScanner:
    """
    RITE: The Scout of the Starfield

    THEOREM: ModuleScanner governs the identification and taxonomy 
        of engine modules to provide a map for governance analysis.

    RITE OF PURPOSE:
        This engine exists to provide a comprehensive and categorized 
        view of the engine's physical structure. It ensures that 
        every Python module is identified and assigned an architectural 
        role, allowing for the correct application of visibility and 
        export policies.

    LAW OF OPERATION:
        Responsibilities:
            - Recursively discover Python modules in the package.
            - Categorize modules based on naming conventions and path.
            - Filter modules based on glob patterns.
        Non-responsibilities:
            - Does not parse module content (delegates to Parser).
            - Does not validate symbols (delegates to Auditor).
        
    Canon: Moira Export Governance Protocol v1.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._export_governance.scanner.ModuleScanner",
      "risk": "low",
      "api": {
        "frozen": ["scan_package", "categorize_module", "get_modules_by_category"]
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": ["filesystem read"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["categorization_logic_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    # Facade module patterns
    FACADE_MODULES = {
        "facade.py",
        "essentials.py",
        "classical.py",
    }
    
    FACADE_PATTERNS = [
        "facade.py",
        "*_facade.py",
    ]
    
    # Constants module patterns
    CONSTANTS_PATTERNS = [
        "constants.py",
        "*_constants.py",
    ]
    
    # Types module patterns
    TYPES_PATTERNS = [
        "*_types.py",
        "types.py",
    ]

    def __init__(self, package_root: Path):
        """
        Initialize scanner with package root directory.
        
        Args:
            package_root: Root directory of the package to scan
        """
        self.package_root = Path(package_root).resolve()

    def scan_package(
        self,
        pattern: str | None = None,
        recursive: bool = True
    ) -> list[Path]:
        """
        Scan package for Python modules matching optional pattern.
        
        Args:
            pattern: Optional glob pattern to filter modules (e.g., "houses*.py")
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            List of Path objects for discovered Python modules
            
        Side effects:
            Reads filesystem to discover modules
        """
        modules: list[Path] = []
        
        if recursive:
            # Recursive scan using rglob
            for py_file in self.package_root.rglob("*.py"):
                if self._should_include_module(py_file, pattern):
                    modules.append(py_file)
        else:
            # Non-recursive scan using glob
            for py_file in self.package_root.glob("*.py"):
                if self._should_include_module(py_file, pattern):
                    modules.append(py_file)
        
        return sorted(modules)

    def _should_include_module(self, module_path: Path, pattern: str | None) -> bool:
        """
        Determine if a module should be included based on pattern.
        
        Args:
            module_path: Path to the module file
            pattern: Optional glob pattern to match against
            
        Returns:
            True if module should be included, False otherwise
        """
        # Skip non-Python files (shouldn't happen with *.py glob, but defensive)
        if module_path.suffix != ".py":
            return False
        
        # If no pattern specified, include all
        if pattern is None:
            return True
        
        # Match pattern against relative path from package root (use forward slashes)
        relative_path = module_path.relative_to(self.package_root)
        relative_str = str(relative_path).replace("\\", "/")
        
        # Try matching against full relative path
        if fnmatch(relative_str, pattern):
            return True
        
        # Also try matching against just the filename for simple patterns
        if fnmatch(module_path.name, pattern):
            return True
        
        return False

    def categorize_module(self, module_path: Path) -> ModuleCategory:
        """
        Determine module category based on path and naming conventions.
        
        Args:
            module_path: Path to the module file
            
        Returns:
            ModuleCategory enum value indicating the module's category
        """
        # Get relative path from package root for pattern matching
        try:
            relative_path = module_path.relative_to(self.package_root)
        except ValueError:
            # Module is outside package root
            return ModuleCategory.UNKNOWN
        
        relative_str = str(relative_path).replace("\\", "/")
        module_name = module_path.name
        
        # Check for __init__.py (package init)
        if module_name == "__init__.py":
            return ModuleCategory.PACKAGE_INIT
        
        # Check for test modules
        if module_name.startswith("test_") or module_name.endswith("_test.py"):
            return ModuleCategory.TEST
        
        # Check for private directories (any parent directory starting with _)
        if any(part.startswith("_") for part in relative_path.parent.parts):
            return ModuleCategory.PRIVATE

        # Check for private modules (leading underscore)
        if module_name.startswith("_") and module_name != "__init__.py":
            return ModuleCategory.PRIVATE
        
        # Check for facade modules (exact filename matches)
        if module_name in self.FACADE_MODULES:
            return ModuleCategory.FACADE
        
        # Check facade patterns (match against filename)
        for pattern in self.FACADE_PATTERNS:
            if fnmatch(module_name, pattern):
                return ModuleCategory.FACADE
        
        # Check constants patterns (match against filename)
        for pattern in self.CONSTANTS_PATTERNS:
            if fnmatch(module_name, pattern):
                return ModuleCategory.CONSTANTS
        
        # Check types patterns (match against filename)
        for pattern in self.TYPES_PATTERNS:
            if fnmatch(module_name, pattern):
                return ModuleCategory.TYPES
        
        # Default to engine module (core computational logic)
        return ModuleCategory.ENGINE

    def scan_with_categories(
        self,
        pattern: str | None = None,
        recursive: bool = True
    ) -> dict[Path, ModuleCategory]:
        """
        Scan package and return modules with their categories.
        
        Args:
            pattern: Optional glob pattern to filter modules
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            Dictionary mapping module paths to their categories
            
        Side effects:
            Reads filesystem to discover modules
        """
        modules = self.scan_package(pattern=pattern, recursive=recursive)
        return {module: self.categorize_module(module) for module in modules}

    def get_modules_by_category(
        self,
        category: ModuleCategory,
        pattern: str | None = None,
        recursive: bool = True
    ) -> list[Path]:
        """
        Get all modules of a specific category.
        
        Args:
            category: The module category to filter by
            pattern: Optional glob pattern to filter modules
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            List of module paths matching the specified category
            
        Side effects:
            Reads filesystem to discover modules
        """
        categorized = self.scan_with_categories(pattern=pattern, recursive=recursive)
        return [path for path, cat in categorized.items() if cat == category]


__all__ = ["ModuleScanner"]
