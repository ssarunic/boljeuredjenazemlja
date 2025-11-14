#!/bin/bash
# Update existing .po files with new strings from .pot template
#
# This script merges new/changed strings from the .pot template
# into existing translation files, preserving existing translations.
#
# Usage: ./scripts/update_translations.sh

set -e

DOMAIN="cadastral"
POT_FILE="po/${DOMAIN}.pot"

echo "========================================="
echo "Updating translation files..."
echo "========================================="

if [ ! -f "${POT_FILE}" ]; then
    echo "Error: Template file ${POT_FILE} not found."
    echo "Run ./scripts/generate_pot.sh first."
    exit 1
fi

# Update each .po file
for PO_FILE in po/*.po; do
    if [ -f "${PO_FILE}" ]; then
        LANG=$(basename "${PO_FILE}" .po)
        echo ""
        echo "Updating ${LANG}..."

        msgmerge \
            --update \
            --backup=none \
            --no-fuzzy-matching \
            "${PO_FILE}" \
            "${POT_FILE}"

        # Statistics
        TOTAL=$(msggrep --no-wrap -v -T -e "." "${PO_FILE}" | grep -c "^msgid" || echo "0")
        TRANSLATED=$(msggrep --no-wrap -T -e "." "${PO_FILE}" | grep -c "^msgid" || echo "0")
        UNTRANSLATED=$((TOTAL - TRANSLATED))

        echo "  ✓ Total: ${TOTAL}, Translated: ${TRANSLATED}, Untranslated: ${UNTRANSLATED}"
    fi
done

echo ""
echo "========================================="
echo "✓ Translation files updated"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit po/*.po files to add/update translations"
echo "  2. Compile translations:"
echo "     ./scripts/compile_translations.sh"
echo ""
