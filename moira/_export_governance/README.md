# Moira Export Governance System

Comprehensive tooling for managing `__all__` declarations across the Moira codebase.

## Overview

The Export Governance System ensures every Python module in Moira explicitly declares its public API surface through `__all__` declarations. This provides:

- **API Clarity**: Clear distinction between public and internal interfaces
- **Import Performance**: Reduced namespace pollution
- **Architectural Visibility**: Explicit module boundaries
- **Maintenance Safety**: Easier refactoring and breaking change detection

## Quick Start

### Validate Your Code

```bash
# Validate entire package
python scripts/moira-validate-exports.py

# Validate specific modules
python scripts/moira-validate-exports.py --pattern "houses*.py"

# Strict mode (warnings become errors)
python scripts/moira-validate-exports.py --strict

# Generate report
python scripts/moira-validate-exports.py --output report.json --format json
```

### Check Audit Progress

```bash
# Show governance coverage
python scripts/moira-audit-exports.py --show-progress
```

## Components

### 1. Module Scanner (`scanner.py`)
- Recursively discovers Python modules
- Categorizes modules (ENGINE, FACADE, CONSTANTS, TYPES, etc.)
- Supports pattern-based filtering

### 2. AST Parser (`parser.py`)
- Extracts symbol definitions from Python source
- Parses existing `__all__` declarations
- Tracks import statements for facade analysis

### 3. Symbol Classifier (`classifier.py`)
- Classifies symbols as public/private
- Applies category-specific classification rules
- Determines export eligibility

### 4. Policy Engine (`policy.py`)
- Defines export rules for each module category
- Generates export recommendations
- Validates existing `__all__` declarations

### 5. Validation Engine (`validator.py`)
- Validates modules and packages
- Supports strict and report modes
- Generates violation summaries

### 6. Report Generator (`reporter.py`)
- Produces reports in JSON, Markdown, and HTML formats
- Generates coverage statistics
- Summarizes violations by severity and rule

### 7. Audit Log (`audit_log.py`)
- Tracks audit progress
- Supports workflow resumption
- Calculates governance coverage

## Module Categories

### Engine Modules
Core computational modules that own their logic.

**Export**: All public classes, functions, constants, type aliases

```python
__all__ = ["MyClass", "my_function", "MY_CONSTANT"]
```

### Facade Modules
Modules that re-export symbols from other modules.

**Export**: All imported symbols intended for public use

```python
from moira.aspects import AspectData
__all__ = ["AspectData"]
```

### Constants Modules
Modules containing configuration and constants.

**Export**: All uppercase identifiers and Enums

```python
__all__ = ["MY_CONSTANT", "MyEnum"]
```

### Types Modules
Modules defining type contracts.

**Export**: All dataclasses, TypedDicts, Protocols, type aliases

```python
__all__ = ["MyDataClass", "MyProtocol", "MyType"]
```

## Validation Rules

### Rule: NO_PRIVATE_SYMBOLS
Private symbols (leading underscore) must not be in `__all__`.

**Severity**: ERROR

### Rule: SYMBOL_MUST_EXIST
All symbols in `__all__` must be defined or imported.

**Severity**: ERROR

### Rule: MISSING_PUBLIC_CLASS
All public classes should be in `__all__` (ENGINE modules).

**Severity**: WARNING

### Rule: MISSING_PUBLIC_FUNCTION
All public functions should be in `__all__` (ENGINE modules).

**Severity**: WARNING

### Rule: INCOMPLETE_FACADE
Facade modules should re-export all imported symbols.

**Severity**: WARNING

## CLI Tools

### moira-validate-exports.py

Validates `__all__` declarations across the package.

**Options**:
- `--strict`: Enable strict mode (warnings → errors)
- `--fail-on-warning`: Exit with error if warnings found
- `--pattern PATTERN`: Filter modules by glob pattern
- `--output PATH`: Write report to file
- `--format {text,json,markdown}`: Output format

**Exit Codes**:
- `0`: Validation passed
- `1`: Validation failed (errors found)

### moira-audit-exports.py

Manages audit workflow and progress tracking.

**Options**:
- `--show-progress`: Display coverage statistics
- `--pattern PATTERN`: Filter modules
- `--resume`: Resume from last audited module

## Python API

### Validate a Module

```python
from pathlib import Path
from moira._export_governance.validator import ValidationEngine

validator = ValidationEngine(Path("moira"))
result = validator.validate_module(Path("moira/aspects.py"))

if result.is_valid:
    print("✓ Module is valid")
else:
    for violation in result.violations:
        print(f"✗ {violation.message}")
```

### Generate Recommendations

```python
from moira._export_governance.scanner import ModuleScanner
from moira._export_governance.parser import ModuleParser
from moira._export_governance.policy import ExportPolicyEngine

scanner = ModuleScanner(Path("moira"))
parser = ModuleParser()
policy = ExportPolicyEngine()
policy.load_policy()

# Parse module
parsed = parser.parse_module(Path("moira/aspects.py"))
category = scanner.categorize_module(Path("moira/aspects.py"))

# Get recommendations
recommended = policy.recommend_exports(
    parsed.symbols,
    category,
    parsed.all_declaration
)

print(f"Recommended exports: {recommended}")
```

### Track Audit Progress

```python
from pathlib import Path
from moira._export_governance.audit_log import AuditLog

log = AuditLog(Path(".kiro/specs/moira-export-governance/audit-log.json"))

# Get progress
summary = log.get_progress_summary()
print(f"Coverage: {summary['coverage_percentage']}%")
print(f"Audited: {summary['audited']}/{summary['total_modules']}")
```

## Testing

Run the test suite:

```bash
# All tests
pytest tests/export_governance/ -v

# Specific component
pytest tests/export_governance/test_validator.py -v

# With coverage
pytest tests/export_governance/ --cov=moira/_export_governance
```

## Configuration

Configure governance in `pyproject.toml`:

```toml
[tool.moira.export_governance]
# Validation mode: "strict" or "report"
mode = "report"

# Fail on warnings in CI
fail_on_warning = false

# Exempted modules
exemptions = [
    {module = "moira/_internal.py", reason = "Private implementation"},
]

# Module category overrides
category_overrides = {
    "moira/facade.py" = "facade",
}
```

## Documentation

- **Export Policy**: `moira/docs/EXPORT_POLICY.md` - Canonical policy rules
- **Design Document**: `.kiro/specs/moira-export-governance/design.md`
- **Requirements**: `.kiro/specs/moira-export-governance/requirements.md`
- **Tasks**: `.kiro/specs/moira-export-governance/tasks.md`

## Architecture

```
moira/_export_governance/
├── models.py          # Data models and enums
├── scanner.py         # Module discovery
├── parser.py          # AST parsing
├── classifier.py      # Symbol classification
├── policy.py          # Policy engine
├── validator.py       # Validation engine
├── reporter.py        # Report generation
└── audit_log.py       # Audit tracking

scripts/
├── moira-validate-exports.py  # Validation CLI
└── moira-audit-exports.py     # Audit CLI
```

## Development

### Adding New Validation Rules

1. Define rule in `policy.py`:
```python
def _check_my_rule(self, current_all, symbols):
    violations = []
    # Check logic here
    return violations
```

2. Add to `validate_exports()` method
3. Add tests in `tests/export_governance/test_policy.py`

### Adding New Module Categories

1. Add enum value to `ModuleCategory` in `models.py`
2. Add categorization logic in `scanner.py`
3. Add policy rules in `policy.py`
4. Add classification rules in `classifier.py`
5. Add tests

## Troubleshooting

### "Module not found" errors
Ensure you're running from the repository root and the virtual environment is activated.

### Parse errors
Check for syntax errors in the module. The parser will report specific issues.

### Unexpected violations
Review the export policy documentation and ensure your `__all__` follows the rules for your module category.

## Contributing

When adding new modules to Moira:

1. Include `__all__` declaration
2. Follow category-specific export rules
3. Run validation before committing
4. Update audit log if needed

## License

Part of the Moira project. See main LICENSE file.
