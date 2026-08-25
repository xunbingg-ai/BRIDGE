import os

from flask import Flask, g, jsonify
from flask_cors import CORS


def _load_dotenv() -> None:
    """加载 backend/.env（git-ignored），在读取环境变量的模块导入前注入 DEEPSEEK_*/OPENAI_*。

    python-dotenv 未安装，用极简解析器即可（每行 KEY=VALUE，# 注释，跳过已存在的变量）。
    """
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()

import admin
import auth
import cases
import sessions
import ai_service
from database import get_db, init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.before_request
    def open_db():
        g.db = get_db()

    @app.teardown_request
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    app.register_blueprint(auth.bp)
    app.register_blueprint(cases.bp)
    app.register_blueprint(sessions.bp)
    app.register_blueprint(admin.bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "llm": ai_service.llm_mode_info()})

    return app


app = create_app()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
