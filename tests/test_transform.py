from __future__ import annotations

from chat_hateoas.services.transform import (
    ButtonSegment,
    parse_segments,
    render_assistant_html,
)


def test_parse_segments_identifies_button_and_tool_json() -> None:
    raw = (
        "Start text\n"
        "[[button:Summarize|summarize]]\n"
        '{"toolUse": {"toolName": "search", "input": {"q": "hello"}}}\n'
        "end"
    )

    segments = parse_segments(raw)

    assert any(isinstance(segment, ButtonSegment) for segment in segments)
    assert any(getattr(segment, "kind", None) == "tool_json" for segment in segments)


def test_render_assistant_html_escapes_unsafe_html() -> None:
    raw = "hello <script>alert(1)</script>"
    html = render_assistant_html(raw, message_id=1)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_malformed_marker_is_rendered_as_text() -> None:
    raw = "[[button:missing-action]]"
    html = render_assistant_html(raw, message_id=2)

    assert "fake-action" not in html
    assert "[[button:missing-action]]" in html
