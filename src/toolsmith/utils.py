"""Shared utility helpers for ToolSmith."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(data: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest of a JSON-serialisable dict."""
    raw = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate *text* to *max_len* characters, adding an ellipsis if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def merge_schemas(*schemas: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple JSON-Schema ``object`` definitions into one.

    Properties and required lists are combined; later schemas win on conflict.
    """
    merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    for schema in schemas:
        merged["properties"].update(schema.get("properties", {}))
        for req in schema.get("required", []):
            if req not in merged["required"]:
                merged["required"].append(req)
    return merged
