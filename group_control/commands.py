"""Slash command: /gc mode observe|mention"""

from __future__ import annotations

from datetime import datetime, timezone

from .config import load_config
from .ingest import _get_storage


def _normalize_admin_id(value: str) -> str:
    v = str(value or "").strip()
    if ":" in v and "@" in v:
        v = v.replace(":", "@", 1)
    return v


def _is_admin(user_id: str, admins: set[str]) -> bool:
    if not admins:
        return True
    uid = _normalize_admin_id(user_id)
    bare = uid.split("@", 1)[0] if uid else ""
    for admin in admins:
        a = _normalize_admin_id(admin)
        if uid and (uid == a or bare == a.split("@", 1)[0]):
            return True
        if bare and bare == a.split("@", 1)[0]:
            return True
    return False


def _session_chat_id() -> str:
    try:
        from gateway.session_context import get_session_env

        return str(get_session_env("HERMES_SESSION_CHAT_ID", "") or "").strip()
    except Exception:
        return ""


def _session_user_id() -> str:
    try:
        from gateway.session_context import get_session_env

        return str(get_session_env("HERMES_SESSION_USER_ID", "") or "").strip()
    except Exception:
        return ""


def _session_platform() -> str:
    try:
        from gateway.session_context import get_session_env

        return str(get_session_env("HERMES_SESSION_PLATFORM", "") or "").strip().lower()
    except Exception:
        return ""


def handle_gc_command(raw_args: str) -> str:
    argv = (raw_args or "").strip().split()
    if len(argv) < 2 or argv[0].lower() != "mode":
        return (
            "Usage: /gc mode observe — silent archive only\n"
            "       /gc mode mention — reply when @mentioned"
        )

    mode = argv[1].lower()
    if mode not in {"observe", "mention"}:
        return "Mode must be `observe` or `mention`."

    cfg = load_config()
    user_id = _session_user_id()
    if not _is_admin(user_id, cfg.admins):
        return "Not authorized. Add your id to group_control.admins in config.yaml."

    platform = _session_platform()
    if platform and platform != "whatsapp":
        return "Run this command from a WhatsApp session."

    group_jid = _session_chat_id()
    if not group_jid or not group_jid.endswith("@g.us"):
        return "Run this command inside a WhatsApp group chat."

    _, store = _get_storage()
    now = datetime.now(timezone.utc).isoformat()
    if not store.set_group_mode(group_jid, mode, now):
        return (
            "Group not in archive yet. Send any message in this group first, "
            "then run /gc mode again."
        )

    if mode == "observe":
        return f"Group set to observe — archive only, no replies (even @mentions)."
    return f"Group set to mention — archive + Hermes replies when @mentioned."
