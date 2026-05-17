"""
Data models for Moira export governance system.

This module defines all data structures used throughout the export governance
infrastructure, including symbol information, audit reports, policy violations,
and facade analysis results.

Boundary: Owns all data model definitions for export governance.
Dependencies: Python 3.10+ standard library (dataclasses, enum, datetime).
Public surface: All dataclasses and enums defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ModuleCategory(Enum):
    """Categories of modules with distinct export policies."""
    ENGINE = "engine"  # Core computational modules
    FACADE = "facade"  # Re-export modules
    CONSTANTS = "constants"  # Constant definitions
    TYPES = "types"  # Type definitions
    PRIVATE = "private"  # Private implementation (_*.py)
    PACKAGE_INIT = "package_init"  # __init__.py files
    TEST = "test"  # Test modules
    UNKNOWN = "unknown"


class SymbolType(Enum):
    """Types of symbols that can be exported."""
    CLASS = "class"
    FUNCTION = "function"
    CONSTANT = "constant"
    TYPE_ALIAS = "type_alias"
    ENUM = "enum"
    DATACLASS = "dataclass"
    PROTOCOL = "protocol"
    TYPED_DICT = "typed_dict"


class AuditStatus(Enum):
    """Status of module in audit workflow."""
    PENDING = "pending"  # Not yet audited
    AUDITED = "audited"  # Audit complete and applied
    SKIPPED = "skipped"  # Intentionally skipped
    EXEMPTED = "exempted"  # Exempt from governance


class Severity(Enum):
    """Severity levels for policy violations."""
    ERROR = "error"  # Must be fixed
    WARNING = "warning"  # Should be fixed
    INFO = "info"  # Informational only


class AuditDecision(Enum):
    """Audit decision types."""
    APPROVED = "approved"  # Recommendations approved as-is
    MODIFIED = "modified"  # Recommendations modified by auditor
    EXEMPTED = "exempted"  # Module exempted from governance


@dataclass
class SymbolInfo:
    """Represents a symbol defined in a module."""
    name: str
    symbol_type: SymbolType
    is_public: bool  # Based on naming convention
    lineno: int
    is_imported: bool = False
    import_source: str | None = None


@dataclass
class PolicyViolation:
    """Represents a policy rule violation."""
    rule_id: str
    severity: Severity
    message: str
    symbol_name: str | None = None
    lineno: int | None = None


@dataclass
class ModuleAuditReport:
    """Complete audit report for a single module."""
    module_path: str
    has_all_declaration: bool
    current_all: list[str]
    defined_symbols: list[SymbolInfo]
    recommended_exports: list[str]
    missing_exports: list[str]  # Public symbols not in __all__
    policy_violations: list[PolicyViolation]
    module_category: ModuleCategory
    audit_timestamp: datetime


@dataclass
class AuditLogEntry:
    """Records an audit decision."""
    module_path: str
    status: AuditStatus
    timestamp: datetime
    auditor: str
    decision: AuditDecision
    rationale: str | None = None
    applied_exports: list[str] = field(default_factory=list)


@dataclass
class FacadeAnalysisReport:
    """Analysis of a facade module's export alignment."""
    facade_module: str
    imported_symbols: dict[str, str]  # symbol -> source_module
    exported_symbols: list[str]
    missing_exports: list[str]  # Imported but not exported
    stale_exports: list[str]  # Exported but not imported
    delegate_modules: list[str]


__all__ = [
    "ModuleCategory",
    "SymbolType",
    "AuditStatus",
    "Severity",
    "AuditDecision",
    "SymbolInfo",
    "PolicyViolation",
    "ModuleAuditReport",
    "AuditLogEntry",
    "FacadeAnalysisReport",
]
