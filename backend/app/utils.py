"""Utility functions for the Notes for Emi backend."""

from __future__ import annotations

from html.parser import HTMLParser

import nh3

# ---------------------------------------------------------------------------
# Excerpt generation
# ---------------------------------------------------------------------------

_EXCERPT_MAX_CHARS = 200


class _TextExtractor(HTMLParser):
    """Minimal HTML parser that collects visible text content."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:  # noqa: D102
        self._parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._parts)


def generate_excerpt(body_html: str) -> str:
    """Strip HTML tags from *body_html* and return up to 200 plain-text characters.

    Uses the standard-library ``html.parser`` — no third-party dependency.
    """
    extractor = _TextExtractor()
    extractor.feed(body_html)
    plain = extractor.text
    return plain[:_EXCERPT_MAX_CHARS]


# ---------------------------------------------------------------------------
# HTML sanitisation
# ---------------------------------------------------------------------------

# Tags produced by the Tiptap editor that we want to preserve.
_ALLOWED_TAGS: set[str] = {
    "p",
    "strong",
    "em",
    "h1",
    "h2",
    "h3",
    "ul",
    "ol",
    "li",
    "img",
}

# Per-tag attribute allowlists.  ``nh3`` accepts a ``dict[str, set[str]]``
# mapping tag names to the set of attributes permitted on that tag.
_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "img": {"src", "class", "alt"},
}


def sanitise_html(body_html: str) -> str:
    """Sanitise *body_html* using ``nh3``, keeping only Tiptap-produced tags.

    Allowed tags: p, strong, em, h1, h2, h3, ul, ol, li, img.
    Allowed attributes on <img>: src, class, alt.
    All other tags and attributes are stripped.
    """
    return nh3.clean(
        body_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
    )


# ---------------------------------------------------------------------------
# Label normalisation
# ---------------------------------------------------------------------------


def normalise_labels(labels: list[str]) -> list[str]:
    """Strip whitespace, lowercase, and deduplicate *labels*.

    Deduplication preserves the first occurrence of each unique value
    (case-insensitive comparison after stripping and lowercasing).

    Examples::

        >>> normalise_labels(["Life", " life ", "LIFE", "lessons"])
        ['life', 'lessons']
    """
    seen: set[str] = set()
    result: list[str] = []
    for label in labels:
        normalised = label.strip().lower()
        if normalised and normalised not in seen:
            seen.add(normalised)
            result.append(normalised)
    return result
