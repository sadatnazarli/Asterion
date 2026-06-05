"""Provenance helpers — hashing and CIK normalization.

Pure functions, no I/O, no external deps. Used by ingestion to stamp every stored
artifact with a reproducible content hash and a canonical CIK.
"""
from __future__ import annotations

import hashlib


def content_hash(payload: bytes | str) -> str:
    """Stable sha256 hex digest of a raw payload (bytes or text).

    The hash anchors deduplication and provenance. Text is UTF-8 encoded so the
    same logical content always yields the same digest.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_cik(cik: str | int) -> str:
    """Return a zero-padded 10-digit CIK string (SEC canonical form).

    Accepts ints, plain digit strings, or already-prefixed 'CIK0000000000'.
    Raises ValueError on non-numeric / empty input.
    """
    s = str(cik).strip().upper()
    if s.startswith("CIK"):
        s = s[3:]
    s = s.lstrip()
    if not s or not s.isdigit():
        raise ValueError(f"invalid CIK: {cik!r}")
    if len(s) > 10:
        raise ValueError(f"CIK too long: {cik!r}")
    return s.zfill(10)


def cik_url_fragment(cik: str | int) -> str:
    """'CIK##########' form used in SEC data.sec.gov paths."""
    return f"CIK{normalize_cik(cik)}"
