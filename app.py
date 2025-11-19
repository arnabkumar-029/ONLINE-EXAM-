# app.py
import os
import time
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecret123"

    from auth_routes import auth_bp
    from exam_routes import exam_bp
    from admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(admin_bp)

    if os.getenv("SKIP_MIGRATE") != "1":
        try:
            from utils import load_questions
            _ = load_questions()
        except Exception as e:
            print("Warning: load_questions() failed during startup:", e)

    return app

# 🔴 ADD THIS LINE (GLOBAL APP FOR GUNICORN)
app = create_app()

if __name__ == "__main__":
    t0 = time.time()
    # we already created app above, so just use it
    t1 = time.time()
    print(f"[STARTUP] create_app() took {t1-t0:.3f}s")

    # Local dev server
    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)
