"""
Oracle Validation Package — comprehensive external-oracle campaign for the
12 rewritten-pending-oracle functions in the Moira Swiss-lineage remediation.

Modules:
  - oracle_policy.py: tolerance matrices, test-case epochs, validation results vessel
  - horizons_oracle.py: JPL Horizons API client for reference ephemeris
  - test_oracle_validation.py: comprehensive test suite with internal and external checks

Usage:
  # Run internal consistency checks (no network required):
  pytest tests/oracle/test_oracle_validation.py -v

  # Run full JPL Horizons validation (requires network):
  pytest tests/oracle/test_oracle_validation.py::TestOracleHorizonsIntegration -v --network

Authority chain:
  1. JPL HORIZONS API (primary ephemeris)
  2. SOFA/ERFA (coordinate transforms)
  3. Moira internal consistency (fallback)
"""

__all__ = [
    "oracle_policy",
    "horizons_oracle",
    "test_oracle_validation",
]
