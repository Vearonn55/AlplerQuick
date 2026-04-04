"""Replace catalogue href in page HTML using data-catalogue selector."""

from __future__ import annotations

import re


class HrefReplaceError(Exception):
    pass


def replace_href_by_selector(html: str, selector: str, new_url: str) -> str:
    """
    Find exactly one <a> with data-catalogue="selector" and replace its href.
    Supports either attribute order: data-catalogue before href, or href before data-catalogue.
    """
    if not selector:
        raise HrefReplaceError("selector is empty")

    if '"' in new_url:
        raise HrefReplaceError("New URL contains a double quote; refusing to write HTML.")

    esc = re.escape(selector)

    # Order A: data-catalogue="..." ... href="..."
    pat_a = re.compile(
        r'(<a\b[^>]*\bdata-catalogue="' + esc + r'"[^>]*\bhref=")([^"]*)(")',
        re.IGNORECASE,
    )
    # Order B: href="..." ... data-catalogue="..."
    pat_b = re.compile(
        r'(<a\b[^>]*\bhref=")([^"]*)("[^>]*\bdata-catalogue="' + esc + r'"[^>]*)',
        re.IGNORECASE,
    )

    for pat in (pat_a, pat_b):
        matches = list(pat.finditer(html))
        if len(matches) == 1:
            return pat.sub(lambda m: m.group(1) + new_url + m.group(3), html, count=1)
        if len(matches) > 1:
            raise HrefReplaceError(
                f'Multiple ({len(matches)}) <a> tags match data-catalogue="{selector}"; selector must be unique.'
            )

    raise HrefReplaceError(
        f'No <a> tag with data-catalogue="{selector}" found in page content.'
    )
