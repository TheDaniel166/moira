"""
Symbol classifier for determining public/private status and symbol types.

This module provides functionality to classify symbols based on naming
conventions, decorators, and module-category-specific rules.

Boundary: Owns symbol classification logic.
Dependencies: models module for SymbolInfo and enums.
Public surface: SymbolClassifier class.
"""

from moira._export_governance.models import SymbolInfo, SymbolType, ModuleCategory


class SymbolClassifier:
    """
    Classifies symbols as public/private and determines their types.
    
    Applies naming convention rules (leading underscore for private),
    identifies symbol types (class, function, constant, etc.), and
    applies module-category-specific classification rules.
    """

    def classify_symbol(
        self,
        symbol: SymbolInfo,
        module_category: ModuleCategory
    ) -> SymbolInfo:
        """
        Classify a symbol with module-category-specific rules.
        
        Args:
            symbol: Symbol to classify
            module_category: Category of the module containing the symbol
            
        Returns:
            SymbolInfo with updated classification
        """
        # Apply category-specific rules
        if module_category == ModuleCategory.CONSTANTS:
            return self._classify_constants_module_symbol(symbol)
        elif module_category == ModuleCategory.TYPES:
            return self._classify_types_module_symbol(symbol)
        elif module_category == ModuleCategory.PRIVATE:
            return self._classify_private_module_symbol(symbol)
        else:
            # Default classification (already done by parser)
            return symbol

    def _classify_constants_module_symbol(self, symbol: SymbolInfo) -> SymbolInfo:
        """
        Apply constants module classification rules.
        
        In constants modules, all uppercase identifiers and Enums are public.
        
        Args:
            symbol: Symbol to classify
            
        Returns:
            SymbolInfo with updated classification
        """
        # Uppercase identifiers are constants and public
        if symbol.name.isupper():
            symbol.is_public = True
            symbol.symbol_type = SymbolType.CONSTANT
        
        # Enums are public in constants modules
        if symbol.symbol_type == SymbolType.ENUM:
            symbol.is_public = not symbol.name.startswith("_")
        
        return symbol

    def _classify_types_module_symbol(self, symbol: SymbolInfo) -> SymbolInfo:
        """
        Apply types module classification rules.
        
        In types modules, dataclasses, TypedDicts, Protocols, and type aliases
        are all public unless they have leading underscore.
        
        Args:
            symbol: Symbol to classify
            
        Returns:
            SymbolInfo with updated classification
        """
        # Type-related symbols are public in types modules
        if symbol.symbol_type in (
            SymbolType.DATACLASS,
            SymbolType.TYPED_DICT,
            SymbolType.PROTOCOL,
            SymbolType.TYPE_ALIAS
        ):
            symbol.is_public = not symbol.name.startswith("_")
        
        return symbol

    def _classify_private_module_symbol(self, symbol: SymbolInfo) -> SymbolInfo:
        """
        Apply private module classification rules.
        
        In private modules (leading underscore), symbols are generally internal
        unless explicitly marked for export.
        
        Args:
            symbol: Symbol to classify
            
        Returns:
            SymbolInfo with updated classification
        """
        # In private modules, be conservative - most symbols are private
        # Only symbols without leading underscore might be exported
        symbol.is_public = not symbol.name.startswith("_")
        
        return symbol

    def is_public_symbol(self, name: str) -> bool:
        """
        Determine if a symbol name indicates public visibility.
        
        Uses Python naming convention: leading underscore indicates private.
        
        Args:
            name: Symbol name to check
            
        Returns:
            True if symbol is public, False if private
        """
        return not name.startswith("_")

    def is_constant(self, name: str) -> bool:
        """
        Determine if a symbol name indicates a constant.
        
        Uses Python naming convention: all uppercase indicates constant.
        
        Args:
            name: Symbol name to check
            
        Returns:
            True if symbol appears to be a constant
        """
        return name.isupper() and len(name) > 0

    def should_export(
        self,
        symbol: SymbolInfo,
        module_category: ModuleCategory
    ) -> bool:
        """
        Determine if a symbol should be exported based on category rules.
        
        Args:
            symbol: Symbol to evaluate
            module_category: Category of the module
            
        Returns:
            True if symbol should be in __all__, False otherwise
        """
        # Never export private symbols
        if not symbol.is_public:
            return False
        
        # Never export imported symbols (unless in facade module)
        if symbol.is_imported and module_category != ModuleCategory.FACADE:
            return False
        
        # Category-specific rules
        if module_category == ModuleCategory.ENGINE:
            # Export all public classes, functions, constants, type aliases
            return symbol.symbol_type in (
                SymbolType.CLASS,
                SymbolType.FUNCTION,
                SymbolType.CONSTANT,
                SymbolType.TYPE_ALIAS,
                SymbolType.ENUM,
                SymbolType.DATACLASS,
                SymbolType.PROTOCOL,
                SymbolType.TYPED_DICT,
            )
        
        elif module_category == ModuleCategory.FACADE:
            # Export all imported symbols (re-exports)
            return symbol.is_imported or symbol.is_public
        
        elif module_category == ModuleCategory.CONSTANTS:
            # Export all uppercase constants and Enums
            return (
                symbol.symbol_type == SymbolType.CONSTANT or
                symbol.symbol_type == SymbolType.ENUM
            )
        
        elif module_category == ModuleCategory.TYPES:
            # Export all type-related symbols
            return symbol.symbol_type in (
                SymbolType.DATACLASS,
                SymbolType.TYPED_DICT,
                SymbolType.PROTOCOL,
                SymbolType.TYPE_ALIAS,
            )
        
        elif module_category == ModuleCategory.PACKAGE_INIT:
            # Export symbols intended for package-level import
            return symbol.is_public
        
        elif module_category == ModuleCategory.PRIVATE:
            # Minimal exports from private modules
            return False
        
        elif module_category == ModuleCategory.TEST:
            # No exports from test modules
            return False
        
        # Default: export public symbols
        return symbol.is_public


__all__ = ["SymbolClassifier"]
