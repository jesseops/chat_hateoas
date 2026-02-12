from __future__ import annotations

from flask import render_template


def render_feedback(message_id: int, vote: str | None) -> str:
    return render_template("chat/_feedback.html", message_id=message_id, vote=vote)


def render_stream_delta(body_html: str) -> str:
    return body_html


def render_stream_done(body_html: str, message_id: int, vote: str | None) -> str:
    feedback_html = render_feedback(message_id=message_id, vote=vote)
    return f"{body_html}{feedback_html}"
