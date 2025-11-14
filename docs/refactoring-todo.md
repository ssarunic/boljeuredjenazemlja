# Cadastral API Monorepo Refactoring TODO

This checklist guides the refactoring of the current structure into a clean monorepo with separate projects.

**Status Legend:**
- [ ] Not started
- [x] Completed
- [~] In progress

---

## Phase 1: Create New Monorepo Structure (Foundation)

### 1.1 Create Top-Level Project Directories

- [ ] Create `api/` directory (Python SDK)
- [ ] Create `cli/` directory (CLI application)
- [ ] Create `mcp/` directory (MCP server)
- [ ] Rename `mock_server/` to `mock-server/` (kebab-case convention)

### 1.2 Create Standard Subdirectories for Each Project

**For `api/` project:**
- [ ] Create `api/src/`
- [ ] Create `api/tests/`
- [ ] Create `api/tests/unit/`
- [ ] Create `api/tests/integration/`
- [ ] Create `api/docs/`
- [ ] Create `api/examples/`

**For `cli/` project:**
- [ ] Create `cli/src/`
- [ ] Create `cli/tests/`
- [ ] Create `cli/docs/`

**For `mcp/` project:**
- [ ] Create `mcp/src/`
- [ ] Create `mcp/tests/`
- [ ] Create `mcp/docs/`

**For `mock-server/`:**
- [ ] Create `mock-server/src/`
- [ ] Create `mock-server/docs/`
- [ ] Keep `mock-server/data/` (already exists)

### 1.3 Create Repository-Level Directories

- [ ] Create root `docs/` (for repo-wide documentation)
- [ ] Keep root `scripts/` (for repo-wide scripts)
- [ ] Create `shared/` or `common/` (if needed for shared code)

---

## Phase 2: Move API (SDK) Code

### 2.1 Move Core API Code

**From `src/cadastral_api/` to `api/src/cadastral_api/`:**

- [ ] Move `src/cadastral_api/__init__.py` → `api/src/cadastral_api/`
- [ ] Move `src/cadastral_api/exceptions.py` → `api/src/cadastral_api/`
- [ ] Move `src/cadastral_api/i18n.py` → `api/src/cadastral_api/`
- [ ] Move `src/cadastral_api/client/` → `api/src/cadastral_api/client/`
- [ ] Move `src/cadastral_api/models/` → `api/src/cadastral_api/models/`
- [ ] Move `src/cadastral_api/gis/` → `api/src/cadastral_api/gis/`
- [ ] Move `src/cadastral_api/locale/` → `api/src/cadastral_api/locale/`

**Note:** Do NOT move `cli/` subdirectory yet - that goes to the CLI project.

### 2.2 Move API Tests

- [ ] Move `src/cadastral_api/tests/test_batch_input_parsers.py` → `api/tests/unit/`
- [ ] Move `src/cadastral_api/tests/test_batch_processor.py` → `api/tests/unit/`
- [ ] Move root `test_exception.py` → `api/tests/unit/test_exceptions.py`
- [ ] Move root `test_validation.py` → `api/tests/unit/test_validation.py`

### 2.3 Move API Examples

- [ ] Move `examples/basic_usage.py` → `api/examples/`
- [ ] Move `examples/municipality_search.py` → `api/examples/`
- [ ] Move `examples/gis_parcel_geometry.py` → `api/examples/`
- [ ] Move `examples/batch_parcels.csv` → `api/examples/`
- [ ] Move `examples/batch_parcels_ids.csv` → `api/examples/`

### 2.4 Move API Documentation

Project-specific docs go to `api/docs/`:
- [ ] Move `specs/Pydantic_Business_Entities_Implementation.md` → `api/docs/pydantic-entities-implementation.md` (rename)
- [ ] Create `api/docs/README.md` (API documentation index)
- [ ] Create `api/README.md` (API project README with quick start)

### 2.5 Create API Configuration

- [ ] Copy `pyproject.toml` → `api/pyproject.toml`
- [ ] Update `api/pyproject.toml` to include only API dependencies
- [ ] Remove CLI and MCP-specific dependencies from `api/pyproject.toml`
- [ ] Update package name in `api/pyproject.toml` if needed
- [ ] Update entry points in `api/pyproject.toml` (remove CLI entry)

---

## Phase 3: Move CLI Code

### 3.1 Move CLI Code

**From `src/cadastral_api/cli/` to `cli/src/cadastral_cli/`:**

- [ ] Move `src/cadastral_api/__main__.py` → `cli/src/cadastral_cli/`
- [ ] Move `src/cadastral_api/cli/` → `cli/src/cadastral_cli/`
- [ ] Rename package internally from `cadastral_api.cli` to `cadastral_cli`

**Files to move:**
- [ ] `cli/main.py` → `cli/src/cadastral_cli/main.py`
- [ ] `cli/formatters.py` → `cli/src/cadastral_cli/formatters.py`
- [ ] `cli/input_parsers.py` → `cli/src/cadastral_cli/input_parsers.py`
- [ ] `cli/batch_processor.py` → `cli/src/cadastral_cli/batch_processor.py`
- [ ] `cli/commands/` → `cli/src/cadastral_cli/commands/`

### 3.2 Update CLI Imports

**In all CLI files, update imports:**
- [ ] Change `from ...client import` → `from cadastral_api.client import`
- [ ] Change `from ...exceptions import` → `from cadastral_api.exceptions import`
- [ ] Change `from ...models import` → `from cadastral_api.models import`
- [ ] Change `from ...i18n import` → `from cadastral_api.i18n import`
- [ ] Update internal CLI imports to use `cadastral_cli` package

**Files to update:**
- [ ] `cli/src/cadastral_cli/main.py`
- [ ] `cli/src/cadastral_cli/formatters.py`
- [ ] `cli/src/cadastral_cli/input_parsers.py`
- [ ] `cli/src/cadastral_cli/batch_processor.py`
- [ ] `cli/src/cadastral_cli/commands/search.py`
- [ ] `cli/src/cadastral_cli/commands/parcel.py`
- [ ] `cli/src/cadastral_cli/commands/batch.py`
- [ ] `cli/src/cadastral_cli/commands/gis.py`
- [ ] `cli/src/cadastral_cli/commands/discovery.py`
- [ ] `cli/src/cadastral_cli/commands/cache.py`

### 3.3 Move CLI Tests

- [ ] Create `cli/tests/test_cli_commands.py` (new integration tests)
- [ ] Create `cli/tests/test_formatters.py` (new unit tests)

### 3.4 Move CLI Documentation

- [ ] Move `docs/CLI.md` → `cli/docs/command-reference.md` (rename)
- [ ] Create `cli/docs/README.md` (CLI documentation index)
- [ ] Create `cli/README.md` (CLI project README)

### 3.5 Create CLI Configuration

- [ ] Create `cli/pyproject.toml`
- [ ] Add `cadastral-api` as dependency in `cli/pyproject.toml`
- [ ] Configure CLI entry point: `cadastral = cadastral_cli.main:cli`
- [ ] Add CLI-specific dependencies (click, rich, etc.)

---

## Phase 4: Move MCP Code

### 4.1 Move MCP Code

**From `src/mcp/` to `mcp/src/cadastral_mcp/`:**

- [ ] Move `src/mcp/__init__.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/main.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/server.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/tools.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/resources.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/prompts.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/config.py` → `mcp/src/cadastral_mcp/`
- [ ] Move `src/mcp/http_server.py` → `mcp/src/cadastral_mcp/`

### 4.2 Update MCP Imports

**In all MCP files, update imports:**
- [ ] Change `from cadastral_api import` to explicit imports
- [ ] Update internal imports to use `cadastral_mcp` package
- [ ] Verify all imports work with new structure

### 4.3 Move MCP Documentation

- [ ] Move `docs/MCP_SERVER.md` → `mcp/docs/mcp-server.md` (rename)
- [ ] Move `src/mcp/README.md` → `mcp/docs/README.md`
- [ ] Create `mcp/README.md` (MCP project README)

### 4.4 Create MCP Configuration

- [ ] Create `mcp/pyproject.toml`
- [ ] Add `cadastral-api` as dependency in `mcp/pyproject.toml`
- [ ] Configure MCP entry point: `cadastral-mcp = cadastral_mcp.main:main`
- [ ] Add MCP-specific dependencies (fastmcp, uvicorn, etc.)

---

## Phase 5: Reorganize Mock Server

### 5.1 Rename and Reorganize Mock Server

- [ ] Rename `mock_server/` → `mock-server/` (if not already done)
- [ ] Move `mock_server/main.py` → `mock-server/src/main.py`
- [ ] Keep `mock-server/data/` as-is
- [ ] Add `.gitkeep` to `mock-server/data/geometry/` OR remove if unused

### 5.2 Move Mock Server Documentation

- [ ] Move `mock_server/README.md` → `mock-server/docs/README.md`
- [ ] Move `mock_server/QUICKSTART.md` → `mock-server/docs/QUICKSTART.md`
- [ ] Create `mock-server/README.md` (project README with usage)

### 5.3 Create Mock Server Configuration

- [ ] Move `mock_server/requirements.txt` → `mock-server/requirements.txt`
- [ ] Consider creating `mock-server/pyproject.toml` for consistency

---

## Phase 6: Organize Repository-Wide Resources

### 6.1 Organize Shared Documentation

**Keep in root `docs/` (applies to multiple projects):**
- [ ] Move/copy `specs/Croatian_Cadastral_API_Specification.md` → `docs/croatian-cadastral-api-specification.md`
- [ ] Create `docs/README.md` (documentation index)
- [ ] Create `docs/architecture.md` (monorepo architecture overview)
- [ ] Create `docs/contributing.md` (contribution guidelines)
- [ ] Create `docs/development-guide.md` (dev environment setup)

**Keep in `specs/` OR move to `docs/`:**
- [ ] Decide: Keep `specs/` or merge into `docs/`
- [ ] If keeping `specs/`, rename files to kebab-case:
  - [ ] `I18N_GUIDE.md` → `specs/i18n-guide.md`
  - [ ] `I18N_IMPLEMENTATION_STATUS.md` → `specs/i18n-implementation-status.md`
  - [ ] `TRANSLATION_STATUS.md` → `specs/translation-status.md`
  - [ ] `DOCUMENTATION_STRUCTURE.md` → `specs/documentation-structure.md`
  - [ ] `LOCALIZATION_EXAMPLE.py` → `specs/localization_example.py`

### 6.2 Organize Translation Files

**Decision needed: Where do translations live?**

**Option A: Shared in root** (if all projects use same translations)
- [ ] Keep `po/` in root
- [ ] Keep translation scripts in root `scripts/`
- [ ] Move `build_translations.py` → `scripts/build_translations.py`

**Option B: Per-project** (if different translations per project)
- [ ] Move `po/` → `api/po/` and `cli/po/`
- [ ] Move translation scripts to each project
- [ ] Update build scripts

**Recommendation**: Option A (shared) - translations are likely shared.

### 6.3 Organize Scripts

- [ ] Keep `scripts/` in root for repo-wide scripts
- [ ] Move `build_translations.py` → `scripts/build_translations.py`
- [ ] Keep `scripts/compile_translations.sh`
- [ ] Keep `scripts/generate_pot.sh`
- [ ] Keep `scripts/init_language.sh`
- [ ] Keep `scripts/update_translations.sh`
- [ ] Create `scripts/setup_all.sh` (setup all projects)
- [ ] Create `scripts/test_all.sh` (run all tests)

### 6.4 Clean Up Root Directory

**Remove old structure:**
- [ ] Remove `src/` directory (after moving all content)
- [ ] Remove `examples/` directory (after moving to `api/examples/`)
- [ ] Remove old empty directories

**Keep in root:**
- [ ] `README.md` (repository main README)
- [ ] `CLAUDE.md` (AI assistant instructions)
- [ ] `NAMING_CONVENTIONS.md` (this file)
- [ ] `REFACTORING_TODO.md` (this file)
- [ ] `.env.example`
- [ ] `.gitignore`
- [ ] `.vscode/` (if shared settings)
- [ ] `.claude/` (if shared settings)

**Remove from root:**
- [ ] Delete `test_exception.py` (moved to `api/tests/unit/`)
- [ ] Delete `test_validation.py` (moved to `api/tests/unit/`)
- [ ] Delete `debug_api_response.py` (move to `scripts/` or delete)
- [ ] Delete `messages.mo` (orphaned translation file)
- [ ] Delete `src/croatian_cadastral_api.egg-info/` (build artifact)

---

## Phase 7: Update Configuration Files

### 7.1 Update Root Configuration

**Update root `README.md`:**
- [ ] Update to reflect monorepo structure
- [ ] Add links to each project's README
- [ ] Explain overall architecture
- [ ] Update installation instructions

**Update `.gitignore`:**
- [ ] Update paths for new structure
- [ ] Add `*/build/`, `*/dist/`, `*/.egg-info/`
- [ ] Add `*/__pycache__/`, `*/.pytest_cache/`
- [ ] Verify all build artifacts are ignored

**Update `CLAUDE.md`:**
- [ ] Update project structure section
- [ ] Update file paths in examples
- [ ] Update cross-references to documentation

### 7.2 Create Project-Specific pyproject.toml Files

**For `api/pyproject.toml`:**
- [ ] Package name: `croatian-cadastral-api`
- [ ] Dependencies: Core SDK dependencies only
- [ ] No CLI entry point
- [ ] Export Python package: `cadastral_api`

**For `cli/pyproject.toml`:**
- [ ] Package name: `cadastral-cli`
- [ ] Dependencies: Include `cadastral-api`, `click`, `rich`
- [ ] Entry point: `cadastral = cadastral_cli.main:cli`
- [ ] Export Python package: `cadastral_cli`

**For `mcp/pyproject.toml`:**
- [ ] Package name: `cadastral-mcp-server`
- [ ] Dependencies: Include `cadastral-api`, `fastmcp`
- [ ] Entry point: `cadastral-mcp = cadastral_mcp.main:main`
- [ ] Export Python package: `cadastral_mcp`

### 7.3 Environment Configuration

**Update `.env.example`:**
- [ ] Verify it works for all projects
- [ ] Add project-specific sections if needed
- [ ] Document which projects use which variables

---

## Phase 8: Testing & Validation

### 8.1 Create Missing Tests

**API tests:**
- [ ] Create `api/tests/unit/test_api_client.py`
- [ ] Create `api/tests/unit/test_entities.py`
- [ ] Create `api/tests/unit/test_gis_parser.py`
- [ ] Create `api/tests/unit/test_gis_cache.py`
- [ ] Create `api/tests/integration/test_full_workflow.py`

**CLI tests:**
- [ ] Create `cli/tests/test_cli_commands.py`
- [ ] Create `cli/tests/test_formatters.py`
- [ ] Create `cli/tests/test_integration.py`

**MCP tests:**
- [ ] Create `mcp/tests/test_mcp_server.py`
- [ ] Create `mcp/tests/test_mcp_tools.py`

### 8.2 Verify Builds

- [ ] Build API package: `cd api && pip install -e .`
- [ ] Build CLI package: `cd cli && pip install -e .`
- [ ] Build MCP package: `cd mcp && pip install -e .`
- [ ] Verify all imports work
- [ ] Verify CLI commands work
- [ ] Verify MCP server starts

### 8.3 Run Tests

- [ ] Run API tests: `cd api && pytest`
- [ ] Run CLI tests: `cd cli && pytest`
- [ ] Run MCP tests: `cd mcp && pytest`
- [ ] Run mock server: `cd mock-server && python src/main.py`
- [ ] Verify all tests pass

---

## Phase 9: Git Setup (Final Step)

### 9.1 Prepare Git Repository

- [ ] Review all changes
- [ ] Verify `.gitignore` is complete
- [ ] Verify no sensitive data in repo
- [ ] Verify no unnecessary files (build artifacts, etc.)

### 9.2 Initialize Git

- [ ] `git init`
- [ ] `git add .`
- [ ] Review staged files: `git status`
- [ ] Create initial commit: `git commit -m "Initial commit: Monorepo structure with API, CLI, MCP, and mock server projects"`

### 9.3 Create Git Tags (Optional)

- [ ] Tag initial version: `git tag -a v0.1.0 -m "Initial monorepo structure"`
- [ ] Consider tagging per-project versions if needed

---

## Phase 10: Documentation Finalization

### 10.1 Update All READMEs

**Root `README.md`:**
- [ ] Overview of monorepo
- [ ] Links to each project
- [ ] Quick start for contributors
- [ ] Architecture overview

**`api/README.md`:**
- [ ] API package description
- [ ] Installation instructions
- [ ] Quick start examples
- [ ] Link to full docs

**`cli/README.md`:**
- [ ] CLI tool description
- [ ] Installation instructions
- [ ] Basic command examples
- [ ] Link to command reference

**`mcp/README.md`:**
- [ ] MCP server description
- [ ] Installation and setup
- [ ] Usage examples
- [ ] Link to protocol docs

**`mock-server/README.md`:**
- [ ] Mock server description
- [ ] How to run
- [ ] Available endpoints
- [ ] Test data info

### 10.2 Create Architecture Documentation

- [ ] Create `docs/architecture.md` with:
  - Monorepo structure diagram
  - Project dependencies
  - Data flow between projects
  - Deployment architecture

### 10.3 Create Contribution Guide

- [ ] Create `docs/contributing.md` with:
  - Development environment setup
  - Coding standards (link to NAMING_CONVENTIONS.md)
  - Testing requirements
  - Pull request process

---

## Priority Order

### Do First (Foundation):
1. **Phase 1**: Create new directory structure
2. **Phase 2**: Move API code (most critical)
3. **Phase 5**: Reorganize mock server (needed for testing)

### Then (Projects):
4. **Phase 3**: Move CLI code
5. **Phase 4**: Move MCP code

### Next (Organization):
6. **Phase 6**: Organize shared resources
7. **Phase 7**: Update configuration files

### Finally (Polish):
8. **Phase 8**: Testing & validation
9. **Phase 10**: Documentation finalization
10. **Phase 9**: Git initialization (very last step)

---

## Notes

- Use `git mv` when possible to preserve history
- Test after each major phase
- Update imports incrementally
- Keep backup before starting
- Can work on phases in parallel (API and CLI are independent)

---

**Status**: Not started
**Last Updated**: 2025-01-14
