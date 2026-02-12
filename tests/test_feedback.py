from __future__ import annotations

from chat_hateoas import db


def test_feedback_upsert_is_mutable(client, app) -> None:
    with app.app_context():
        conversation_id = db.create_conversation("Feedback Test")
        assistant_id = db.create_message(
            conversation_id=conversation_id,
            role="assistant",
            raw_text="done",
            rendered_html="done",
            status="complete",
        )

    first = client.post(
        f"/messages/{assistant_id}/feedback",
        data={"vote": "up"},
        headers={"HX-Request": "true"},
    )
    assert first.status_code == 200
    assert "active" in first.get_data(as_text=True)

    second = client.post(
        f"/messages/{assistant_id}/feedback",
        data={"vote": "down"},
        headers={"HX-Request": "true"},
    )
    body = second.get_data(as_text=True)

    assert second.status_code == 200
    assert "down" in body

    with app.app_context():
        assert db.get_feedback(assistant_id) == "down"
