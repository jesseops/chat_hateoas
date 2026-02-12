from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from urllib.parse import urlparse

BUTTON_PATTERN = re.compile(r"\[\[button:([^|\]]+)\|([A-Za-z0-9_./:-]+)\]\]")
TOOL_KEYS = {"toolUse", "toolResult"}


@dataclass(slots=True)
class Segment:
    kind: str
    value: str


@dataclass(slots=True)
class ButtonSegment:
    label: str
    action_id: str


INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
ITALIC_PATTERN = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_PATTERN = re.compile(r"^\s*[-*]\s+(.*)$")


def _tokenize_pattern(
    text: str,
    pattern: re.Pattern[str],
    render_match,
    stash,
) -> str:
    def _replace(match: re.Match[str]) -> str:
        return stash(render_match(match))

    return pattern.sub(_replace, text)


def _is_safe_http_url(candidate: str) -> bool:
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _render_inline_markdown(text: str) -> str:
    tokens: list[str] = []

    def stash(html: str) -> str:
        token = f"@@MDTOK{len(tokens)}@@"
        tokens.append(html)
        return token

    transformed = text
    transformed = _tokenize_pattern(
        transformed,
        INLINE_CODE_PATTERN,
        lambda m: f"<code>{escape(m.group(1))}</code>",
        stash,
    )
    transformed = _tokenize_pattern(
        transformed,
        LINK_PATTERN,
        lambda m: (
            f"<a href=\"{escape(m.group(2), quote=True)}\" target=\"_blank\" rel=\"noopener noreferrer\">"
            f"{escape(m.group(1))}</a>"
            if _is_safe_http_url(m.group(2))
            else escape(m.group(0))
        ),
        stash,
    )
    transformed = _tokenize_pattern(
        transformed,
        BOLD_PATTERN,
        lambda m: f"<strong>{escape(m.group(1))}</strong>",
        stash,
    )
    transformed = _tokenize_pattern(
        transformed,
        ITALIC_PATTERN,
        lambda m: f"<em>{escape(m.group(1))}</em>",
        stash,
    )

    escaped_body = escape(transformed)
    for idx, html in enumerate(tokens):
        escaped_body = escaped_body.replace(f"@@MDTOK{idx}@@", html)
    return escaped_body


def _flush_paragraph(output: list[str], paragraph_lines: list[str]) -> None:
    if not paragraph_lines:
        return
    inline = _render_inline_markdown("\n".join(paragraph_lines))
    inline_with_breaks = inline.replace("\n", "<br>")
    output.append(f"<p>{inline_with_breaks}</p>")
    paragraph_lines.clear()


def render_markdown_html(raw_text: str) -> str:
    lines = raw_text.splitlines()
    output: list[str] = []
    paragraph_lines: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for line in lines:
        if line.startswith("```"):
            _flush_paragraph(output, paragraph_lines)
            close_list()

            if in_code:
                code_body = escape("\n".join(code_lines))
                output.append(f"<pre><code>{code_body}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            _flush_paragraph(output, paragraph_lines)
            close_list()
            continue

        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            _flush_paragraph(output, paragraph_lines)
            close_list()
            level = len(heading_match.group(1))
            heading_body = _render_inline_markdown(heading_match.group(2).strip())
            output.append(f"<h{level}>{heading_body}</h{level}>")
            continue

        list_match = LIST_PATTERN.match(line)
        if list_match:
            _flush_paragraph(output, paragraph_lines)
            if not in_list:
                output.append("<ul>")
                in_list = True
            item_body = _render_inline_markdown(list_match.group(1).strip())
            output.append(f"<li>{item_body}</li>")
            continue

        paragraph_lines.append(line)

    if in_code:
        code_body = escape("\n".join(code_lines))
        output.append(f"<pre><code>{code_body}</code></pre>")

    _flush_paragraph(output, paragraph_lines)
    close_list()
    return "".join(output)


def _append_text(segments: list[Segment | ButtonSegment], text: str) -> None:
    if not text:
        return
    if segments and isinstance(segments[-1], Segment) and segments[-1].kind == "text":
        segments[-1].value += text
        return
    segments.append(Segment(kind="text", value=text))


def _parse_text_tool_lines(text: str) -> list[Segment]:
    parsed: list[Segment] = []
    if not text:
        return parsed

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                parsed.append(Segment(kind="text", value=line))
                continue

            if isinstance(payload, dict) and any(key in payload for key in TOOL_KEYS):
                parsed.append(Segment(kind="tool_json", value=json.dumps(payload, sort_keys=True, indent=2)))
                if line.endswith("\n"):
                    parsed.append(Segment(kind="text", value="\n"))
                continue

        parsed.append(Segment(kind="text", value=line))

    return parsed


def parse_segments(raw_text: str) -> list[Segment | ButtonSegment]:
    segments: list[Segment | ButtonSegment] = []
    cursor = 0
    for match in BUTTON_PATTERN.finditer(raw_text):
        before = raw_text[cursor : match.start()]
        before_segments = _parse_text_tool_lines(before)
        for item in before_segments:
            if item.kind == "text":
                _append_text(segments, item.value)
            else:
                segments.append(item)

        label = match.group(1).strip()
        action_id = match.group(2).strip()
        if label and action_id:
            segments.append(ButtonSegment(label=label, action_id=action_id))
        else:
            _append_text(segments, match.group(0))

        cursor = match.end()

    tail = raw_text[cursor:]
    for item in _parse_text_tool_lines(tail):
        if item.kind == "text":
            _append_text(segments, item.value)
        else:
            segments.append(item)

    return segments


def render_assistant_html(raw_text: str, message_id: int) -> str:
    output: list[str] = []
    saw_action = False

    for segment in parse_segments(raw_text):
        if isinstance(segment, ButtonSegment):
            saw_action = True
            hx_vals = json.dumps({"action_id": segment.action_id, "message_id": message_id})
            output.append(
                (
                    "<button class=\"fake-action\" type=\"button\" "
                    "hx-post=\"/actions/fake\" "
                    f"hx-vals='{escape(hx_vals)}' "
                    f"hx-target=\"#action-result-{message_id}\" "
                    "hx-swap=\"innerHTML transition:true\">"
                    f"{escape(segment.label)}"
                    "</button>"
                )
            )
            continue

        if segment.kind == "tool_json":
            output.append(
                "<details class=\"tool-block\">"
                "<summary>Tool payload</summary>"
                f"<pre>{escape(segment.value)}</pre>"
                "</details>"
            )
            continue

        output.append(render_markdown_html(segment.value))

    if saw_action:
        output.append(f"<div id=\"action-result-{message_id}\" class=\"action-result\"></div>")

    return "".join(output)


def render_user_html(raw_text: str) -> str:
    return escape(raw_text).replace("\n", "<br>")
