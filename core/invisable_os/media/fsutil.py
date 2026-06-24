"""Small filesystem helpers for the media pipeline."""

from __future__ import annotations

import os
import re


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def slug(text: str, n: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:n] or "asset"


def write_bytes(path: str, data: bytes) -> str:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "wb") as f:
        f.write(data)
    return path


def write_text(path: str, text: str) -> str:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
