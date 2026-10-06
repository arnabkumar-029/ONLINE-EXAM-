# admin_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from utils import (
    load_questions,
    save_json,
    load_users,
    save_users,
    load_results,
    save_results,
    _migrate_one_question,
    _fix_type_to_capital,
    load_course_exams,
    save_course_exams,
    get_course_exam_by_id,
    get_exam_live_status,
    get_course_exam_stats,
    get_unique_courses_and_subjects,
    get_matching_questions,
    get_program_name,
    calculate_academic_year,
    get_available_programs,
    get_available_admission_years,
    get_academic_years,
    get_all_students_for_eligibility,
    count_eligible_students,
    is_email_taken,
    is_student_code_taken,
    group_questions_by_course_subject,
)
import re
import json
import os
import time
import random
import uuid
import socket
import threading
import urllib.request
import urllib.error
from dotenv import load_dotenv  # 👈 load from .env

# -----------------------
# Load environment vars
# -----------------------
load_dotenv()  # This reads .env file locally

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
if not GEMINI_API_KEY:
    print("[admin_routes] Note: GEMINI_API_KEY is not set in environment. AI question generation will return a configuration error when called.")

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
print(f"[AI] Gemini model: {GEMINI_MODEL}")

# Concurrency lock to prevent simultaneous heavy AI generation requests from exhausting memory on Render
_AI_GENERATION_LOCK = threading.BoundedSemaphore(value=1)

# Blueprint MUST be defined before any @admin_bp.route()
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Simple hard-coded admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# =======================
#  Student data helpers
# =======================
def _pct(record):
    """Score as a percentage for one history record."""
    total = record.get("total") or 0
    if not total:
        return 0.0
    return (record.get("score", 0) / total) * 100


def _student_summary(username, results):
    """Attempts / latest / best-score summary for one student."""
    history = results.get(username, {}).get("history", []) or []
    if not history:
        return {
            "attempts": 0,
            "latest_score": None,
            "latest_total": None,
            "best_pct": 0.0,
        }

    latest = history[-1]
    best = max(history, key=_pct)

    return {
        "attempts": len(history),
        "latest_score": latest.get("score"),
        "latest_total": latest.get("total"),
        "best_pct": round(_pct(best), 1),
    }


def _flatten_history(results):
    """Every exam attempt, by every student, as one flat list (newest first)."""
    rows = []
    users = load_users()
    for user_key, udata in results.items():
        disp_name = user_key
        if user_key in users and isinstance(users[user_key], dict):
            disp_name = users[user_key].get("name") or users[user_key].get("username") or user_key
        for rec in udata.get("history", []) or []:
            rows.append({
                "username": disp_name,
                "date": rec.get("date", ""),
                "score": rec.get("score", 0),
                "total": rec.get("total", 0),
                "time_taken": rec.get("time_taken"),
                "exam_title": rec.get("exam_title", "Practice Examination"),
                "course_code": rec.get("course_code", ""),
            })
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def _leaderboard_rows(results):
    """One row per student who has attempted at least one exam, ranked by best %."""
    rows = []
    users = load_users()
    for user_key, udata in results.items():
        history = udata.get("history", []) or []
        if not history:
            continue
        disp_name = user_key
        if user_key in users and isinstance(users[user_key], dict):
            disp_name = users[user_key].get("name") or users[user_key].get("username") or user_key
        best = max(history, key=_pct)
        rows.append({
            "username": disp_name,
            "score": best.get("score", 0),
            "total": best.get("total", 0),
            "pct": round(_pct(best), 1),
            "time_taken": best.get("time_taken") or "N/A",
            "attempts": len(history),
        })
    rows.sort(key=lambda r: (r["pct"], r["score"]), reverse=True)
    return rows


# =======================
#  Admin login / logout
# =======================
@admin_bp.route("", methods=["GET", "POST"])
@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (
            request.form.get("username") == ADMIN_USERNAME
            and request.form.get("password") == ADMIN_PASSWORD
        ):
            session["admin"] = True
            return redirect(url_for("admin.admin_dashboard"))
        flash("Invalid admin credentials!", "error")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("auth.auth_page"))


# =======================
#  Admin dashboard (welcome / stats)
# =======================
@admin_bp.route("/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    questions = load_questions()
    users = load_users()
    results = load_results()

    total_questions = len(questions)
    total_students = len(users)
    total_exams = sum(len(data.get("history", [])) for data in results.values())
    total_ai_questions = sum(1 for q in questions if q.get("source", "").upper() == "AI")

    return render_template(
        "admin_dashboard.html",
        total_questions=total_questions,
        total_students=total_students,
        total_exams=total_exams,
        total_ai_questions=total_ai_questions,
    )


@admin_bp.route("/user_history/<string:username>")
def admin_user_history(username):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))
    results = load_results()
    users = load_users()

    history = results.get(username, {}).get("history")
    display_name = username
    if not history:
        for uid, udata in users.items():
            if not isinstance(udata, dict):
                continue
            if uid == username or str(udata.get("id")) == username or str(udata.get("username")).lower() == username.lower() or str(udata.get("email")).lower() == username.lower():
                display_name = udata.get("name") or udata.get("username") or username
                history = (results.get(uid, {}).get("history") or
                           results.get(str(udata.get("id")), {}).get("history") or
                           results.get(udata.get("username"), {}).get("history") or
                           results.get(udata.get("email"), {}).get("history"))
                if history:
                    break

    if not history:
        flash("No history found for this user!", "error")
        return redirect(url_for("admin.students_page"))
    return render_template(
        "admin_dashboard.html",
        page="user_history",
        username=display_name,
        history=history,
    )


# =======================
#  Students section (All Students / Leaderboard / Exam History)
# =======================
@admin_bp.route("/students")
def students_page():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    users = load_users()
    results = load_results()

    students = []
    programs_set = set()
    admission_years_set = set()
    academic_years_set = set()

    for ukey, info in users.items():
        if not isinstance(info, dict):
            continue
        # Exclude admin accounts
        uname = str(info.get("username") or ukey)
        if ukey.lower() in ("admin", "adminc") or uname.lower() in ("admin", "adminc") or info.get("is_admin") or info.get("user_type") == "ADMIN":
            continue

        user_id = str(info.get("id") or ukey)
        display_name = str(info.get("name") or info.get("username") or ukey)
        user_email = str(info.get("email") or "")
        summary = _student_summary(user_id, results)
        if summary.get("attempts") == 0:
            summary = _student_summary(display_name, results)
            if summary.get("attempts") == 0 and ukey != user_id:
                summary = _student_summary(ukey, results)

        user_type = info.get("user_type") or ("UNIVERSITY" if (info.get("student_code") or info.get("program_code")) else "EXTERNAL")
        sc = str(info.get("student_code") or "").strip()
        p_code = str(info.get("program_code") or "").strip()
        p_name = str(info.get("program_name") or (get_program_name(p_code) if p_code else "-")).strip()
        dept_name = str(info.get("department_name") or "-").strip()
        roll_num = str(info.get("roll_number") or "-").strip()
        adm_yr = str(info.get("admission_year") or "").strip()
        acad_yr = str(info.get("academic_year") or "-").strip()
        if not acad_yr or acad_yr == "None":
            acad_yr = "-"

        if p_name and p_name != "-":
            programs_set.add(p_name)
        if adm_yr and adm_yr != "-":
            admission_years_set.add(adm_yr)
        if acad_yr and acad_yr != "-":
            academic_years_set.add(acad_yr)

        students.append({
            "user_id": user_id,
            "key": ukey,
            "username": display_name,
            "name": display_name,
            "email": user_email,
            "user_type": user_type,
            "student_code": sc or "-",
            "program_code": p_code or "-",
            "program_name": p_name,
            "department_name": dept_name,
            "roll_number": roll_num,
            "admission_year": adm_yr or "-",
            "academic_year": acad_yr,
            **summary,
        })

    from utils import get_available_programs, get_academic_years

    valid_years = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "6th Year", "7th Year"]
    sorted_acad_years = sorted(
        [y for y in academic_years_set if y and y != "-"],
        key=lambda y: valid_years.index(y) if y in valid_years else 99
    )

    return render_template(
        "admin_dashboard.html",
        page="students",
        students=students,
        available_programs=get_available_programs(),
        available_academic_years=get_academic_years(),
        filter_programs=sorted(list(programs_set)),
        filter_admission_years=sorted(list(admission_years_set), reverse=True),
        filter_academic_years=sorted_acad_years
    )


@admin_bp.route("/add_student", methods=["POST"])
def add_student():
    """Admin endpoint to create an official University Student with program mapping."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from utils import (
        is_valid_username, parse_student_code, is_student_code_taken, is_email_taken,
        load_users, save_users, get_program_name, get_program_by_code, calculate_academic_year
    )
    import uuid
    from werkzeug.security import generate_password_hash

    name = (request.form.get("name") or request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    if not name:
        flash("Student Name is required!", "error")
        return redirect(url_for("admin.students_page"))

    if not is_valid_username(name):
        flash("Student Name must be at least 2 characters long!", "error")
        return redirect(url_for("admin.students_page"))

    if not email:
        flash("Student Email is required!", "error")
        return redirect(url_for("admin.students_page"))

    if is_email_taken(email):
        flash("Email already exists. Please use a different email.", "error")
        return redirect(url_for("admin.students_page"))

    if not password:
        flash("Student Password is required!", "error")
        return redirect(url_for("admin.students_page"))

    if " " in password:
        flash("Password cannot contain spaces!", "error")
        return redirect(url_for("admin.students_page"))

    # Program selection & automatic Student Code generation
    program_code = (request.form.get("program_code") or request.form.get("program") or "").strip().upper()
    dept_name = (request.form.get("department_name") or "").strip()
    adm_yr_raw = (request.form.get("admission_year") or "2024").strip()
    academic_year = (request.form.get("academic_year") or "").strip()
    roll_raw = (request.form.get("roll_number") or "").strip()
    direct_student_code = (request.form.get("student_code") or "").strip().upper()

    if not dept_name:
        flash("Department Name is required.", "error")
        return redirect(url_for("admin.students_page"))

    if not academic_year:
        flash("Academic Year is required.", "error")
        return redirect(url_for("admin.students_page"))

    valid_academic_years = {"1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "6th Year", "7th Year"}
    if academic_year not in valid_academic_years:
        flash("Academic Year is required.", "error")
        return redirect(url_for("admin.students_page"))

    if program_code:
        # Program mapping flow: Code comes automatically from Admin's program data
        program_name = get_program_name(program_code)
        try:
            admission_year = int(adm_yr_raw)
        except Exception:
            admission_year = 2024
        yy = str(admission_year)[-2:]

        if not roll_raw:
            flash("Roll Number is required!", "error")
            return redirect(url_for("admin.students_page"))
        roll_number = roll_raw.zfill(3) if roll_raw.isdigit() else roll_raw.upper()
        student_code = f"BWU/{program_code}/{yy}/{roll_number}"
        university_code = "BWU"
    elif direct_student_code:
        # Fallback for direct student_code submission (backward compatibility)
        parsed = parse_student_code(direct_student_code)
        if not parsed:
            flash("Invalid Student Code format! Please use format UNIVERSITY/PROGRAM/YY/ROLL, e.g. BWU/AIR/24/029.", "error")
            return redirect(url_for("admin.students_page"))
        student_code = parsed["student_code"]
        university_code = parsed["university_code"]
        program_code = parsed["program_code"]
        program_name = parsed["program_name"]
        admission_year = parsed["admission_year"]
        if not academic_year:
            academic_year = parsed.get("academic_year", "")
        roll_number = parsed["roll_number"]
    else:
        flash("Please select a Program from the dropdown!", "error")
        return redirect(url_for("admin.students_page"))

    if is_student_code_taken(student_code):
        flash("Student Code already exists.", "error")
        return redirect(url_for("admin.students_page"))

    users = load_users()
    internal_id = f"user_{uuid.uuid4().hex[:10]}"

    pw_hash = generate_password_hash(password)
    users[internal_id] = {
        "id": internal_id,
        "name": name,
        "username": name,  # Represents the student's name, NOT UNIQUE
        "email": email,
        "pw_hash": pw_hash,
        "password": pw_hash,
        "user_type": "UNIVERSITY",
        "student_code": student_code,
        "university_code": university_code,
        "program_code": program_code,
        "program_name": program_name,
        "department_name": dept_name,
        "admission_year": admission_year,
        "academic_year": academic_year,
        "roll_number": roll_number
    }
    save_users(users)

    flash(f"University Student '{name}' ({student_code}) added successfully!", "success")
    return redirect(url_for("admin.students_page"))


@admin_bp.route("/edit_student", methods=["POST"])
def edit_student():
    """Admin endpoint to edit a University Student's details and automatically regenerate Student Code."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from utils import (
        is_valid_username, is_student_code_taken,
        load_users, save_users, get_program_name, calculate_academic_year
    )
    from werkzeug.security import generate_password_hash

    user_id = (request.form.get("user_id") or "").strip()
    name = (request.form.get("name") or request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    program_code = (request.form.get("program_code") or "").strip().upper()
    dept_name = (request.form.get("department_name") or "").strip()
    adm_yr_raw = (request.form.get("admission_year") or "").strip()
    academic_year = (request.form.get("academic_year") or "").strip()
    roll_raw = (request.form.get("roll_number") or "").strip()
    new_password = (request.form.get("new_password") or "").strip()

    if not user_id:
        flash("Student ID is missing!", "error")
        return redirect(url_for("admin.students_page"))

    users = load_users()
    target_key = None
    user_record = None
    for k, v in users.items():
        if isinstance(v, dict) and (str(v.get("id")) == user_id or k == user_id):
            target_key = k
            user_record = v
            break

    if not user_record:
        flash("Student account not found!", "error")
        return redirect(url_for("admin.students_page"))

    if not name or not is_valid_username(name):
        flash("Student Name must be at least 2 characters long!", "error")
        return redirect(url_for("admin.students_page"))

    if not email:
        flash("Student Email is required!", "error")
        return redirect(url_for("admin.students_page"))

    if not dept_name:
        flash("Department Name is required.", "error")
        return redirect(url_for("admin.students_page"))

    if not academic_year:
        flash("Academic Year is required.", "error")
        return redirect(url_for("admin.students_page"))

    valid_academic_years = {"1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "6th Year", "7th Year"}
    if academic_year not in valid_academic_years:
        flash("Academic Year is required.", "error")
        return redirect(url_for("admin.students_page"))

    # Check email duplicate across other accounts
    old_email = str(user_record.get("email") or "").strip().lower()
    if email != old_email:
        for k, v in users.items():
            if k != target_key and isinstance(v, dict) and str(v.get("email") or "").strip().lower() == email:
                flash("Email already exists. Please use a different email.", "error")
                return redirect(url_for("admin.students_page"))

    if not program_code:
        program_code = str(user_record.get("program_code") or "AIR").strip().upper()

    try:
        admission_year = int(adm_yr_raw) if adm_yr_raw else int(user_record.get("admission_year") or 2024)
    except Exception:
        admission_year = 2024

    if not roll_raw:
        roll_raw = str(user_record.get("roll_number") or "001").strip()
    roll_clean = roll_raw.zfill(3) if roll_raw.isdigit() else roll_raw.upper()

    program_name = get_program_name(program_code)
    yy = str(admission_year)[-2:]
    new_student_code = f"BWU/{program_code}/{yy}/{roll_clean}"

    old_student_code = str(user_record.get("student_code") or "").strip().upper()
    if new_student_code != old_student_code:
        for k, v in users.items():
            if k != target_key and isinstance(v, dict) and str(v.get("student_code") or "").strip().upper() == new_student_code:
                flash("Student Code already exists.", "error")
                return redirect(url_for("admin.students_page"))

    user_record["name"] = name
    user_record["username"] = name
    user_record["email"] = email
    user_record["program_code"] = program_code
    user_record["program_name"] = program_name
    user_record["department_name"] = dept_name
    user_record["admission_year"] = admission_year
    user_record["academic_year"] = academic_year
    user_record["roll_number"] = roll_clean
    user_record["student_code"] = new_student_code

    if new_password:
        if " " in new_password:
            flash("Password cannot contain spaces!", "error")
            return redirect(url_for("admin.students_page"))
        pw_h = generate_password_hash(new_password)
        user_record["pw_hash"] = pw_h
        user_record["password"] = pw_h

    save_users(users)
    flash(f"University Student '{name}' ({new_student_code}) updated successfully!", "success")
    return redirect(url_for("admin.students_page"))


# ==============================================================
# ADMIN PROGRAM MANAGEMENT ROUTES
# ==============================================================

@admin_bp.route("/programs")
def programs_page():
    """Admin endpoint to view and manage academic programs."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from utils import load_programs, count_students_in_program
    raw_programs = load_programs()
    programs_with_counts = []
    for p in raw_programs:
        c = str(p.get("code") or "").strip().upper()
        n = str(p.get("name") or "").strip()
        s_count = count_students_in_program(c)
        programs_with_counts.append({
            "name": n,
            "code": c,
            "student_count": s_count
        })

    programs_with_counts.sort(key=lambda x: x["name"])

    return render_template(
        "admin_dashboard.html",
        page="programs",
        programs=programs_with_counts
    )


@admin_bp.route("/add_program", methods=["POST"])
def add_program():
    """Admin endpoint to create a new Academic Program with unique Program Code."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from utils import load_programs, save_programs

    name = (request.form.get("name") or request.form.get("program_name") or "").strip()
    code = (request.form.get("code") or request.form.get("program_code") or "").strip().upper()

    if not name:
        flash("Program Name is required.", "error")
        return redirect(url_for("admin.programs_page"))

    if not code:
        flash("Program Code is required.", "error")
        return redirect(url_for("admin.programs_page"))

    programs = load_programs()

    # Requirement 7: Program Code must be unique
    for p in programs:
        if str(p.get("code") or "").strip().upper() == code:
            flash("Program Code already exists.", "error")
            return redirect(url_for("admin.programs_page"))

    # Requirement 8: Program Name safe check
    for p in programs:
        if str(p.get("name") or "").strip().lower() == name.lower():
            flash("Program Name already exists.", "error")
            return redirect(url_for("admin.programs_page"))

    programs.append({"name": name, "code": code})
    save_programs(programs)
    flash(f"Program '{name}' ({code}) added successfully.", "success")
    return redirect(url_for("admin.programs_page"))


@admin_bp.route("/edit_program", methods=["POST"])
def edit_program():
    """Admin endpoint to edit a Program Name or Program Code with student protection."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from utils import load_programs, save_programs, load_users, save_users, count_students_in_program

    old_code = (request.form.get("old_code") or "").strip().upper()
    new_name = (request.form.get("name") or "").strip()
    new_code = (request.form.get("code") or "").strip().upper()
    confirm_update_students = request.form.get("confirm_update_students") == "yes"

    if not old_code:
        flash("Original program code is missing.", "error")
        return redirect(url_for("admin.programs_page"))

    if not new_name:
        flash("Program Name is required.", "error")
        return redirect(url_for("admin.programs_page"))

    if not new_code:
        flash("Program Code is required.", "error")
        return redirect(url_for("admin.programs_page"))

    programs = load_programs()
    prog_idx = -1
    for i, p in enumerate(programs):
        if str(p.get("code") or "").strip().upper() == old_code:
            prog_idx = i
            break

    if prog_idx == -1:
        flash(f"Program with code '{old_code}' not found.", "error")
        return redirect(url_for("admin.programs_page"))

    # Check duplicate code if changed
    if new_code != old_code:
        for i, p in enumerate(programs):
            if i != prog_idx and str(p.get("code") or "").strip().upper() == new_code:
                flash("Program Code already exists.", "error")
                return redirect(url_for("admin.programs_page"))

    # Check duplicate name if changed
    for i, p in enumerate(programs):
        if i != prog_idx and str(p.get("name") or "").strip().lower() == new_name.lower():
            flash("Program Name already exists.", "error")
            return redirect(url_for("admin.programs_page"))

    # Requirement 12: Protect existing student records
    student_count = count_students_in_program(old_code)
    if new_code != old_code and student_count > 0:
        if not confirm_update_students:
            flash(
                f"Warning: {student_count} student(s) currently use '{old_code}'. "
                "Changing this code will modify their Student Codes and academic records. "
                "Please check the confirmation box to proceed with the controlled update.",
                "warning"
            )
            return redirect(url_for("admin.programs_page"))

        # Controlled update for students
        users = load_users()
        for u, rec in users.items():
            if isinstance(rec, dict) and rec.get("user_type") == "UNIVERSITY" and str(rec.get("program_code") or "").strip().upper() == old_code:
                rec["program_code"] = new_code
                rec["program_name"] = new_name
                adm_yr = str(rec.get("admission_year") or "24")[-2:]
                roll = str(rec.get("roll_number") or "001")
                univ = str(rec.get("university_code") or "BWU")
                rec["student_code"] = f"{univ}/{new_code}/{adm_yr}/{roll}"
        save_users(users)

    programs[prog_idx] = {"name": new_name, "code": new_code}
    save_programs(programs)

    if new_code != old_code and student_count > 0:
        flash(f"Program updated to '{new_name}' ({new_code}) and {student_count} student record(s) updated.", "success")
    else:
        flash(f"Program '{new_name}' ({new_code}) updated successfully.", "success")

    return redirect(url_for("admin.programs_page"))


@admin_bp.route("/delete_program/<string:code>", methods=["POST", "GET"])
def delete_program(code):
    """Admin endpoint to safely delete an Academic Program if no students are assigned."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from utils import load_programs, save_programs, count_students_in_program

    c = (code or "").strip().upper()
    programs = load_programs()
    prog_to_delete = None
    for p in programs:
        if str(p.get("code") or "").strip().upper() == c:
            prog_to_delete = p
            break

    if not prog_to_delete:
        flash(f"Program with code '{c}' not found.", "error")
        return redirect(url_for("admin.programs_page"))

    # Requirement 13: "If a Program is currently assigned to students: Do NOT blindly delete it. Show: 'This program is currently assigned to students and cannot be deleted.'"
    students_count = count_students_in_program(c)
    if students_count > 0:
        flash("This program is currently assigned to students and cannot be deleted.", "error")
        return redirect(url_for("admin.programs_page"))

    programs = [p for p in programs if str(p.get("code") or "").strip().upper() != c]
    save_programs(programs)
    flash(f"Program '{prog_to_delete.get('name')}' ({c}) deleted successfully.", "success")
    return redirect(url_for("admin.programs_page"))


@admin_bp.route("/reset_student_password", methods=["POST"])
def reset_student_password():
    """Admin endpoint to safely set or reset a student password."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from werkzeug.security import generate_password_hash
    identifier = (request.form.get("username") or request.form.get("user_id") or "").strip()
    new_password = (request.form.get("new_password") or "").strip()

    if not identifier:
        flash("Student identifier is required!", "error")
        return redirect(url_for("admin.students_page"))

    if not new_password:
        flash("New password cannot be empty!", "error")
        return redirect(url_for("admin.students_page"))

    if " " in new_password:
        flash("Password cannot contain spaces!", "error")
        return redirect(url_for("admin.students_page"))

    users = load_users()
    target_key = None
    if identifier in users:
        target_key = identifier
    else:
        for k, v in users.items():
            if isinstance(v, dict):
                if v.get("id") == identifier or (v.get("email") and v.get("email").lower() == identifier.lower()) or v.get("student_code") == identifier or v.get("username") == identifier:
                    target_key = k
                    break

    if not target_key:
        flash("Student not found!", "error")
        return redirect(url_for("admin.students_page"))

    users[target_key]["pw_hash"] = generate_password_hash(new_password)
    save_users(users)
    disp_name = users[target_key].get("name") or users[target_key].get("username") or identifier
    flash(f"Password for student '{disp_name}' updated successfully!", "success")
    return redirect(url_for("admin.students_page"))


@admin_bp.route("/delete_student/<string:username>", methods=["POST", "GET"])
def delete_student(username):
    """Admin endpoint to delete a student account."""
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    users = load_users()
    deleted = False
    deleted_name = username

    if username in users:
        deleted_name = users[username].get("name") or users[username].get("username") or username
        del users[username]
        deleted = True
    else:
        target_key = None
        for k, v in users.items():
            if isinstance(v, dict):
                if v.get("id") == username or (v.get("email") and v.get("email").lower() == username.lower()) or v.get("student_code") == username or v.get("username") == username:
                    target_key = k
                    deleted_name = v.get("name") or v.get("username") or username
                    break
        if target_key:
            del users[target_key]
            deleted = True

    if deleted:
        save_users(users)
        flash(f"Student '{deleted_name}' deleted successfully!", "success")
    else:
        flash("Student not found!", "error")
    return redirect(url_for("admin.students_page"))


@admin_bp.route("/leaderboard")
def leaderboard():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    results = load_results()
    return render_template(
        "admin_dashboard.html",
        page="leaderboard",
        leaderboard=_leaderboard_rows(results),
    )


@admin_bp.route("/exam-history")
def exam_history():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    results = load_results()
    return render_template(
        "admin_dashboard.html",
        page="exam_history",
        history_rows=_flatten_history(results),
    )


# Backward-compatible alias in case anything still links to the old /admin/users URL
@admin_bp.route("/users")
def users():
    return redirect(url_for("admin.students_page"))


# =======================
#  Add / delete questions
# =======================
@admin_bp.route("/add_question", methods=["POST"])
def add_question():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    import uuid

    # 1. Required Course/Subject classification fields
    course_code = (request.form.get("course_code") or "").strip().upper()
    course_name = (request.form.get("course_name") or "").strip()
    subject = (request.form.get("subject") or "").strip()

    # 2. Program, Admission Year & Academic Year classification
    program_code = (request.form.get("program_code") or "ALL").strip().upper()
    if not program_code:
        program_code = "ALL"
    program_name = "All Programs" if program_code == "ALL" else get_program_name(program_code)

    raw_admission_year = (request.form.get("admission_year") or "ALL").strip()
    if raw_admission_year.upper() in ("ALL", ""):
        admission_year = "ALL"
    else:
        try:
            admission_year = int(raw_admission_year)
        except (ValueError, TypeError):
            admission_year = raw_admission_year

    academic_year = (request.form.get("academic_year") or "ALL").strip()
    if not academic_year:
        academic_year = "ALL"

    # 3. Optional classification fields
    unit = (request.form.get("unit") or "").strip()
    topic = (request.form.get("topic") or "").strip()

    # 4. Question type & level
    qtype = (request.form.get("type") or "MCQ").upper()
    level = (request.form.get("level") or "Easy").strip()
    qtext = (request.form.get("question") or "").strip()

    # Validations matching exact user specifications:
    if not course_code:
        flash("Please enter Course Code.", "error")
        return redirect(url_for("admin.add_question_page"))

    if not course_name:
        flash("Please enter Course Name.", "error")
        return redirect(url_for("admin.add_question_page"))

    if not subject:
        flash("Please select/enter Subject.", "error")
        return redirect(url_for("admin.add_question_page"))

    if not qtext:
        flash("Please enter question.", "error")
        return redirect(url_for("admin.add_question_page"))

    qid = f"Q-{course_code}-{uuid.uuid4().hex[:6].upper()}"
    questions = load_questions()

    # DESCRIPTIVE
    if qtype == "DESCRIPTIVE":
        ak = (request.form.get("answer_key") or "").strip()
        if not ak:
            flash("Please enter model answer / answer key keywords.", "error")
            return redirect(url_for("admin.add_question_page"))

        if not ak.lower().startswith("keywords:"):
            ak = "keywords: " + ak

        try:
            max_marks = int(request.form.get("max_marks", 5))
        except Exception:
            max_marks = 5

        new_q = {
            "id": qid,
            "course_code": course_code,
            "course_name": course_name,
            "subject": subject,
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
            "unit": unit,
            "topic": topic,
            "type": "DESCRIPTIVE",
            "level": level,
            "question": qtext,
            "q": qtext,
            "answer_key": ak,
            "max_marks": max_marks,
            "source": "MANUAL",
        }

    # MCQ
    else:
        o1 = (request.form.get("opt1") or "").strip()
        o2 = (request.form.get("opt2") or "").strip()
        o3 = (request.form.get("opt3") or "").strip()
        o4 = (request.form.get("opt4") or "").strip()
        correct = (request.form.get("correct") or "").strip()

        if not all([o1, o2, o3, o4, correct]):
            flash("Fill all MCQ options and correct answer!", "error")
            return redirect(url_for("admin.add_question_page"))

        opts = [o1, o2, o3, o4]
        new_q = {
            "id": qid,
            "course_code": course_code,
            "course_name": course_name,
            "subject": subject,
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
            "unit": unit,
            "topic": topic,
            "type": "MCQ",
            "level": level,
            "question": qtext,
            "q": qtext,
            "options": opts,
            "a": opts,
            "correct": correct,
            "source": "MANUAL",
        }

    questions.append(new_q)
    save_json("questions.json", questions)
    flash("Question added successfully!", "success")
    return redirect(url_for("admin.add_question_page"))


@admin_bp.route("/delete_question/<int:index>")
def delete_question(index):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    questions = load_questions()
    if 0 <= index < len(questions):
        questions.pop(index)
        save_json("questions.json", questions)
        flash("Question deleted!", "success")
    else:
        flash("Invalid question index!", "error")

    return redirect(url_for("admin.all_questions"))


@admin_bp.route("/edit_question/<int:index>", methods=["POST"])
def edit_question(index):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    questions = load_questions()

    if 0 <= index < len(questions):
        questions[index]["level"] = request.form.get("level")

        if questions[index].get("type") == "DESCRIPTIVE":
            try:
                questions[index]["max_marks"] = int(request.form.get("max_marks", 5))
            except Exception:
                questions[index]["max_marks"] = 5

        save_json("questions.json", questions)
        flash("Updated!", "success")

    return redirect(url_for("admin.all_questions"))


@admin_bp.route("/delete_selected", methods=["POST"])
def delete_selected():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    selected = request.form.getlist("selected")

    if not selected:
        flash("No questions selected!", "error")
        return redirect(url_for("admin.all_questions"))

    questions = load_questions()
    selected = sorted([int(i) for i in selected], reverse=True)

    for index in selected:
        if 0 <= index < len(questions):
            questions.pop(index)

    save_json("questions.json", questions)
    flash(f"{len(selected)} question(s) deleted successfully!", "success")
    return redirect(url_for("admin.all_questions"))


# =======================
#  Admin Pages
# =======================
@admin_bp.route("/all-questions")
def all_questions():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    questions = load_questions()
    unique_data = get_unique_courses_and_subjects()

    return render_template(
        "admin_dashboard.html",
        page="all_questions",
        questions=questions,
        filter_courses=unique_data["courses"],
        filter_course_names=unique_data.get("course_names", []),
        filter_subjects=unique_data["subjects"],
        filter_programs=get_available_programs(),
        filter_admission_years=get_available_admission_years(),
        filter_academic_years=get_academic_years(),
        filter_units=unique_data.get("units", []),
        filter_topics=unique_data.get("topics", [])
    )


@admin_bp.route("/add-question")
def add_question_page():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    unique_data = get_unique_courses_and_subjects()

    return render_template(
        "admin_dashboard.html",
        page="add_question",
        existing_courses=unique_data["courses"],
        existing_course_names=unique_data.get("course_names", []),
        existing_subjects=unique_data["subjects"],
        available_programs=get_available_programs(),
        available_admission_years=get_available_admission_years(),
        available_academic_years=get_academic_years()
    )


# =======================
#  Generate questions page
# =======================
@admin_bp.route("/generate_questions")
@admin_bp.route("/generate-questions")
def generate_questions_page():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))
    unique_data = get_unique_courses_and_subjects()
    preview_questions = session.pop("ai_preview_questions", None)
    return render_template(
        "admin_dashboard.html",
        page="generate_questions",
        existing_courses=unique_data.get("courses", []),
        existing_course_names=unique_data.get("course_names", []),
        existing_subjects=unique_data.get("subjects", []),
        available_programs=get_available_programs(),
        available_admission_years=get_available_admission_years(),
        available_academic_years=get_academic_years(),
        preview_questions=preview_questions
    )


# =======================
#  AI JSON Parser & Cleaner
# =======================
def _clean_and_parse_ai_json(raw_text: str):
    """
    Safely cleans markdown code fences and extracts a JSON array or list of objects from raw AI output.
    Returns (parsed_list, error_message).
    """
    if not raw_text or not str(raw_text).strip():
        return None, "Empty response received from AI model."

    cleaned = str(raw_text).strip()
    # Strip markdown code fences (e.g. ```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # 1. Direct JSON parse
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed, None
        elif isinstance(parsed, dict):
            for k in ["questions", "items", "data", "results", "generated_questions"]:
                if k in parsed and isinstance(parsed[k], list):
                    return parsed[k], None
            return [parsed], None
    except Exception:
        pass

    # 2. Extract outer JSON array [ ... ]
    m_arr = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned)
    if m_arr:
        try:
            parsed = json.loads(m_arr.group(0))
            if isinstance(parsed, list):
                return parsed, None
            elif isinstance(parsed, dict):
                return [parsed], None
        except Exception:
            pass

    # 3. Extract single outer JSON object { ... }
    m_obj = re.search(r"\{[\s\S]*\}", cleaned)
    if m_obj:
        try:
            parsed = json.loads(m_obj.group(0))
            if isinstance(parsed, dict):
                for k in ["questions", "items", "data", "results", "generated_questions"]:
                    if k in parsed and isinstance(parsed[k], list):
                        return parsed[k], None
                return [parsed], None
        except Exception:
            pass

    return None, "Unable to parse valid JSON from AI output."


# =======================
#  AI Question Generation (Preview Stage)
# =======================
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def _call_gemini_http(prompt: str, api_key: str, model: str = DEFAULT_GEMINI_MODEL, timeout: float = 60.0):
    """
    Production-safe HTTP REST call to Google Gemini generateContent endpoint.
    Uses standard library urllib.request to eliminate gRPC fork issues, heavy native C-extensions,
    and excessive memory consumption on Render's 512MB RAM environment.
    Enforces a strict timeout (default 60s) so Gunicorn workers are never aborted by SIGKILL.
    Includes rate-limit (429) and temporary provider error (500/502/503/504) retry handling with exponential backoff:
      - 503 / UNAVAILABLE: 4 retries (~5s, ~10s, ~20s, ~40s + jitter)
    Provides safe detailed diagnostic logging without exposing API keys.
    Returns (raw_text, error_message). Exactly one is non-None.
    """
    if not api_key or not str(api_key).strip():
        return None, "AI service is not configured correctly."

    clean_key = str(api_key).strip().strip('"').strip("'")
    current_model = str(model).strip() or DEFAULT_GEMINI_MODEL

    max_retries = 4
    retry_count = 0
    base_delays = [5.0, 10.0, 20.0, 40.0]

    while True:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={clean_key}"

        # Build generationConfig for Gemini 3.5 Flash-Lite
        # Supports responseMimeType="application/json" and thinkingConfig with thinkingLevel: "low"
        generation_config = {
            "responseMimeType": "application/json",
            "thinkingConfig": {
                "thinkingLevel": "low"
            }
        }

        payload_bytes = json.dumps({
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": generation_config
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )

        call_t0 = time.time()
        print(f"[api_generate] Gemini HTTP request started (model={current_model})")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                call_elapsed = time.time() - call_t0
                data = json.loads(resp.read().decode("utf-8"))
                print(f"[api_generate] Gemini HTTP request completed (status={resp.status}, elapsed={call_elapsed:.2f}s)")
                candidates = data.get("candidates") or []
                if not candidates:
                    feedback = data.get("promptFeedback") or {}
                    block_reason = feedback.get("blockReason")
                    if block_reason:
                        return None, f"AI generation blocked by safety policy ({block_reason})."
                    return None, "AI provider returned an empty response."

                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []
                if not parts:
                    return None, "AI provider returned no text parts in response."

                raw_text = parts[0].get("text") or ""
                return raw_text, None

        except urllib.error.HTTPError as e:
            call_elapsed = time.time() - call_t0
            body = ""
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass

            err_status = ""
            err_msg = ""
            err_reason = ""
            retry_delay_from_body = None

            try:
                if body:
                    err_json = json.loads(body)
                    err_obj = err_json.get("error") or {}
                    err_status = str(err_obj.get("status") or "")
                    err_msg = str(err_obj.get("message") or "")
                    details = err_obj.get("details") or []
                    for d in details:
                        if isinstance(d, dict):
                            if "reason" in d and not err_reason:
                                err_reason = str(d["reason"])
                            if "@type" in d and "RetryInfo" in d["@type"] and "retryDelay" in d:
                                delay_str = str(d["retryDelay"]).rstrip("s")
                                try:
                                    retry_delay_from_body = float(delay_str)
                                except (ValueError, TypeError):
                                    pass
            except Exception:
                pass

            # Safe diagnostic logging: NEVER print API key or Authorization headers
            print(
                f"[api_generate] Gemini HTTP error: status={e.code}, "
                f"error_status='{err_status}', message='{err_msg}', "
                f"model='{current_model}', elapsed={call_elapsed:.2f}s"
            )

            # --- Classification 1: 401 / 403 or 400 with API key invalid (Authentication / Project configuration) ---
            # DO NOT retry! Clearly report configuration error.
            is_auth_error = (
                e.code in (401, 403)
                or (e.code == 400 and ("API_KEY" in err_reason or "api key" in err_msg.lower() or "key" in err_msg.lower()))
            )
            if is_auth_error:
                return None, "AI service is not configured correctly or API key is invalid."

            # --- Classification 2: 404 Model or endpoint problem ---
            # DO NOT retry! Clearly report configuration/model error.
            if e.code == 404:
                return None, f"Configured AI model '{current_model}' was not found or is unsupported."

            # --- Classification 3: 429 Quota / Rate limit problem ---
            # Free tier quota reached: do not spin-retry long-reset errors (> 15s)
            if e.code == 429 or "RESOURCE_EXHAUSTED" in err_reason or "RESOURCE_EXHAUSTED" in err_status:
                retry_after_hdr = e.headers.get("Retry-After") if (hasattr(e, "headers") and e.headers) else None
                sleep_time = None
                if retry_after_hdr:
                    try:
                        sleep_time = float(retry_after_hdr)
                    except (ValueError, TypeError):
                        sleep_time = None
                if sleep_time is None and retry_delay_from_body is not None:
                    sleep_time = retry_delay_from_body

                if sleep_time is not None and sleep_time > 15.0:
                    print(f"[api_generate] Quota exhausted with long reset window ({sleep_time:.0f}s). Aborting retries.")
                    return None, "AI service free-tier request quota has been reached. Please try again later."

                if sleep_time is not None and retry_count < max_retries:
                    retry_count += 1
                    sleep_time_actual = max(sleep_time, 1.0)
                    print(f"[api_generate] Rate limit (HTTP 429/RESOURCE_EXHAUSTED) encountered. Backing off for {sleep_time_actual:.2f}s (retry {retry_count}/{max_retries})...")
                    time.sleep(sleep_time_actual)
                    continue

                return None, "AI service free-tier request quota has been reached. Please try again later."

            # --- Classification 4: 500 / 502 / 503 / 504 Temporary Gemini provider / server problem ---
            # Retry with exponential backoff: 1st ~5s, 2nd ~10s, 3rd ~20s, 4th ~40s (max 4 retries)
            if e.code in (500, 502, 503, 504):
                if retry_count < max_retries:
                    retry_count += 1
                    sleep_base = base_delays[retry_count - 1]
                    jitter = round(random.uniform(0.1, 0.9), 2)
                    sleep_time = sleep_base + jitter

                    if e.code == 503 or "UNAVAILABLE" in err_status.upper() or "UNAVAILABLE" in err_reason.upper():
                        print("[api_generate] Gemini 503/UNAVAILABLE")
                        print(f"[api_generate] Retry {retry_count}/{max_retries} in {int(round(sleep_time))} seconds")
                    else:
                        print(f"[api_generate] Gemini {e.code}/{err_status or 'SERVER_ERROR'}")
                        print(f"[api_generate] Retry {retry_count}/{max_retries} in {int(round(sleep_time))} seconds")

                    time.sleep(sleep_time)
                    continue
                else:
                    return None, "AI provider service is temporarily unavailable. Please try again later."

            # Other 400 Bad Request - DO NOT retry
            if e.code == 400:
                err_detail = err_msg if err_msg else "Please check input parameters."
                return None, f"AI request was rejected by provider (HTTP 400). {err_detail}"

            # Other 4xx errors - DO NOT retry
            if 400 <= e.code < 500:
                return None, f"AI request was rejected by provider (HTTP {e.code}). Please check input parameters."

            # Any other unclassified status
            return None, f"AI generation failed (HTTP {e.code}). Please try again."

        except (socket.timeout, TimeoutError):
            call_elapsed = time.time() - call_t0
            print(f"[api_generate] Gemini HTTP request timed out after {call_elapsed:.2f}s (model='{current_model}')")
            return None, "AI generation timed out. Please try again."

        except urllib.error.URLError as e:
            call_elapsed = time.time() - call_t0
            reason_str = str(getattr(e, "reason", "")).lower()
            if isinstance(getattr(e, "reason", None), socket.timeout) or "timed out" in reason_str:
                print(f"[api_generate] Gemini HTTP connection timed out after {call_elapsed:.2f}s (model='{current_model}')")
                return None, "AI generation timed out. Please try again."
            print(f"[api_generate] Gemini HTTP network error: {e.reason} (elapsed: {call_elapsed:.2f}s)")
            return None, "Network connection to AI service failed. Please check internet connection."

        except Exception as ex:
            call_elapsed = time.time() - call_t0
            print(f"[api_generate] Unexpected error calling Gemini: {type(ex).__name__} (elapsed: {call_elapsed:.2f}s)")
            return None, "An unexpected error occurred during AI generation."


def _normalize_question_text_for_dedup(text: str) -> str:
    """Normalizes question text for robust deduplication comparison."""
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


def _build_batch_prompt(course_code, course_name, subject, program_name, program_code,
                        admission_year, academic_year, unit, topic, difficulty,
                        batch_mcq_count, batch_desc_count, sample_existing_questions=None):
    """
    Builds an academically grounded prompt tailored specifically for a single batch.
    Includes anti-duplication hints if previous questions have already been generated in earlier batches.
    """
    batch_count = batch_mcq_count + batch_desc_count

    if batch_mcq_count > 0 and batch_desc_count > 0:
        type_instructions = f"""
Generate a MIXED set containing exactly {batch_mcq_count} Multiple Choice Questions (MCQ) and {batch_desc_count} Descriptive Questions (Total: {batch_count} questions).
For MCQ questions:
- "type": "MCQ"
- "question": "Clear and rigorous question statement"
- "options": ["Option A text", "Option B text", "Option C text", "Option D text"] (exactly 4 distinct options)
- "correct": "The exact verbatim text of the correct option from options list"
- "level": "{difficulty}"

For Descriptive questions:
- "type": "DESCRIPTIVE"
- "question": "Analytical, theoretical, or problem-solving question"
- "answer_key": "Thorough model answer, essential concepts, and grading criteria"
- "max_marks": 5
- "level": "{difficulty}"
"""
    elif batch_mcq_count > 0:
        type_instructions = f"""
Generate exactly {batch_mcq_count} Multiple Choice Questions (MCQ).
Every question object MUST contain:
- "type": "MCQ"
- "question": "Clear and rigorous question statement"
- "options": ["Option A text", "Option B text", "Option C text", "Option D text"] (exactly 4 distinct options)
- "correct": "The exact verbatim text of the correct option from options list"
- "level": "{difficulty}"
"""
    else:
        type_instructions = f"""
Generate exactly {batch_desc_count} Descriptive examination questions.
Every question object MUST contain:
- "type": "DESCRIPTIVE"
- "question": "Analytical, theoretical, or problem-solving question"
- "answer_key": "Thorough model answer, essential concepts, and grading criteria"
- "max_marks": 5
- "level": "{difficulty}"
"""

    existing_note = ""
    if sample_existing_questions:
        cleaned_samples = [q[:70] for q in sample_existing_questions[-8:] if q]
        if cleaned_samples:
            existing_note = "\nDO NOT duplicate or repeat the following questions already generated in previous batches:\n- " + "\n- ".join(cleaned_samples) + "\n"

    prompt = f"""You are a university examination professor and curriculum assessment specialist.
Generate high-quality academic questions strictly aligned with this curriculum syllabus:
- Course Code: {course_code}
- Course Name: {course_name}
- Subject: {subject}
- Program / Degree: {program_name} ({program_code})
- Target Batch / Admission Year: {admission_year}
- Target Academic Year: {academic_year}
- Unit / Module: {unit}
- Topic: {topic}
- Target Difficulty: {difficulty}
{existing_note}
{type_instructions}

CRITICAL RULES:
1. Return ONLY a valid JSON array of objects: [ ... ]
2. Do NOT wrap in markdown code blocks or backticks (no ```json or ```).
3. Do NOT include introductory greetings, notes, comments, or summaries.
4. Ensure every question is academically accurate, distinct, and tests concepts specific to {topic} under {unit} tailored for {academic_year} university students in {program_name}.
"""
    return prompt


def _normalize_ai_question_item(item, course_code, course_name, subject, program_code,
                                program_name, admission_year, academic_year, unit, topic, difficulty):
    """
    Validates and normalizes an individual raw AI question dictionary into the standard schema.
    """
    if not isinstance(item, dict):
        return None

    q_text = str(item.get("question") or item.get("q") or "").strip()
    if not q_text:
        return None

    raw_t = str(item.get("type") or "").strip().upper()
    if "MCQ" in raw_t or "OBJECTIVE" in raw_t or "CHOICE" in raw_t or "options" in item:
        item_type = "MCQ"
    else:
        item_type = "DESCRIPTIVE"

    item_level = str(item.get("level") or difficulty).strip().capitalize()
    if item_level not in ("Easy", "Medium", "Hard"):
        item_level = difficulty

    qid = f"Q-{course_code}-{uuid.uuid4().hex[:6].upper()}"

    q_obj = {
        "id": qid,
        "course_code": course_code,
        "course_name": course_name,
        "subject": subject,
        "program_code": program_code,
        "program_name": program_name,
        "admission_year": admission_year,
        "academic_year": academic_year,
        "unit": unit,
        "topic": topic,
        "type": item_type,
        "level": item_level,
        "question": q_text,
        "q": q_text,
        "source": "AI",
    }

    if item_type == "MCQ":
        opts_raw = item.get("options") or item.get("a") or []
        if isinstance(opts_raw, list):
            opts = [str(x).strip() for x in opts_raw if str(x).strip()]
        else:
            opts = []

        if len(opts) < 2:
            return None

        correct = str(item.get("correct") or "").strip()
        if correct not in opts:
            matched = False
            for idx, prefix in enumerate(["A", "B", "C", "D"]):
                if correct.upper() == prefix or correct.upper().startswith(f"OPTION {prefix}"):
                    if idx < len(opts):
                        correct = opts[idx]
                        matched = True
                        break
            if not matched:
                correct = opts[0]

        q_obj["options"] = opts
        q_obj["a"] = opts
        q_obj["correct"] = correct

    else:  # DESCRIPTIVE
        ak = str(item.get("answer_key") or item.get("model_answer") or "").strip()
        if not ak:
            ak = "Comprehensive model answer criteria with core concepts and key terminology."
        try:
            mm = int(item.get("max_marks", 5))
        except Exception:
            mm = 5

        q_obj["answer_key"] = ak
        q_obj["model_answer"] = ak
        q_obj["max_marks"] = mm

    return q_obj


@admin_bp.route("/api_generate", methods=["POST"])
def api_generate():
    """
    Generates questions using Gemini based on strict academic classification.
    Processes large requests in safe batches (max 10 questions per batch) sequentially
    to stay well within the 22.0s per-request timeout while producing up to 50 questions reliably.
    Returns generated questions in a structured format for PREVIEW before saving.
    Always returns JSON responses to prevent unexpected HTML parsing errors.
    """
    if not session.get("admin"):
        return jsonify({"success": False, "error": "Unauthorized. Please log in as admin."}), 401

    # Support JSON payload or Form data
    data = request.get_json(silent=True) if request.is_json else request.form
    if not data:
        data = {}

    course_code = (data.get("course_code") or "").strip().upper()
    course_name = (data.get("course_name") or "").strip()
    subject = (data.get("subject") or "").strip()
    unit = (data.get("unit") or "").strip()
    topic = (data.get("topic") or "").strip()

    # Program, Admission Year & Academic Year classification
    program_code = (data.get("program_code") or "ALL").strip().upper()
    if not program_code:
        program_code = "ALL"
    program_name = "All Programs" if program_code == "ALL" else get_program_name(program_code)

    raw_admission_year = (data.get("admission_year") or "ALL").strip()
    if raw_admission_year.upper() in ("ALL", ""):
        admission_year = "ALL"
    else:
        try:
            admission_year = int(raw_admission_year)
        except (ValueError, TypeError):
            admission_year = raw_admission_year

    academic_year = (data.get("academic_year") or "ALL").strip()
    if not academic_year:
        academic_year = "ALL"

    qtype_raw = (data.get("qtype") or "MCQ").strip().upper()
    if qtype_raw in ("MCQ", "DESCRIPTIVE", "MIXED"):
        qtype = qtype_raw
    else:
        qtype = "MCQ"

    difficulty = (data.get("difficulty") or data.get("level") or "Medium").strip().capitalize()
    if difficulty not in ("Easy", "Medium", "Hard"):
        difficulty = "Medium"

    try:
        count = int(data.get("count") or 5)
    except Exception:
        count = 5

    def error_response(msg, status_code=400):
        return jsonify({"success": False, "error": msg}), status_code

    # Required field validations
    if not course_code:
        return error_response("Please enter Course Code.")
    if not course_name:
        return error_response("Please enter Course Name.")
    if not subject:
        return error_response("Please enter Subject.")
    if not unit:
        return error_response("Please enter Unit / Module.")
    if not topic:
        return error_response("Please enter Topic.")
    if count < 1 or count > 50:
        return error_response("Number of questions must be between 1 and 50.")

    # Validate API key configuration safely
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        print("[api_generate] Missing GEMINI_API_KEY in environment.")
        return error_response("AI service is not configured correctly.", 400)

    # Concurrency control: prevent multiple simultaneous AI calls from creating memory/process pressure on Render
    acquired = _AI_GENERATION_LOCK.acquire(blocking=True, timeout=2.0)
    if not acquired:
        print("[api_generate] Rejected concurrent request - lock busy.")
        return error_response("Another AI generation request is currently processing. Please wait a few seconds and try again.", 429)

    try:
        # Determine batch partition (safe batches of at most 5 questions each)
        BATCH_SIZE = 5
        batches = []
        rem = count
        while rem > 0:
            b_size = min(BATCH_SIZE, rem)
            batches.append(b_size)
            rem -= b_size

        total_batches = len(batches)

        # Calculate overall target counts
        if qtype == "MIXED":
            total_mcq_target = count // 2
            total_desc_target = count - total_mcq_target
        elif qtype == "MCQ":
            total_mcq_target = count
            total_desc_target = 0
        else:
            total_mcq_target = 0
            total_desc_target = count

        # Determine per-batch MCQ and Descriptive allocations
        batch_plans = []
        rem_mcq = total_mcq_target
        rem_desc = total_desc_target
        for b_size in batches:
            if qtype == "MIXED":
                b_mcq = min(rem_mcq, (b_size + 1) // 2)
                if b_size - b_mcq > rem_desc:
                    b_mcq = b_size - rem_desc
                b_desc = b_size - b_mcq
            elif qtype == "MCQ":
                b_mcq = b_size
                b_desc = 0
            else:
                b_mcq = 0
                b_desc = b_size
            rem_mcq -= b_mcq
            rem_desc -= b_desc
            batch_plans.append((b_mcq, b_desc))

        print(f"[api_generate] Request started: count={count}")
        print(f"[api_generate] Internal generation: {total_batches} batches of {BATCH_SIZE}")

        final_questions = []
        seen_keys = set()

        # Pre-populate seen_keys with existing questions for this course to prevent duplicates
        try:
            existing_qb = load_questions()
            for eq in existing_qb:
                if isinstance(eq, dict):
                    eq_course = str(eq.get("course_code") or "").strip().upper()
                    if eq_course == course_code.upper():
                        q_text = eq.get("question") or eq.get("q")
                        if q_text:
                            seen_keys.add(_normalize_question_text_for_dedup(q_text))
        except Exception as e:
            print(f"[api_generate] Note: could not load existing questions for dedup: {e}")

        timeout_seconds = float(os.getenv("GEMINI_TIMEOUT", "60.0"))
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL

        # Execute batches sequentially to avoid memory spikes and API rate-limit issues
        for batch_idx, (b_mcq, b_desc) in enumerate(batch_plans, start=1):
            b_size = b_mcq + b_desc
            print(f"[api_generate] Batch {batch_idx}/{total_batches} started")
            t0 = time.time()

            sample_titles = [q["question"] for q in final_questions[-8:]]
            prompt = _build_batch_prompt(
                course_code=course_code,
                course_name=course_name,
                subject=subject,
                program_name=program_name,
                program_code=program_code,
                admission_year=admission_year,
                academic_year=academic_year,
                unit=unit,
                topic=topic,
                difficulty=difficulty,
                batch_mcq_count=b_mcq,
                batch_desc_count=b_desc,
                sample_existing_questions=sample_titles
            )

            raw_text, ai_error = _call_gemini_http(prompt, api_key, model=model_name, timeout=timeout_seconds)
            elapsed = time.time() - t0

            if ai_error:
                if "timed out" in ai_error.lower():
                    print(f"[api_generate] Batch {batch_idx}/{total_batches} timed out")
                    err_msg = "AI generation timed out. Please try again." if total_batches == 1 else f"AI generation timed out while creating the complete question set (Batch {batch_idx} of {total_batches}). Please try again."
                    return error_response(err_msg, 400)
                else:
                    print(f"[api_generate] AI error in Batch {batch_idx}/{total_batches}: {ai_error} (elapsed: {elapsed:.2f}s)")
                    err_msg = ai_error
                    return error_response(err_msg, 400)

            # Validate JSON immediately after each batch
            parsed_list, parse_err = _clean_and_parse_ai_json(raw_text)
            if not parsed_list:
                print(f"[api_generate] JSON parse error in Batch {batch_idx}/{total_batches}: {parse_err}. Raw text preview: {(raw_text or '')[:200]}")
                err_msg = "AI generation returned invalid format. Please try again." if total_batches == 1 else f"AI generation produced invalid JSON in Batch {batch_idx} of {total_batches}. Please try again."
                return error_response(err_msg, 400)

            batch_added = 0
            for item in parsed_list:
                q_obj = _normalize_ai_question_item(
                    item, course_code, course_name, subject, program_code, program_name,
                    admission_year, academic_year, unit, topic, difficulty
                )
                if not q_obj:
                    continue

                k = _normalize_question_text_for_dedup(q_obj["question"])
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                final_questions.append(q_obj)
                batch_added += 1

            print(f"[api_generate] Batch {batch_idx}/{total_batches} completed")

        # Top-up batches if deduplication or validation resulted in fewer questions than requested
        topup_attempts = 0
        max_topup_attempts = 10
        while len(final_questions) < count and topup_attempts < max_topup_attempts:
            topup_attempts += 1
            missing_count = count - len(final_questions)
            topup_batch_size = min(BATCH_SIZE, missing_count)

            curr_mcq = sum(1 for q in final_questions if q["type"] == "MCQ")
            curr_desc = sum(1 for q in final_questions if q["type"] == "DESCRIPTIVE")

            if qtype == "MIXED":
                topup_mcq = min(topup_batch_size, max(0, total_mcq_target - curr_mcq))
                topup_desc = topup_batch_size - topup_mcq
            elif qtype == "MCQ":
                topup_mcq = topup_batch_size
                topup_desc = 0
            else:
                topup_mcq = 0
                topup_desc = topup_batch_size

            sample_titles = [q["question"] for q in final_questions[-8:]]
            topup_prompt = _build_batch_prompt(
                course_code=course_code,
                course_name=course_name,
                subject=subject,
                program_name=program_name,
                program_code=program_code,
                admission_year=admission_year,
                academic_year=academic_year,
                unit=unit,
                topic=topic,
                difficulty=difficulty,
                batch_mcq_count=topup_mcq,
                batch_desc_count=topup_desc,
                sample_existing_questions=sample_titles
            )

            raw_text, ai_error = _call_gemini_http(topup_prompt, api_key, model=model_name, timeout=timeout_seconds)
            if ai_error or not raw_text:
                print(f"[api_generate] Top-up batch failed: {ai_error}")
                break

            parsed_list, _ = _clean_and_parse_ai_json(raw_text)
            if not parsed_list:
                break

            added_in_topup = 0
            for item in parsed_list:
                if len(final_questions) >= count:
                    break
                q_obj = _normalize_ai_question_item(
                    item, course_code, course_name, subject, program_code, program_name,
                    admission_year, academic_year, unit, topic, difficulty
                )
                if not q_obj:
                    continue
                k = _normalize_question_text_for_dedup(q_obj["question"])
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                final_questions.append(q_obj)
                added_in_topup += 1

            if added_in_topup == 0:
                break

        # Trim to exact requested count if any excess items were returned
        if len(final_questions) > count:
            final_questions = final_questions[:count]

        if not final_questions:
            return error_response("AI generated output contained no usable question items.", 400)

        # Logging: Combined and response generated
        print(f"[api_generate] Combined result: {len(final_questions)} questions")
        print(f"[api_generate] Response generated: {len(final_questions)} unique questions returned successfully")

        return jsonify({
            "success": True,
            "questions": final_questions,
            "count": len(final_questions),
            "course_code": course_code,
            "course_name": course_name,
            "subject": subject,
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
            "unit": unit,
            "topic": topic,
        })

    except Exception as e:
        print(f"[api_generate] Unhandled exception: {type(e).__name__} - {str(e)[:100]}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred during AI generation. Please try again."
        }), 500

    finally:
        _AI_GENERATION_LOCK.release()


# =======================
#  Save Generated Questions to Question Bank
# =======================
@admin_bp.route("/api_save_generated", methods=["POST"])
def api_save_generated():
    """
    Saves the previewed & approved AI-generated questions into questions.json.
    - Validates course_code and subject on every question.
    - Sets source = 'AI'.
    - Appends to existing questions without overwriting.
    """
    if not session.get("admin"):
        return jsonify({"success": False, "error": "Unauthorized. Please log in as admin."}), 401

    payload = request.get_json(silent=True) or {}
    questions_to_save = payload.get("questions")

    if not questions_to_save or not isinstance(questions_to_save, list):
        return jsonify({"success": False, "error": "No questions provided to save."}), 400

    # Strict Validation: Do NOT save if course_code or subject is missing.
    validated_questions = []
    for idx, q in enumerate(questions_to_save):
        if not isinstance(q, dict):
            continue

        course_code = (q.get("course_code") or "").strip().upper()
        course_name = (q.get("course_name") or "").strip()
        subject = (q.get("subject") or "").strip()
        unit = (q.get("unit") or "").strip()
        topic = (q.get("topic") or "").strip()
        q_text = (q.get("question") or q.get("q") or "").strip()

        # Program, Admission Year & Academic Year classification
        program_code = (q.get("program_code") or "ALL").strip().upper()
        if not program_code:
            program_code = "ALL"
        program_name = "All Programs" if program_code == "ALL" else get_program_name(program_code)

        raw_admission_year = q.get("admission_year")
        if raw_admission_year in (None, "") or str(raw_admission_year).strip().upper() in ("ALL", "ALL BATCHES"):
            admission_year = "ALL"
        else:
            try:
                admission_year = int(raw_admission_year)
            except (ValueError, TypeError):
                admission_year = str(raw_admission_year).strip()

        academic_year = str(q.get("academic_year") or "ALL").strip()
        if not academic_year:
            academic_year = "ALL"

        if not course_code or not subject:
            return jsonify({
                "success": False,
                "error": f"Question #{idx+1} is missing required Course Code or Subject. Save aborted."
            }), 400

        if not q_text:
            return jsonify({
                "success": False,
                "error": f"Question #{idx+1} is missing question statement. Save aborted."
            }), 400

        qtype = _fix_type_to_capital(q.get("type"))
        level = (q.get("level") or "Medium").strip().capitalize()
        if level not in ("Easy", "Medium", "Hard"):
            level = "Medium"

        clean_item = {
            "id": q.get("id") or f"Q-{course_code}-{idx+1}",
            "course_code": course_code,
            "course_name": course_name or course_code,
            "subject": subject,
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
            "unit": unit,
            "topic": topic,
            "type": qtype,
            "level": level,
            "question": q_text,
            "q": q_text,
            "source": "AI",
        }

        if qtype == "MCQ":
            opts = q.get("options") or q.get("a") or []
            if isinstance(opts, list):
                clean_opts = [str(x).strip() for x in opts if str(x).strip()]
            else:
                clean_opts = []

            if len(clean_opts) < 2:
                return jsonify({
                    "success": False,
                    "error": f"MCQ Question #{idx+1} must contain at least 2 options."
                }), 400

            correct = str(q.get("correct") or "").strip()
            if not correct or correct not in clean_opts:
                correct = clean_opts[0]

            clean_item["options"] = clean_opts
            clean_item["a"] = clean_opts
            clean_item["correct"] = correct

        else:  # DESCRIPTIVE
            ak = str(q.get("answer_key") or q.get("model_answer") or "").strip()
            try:
                mm = int(q.get("max_marks", 5))
            except Exception:
                mm = 5

            clean_item["answer_key"] = ak
            clean_item["model_answer"] = ak
            clean_item["max_marks"] = mm

        validated_questions.append(clean_item)

    if not validated_questions:
        return jsonify({"success": False, "error": "No valid questions were processed."}), 400

    print(f"[api_save_generated] Saving {len(validated_questions)} questions")
    # Append to existing questions
    existing_questions = load_questions()
    existing_questions.extend(validated_questions)
    save_json("questions.json", existing_questions)
    print(f"[api_save_generated] {len(validated_questions)} questions saved successfully")

    return jsonify({
        "success": True,
        "saved_count": len(validated_questions),
        "message": f"{len(validated_questions)} questions saved successfully."
    })


# =========================================================
#  COURSE EXAM MANAGEMENT ROUTES
# =========================================================

@admin_bp.route("/course-exams")
def course_exams_manage():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    exams = load_course_exams()
    decorated_exams = []
    for e in exams:
        live_info = get_exam_live_status(e)
        decorated_exams.append({**e, "live": live_info})

    # Sort: active first, then upcoming, draft, completed, closed
    priority_order = {"live": 0, "upcoming": 1, "draft": 2, "completed": 3, "closed": 4}
    decorated_exams.sort(key=lambda x: priority_order.get(x["live"]["time_state"], 99))

    stats = get_course_exam_stats()
    unique_data = get_unique_courses_and_subjects()

    auto_open_exam = session.pop("auto_open_exam", None)
    draft_exam = session.get("draft_course_exam")

    available_programs = get_available_programs()
    available_admission_years = get_available_admission_years()
    available_academic_years = get_academic_years()
    all_students = get_all_students_for_eligibility()

    return render_template(
        "admin_dashboard.html",
        page="course_exams",
        exams=decorated_exams,
        stats=stats,
        existing_courses=unique_data["courses"],
        existing_subjects=unique_data["subjects"],
        auto_open_exam=auto_open_exam,
        draft_exam=draft_exam,
        available_programs=available_programs,
        available_admission_years=available_admission_years,
        available_academic_years=available_academic_years,
        all_students=all_students,
    )


@admin_bp.route("/api/course-exams/eligibility", methods=["GET", "POST"])
def api_course_exam_eligibility():
    """
    Live API endpoint to compute eligible student count and student list
    given program_code, admission_year, and academic_year.
    """
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
    else:
        data = request.args

    p_code = (data.get("program_code") or "").strip().upper()
    adm_year = (data.get("admission_year") or "").strip()
    acad_year = (data.get("academic_year") or "").strip()

    students = get_all_students_for_eligibility()
    matching = []
    for s in students:
        s_p = str(s.get("program_code") or "").strip().upper()
        s_adm = str(s.get("admission_year") or "").strip()
        s_acad = str(s.get("academic_year") or "").strip().lower()

        p_match = not p_code or s_p == p_code
        adm_match = not adm_year or s_adm == adm_year
        acad_match = not acad_year or s_acad == acad_year.lower()

        if p_match and adm_match and acad_match:
            matching.append(s)

    return jsonify({
        "success": True,
        "program_code": p_code,
        "program_name": get_program_name(p_code),
        "admission_year": adm_year,
        "academic_year": acad_year,
        "eligible_count": len(matching),
        "students": matching
    })


@admin_bp.route("/course-exams/create", methods=["POST"])
def create_course_exam():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    import uuid
    from datetime import datetime

    title = (request.form.get("title") or "").strip()
    course_code = (request.form.get("course_code") or "").strip().upper()
    course_name = (request.form.get("course_name") or "").strip()
    subject = (request.form.get("subject") or "").strip()
    description = (request.form.get("description") or "").strip()
    exam_type = (request.form.get("exam_type") or "MCQ").strip()
    exam_date = (request.form.get("exam_date") or "").strip()
    start_time = (request.form.get("start_time") or "").strip()
    end_time = (request.form.get("end_time") or "").strip()

    try:
        duration = max(1, int(request.form.get("duration") or 60))
    except Exception:
        duration = 60

    try:
        num_questions = max(1, int(request.form.get("num_questions") or 10))
    except Exception:
        num_questions = 10

    difficulty = (request.form.get("difficulty") or "All").strip()
    status = (request.form.get("status") or "Draft").strip()

    raw_qids = request.form.get("question_ids") or "[]"
    try:
        qids = json.loads(raw_qids) if isinstance(raw_qids, str) else []
    except Exception:
        qids = []

    # Target / Student Eligibility configuration
    target_mode = (request.form.get("target_mode") or "PROGRAM_BATCH_YEAR").strip().upper()
    program_code = (request.form.get("program_code") or "").strip().upper()
    admission_year = (request.form.get("admission_year") or "").strip()
    academic_year = (request.form.get("academic_year") or "").strip()
    all_in_batch = (request.form.get("all_in_batch") == "on" or request.form.get("all_in_batch") == "1")

    raw_scodes = request.form.get("student_codes") or "[]"
    try:
        student_codes = json.loads(raw_scodes) if isinstance(raw_scodes, str) else []
    except Exception:
        student_codes = []
    if not student_codes:
        student_codes = request.form.getlist("specific_students")

    # Validations
    if not title:
        flash("Exam Title is required!", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not course_code:
        flash("Course Code is required!", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not subject:
        flash("Subject is required!", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not exam_date or not start_time or not end_time:
        flash("Exam Date, Start Time, and End Time are required!", "error")
        return redirect(url_for("admin.course_exams_manage"))

    # Eligibility Validations
    if not program_code:
        flash("Please select a target program.", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not admission_year:
        flash("Please select an admission year.", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not academic_year:
        flash("Please select an academic year.", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if target_mode == "SPECIFIC_STUDENTS" and not student_codes:
        flash("Please select at least one student for Specific Students mode.", "error")
        return redirect(url_for("admin.course_exams_manage"))

    # Validate date/time format
    try:
        st_dt = datetime.strptime(f"{exam_date} {start_time}", "%Y-%m-%d %H:%M")
        et_dt = datetime.strptime(f"{exam_date} {end_time}", "%Y-%m-%d %H:%M")
        if et_dt <= st_dt:
            flash("End Time must be after Start Time!", "error")
            return redirect(url_for("admin.course_exams_manage"))
    except Exception:
        flash("Invalid Date or Time format! (Expected Date: YYYY-MM-DD, Time: HH:MM)", "error")
        return redirect(url_for("admin.course_exams_manage"))

    exam_id = f"EXAM-{course_code}-{uuid.uuid4().hex[:6].upper()}"

    new_exam = {
        "id": exam_id,
        "title": title,
        "course_code": course_code,
        "course_name": course_name or course_code,
        "subject": subject,
        "description": description,
        "exam_type": exam_type,
        "exam_date": exam_date,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "num_questions": num_questions,
        "difficulty": difficulty,
        "status": status,
        "question_ids": qids,
        "target_mode": target_mode,
        "program_code": program_code,
        "program_name": get_program_name(program_code),
        "admission_year": int(admission_year) if admission_year.isdigit() else admission_year,
        "academic_year": academic_year,
        "all_in_batch": all_in_batch,
        "student_codes": student_codes if target_mode == "SPECIFIC_STUDENTS" else [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    exams = load_course_exams()
    exams.append(new_exam)
    save_course_exams(exams)
    session.pop("draft_course_exam", None)

    matching_qs = get_matching_questions(
        course_code=course_code,
        subject=subject,
        qtype=exam_type,
        difficulty=difficulty
    )
    if len(matching_qs) < num_questions:
        flash(f"Exam '{title}' created! Warning: Only {len(matching_qs)} matching questions are available for this exam (required: {num_questions}).", "warning")
    else:
        flash(f"Course Examination '{title}' created successfully! ({len(matching_qs)} matching questions ready)", "success")
    return redirect(url_for("admin.course_exams_manage"))


@admin_bp.route("/course-exams/edit/<string:exam_id>", methods=["POST"])
def edit_course_exam(exam_id):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    from datetime import datetime

    exams = load_course_exams()
    exam = None
    for e in exams:
        if str(e.get("id")) == str(exam_id):
            exam = e
            break

    if not exam:
        flash("Examination not found!", "error")
        return redirect(url_for("admin.course_exams_manage"))

    title = (request.form.get("title") or "").strip()
    course_code = (request.form.get("course_code") or "").strip().upper()
    course_name = (request.form.get("course_name") or "").strip()
    subject = (request.form.get("subject") or "").strip()
    description = (request.form.get("description") or "").strip()
    exam_type = (request.form.get("exam_type") or "MCQ").strip()
    exam_date = (request.form.get("exam_date") or "").strip()
    start_time = (request.form.get("start_time") or "").strip()
    end_time = (request.form.get("end_time") or "").strip()

    try:
        duration = max(1, int(request.form.get("duration") or 60))
    except Exception:
        duration = 60

    try:
        num_questions = max(1, int(request.form.get("num_questions") or 10))
    except Exception:
        num_questions = 10

    difficulty = (request.form.get("difficulty") or "All").strip()
    status = (request.form.get("status") or "Draft").strip()

    # Target / Student Eligibility configuration
    target_mode = (request.form.get("target_mode") or "PROGRAM_BATCH_YEAR").strip().upper()
    program_code = (request.form.get("program_code") or "").strip().upper()
    admission_year = (request.form.get("admission_year") or "").strip()
    academic_year = (request.form.get("academic_year") or "").strip()
    all_in_batch = (request.form.get("all_in_batch") == "on" or request.form.get("all_in_batch") == "1")

    raw_scodes = request.form.get("student_codes") or "[]"
    try:
        student_codes = json.loads(raw_scodes) if isinstance(raw_scodes, str) else []
    except Exception:
        student_codes = []
    if not student_codes:
        student_codes = request.form.getlist("specific_students")

    if not title or not course_code or not subject or not exam_date or not start_time or not end_time:
        flash("Please fill all required examination fields!", "error")
        return redirect(url_for("admin.course_exams_manage"))

    # Eligibility Validations
    if not program_code:
        flash("Please select a target program.", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not admission_year:
        flash("Please select an admission year.", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if not academic_year:
        flash("Please select an academic year.", "error")
        return redirect(url_for("admin.course_exams_manage"))
    if target_mode == "SPECIFIC_STUDENTS" and not student_codes:
        flash("Please select at least one student for Specific Students mode.", "error")
        return redirect(url_for("admin.course_exams_manage"))

    try:
        st_dt = datetime.strptime(f"{exam_date} {start_time}", "%Y-%m-%d %H:%M")
        et_dt = datetime.strptime(f"{exam_date} {end_time}", "%Y-%m-%d %H:%M")
        if et_dt <= st_dt:
            flash("End Time must be after Start Time!", "error")
            return redirect(url_for("admin.course_exams_manage"))
    except Exception:
        flash("Invalid Date or Time format!", "error")
        return redirect(url_for("admin.course_exams_manage"))

    exam["title"] = title
    exam["course_code"] = course_code
    exam["course_name"] = course_name or course_code
    exam["subject"] = subject
    exam["description"] = description
    exam["exam_type"] = exam_type
    exam["exam_date"] = exam_date
    exam["start_time"] = start_time
    exam["end_time"] = end_time
    exam["duration"] = duration
    exam["num_questions"] = num_questions
    exam["difficulty"] = difficulty
    exam["status"] = status
    exam["target_mode"] = target_mode
    exam["program_code"] = program_code
    exam["program_name"] = get_program_name(program_code)
    exam["admission_year"] = int(admission_year) if admission_year.isdigit() else admission_year
    exam["academic_year"] = academic_year
    exam["all_in_batch"] = all_in_batch
    exam["student_codes"] = student_codes if target_mode == "SPECIFIC_STUDENTS" else []
    exam["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_qids = request.form.get("question_ids")
    if raw_qids:
        try:
            qids = json.loads(raw_qids) if isinstance(raw_qids, str) else []
            exam["question_ids"] = qids
        except Exception:
            pass

    save_course_exams(exams)
    session.pop("draft_course_exam", None)
    flash(f"Course Examination '{title}' updated successfully!", "success")
    return redirect(url_for("admin.course_exams_manage"))


@admin_bp.route("/course-exams/publish/<string:exam_id>", methods=["POST", "GET"])
def publish_course_exam(exam_id):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    exams = load_course_exams()
    for e in exams:
        if str(e.get("id")) == str(exam_id):
            e["status"] = "Published"
            save_course_exams(exams)
            matching_qs = get_matching_questions(
                course_code=e.get("course_code"),
                subject=e.get("subject"),
                qtype=e.get("exam_type", "ALL"),
                difficulty=e.get("difficulty", "ALL"),
                program_code=e.get("program_code"),
                admission_year=e.get("admission_year"),
                academic_year=e.get("academic_year")
            )
            req_q = int(e.get("num_questions") or 10)
            if len(matching_qs) < req_q:
                flash(f"Exam '{e.get('title')}' is now Published! Warning: Only {len(matching_qs)} matching questions are available for this exam (required: {req_q}).", "warning")
            else:
                flash(f"Exam '{e.get('title')}' is now Published! ({len(matching_qs)} matching questions ready)", "success")
            break
    else:
        flash("Examination not found!", "error")

    return redirect(url_for("admin.course_exams_manage"))


@admin_bp.route("/course-exams/unpublish/<string:exam_id>", methods=["POST", "GET"])
def unpublish_course_exam(exam_id):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    exams = load_course_exams()
    for e in exams:
        if str(e.get("id")) == str(exam_id):
            e["status"] = "Draft"
            save_course_exams(exams)
            flash(f"Exam '{e.get('title')}' moved to Draft (Unpublished).", "info")
            break
    else:
        flash("Examination not found!", "error")

    return redirect(url_for("admin.course_exams_manage"))


@admin_bp.route("/course-exams/close/<string:exam_id>", methods=["POST", "GET"])
def close_course_exam(exam_id):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    exams = load_course_exams()
    for e in exams:
        if str(e.get("id")) == str(exam_id):
            e["status"] = "Closed"
            save_course_exams(exams)
            flash(f"Exam '{e.get('title')}' is now Closed.", "info")
            break
    else:
        flash("Examination not found!", "error")

    return redirect(url_for("admin.course_exams_manage"))


@admin_bp.route("/course-exams/delete/<string:exam_id>", methods=["POST", "GET"])
def delete_course_exam(exam_id):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    exams = load_course_exams()
    filtered = [e for e in exams if str(e.get("id")) != str(exam_id)]
    if len(filtered) < len(exams):
        save_course_exams(filtered)
        flash("Examination deleted successfully!", "success")
    else:
        flash("Examination not found!", "error")

    return redirect(url_for("admin.course_exams_manage"))


@admin_bp.route("/course-exams/questions/<string:exam_id>")
def view_exam_questions_api(exam_id):
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    exam = get_course_exam_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Examination not found"}), 404

    course_code = exam.get("course_code")
    subject = exam.get("subject")
    qtype = exam.get("exam_type", "ALL")
    difficulty = exam.get("difficulty", "ALL")
    num_required = int(exam.get("num_questions") or 10)

    matched = get_matching_questions(
        course_code,
        subject,
        qtype,
        difficulty,
        program_code=exam.get("program_code"),
        admission_year=exam.get("admission_year"),
        academic_year=exam.get("academic_year")
    )

    return jsonify({
        "exam_id": exam["id"],
        "title": exam["title"],
        "course_code": course_code,
        "subject": subject,
        "program_code": exam.get("program_code"),
        "admission_year": exam.get("admission_year"),
        "academic_year": exam.get("academic_year"),
        "exam_type": qtype,
        "difficulty": difficulty,
        "required_questions": num_required,
        "total_available": len(matched),
        "is_sufficient": len(matched) >= num_required,
        "questions": matched
    })


# ==============================================================
# COURSE EXAM QUESTION SELECTION & MANUAL QUESTION AUTHORING
# ==============================================================

@admin_bp.route("/course-exams/prepare-selection", methods=["POST"])
def prepare_exam_selection():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    exam_id = str(data.get("exam_id") or "new").strip()
    session["draft_course_exam"] = data

    redirect_url = url_for("admin.select_course_exam_questions", exam_id=exam_id)
    return jsonify({"success": True, "redirect_url": redirect_url})


@admin_bp.route("/course-exams/select-questions/<string:exam_id>", methods=["GET"])
def select_course_exam_questions(exam_id):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    exam = None
    draft = session.get("draft_course_exam")

    if exam_id == "new":
        if not draft:
            flash("Please start by configuring a new Course Exam.", "warning")
            return redirect(url_for("admin.course_exams_manage"))
        exam = dict(draft)
        exam["id"] = "new"
    else:
        existing = get_course_exam_by_id(exam_id)
        if not existing:
            flash("Examination not found!", "error")
            return redirect(url_for("admin.course_exams_manage"))
        exam = dict(existing)
        # Overlay in-progress draft edits if admin edited before clicking select
        if draft and str(draft.get("exam_id")) == str(exam_id):
            for k in ["title", "course_code", "course_name", "subject", "num_questions", "difficulty", "exam_type", "description", "target_mode", "program_code", "admission_year", "academic_year", "all_in_batch", "student_codes"]:
                if draft.get(k) is not None:
                    exam[k] = draft[k]

    try:
        exam["num_questions"] = max(1, int(exam.get("num_questions") or 10))
    except Exception:
        exam["num_questions"] = 10

    selected_ids = exam.get("question_ids")
    if isinstance(selected_ids, str):
        try:
            selected_ids = json.loads(selected_ids)
        except Exception:
            selected_ids = []
    if not isinstance(selected_ids, list):
        selected_ids = []
    exam["question_ids"] = selected_ids

    all_qs = load_questions()
    unique_data = get_unique_courses_and_subjects()

    return render_template(
        "admin_dashboard.html",
        page="select_exam_questions",
        exam=exam,
        questions=all_qs,
        grouped_questions=group_questions_by_course_subject(all_qs),
        selected_ids=selected_ids,
        existing_courses=unique_data["courses"],
        existing_subjects=unique_data["subjects"],
        available_programs=get_available_programs(),
        available_admission_years=get_available_admission_years(),
        available_academic_years=get_academic_years(),
    )


@admin_bp.route("/course-exams/save-selection/<string:exam_id>", methods=["POST"])
def save_course_exam_selection(exam_id):
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    qids = payload.get("question_ids", [])
    if not isinstance(qids, list):
        return jsonify({"error": "Invalid question_ids format"}), 400

    all_qs = load_questions()
    existing_q_ids = {str(q.get("id")) for q in all_qs if q.get("id")}
    valid_qids = [str(qid) for qid in qids if str(qid) in existing_q_ids]
    unique_qids = list(dict.fromkeys(valid_qids))

    if exam_id == "new":
        if "draft_course_exam" in session:
            session["draft_course_exam"]["question_ids"] = unique_qids
        session["auto_open_exam"] = "new"
    else:
        exams = load_course_exams()
        found = False
        for e in exams:
            if str(e.get("id")) == str(exam_id):
                e["question_ids"] = unique_qids
                found = True
                break
        if found:
            save_course_exams(exams)
        if "draft_course_exam" in session and str(session["draft_course_exam"].get("exam_id")) == str(exam_id):
            session["draft_course_exam"]["question_ids"] = unique_qids
        session["auto_open_exam"] = exam_id

    flash(f"{len(unique_qids)} questions selected successfully.", "success")
    return jsonify({
        "success": True,
        "count": len(unique_qids),
        "redirect_url": url_for("admin.course_exams_manage")
    })


@admin_bp.route("/course-exams/add-manual-question", methods=["POST"])
def add_manual_course_exam_question():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    import uuid
    data = request.get_json(silent=True) or request.form

    course_code = (data.get("course_code") or "").strip().upper()
    course_name = (data.get("course_name") or "").strip()
    subject = (data.get("subject") or "").strip()
    unit = (data.get("unit") or "").strip()
    topic = (data.get("topic") or "").strip()
    qtype = (data.get("type") or "MCQ").strip().upper()
    level = (data.get("level") or "Easy").strip()
    qtext = (data.get("question") or "").strip()

    # Program, Admission Year & Academic Year classification
    program_code = (data.get("program_code") or "ALL").strip().upper()
    if not program_code:
        program_code = "ALL"
    program_name = "All Programs" if program_code == "ALL" else get_program_name(program_code)

    raw_admission_year = (data.get("admission_year") or "ALL")
    if str(raw_admission_year).strip().upper() in ("ALL", ""):
        admission_year = "ALL"
    else:
        try:
            admission_year = int(raw_admission_year)
        except (ValueError, TypeError):
            admission_year = str(raw_admission_year).strip()

    academic_year = str(data.get("academic_year") or "ALL").strip()
    if not academic_year:
        academic_year = "ALL"

    if not course_code or not subject:
        return jsonify({"error": "Course Code and Subject are required."}), 400
    if not qtext:
        return jsonify({"error": "Question text is required."}), 400

    qid = f"Q-{course_code}-{uuid.uuid4().hex[:6].upper()}"
    questions = load_questions()

    if qtype == "DESCRIPTIVE":
        ak = (data.get("answer_key") or "").strip()
        try:
            mm = int(data.get("max_marks") or 5)
        except Exception:
            mm = 5
        q_obj = {
            "id": qid,
            "course_code": course_code,
            "course_name": course_name or course_code,
            "subject": subject,
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
            "unit": unit,
            "topic": topic,
            "type": "DESCRIPTIVE",
            "level": level,
            "question": qtext,
            "q": qtext,
            "answer_key": ak,
            "max_marks": mm,
            "source": "MANUAL"
        }
    else:
        # MCQ
        opts = [
            (data.get("option_a") or "").strip(),
            (data.get("option_b") or "").strip(),
            (data.get("option_c") or "").strip(),
            (data.get("option_d") or "").strip()
        ]
        correct = (data.get("correct") or "").strip()
        q_obj = {
            "id": qid,
            "course_code": course_code,
            "course_name": course_name or course_code,
            "subject": subject,
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
            "unit": unit,
            "topic": topic,
            "type": "MCQ",
            "level": level,
            "question": qtext,
            "q": qtext,
            "options": opts,
            "a": opts,
            "correct": correct,
            "source": "MANUAL"
        }

    # Prepend new question and save
    questions.insert(0, q_obj)
    save_json("questions.json", questions)

    return jsonify({
        "success": True,
        "message": "Question added successfully.",
        "question": q_obj
    })