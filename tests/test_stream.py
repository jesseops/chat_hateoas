from __future__ import annotations

from chat_hateoas import db


def test_stream_emits_events_and_persists_metadata(client, app) -> None:
    with app.app_context():
        conversation_id = db.create_conversation("Stream Test")
        db.create_message(
            conversation_id=conversation_id,
            role="user",
            raw_text="Tell me something",
            rendered_html="Tell me something",
            status="complete",
        )
        assistant_id = db.create_message(
            conversation_id=conversation_id,
            role="assistant",
            raw_text="",
            rendered_html="",
            status="streaming",
        )

    response = client.get(f"/responses/{assistant_id}/stream", buffered=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "event: messageStart" in body
    assert "event: contentBlockDelta" in body
    assert "event: ui_delta" in body
    assert "event: ui_done" in body
    assert "Running " in body
    assert "Tool completed:" in body
    assert 'hx-swap-oob="outerHTML"' in body

    with app.app_context():
        updated_message = db.get_message(assistant_id)
        metadata = db.fetch_one(
            "SELECT * FROM assistant_metadata WHERE message_id = ?",
            (assistant_id,),
        )

        assert updated_message is not None
        assert updated_message["status"] == "complete"
        assert metadata is not None
        assert metadata["provider"] == "mock-bedrock"


def test_stream_for_completed_message_returns_done_only(client, app) -> None:
    with app.app_context():
        conversation_id = db.create_conversation("Done Stream Test")
        assistant_id = db.create_message(
            conversation_id=conversation_id,
            role="assistant",
            raw_text="already done",
            rendered_html="<p>done</p>",
            status="complete",
        )

    response = client.get(f"/responses/{assistant_id}/stream", buffered=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "event: ui_done" in body
    assert "event: contentBlockDelta" not in body
