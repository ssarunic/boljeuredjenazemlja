"""Custom setuptools command to compile translations during build.

This module provides a build hook that automatically compiles .po translation
files to binary .mo files when building the package with pip install or
python setup.py build.
"""

import subprocess
from pathlib import Path

from setuptools import Command


class BuildTranslations(Command):
    """Compile .po files to .mo files during package build."""

    description = "Compile translation files (.po -> .mo)"
    user_options = []

    def initialize_options(self):
        """Set default values for options."""
        pass

    def finalize_options(self):
        """Post-process options."""
        pass

    def run(self):
        """Compile all .po files to .mo files."""
        po_dir = Path("po")
        locale_dir = Path("src/cadastral_api/locale")

        if not po_dir.exists():
            self.announce("No po/ directory found, skipping translation compilation", level=2)
            return

        # Create locale directory
        locale_dir.mkdir(parents=True, exist_ok=True)

        # Compile each .po file
        po_files = list(po_dir.glob("*.po"))
        if not po_files:
            self.announce("No .po files found, skipping translation compilation", level=2)
            return

        for po_file in po_files:
            lang = po_file.stem
            mo_dir = locale_dir / lang / "LC_MESSAGES"
            mo_dir.mkdir(parents=True, exist_ok=True)
            mo_file = mo_dir / "cadastral.mo"

            self.announce(f"Compiling {lang}...", level=2)

            try:
                subprocess.run(
                    ["msgfmt", "-o", str(mo_file), str(po_file)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                self.announce(f"  ✓ Created: {mo_file}", level=2)
            except subprocess.CalledProcessError as e:
                self.warn(f"Failed to compile {po_file}: {e.stderr}")
            except FileNotFoundError:
                self.warn(
                    "msgfmt not found. Install gettext tools to compile translations.\n"
                    "  macOS: brew install gettext\n"
                    "  Ubuntu/Debian: apt-get install gettext\n"
                    "  Fedora: dnf install gettext"
                )
                break

        self.announce("Translation compilation complete", level=2)
