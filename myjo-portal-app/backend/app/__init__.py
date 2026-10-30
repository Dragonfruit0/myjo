import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from .config import Config
from .extensions import db
from .util import ApiError


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if app.config["SECRET_KEY"] == "change-me-in-production" and not app.config.get("TESTING"):
        app.logger.warning("SECRET_KEY is the built-in default. Set SECRET_KEY in .env before going live.")
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    db.init_app(app)

    from .api import auth, meta, requests_api, academic, portal, admin, dashboard, reports, files
    for bp in (auth.bp, meta.bp, requests_api.bp, academic.bp, portal.bp, admin.bp, dashboard.bp, reports.bp, files.bp):
        app.register_blueprint(bp, url_prefix="/api")

    @app.errorhandler(ApiError)
    def _api_error(e):
        db.session.rollback()
        return e.response()

    @app.errorhandler(HTTPException)
    def _http(e):
        return jsonify({"error": e.description or e.name}), e.code

    @app.errorhandler(Exception)
    def _unexpected(e):
        db.session.rollback()
        app.logger.exception("Unhandled error")
        return jsonify({"error": "Something went wrong on the server. Please try again."}), 500

    @app.after_request
    def _headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    @app.get("/api/health")
    def health():
        return {"ok": True}

    from .cli import register
    register(app)
    return app
