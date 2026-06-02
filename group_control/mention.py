"""Detect whether an inbound WhatsApp event mentions the bot."""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from .whatsapp_ids import expand_whatsapp_identifiers, normalize_whatsapp_identifier


def is_bot_mentioned(event, raw: Optional[Dict[str, Any]] = None) -> bool:
    raw = raw if isinstance(raw, dict) else getattr(event, "raw_message", None)
    if not isinstance(raw, dict):
        return False

    body = str(getattr(event, "text", "") or raw.get("body") or "").strip()
    if body.startswith("/"):
        return True

    bot_ids = _expand_id_set(raw.get("botIds") or [])
    if not bot_ids:
        return False

    mentioned = _expand_id_set(raw.get("mentionedIds") or [])
    if mentioned & bot_ids:
        return True

    quoted = _normalize_jid(raw.get("quotedParticipant"))
    if quoted:
        quoted_aliases = expand_whatsapp_identifiers(quoted) | {quoted, quoted.split("@", 1)[0]}
        if quoted_aliases & bot_ids:
            return True

    lower_body = body.lower()
    for bot_id in bot_ids:
        bare = bot_id.split("@", 1)[0].lower() if "@" in bot_id else str(bot_id).lower()
        if bare and (f"@{bare}" in lower_body or bare in lower_body):
            return True

    return False


def _expand_id_set(candidates) -> Set[str]:
    """Normalize JIDs and expand LID/phone aliases for set intersection."""
    out: Set[str] = set()
    for candidate in candidates:
        normalized = _normalize_jid(candidate)
        if not normalized:
            continue
        out.add(normalized)
        bare = normalized.split("@", 1)[0]
        if bare:
            out.add(bare)
        out |= expand_whatsapp_identifiers(normalized)
    return out


def _normalize_jid(value: Any) -> str:
    if not value:
        return ""
    normalized = str(value).strip()
    if ":" in normalized and "@" in normalized:
        normalized = normalized.replace(":", "@", 1)
    return normalized
