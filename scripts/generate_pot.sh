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

# click renders its own messages ("Usage:", "Options", "Missing option" ...)
# through the same catalog (see cadastral_api.i18n), so extract them as well.
#
# The strings must come from the *same* click the CLI and the coverage gate run
# with, so prefer the repository venv over whatever python3 is on PATH (a stray
# user-site click of another version silently produces a drifted catalog).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "${PYTHON:-}" ]; then
    if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
        PYTHON="${REPO_ROOT}/.venv/bin/python"
    else
        PYTHON="python3"
    fi
fi
CLICK_DIR=$("${PYTHON}" -c "import click, os; print(os.path.dirname(click.__file__))" 2>/dev/null || true)
if [ -n "${CLICK_DIR}" ]; then
    CLICK_VERSION=$("${PYTHON}" -c "from importlib.metadata import version; print(version(\"click\"))")
    echo "Adding click ${CLICK_VERSION} messages from ${CLICK_DIR} (via ${PYTHON})"
    (
        cd "$(dirname "${CLICK_DIR}")" && xgettext \
            --language=Python \
            --keyword=_ \
            --keyword=ngettext:1,2 \
            --flag=ngettext:1:no-python-brace-format \
            --flag=ngettext:2:no-python-brace-format \
            --from-code=UTF-8 \
            --join-existing \
            --output="${OLDPWD}/${POT_FILE}" \
            click/*.py
    )
else
    echo "WARNING: click not importable via ${PYTHON}; its messages were not extracted." >&2
    echo "         Set PYTHON=/path/to/python with click installed and re-run." >&2
fi

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
