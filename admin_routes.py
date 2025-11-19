# admin_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils import (
    load_questions,
    save_json,
    load_users,
    load_results,
    save_results,
    _migrate_one_question,
    _fix_type_to_capital,
)
import re
import json
import os
import google.generativeai as genai

# Blueprint MUST be defined before any @admin_bp.route()
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Simple hard-coded admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


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
#  Admin dashboard / history
# =======================
@admin_bp.route("/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))
    return render_template(
        "admin_dashboard.html",
        questions=load_questions(),
        users=load_users(),
        results=load_results(),
    )


@admin_bp.route("/user_history/<string:username>")
def admin_user_history(username):
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))
    results = load_results()
    history = results.get(username, {}).get("history")
    if not history:
        flash("No history found for this user!", "error")
        return redirect(url_for("admin.admin_dashboard"))
    return render_template("admin_user_history.html", username=username, history=history)


# =======================
#  Add / delete questions
# =======================
@admin_bp.route("/add_question", methods=["POST"])
def add_question():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    qtype = (request.form.get("type") or "MCQ").upper()
    qtext = (request.form.get("question") or "").strip()
    level = (request.form.get("level") or "Easy").strip()

    if not qtext:
        flash("Enter question!", "error")
        return redirect(url_for("admin.generate_questions_page"))

    questions = load_questions()

    # DESCRIPTIVE
    if qtype == "DESCRIPTIVE":
        ak = (request.form.get("answer_key") or "").strip()
        if ak and not ak.lower().startswith("keywords:"):
            ak = "keywords: " + ak
        try:
            max_marks = int(request.form.get("max_marks", 5))
        except Exception:
            max_marks = 5

        questions.append(
            {
                "q": qtext,
                "type": "DESCRIPTIVE",
                "answer_key": ak,
                "max_marks": max_marks,
                "level": level,
            }
        )

    # MCQ
    else:
        o1 = request.form.get("opt1")
        o2 = request.form.get("opt2")
        o3 = request.form.get("opt3")
        o4 = request.form.get("opt4")
        correct = (request.form.get("correct") or "").strip()

        if not all([o1, o2, o3, o4, correct]):
            flash("Fill all MCQ fields!", "error")
            return redirect(url_for("admin.generate_questions_page"))

        questions.append(
            {
                "q": qtext,
                "type": "MCQ",
                "a": [o1, o2, o3, o4],
                "correct": correct,
                "level": level,
            }
        )

    save_json("questions.json", questions)
    flash("Question added!", "success")
    return redirect(url_for("admin.generate_questions_page"))


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

    return redirect(url_for("admin.admin_dashboard"))


# =======================
#  Generate questions page
# =======================
@admin_bp.route("/generate_questions")
def generate_questions_page():
    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))
    return render_template("generate_questions.html")


# =======================
#  AI Question Generation
# =======================
@admin_bp.route("/api_generate", methods=["POST"])
def api_generate():
    """
    Generate MCQ or DESCRIPTIVE questions with Gemini and store them safely.

    - Accepts AI output as:
      * JSON array: [ {...}, {...} ]
      * Single JSON object: { ... }   (wrapped into list)
    - Cleans markdown fences.
    - Shows "Invalid JSON from AI!" only when parsing genuinely fails.
    """

    if not session.get("admin"):
        return redirect(url_for("admin.admin_login"))

    qtype_req = _fix_type_to_capital(request.form.get("qtype", "MCQ"))
    topic = (request.form.get("topic") or "").strip()
    try:
        count = int(request.form.get("count") or 1)
    except Exception:
        count = 1

    if not topic:
        flash("Enter topic!", "error")
        return redirect(url_for("admin.generate_questions_page"))

    # ----- Prompt construction -----
    extra_note = (
        "Return EXACTLY a JSON array (even if count=1, still return [ { ... } ]).\n"
        "Do NOT include any explanation, headings, or markdown fences."
    )

    if qtype_req == "MCQ":
        prompt = f"""
Generate {count} MCQs about "{topic}".
{extra_note}
Each item in the array must be an object like:
{{
  "q": "Question?",
  "a": ["Option A", "Option B", "Option C", "Option D"],
  "correct": "Option A",
  "type": "MCQ",
  "level": "Easy"
}}
"""
    else:
        prompt = f"""
Generate {count} DESCRIPTIVE questions about "{topic}".
{extra_note}
Each item in the array must be an object like:
{{
  "q": "Explain ...?",
  "answer_key": "keywords: <comma-separated key points only>",
  "max_marks": 5,
  "type": "DESCRIPTIVE",
  "level": "Medium"
}}
"""

    # ----- Configure Gemini -----
    # For simplicity, we use your hard-coded key as requested.
    API_KEY = "AIzaSyCJimhwj57WXZh7IFuru6SCWYPqRU-xqaw"
    genai.configure(api_key=API_KEY)

    model_name = "models/gemini-2.5-flash"

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        raw = (getattr(response, "text", "") or "").strip()

        print("RAW OUTPUT:\n", raw)

        # Remove markdown code fences if present
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        data_list = None

        # 1) Try parse whole cleaned text directly
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                data_list = parsed
                print("[api_generate] Parsed top-level JSON list.")
            elif isinstance(parsed, dict):
                data_list = [parsed]
                print("[api_generate] Parsed top-level JSON object; wrapped into list.")
        except Exception:
            pass

        # 2) Try find an array block [ ... ]
        if data_list is None:
            m_arr = re.search(r"\[[\s\S]*\]", cleaned)
            if m_arr:
                try:
                    parsed = json.loads(m_arr.group(0))
                    if isinstance(parsed, list):
                        data_list = parsed
                        print("[api_generate] Extracted JSON array block.")
                    elif isinstance(parsed, dict):
                        data_list = [parsed]
                        print("[api_generate] Extracted JSON dict from array block; wrapped into list.")
                except Exception as e:
                    print("[api_generate] Failed to parse array block:", e)

        # 3) Try find a single object { ... } and wrap into list
        if data_list is None:
            m_obj = re.search(r"\{[\s\S]*\}", cleaned)
            if m_obj:
                try:
                    obj = json.loads(m_obj.group(0))
                    data_list = [obj]
                    print("[api_generate] Extracted single JSON object and wrapped into list.")
                except Exception as e:
                    print("[api_generate] Failed to parse object block:", e)

        # FINAL CHECK: if still nothing, it's truly invalid
        if not data_list:
            flash("Invalid JSON from AI!", "error")
            print("[api_generate] PARSE FAILED. CLEANED RAW WAS:\n", cleaned[:2000])
            return redirect(url_for("admin.generate_questions_page"))

        # ----- Normalize and save -----
        normalized = []
        for item in data_list:
            fixed = _migrate_one_question(item)
            if fixed:
                fixed["type"] = qtype_req
                normalized.append(fixed)

        if not normalized:
            flash("AI JSON parsed but no valid questions after migration!", "error")
            print("[api_generate] MIGRATION produced 0 items. Parsed data:", data_list)
            return redirect(url_for("admin.generate_questions_page"))

        questions = load_questions()
        questions.extend(normalized)
        save_json("questions.json", questions)

        flash(f"Added {len(normalized)} {qtype_req} question(s)!", "success")
        return redirect(url_for("admin.generate_questions_page"))

    except Exception as e:
        print("AI ERROR:", e)
        flash("AI generation failed!", "error")
        return redirect(url_for("admin.generate_questions_page"))
