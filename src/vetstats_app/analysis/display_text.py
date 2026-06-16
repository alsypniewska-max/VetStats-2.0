from __future__ import annotations

import unicodedata

PLAIN_BETA = "\u03b2"


def sanitize_matplotlib_text(text: str) -> str:
    """Replace Unicode mathematical beta glyphs with plain Greek beta for rendering."""
    if not text:
        return text

    sanitized: list[str] = []
    for char in text:
        if char == PLAIN_BETA:
            sanitized.append(char)
            continue
        if "SMALL BETA" in unicodedata.name(char, ""):
            sanitized.append(PLAIN_BETA)
        else:
            sanitized.append(char)
    return "".join(sanitized)
