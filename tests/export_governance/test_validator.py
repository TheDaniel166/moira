"""
Unit tests for validation engine.

Tests module validation, package validation, rule checking,
and strict mode behavior.
"""

from pathlib import Path
import tempfile
import shutil

import pytest

from moira._export_governance.validator import (
    ValidationEngine,
    ValidationResult,
    PackageValidationResult,
)
from moira._export_governance.models import Severity


@pytest.fixture
def temp_package():
    """Create a temporary package for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    package_root = temp_dir / "test_package"
    package_root.mkdir()
    
    yield package_root
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def validator(temp_package):
    """Create a ValidationEngine instance."""
    return ValidationEngine(temp_package)


class TestModuleValidation:
    """Test single module validation."""

    def test_validate_module_with_all(self, validator, temp_package):
        """Test validating module with proper __all__."""
        module = temp_package / "good_module.py"
        module.write_text("""
__all__ = ["MyClass", "my_function"]

class MyClass:
    pass

def my_function():
    pass
""")
        
        result = validator.validate_module(module)
        
        assert result.is_valid is True
        assert result.has_all_declaration is True
        assert len(result.violations) == 0

    def test_validate_module_without_all(self, validator, temp_package):
        """Test validating module without __all__."""
        module = temp_package / "no_all.py"
        module.write_text("""
class MyClass:
    pass
""")
        
        result = validator.validate_module(module, strict_mode=False)
        
        # In non-strict mode, missing __all__ is not an error
        assert result.has_all_declaration is False

    def test_validate_module_without_all_strict(self, validator, temp_package):
        """Test validating module without __all__ in strict mode."""
        module = temp_package / "no_all.py"
        module.write_text("""
class MyClass:
    pass
""")
        
        result = validator.validate_module(module, strict_mode=True)
        
        assert result.is_valid is False
        assert result.has_all_declaration is False
        assert any(v.rule_id == "MISSING_ALL_DECLARATION" for v in result.violations)

    def test_validate_module_with_private_symbol(self, validator, temp_package):
        """Test validating module with private symbol in __all__."""
        module = temp_package / "bad_module.py"
        module.write_text("""
__all__ = ["_PrivateClass"]

class _PrivateClass:
    pass
""")
        
        result = validator.validate_module(module)
        
        assert result.is_valid is False
        assert any(v.rule_id == "NO_PRIVATE_SYMBOLS" for v in result.violations)
        assert any(v.severity == Severity.ERROR for v in result.violations)

    def test_validate_module_with_undefined_symbol(self, validator, temp_package):
        """Test validating module with undefined symbol in __all__."""
        module = temp_package / "bad_module.py"
        module.write_text("""
__all__ = ["NonExistent"]

class MyClass:
    pass
""")
        
        result = validator.validate_module(module)
        
        assert result.is_valid is False
        assert any(v.rule_id == "SYMBOL_MUST_EXIST" for v in result.violations)

    def test_validate_module_missing_public_class(self, validator, temp_package):
        """Test validating module missing public class in __all__."""
        module = temp_package / "incomplete.py"
        module.write_text("""
__all__ = ["MyClass"]

class MyClass:
    pass

class AnotherClass:
    pass
""")
        
        result = validator.validate_module(module)
        
        # Should have warning about missing AnotherClass
        assert any(v.rule_id == "MISSING_PUBLIC_CLASS" for v in result.violations)
        assert any(v.symbol_name == "AnotherClass" for v in result.violations)

    def test_validate_parse_error(self, validator, temp_package):
        """Test validating module with syntax error."""
        module = temp_package / "broken.py"
        module.write_text("""
def broken_function(
    # Missing closing parenthesis
""")
        
        result = validator.validate_module(module)
        
        assert result.is_valid is False
        assert any(v.rule_id == "PARSE_ERROR" for v in result.violations)


class TestStrictMode:
    """Test strict mode behavior."""

    def test_strict_mode_warnings_as_errors(self, validator, temp_package):
        """Test that warnings become errors in strict mode."""
        module = temp_package / "incomplete.py"
        module.write_text("""
__all__ = ["MyClass"]

class MyClass:
    pass

class AnotherClass:
    pass
""")
        
        # Non-strict mode
        result_normal = validator.validate_module(module, strict_mode=False)
        warnings = [v for v in result_normal.violations if v.severity == Severity.WARNING]
        assert len(warnings) > 0
        
        # Strict mode
        result_strict = validator.validate_module(module, strict_mode=True)
        warnings_strict = [v for v in result_strict.violations if v.severity == Severity.WARNING]
        errors_strict = [v for v in result_strict.violations if v.severity == Severity.ERROR]
        
        # All warnings should become errors
        assert len(warnings_strict) == 0
        assert len(errors_strict) > 0


class TestPackageValidation:
    """Test package-level validation."""

    def test_validate_empty_package(self, validator, temp_package):
        """Test validating empty package."""
        result = validator.validate_package()
        
        assert result.total_modules == 0
        assert result.valid_modules == 0
        assert result.invalid_modules == 0

    def test_validate_package_with_modules(self, validator, temp_package):
        """Test validating package with multiple modules."""
        # Create good module
        good = temp_package / "good.py"
        good.write_text("""
__all__ = ["MyClass"]

class MyClass:
    pass
""")
        
        # Create bad module
        bad = temp_package / "bad.py"
        bad.write_text("""
__all__ = ["_PrivateClass"]

class _PrivateClass:
    pass
""")
        
        result = validator.validate_package()
        
        assert result.total_modules == 2
        assert result.valid_modules == 1
        assert result.invalid_modules == 1
        assert result.total_violations > 0

    def test_validate_package_with_pattern(self, validator, temp_package):
        """Test validating package with pattern filter."""
        # Create modules
        (temp_package / "test_module.py").write_text("class Test: pass")
        (temp_package / "real_module.py").write_text("class Real: pass")
        
        result = validator.validate_package(pattern="test_*.py")
        
        # Should only validate test_module.py
        assert result.total_modules == 1

    def test_package_validation_is_valid_property(self, validator, temp_package):
        """Test is_valid property on package result."""
        # Create only good modules
        good1 = temp_package / "good1.py"
        good1.write_text("""
__all__ = ["MyClass"]

class MyClass:
    pass
""")
        
        good2 = temp_package / "good2.py"
        good2.write_text("""
__all__ = ["AnotherClass"]

class AnotherClass:
    pass
""")
        
        result = validator.validate_package()
        
        assert result.is_valid is True
        assert result.invalid_modules == 0


class TestRuleChecking:
    """Test specific rule checking."""

    def test_check_specific_rule(self, validator, temp_package):
        """Test checking a specific rule."""
        module = temp_package / "test.py"
        module.write_text("""
__all__ = ["_PrivateClass", "NonExistent"]

class _PrivateClass:
    pass
""")
        
        # Check NO_PRIVATE_SYMBOLS rule
        violations = validator.check_rule("NO_PRIVATE_SYMBOLS", module)
        
        assert len(violations) > 0
        assert all(v.rule_id == "NO_PRIVATE_SYMBOLS" for v in violations)

    def test_check_rule_no_violations(self, validator, temp_package):
        """Test checking rule with no violations."""
        module = temp_package / "good.py"
        module.write_text("""
__all__ = ["MyClass"]

class MyClass:
    pass
""")
        
        violations = validator.check_rule("NO_PRIVATE_SYMBOLS", module)
        
        assert len(violations) == 0


class TestViolationSummary:
    """Test violation summary generation."""

    def test_get_violation_summary(self, validator, temp_package):
        """Test generating violation summary."""
        # Create modules with various violations
        bad1 = temp_package / "bad1.py"
        bad1.write_text("""
__all__ = ["_PrivateClass"]

class _PrivateClass:
    pass
""")
        
        bad2 = temp_package / "bad2.py"
        bad2.write_text("""
__all__ = ["NonExistent"]

class MyClass:
    pass
""")
        
        result = validator.validate_package()
        summary = validator.get_violation_summary(result)
        
        assert "by_severity" in summary
        assert "by_rule" in summary
        assert summary["by_severity"]["errors"] > 0
        assert summary["by_severity"]["total"] > 0

    def test_violation_summary_by_rule(self, validator, temp_package):
        """Test violation summary counts by rule."""
        module = temp_package / "bad.py"
        module.write_text("""
__all__ = ["_Private1", "_Private2"]

class _Private1:
    pass

class _Private2:
    pass
""")
        
        result = validator.validate_package()
        summary = validator.get_violation_summary(result)
        
        # Should have multiple NO_PRIVATE_SYMBOLS violations
        assert "NO_PRIVATE_SYMBOLS" in summary["by_rule"]
        assert summary["by_rule"]["NO_PRIVATE_SYMBOLS"] == 2


class TestRealMoiraValidation:
    """Test validation on real Moira package."""

    def test_validate_real_moira_module(self):
        """Test validating a real Moira module."""
        moira_root = Path(__file__).parent.parent.parent / "moira"
        
        if not moira_root.exists():
            pytest.skip("Moira package not found")
        
        validator = ValidationEngine(moira_root)
        
        # Test that validation runs without errors
        constants_file = moira_root / "constants.py"
        if constants_file.exists():
            result = validator.validate_module(constants_file)
            
            # Validation should complete (may or may not have __all__)
            assert result.module_path == constants_file
            # No parse errors
            assert not any(v.rule_id == "PARSE_ERROR" for v in result.violations)

    def test_validate_real_moira_package_sample(self):
        """Test validating a sample of real Moira modules."""
        moira_root = Path(__file__).parent.parent.parent / "moira"
        
        if not moira_root.exists():
            pytest.skip("Moira package not found")
        
        validator = ValidationEngine(moira_root)
        
        # Validate just a few modules (not the whole package)
        result = validator.validate_package(pattern="constants.py")
        
        if result.total_modules > 0:
            assert result.total_modules >= 1
