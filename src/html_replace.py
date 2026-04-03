"""Replace a single catalogue href in page HTML by unique marker substring."""

from __future__ import annotations

import re


class HrefReplaceError(Exception):
    pass


def replace_href_by_marker(html: str, href_marker: str, new_url: str) -> str:
    """
    Find exactly one href=\"...\" whose value contains href_marker and set it to new_url.
    Marker is usually the PDF filename (stable across http/https/www variants).
    """
    if not href_marker:
        raise HrefReplaceError("href_marker is empty")
    # Match href="...marker..." — marker may appear anywhere in the URL path
    pattern = re.compile(
        r'href="([^"]*' + re.escape(href_marker) + r'[^"]*)"',
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(html))
    if len(matches) == 0:
        raise HrefReplaceError(
            f"No href containing {href_marker!r} found in page content. "
            "Check catalogues.json href_marker matches the live page HTML."
        )
    if len(matches) > 1:
        raise HrefReplaceError(
            f"Multiple ({len(matches)}) hrefs contain {href_marker!r}; use a more specific marker."
        )
    if '"' in new_url:
        raise HrefReplaceError("New URL contains a double quote; refusing to write HTML.")
    return pattern.sub(f'href="{new_url}"', html, count=1)
