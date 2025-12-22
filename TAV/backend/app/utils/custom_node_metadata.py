"""
Utilities for extracting metadata from custom node source code.

We treat the @register_node(...) decorator as source-of-truth for display metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CustomNodeMetadata:
    category: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    version: Optional[str] = None


_DECORATOR_BLOCK_RE = re.compile(
    r"@register_node\s*\(\s*([\s\S]*?)\)\s*\n\s*class\s+",
    re.IGNORECASE,
)


def _extract_str(block: str, key: str) -> Optional[str]:
    m = re.search(rf"{re.escape(key)}\s*=\s*['\"]([^'\"]+)['\"]", block)
    return m.group(1).strip() if m else None


def _extract_category(block: str) -> Optional[str]:
    # category=NodeCategory.WORKFLOW
    m = re.search(r"category\s*=\s*NodeCategory\.([A-Z_]+)", block)
    if m:
        return m.group(1).strip().lower()
    # category="workflow"
    m2 = re.search(r"category\s*=\s*['\"]([^'\"]+)['\"]", block)
    if m2:
        return m2.group(1).strip().lower()
    return None


def extract_custom_node_metadata(code: str) -> CustomNodeMetadata:
    """
    Best-effort parse metadata from @register_node(...) in `code`.
    Returns empty fields if not found / unparsable.
    """
    if not code:
        return CustomNodeMetadata()

    m = _DECORATOR_BLOCK_RE.search(code)
    if not m:
        return CustomNodeMetadata()

    block = m.group(1)
    return CustomNodeMetadata(
        category=_extract_category(block),
        name=_extract_str(block, "name"),
        description=_extract_str(block, "description"),
        icon=_extract_str(block, "icon"),
        version=_extract_str(block, "version"),
    )


