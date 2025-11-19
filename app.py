# app.py
import os
import time
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecret123"

    # register blueprints
    # NOTE: these imports should not perform heavy work at import-time.
    from auth_routes import auth_bp
    from exam_routes import exam_bp
    from admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(admin_bp)

    # Optionally pre-load/migrate questions on startup.
    # Set environment variable SKIP_MIGRATE=1 to skip this for faster startup.
    if os.getenv("SKIP_MIGRATE") != "1":
        try:
            # load_questions is cached in utils if implemented as suggested
            from utils import load_questions
            _ = load_questions()
        except Exception as e:
            # Don't crash the app on migration problems at startup; log and continue
            print("Warning: load_questions() failed during startup:", e)

    return app

if __name__ == "__main__":
    t0 = time.time()
    app = create_app()
    t1 = time.time()
    print(f"[STARTUP] create_app() took {t1-t0:.3f}s")

    # Start Flask dev server WITHOUT the auto-reloader for faster startup.
    # Use SKIP_MIGRATE=1 in your terminal to skip question pre-load if desired.
    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)
