"""pre_gateway_dispatch hook — archive then skip or allow."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .ingest import ingest_message, is_whatsapp_group_message
from .policy import dispatch_action

logger = logging.getLogger(__name__)


def on_pre_gateway_dispatch(event, **kwargs) -> Optional[Dict[str, Any]]:
    if not is_whatsapp_group_message(event):
        return None

    group_mode = "observe"
    ingest_ok = False
    try:
        group_mode, ingest_ok = ingest_message(event)
    except Exception as exc:
        logger.exception("group-control: ingest failed: %s", exc)
        ingest_ok = False

    action = dispatch_action(group_mode, event)

    if action is not None:
        return action

    if not ingest_ok:
        return {"action": "skip", "reason": "group-control-ingest-failed"}

    return None
