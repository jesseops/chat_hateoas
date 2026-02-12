from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, redirect, render_template, request, url_for

from chat_hateoas import db
from chat_hateoas.services.transform import render_user_html

bp = Blueprint("web", __name__)


def _is_htmx() -> bool:
    return request.headers.get("HX-Request") == "true"


def _normalize_active_conversation(
    conversations: list[Any],
    requested_id: int | None,
) -> int | None:
    if not conversations:
        return None

    available_ids = {int(item["id"]) for item in conversations}
    if requested_id is not None and requested_id in available_ids:
        return requested_id
    return int(conversations[0]["id"])


def _ensure_seed_conversation() -> None:
    if db.conversation_count() > 0:
        return
    db.create_conversation("Conversation 1")


def _new_conversation_title() -> str:
    return f"Conversation {db.conversation_count() + 1}"


def _render_thread_and_sidebar(active_id: int) -> str:
    conversations = db.list_conversations()
    conversation = db.get_conversation(active_id)
    if conversation is None:
        abort(404)
    messages = db.list_messages(active_id)

    thread_html = render_template(
        "chat/_thread.html",
        conversation=conversation,
        messages=messages,
    )
    sidebar_html = render_template(
        "chat/_conversation_list.html",
        conversations=conversations,
        active_id=active_id,
        oob=True,
    )
    return f"{thread_html}{sidebar_html}"


@bp.get("/")
def index() -> str:
    _ensure_seed_conversation()

    requested_id = request.args.get("conversation_id", type=int)
    conversations = db.list_conversations()
    active_id = _normalize_active_conversation(conversations, requested_id)

    conversation = db.get_conversation(active_id) if active_id is not None else None
    messages = db.list_messages(active_id) if active_id is not None else []

    return render_template(
        "chat/index.html",
        conversations=conversations,
        conversation=conversation,
        active_id=active_id,
        messages=messages,
    )


@bp.post("/conversations")
def create_conversation() -> Any:
    conversation_id = db.create_conversation(_new_conversation_title())

    if _is_htmx():
        return _render_thread_and_sidebar(conversation_id)

    return redirect(url_for("web.index", conversation_id=conversation_id))


@bp.post("/conversations/<int:conversation_id>/delete")
def delete_conversation(conversation_id: int) -> Any:
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        abort(404)

    db.delete_conversation(conversation_id)
    if db.conversation_count() == 0:
        db.create_conversation("Conversation 1")

    conversations = db.list_conversations()
    next_active_id = int(conversations[0]["id"])

    if _is_htmx():
        return _render_thread_and_sidebar(next_active_id)

    return redirect(url_for("web.index", conversation_id=next_active_id))


@bp.get("/conversations/<int:conversation_id>")
def get_conversation(conversation_id: int) -> Any:
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        abort(404)

    if _is_htmx():
        return _render_thread_and_sidebar(conversation_id)

    return redirect(url_for("web.index", conversation_id=conversation_id))


@bp.post("/conversations/<int:conversation_id>/messages")
def post_message(conversation_id: int) -> Any:
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        abort(404)

    text = (request.form.get("message") or "").strip()
    if not text:
        abort(400, description="Message body cannot be empty")

    user_id = db.create_message(
        conversation_id=conversation_id,
        role="user",
        raw_text=text,
        rendered_html=render_user_html(text),
        status="complete",
    )
    assistant_id = db.create_message(
        conversation_id=conversation_id,
        role="assistant",
        raw_text="",
        rendered_html="",
        status="streaming",
    )
    db.update_conversation_timestamp(conversation_id)

    user_message = db.get_message(user_id)
    assistant_message = db.get_message(assistant_id)

    if user_message is None or assistant_message is None:
        abort(500)

    user_html = render_template("chat/_message.html", message=user_message)
    assistant_shell = render_template("chat/_assistant_stream_shell.html", message=assistant_message)
    return f"{user_html}{assistant_shell}"


@bp.post("/messages/<int:message_id>/feedback")
def message_feedback(message_id: int) -> Any:
    vote = (request.form.get("vote") or "").strip()
    if vote not in {"up", "down"}:
        abort(400, description="vote must be up or down")

    message = db.get_message(message_id)
    if message is None or message["role"] != "assistant":
        abort(404)

    db.upsert_feedback(message_id, vote)
    new_vote = db.get_feedback(message_id)
    return render_template("chat/_feedback.html", message_id=message_id, vote=new_vote)


@bp.post("/actions/fake")
def fake_action() -> str:
    action_id = (request.form.get("action_id") or "unknown").strip()
    message_id = request.form.get("message_id", type=int)

    action_map = {
        "summarize": "Generated summary placeholder returned.",
        "retry": "Retry queued in mock mode.",
        "cite_sources": "Mock citations: [source-1, source-2].",
    }
    result = action_map.get(action_id, f"Action '{action_id}' completed in mock mode.")

    return render_template(
        "chat/_fake_action_result.html",
        message_id=message_id,
        result=result,
    )
