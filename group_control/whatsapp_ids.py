"""Resolve WhatsApp LID ↔ phone using bridge session mapping files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Set


def _default_session_dir() -> Path:
    home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
    return Path(os.getenv("WHATSAPP_SESSION_DIR", home / "whatsapp" / "session"))


def normalize_whatsapp_identifier(value: str) -> str:
    normalized = str(value or "").strip()
    if ":" in normalized and "@" in normalized:
        normalized = normalized.replace(":", "@", 1)
    if "@" in normalized:
        normalized = normalized.split("@", 1)[0]
    return normalized.lstrip("+")


def _read_mapping_file(session_dir: Path, identifier: str, suffix: str = "") -> str | None:
    path = session_dir / f"lid-mapping-{identifier}{suffix}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        resolved = normalize_whatsapp_identifier(data)
        return resolved or None
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def expand_whatsapp_identifiers(identifier: str, session_dir: Path | None = None) -> Set[str]:
    """Return phone/LID aliases for an id (mirrors whatsapp-bridge allowlist.js)."""
    session_dir = session_dir or _default_session_dir()
    normalized = normalize_whatsapp_identifier(identifier)
    if not normalized:
        return set()

    resolved: Set[str] = set()
    queue = [normalized]

    while queue:
        current = queue.pop(0)
        if not current or current in resolved:
            continue
        resolved.add(current)
        for suffix in ("", "_reverse"):
            mapped = _read_mapping_file(session_dir, current, suffix)
            if mapped and mapped not in resolved:
                queue.append(mapped)

    return resolved
