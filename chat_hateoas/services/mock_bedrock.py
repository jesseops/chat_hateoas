from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator


LOREM_SENTENCES = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    "Praesent elementum facilisis leo vel fringilla est ullamcorper eget nulla.",
    "Amet consectetur adipiscing elit pellentesque habitant morbi tristique senectus et netus.",
    "Vitae aliquet nec ullamcorper sit amet risus nullam eget felis.",
    "Nibh nisl condimentum id venenatis a condimentum vitae sapien pellentesque.",
    "Velit euismod in pellentesque massa placerat duis ultricies lacus sed.",
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
        if band == "short":
            count = rng.randint(2, 4)
        elif band == "medium":
            count = rng.randint(5, 8)
        else:
            count = rng.randint(9, 14)

        text_parts = [rng.choice(LOREM_SENTENCES) for _ in range(count)]

        if rng.random() < 0.9:
            button_label, action_id = rng.choice(BUTTON_ACTIONS)
            text_parts.append(f"[[button:{button_label}|{action_id}]]")

        if rng.random() < 0.8:
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
