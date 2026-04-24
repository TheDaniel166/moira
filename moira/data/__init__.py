"""
Moira — Data Package Guardian
Governs access to astronomical data files, catalogs, and reference datasets required for Moira's computational operations.

Boundary: owns data file organization and access patterns. Delegates actual data parsing and validation to specialized data modules.

Import-time side effects: None

External dependencies:
    - File system access for data file reading
    - Package resource management

Public surface:
    Package initialization and data module organization
"""

# moira/data/__init__.py
