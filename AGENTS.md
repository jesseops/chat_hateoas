# AGENTS.md

This file defines project-specific guidance for coding agents working in this repository.

## Maintenance Rule

- Keep this file current as the project evolves.
- Update `AGENTS.md` in the same change set when architecture, workflows, conventions, commands, or core behavior changes.

## Project Overview

- Stack: Flask, HTMX, AlpineJS, SQLite, SSE.
- Package: `chat_hateoas`.
- Main goal: server-rendered chat UI with minimal client-side JavaScript.
- Mock LLM: Bedrock-like streaming events with Markdown output and tool/button markers.
- Conversations support deletion and timestamp display in list/thread views.
- Messages display per-message timestamps in the thread.
- Thread autoscroll is sticky: it follows new content only while the user is at/near bottom.

## Repository Layout

- `chat_hateoas/__init__.py`: app factory (`create_app`).
- `chat_hateoas/routes/web.py`: page + HTMX endpoints.
- `chat_hateoas/routes/stream.py`: SSE streaming endpoint.
- `chat_hateoas/services/mock_bedrock.py`: mock model output generator.
- `chat_hateoas/services/transform.py`: safe transform and Markdown rendering.
- `chat_hateoas/db.py`, `chat_hateoas/schema.sql`: persistence layer.
- `templates/`: Jinja templates and HTMX fragments.
  - `templates/chat/_icons/`: shared inline SVG icon partials.
- `static/app.css`: styles.
- `tests/`: pytest suite.

## Local Commands

Use `uv` for all dependency and run workflows.

- Install/sync deps: `uv sync --dev`
- Run app: `uv run flask --app chat_hateoas:create_app --debug run`
- Run tests: `uv run pytest -q`

## Coding Standards

- Keep logic server-first; avoid adding unnecessary frontend state.
- Prefer HTMX interactions over custom JavaScript.
- Keep Alpine usage minimal (UI state only).
- Preserve safe rendering rules:
  - Do not render arbitrary model HTML.
  - Keep tool payloads escaped.
  - Keep button rendering whitelist-based.
- Follow existing naming and module boundaries.
- Use ASCII unless file already requires Unicode.
- Prefer inline SVG icon partials from `templates/chat/_icons/` for UI iconography.

## Streaming and SSE Notes

- SSE event flow should remain Bedrock-like (`messageStart`, `contentBlockDelta`, etc.).
- `ui_done` must replace the entire streaming message shell (to prevent reconnect loops).
- Keep stream pacing configurable via:
  - `STREAM_DELAY_MIN_MS`
  - `STREAM_DELAY_MAX_MS`

## Database and Data Model

- SQLite file defaults to `instance/chat.db`.
- Feedback model is one mutable vote per assistant message (`up`/`down`).
- Conversation deletion is performed via `POST /conversations/<id>/delete`.
- If schema changes are required, update both:
  - `chat_hateoas/schema.sql`
  - data access functions in `chat_hateoas/db.py`

## Testing Expectations

- Run full pytest suite for behavior changes.
- Add/update tests for:
  - Transform safety (escaping/sanitization).
  - Streaming lifecycle behavior.
  - Feedback persistence behavior.
- Keep tests deterministic when using random output (seeded behavior).

## Change Discipline

- Make focused, minimal patches.
- Do not introduce unrelated refactors.
- Keep README usage commands aligned with actual app entrypoints.
- If adding new HTMX swaps, include transition behavior used in this repo.

## Common Pitfalls

- Leaving SSE attributes on completed messages causes reconnection loops.
- Rendering model-generated HTML directly introduces XSS risk.
- Moving template/static folders without updating Flask app factory breaks rendering.
