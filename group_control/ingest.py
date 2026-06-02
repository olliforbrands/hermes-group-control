"""Ingest WhatsApp group messages into the archive."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from gateway.config import Platform
from gateway.platforms.base import MessageEvent, MessageType

from .config import GroupControlConfig, load_config
from .media import copy_media_files
from .storage import Storage

logger = logging.getLogger(__name__)

_storage: Optional[Storage] = None
_config: Optional[GroupControlConfig] = None


def _get_storage() -> Tuple[GroupControlConfig, Storage]:
    global _storage, _config
    if _config is None:
        _config = load_config()
    if _storage is None:
        _storage = Storage(_config.db_path)
    return _config, _storage


def is_whatsapp_group_message(event) -> bool:
    if getattr(event, "internal", False):
        return False
    source = getattr(event, "source", None)
    if source is None:
        return False
    platform = getattr(source, "platform", None)
    plat_val = getattr(platform, "value", platform)
    if str(plat_val) != Platform.WHATSAPP.value:
        return False
    return getattr(source, "chat_type", "") == "group"


def ingest_message(event: MessageEvent) -> Tuple[str, bool]:
    """Archive message. Returns (group_mode, ingest_ok)."""
    cfg, store = _get_storage()
    source = event.source
    group_jid = str(source.chat_id or "")
    if not group_jid:
        return cfg.default_mode, False

    now = datetime.now(timezone.utc).isoformat()
    name = str(source.chat_name or group_jid)
    message_id = str(event.message_id or "")
    if not message_id:
        message_id = f"noid-{now}-{hash(event.text) & 0xFFFFFFFF:x}"

    if store.message_exists(message_id):
        mode = store.upsert_group(group_jid, name, cfg.default_mode, now)
        return mode, True

    mode = store.upsert_group(group_jid, name, cfg.default_mode, now)

    msg_type = _msg_type_name(event)
    media_path = None
    mime_type = None
    media_size = None
    has_media = 0
    urls = list(getattr(event, "media_urls", None) or [])
    types = list(getattr(event, "media_types", None) or [])
    if urls:
        max_bytes = cfg.media_max_mb * 1024 * 1024
        media_path, mime_type, media_size = copy_media_files(
            urls, types, cfg.media_dir, group_jid, message_id, max_bytes
        )
        if media_path:
            has_media = 1

    sender_jid = str(source.user_id or "")
    sender_name = str(source.user_name or "")

    try:
        store.insert_message(
            {
                "message_id": message_id,
                "group_jid": group_jid,
                "sender_jid": sender_jid,
                "sender_name": sender_name,
                "body": str(event.text or ""),
                "ts": now,
                "msg_type": msg_type,
                "has_media": has_media,
                "media_path": media_path,
                "mime_type": mime_type,
                "media_size": media_size,
            }
        )
        store.touch_group(group_jid, now)
        return mode, True
    except Exception as exc:
        logger.exception("group-control: failed to insert message %s: %s", message_id, exc)
        return mode, False


def _msg_type_name(event: MessageEvent) -> str:
    mt = getattr(event, "message_type", MessageType.TEXT)
    if mt == MessageType.PHOTO:
        return "photo"
    if mt == MessageType.VIDEO:
        return "video"
    if mt == MessageType.VOICE:
        return "voice"
    if mt == MessageType.DOCUMENT:
        return "document"
    return "text"
