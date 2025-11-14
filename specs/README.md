# Specifications Directory

This directory contains technical specifications and implementation documentation for the Croatian Cadastral API client.

## Contents

### API Documentation

- **[Croatian_Cadastral_API_Specification.md](Croatian_Cadastral_API_Specification.md)**
  - Complete API endpoint documentation
  - Request/response formats with real examples
  - Data structure details for all nested objects
  - Tested parcels and verification data
  - Known issues and discrepancies
  - Last updated: November 7, 2025

### Implementation Specifications

- **[Pydantic_Business_Entities_Implementation.md](Pydantic_Business_Entities_Implementation.md)**
  - Pydantic V2 business entity design and architecture
  - Complete field documentation for all 7 models
  - Computed properties and validators
  - Type hint specifications (Python 3.12+)
  - Testing results and findings
  - Usage examples

### Internationalization (i18n)

- **[I18N_GUIDE.md](I18N_GUIDE.md)**
  - Developer guide for localizing the CLI
  - Translation patterns and examples
  - Best practices and common mistakes
  - Workflow for adding/updating translations
  - Croatian translation reference

- **[I18N_IMPLEMENTATION_STATUS.md](I18N_IMPLEMENTATION_STATUS.md)**
  - Current status of i18n implementation
  - Completed components
  - Pending tasks and next steps
  - Effort estimates

- **[LOCALIZATION_EXAMPLE.py](LOCALIZATION_EXAMPLE.py)**
  - Complete working example of localized CLI command
  - Reference implementation showing all patterns

## Future Specifications

This directory is organized to support future feature implementations:

- `*_API_*.md` - API-related specifications
- `*_Implementation.md` - Implementation specifications for specific features
- `*_Architecture.md` - Architecture and design documents
- `*_Testing.md` - Testing strategies and results

## Naming Convention

Use descriptive names that clearly indicate the content:
- Good: `Pydantic_Business_Entities_Implementation.md`
- Good: `Async_Client_Implementation.md`
- Good: `Caching_Strategy_Architecture.md`
- Avoid: `implementation.md`, `spec1.md`, `notes.md`
