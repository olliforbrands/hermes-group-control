"""Tests for the user-installed group-control plugin at ~/.hermes/plugins/group-control/."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from gateway.config import Platform
from gateway.platforms.base import MessageEvent, MessageType
from gateway.session import SessionSource

# Repo root when cloned; falls back to standard Hermes install path.
PLUGIN_SRC = Path(__file__).resolve().parents[1]
_INSTALLED = Path.home() / ".hermes" / "plugins" / "group-control"
if not (PLUGIN_SRC / "plugin.yaml").exists() and (_INSTALLED / "plugin.yaml").exists():
    PLUGIN_SRC = _INSTALLED
GROUP_JID = "120363000000000000@g.us"
BOT_JID = "15551234567@s.whatsapp.net"


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    plugin_dest = home / "plugins" / "group-control"
    shutil.copytree(PLUGIN_SRC, plugin_dest)
    (home / "config.yaml").write_text(
        f"""
group_control:
  db_path: {home / "group-control" / "data.db"}
  media_dir: {home / "group-control" / "media"}
  media_max_mb: 50
  default_mode: observe
  admins:
    - "15551234567"
plugins:
  enabled:
    - group-control
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


def _load_plugin_package():
    if "hermes_plugins" not in sys.modules:
        ns = types.ModuleType("hermes_plugins")
        ns.__path__ = []
        sys.modules["hermes_plugins"] = ns

    plugin_dir = PLUGIN_SRC
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.group_control_plugin",
        plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "hermes_plugins.group_control_plugin"
    mod.__path__ = [str(plugin_dir)]
    sys.modules["hermes_plugins.group_control_plugin"] = mod
    spec.loader.exec_module(mod)
    return mod


def _group_event(
    text: str = "hello",
    message_id: str = "msg-1",
    raw_message: dict | None = None,
) -> MessageEvent:
    return MessageEvent(
        text=text,
        message_id=message_id,
        message_type=MessageType.TEXT,
        raw_message=raw_message or {},
        source=SessionSource(
            platform=Platform.WHATSAPP,
            user_id="6281234567890@s.whatsapp.net",
            chat_id=GROUP_JID,
            user_name="alice",
            chat_name="Test Group",
            chat_type="group",
        ),
    )


def _reset_ingest_singleton():
    import group_control.ingest as ingest_mod

    ingest_mod._storage = None
    ingest_mod._config = None


@pytest.fixture(autouse=True)
def _ensure_plugin_on_path():
    plugin_dir = str(PLUGIN_SRC)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)
    yield
    _reset_ingest_singleton()


class TestPolicy:
    def test_observe_always_skips(self):
        policy = importlib.import_module("group_control.policy")
        event = _group_event(
            raw_message={
                "botIds": [BOT_JID],
                "mentionedIds": [BOT_JID],
            }
        )
        result = policy.dispatch_action("observe", event)
        assert result == {"action": "skip", "reason": "group-control-observe"}

    def test_mention_not_tagged_skips(self):
        policy = importlib.import_module("group_control.policy")
        event = _group_event(raw_message={"botIds": [BOT_JID], "mentionedIds": []})
        result = policy.dispatch_action("mention", event)
        assert result == {
            "action": "skip",
            "reason": "group-control-mention-not-tagged",
        }

    def test_mention_tagged_allows(self):
        policy = importlib.import_module("group_control.policy")
        event = _group_event(
            raw_message={
                "botIds": [BOT_JID],
                "mentionedIds": [BOT_JID],
            }
        )
        assert policy.dispatch_action("mention", event) is None


class TestMention:
    def test_slash_prefix_counts_as_mention(self):
        mention = importlib.import_module("group_control.mention")
        event = _group_event(text="/gc mode observe", raw_message={})
        assert mention.is_bot_mentioned(event) is True


class TestStorageAndIngest:
    def test_ingest_idempotent(self, hermes_home):
        _reset_ingest_singleton()
        ingest = importlib.import_module("group_control.ingest")
        event = _group_event(message_id="dup-1")
        mode1, ok1 = ingest.ingest_message(event)
        mode2, ok2 = ingest.ingest_message(event)
        assert ok1 and ok2
        assert mode1 == mode2 == "observe"

        _, store = ingest._get_storage()
        count = store._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE message_id = ?",
            ("dup-1",),
        ).fetchone()[0]
        assert count == 1

    def test_set_group_mode(self, hermes_home):
        _reset_ingest_singleton()
        storage_mod = importlib.import_module("group_control.storage")
        cfg_mod = importlib.import_module("group_control.config")
        cfg = cfg_mod.load_config()
        store = storage_mod.Storage(cfg.db_path)
        now = "2026-06-02T00:00:00+00:00"
        store.upsert_group(GROUP_JID, "G", "observe", now)
        assert store.set_group_mode(GROUP_JID, "mention", now)
        row = store._conn.execute(
            "SELECT mode FROM groups WHERE jid = ?",
            (GROUP_JID,),
        ).fetchone()
        assert row["mode"] == "mention"


class TestMedia:
    def test_media_copy(self, hermes_home, tmp_path):
        media_mod = importlib.import_module("group_control.media")
        src = tmp_path / "photo.jpg"
        src.write_bytes(b"jpeg-bytes")
        media_dir = hermes_home / "group-control" / "media"
        path, mime, size = media_mod.copy_media_files(
            [str(src)],
            ["image/jpeg"],
            media_dir,
            GROUP_JID,
            "m-media",
            max_bytes=1024 * 1024,
        )
        assert path is not None
        assert Path(path).is_file()
        assert mime == "image/jpeg"
        assert size == len(b"jpeg-bytes")

    def test_media_over_size_skipped(self, hermes_home, tmp_path):
        media_mod = importlib.import_module("group_control.media")
        src = tmp_path / "big.bin"
        src.write_bytes(b"x" * 200)
        media_dir = hermes_home / "group-control" / "media"
        path, _, _ = media_mod.copy_media_files(
            [str(src)],
            [],
            media_dir,
            GROUP_JID,
            "m-big",
            max_bytes=50,
        )
        assert path is None


class TestHook:
    def test_hook_observe_skips(self, hermes_home):
        _reset_ingest_singleton()
        hook = importlib.import_module("group_control.hook")
        event = _group_event(message_id="hook-1")
        with patch.object(hook, "ingest_message", return_value=("observe", True)):
            result = hook.on_pre_gateway_dispatch(event)
        assert result == {"action": "skip", "reason": "group-control-observe"}

    def test_hook_mention_ingest_fail_skips(self, hermes_home):
        _reset_ingest_singleton()
        hook = importlib.import_module("group_control.hook")
        event = _group_event(
            message_id="hook-2",
            raw_message={"botIds": [BOT_JID], "mentionedIds": [BOT_JID]},
        )
        with patch.object(hook, "ingest_message", return_value=("mention", False)):
            result = hook.on_pre_gateway_dispatch(event)
        assert result == {"action": "skip", "reason": "group-control-ingest-failed"}

    def test_non_group_returns_none(self):
        hook = importlib.import_module("group_control.hook")
        event = MessageEvent(
            text="dm",
            message_id="dm-1",
            source=SessionSource(
                platform=Platform.WHATSAPP,
                user_id=BOT_JID,
                chat_id=BOT_JID,
                chat_type="dm",
            ),
        )
        assert hook.on_pre_gateway_dispatch(event) is None


class TestPluginDiscovery:
    def test_plugin_register_and_discover(self, hermes_home):
        mod = _load_plugin_package()
        assert callable(mod.register)

        from hermes_cli.plugins import PluginManager

        pm = PluginManager()
        pm.discover_and_load(force=True)
        loaded = pm._plugins.get("group-control")
        assert loaded is not None
        assert loaded.enabled is True
        assert loaded.error is None
