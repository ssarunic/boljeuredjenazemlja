"""Root test configuration: stop the ``mcp/`` directory from shadowing the ``mcp`` package.

A bare ``pytest`` from the repository root runs every project's suite
(``testpaths`` in ``pyproject.toml``). The repository root is then on
``sys.path``, so ``import mcp`` would find the ``mcp/`` project directory (an
implicit namespace package) instead of the installed MCP SDK, and the MCP
server tests would fail to import. Dropping the root from ``sys.path`` is
safe because the suites are collected with ``--import-mode=importlib`` and
the packages under test are installed (``pip install -e``).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
sys.path[:] = [
    entry
    for entry in sys.path
    if entry and Path(entry).resolve() != _REPO_ROOT
]
_shadow = sys.modules.get("mcp")
if _shadow is not None and getattr(_shadow, "__file__", None) is None:
    del sys.modules["mcp"]

# pytest's importlib mode names ``mcp/tests/test_x.py`` ``mcp.tests.test_x`` after
# the rootdir and, when several suites are collected, registers a namespace
# package ``mcp`` for the directory. Importing the real SDK first pins the
# name to the installed package; the test modules then hang off it harmlessly.
try:
    importlib.import_module("mcp")
except ImportError:  # the MCP SDK is not installed in this environment
    pass
