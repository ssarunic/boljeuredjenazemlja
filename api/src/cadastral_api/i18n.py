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

``_``, ``ngettext`` and ``pgettext`` are stable functions that always consult
the catalog selected by the most recent :func:`set_language` call, so modules
may import them at module level and still follow a later language switch.

The selected language is also bound to Python's module-level gettext domain
(``gettext.textdomain``) and exported via the ``LANGUAGE`` environment
variable, so libraries that use ``gettext.gettext`` directly (click does)
render their own messages from the same catalog.
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
        # Try to get locale from the current locale settings
        lang = locale.getlocale()[0]
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
            lang_code = env_lang.split('_')[0].split('.')[0].split(':')[0].lower()
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


def _load_catalog(lang: str) -> _gettext_module.NullTranslations:
    """Load the catalog for ``lang``, falling back to source strings."""
    try:
        return _gettext_module.translation(
            domain=DOMAIN,
            localedir=str(_LOCALE_DIR),
            languages=[lang],
            fallback=True,  # Fall back to source strings if not found
        )
    except Exception:
        # If locale directory doesn't exist or translation files are missing,
        # create a NullTranslations object that returns source strings
        return _gettext_module.NullTranslations()


def _activate(lang: str) -> None:
    """Make ``lang`` the active language for this module and for libraries."""
    global _current_language, TRANSLATIONS

    _current_language = lang
    TRANSLATIONS = _load_catalog(lang)

    # Route the module-level gettext API (used by click for its own messages
    # such as "Usage:", "Options" and "Missing option") to the same catalog.
    _gettext_module.bindtextdomain(DOMAIN, str(_LOCALE_DIR))
    _gettext_module.textdomain(DOMAIN)
    os.environ["LANGUAGE"] = lang


# Initialize translations
_current_language = DEFAULT_LANGUAGE
TRANSLATIONS: _gettext_module.NullTranslations = _gettext_module.NullTranslations()
_activate(get_translation_language())


# Public translation API. These delegate on every call so that a module-level
# ``from cadastral_api.i18n import _`` keeps working after set_language().
def _(message: str) -> str:
    """Translate ``message`` using the active catalog."""
    return TRANSLATIONS.gettext(message)


def gettext(message: str) -> str:
    """Alias of :func:`_` for callers that prefer the explicit name."""
    return TRANSLATIONS.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate a message with plural forms: ngettext("1 item", "{n} items", n)."""
    return TRANSLATIONS.ngettext(singular, plural, n)


def pgettext(context: str, message: str) -> str:
    """Translate a message in a specific context: pgettext("menu", "File")."""
    return TRANSLATIONS.pgettext(context, message)


def N_(message: str) -> str:  # noqa: N802 - conventional gettext marker name
    """Mark ``message`` for extraction without translating it here.

    Use it for strings that are translated later (or by a library) via a
    variable, which xgettext cannot see: ``N_("required")``.
    """
    return message


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
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {lang}. "
            f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    _activate(lang)
