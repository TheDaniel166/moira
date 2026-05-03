"""
Export policy engine for recommending and validating __all__ declarations.

This module implements the policy rules that determine which symbols should
be exported from different module categories, and validates existing __all__
declarations against those rules.

Boundary: Owns export policy logic and validation rules.
Dependencies: models, classifier modules.
Public surface: ExportPolicyEngine class.
"""

from pathlib import Path
from typing import Any

from moira._export_governance.models import (
    SymbolInfo,
    ModuleCategory,
    PolicyViolation,
    Severity,
)
from moira._export_governance.classifier import SymbolClassifier


class ExportPolicyEngine:
    """
    Applies export policy rules and validates __all__ declarations.
    
    This engine implements category-specific rules for determining which
    symbols should be exported, and validates existing declarations against
    those rules.
    """

    def __init__(self):
        """Initialize the policy engine."""
        self.classifier = SymbolClassifier()
        self.policy_config: dict[str, Any] = {}

    def load_policy(self, policy_path: Path | None = None) -> None:
        """
        Load policy configuration from file or use defaults.
        
        Args:
            policy_path: Optional path to policy configuration file
            
        Side effects:
            Updates internal policy_config
        """
        if policy_path and policy_path.exists():
            # TODO: Load from JSON/TOML file when configuration format is defined
            pass
        
        # Use default policy configuration
        self.policy_config = self._get_default_policy()

    def _get_default_policy(self) -> dict[str, Any]:
        """
        Get default policy configuration.
        
        Returns:
            Dictionary containing default policy rules
        """
        return {
            "strict_mode": False,
            "conservative_mode": True,
            "rules": {
                "no_private_symbols": True,
                "all_public_classes": True,
                "all_public_functions": True,
                "facade_completeness": True,
                "symbols_must_exist": True,
            }
        }

    def recommend_exports(
        self,
        symbols: list[SymbolInfo],
        module_category: ModuleCategory,
        current_all: list[str] | None = None
    ) -> list[str]:
        """
        Generate recommended __all__ contents based on policy rules.
        
        Args:
            symbols: List of symbols defined in the module
            module_category: Category of the module
            current_all: Existing __all__ declaration (preserved in conservative mode)
            
        Returns:
            List of symbol names that should be in __all__
        """
        recommended: set[str] = set()
        
        # In conservative mode, preserve existing exports
        if current_all and self.policy_config.get("conservative_mode", True):
            recommended.update(current_all)
        
        # Apply category-specific rules
        if module_category == ModuleCategory.ENGINE:
            recommended.update(self._recommend_engine_exports(symbols))
        
        elif module_category == ModuleCategory.FACADE:
            recommended.update(self._recommend_facade_exports(symbols))
        
        elif module_category == ModuleCategory.CONSTANTS:
            recommended.update(self._recommend_constants_exports(symbols))
        
        elif module_category == ModuleCategory.TYPES:
            recommended.update(self._recommend_types_exports(symbols))
        
        elif module_category == ModuleCategory.PACKAGE_INIT:
            recommended.update(self._recommend_package_init_exports(symbols))
        
        elif module_category == ModuleCategory.PRIVATE:
            # Private modules have minimal exports
            if current_all:
                recommended.update(current_all)
        
        elif module_category == ModuleCategory.TEST:
            # Test modules typically don't export
            pass
        
        return sorted(recommended)

    def _recommend_engine_exports(self, symbols: list[SymbolInfo]) -> set[str]:
        """
        Recommend exports for engine modules.
        
        Engine modules export all public classes, functions, constants, and type aliases.
        
        Args:
            symbols: List of symbols in the module
            
        Returns:
            Set of symbol names to export
        """
        exports: set[str] = set()
        
        for symbol in symbols:
            if self.classifier.should_export(symbol, ModuleCategory.ENGINE):
                exports.add(symbol.name)
        
        return exports

    def _recommend_facade_exports(self, symbols: list[SymbolInfo]) -> set[str]:
        """
        Recommend exports for facade modules.
        
        Facade modules re-export all imported symbols.
        
        Args:
            symbols: List of symbols in the module
            
        Returns:
            Set of symbol names to export
        """
        exports: set[str] = set()
        
        for symbol in symbols:
            # Export all imported symbols (re-exports)
            if symbol.is_imported:
                exports.add(symbol.name)
            # Also export any public symbols defined in the facade
            elif symbol.is_public:
                exports.add(symbol.name)
        
        return exports

    def _recommend_constants_exports(self, symbols: list[SymbolInfo]) -> set[str]:
        """
        Recommend exports for constants modules.
        
        Constants modules export all uppercase identifiers and Enums.
        
        Args:
            symbols: List of symbols in the module
            
        Returns:
            Set of symbol names to export
        """
        exports: set[str] = set()
        
        for symbol in symbols:
            if self.classifier.should_export(symbol, ModuleCategory.CONSTANTS):
                exports.add(symbol.name)
        
        return exports

    def _recommend_types_exports(self, symbols: list[SymbolInfo]) -> set[str]:
        """
        Recommend exports for types modules.
        
        Types modules export all dataclasses, TypedDicts, Protocols, and type aliases.
        
        Args:
            symbols: List of symbols in the module
            
        Returns:
            Set of symbol names to export
        """
        exports: set[str] = set()
        
        for symbol in symbols:
            if self.classifier.should_export(symbol, ModuleCategory.TYPES):
                exports.add(symbol.name)
        
        return exports

    def _recommend_package_init_exports(self, symbols: list[SymbolInfo]) -> set[str]:
        """
        Recommend exports for package __init__.py files.
        
        Package inits export symbols intended for package-level import.
        
        Args:
            symbols: List of symbols in the module
            
        Returns:
            Set of symbol names to export
        """
        exports: set[str] = set()
        
        for symbol in symbols:
            if self.classifier.should_export(symbol, ModuleCategory.PACKAGE_INIT):
                exports.add(symbol.name)
        
        return exports

    def validate_exports(
        self,
        current_all: list[str],
        symbols: list[SymbolInfo],
        module_category: ModuleCategory
    ) -> list[PolicyViolation]:
        """
        Validate existing __all__ declaration against policy rules.
        
        Args:
            current_all: Current __all__ declaration
            symbols: List of symbols defined in the module
            module_category: Category of the module
            
        Returns:
            List of policy violations found
        """
        violations: list[PolicyViolation] = []
        
        # Create symbol lookup
        symbol_map = {s.name: s for s in symbols}
        
        # Rule: No private symbols in __all__
        if self.policy_config["rules"]["no_private_symbols"]:
            violations.extend(self._check_no_private_symbols(current_all, symbol_map))
        
        # Rule: All symbols in __all__ must exist
        if self.policy_config["rules"]["symbols_must_exist"]:
            violations.extend(self._check_symbols_exist(current_all, symbol_map))
        
        # Rule: All public classes must be exported (ENGINE modules)
        if (module_category == ModuleCategory.ENGINE and 
            self.policy_config["rules"]["all_public_classes"]):
            violations.extend(self._check_all_public_classes(current_all, symbols))
        
        # Rule: All public functions must be exported (ENGINE modules)
        if (module_category == ModuleCategory.ENGINE and 
            self.policy_config["rules"]["all_public_functions"]):
            violations.extend(self._check_all_public_functions(current_all, symbols))
        
        # Rule: Facade completeness (FACADE modules)
        if (module_category == ModuleCategory.FACADE and 
            self.policy_config["rules"]["facade_completeness"]):
            violations.extend(self._check_facade_completeness(current_all, symbols))
        
        return violations

    def _check_no_private_symbols(
        self,
        current_all: list[str],
        symbol_map: dict[str, SymbolInfo]
    ) -> list[PolicyViolation]:
        """
        Check that no private symbols appear in __all__.
        
        Args:
            current_all: Current __all__ declaration
            symbol_map: Map of symbol names to SymbolInfo
            
        Returns:
            List of violations found
        """
        violations: list[PolicyViolation] = []
        
        for name in current_all:
            if name.startswith("_"):
                symbol = symbol_map.get(name)
                lineno = symbol.lineno if symbol else None
                violations.append(PolicyViolation(
                    rule_id="NO_PRIVATE_SYMBOLS",
                    severity=Severity.ERROR,
                    message=f"Private symbol '{name}' should not be in __all__",
                    symbol_name=name,
                    lineno=lineno
                ))
        
        return violations

    def _check_symbols_exist(
        self,
        current_all: list[str],
        symbol_map: dict[str, SymbolInfo]
    ) -> list[PolicyViolation]:
        """
        Check that all symbols in __all__ are defined or imported.
        
        Args:
            current_all: Current __all__ declaration
            symbol_map: Map of symbol names to SymbolInfo
            
        Returns:
            List of violations found
        """
        violations: list[PolicyViolation] = []
        
        for name in current_all:
            if name not in symbol_map:
                violations.append(PolicyViolation(
                    rule_id="SYMBOL_MUST_EXIST",
                    severity=Severity.ERROR,
                    message=f"Symbol '{name}' in __all__ is not defined or imported",
                    symbol_name=name,
                    lineno=None
                ))
        
        return violations

    def _check_all_public_classes(
        self,
        current_all: list[str],
        symbols: list[SymbolInfo]
    ) -> list[PolicyViolation]:
        """
        Check that all public classes are in __all__.
        
        Args:
            current_all: Current __all__ declaration
            symbols: List of symbols in the module
            
        Returns:
            List of violations found
        """
        violations: list[PolicyViolation] = []
        current_set = set(current_all)
        
        for symbol in symbols:
            if (symbol.symbol_type.value in ("class", "dataclass", "enum", "protocol", "typed_dict") and
                symbol.is_public and
                not symbol.is_imported and
                symbol.name not in current_set):
                violations.append(PolicyViolation(
                    rule_id="MISSING_PUBLIC_CLASS",
                    severity=Severity.WARNING,
                    message=f"Public class '{symbol.name}' should be in __all__",
                    symbol_name=symbol.name,
                    lineno=symbol.lineno
                ))
        
        return violations

    def _check_all_public_functions(
        self,
        current_all: list[str],
        symbols: list[SymbolInfo]
    ) -> list[PolicyViolation]:
        """
        Check that all public functions are in __all__.
        
        Args:
            current_all: Current __all__ declaration
            symbols: List of symbols in the module
            
        Returns:
            List of violations found
        """
        violations: list[PolicyViolation] = []
        current_set = set(current_all)
        
        for symbol in symbols:
            if (symbol.symbol_type.value == "function" and
                symbol.is_public and
                not symbol.is_imported and
                symbol.name not in current_set):
                violations.append(PolicyViolation(
                    rule_id="MISSING_PUBLIC_FUNCTION",
                    severity=Severity.WARNING,
                    message=f"Public function '{symbol.name}' should be in __all__",
                    symbol_name=symbol.name,
                    lineno=symbol.lineno
                ))
        
        return violations

    def _check_facade_completeness(
        self,
        current_all: list[str],
        symbols: list[SymbolInfo]
    ) -> list[PolicyViolation]:
        """
        Check that facade modules re-export all imported internal symbols.
        
        Args:
            current_all: Current __all__ declaration
            symbols: List of symbols in the module
            
        Returns:
            List of violations found
        """
        violations: list[PolicyViolation] = []
        current_set = set(current_all)
        
        for symbol in symbols:
            if symbol.is_imported and symbol.name not in current_set:
                # Only enforce re-export for internal Moira symbols
                if not symbol.import_source or not (
                    symbol.import_source.startswith("moira") or 
                    symbol.import_source.startswith(".")
                ):
                    continue
                    
                violations.append(PolicyViolation(
                    rule_id="INCOMPLETE_FACADE",
                    severity=Severity.WARNING,
                    message=f"Imported internal symbol '{symbol.name}' should be re-exported in __all__",
                    symbol_name=symbol.name,
                    lineno=symbol.lineno
                ))
        
        return violations


__all__ = ["ExportPolicyEngine"]
