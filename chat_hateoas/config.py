from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DATABASE = os.environ.get("DATABASE_PATH", os.path.join("instance", "chat.db"))
    MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-sonnet-mock")
    MOCK_SEED = int(os.environ.get("MOCK_SEED", "13"))
    MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
    TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))
    STREAM_DELAY_MIN_MS = int(os.environ.get("STREAM_DELAY_MIN_MS", "90"))
    STREAM_DELAY_MAX_MS = int(os.environ.get("STREAM_DELAY_MAX_MS", "180"))
    TOOL_CALL_DELAY_MS = int(os.environ.get("TOOL_CALL_DELAY_MS", "5000"))
    DEBUG_SSE_STREAM = _env_bool("DEBUG_SSE_STREAM", default=False)
