from __future__ import annotations

from chat_hateoas import db


def test_index_renders_chat_shell(client) -> None:
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Chat HATEOAS" in body
    assert "htmx.org" in body


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
