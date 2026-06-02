"""pre_gateway_dispatch hook — archive then skip or allow."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .commands import handle_gc_command_for_source
from .ingest import ingest_message, is_whatsapp_group_message
from .policy import dispatch_action
from .reply import schedule_reply

logger = logging.getLogger(__name__)


def _source_field(event, name: str) -> str:
    source = getattr(event, "source", None)
    if source is None:
        return ""
    value = getattr(source, name, None)
    if value is None:
        return ""
    plat_val = getattr(value, "value", value)
    return str(plat_val)


def on_pre_gateway_dispatch(event, gateway=None, session_store=None, **kwargs) -> Optional[Dict[str, Any]]:
    if not is_whatsapp_group_message(event):
        return None

    group_mode = "observe"
    ingest_ok = False
    try:
        group_mode, ingest_ok = ingest_message(event)
    except Exception as exc:
        logger.exception("group-control: ingest failed: %s", exc)
        ingest_ok = False

    if event.get_command() == "gc":
        reply = handle_gc_command_for_source(
            raw_args=event.get_command_args(),
            user_id=_source_field(event, "user_id"),
            chat_id=_source_field(event, "chat_id"),
            platform=_source_field(event, "platform"),
        )
        schedule_reply(gateway, event, reply)
        return {"action": "skip", "reason": "group-control-gc-command"}

    action = dispatch_action(group_mode, event)

    if action is not None:
        return action

    if not ingest_ok:
        return {"action": "skip", "reason": "group-control-ingest-failed"}

    return None
