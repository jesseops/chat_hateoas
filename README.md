# chat_hateoas

Flask scaffold for a HATEOAS-style chat UI using HTMX + AlpineJS, with:

- Multi-conversation chat interface
- SQLite persistence
- Mock Bedrock-like SSE streaming responses
- Safe server-side transformation of model markers into UI controls
- Persisted per-assistant-message feedback (`up` / `down`)

## Quickstart (`uv`)

1. Install `uv` on your machine.
2. Sync dependencies:
   ```bash
   uv sync --dev
   ```
3. Run the app:
   ```bash
   uv run flask --app chat_hateoas:create_app --debug run
   ```
4. Run tests:
   ```bash
   uv run pytest
   ```

The default SQLite database path is `instance/chat.db`.

## Notes

- Streaming endpoint emits both Bedrock-like event names and UI events for HTMX SSE swapping.
- Model output supports safe marker transforms:
  - `[[button:Label|action_id]]` -> fake action button
  - JSON lines with `toolUse` / `toolResult` -> rendered tool blocks
