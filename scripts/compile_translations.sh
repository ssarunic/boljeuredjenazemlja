#!/bin/bash
# Compile .po translation files to binary .mo files
#
# This script compiles human-readable .po files into binary .mo files
# that are used at runtime for fast translation lookups.
#
# Usage: ./scripts/compile_translations.sh

set -e

DOMAIN="cadastral"
LOCALE_DIR="src/cadastral_api/locale"

echo "========================================="
echo "Compiling translation files..."
echo "========================================="

# Create locale directory if it doesn't exist
mkdir -p "${LOCALE_DIR}"

# Compile each .po file
for PO_FILE in po/*.po; do
    if [ -f "${PO_FILE}" ]; then
        LANG=$(basename "${PO_FILE}" .po)
        MO_DIR="${LOCALE_DIR}/${LANG}/LC_MESSAGES"
        MO_FILE="${MO_DIR}/${DOMAIN}.mo"

        echo ""
        echo "Compiling ${LANG}..."

        # Create directory
        mkdir -p "${MO_DIR}"

        # Compile with statistics
        msgfmt \
            --check \
            --statistics \
            --output-file="${MO_FILE}" \
            "${PO_FILE}"

        echo "  ✓ Created: ${MO_FILE}"
    fi
done

echo ""
echo "========================================="
echo "✓ Compiled translations in ${LOCALE_DIR}"
echo "========================================="
echo ""
echo "Test translations:"
echo "  cadastral --help"
echo "  cadastral search --help"
echo "  CADASTRAL_LANG=en cadastral --help"
echo ""
