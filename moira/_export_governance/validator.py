"""
Moira — Governance Validation Orchestration
===========================================

Archetype: Governance Logic (Logic Actor)

Purpose
-------
Governs the orchestration of export governance validation across the 
Moira package. Coordinates discovery, parsing, and policy enforcement 
to verify the integrity of the engine's public surface, identifying 
structural violations and alignment issues.

Boundary
--------
Owns:
    - Validation orchestration logic.
    - Strict mode enforcement policy.
    - Aggregated validation reporting.
Delegates:
    - Module discovery to moira._export_governance.scanner.
    - Symbol extraction to moira._export_governance.parser.
    - Policy enforcement to moira._export_governance.policy.
    - Classification to moira._export_governance.classifier.

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- Filesystem access for scanning and reading module source code.

Public surface
--------------
ValidationEngine class and associated result vessels.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moira._export_governance.models import (
    PolicyViolation,
    ModuleCategory,
    Severity,
    SymbolInfo,
    SymbolType,
)
from moira._export_governance.scanner import ModuleScanner
from moira._export_governance.parser import ModuleParser
from moira._export_governance.policy import ExportPolicyEngine
from moira._export_governance.classifier import SymbolClassifier


@dataclass
class ValidationResult:
    """Vessel: Result of validating a single module."""
    module_path: Path
    is_valid: bool
    violations: list[PolicyViolation] = field(default_factory=list)
    has_all_declaration: bool = False


@dataclass
class PackageValidationResult:
    """Vessel: Result of validating an entire package."""
    total_modules: int
    valid_modules: int
    invalid_modules: int
    total_violations: int
    module_results: list[ValidationResult] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if entire package is valid."""
        return self.invalid_modules == 0


class ValidationEngine:
    """
    RITE: The High Auditor

    THEOREM: ValidationEngine governs the complete verification 
        cycle of the engine's public surface against its 
        internal reality.

    RITE OF PURPOSE:
        This engine exists to provide a singular, authoritative 
        verification entry point for the engine's governance layer. 
        It ensures that the entire package adheres to the visibility 
        doctrine, providing the necessary assurance that the 
        sovereign boundary is secure and truthful.

    LAW OF OPERATION:
        Responsibilities:
            - Orchestrate the validation of individual modules.
            - Aggregate validation results across entire packages.
            - Enforce strictness levels based on operational requirements.
        Non-responsibilities:
            - Does not define policies (delegates to PolicyEngine).
            - Does not perform AST parsing (delegates to Parser).
        
    Canon: Moira Export Governance Protocol v1.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._export_governance.validator.ValidationEngine",
      "risk": "medium",
      "api": {
        "frozen": ["validate_module", "validate_package", "check_rule"]
      },
      "state": {"mutable": true, "owners": ["Governance Auditor"]},
      "effects": {"signals_emitted": [], "io": ["filesystem read"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["orchestration_logic_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, package_root: Path):
        """
        Initialize validation engine.
        
        Args:
            package_root: Root directory of package to validate
        """
        self.package_root = Path(package_root)
        self.scanner = ModuleScanner(self.package_root)
        self.parser = ModuleParser()
        self.policy_engine = ExportPolicyEngine()
        self.classifier = SymbolClassifier()
        
        # Load default policy
        self.policy_engine.load_policy()

    def validate_module(
        self,
        module_path: Path,
        strict_mode: bool = False
    ) -> ValidationResult:
        """
        Validate a single module's __all__ declaration.
        
        Args:
            module_path: Path to module file
            strict_mode: If True, all violations are errors; if False, warnings allowed
            
        Returns:
            ValidationResult with violations found
        """
        # Parse the module
        parsed = self.parser.parse_module(module_path)
        
        # Check for parse errors
        if parsed.parse_error:
            return ValidationResult(
                module_path=module_path,
                is_valid=False,
                violations=[
                    PolicyViolation(
                        rule_id="PARSE_ERROR",
                        severity=Severity.ERROR,
                        message=f"Failed to parse module: {parsed.parse_error}",
                        symbol_name=None,
                        lineno=None
                    )
                ],
                has_all_declaration=False
            )
        
        # Determine module category
        module_category = self.scanner.categorize_module(module_path)
        
        # Check if module has __all__ declaration
        has_all = parsed.all_declaration is not None
        
        # Merge imports into symbols list for validation
        all_symbols = list(parsed.symbols)
        for symbol_name, source_module in parsed.imports.items():
            # Add imported symbols as SymbolInfo objects
            all_symbols.append(SymbolInfo(
                name=symbol_name,
                symbol_type=SymbolType.FUNCTION,  # We don't know the actual type
                is_public=not symbol_name.startswith("_"),
                lineno=0,  # Imports don't have a meaningful line number for this purpose
                is_imported=True,
                import_source=source_module
            ))
        
        violations: list[PolicyViolation] = []
        
        # Rule: Every module must have __all__ (in strict mode)
        if strict_mode and not has_all:
            violations.append(PolicyViolation(
                rule_id="MISSING_ALL_DECLARATION",
                severity=Severity.ERROR,
                message="Module must have __all__ declaration",
                symbol_name=None,
                lineno=None
            ))
        
        # If module has __all__, validate it
        if has_all:
            current_all = parsed.all_declaration or []
            violations.extend(
                self.policy_engine.validate_exports(
                    current_all,
                    all_symbols,  # Use merged symbols list
                    module_category
                )
            )
        
        # In strict mode, treat warnings as errors
        if strict_mode:
            for violation in violations:
                if violation.severity == Severity.WARNING:
                    violation.severity = Severity.ERROR
        
        # Determine if module is valid
        has_errors = any(v.severity == Severity.ERROR for v in violations)
        is_valid = not has_errors
        
        return ValidationResult(
            module_path=module_path,
            is_valid=is_valid,
            violations=violations,
            has_all_declaration=has_all
        )

    def validate_package(
        self,
        pattern: str | None = None,
        strict_mode: bool = False
    ) -> PackageValidationResult:
        """
        Validate all modules in package.
        
        Args:
            pattern: Optional glob pattern to filter modules
            strict_mode: If True, enforce strict validation rules
            
        Returns:
            PackageValidationResult with aggregated results
        """
        # Scan for modules
        modules = self.scanner.scan_package(pattern=pattern, recursive=True)
        
        # Validate each module
        results: list[ValidationResult] = []
        for module_path in modules:
            result = self.validate_module(module_path, strict_mode=strict_mode)
            results.append(result)
        
        # Aggregate statistics
        total_modules = len(results)
        valid_modules = sum(1 for r in results if r.is_valid)
        invalid_modules = total_modules - valid_modules
        total_violations = sum(len(r.violations) for r in results)
        
        return PackageValidationResult(
            total_modules=total_modules,
            valid_modules=valid_modules,
            invalid_modules=invalid_modules,
            total_violations=total_violations,
            module_results=results
        )

    def check_rule(
        self,
        rule_id: str,
        module_path: Path
    ) -> list[PolicyViolation]:
        """
        Check a specific validation rule on a module.
        
        Args:
            rule_id: ID of rule to check
            module_path: Path to module file
            
        Returns:
            List of violations for that specific rule
        """
        # Validate the module
        result = self.validate_module(module_path, strict_mode=False)
        
        # Filter violations by rule ID
        return [v for v in result.violations if v.rule_id == rule_id]

    def get_violation_summary(
        self,
        result: PackageValidationResult
    ) -> dict[str, Any]:
        """
        Generate summary of violations by severity and rule.
        
        Args:
            result: Package validation result
            
        Returns:
            Dictionary with violation statistics
        """
        # Count by severity
        error_count = 0
        warning_count = 0
        info_count = 0
        
        # Count by rule
        rule_counts: dict[str, int] = {}
        
        for module_result in result.module_results:
            for violation in module_result.violations:
                # Count by severity
                if violation.severity == Severity.ERROR:
                    error_count += 1
                elif violation.severity == Severity.WARNING:
                    warning_count += 1
                elif violation.severity == Severity.INFO:
                    info_count += 1
                
                # Count by rule
                rule_counts[violation.rule_id] = rule_counts.get(violation.rule_id, 0) + 1
        
        return {
            "by_severity": {
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
                "total": error_count + warning_count + info_count
            },
            "by_rule": rule_counts
        }


__all__ = ["ValidationEngine", "ValidationResult", "PackageValidationResult"]
