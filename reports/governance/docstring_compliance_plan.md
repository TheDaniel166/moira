# Moira Docstring Governance Compliance Plan

## Scope
Fix docstring governance violations across the entire moira package (100+ Python files) to comply with HermitiCalc Docstring Governance standard.

## Violation Categories Identified
1. **MOD-001**: Missing module docstring (13 files)
2. **CLS-001**: Classes missing governance markers (619 classes)
3. **MC-005/006**: Wrong MACHINE_CONTRACT concurrency values (48 violations, 4 files)
4. **PARSE-001**: BOM encoding (false positive, now fixed) (0)

## Systematic Approach

### Phase 1: Module-Level Docstrings (MOD-001)
Target: 13 files missing proper module docstrings
- Audit each Python file for module-level docstring compliance
- Ensure all 5 required elements: Purpose, Boundary, Import-time side effects, External dependencies, Public surface

### Phase 2: Class Docstrings (CLS-001)  
Target: 619 classes missing governance markers
- Audit each class for RITE/THEOREM/RITE OF PURPOSE/LAW OF OPERATION structure
- Add missing MACHINE_CONTRACT v1 JSON blocks
- Apply canonical vocabulary (Engine, Guardian, Scribe, etc.)

### Phase 3: MACHINE_CONTRACT Fixes (MC-005/006)
Target: 48 violations in 4 files for concurrency values
- Fix incorrect concurrency values in MACHINE_CONTRACT blocks
- Ensure proper thread safety declarations

### Phase 4: Method Docstrings
- Audit non-trivial methods for proper docstring structure
- Ensure side effects, failure behavior, and concurrency contracts are declared

## Execution Strategy
1. Start with core/foundational files first
2. Process files in dependency order where possible
3. Batch similar violations together for efficiency
4. Validate compliance after each major batch

## Files to Process (Priority Order)
1. Core constants and utilities
2. Coordinate and time systems  
3. Planetary computation
4. Astrological engines (aspects, houses, etc.)
5. Specialized modules and subpackages

## Quality Gates
- Each file must pass docstring governance audit
- All classes must have proper RITE/THEOREM structure
- All MACHINE_CONTRACT blocks must be valid JSON with correct concurrency values
- Canonical vocabulary must be used throughout