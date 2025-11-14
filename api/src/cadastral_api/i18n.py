"""Internationalization support for Croatian Cadastral API CLI.

This module provides i18n support using Python's built-in gettext.
Croatian (hr) is the default language, with English (en) as fallback.

Language Selection Priority:
1. --lang CLI flag
2. CADASTRAL_LANG environment variable
3. System locale (LANG, LC_MESSAGES, etc.)
4. Default: Croatian (hr)

Usage:
    from cadastral_api.i18n import _, ngettext, pgettext

    # Basic translation
    print(_("Hello, world!"))

    # Plural forms
    msg = ngettext("Found {count} result", "Found {count} results", count)

    # Context-specific translation
    label = pgettext("button", "Open")
"""

import gettext as _gettext_module
import locale
import os
from pathlib import Path

# Package and locale directory paths
_PACKAGE_PATH = Path(__file__).parent
_LOCALE_DIR = _PACKAGE_PATH / "locale"

# Supported languages
SUPPORTED_LANGUAGES = ["hr", "en"]
DEFAULT_LANGUAGE = "hr"  # Croatian is default

# Translation domain name (matches .mo filename)
DOMAIN = "cadastral"


def get_system_locale() -> str:
    """
    Get system locale and map to supported language.

    Reads from system environment variables and locale settings
    to determine the user's preferred language.

    Returns:
        Language code ('hr' or 'en')
    """
    try:
        # Try to get locale from system
        lang = locale.getdefaultlocale()[0]
        if lang:
            # Extract language code (e.g., 'hr_HR' -> 'hr', 'en_US' -> 'en')
            lang_code = lang.split('_')[0].lower()
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
    except Exception:
        pass

    # Check environment variables (in order of precedence)
    for env_var in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"]:
        env_lang = os.getenv(env_var, "")
        if env_lang:
            # Extract language code
            lang_code = env_lang.split('_')[0].split('.')[0].lower()
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code

    return DEFAULT_LANGUAGE


def get_translation_language() -> str:
    """
    Determine which language to use for translations.

    Priority order:
    1. CADASTRAL_LANG environment variable (explicit override)
    2. System locale detection
    3. Default (Croatian)

    Returns:
        Language code ('hr' or 'en')
    """
    # Check for explicit override via environment variable
    override = os.getenv("CADASTRAL_LANG", "").lower()
    if override in SUPPORTED_LANGUAGES:
        return override

    # Check system locale
    return get_system_locale()


# Initialize translations
_current_language = get_translation_language()

try:
    # Attempt to load translations for selected language
    TRANSLATIONS = _gettext_module.translation(
        domain=DOMAIN,
        localedir=str(_LOCALE_DIR),
        languages=[_current_language],
        fallback=True  # Fall back to source strings if not found
    )
except Exception:
    # If locale directory doesn't exist or translation files are missing,
    # create a NullTranslations object that returns source strings
    TRANSLATIONS = _gettext_module.NullTranslations()


# Public translation API
_ = TRANSLATIONS.gettext           # Basic translation: _("text")
ngettext = TRANSLATIONS.ngettext   # Plural forms: ngettext("1 item", "{n} items", n)
pgettext = TRANSLATIONS.pgettext   # Context-specific: pgettext("menu", "File")


def get_current_language() -> str:
    """
    Get the currently active language.

    Returns:
        Language code ('hr' or 'en')
    """
    return _current_language


def set_language(lang: str) -> None:
    """
    Change the active language at runtime.

    Args:
        lang: Language code ('hr' or 'en')

    Raises:
        ValueError: If language is not supported
    """
    global _current_language, TRANSLATIONS, _, ngettext, pgettext

    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {lang}. "
            f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    _current_language = lang

    try:
        TRANSLATIONS = _gettext_module.translation(
            domain=DOMAIN,
            localedir=str(_LOCALE_DIR),
            languages=[lang],
            fallback=True
        )
    except Exception:
        TRANSLATIONS = _gettext_module.NullTranslations()

    # Update public API
    _ = TRANSLATIONS.gettext
    ngettext = TRANSLATIONS.ngettext
    pgettext = TRANSLATIONS.pgettext
