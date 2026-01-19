# Quick Linting Reference

## One-Line Commands

### Check Everything
```bash
# From repository root
ruff check . && mypy api/src cli/src mcp/src && pylint api/src/cadastral_api cli/src/cadastral_cli mcp/src/cadastral_mcp
```

### Auto-Fix What You Can
```bash
# Format code
ruff format .

# Fix auto-fixable issues
ruff check --fix .
```

### Check Specific Project
```bash
# API
cd api && ruff check src/ && mypy src/ && pylint src/cadastral_api

# CLI
cd cli && ruff check src/ && mypy src/ && pylint src/cadastral_cli

# MCP
cd mcp && ruff check src/ && mypy src/ && pylint src/cadastral_mcp
```

## Common Pylint Disables

Sometimes you need to disable specific checks for valid reasons:

```python
# Disable for a single line
result = some_function()  # pylint: disable=broad-exception-caught

# Disable for a block
# pylint: disable=too-many-locals
def complex_function():
    var1 = 1
    var2 = 2
    # ... many variables
# pylint: enable=too-many-locals

# Disable for entire file (at top of file)
# pylint: disable=missing-module-docstring
```

## Error Code Quick Reference

### Ruff
- **F**: pyflakes (imports, undefined names)
- **E**: pycodestyle errors (syntax, indentation)
- **W**: pycodestyle warnings
- **I**: isort (import ordering)
- **N**: pep8-naming (naming conventions)

### Pylint
- **C**: Convention (style violations)
- **R**: Refactor (code smells)
- **W**: Warning (potential issues)
- **E**: Error (probable bugs)
- **F**: Fatal (prevents further processing)

### Common Issues

| Code | Tool | Description | Fix |
|------|------|-------------|-----|
| F401 | Ruff | Unused import | Remove the import |
| E501 | Ruff | Line too long | Break into multiple lines |
| I001 | Ruff | Import order | Run `ruff check --fix` |
| C0301 | Pylint | Line too long | Break into multiple lines |
| W0611 | Pylint | Unused import | Remove the import |
| W0621 | Pylint | Redefining name | Rename variable |
| E1101 | Pylint | No member | Check type annotations |

## Ignore Files

Create `.pylintrc` or add to `pyproject.toml` to ignore certain files:

```toml
[tool.pylint.main]
ignore-paths = [
    "tests/.*",
    "docs/.*",
    ".*/migrations/.*"
]
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Lint with ruff
  run: ruff check .

- name: Type check with mypy
  run: mypy api/src cli/src mcp/src

- name: Lint with pylint
  run: |
    pylint api/src/cadastral_api
    pylint cli/src/cadastral_cli
    pylint mcp/src/cadastral_mcp
```

## Score Interpretation

### Pylint Score
- **10.0**: Perfect (rare in real projects)
- **9.5+**: Excellent code quality
- **8.0-9.5**: Good, production-ready
- **7.0-8.0**: Acceptable, some cleanup needed
- **<7.0**: Needs significant improvements

### Mypy Output
- **Success**: No type errors found
- **note**: Informational messages
- **error**: Type mismatches that need fixing

### Ruff
- **No output**: All checks passed
- **With [*]**: Auto-fixable with `--fix`
- **Without [*]**: Requires manual intervention
