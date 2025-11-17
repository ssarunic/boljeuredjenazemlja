#!/bin/bash
# Extract translatable strings from Python source code to create .pot template
#
# This script uses xgettext to scan all Python files and extract strings
# wrapped in _(), ngettext(), and pgettext() calls.
#
# Usage: ./scripts/generate_pot.sh

set -e

DOMAIN="cadastral"
POT_FILE="po/${DOMAIN}.pot"
API_SRC_DIR="api/src/cadastral_api"
CLI_SRC_DIR="cli/src/cadastral_cli"
VERSION="0.1.0"
BUGS_EMAIL="your.email@example.com"

echo "========================================="
echo "Extracting translatable strings..."
echo "========================================="

# Create po directory if it doesn't exist
mkdir -p po

# Extract strings from Python source files
xgettext \
    --language=Python \
    --keyword=_ \
    --keyword=N_ \
    --keyword=ngettext:1,2 \
    --keyword=pgettext:1c,2 \
    --keyword=npgettext:1c,2,3 \
    --from-code=UTF-8 \
    --add-comments=TRANSLATORS: \
    --output="${POT_FILE}" \
    --package-name="Croatian Cadastral API" \
    --package-version="${VERSION}" \
    --msgid-bugs-address="${BUGS_EMAIL}" \
    --copyright-holder="Croatian Cadastral API Contributors" \
    --foreign-user \
    $(find ${API_SRC_DIR} ${CLI_SRC_DIR} -name "*.py" -type f 2>/dev/null)

# Count extracted strings
TOTAL_STRINGS=$(grep -c "^msgid" "${POT_FILE}" || echo "0")

echo ""
echo "========================================="
echo "✓ Template created: ${POT_FILE}"
echo "✓ Total strings: ${TOTAL_STRINGS}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Create language files:"
echo "     ./scripts/init_language.sh hr"
echo "     ./scripts/init_language.sh en"
echo "  2. Or update existing translations:"
echo "     ./scripts/update_translations.sh"
echo ""
