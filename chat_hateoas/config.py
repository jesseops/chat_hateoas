from __future__ import annotations

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DATABASE = os.environ.get("DATABASE_PATH", os.path.join("instance", "chat.db"))
    MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-sonnet-mock")
    MOCK_SEED = int(os.environ.get("MOCK_SEED", "13"))
    MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
    TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))
