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


def test_markdown_is_rendered_for_assistant_text() -> None:
    raw = (
        "# Heading\n\n"
        "This has **bold**, *italic*, and `code`.\n\n"
        "- one\n"
        "- two\n\n"
        "[docs](https://example.com)"
    )
    html = render_assistant_html(raw, message_id=3)

    assert "<h1>Heading</h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert "<code>code</code>" in html
    assert "<ul>" in html
    assert "<a href=\"https://example.com\"" in html


def test_markdown_escapes_unsafe_link_and_html() -> None:
    raw = '[click](javascript:alert(1)) <img src=x onerror=alert(1)>'
    html = render_assistant_html(raw, message_id=4)

    assert "href=\"javascript:alert(1)\"" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
