from __future__ import annotations

from chat_hateoas import db


def test_index_renders_chat_shell(client) -> None:
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Chat HATEOAS" in body
    assert "htmx.org" in body
    assert "<time" in body


def test_create_conversation_htmx_returns_thread_and_sidebar_oob(client) -> None:
    response = client.post("/conversations", headers={"HX-Request": "true"})
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "id=\"thread-panel\"" in body
    assert "id=\"conversation-list\"" in body
    assert "hx-swap-oob=\"outerHTML\"" in body


def test_post_message_adds_user_and_assistant_shell(client, app) -> None:
    client.get("/")

    with app.app_context():
        conversation = db.list_conversations()[0]
        conversation_id = int(conversation["id"])

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        data={"message": "hello world"},
        headers={"HX-Request": "true"},
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "message--user" in body
    assert "sse-connect" in body

    with app.app_context():
        messages = db.list_messages(conversation_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["status"] == "streaming"


def test_delete_conversation_htmx_reloads_sidebar_and_thread(client, app) -> None:
    with app.app_context():
        keep_id = db.create_conversation("Keep")
        delete_id = db.create_conversation("Delete")

    response = client.post(
        f"/conversations/{delete_id}/delete",
        headers={"HX-Request": "true"},
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "id=\"thread-panel\"" in body
    assert "id=\"conversation-list\"" in body
    assert f"/conversations/{delete_id}" not in body

    with app.app_context():
        deleted = db.get_conversation(delete_id)
        kept = db.get_conversation(keep_id)
        assert deleted is None
        assert kept is not None


def test_debug_sse_panel_renders_when_enabled(client, app) -> None:
    app.config["DEBUG_SSE_STREAM"] = True
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Raw SSE Stream" in body
    assert "id=\"debug-events\"" in body
