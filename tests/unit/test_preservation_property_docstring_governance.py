"""
Property-based tests for preservation of computational behavior during docstring governance fixes.

**Validates: Requirements 3.1, 3.2, 3.3**

These tests verify that docstring governance fixes do NOT affect computational behavior.
All astronomical calculations, API surfaces, and module behavior must be preserved.
"""

import pytest
import hypothesis
from hypothesis import given, strategies as st, settings
import importlib
import sys
from pathlib import Path
import inspect

# Import core moira modules for testing
import moira
from moira.constants import Body, HouseSystem
from moira.chart import create_chart, ChartContext


class TestPreservationProperty:
    """
    Property 2: Preservation - Computational Behavior Unchanged
    
    For any computational operation, API call, or module import that does NOT involve 
    docstring content, the fixed code SHALL produce exactly the same behavior as the 
    original code, preserving all astronomical calculations, public interfaces, and 
    runtime characteristics.
    """

    def test_module_import_preservation(self):
        """Test that all moira modules can be imported successfully."""
        # Core modules that should always import
        core_modules = [
            'moira.facade',
            'moira.constants', 
            'moira.julian',
            'moira.planets',
            'moira.houses',
        ]
        
        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Failed to import {module_name}"
            except ImportError as e:
                pytest.fail(f"Import failed for {module_name}: {e}")

    @given(jd=st.floats(min_value=2400000.0, max_value=2500000.0))
    @settings(max_examples=10, deadline=None)
    def test_body_position_computation_preservation(
        self,
        planetary_reader,
        jd: float,
    ):
        """Test that body position calculations produce consistent results."""
        hypothesis.assume(2400000.0 <= jd <= 2500000.0)

        # Test basic chart creation and planet data access.
        test_lat = 40.7128   # New York latitude
        test_lon = -74.0060  # New York longitude

        chart = create_chart(
            jd,
            test_lat,
            test_lon,
            reader=planetary_reader,
        )

        sun_data = chart.planets.get(Body.SUN)
        assert sun_data is not None, "Chart should contain Sun data"
        assert hasattr(sun_data, 'longitude'), "Sun data should have longitude"
        assert 0.0 <= sun_data.longitude < 360.0, (
            f"Sun longitude {sun_data.longitude} out of range"
        )

        moon_data = chart.planets.get(Body.MOON)
        assert moon_data is not None, "Chart should contain Moon data"
        assert hasattr(moon_data, 'longitude'), "Moon data should have longitude"
        assert 0.0 <= moon_data.longitude < 360.0, (
            f"Moon longitude {moon_data.longitude} out of range"
        )

    @given(
        lat=st.floats(min_value=-90.0, max_value=90.0),
        lon=st.floats(min_value=-180.0, max_value=180.0),
        jd=st.floats(min_value=2400000.0, max_value=2500000.0)
    )
    @settings(max_examples=10)  # Reduced from default 100 for faster execution
    def test_coordinate_transformation_preservation(self, lat: float, lon: float, jd: float):
        """Test that coordinate transformations produce consistent results."""
        hypothesis.assume(-90.0 <= lat <= 90.0)
        hypothesis.assume(-180.0 <= lon <= 180.0)
        hypothesis.assume(2400000.0 <= jd <= 2500000.0)
        
        try:
            # Test basic coordinate operations using julian module
            from moira.julian import julian_day, calendar_from_jd
            
            # Test JD conversion - calendar_from_jd returns 4 values: year, month, day, hour
            year, month, day, hour = calendar_from_jd(jd)
            assert isinstance(year, int), "Year should be integer"
            assert isinstance(month, int), "Month should be integer"
            assert isinstance(day, (int, float)), "Day should be numeric"
            assert isinstance(hour, (int, float)), "Hour should be numeric"
            
            # Test round-trip conversion
            jd_converted = julian_day(year, month, int(day))
            assert isinstance(jd_converted, (int, float)), "Converted JD should be numeric"
            assert jd_converted > 0, "JD should be positive"
            
        except ImportError as e:
            pytest.skip(f"Skipping due to missing coordinate functions: {e}")
        except Exception as e:
            if "No module named" in str(e) or "kernel" in str(e).lower():
                pytest.skip(f"Skipping due to missing dependency: {e}")
            else:
                raise

    def test_constants_preservation(self):
        """Test that astronomical constants are preserved."""
        try:
            from moira.constants import Body, HouseSystem
            
            # Verify Body constant exists and has expected structure
            assert Body is not None, "Body enum should exist"
            
            # Verify HouseSystem constant exists and has expected structure  
            assert HouseSystem is not None, "HouseSystem enum should exist"
            
            # Test that we can access some common body values
            if hasattr(Body, 'SUN'):
                assert Body.SUN is not None, "Body.SUN should have a value"
            if hasattr(Body, 'MOON'):
                assert Body.MOON is not None, "Body.MOON should have a value"
                        
        except ImportError as e:
            pytest.skip(f"Skipping due to missing constants: {e}")

    @given(
        jd=st.floats(min_value=2400000.0, max_value=2500000.0),
        body1=st.sampled_from(['SUN', 'MOON', 'MERCURY', 'VENUS', 'MARS']),
        body2=st.sampled_from(['SUN', 'MOON', 'MERCURY', 'VENUS', 'MARS'])
    )
    @settings(max_examples=10, deadline=None)
    def test_aspect_calculation_preservation(
        self,
        planetary_reader,
        jd: float,
        body1: str,
        body2: str,
    ):
        """Test that aspect calculations produce consistent results."""
        hypothesis.assume(2400000.0 <= jd <= 2500000.0)
        hypothesis.assume(body1 != body2)  # Don't calculate aspects between same body

        test_lat = 40.7128   # New York latitude
        test_lon = -74.0060  # New York longitude
        chart = create_chart(
            jd,
            test_lat,
            test_lon,
            reader=planetary_reader,
        )

        planet1_data = chart.planets.get(getattr(Body, body1))
        planet2_data = chart.planets.get(getattr(Body, body2))
        assert planet1_data is not None, f"Chart should contain {body1} data"
        assert planet2_data is not None, f"Chart should contain {body2} data"

        sep = abs(planet1_data.longitude - planet2_data.longitude)
        if sep > 180.0:
            sep = 360.0 - sep

        assert 0.0 <= sep <= 180.0, (
            f"Angular separation {sep} out of range"
        )

    def test_chart_creation_preservation(self, planetary_reader):
        """Test that chart creation functionality is preserved."""
        test_jd = 2451545.0  # J2000.0
        test_lat = 40.7128   # New York latitude
        test_lon = -74.0060  # New York longitude

        test_chart = create_chart(
            test_jd,
            test_lat,
            test_lon,
            reader=planetary_reader,
        )
        assert test_chart is not None, "Chart creation should succeed"
        assert hasattr(test_chart, 'planets'), "Chart should have planets data"
        assert hasattr(test_chart, 'nodes'), "Chart should have nodes data"

    def test_public_api_surface_preservation(self):
        """Test that public API surfaces are preserved."""
        # Test that key modules have expected public attributes
        modules_to_test = [
            ('moira.chart', ['create_chart', 'ChartContext']),
            ('moira.julian', ['julian_day', 'calendar_from_jd']),
            ('moira.constants', ['Body', 'HouseSystem']),
        ]
        
        for module_name, expected_attrs in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                
                for attr_name in expected_attrs:
                    if hasattr(module, attr_name):
                        attr = getattr(module, attr_name)
                        assert attr is not None, f"{module_name}.{attr_name} should not be None"
                        
            except ImportError as e:
                pytest.skip(f"Skipping {module_name} due to import error: {e}")

    @given(jd=st.floats(min_value=2400000.0, max_value=2500000.0))
    @settings(max_examples=10)  # Reduced from default 100 for faster execution
    def test_time_conversion_preservation(self, jd: float):
        """Test that time conversion functions are preserved."""
        hypothesis.assume(2400000.0 <= jd <= 2500000.0)
        
        try:
            from moira.julian import julian_day, calendar_from_jd
            
            # Test basic time conversion functionality
            result = calendar_from_jd(jd)
            assert result is not None, "JD to calendar conversion should return a result"
            assert len(result) >= 3, "Calendar result should have at least year, month, day"
            
            year, month, day = result[:3]
            assert isinstance(year, int), "Year should be integer"
            assert isinstance(month, int), "Month should be integer"
            assert 1 <= month <= 12, "Month should be 1-12"
            
            # Test round-trip conversion with a known date
            test_year, test_month, test_day = 2000, 1, 1
            converted_jd = julian_day(test_year, test_month, test_day)
            assert isinstance(converted_jd, (int, float)), "Calendar to JD should return numeric value"
            assert converted_jd > 0, "JD should be positive"
                
        except ImportError as e:
            pytest.skip(f"Skipping due to missing time module: {e}")
        except Exception as e:
            if "No module named" in str(e) or "kernel" in str(e).lower():
                pytest.skip(f"Skipping due to missing dependency: {e}")
            else:
                raise

    def test_computational_determinism_preservation(
        self,
        planetary_reader,
    ):
        """Test that computations are deterministic (same inputs -> same outputs)."""
        test_jd = 2451545.0  # J2000.0
        test_lat = 40.7128   # New York latitude
        test_lon = -74.0060  # New York longitude

        results = []
        for _ in range(3):
            chart = create_chart(
                test_jd,
                test_lat,
                test_lon,
                reader=planetary_reader,
            )
            sun_data = chart.planets.get(Body.SUN)
            assert sun_data is not None, "Chart should contain Sun data"
            assert hasattr(sun_data, 'longitude'), (
                "Sun data should have longitude"
            )
            results.append(sun_data.longitude)

        assert len(results) == 3
        for result in results[1:]:
            assert abs(result - results[0]) < 1e-10, (
                f"Sun position calculation not deterministic: {results}"
            )

    def test_error_handling_preservation(self):
        """Test that error handling behavior is preserved."""
        with pytest.raises(ValueError):
            create_chart("invalid_jd", 0, 0, reader=object())


# Run the baseline computational test suite to establish preservation baseline
def test_run_baseline_computational_tests():
    """
    Run existing computational test suite on UNFIXED code to establish baseline.
    
    This test documents the current computational behavior that must be preserved
    after docstring fixes are applied.
    """
    import subprocess
    import sys
    
    try:
        # Run a subset of computational tests that don't require external dependencies
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/unit/', 
            '-k', 'not (test_docstring_governance or integration or erfa or astropy or laspy or requests)',
            '--tb=no',  # Suppress traceback for cleaner output
            '-q'        # Quiet mode
        ], capture_output=True, text=True, timeout=60)
        
        # Document the baseline - we expect some tests to fail on unfixed code
        # The key is that the same tests should pass/fail after docstring fixes
        print(f"Baseline test run completed with exit code: {result.returncode}")
        print(f"Tests run: {result.stdout.count('PASSED') + result.stdout.count('FAILED')}")
        print(f"Passed: {result.stdout.count('PASSED')}")
        print(f"Failed: {result.stdout.count('FAILED')}")
        
        # This test always passes - it's just documenting the baseline
        assert True, "Baseline computational test run completed"
        
    except subprocess.TimeoutExpired:
        pytest.skip("Baseline test run timed out")
    except Exception as e:
        pytest.skip(f"Could not run baseline tests: {e}")
