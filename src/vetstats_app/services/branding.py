"""Shared branding constants and asset paths for VetStats 2.0."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtGui import QIcon

APP_REPORT_TITLE = "VetStats 2.0 Microbiology"

AUTHOR_NAME = "Aleksandra Sypniewska"
COPYRIGHT_TEXT = "© 2026 Aleksandra Sypniewska. Wszelkie prawa zastrzeżone."

VETSTATS_LOGO_FILENAME = "vetstats_logo.png"
MICROBIOLOGY_LOGO_FILENAME = "microbiology_logo.png"


def _repo_root() -> Path:
    """Return the repository root for development runs (PYTHONPATH=src).

    Packaged installs may relocate assets under the installed package; adjust
    this resolver (e.g. importlib.resources) when adding package-data support.
    """
    return Path(__file__).resolve().parents[3]


def branding_dir() -> Path:
    """Return the assets/branding directory at the repository root."""
    return _repo_root() / "assets" / "branding"


def branding_asset_path(filename: str) -> Path:
    """Resolve a filename inside assets/branding/."""
    return branding_dir() / filename


def vetstats_logo_path() -> Path:
    return branding_asset_path(VETSTATS_LOGO_FILENAME)


def microbiology_logo_path() -> Path:
    return branding_asset_path(MICROBIOLOGY_LOGO_FILENAME)


def footer_text() -> str:
    """Footer line for PDF/UI; uses copyright only to avoid repeating the author name."""
    return COPYRIGHT_TEXT


def load_window_icon() -> QIcon | None:
    """Return the VetStats window icon, or None if the logo cannot be loaded."""
    try:
        from PyQt6.QtGui import QIcon, QPixmap

        logo_path = vetstats_logo_path()
        if not logo_path.is_file():
            return None

        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            return None

        icon = QIcon(pixmap)
        return None if icon.isNull() else icon
    except Exception:
        return None
