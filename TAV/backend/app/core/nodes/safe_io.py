"""
safe_io - controlled file access helpers for custom nodes

Custom node code runs inside the backend process. Even for local deployments, we should not
allow arbitrary filesystem access from AI-generated code. These helpers allow *read-only*
access to files under explicitly allowlisted root directories, with size limits.

Configure allowlisted roots via environment variable:
  TAV_CUSTOM_NODE_FILE_ROOTS="data,docs"

- Relative roots are resolved relative to current working directory.
- Absolute roots are used as-is.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Iterable, Optional, List


DEFAULT_ALLOWED_ROOTS = ["data", "docs"]
DEFAULT_MAX_BYTES = 1_000_000  # 1MB


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        return path.is_relative_to(root)  # py3.9+
    except AttributeError:
        try:
            path.relative_to(root)
            return True
        except Exception:
            return False


def _get_allowed_roots() -> List[Path]:
    raw = os.getenv("TAV_CUSTOM_NODE_FILE_ROOTS", "")
    roots = [r.strip() for r in raw.split(",") if r.strip()] or DEFAULT_ALLOWED_ROOTS

    resolved: List[Path] = []
    cwd = Path.cwd()
    for r in roots:
        p = Path(r).expanduser()
        if not p.is_absolute():
            p = (cwd / p)
        resolved.append(p.resolve())
    return resolved


def _ensure_allowed(path: Path, allowed_roots: Iterable[Path]) -> None:
    for root in allowed_roots:
        if _is_relative_to(path, root):
            return
    allowed_str = ", ".join(str(r) for r in allowed_roots)
    raise PermissionError(
        f"File access denied: '{path}'. Allowed roots: {allowed_str}. "
        f"Configure with TAV_CUSTOM_NODE_FILE_ROOTS."
    )


def safe_read_bytes(path: str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    """
    Read bytes from a file under allowed roots, up to max_bytes.
    """
    allowed = _get_allowed_roots()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p)
    p = p.resolve()

    _ensure_allowed(p, allowed)

    if not p.exists() or not p.is_file():
        raise FileNotFoundError(str(p))

    data = p.read_bytes()
    if len(data) > max_bytes:
        return data[:max_bytes]
    return data


def safe_read_text(
    path: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> str:
    """
    Read text from a file under allowed roots, up to max_bytes.
    """
    return safe_read_bytes(path, max_bytes=max_bytes).decode(encoding, errors=errors)


def safe_read_json(path: str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> object:
    """
    Read JSON from a file under allowed roots, up to max_bytes.
    """
    return json.loads(safe_read_text(path, max_bytes=max_bytes))


