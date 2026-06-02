"""Detect whether an inbound WhatsApp event mentions the bot."""

from __future__ import annotations

from typing import Any, Dict, Optional


def is_bot_mentioned(event, raw: Optional[Dict[str, Any]] = None) -> bool:
    raw = raw if isinstance(raw, dict) else getattr(event, "raw_message", None)
    if not isinstance(raw, dict):
        return False

    body = str(getattr(event, "text", "") or raw.get("body") or "").strip()
    if body.startswith("/"):
        return True

    bot_ids = _bot_ids(raw)
    if not bot_ids:
        return False

    mentioned = {
        _normalize_jid(candidate)
        for candidate in (raw.get("mentionedIds") or [])
        if _normalize_jid(candidate)
    }
    if mentioned & bot_ids:
        return True

    quoted = _normalize_jid(raw.get("quotedParticipant"))
    if quoted and quoted in bot_ids:
        return True

    lower_body = body.lower()
    for bot_id in bot_ids:
        bare = bot_id.split("@", 1)[0].lower()
        if bare and (f"@{bare}" in lower_body or bare in lower_body):
            return True

    return False


def _bot_ids(raw: Dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for candidate in raw.get("botIds") or []:
        normalized = _normalize_jid(candidate)
        if normalized:
            out.add(normalized)
    return out


def _normalize_jid(value: Any) -> str:
    if not value:
        return ""
    normalized = str(value).strip()
    if ":" in normalized and "@" in normalized:
        normalized = normalized.replace(":", "@", 1)
    return normalized
