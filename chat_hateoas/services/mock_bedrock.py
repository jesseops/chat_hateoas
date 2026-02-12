from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator


LEAD_SENTENCES = [
    "Here is a practical answer you can use immediately.",
    "Good question. I can give you a concise plan and a concrete next step.",
    "Below is a working response with assumptions called out clearly.",
]

CAPABILITY_POINTS = [
    "Use **server-rendered fragments** so the backend stays the source of truth.",
    "Keep client behavior limited to interaction state and minor UX enhancements.",
    "Stream partial updates in small chunks so users see immediate progress.",
    "Persist every assistant response with metadata for replay and debugging.",
    "Render model output as Markdown-to-HTML with strict safety controls.",
]

RISK_POINTS = [
    "Avoid rendering arbitrary model HTML directly in the browser.",
    "Do not keep long-lived SSE nodes mounted after message completion.",
    "Treat tool payloads as data and render them in escaped blocks.",
    "Validate all action IDs server-side before performing any operation.",
]

FOLLOW_UP_PROMPTS = [
    "If you want, I can adapt this into Flask route signatures next.",
    "I can also provide a migration checklist for your existing prototype.",
    "I can turn this into implementation tasks with acceptance criteria.",
]

REFERENCE_LINKS = [
    ("HTMX swap behavior", "https://htmx.org/attributes/hx-swap/"),
    ("HTMX SSE extension", "https://htmx.org/extensions/sse/"),
    ("Flask patterns", "https://flask.palletsprojects.com/"),
]

BUTTON_ACTIONS = [
    ("Summarize", "summarize"),
    ("Retry answer", "retry"),
    ("Show citations", "cite_sources"),
]

TOOL_SNIPPETS = [
    '{"toolUse": {"toolName": "web_search", "input": {"query": "weather in boston"}}}',
    '{"toolResult": {"toolName": "web_search", "status": "ok", "items": 3}}',
    '{"toolUse": {"toolName": "calculator", "input": {"expression": "144/12"}}}',
]


@dataclass(slots=True)
class MockBedrockClient:
    seed: int | None = None

    def converse_stream(
        self,
        messages: list[dict[str, str]],
        model_id: str,
        max_tokens: int,
        temperature: float,
    ) -> Iterator[dict]:
        rng = random.Random(self.seed)

        response_text = self._build_response_text(rng)
        chunks = self._chunk_text(response_text, rng)

        yield {"type": "messageStart", "message": {"role": "assistant"}}
        yield {"type": "contentBlockStart", "contentBlockIndex": 0, "start": {"text": ""}}

        for chunk in chunks:
            yield {
                "type": "contentBlockDelta",
                "contentBlockIndex": 0,
                "delta": {"text": chunk},
            }

        yield {"type": "contentBlockStop", "contentBlockIndex": 0}
        yield {
            "type": "messageStop",
            "stopReason": rng.choice(["end_turn", "max_tokens"]),
        }

        input_tokens = max(20, sum(len(message.get("content", "")) for message in messages) // 4)
        output_tokens = max(24, len(response_text) // 4)
        yield {
            "type": "metadata",
            "metadata": {
                "modelId": model_id,
                "usage": {
                    "inputTokens": min(input_tokens, max_tokens),
                    "outputTokens": min(output_tokens, max_tokens),
                },
                "temperature": temperature,
            },
        }

    def _build_response_text(self, rng: random.Random) -> str:
        band = rng.choice(["short", "medium", "long"])
        bullet_count = {"short": 2, "medium": 3, "long": 5}[band]
        risk_count = {"short": 1, "medium": 2, "long": 3}[band]

        topic = rng.choice(
            [
                "chat architecture",
                "streaming UX",
                "response rendering",
                "feedback workflows",
                "integration reliability",
            ]
        )
        lead = rng.choice(LEAD_SENTENCES)

        text_parts: list[str] = []
        text_parts.append(f"### Recommendation: {topic.title()}")
        text_parts.append(lead)
        text_parts.append("")
        text_parts.append("#### What to implement")
        for point in rng.sample(CAPABILITY_POINTS, k=bullet_count):
            text_parts.append(f"- {point}")

        text_parts.append("")
        text_parts.append("#### Why this works")
        text_parts.append(
            "This keeps your interface **simple**, improves reliability, and preserves a clear "
            "request/response boundary while still supporting rich interactions."
        )

        if band in {"medium", "long"}:
            text_parts.append("")
            text_parts.append("#### Example payload handling")
            text_parts.append("```json")
            text_parts.append(
                '{ "event": "contentBlockDelta", "delta": { "text": "partial markdown chunk" } }'
            )
            text_parts.append("```")

        text_parts.append("")
        text_parts.append("#### Risks to watch")
        for point in rng.sample(RISK_POINTS, k=risk_count):
            text_parts.append(f"- {point}")

        if band == "long":
            ref_label, ref_url = rng.choice(REFERENCE_LINKS)
            text_parts.append("")
            text_parts.append(f"Reference: [{ref_label}]({ref_url})")

        text_parts.append("")
        text_parts.append(rng.choice(FOLLOW_UP_PROMPTS))

        if rng.random() < 0.9:
            button_label, action_id = rng.choice(BUTTON_ACTIONS)
            text_parts.append("")
            text_parts.append(f"[[button:{button_label}|{action_id}]]")

        if rng.random() < 0.8:
            text_parts.append("")
            text_parts.append(rng.choice(TOOL_SNIPPETS))

        if rng.random() < 0.35:
            text_parts.append(rng.choice(TOOL_SNIPPETS))

        return "\n".join(text_parts)

    def _chunk_text(self, text: str, rng: random.Random) -> list[str]:
        chunks: list[str] = []
        cursor = 0
        while cursor < len(text):
            size = rng.randint(20, 72)
            chunks.append(text[cursor : cursor + size])
            cursor += size
        return chunks
