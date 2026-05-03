"""
Unit tests for module scanner.

Tests recursive scanning, pattern filtering, module categorization,
and handling of edge cases.
"""

from pathlib import Path
import tempfile
import shutil

import pytest

from moira._export_governance.scanner import ModuleScanner
from moira._export_governance.models import ModuleCategory


@pytest.fixture
def temp_package():
    """Create a temporary package structure for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    package_root = temp_dir / "test_package"
    package_root.mkdir()
    
    # Create various module types
    (package_root / "__init__.py").write_text("# Package init")
    (package_root / "engine_module.py").write_text("# Engine module")
    (package_root / "constants.py").write_text("# Constants module")
    (package_root / "types.py").write_text("# Types module")
    (package_root / "facade.py").write_text("# Facade module")
    (package_root / "_private.py").write_text("# Private module")
    (package_root / "test_something.py").write_text("# Test module")
    
    # Create subdirectory with modules
    subdir = package_root / "subpackage"
    subdir.mkdir()
    (subdir / "__init__.py").write_text("# Subpackage init")
    (subdir / "sub_module.py").write_text("# Sub module")
    (subdir / "houses_tropical.py").write_text("# Houses module")
    (subdir / "houses_sidereal.py").write_text("# Houses module")
    
    # Create constellations subdirectory
    constellations = package_root / "constellations"
    constellations.mkdir()
    (constellations / "__init__.py").write_text("# Constellations init")
    (constellations / "stars_aries.py").write_text("# Aries stars")
    (constellations / "stars_taurus.py").write_text("# Taurus stars")
    
    yield package_root
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestModuleScanner:
    """Test ModuleScanner class."""

    def test_initialization(self, temp_package):
        """Test scanner initialization."""
        scanner = ModuleScanner(temp_package)
        assert scanner.package_root == temp_package.resolve()

    def test_scan_package_recursive(self, temp_package):
        """Test recursive scanning of package."""
        scanner = ModuleScanner(temp_package)
        modules = scanner.scan_package(recursive=True)
        
        # Should find all .py files recursively
        assert len(modules) > 0
        
        # Check that we found modules in subdirectories
        module_names = [m.name for m in modules]
        assert "__init__.py" in module_names
        assert "engine_module.py" in module_names
        assert "sub_module.py" in module_names
        assert "stars_aries.py" in module_names

    def test_scan_package_non_recursive(self, temp_package):
        """Test non-recursive scanning (top-level only)."""
        scanner = ModuleScanner(temp_package)
        modules = scanner.scan_package(recursive=False)
        
        # Should only find top-level modules
        module_names = [m.name for m in modules]
        assert "__init__.py" in module_names
        assert "engine_module.py" in module_names
        
        # Should NOT find subdirectory modules
        assert "sub_module.py" not in module_names
        assert "stars_aries.py" not in module_names

    def test_scan_with_pattern_simple(self, temp_package):
        """Test scanning with simple filename pattern."""
        scanner = ModuleScanner(temp_package)
        modules = scanner.scan_package(pattern="houses*.py", recursive=True)
        
        module_names = [m.name for m in modules]
        assert "houses_tropical.py" in module_names
        assert "houses_sidereal.py" in module_names
        assert "engine_module.py" not in module_names

    def test_scan_with_pattern_directory(self, temp_package):
        """Test scanning with directory pattern."""
        scanner = ModuleScanner(temp_package)
        modules = scanner.scan_package(pattern="constellations/*.py", recursive=True)
        
        module_names = [m.name for m in modules]
        assert "stars_aries.py" in module_names
        assert "stars_taurus.py" in module_names
        assert "engine_module.py" not in module_names

    def test_categorize_package_init(self, temp_package):
        """Test categorization of __init__.py files."""
        scanner = ModuleScanner(temp_package)
        init_file = temp_package / "__init__.py"
        
        category = scanner.categorize_module(init_file)
        assert category == ModuleCategory.PACKAGE_INIT

    def test_categorize_test_module(self, temp_package):
        """Test categorization of test modules."""
        scanner = ModuleScanner(temp_package)
        test_file = temp_package / "test_something.py"
        
        category = scanner.categorize_module(test_file)
        assert category == ModuleCategory.TEST

    def test_categorize_private_module(self, temp_package):
        """Test categorization of private modules."""
        scanner = ModuleScanner(temp_package)
        private_file = temp_package / "_private.py"
        
        category = scanner.categorize_module(private_file)
        assert category == ModuleCategory.PRIVATE

    def test_categorize_facade_module(self, temp_package):
        """Test categorization of facade modules."""
        scanner = ModuleScanner(temp_package)
        facade_file = temp_package / "facade.py"
        
        category = scanner.categorize_module(facade_file)
        assert category == ModuleCategory.FACADE

    def test_categorize_constants_module(self, temp_package):
        """Test categorization of constants modules."""
        scanner = ModuleScanner(temp_package)
        constants_file = temp_package / "constants.py"
        
        category = scanner.categorize_module(constants_file)
        assert category == ModuleCategory.CONSTANTS

    def test_categorize_types_module(self, temp_package):
        """Test categorization of types modules."""
        scanner = ModuleScanner(temp_package)
        types_file = temp_package / "types.py"
        
        category = scanner.categorize_module(types_file)
        assert category == ModuleCategory.TYPES

    def test_categorize_engine_module(self, temp_package):
        """Test categorization of engine modules (default)."""
        scanner = ModuleScanner(temp_package)
        engine_file = temp_package / "engine_module.py"
        
        category = scanner.categorize_module(engine_file)
        assert category == ModuleCategory.ENGINE

    def test_scan_with_categories(self, temp_package):
        """Test scanning with category assignment."""
        scanner = ModuleScanner(temp_package)
        categorized = scanner.scan_with_categories(recursive=True)
        
        assert len(categorized) > 0
        
        # Check that categories are assigned
        categories = set(categorized.values())
        assert ModuleCategory.PACKAGE_INIT in categories
        assert ModuleCategory.ENGINE in categories

    def test_get_modules_by_category(self, temp_package):
        """Test filtering modules by category."""
        scanner = ModuleScanner(temp_package)
        
        # Get all package init files
        init_modules = scanner.get_modules_by_category(
            ModuleCategory.PACKAGE_INIT,
            recursive=True
        )
        assert len(init_modules) > 0
        assert all(m.name == "__init__.py" for m in init_modules)
        
        # Get all test modules
        test_modules = scanner.get_modules_by_category(
            ModuleCategory.TEST,
            recursive=True
        )
        assert len(test_modules) > 0
        assert all(m.name.startswith("test_") for m in test_modules)

    def test_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_package = Path(temp_dir) / "empty"
            empty_package.mkdir()
            
            scanner = ModuleScanner(empty_package)
            modules = scanner.scan_package(recursive=True)
            
            assert len(modules) == 0

    def test_categorize_module_outside_package(self, temp_package):
        """Test categorizing a module outside the package root."""
        scanner = ModuleScanner(temp_package)
        
        # Create a module outside the package
        with tempfile.TemporaryDirectory() as temp_dir:
            outside_module = Path(temp_dir) / "outside.py"
            outside_module.write_text("# Outside module")
            
            category = scanner.categorize_module(outside_module)
            assert category == ModuleCategory.UNKNOWN


class TestRealMoiraPackage:
    """Test scanner on real Moira package structure."""

    def test_scan_real_moira_package(self):
        """Test scanning the actual Moira package."""
        moira_root = Path(__file__).parent.parent.parent / "moira"
        
        if not moira_root.exists():
            pytest.skip("Moira package not found")
        
        scanner = ModuleScanner(moira_root)
        modules = scanner.scan_package(recursive=True)
        
        # Should find many modules
        assert len(modules) > 50
        
        # Should find specific known modules
        module_names = {m.name for m in modules}
        assert "__init__.py" in module_names
        assert "constants.py" in module_names

    def test_categorize_real_facade_modules(self):
        """Test categorization of real Moira facade modules."""
        moira_root = Path(__file__).parent.parent.parent / "moira"
        
        if not moira_root.exists():
            pytest.skip("Moira package not found")
        
        scanner = ModuleScanner(moira_root)
        
        # Test known facade modules
        facade_file = moira_root / "facade.py"
        if facade_file.exists():
            category = scanner.categorize_module(facade_file)
            assert category == ModuleCategory.FACADE
        
        essentials_file = moira_root / "essentials.py"
        if essentials_file.exists():
            category = scanner.categorize_module(essentials_file)
            assert category == ModuleCategory.FACADE

    def test_scan_houses_modules(self):
        """Test scanning for houses modules with pattern."""
        moira_root = Path(__file__).parent.parent.parent / "moira"
        
        if not moira_root.exists():
            pytest.skip("Moira package not found")
        
        scanner = ModuleScanner(moira_root)
        houses_modules = scanner.scan_package(pattern="houses*.py", recursive=True)
        
        # Should find houses modules if they exist
        if len(houses_modules) > 0:
            assert all("houses" in m.name for m in houses_modules)

    def test_scan_constellations_directory(self):
        """Test scanning constellations subdirectory."""
        moira_root = Path(__file__).parent.parent.parent / "moira"
        
        if not moira_root.exists():
            pytest.skip("Moira package not found")
        
        scanner = ModuleScanner(moira_root)
        constellation_modules = scanner.scan_package(
            pattern="constellations/*.py",
            recursive=True
        )
        
        # Should find constellation star modules if they exist
        if len(constellation_modules) > 0:
            module_names = {m.name for m in constellation_modules}
            # Check for known constellation modules
            assert any("stars_" in name for name in module_names)
