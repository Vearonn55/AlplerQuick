"""Linearize PDF bytes for faster web loading (pikepdf)."""

from __future__ import annotations

import io
import logging

import pikepdf

logger = logging.getLogger(__name__)


class LinearizeError(Exception):
    """PDF could not be linearized."""


def linearize_pdf_bytes(data: bytes) -> bytes:
    try:
        with pikepdf.open(io.BytesIO(data)) as pdf:
            out = io.BytesIO()
            pdf.save(out, linearize=True)
            return out.getvalue()
    except Exception as exc:
        logger.exception("PDF linearization failed")
        raise LinearizeError(str(exc)) from exc
