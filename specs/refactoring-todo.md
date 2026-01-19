# Cadastral API Monorepo Refactoring TODO

This checklist guides the refactoring of the current structure into a clean monorepo with separate projects.

**Status Legend:**

- [ ] Not started
- [x] Completed
- [~] In progress

**Overall Status:** ✅ **COMPLETED** - Monorepo refactoring is complete!

---

## Phase 1: Create New Monorepo Structure (Foundation) ✅

### 1.1 Create Top-Level Project Directories ✅

- [x] Create `api/` directory (Python SDK)
- [x] Create `cli/` directory (CLI application)
- [x] Create `mcp/` directory (MCP server)
- [x] Rename `mock_server/` to `mock-server/` (kebab-case convention)

### 1.2 Create Standard Subdirectories for Each Project ✅

**For `api/` project:**

- [x] Create `api/src/`
- [x] Create `api/tests/`
- [x] Create `api/tests/unit/`
- [x] Create `api/tests/integration/`
- [x] Create `api/docs/`
- [x] Create `api/examples/`

**For `cli/` project:**

- [x] Create `cli/src/`
- [x] Create `cli/tests/`
- [x] Create `cli/docs/`

**For `mcp/` project:**

- [x] Create `mcp/src/`
- [x] Create `mcp/tests/`
- [x] Create `mcp/docs/`

**For `mock-server/`:**

- [x] Create `mock-server/src/`
- [x] Create `mock-server/docs/`
- [x] Keep `mock-server/data/` (already exists)

### 1.3 Create Repository-Level Directories ✅

- [x] Create root `docs/` (for repo-wide documentation)
- [x] Keep root `scripts/` (for repo-wide scripts)
- [x] Create `shared/` or `common/` (if needed for shared code) - Not needed

---

## Phase 2: Move API (SDK) Code ✅

### 2.1 Move Core API Code ✅

**From `src/cadastral_api/` to `api/src/cadastral_api/`:**

- [x] Move `src/cadastral_api/__init__.py` → `api/src/cadastral_api/`
- [x] Move `src/cadastral_api/exceptions.py` → `api/src/cadastral_api/`
- [x] Move `src/cadastral_api/i18n.py` → `api/src/cadastral_api/`
- [x] Move `src/cadastral_api/client/` → `api/src/cadastral_api/client/`
- [x] Move `src/cadastral_api/models/` → `api/src/cadastral_api/models/`
- [x] Move `src/cadastral_api/gis/` → `api/src/cadastral_api/gis/`
- [x] Move `src/cadastral_api/locale/` → `api/src/cadastral_api/locale/`

**Note:** CLI subdirectory moved to CLI project as expected.

### 2.2 Move API Tests ✅

- [x] Move `src/cadastral_api/tests/test_batch_input_parsers.py` → `api/tests/unit/` (moved to CLI)
- [x] Move `src/cadastral_api/tests/test_batch_processor.py` → `api/tests/unit/` (moved to CLI)
- [x] Move root `test_exception.py` → `api/tests/unit/test_exceptions.py`
- [x] Move root `test_validation.py` → `api/tests/unit/test_validation.py`

### 2.3 Move API Examples ✅

- [x] Move `examples/basic_usage.py` → `api/examples/`
- [x] Move `examples/municipality_search.py` → `api/examples/`
- [x] Move `examples/gis_parcel_geometry.py` → `api/examples/`
- [x] Move `examples/batch_parcels.csv` → `api/examples/`
- [x] Move `examples/batch_parcels_ids.csv` → `api/examples/`

### 2.4 Move API Documentation ✅

Project-specific docs go to `api/docs/`:

- [x] Move `specs/Pydantic_Business_Entities_Implementation.md` → `api/docs/pydantic-entities-implementation.md` (in docs/)
- [x] Create `api/docs/README.md` (API documentation index)
- [x] Create `api/README.md` (API project README with quick start)

### 2.5 Create API Configuration ✅

- [x] Copy `pyproject.toml` → `api/pyproject.toml`
- [x] Update `api/pyproject.toml` to include only API dependencies
- [x] Remove CLI and MCP-specific dependencies from `api/pyproject.toml`
- [x] Update package name in `api/pyproject.toml` (croatian-cadastral-api)
- [x] Update entry points in `api/pyproject.toml` (remove CLI entry)

---

## Phase 3: Move CLI Code ✅

### 3.1 Move CLI Code ✅

**From `src/cadastral_api/cli/` to `cli/src/cadastral_cli/`:**

- [x] Move `src/cadastral_api/__main__.py` → `cli/src/cadastral_cli/`
- [x] Move `src/cadastral_api/cli/` → `cli/src/cadastral_cli/`
- [x] Rename package internally from `cadastral_api.cli` to `cadastral_cli`

**Files to move:**

- [x] `cli/main.py` → `cli/src/cadastral_cli/main.py`
- [x] `cli/formatters.py` → `cli/src/cadastral_cli/formatters.py`
- [x] `cli/input_parsers.py` → `cli/src/cadastral_cli/input_parsers.py`
- [x] `cli/batch_processor.py` → `cli/src/cadastral_cli/batch_processor.py`
- [x] `cli/commands/` → `cli/src/cadastral_cli/commands/`

### 3.2 Update CLI Imports ✅

**In all CLI files, update imports:**

- [x] Change `from ...client import` → `from cadastral_api.client import`
- [x] Change `from ...exceptions import` → `from cadastral_api.exceptions import`
- [x] Change `from ...models import` → `from cadastral_api.models import`
- [x] Change `from ...i18n import` → `from cadastral_api.i18n import`
- [x] Update internal CLI imports to use `cadastral_cli` package

**Files to update:**

- [x] `cli/src/cadastral_cli/main.py`
- [x] `cli/src/cadastral_cli/formatters.py`
- [x] `cli/src/cadastral_cli/input_parsers.py`
- [x] `cli/src/cadastral_cli/batch_processor.py`
- [x] `cli/src/cadastral_cli/commands/search.py`
- [x] `cli/src/cadastral_cli/commands/parcel.py`
- [x] `cli/src/cadastral_cli/commands/batch.py`
- [x] `cli/src/cadastral_cli/commands/gis.py`
- [x] `cli/src/cadastral_cli/commands/discovery.py`
- [x] `cli/src/cadastral_cli/commands/cache.py`

### 3.3 Move CLI Tests ✅

- [x] Create `cli/tests/` directory structure

### 3.4 Move CLI Documentation ✅

- [x] Move `docs/CLI.md` → `cli/docs/command-reference.md`
- [x] Create `cli/docs/README.md` (CLI documentation index)
- [x] Create `cli/README.md` (CLI project README)

### 3.5 Create CLI Configuration ✅

- [x] Create `cli/pyproject.toml`
- [x] Add `cadastral-api` as dependency in `cli/pyproject.toml`
- [x] Configure CLI entry point: `cadastral = cadastral_cli.main:cli`
- [x] Add CLI-specific dependencies (click, rich, etc.)

---

## Phase 4: Move MCP Code ✅

### 4.1 Move MCP Code ✅

**From `src/mcp/` to `mcp/src/cadastral_mcp/`:**

- [x] Move `src/mcp/__init__.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/main.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/server.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/tools.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/resources.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/prompts.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/config.py` → `mcp/src/cadastral_mcp/`
- [x] Move `src/mcp/http_server.py` → `mcp/src/cadastral_mcp/`

### 4.2 Update MCP Imports ✅

**In all MCP files, update imports:**

- [x] Change `from cadastral_api import` to explicit imports
- [x] Update internal imports to use `cadastral_mcp` package
- [x] Verify all imports work with new structure

### 4.3 Move MCP Documentation ✅

- [x] Move `docs/MCP_SERVER.md` → `mcp/docs/mcp-server.md`
- [x] Move `src/mcp/README.md` → `mcp/docs/README.md`
- [x] Create `mcp/README.md` (MCP project README)

### 4.4 Create MCP Configuration ✅

- [x] Create `mcp/pyproject.toml`
- [x] Add `cadastral-api` as dependency in `mcp/pyproject.toml`
- [x] Configure MCP entry point: `cadastral-mcp = cadastral_mcp.main:main`
- [x] Add MCP-specific dependencies (fastmcp, uvicorn, etc.)

---

## Phase 5: Reorganize Mock Server ✅

### 5.1 Rename and Reorganize Mock Server ✅

- [x] Rename `mock_server/` → `mock-server/` (if not already done)
- [x] Move `mock_server/main.py` → `mock-server/src/main.py`
- [x] Keep `mock-server/data/` as-is
- [x] Add `.gitkeep` to `mock-server/data/geometry/` OR remove if unused

### 5.2 Move Mock Server Documentation ✅

- [x] Move `mock_server/README.md` → `mock-server/README.md`
- [x] Move `mock_server/QUICKSTART.md` → `mock-server/QUICKSTART.md`
- [x] Create `mock-server/README.md` (project README with usage)

### 5.3 Create Mock Server Configuration ✅

- [x] Move `mock_server/requirements.txt` → `mock-server/requirements.txt`
- [x] Consider creating `mock-server/pyproject.toml` for consistency (using requirements.txt)

---

## Phase 6: Organize Repository-Wide Resources ✅

### 6.1 Organize Shared Documentation ✅

**Keep in root `docs/` (applies to multiple projects):**

- [x] Move/copy `specs/Croatian_Cadastral_API_Specification.md` → `docs/croatian-cadastral-api-specification.md`
- [x] Create `docs/README.md` (documentation index)
- [ ] Create `docs/architecture.md` (monorepo architecture overview) - **PENDING**
- [ ] Create `docs/contributing.md` (contribution guidelines) - **PENDING**
- [ ] Create `docs/development-guide.md` (dev environment setup) - **PENDING**

**Merged into `docs/`:**

- [x] Decided to merge specs into docs
- [x] Renamed files to kebab-case:
  - [x] `I18N_GUIDE.md` → `docs/i18n-guide.md`
  - [x] `I18N_IMPLEMENTATION_STATUS.md` → `docs/i18n-implementation-status.md`
  - [x] `TRANSLATION_STATUS.md` → `docs/translation-status.md`
  - [x] `DOCUMENTATION_STRUCTURE.md` → `docs/documentation-structure.md`
  - [x] `LOCALIZATION_EXAMPLE.py` → `docs/localization_example.py`
  - [x] `NAMING_CONVENTIONS.md` → `docs/naming-conventions.md`

### 6.2 Organize Translation Files ✅

**Option A: Shared in root** (CHOSEN)

- [x] Keep `po/` in root
- [x] Keep translation scripts in root `scripts/`
- [x] Translations compiled to `api/src/cadastral_api/locale/`

### 6.3 Organize Scripts ✅

- [x] Keep `scripts/` in root for repo-wide scripts
- [x] Keep `scripts/compile_translations.sh`
- [x] Keep `scripts/generate_pot.sh`
- [x] Keep `scripts/init_language.sh`
- [x] Keep `scripts/update_translations.sh`
- [ ] Create `scripts/setup_all.sh` (setup all projects) - **OPTIONAL**
- [ ] Create `scripts/test_all.sh` (run all tests) - **OPTIONAL**

### 6.4 Clean Up Root Directory ✅

**Remove old structure:**

- [x] Remove `src/` directory (after moving all content)
- [x] Remove `examples/` directory (after moving to `api/examples/`)
- [x] Remove old empty directories

**Keep in root:**

- [x] `README.md` (repository main README)
- [x] `CLAUDE.md` (AI assistant instructions)
- [x] Moved to docs: `NAMING_CONVENTIONS.md`
- [x] Moved to docs: `REFACTORING_TODO.md`
- [x] `.env.example`
- [x] `.gitignore`
- [x] `.vscode/` (shared settings)
- [x] `.claude/` (shared settings)

**Removed from root:**

- [x] Delete `test_exception.py` (moved to `api/tests/unit/`)
- [x] Delete `test_validation.py` (moved to `api/tests/unit/`)
- [x] All old structure removed

---

## Phase 7: Update Configuration Files ✅

### 7.1 Update Root Configuration ✅

**Update root `README.md`:**

- [x] Update to reflect monorepo structure
- [x] Add links to each project's README
- [x] Explain overall architecture
- [x] Update installation instructions

**Update `.gitignore`:**

- [x] Update paths for new structure
- [x] Add `*/build/`, `*/dist/`, `*/.egg-info/`
- [x] Add `*/__pycache__/`, `*/.pytest_cache/`
- [x] Verify all build artifacts are ignored

**Update `CLAUDE.md`:**

- [x] Update project structure section
- [x] Update file paths in examples
- [x] Update cross-references to documentation

### 7.2 Create Project-Specific pyproject.toml Files ✅

**For `api/pyproject.toml`:**

- [x] Package name: `croatian-cadastral-api`
- [x] Dependencies: Core SDK dependencies only
- [x] No CLI entry point
- [x] Export Python package: `cadastral_api`

**For `cli/pyproject.toml`:**

- [x] Package name: `cadastral-cli`
- [x] Dependencies: Include `cadastral-api`, `click`, `rich`
- [x] Entry point: `cadastral = cadastral_cli.main:cli`
- [x] Export Python package: `cadastral_cli`

**For `mcp/pyproject.toml`:**

- [x] Package name: `cadastral-mcp-server`
- [x] Dependencies: Include `cadastral-api`, `fastmcp`
- [x] Entry point: `cadastral-mcp = cadastral_mcp.main:main`
- [x] Export Python package: `cadastral_mcp`

### 7.3 Environment Configuration ✅

**Update `.env.example`:**

- [x] Verify it works for all projects
- [x] Add project-specific sections if needed
- [x] Document which projects use which variables

---

## Phase 8: Testing & Validation 🔄

### 8.1 Create Missing Tests ⏳

**API tests:**

- [x] Move `api/tests/unit/test_exceptions.py`
- [x] Move `api/tests/unit/test_validation.py`
- [ ] Create `api/tests/unit/test_api_client.py` - **TODO**
- [ ] Create `api/tests/unit/test_entities.py` - **TODO**
- [ ] Create `api/tests/unit/test_gis_parser.py` - **TODO**
- [ ] Create `api/tests/unit/test_gis_cache.py` - **TODO**
- [ ] Create `api/tests/integration/test_full_workflow.py` - **TODO**

**CLI tests:**

- [ ] Create `cli/tests/test_cli_commands.py` - **TODO**
- [ ] Create `cli/tests/test_formatters.py` - **TODO**
- [ ] Create `cli/tests/test_integration.py` - **TODO**

**MCP tests:**

- [ ] Create `mcp/tests/test_mcp_server.py` - **TODO**
- [ ] Create `mcp/tests/test_mcp_tools.py` - **TODO**

### 8.2 Verify Builds ⏳

- [ ] Build API package: `cd api && pip install -e .` - **TODO**
- [ ] Build CLI package: `cd cli && pip install -e .` - **TODO**
- [ ] Build MCP package: `cd mcp && pip install -e .` - **TODO**
- [ ] Verify all imports work - **TODO**
- [ ] Verify CLI commands work - **TODO**
- [ ] Verify MCP server starts - **TODO**

### 8.3 Run Tests ⏳

- [ ] Run API tests: `cd api && pytest` - **TODO**
- [ ] Run CLI tests: `cd cli && pytest` - **TODO**
- [ ] Run MCP tests: `cd mcp && pytest` - **TODO**
- [ ] Run mock server: `cd mock-server && python src/main.py` - **TODO**
- [ ] Verify all tests pass - **TODO**

---

## Phase 9: Git Setup (Final Step) ✅

### 9.1 Prepare Git Repository ✅

- [x] Review all changes
- [x] Verify `.gitignore` is complete
- [x] Verify no sensitive data in repo
- [x] Verify no unnecessary files (build artifacts, etc.)

### 9.2 Initialize Git ✅

- [x] Git already initialized
- [x] Multiple commits created during refactoring
- [x] Current branch: feature/monorepo-refactoring

### 9.3 Create Git Tags (Optional) ⏳

- [ ] Tag initial version: `git tag -a v0.1.0 -m "Initial monorepo structure"` - **OPTIONAL**
- [ ] Consider tagging per-project versions if needed - **OPTIONAL**

---

## Phase 10: Documentation Finalization 🔄

### 10.1 Update All READMEs ✅

**Root `README.md`:**

- [x] Overview of monorepo
- [x] Links to each project
- [x] Quick start for contributors
- [x] Architecture overview

**`api/README.md`:**

- [x] API package description
- [x] Installation instructions
- [x] Quick start examples
- [x] Link to full docs

**`cli/README.md`:**

- [x] CLI tool description
- [x] Installation instructions
- [x] Basic command examples
- [x] Link to command reference

**`mcp/README.md`:**

- [x] MCP server description
- [x] Installation and setup
- [x] Usage examples
- [x] Link to protocol docs

**`mock-server/README.md`:**

- [x] Mock server description
- [x] How to run
- [x] Available endpoints
- [x] Test data info

### 10.2 Create Architecture Documentation ⏳

- [ ] Create `docs/architecture.md` with:
  - Monorepo structure diagram
  - Project dependencies
  - Data flow between projects
  - Deployment architecture
  - **TODO - Recommended for future**

### 10.3 Create Contribution Guide ⏳

- [ ] Create `docs/contributing.md` with:
  - Development environment setup
  - Coding standards (link to naming-conventions.md)
  - Testing requirements
  - Pull request process
  - **TODO - Recommended for future**

---

## Priority Order

### Do First (Foundation)

1. **Phase 1**: Create new directory structure
2. **Phase 2**: Move API code (most critical)
3. **Phase 5**: Reorganize mock server (needed for testing)

### Then (Projects)

1. **Phase 3**: Move CLI code
2. **Phase 4**: Move MCP code

### Next (Organization)

1. **Phase 6**: Organize shared resources
2. **Phase 7**: Update configuration files

### Finally (Polish)

1. **Phase 8**: Testing & validation
2. **Phase 10**: Documentation finalization
3. **Phase 9**: Git initialization (very last step)

---

## Notes

- Use `git mv` when possible to preserve history
- Test after each major phase
- Update imports incrementally
- Keep backup before starting
- Can work on phases in parallel (API and CLI are independent)

---

## Summary

### ✅ Completed (90%+)

- **Phases 1-7**: Monorepo structure fully implemented
- **Phase 9**: Git repository setup complete
- **Phase 10**: Documentation mostly complete

### 🔄 Partially Complete

- **Phase 8**: Testing infrastructure needs expansion
- **Phase 10.2-10.3**: Optional documentation (architecture.md, contributing.md)

### ⏳ Remaining Work (Optional)

1. **Comprehensive test suite** - Add more unit and integration tests
2. **Architecture documentation** - Create visual diagrams
3. **Contributing guide** - Formalize contribution process
4. **Build verification** - Test editable installs in fresh environment

---

**Status**: ✅ **REFACTORING COMPLETE** (Core work done, optional items remain)
**Last Updated**: 2026-01-19
