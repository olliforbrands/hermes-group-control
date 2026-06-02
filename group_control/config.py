"""Load group_control settings from ~/.hermes/config.yaml and environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Set

_DEFAULT_HOME = Path.home() / ".hermes" / "group-control"


@dataclass(frozen=True)
class GroupControlConfig:
    db_path: Path
    media_dir: Path
    media_max_mb: int
    default_mode: str
    admins: Set[str]


def _expand_path(raw: str, default: Path) -> Path:
    if not raw:
        return default
    return Path(os.path.expanduser(str(raw).strip())).resolve()


def _parse_admins(raw) -> Set[str]:
    parts: list[str] = []
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(",", " ").split() if p.strip()]
    elif isinstance(raw, list):
        parts = [str(p).strip() for p in raw if str(p).strip()]
    env_extra = os.getenv("GROUP_CONTROL_ADMINS", "").strip()
    if env_extra:
        parts.extend(p.strip() for p in env_extra.replace(",", " ").split() if p.strip())
    return set(parts)


def load_config() -> GroupControlConfig:
    section: dict = {}
    try:
        from hermes_cli.config import load_config as load_hermes_config

        cfg = load_hermes_config()
        if isinstance(cfg, dict):
            section = cfg.get("group_control") or {}
        else:
            section = getattr(cfg, "group_control", None) or {}
    except Exception:
        section = {}

    if not isinstance(section, dict):
        section = {}

    db_path = _expand_path(
        str(section.get("db_path") or os.getenv("GROUP_CONTROL_DB_PATH", "")),
        _DEFAULT_HOME / "data.db",
    )
    media_dir = _expand_path(
        str(section.get("media_dir") or os.getenv("GROUP_CONTROL_MEDIA_DIR", "")),
        _DEFAULT_HOME / "media",
    )

    media_max_mb = int(section.get("media_max_mb") or os.getenv("GROUP_CONTROL_MEDIA_MAX_MB", "50") or 50)
    default_mode = str(
        section.get("default_mode") or os.getenv("GROUP_CONTROL_DEFAULT_MODE", "observe")
    ).strip().lower()
    if default_mode not in {"observe", "mention"}:
        default_mode = "observe"

    return GroupControlConfig(
        db_path=db_path,
        media_dir=media_dir,
        media_max_mb=max(1, media_max_mb),
        default_mode=default_mode,
        admins=_parse_admins(section.get("admins")),
    )
