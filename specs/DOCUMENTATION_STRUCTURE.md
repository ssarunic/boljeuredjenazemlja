# Documentation Structure

This document describes the organization of documentation in this repository.

## Directory Structure

```
Croatian Cadastral API/
│
├── README.md                  # Main project documentation (Python SDK + CLI overview)
├── CLAUDE.md                  # AI assistant guidance
│
├── docs/                      # 📖 USER DOCUMENTATION
│   ├── README.md             # User documentation index
│   └── CLI.md                # Complete CLI command reference
│
├── specs/                     # 🔧 TECHNICAL SPECIFICATIONS
│   ├── README.md             # Specifications index
│   ├── Croatian_Cadastral_API_Specification.md     # API documentation
│   ├── Pydantic_Business_Entities_Implementation.md # Pydantic models spec
│   ├── I18N_GUIDE.md                                # i18n developer guide
│   ├── I18N_IMPLEMENTATION_STATUS.md                # i18n status
│   └── LOCALIZATION_EXAMPLE.py                      # i18n code example
│
├── examples/                  # 💻 CODE EXAMPLES
│   └── basic_usage.py        # Python SDK examples
│
├── scripts/                   # 🛠️ BUILD & UTILITY SCRIPTS
│   ├── generate_pot.sh       # Extract translatable strings
│   ├── update_translations.sh # Update translation files
│   ├── compile_translations.sh # Compile translations
│   └── init_language.sh      # Initialize new language
│
├── po/                        # 🌍 TRANSLATION FILES
│   ├── cadastral.pot         # Translation template
│   ├── hr.po                 # Croatian translations (to be created)
│   └── en.po                 # English translations (to be created)
│
└── src/                       # 📦 SOURCE CODE
    └── cadastral_api/
        ├── client/           # API client
        ├── models/           # Pydantic models
        ├── gis/              # GIS functionality
        ├── cli/              # CLI commands
        ├── i18n.py           # Internationalization
        └── exceptions.py     # Custom exceptions
```

## Documentation Organization

### User Documentation (`docs/`)
**Audience**: End users of the CLI tool

**Contents**:
- CLI command reference
- Usage examples
- Quick start guides
- Troubleshooting

**Keep it**:
- Simple and practical
- Example-driven
- Focused on "how to use"

### Technical Specifications (`specs/`)
**Audience**: Developers, contributors, maintainers

**Contents**:
- API specifications
- Implementation details
- Architecture decisions
- Developer guides (like i18n)
- Technical examples

**Keep it**:
- Detailed and comprehensive
- Technical and precise
- Focused on "how it works"

## Document Types

### User-Facing
- `docs/CLI.md` - End-user CLI documentation
- `README.md` - Project overview and getting started
- `examples/` - Practical code examples

### Developer-Facing
- `specs/` - All technical specifications
- `CLAUDE.md` - AI assistant context
- `scripts/` - Build and development tools

### Build/Infrastructure
- `po/` - Translation source files
- `.vscode/` - VS Code configuration
- `pyproject.toml` - Project configuration

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Use the CLI | [docs/CLI.md](docs/CLI.md) |
| Use the Python SDK | [README.md](README.md) |
| See code examples | [examples/](examples/) |
| Understand the API | [specs/Croatian_Cadastral_API_Specification.md](specs/Croatian_Cadastral_API_Specification.md) |
| Contribute translations | [specs/I18N_GUIDE.md](specs/I18N_GUIDE.md) |
| Debug a command | [.vscode/launch.json](.vscode/launch.json) |

## Contributing Documentation

### Adding User Documentation
1. Place in `docs/` directory
2. Update `docs/README.md` index
3. Link from main `README.md` if appropriate
4. Keep language simple and example-driven

### Adding Technical Specifications
1. Place in `specs/` directory
2. Update `specs/README.md` index
3. Use descriptive filename (e.g., `Feature_Name_Implementation.md`)
4. Include technical details, architecture, and rationale

### Naming Conventions
- Use `_` for word separation (not `-` or spaces)
- Be descriptive (avoid generic names like `spec.md` or `notes.md`)
- Include document type in name:
  - `*_API_*.md` - API documentation
  - `*_Implementation.md` - Implementation specs
  - `*_Guide.md` - Developer guides
  - `*_Status.md` - Status documents

## Examples

### Good Documentation Placement

✅ `docs/CLI.md` - User-facing CLI guide  
✅ `specs/I18N_GUIDE.md` - Technical developer guide  
✅ `specs/Croatian_Cadastral_API_Specification.md` - API specification  
✅ `examples/basic_usage.py` - Practical code example  

### Poor Documentation Placement

❌ `CLI_Technical_Implementation.md` in `docs/` - Should be in `specs/`  
❌ `Quick_Start_Guide.md` in `specs/` - Should be in `docs/`  
❌ `notes.md` anywhere - Too generic, unclear content  
❌ API details in `README.md` - Should be in separate spec file  

## Maintenance

- Keep user docs (`docs/`) up to date with CLI changes
- Update technical specs (`specs/`) when architecture changes
- Main `README.md` should be concise - link to detailed docs
- Use relative links so docs work in GitHub and locally
