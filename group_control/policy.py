"""Dispatch policy: skip vs allow Hermes agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .mention import is_bot_mentioned

MODE_OBSERVE = "observe"
MODE_MENTION = "mention"


def dispatch_action(group_mode: str, event) -> Optional[Dict[str, Any]]:
    mode = (group_mode or MODE_OBSERVE).strip().lower()
    if mode == MODE_OBSERVE:
        return {"action": "skip", "reason": "group-control-observe"}

    if mode == MODE_MENTION:
        if is_bot_mentioned(event):
            return None
        return {"action": "skip", "reason": "group-control-mention-not-tagged"}

    return {"action": "skip", "reason": "group-control-unknown-mode"}
