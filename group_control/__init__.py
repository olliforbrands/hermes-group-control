"""Hermes group-control plugin — WhatsApp group archive + observe/mention gate."""

from __future__ import annotations

from .commands import handle_gc_command
from .hook import on_pre_gateway_dispatch


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", on_pre_gateway_dispatch)
    ctx.register_command(
        "gc",
        handler=handle_gc_command,
        description="Group control: /gc mode observe|mention",
        args_hint="mode observe|mention",
    )
