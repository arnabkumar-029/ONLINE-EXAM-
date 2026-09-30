# admin_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from utils import (
    load_questions,
    save_json,
    load_users,
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
)
import re
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv  # 👈 load from .env

# -----------------------
# Load environment vars
# -----------------------
load_dotenv()  # This reads .env file locally

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    # You will see this error if GEMINI_API_KEY is missing
    raise RuntimeError("GEMINI_API_KEY not set in environment!")

# Configure Gemini once (global)
genai.configure(api_key=GEMINI_API_KEY)

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
    for username, udata in results.items():
        for rec in udata.get("history", []) or []:
            rows.append({
                "username": username,
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
    for username, udata in results.items():
        history = udata.get("history", []) or []
        if not history:
            continue
        best = max(history, key=_pct)
        rows.append({
            "username": username,
            "score": best.get("score", 0),
            "total": best.get("total", 0),
            "pct": round(_pct(best), 1),
            "time_taken": best.get("time_taken") or "N/A",
            "attempts": len(history),
        })
    rows.sort(key=lambda r: r["pct"], reverse=True)
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
    history = results.get(username, {}).get("history")
    if not history:
        flash("No history found for this user!", "error")
        return redirect(url_for("admin.students_page"))
    return render_template(
        "admin_dashboard.html",
        page="user_history",
        username=username,
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
    for username, info in users.items():
        summary = _student_summary(username, results)
        students.append({
            "username": username,
            "email": info.get("email", ""),
            **summary,
        })

    return render_template("admin_dashboard.html", page="students", students=students)


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

    # 2. Optional classification fields
    unit = (request.form.get("unit") or "").strip()
    topic = (request.form.get("topic") or "").strip()

    # 3. Question type & level
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
        filter_subjects=unique_data["subjects"]
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
        existing_subjects=unique_data["subjects"]
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
@admin_bp.route("/api_generate", methods=["POST"])
def api_generate():
    """
    Generates questions using Gemini based on strict academic classification.
    Returns generated questions in a structured format for PREVIEW before saving.
    Classification values (course_code, course_name, subject, unit, topic) are strictly
    enforced from the admin form and CANNOT be altered or invented by the AI.
    """
    if not session.get("admin"):
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "Unauthorized. Please log in as admin."}), 401
        return redirect(url_for("admin.admin_login"))

    import uuid

    # Support JSON payload or Form data
    data = request.get_json(silent=True) if request.is_json else request.form

    course_code = (data.get("course_code") or "").strip().upper()
    course_name = (data.get("course_name") or "").strip()
    subject = (data.get("subject") or "").strip()
    unit = (data.get("unit") or "").strip()
    topic = (data.get("topic") or "").strip()

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

    is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")

    def error_response(msg):
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("admin.generate_questions_page"))

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

    # Build prompt instructions based on question type
    if qtype == "MIXED":
        mcq_count = max(1, count // 2)
        desc_count = max(1, count - mcq_count)
        type_instructions = f"""
Generate a MIXED set containing exactly {mcq_count} Multiple Choice Questions (MCQ) and {desc_count} Descriptive Questions (Total: {count} questions).
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
    elif qtype == "MCQ":
        type_instructions = f"""
Generate {count} Multiple Choice Questions (MCQ).
Every question object MUST contain:
- "type": "MCQ"
- "question": "Clear and rigorous question statement"
- "options": ["Option A text", "Option B text", "Option C text", "Option D text"] (exactly 4 distinct options)
- "correct": "The exact verbatim text of the correct option from options list"
- "level": "{difficulty}"
"""
    else:  # DESCRIPTIVE
        type_instructions = f"""
Generate {count} Descriptive examination questions.
Every question object MUST contain:
- "type": "DESCRIPTIVE"
- "question": "Analytical, theoretical, or problem-solving question"
- "answer_key": "Thorough model answer, essential concepts, and grading criteria"
- "max_marks": 5
- "level": "{difficulty}"
"""

    prompt = f"""You are a university examination professor and curriculum assessment specialist.
Generate high-quality academic questions strictly aligned with this curriculum syllabus:
- Course Code: {course_code}
- Course Name: {course_name}
- Subject: {subject}
- Unit / Module: {unit}
- Topic: {topic}
- Target Difficulty: {difficulty}

{type_instructions}

CRITICAL RULES:
1. Return ONLY a valid JSON array of objects: [ ... ]
2. Do NOT wrap in markdown code blocks or backticks (no ```json or ```).
3. Do NOT include introductory greetings, notes, comments, or summaries.
4. Ensure every question is academically accurate and tests concepts specific to {topic} under {unit}.
"""

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)
        raw_text = (getattr(response, "text", "") or "").strip()

        parsed_list, parse_err = _clean_and_parse_ai_json(raw_text)
        if not parsed_list:
            print("[api_generate] JSON parse error:", parse_err, "Raw text:", raw_text[:500])
            return error_response(f"AI generation produced invalid JSON. {parse_err}")

        # Normalize and strictly enforce admin classification fields
        normalized_questions = []
        for item in parsed_list:
            if not isinstance(item, dict):
                continue

            q_text = str(item.get("question") or item.get("q") or "").strip()
            if not q_text:
                continue

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
                    continue

                correct = str(item.get("correct") or "").strip()
                if correct not in opts:
                    # Check letter prefix match like 'A' or 'Option A'
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

            normalized_questions.append(q_obj)

        if not normalized_questions:
            return error_response("AI generated output contained no usable question items.")

        if is_ajax:
            return jsonify({
                "success": True,
                "questions": normalized_questions,
                "count": len(normalized_questions),
                "course_code": course_code,
                "course_name": course_name,
                "subject": subject,
                "unit": unit,
                "topic": topic,
            })

        # Traditional fallback
        session["ai_preview_questions"] = normalized_questions
        return redirect(url_for("admin.generate_questions_page"))

    except Exception as e:
        print("[api_generate] AI Exception:", e)
        return error_response(f"AI generation failed: {str(e)}")


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

    # Append to existing questions
    existing_questions = load_questions()
    existing_questions.extend(validated_questions)
    save_json("questions.json", existing_questions)

    return jsonify({
        "success": True,
        "saved_count": len(validated_questions),
        "message": f"Successfully saved {len(validated_questions)} AI-generated questions to the Question Bank!"
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

    return render_template(
        "admin_dashboard.html",
        page="course_exams",
        exams=decorated_exams,
        stats=stats,
        existing_courses=unique_data["courses"],
        existing_subjects=unique_data["subjects"],
        auto_open_exam=auto_open_exam,
        draft_exam=draft_exam,
    )


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

    if not title or not course_code or not subject or not exam_date or not start_time or not end_time:
        flash("Please fill all required examination fields!", "error")
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
                difficulty=e.get("difficulty", "ALL")
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

    matched = get_matching_questions(course_code, subject, qtype, difficulty)

    return jsonify({
        "exam_id": exam["id"],
        "title": exam["title"],
        "course_code": course_code,
        "subject": subject,
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
            for k in ["title", "course_code", "course_name", "subject", "num_questions", "difficulty", "exam_type", "description"]:
                if draft.get(k):
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
        selected_ids=selected_ids,
        existing_courses=unique_data["courses"],
        existing_subjects=unique_data["subjects"],
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