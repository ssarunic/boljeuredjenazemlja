# Linting and Code Quality Guide

This project uses multiple tools to ensure code quality and consistency:

## Tools Overview

### 1. Ruff (Fast Python Linter)
- **Purpose**: Fast formatting and common error detection
- **Speed**: Extremely fast, written in Rust
- **Use for**: Quick checks, auto-formatting, import sorting

### 2. Mypy (Type Checker)
- **Purpose**: Static type checking
- **Use for**: Ensuring type safety and catching type-related bugs

### 3. Pylint (Comprehensive Linter)
- **Purpose**: In-depth code quality analysis and best practices
- **Use for**: Detecting code smells, enforcing coding standards, finding bugs

## Running Linters

### Individual Projects

Each project (api/, cli/, mcp/) can be linted independently:

```bash
# Navigate to project directory
cd api/

# Run all linters
ruff check src/
mypy src/
pylint src/

# Auto-fix ruff issues
ruff check --fix src/

# Format code
ruff format src/
```

### From Repository Root

Run linters across the entire monorepo:

```bash
# Ruff
ruff check api/src/ cli/src/ mcp/src/

# Mypy
mypy api/src/ cli/src/ mcp/src/

# Pylint
pylint api/src/cadastral_api/
pylint cli/src/cadastral_cli/
pylint mcp/src/cadastral_mcp/
```

### Run All Linters at Once

```bash
# Create a simple script or use this one-liner
ruff check api/src/ cli/src/ mcp/src/ && \
mypy api/src/ cli/src/ mcp/src/ && \
pylint api/src/cadastral_api/ cli/src/cadastral_cli/ mcp/src/cadastral_mcp/
```

## Pylint Configuration

Pylint is configured in each `pyproject.toml` with sensible defaults:

### Disabled Checks

The following checks are disabled to reduce noise while keeping best practices:

- **missing-*-docstring**: Not requiring docstrings everywhere (optional but recommended)
- **too-few-public-methods**: Allows data classes and simple classes
- **too-many-arguments**: Configured to allow up to 8 arguments
- **too-many-instance-attributes**: Configured to allow up to 12 attributes
- **fixme**: Allows TODO comments in code

### Key Settings

- **Max line length**: 100 characters (matches ruff)
- **Python version**: 3.12
- **Parallel execution**: Uses all available CPU cores
- **Good variable names**: `i`, `j`, `k`, `ex`, `_`, `id`, `ok`, `cli`

## Recommended Workflow

### Before Committing

```bash
# 1. Format code
ruff format .

# 2. Fix auto-fixable issues
ruff check --fix .

# 3. Run type checker
mypy api/src/ cli/src/ mcp/src/

# 4. Run comprehensive linting
pylint api/src/cadastral_api/ cli/src/cadastral_cli/ mcp/src/cadastral_mcp/

# 5. Run tests
pytest
```

### IDE Integration

#### VS Code

Install these extensions:
- **Ruff**: charliermarsh.ruff
- **Pylint**: ms-python.pylint
- **Mypy**: matangover.mypy

Add to `.vscode/settings.json`:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": true,
      "source.organizeImports.ruff": true
    }
  },
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.ruffEnabled": true
}
```

#### PyCharm

- Ruff: Install the Ruff plugin from marketplace
- Pylint: Configure in Settings → Tools → External Tools
- Mypy: Built-in support, enable in Settings → Editor → Inspections → Python → Type Checker

## Interpreting Results

### Ruff Output

```text
api/src/cadastral_api/client.py:45:10: F401 [*] `httpx.HTTPError` imported but unused
```

- `F401`: Error code (F = pyflakes)
- `[*]`: Auto-fixable with `--fix`

### Mypy Output

```text
api/src/cadastral_api/models.py:23: error: Argument 1 to "get" has incompatible type "str | None"; expected "str"
```

- Clear type mismatch errors with line numbers

### Pylint Output

```text
************* Module cadastral_api.client
api/src/cadastral_api/client.py:67:0: C0116: Missing function or method docstring (missing-function-docstring)
api/src/cadastral_api/client.py:89:8: W0612: Unused variable 'response' (unused-variable)
```
- Letter codes: C = convention, R = refactor, W = warning, E = error, F = fatal
- Detailed messages with suggestions

### Pylint Score

Pylint provides a score out of 10. Aim for:
- **9.0+**: Excellent
- **8.0-9.0**: Good
- **7.0-8.0**: Acceptable
- **<7.0**: Needs improvement

## Common Issues and Fixes

### Import Order (Ruff I001)
```python
# Bad
import click
from pathlib import Path
import httpx

# Good (standard lib, third-party, local)
from pathlib import Path

import click
import httpx

from cadastral_api import CadastralAPIClient
```

### Unused Imports (Ruff F401, Pylint W0611)
```python
# Bad
from typing import Optional, List  # List is unused

# Good
from typing import Optional
```

### Type Errors (Mypy)
```python
# Bad
def get_parcel(parcel_id: str | None) -> Parcel:
    return fetch_parcel(parcel_id)  # Error: parcel_id could be None

# Good
def get_parcel(parcel_id: str | None) -> Parcel:
    if parcel_id is None:
        raise ValueError("parcel_id cannot be None")
    return fetch_parcel(parcel_id)
```

### Line Length (Ruff E501, Pylint C0301)
```python
# Bad (>100 chars)
result = some_very_long_function_name(argument1, argument2, argument3, argument4, argument5, argument6)

# Good
result = some_very_long_function_name(
    argument1, argument2, argument3,
    argument4, argument5, argument6
)
```

## Customizing Configuration

To adjust pylint settings for your needs, edit `pyproject.toml`:

```toml
[tool.pylint.messages_control]
disable = [
    "missing-module-docstring",
    # Add more checks to disable
]

enable = [
    # Re-enable specific checks if needed
]

[tool.pylint.design]
max-attributes = 15  # Increase if needed
max-args = 10        # Increase if needed
```

## Pre-commit Hooks (Recommended)

Consider setting up pre-commit hooks to run these checks automatically:

```bash
pip install pre-commit
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0.0, httpx>=0.25.0]

  - repo: local
    hooks:
      - id: pylint
        name: pylint
        entry: pylint
        language: system
        types: [python]
```

Then:
```bash
pre-commit install
```

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Pylint Documentation](https://pylint.readthedocs.io/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
