"""Copy bridge media files into the group-control archive."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def copy_media_files(
    media_urls: List[str],
    media_types: List[str],
    media_dir: Path,
    group_jid: str,
    message_id: str,
    max_bytes: int,
) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    if not media_urls:
        return None, None, None

    safe_jid = group_jid.replace("@", "_").replace("/", "_")
    dest_dir = media_dir / safe_jid
    dest_dir.mkdir(parents=True, exist_ok=True)

    for idx, src in enumerate(media_urls):
        src_path = Path(src)
        if not src_path.is_file():
            logger.warning("group-control: missing media file %s", src)
            continue
        size = src_path.stat().st_size
        if size > max_bytes:
            logger.warning(
                "group-control: skip media over limit (%s > %s): %s",
                size,
                max_bytes,
                src_path,
            )
            continue
        ext = src_path.suffix or _guess_ext(media_types, idx)
        dest_name = f"{message_id}_{idx}{ext}"
        dest_path = dest_dir / dest_name
        try:
            shutil.copy2(src_path, dest_path)
        except OSError as exc:
            logger.warning("group-control: failed to copy %s: %s", src_path, exc)
            continue
        mime = media_types[idx] if idx < len(media_types) else None
        return str(dest_path), mime, size

    return None, None, None


def _guess_ext(media_types: List[str], idx: int) -> str:
    mime = media_types[idx].lower() if idx < len(media_types) else ""
    if "jpeg" in mime or mime == "image/jpeg":
        return ".jpg"
    if "png" in mime:
        return ".png"
    if "webp" in mime:
        return ".webp"
    if "ogg" in mime:
        return ".ogg"
    if "mp4" in mime:
        return ".mp4"
    if "pdf" in mime:
        return ".pdf"
    return ".bin"
