"""Runtime checks for optional statistical dependencies."""

from __future__ import annotations

from vetstats_app.analysis.detailed_comparative import BLOCK_SCIPY_MISSING


def scipy_missing_message() -> str | None:
    try:
        import scipy.stats  # noqa: F401
    except ImportError:
        return BLOCK_SCIPY_MISSING
    return None


def format_statistical_runtime_error(detail: str | None) -> str:
    if detail and _is_scipy_import_error(detail):
        return BLOCK_SCIPY_MISSING
    return detail or ""


def _is_scipy_import_error(detail: str) -> bool:
    lowered = detail.casefold()
    return "no module named 'scipy'" in lowered or 'no module named "scipy"' in lowered
