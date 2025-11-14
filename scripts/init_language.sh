#!/bin/bash
# Initialize a new language translation file from template
#
# This script creates a new .po file for a language from the .pot template.
# Use this when adding support for a new language.
#
# Usage: ./scripts/init_language.sh <language_code>
# Example: ./scripts/init_language.sh de

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <language_code>"
    echo ""
    echo "Examples:"
    echo "  $0 hr    # Croatian"
    echo "  $0 en    # English"
    echo "  $0 de    # German"
    echo "  $0 it    # Italian"
    exit 1
fi

LANG=$1
DOMAIN="cadastral"
POT_FILE="po/${DOMAIN}.pot"
PO_FILE="po/${LANG}.po"

echo "========================================="
echo "Initializing ${LANG} translation..."
echo "========================================="

if [ ! -f "${POT_FILE}" ]; then
    echo "Error: Template ${POT_FILE} not found."
    echo "Run ./scripts/generate_pot.sh first."
    exit 1
fi

if [ -f "${PO_FILE}" ]; then
    echo "Error: ${PO_FILE} already exists."
    echo "Use ./scripts/update_translations.sh to update existing translations."
    exit 1
fi

echo ""
echo "Creating ${PO_FILE}..."

# Create new .po file from template
msginit \
    --input="${POT_FILE}" \
    --locale="${LANG}" \
    --output="${PO_FILE}" \
    --no-translator

echo ""
echo "========================================="
echo "✓ Language file created: ${PO_FILE}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit ${PO_FILE} and translate strings"
echo "  2. Compile translations:"
echo "     ./scripts/compile_translations.sh"
echo "  3. Test:"
echo "     CADASTRAL_LANG=${LANG} cadastral --help"
echo ""
