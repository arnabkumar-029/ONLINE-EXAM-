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
    session["questions"] = []   # keep empty
    session["index"] = 0
    session["answers"] = {}
    session["start_time"] = int(time.time())
    return redirect(url_for("auth.exam_options"))

@auth_bp.route("/exam-options")
@auth_bp.route("/exam_options")
def exam_options():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))
    return render_template("exam_options.html")

@auth_bp.route("/course-exams")
def course_exams():
    from exam_routes import course_exams as _exam_course_exams
    return _exam_course_exams()

@auth_bp.route("/logout_final")
def logout_final():
    session.clear()
    flash("Logged out!", "success")
    return redirect(url_for("auth.auth_page"))

@auth_bp.route("/choose_exam")
def choose_exam():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))

    import json
    from utils import load_questions

    all_qs = load_questions()
    courses_dict = {}
    questions_meta = []

    for q in all_qs:
        cc = str(q.get("course_code") or "").strip().upper()
        cn = str(q.get("course_name") or "").strip()
        sub = str(q.get("subject") or "").strip()
        qtype = str(q.get("type") or "MCQ").strip().upper()
        level = str(q.get("level") or "Easy").strip()

        if cc:
            if cc not in courses_dict:
                courses_dict[cc] = {
                    "code": cc,
                    "name": cn or cc,
                    "subjects": set()
                }
            if sub:
                courses_dict[cc]["subjects"].add(sub)

        questions_meta.append({
            "course_code": cc,
            "subject": sub,
            "type": qtype,
            "level": level
        })

    course_list = []
    for cc, info in sorted(courses_dict.items()):
        name_str = info["name"]
        display_label = f"{cc} — {name_str}" if name_str and name_str != cc else cc
        course_list.append({
            "code": cc,
            "name": name_str,
            "display": display_label,
            "subjects": sorted(list(info["subjects"]))
        })

    return render_template(
        "choose_exam.html",
        course_list=course_list,
        questions_meta_json=json.dumps(questions_meta)
    )


