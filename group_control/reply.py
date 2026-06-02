"""Send WhatsApp (or other platform) replies from sync plugin hooks."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def schedule_reply(gateway: Any, event: Any, text: str) -> None:
    """Schedule an async adapter.send from a synchronous pre_gateway_dispatch hook."""
    if not gateway or not text:
        return

    source = getattr(event, "source", None)
    if source is None:
        return

    platform = getattr(source, "platform", None)
    chat_id = getattr(source, "chat_id", None)
    if platform is None or not chat_id:
        return

    adapters = getattr(gateway, "adapters", None) or {}
    adapter = adapters.get(platform)
    if adapter is None:
        logger.warning("group-control: no adapter for platform %s", platform)
        return

    async def _send() -> None:
        try:
            await adapter.send(str(chat_id), str(text))
        except Exception as exc:
            logger.warning("group-control: failed to send /gc reply: %s", exc)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("group-control: no event loop for /gc reply")
        return

    loop.create_task(_send())
