from __future__ import annotations

import pytest

from chat_hateoas import create_app


@pytest.fixture()
def app(tmp_path):
    test_db = tmp_path / "test.sqlite"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(test_db),
            "MODEL_ID": "anthropic.claude-3-sonnet-mock",
            "MOCK_SEED": 7,
            "MAX_TOKENS": 512,
            "TEMPERATURE": 0.4,
            "STREAM_DELAY_MIN_MS": 0,
            "STREAM_DELAY_MAX_MS": 0,
        }
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
