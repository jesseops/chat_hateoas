from __future__ import annotations

import json
import random
import time
from typing import Any, Iterator

from flask import Blueprint, Response, abort, current_app, stream_with_context

from chat_hateoas import db
from chat_hateoas.services.mock_bedrock import MockBedrockClient
from chat_hateoas.services.render import render_stream_delta, render_stream_done
from chat_hateoas.services.transform import render_assistant_html

bp = Blueprint("stream", __name__)


def _sse_event(event_name: str, data: str) -> str:
    lines = data.splitlines() or [""]
    payload = [f"event: {event_name}"]
    payload.extend(f"data: {line}" for line in lines)
    payload.append("")
    return "\n".join(payload) + "\n"


def _sse_json(event_name: str, payload: dict[str, Any]) -> str:
    return _sse_event(event_name, json.dumps(payload))


@bp.get("/responses/<int:assistant_message_id>/stream")
def stream_response(assistant_message_id: int) -> Response:
    message = db.get_message(assistant_message_id)
    if message is None or message["role"] != "assistant":
        abort(404)

    if message["status"] not in {"streaming", "complete"}:
        abort(409, description="message not streamable")

    conversation_id = int(message["conversation_id"])
    history = db.list_history_for_conversation(conversation_id, up_to_message_id=assistant_message_id)

    model_id = str(current_app.config["MODEL_ID"])
    max_tokens = int(current_app.config["MAX_TOKENS"])
    temperature = float(current_app.config["TEMPERATURE"])
    seed = int(current_app.config["MOCK_SEED"]) + assistant_message_id
    delay_min_ms = int(current_app.config.get("STREAM_DELAY_MIN_MS", 30))
    delay_max_ms = int(current_app.config.get("STREAM_DELAY_MAX_MS", 90))
    if delay_min_ms < 0:
        delay_min_ms = 0
    if delay_max_ms < delay_min_ms:
        delay_max_ms = delay_min_ms

    client = MockBedrockClient(seed=seed)
    delay_rng = random.Random(seed + 1000)

    @stream_with_context
    def generate() -> Iterator[str]:
        assembled_text = ""
        raw_event_count = 0
        tool_events: list[dict[str, Any]] = []
        stop_reason = "end_turn"
        input_tokens = 0
        output_tokens = 0
        start = time.monotonic()

        try:
            for event in client.converse_stream(
                messages=history,
                model_id=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                raw_event_count += 1
                event_type = str(event.get("type", "unknown"))
                yield _sse_json(event_type, event)

                if event_type == "messageStop":
                    stop_reason = str(event.get("stopReason", stop_reason))

                if event_type == "metadata":
                    metadata = event.get("metadata", {})
                    usage = metadata.get("usage", {})
                    input_tokens = int(usage.get("inputTokens", 0))
                    output_tokens = int(usage.get("outputTokens", 0))

                if event_type == "contentBlockDelta":
                    delta = event.get("delta", {})
                    if isinstance(delta, dict) and "text" in delta:
                        assembled_text += str(delta["text"])

                        rendered = render_assistant_html(
                            raw_text=assembled_text,
                            message_id=assistant_message_id,
                        )
                        yield _sse_event("ui_delta", render_stream_delta(rendered))
                        if delay_max_ms > 0:
                            sleep_ms = (
                                delay_rng.randint(delay_min_ms, delay_max_ms)
                                if delay_max_ms > delay_min_ms
                                else delay_max_ms
                            )
                            if sleep_ms > 0:
                                time.sleep(sleep_ms / 1000.0)

                    if isinstance(delta, dict) and any(key in delta for key in ("toolUse", "toolResult")):
                        tool_events.append(delta)

            final_html = render_assistant_html(assembled_text, assistant_message_id)
            db.update_message(
                message_id=assistant_message_id,
                raw_text=assembled_text,
                rendered_html=final_html,
                status="complete",
            )
            db.update_conversation_timestamp(conversation_id)

            latency_ms = int((time.monotonic() - start) * 1000)
            db.save_assistant_metadata(
                message_id=assistant_message_id,
                provider="mock-bedrock",
                model_id=model_id,
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                tool_events=tool_events,
                raw_event_count=raw_event_count,
            )

            completed_message = db.get_message(assistant_message_id)
            if completed_message is None:
                abort(404)

            done_html = render_stream_done(completed_message)
            yield _sse_event("ui_done", done_html)
        except Exception:
            db.update_message(
                message_id=assistant_message_id,
                raw_text=assembled_text,
                rendered_html=render_assistant_html(assembled_text, assistant_message_id),
                status="error",
            )
            raise

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
