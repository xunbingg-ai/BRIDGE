from flask import Flask, g, jsonify
from flask_cors import CORS

import admin
import auth
import cases
import sessions
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
        return jsonify({"status": "ok"})

    return app


app = create_app()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
