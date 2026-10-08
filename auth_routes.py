# auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils import (
    is_valid_username, password_has_spaces, load_users,
    parse_student_code, is_student_code_taken, is_email_taken, get_program_name, calculate_academic_year,
    get_student_identity_from_session_or_db, find_university_student_by_credentials, find_user_by_email,
    create_user_db
)
import random, time, os, uuid
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
    """
    Public registration for Outside / General Practice Students only.
    University students are pre-registered by the admin.
    """
    name = (request.form.get("name") or request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password_raw = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not name:
        flash("Name is required!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    if not email:
        flash("Email is required!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    # Strict duplicate email check (globally unique)
    if is_email_taken(email):
        flash("Email already exists. Please use a different email.", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    if not password_raw:
        flash("Password is required!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    if password_has_spaces(password_raw):
        flash("Password cannot contain spaces!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    if confirm_password and confirm_password != password_raw:
        flash("Passwords do not match!", "error")
        return redirect(url_for('auth.auth_page') + "#register")

    internal_id = f"user_{uuid.uuid4().hex[:10]}"
    try:
        create_user_db({
            "id": internal_id,
            "username": name,
            "name": name,
            "email": email,
            "pw_hash": generate_password_hash(password_raw),
            "user_type": "EXTERNAL"
        })
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('auth.auth_page') + "#register")

    flash("Practice account created successfully! Please login.", "success")
    return redirect(url_for('auth.auth_page') + "#practice")

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Handles authentication for:
      1. UNIVERSITY STUDENT: Email + Student Code + Password (ALL 3 REQUIRED)
      2. PRACTICE STUDENT: Email + Password
    """
    login_type = (request.form.get("login_type") or "").strip().upper()

    # University credentials (all 3 required)
    univ_email = (request.form.get("univ_email") or request.form.get("email") or "").strip().lower()
    univ_code = (request.form.get("univ_student_code") or request.form.get("student_code") or "").strip().upper()
    univ_password = request.form.get("univ_password") or ""

    # Practice credentials
    ext_login_id = (request.form.get("ext_email") or request.form.get("email") or request.form.get("username") or "").strip().lower()
    ext_password = request.form.get("ext_password") or request.form.get("password") or ""

    # Auto-detect login_type if not explicitly passed
    if not login_type:
        if univ_code:
            login_type = "UNIVERSITY"
        else:
            login_type = "EXTERNAL"

    users = load_users()
    matched_key = None
    user_record = None

    # ========================================================
    # 1. UNIVERSITY STUDENT LOGIN (Email + Student Code + Password)
    # ========================================================
    if login_type == "UNIVERSITY":
        if not univ_email or not univ_code or not univ_password:
            flash("All fields are required.", "error")
            return redirect(url_for("auth.auth_page"))

        # Verify all 3 credentials belong to the same University student account
        matched_user = find_university_student_by_credentials(univ_email, univ_code, univ_password)
        if not matched_user:
            flash("Invalid email, student code, or password.", "error")
            return redirect(url_for("auth.auth_page"))

        matched_key, user_record = matched_user
        display_name = user_record.get("username") or user_record.get("name") or matched_key
        flash(f"Welcome back, {display_name}!", "success")

    # ========================================================
    # 2. OUTSIDE / PRACTICE STUDENT LOGIN (Email + Password)
    # ========================================================
    else:
        if not ext_login_id or not ext_password:
            flash("Invalid email or password.", "error")
            return redirect(url_for("auth.auth_page") + "#practice")

        # Primary lookup by email
        for ukey, udata in users.items():
            if not isinstance(udata, dict):
                continue
            rec_email = str(udata.get("email") or "").strip().lower()
            if rec_email == ext_login_id:
                matched_key = ukey
                user_record = udata
                break

        # Fallback to key or id
        if not user_record:
            for ukey, udata in users.items():
                if not isinstance(udata, dict):
                    continue
                if ukey.lower() == ext_login_id or str(udata.get("id") or "").lower() == ext_login_id:
                    matched_key = ukey
                    user_record = udata
                    break

        if not matched_key or not user_record:
            flash("Invalid email or password.", "error")
            return redirect(url_for("auth.auth_page") + "#practice")

        rec_type = user_record.get("user_type") or ("UNIVERSITY" if (user_record.get("student_code") or user_record.get("program_code")) else "EXTERNAL")
        if rec_type == "UNIVERSITY":
            flash("This account is a registered University Student. Please use University Student Login with your Email, Student Code, and Password.", "error")
            return redirect(url_for("auth.auth_page"))

        pw_hash = user_record.get("pw_hash", "")
        if not pw_hash or not check_password_hash(pw_hash, ext_password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("auth.auth_page") + "#practice")

        flash("Login successful!", "success")

    # Store authoritative identity in session (NO passwords)
    user_type = user_record.get("user_type", "EXTERNAL")
    display_name = user_record.get("username") or user_record.get("name") or matched_key
    internal_id = str(user_record.get("id") or matched_key)

    session["username"] = display_name
    session["name"] = display_name
    session["student_id"] = internal_id
    session["user_id"] = internal_id
    session["email"] = user_record.get("email", "")
    session["user_type"] = user_type
    session["student_code"] = user_record.get("student_code", "")
    session["university_code"] = user_record.get("university_code", "")
    session["program_code"] = user_record.get("program_code", "")
    session["program_name"] = user_record.get("program_name") or (get_program_name(user_record.get("program_code", "")) if user_record.get("program_code") else "")
    session["admission_year"] = user_record.get("admission_year", "")

    session["academic_year"] = user_record.get("academic_year") or "N/A"

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

    # Refresh academic identity in session from DB
    student_info = get_student_identity_from_session_or_db(session)
    return render_template("exam_options.html", student_info=student_info)

@auth_bp.route("/course-exams")
def course_exams():
    if "username" not in session:
        flash("Please log in to view course examinations.", "error")
        return redirect(url_for("auth.auth_page"))

    student_info = get_student_identity_from_session_or_db(session)
    if student_info.get("user_type") != "UNIVERSITY":
        flash("Official university examinations are available only to registered university students.", "error")
        return redirect(url_for("auth.exam_options"))

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


