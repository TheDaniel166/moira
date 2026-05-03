# Moira Export Policy

## Purpose

This document defines the canonical export policy for all Python modules in the Moira package. Every module must explicitly declare its public API surface through the `__all__` declaration.

## Why Export Governance?

1. **API Clarity**: Explicit declaration of what is public vs. internal
2. **Import Performance**: Reduces namespace pollution and import overhead
3. **Architectural Visibility**: Makes module boundaries and responsibilities clear
4. **Maintenance**: Easier to identify breaking changes and refactor safely

## Core Principle

**Every module must have an `__all__` declaration that explicitly lists its public exports.**

## Module Categories

Moira modules are categorized based on their architectural role, and each category has specific export rules.

### 1. Engine Modules (Core Computation)

**Examples**: `aspects.py`, `houses.py`, `chart.py`

**Export Rule**: Export all public classes, functions, constants, and type aliases.

```python
# moira/aspects.py
__all__ = [
    "CANONICAL_ASPECTS",      # Constant
    "AspectData",             # Dataclass
    "find_aspects",           # Function
    "calculate_orb",          # Function
]

CANONICAL_ASPECTS = {...}

@dataclass
class AspectData:
    ...

def find_aspects(...):
    ...

def calculate_orb(...):
    ...

def _internal_helper(...):  # NOT exported (private)
    ...
```

**What to Export**:
- ✅ All public classes (no leading underscore)
- ✅ All public functions
- ✅ All uppercase constants
- ✅ All public type aliases
- ✅ Enums, dataclasses, Protocols

**What NOT to Export**:
- ❌ Private symbols (leading underscore)
- ❌ Imported symbols (unless re-exporting intentionally)

### 2. Facade Modules (Re-exports)

**Examples**: `facade.py`, `essentials.py`, `classical.py`

**Export Rule**: Re-export all imported symbols that form the public surface.

```python
# moira/facade.py
from moira.aspects import AspectData, find_aspects
from moira.houses import HouseSystem, calculate_houses
from moira.chart import Chart

__all__ = [
    "AspectData",
    "find_aspects",
    "HouseSystem",
    "calculate_houses",
    "Chart",
]
```

**What to Export**:
- ✅ All imported symbols intended for public use
- ✅ Any symbols defined in the facade itself

**Alignment Rule**: Facade exports must match what is imported from delegate modules.

### 3. Constants Modules

**Examples**: `constants.py`, `*_constants.py`

**Export Rule**: Export all uppercase identifiers and Enum classes.

```python
# moira/constants.py
__all__ = [
    "CANONICAL_PLANETS",
    "CANONICAL_SIGNS",
    "DEFAULT_ORB",
    "AspectType",  # Enum
]

CANONICAL_PLANETS = [...]
CANONICAL_SIGNS = [...]
DEFAULT_ORB = 8.0

class AspectType(Enum):
    MAJOR = "major"
    MINOR = "minor"

def _compute_default():  # NOT exported (helper)
    ...
```

### 4. Types Modules

**Examples**: `*_types.py`, `types.py`

**Export Rule**: Export all dataclasses, TypedDicts, Protocols, and type aliases.

```python
# moira/chart_types.py
from typing import Protocol, TypedDict
from dataclasses import dataclass

__all__ = [
    "ChartData",      # Dataclass
    "ChartConfig",    # TypedDict
    "ChartRenderer",  # Protocol
    "ChartType",      # Type alias
]

@dataclass
class ChartData:
    ...

class ChartConfig(TypedDict):
    ...

class ChartRenderer(Protocol):
    ...

ChartType = Chart | NatalChart | TransitChart
```

### 5. Package `__init__.py` Files

**Export Rule**: Export symbols intended for package-level import.

```python
# moira/__init__.py
from moira.facade import Chart, AspectData, find_aspects

__all__ = [
    "Chart",
    "AspectData",
    "find_aspects",
]
```

**Alignment**: Package init exports should align with the primary facade module.

### 6. Private Modules

**Examples**: `_internal.py`, `_helpers.py`

**Export Rule**: Minimal or no exports. Private modules are implementation details.

```python
# moira/_internal.py
__all__ = []  # Or minimal exports if needed by other internal modules
```

### 7. Test Modules

**Examples**: `test_*.py`, `*_test.py`

**Export Rule**: No exports required. Test modules are not part of the public API.

## Decision Tree

```
Is the symbol name starting with underscore?
├─ YES → Do NOT export (private)
└─ NO → Continue...

What is the module category?
├─ ENGINE → Export if: class, function, constant, or type alias
├─ FACADE → Export if: imported from delegate module
├─ CONSTANTS → Export if: uppercase identifier or Enum
├─ TYPES → Export if: dataclass, TypedDict, Protocol, or type alias
├─ PACKAGE_INIT → Export if: intended for package-level import
├─ PRIVATE → Do NOT export (minimal exports only)
└─ TEST → No exports required
```

## Common Mistakes

### ❌ Mistake 1: Exporting Private Symbols

```python
# WRONG
__all__ = ["MyClass", "_internal_helper"]  # Private symbol exported!
```

**Fix**: Remove private symbols from `__all__`.

### ❌ Mistake 2: Missing Public Classes

```python
# WRONG - PublicClass2 is missing
__all__ = ["PublicClass1"]

class PublicClass1:
    ...

class PublicClass2:  # Should be in __all__!
    ...
```

**Fix**: Add all public classes to `__all__`.

### ❌ Mistake 3: Undefined Symbols in `__all__`

```python
# WRONG
__all__ = ["MyClass", "NonExistent"]  # NonExistent doesn't exist!

class MyClass:
    ...
```

**Fix**: Only include symbols that are actually defined or imported.

### ❌ Mistake 4: Incomplete Facade

```python
# WRONG - missing find_aspects
from moira.aspects import AspectData, find_aspects

__all__ = ["AspectData"]  # find_aspects not re-exported!
```

**Fix**: Re-export all imported symbols in facade modules.

## Validation

Use the governance tooling to validate your `__all__` declarations:

```bash
# Validate a single module
python scripts/moira-validate-exports.py --pattern "aspects.py"

# Validate entire package
python scripts/moira-validate-exports.py

# Strict mode (warnings become errors)
python scripts/moira-validate-exports.py --strict
```

## Rationale

### Why Explicit Over Implicit?

Python allows implicit exports (everything without a leading underscore is importable), but explicit `__all__` declarations provide:

1. **Clear Intent**: Developers know exactly what is public
2. **Refactoring Safety**: Internal changes don't accidentally break users
3. **Documentation**: `__all__` serves as inline API documentation
4. **Tooling Support**: IDEs and linters can provide better autocomplete and warnings

### Why Category-Specific Rules?

Different module types serve different architectural roles:

- **Engine modules** own their logic → export their public interface
- **Facade modules** aggregate functionality → re-export from delegates
- **Constants modules** provide configuration → export all constants
- **Types modules** define contracts → export all type definitions

Category-specific rules ensure governance aligns with architectural intent.

## Enforcement

Export governance is enforced through:

1. **Validation CLI**: `moira-validate-exports.py` checks compliance
2. **CI/CD Integration**: Automated validation on pull requests
3. **Pre-commit Hooks**: Validate before committing changes
4. **Code Review**: Reviewers check `__all__` declarations

## Exemptions

Modules may be exempted from governance requirements with documented rationale:

```toml
# pyproject.toml
[tool.moira.export_governance]
exemptions = [
    {module = "moira/_internal.py", reason = "Private implementation"},
]
```

Exemptions should be rare and well-justified.

## Summary

- ✅ Every module must have `__all__`
- ✅ Export all public symbols appropriate for the module category
- ❌ Never export private symbols (leading underscore)
- ❌ Never export undefined symbols
- ✅ Facade modules must re-export all imports
- ✅ Use validation tooling to ensure compliance

For questions or clarifications, refer to the governance tooling documentation or consult the maintainers.
