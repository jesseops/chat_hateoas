from __future__ import annotations

from flask import render_template


def render_stream_delta(body_html: str) -> str:
    return body_html


def render_stream_done(message) -> str:  # type: ignore[no-untyped-def]
    return render_template("chat/_message.html", message=message, oob=True)
