from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape

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
                    "hx-swap=\"innerHTML\">"
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

        output.append(escape(segment.value).replace("\n", "<br>"))

    if saw_action:
        output.append(f"<div id=\"action-result-{message_id}\" class=\"action-result\"></div>")

    return "".join(output)


def render_user_html(raw_text: str) -> str:
    return escape(raw_text).replace("\n", "<br>")
