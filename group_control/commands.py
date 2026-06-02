"""Slash command: /gc mode observe|mention"""

from __future__ import annotations

from datetime import datetime, timezone
from .config import load_config
from .ingest import _get_storage
from .whatsapp_ids import expand_whatsapp_identifiers, normalize_whatsapp_identifier


def is_admin(user_id: str, admins: set[str]) -> bool:
    """True if user_id is listed in admins. Empty admins allows everyone."""
    if not admins:
        return True
    if not str(user_id or "").strip():
        return False

    user_aliases = expand_whatsapp_identifiers(user_id)
    if not user_aliases:
        user_aliases = {normalize_whatsapp_identifier(user_id)}

    for admin in admins:
        admin_aliases = expand_whatsapp_identifiers(admin)
        if not admin_aliases:
            admin_aliases = {normalize_whatsapp_identifier(admin)}
        if user_aliases & admin_aliases:
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


def _platform_value(platform: str) -> str:
    p = str(platform or "").strip().lower()
    if "." in p:
        return p.split(".")[-1]
    return p


def _mode_confirmation(mode: str, *, already: bool = False) -> str:
    if mode == "observe":
        if already:
            return "Already in observe mode — archive only, no replies."
        return "Group set to observe — archive only, no replies (even @mentions)."
    if already:
        return "Already in mention mode — archive + replies when @mentioned."
    return "Group set to mention — archive + Hermes replies when @mentioned."


def handle_gc_command_for_source(
    raw_args: str,
    user_id: str,
    chat_id: str,
    platform: str,
) -> str:
    """Run /gc using explicit message source (works from pre_gateway_dispatch hook)."""
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
    if not is_admin(user_id, cfg.admins):
        return "Not authorized. Add your id to group_control.admins in config.yaml."

    plat = _platform_value(platform)
    if plat and plat != "whatsapp":
        return "Run this command from a WhatsApp session."

    group_jid = str(chat_id or "").strip()
    if not group_jid or not group_jid.endswith("@g.us"):
        return "Run this command inside a WhatsApp group chat."

    _, store = _get_storage()
    current = store.get_group_mode(group_jid)
    if current == mode:
        return _mode_confirmation(mode, already=True)

    now = datetime.now(timezone.utc).isoformat()
    if not store.set_group_mode(group_jid, mode, now):
        return (
            "Group not in archive yet. Send any message in this group first, "
            "then run /gc mode again."
        )

    return _mode_confirmation(mode, already=False)


def handle_gc_command(raw_args: str) -> str:
    """Slash-command entry (session env when gateway has set context)."""
    return handle_gc_command_for_source(
        raw_args,
        user_id=_session_user_id(),
        chat_id=_session_chat_id(),
        platform=_session_platform(),
    )
