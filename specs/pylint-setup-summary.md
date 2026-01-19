# Pylint Setup Summary

## What Was Added

Pylint has been successfully integrated into all projects in the monorepo.

### Changes Made

1. **Added pylint dependency** to all `pyproject.toml` files:
   - `/pyproject.toml` (root)
   - `/api/pyproject.toml`
   - `/cli/pyproject.toml`
   - `/mcp/pyproject.toml`

2. **Configured pylint settings** in each `pyproject.toml`:
   - Python version: 3.12
   - Max line length: 100 (matches ruff)
   - Parallel execution enabled (uses all CPU cores)
   - Sensible defaults with some strict checks disabled

3. **Created documentation**:
   - [docs/linting-guide.md](linting-guide.md) - Comprehensive guide
   - [docs/quick-lint-reference.md](quick-lint-reference.md) - Quick reference
   - This summary file

## Current Code Quality

**Initial Pylint Score: 8.76/10** ✅

This is a good score! The codebase follows best practices well.

## Configuration Overview

### Disabled Checks

These checks are disabled to reduce noise while maintaining code quality:

- `missing-module-docstring` - Not every module needs a docstring
- `missing-class-docstring` - Not every class needs a docstring
- `missing-function-docstring` - Not every function needs a docstring
- `too-few-public-methods` - Allows simple data classes
- `too-many-arguments` - Allows up to 8 arguments
- `too-many-instance-attributes` - Allows up to 12 attributes
- `fixme` - Allows TODO comments

### Enabled Checks (Pylint Default)

All other pylint checks are enabled, including:

- **Code quality**: Unused variables, imports, arguments
- **Best practices**: Proper exception handling, return consistency
- **Potential bugs**: Undefined variables, wrong types, logic errors
- **Naming conventions**: PEP 8 naming standards
- **Design patterns**: Code complexity, coupling, cohesion

## Quick Start

### Install Dependencies

```bash
# From repository root
pip install -e ".[dev]"

# Or for specific projects
pip install -e "api/[dev]"
pip install -e "cli/[dev]"
pip install -e "mcp/[dev]"
```

### Run Pylint

```bash
# Check entire API
pylint api/src/cadastral_api/

# Check entire CLI
pylint cli/src/cadastral_cli/

# Check entire MCP
pylint mcp/src/cadastral_mcp/

# Check everything
pylint api/src/cadastral_api/ cli/src/cadastral_cli/ mcp/src/cadastral_mcp/
```

### Common Workflows

**Before committing:**
```bash
# 1. Format and auto-fix
ruff format . && ruff check --fix .

# 2. Type check
mypy api/src cli/src mcp/src

# 3. Comprehensive lint
pylint api/src/cadastral_api cli/src/cadastral_cli mcp/src/cadastral_mcp

# 4. Run tests
pytest
```

**Quick check (fast):**
```bash
ruff check . && mypy api/src cli/src mcp/src
```

**Deep check (thorough):**
```bash
pylint api/src/cadastral_api cli/src/cadastral_cli mcp/src/cadastral_mcp
```

## Integration with Existing Tools

You already have `ruff` and `mypy` configured. Here's how they complement each other:

| Tool | Speed | Focus | When to Use |
|------|-------|-------|-------------|
| **Ruff** | ⚡ Very Fast | Formatting, imports, basic errors | Every save/commit |
| **Mypy** | 🏃 Fast | Type safety | Before commit |
| **Pylint** | 🐢 Slower | Code quality, best practices | Before PR, periodic |

## Next Steps

1. **Run initial check**: `pylint api/src/cadastral_api/`
2. **Review issues**: Focus on E (errors) and W (warnings) first
3. **Fix critical issues**: Address any E-level (error) findings
4. **Consider refinements**: Adjust disabled checks if needed
5. **Set up IDE integration**: Configure VS Code/PyCharm (see [linting-guide.md](linting-guide.md))
6. **Optional**: Set up pre-commit hooks for automatic checks

## Improving Your Score

Current: **8.76/10**

To reach **9.0+**:

1. Fix line-too-long issues (use shorter lines or break them)
2. Review and fix pydantic field type hints (E1101 errors)
3. Consider adding docstrings to public APIs
4. Review test fixture naming (W0621 warnings in tests)

To reach **9.5+**:

1. Add comprehensive docstrings
2. Refactor complex functions
3. Improve test coverage
4. Review all R (refactor) suggestions

## Customization

To adjust settings for your preferences, edit the `[tool.pylint]` sections in `pyproject.toml`:

```toml
[tool.pylint.messages_control]
disable = [
    "missing-module-docstring",
    # Add more here
]

[tool.pylint.design]
max-attributes = 15  # Increase if you have data-heavy classes
max-args = 10        # Increase if needed
```

## Support

- 📖 Full guide: [docs/linting-guide.md](linting-guide.md)
- ⚡ Quick reference: [docs/quick-lint-reference.md](quick-lint-reference.md)
- 🔗 Pylint docs: <https://pylint.readthedocs.io/>

## Summary

✅ Pylint successfully integrated into all projects
✅ Sensible defaults configured
✅ Works alongside ruff and mypy
✅ Current score: 8.76/10 (good!)
✅ Documentation created

Your codebase is in good shape. Pylint will help maintain and improve code quality as the project grows!
