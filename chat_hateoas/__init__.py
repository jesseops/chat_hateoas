from __future__ import annotations

from pathlib import Path

from flask import Flask

from chat_hateoas import db
from chat_hateoas.config import Config
from chat_hateoas.routes.stream import bp as stream_bp
from chat_hateoas.routes.web import bp as web_bp


def create_app(test_config: dict | None = None) -> Flask:
    repo_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(repo_root / "templates"),
        static_folder=str(repo_root / "static"),
        instance_path=str(repo_root / "instance"),
    )
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    db_path = Path(app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    app.register_blueprint(web_bp)
    app.register_blueprint(stream_bp)

    with app.app_context():
        db.init_db()

    return app
