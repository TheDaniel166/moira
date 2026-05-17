"""
Moira — Facade Export Alignment
===============================

Archetype: Governance Logic (Logic Actor)

Purpose
-------
Governs the verification of facade module export alignment. Ensures 
that high-level facade modules correctly re-export the public surface 
of their delegate modules, detecting missing re-exports or stale 
entries in __all__.

Boundary
--------
Owns:
    - Facade analysis logic (missing vs stale detection).
    - Delegate-to-facade alignment verification rules.
Delegates:
    - Module scanning to moira._export_governance.scanner.
    - Source parsing to moira._export_governance.parser.
    - Result models to moira._export_governance.models.

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- Filesystem access for reading module source code.

Public surface
--------------
FacadeAnalyzer class.
"""

from pathlib import Path

from moira._export_governance.models import FacadeAnalysisReport, ModuleCategory
from moira._export_governance.scanner import ModuleScanner
from moira._export_governance.parser import ModuleParser


class FacadeAnalyzer:
    """
    RITE: The Guardian of the Gate

    THEOREM: FacadeAnalyzer governs the parity between the engine's 
        internal surfaces and its public facade re-exports.

    RITE OF PURPOSE:
        This engine exists to ensure that the engine's public facade 
        remains a faithful and complete representation of its 
        constituent parts. It prevents "silent drift" where new features 
        are added to substrates but forgotten in the facade, or where 
        stale exports remain after internal refactoring.

    LAW OF OPERATION:
        Responsibilities:
            - Identify missing re-exports in facade modules.
            - Detect stale exports that are no longer imported or defined.
            - Verify alignment between facade __all__ and delegate __all__.
        Non-responsibilities:
            - Does not enforce classification rules (delegates to Classifier).
            - Does not modify files (delegates to CodeGen).
        
    Canon: Moira Export Governance Protocol v1.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._export_governance.facade.FacadeAnalyzer",
      "risk": "medium",
      "api": {
        "frozen": ["analyze_facade", "verify_alignment", "identify_facade_modules"]
      },
      "state": {"mutable": true, "owners": ["Governance Auditor"]},
      "effects": {"signals_emitted": [], "io": ["filesystem read"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["alignment_logic_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, package_root: Path):
        """
        Initialize facade analyzer.
        
        Args:
            package_root: Root directory of package
        """
        self.package_root = Path(package_root)
        self.scanner = ModuleScanner(self.package_root)
        self.parser = ModuleParser()

    def identify_facade_modules(self) -> list[Path]:
        """
        Identify all facade modules in the package.
        
        Returns:
            List of paths to facade modules
        """
        return self.scanner.get_modules_by_category(
            ModuleCategory.FACADE,
            recursive=True
        )

    def analyze_facade(self, facade_path: Path) -> FacadeAnalysisReport:
        """
        Analyze a single facade module.
        
        Args:
            facade_path: Path to facade module
            
        Returns:
            FacadeAnalysisReport with alignment analysis
        """
        # Parse the facade module
        parsed = self.parser.parse_module(facade_path)
        
        # Extract imported symbols
        imported_symbols = self.extract_imported_symbols(parsed.imports)
        
        # Extract exported symbols (from __all__)
        exported_symbols = parsed.all_declaration or []
        
        # Find missing exports (imported but not exported)
        missing_exports = self.find_missing_exports(
            imported_symbols,
            exported_symbols
        )
        
        # Find stale exports (exported but not imported)
        stale_exports = self.find_stale_exports(
            imported_symbols,
            exported_symbols,
            parsed.symbols
        )
        
        # Get delegate modules
        delegate_modules = list(set(imported_symbols.values()))
        
        return FacadeAnalysisReport(
            facade_module=str(facade_path),
            imported_symbols=imported_symbols,
            exported_symbols=exported_symbols,
            missing_exports=missing_exports,
            stale_exports=stale_exports,
            delegate_modules=delegate_modules
        )

    def extract_imported_symbols(
        self,
        imports: dict[str, str]
    ) -> dict[str, str]:
        """
        Extract symbols imported from delegate modules.
        
        Args:
            imports: Dictionary of symbol -> source module
            
        Returns:
            Dictionary of imported symbols and their sources
        """
        # Filter out standard library and third-party imports
        # Keep only moira.* imports
        return {
            symbol: source
            for symbol, source in imports.items()
            if (
                source.startswith("moira")
                and not (symbol.startswith("_") and not symbol.startswith("__"))
                and "._" not in source
            )
        }

    def find_missing_exports(
        self,
        imported_symbols: dict[str, str],
        exported_symbols: list[str]
    ) -> list[str]:
        """
        Find symbols imported but not re-exported.
        
        Args:
            imported_symbols: Dictionary of imported symbols
            exported_symbols: List of exported symbols
            
        Returns:
            List of missing export names
        """
        exported_set = set(exported_symbols)
        return [
            symbol
            for symbol in imported_symbols.keys()
            if symbol not in exported_set
        ]

    def find_stale_exports(
        self,
        imported_symbols: dict[str, str],
        exported_symbols: list[str],
        defined_symbols: list
    ) -> list[str]:
        """
        Find symbols in __all__ but not imported or defined.
        
        Args:
            imported_symbols: Dictionary of imported symbols
            exported_symbols: List of exported symbols
            defined_symbols: List of SymbolInfo for defined symbols
            
        Returns:
            List of stale export names
        """
        imported_set = set(imported_symbols.keys())
        defined_set = {s.name for s in defined_symbols if not s.is_imported}
        
        stale = []
        for symbol in exported_symbols:
            if symbol not in imported_set and symbol not in defined_set:
                stale.append(symbol)
        
        return stale

    def verify_alignment(
        self,
        facade_path: Path,
        delegate_paths: list[Path]
    ) -> dict[str, list[str]]:
        """
        Verify facade exports align with delegate module exports.
        
        Args:
            facade_path: Path to facade module
            delegate_paths: Paths to delegate modules
            
        Returns:
            Dictionary with alignment issues by delegate
        """
        # Parse facade
        facade_parsed = self.parser.parse_module(facade_path)
        facade_exports = set(facade_parsed.all_declaration or [])
        
        alignment_issues: dict[str, list[str]] = {}
        
        # Check each delegate
        for delegate_path in delegate_paths:
            delegate_parsed = self.parser.parse_module(delegate_path)
            delegate_exports = set(delegate_parsed.all_declaration or [])
            
            # Find symbols in delegate but not in facade
            missing_in_facade = delegate_exports - facade_exports
            
            if missing_in_facade:
                alignment_issues[str(delegate_path)] = list(missing_in_facade)
        
        return alignment_issues


__all__ = ["FacadeAnalyzer"]
