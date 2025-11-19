# auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils import is_valid_username, password_has_spaces, load_users, save_users
import random, time, os
import sys

auth_bp = Blueprint("auth", __name__, url_prefix="")

@auth_bp.route("/")
def home():
    return redirect(url_for("auth.auth_page"))

@auth_bp.route("/auth")
def auth_page():
    return render_template("auth.html")

@auth_bp.route('/signup', methods=['POST'])
def signup():
    username = (request.form.get("username") or "")
    email = (request.form.get("email") or "").strip()
    password_raw = request.form.get("password") or ""

    if not is_valid_username(username):
        flash("Username cannot contain spaces!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    if password_has_spaces(password_raw):
        flash("Password cannot contain spaces!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    if not email:
        flash("Email required!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    users = load_users()
    if username in users:
        flash("Username already exists! Please login.", "error")
        return redirect(url_for('auth.auth_page'))

    users[username] = {"email": email, "pw_hash": generate_password_hash(password_raw)}
    save_users(users)
    flash("Registration successful! Please login.", "success")
    return redirect(url_for('auth.auth_page'))

@auth_bp.route("/login", methods=["POST"])
def login():
    username = (request.form.get("username") or "")
    password_raw = request.form.get("password") or ""

    if not is_valid_username(username):
        flash("Invalid username. Remove spaces.", "error")
        return redirect(url_for("auth.auth_page"))

    if password_has_spaces(password_raw):
        flash("Password cannot contain spaces.", "error")
        return redirect(url_for("auth.auth_page"))

    users = load_users()
    if username not in users:
        flash("User not found! Please register.", "error")
        return redirect(url_for("auth.auth_page") + "#register")

    if not check_password_hash(users[username]["pw_hash"], password_raw):
        flash("Incorrect password!", "error")
        return redirect(url_for("auth.auth_page"))

    flash("Login successful!", "success")

    # Lazy-load questions on first successful login (prevents slow startup)
    qs = []
    try:
        # import here so load_questions runs only when needed
        from utils import load_questions
        start = time.time()
        qs = load_questions() or []
        took = time.time() - start
        # debug log - prints to server console so you can see if load was heavy
        print(f"[auth.login] load_questions() returned {len(qs)} items in {took:.3f}s", file=sys.stderr)
    except Exception as e:
        # don't block login on errors; proceed with empty question set
        print("Warning: load_questions() failed in login():", e, file=sys.stderr)
        qs = []

    session["username"] = username
    session["questions"] = random.sample(qs, len(qs)) if qs else []
    session["index"] = 0
    session["answers"] = {}
    session["start_time"] = int(time.time())
    return redirect(url_for("exam.exam"))

@auth_bp.route("/logout_final")
def logout_final():
    session.clear()
    flash("Logged out!", "success")
    return redirect(url_for("auth.auth_page"))
