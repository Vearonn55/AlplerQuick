"""Load catalogue definitions for HTML href replacement."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CatalogueEntry:
    id: str
    label: str
    href_marker: str
    upload_filename: str


def load_catalogues(path: Path) -> list[CatalogueEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("catalogues.json must be a JSON array")
    out: list[CatalogueEntry] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"catalogues.json[{i}] must be an object")
        cid = str(item["id"]).strip()
        label = str(item["label"]).strip()
        marker = str(item["href_marker"]).strip()
        upload = str(item.get("upload_filename") or marker).strip()
        if not cid or not label or not marker:
            raise ValueError(f"catalogues.json[{i}] needs id, label, href_marker")
        out.append(CatalogueEntry(id=cid, label=label, href_marker=marker, upload_filename=upload))
    if not out:
        raise ValueError("catalogues.json must contain at least one entry")
    return out


def by_id(entries: list[CatalogueEntry]) -> dict[str, CatalogueEntry]:
    return {e.id: e for e in entries}
