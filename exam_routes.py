# exam_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils import load_results, save_results, descriptive_similarity, load_questions
import time, sys, pprint

exam_bp = Blueprint("exam", __name__, url_prefix="")

@exam_bp.route("/history")
def history():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))
    username = session["username"]
    results = load_results()
    return render_template("user_history.html", username=username,
                           history=results.get(username, {}).get("history", []))


@exam_bp.route("/exam", methods=["GET", "POST"])
def exam():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))

    questions = session.get("questions", [])
    if not questions:
        flash("No questions available!", "error")
        return redirect(url_for("auth.auth_page"))

    index = int(session.get("index", 0))
    if index < 0 or index >= len(questions):
        index = 0
        session["index"] = 0

    answers = session.get("answers", {}) or {}
    question = questions[index]

    if request.method == "POST":
        action = request.form.get("action")
        raw_ans = request.form.get("answer")

        # Normalize
        ans = "" if raw_ans is None else str(raw_ans).strip()

        # DEBUG LOG
        print("=== DEBUG POST ===", file=sys.stderr)
        print("Index:", index, " Action:", action, file=sys.stderr)
        print("Raw Answer:", repr(raw_ans), file=sys.stderr)
        print("Normalized Answer:", repr(ans), file=sys.stderr)
        print("Answers BEFORE:", answers, file=sys.stderr)

        # Always store answer (even empty)
        answers[str(index)] = ans
        session["answers"] = answers

        print("Answers AFTER:", session["answers"], file=sys.stderr)
        print("==================", file=sys.stderr)

        # PREVIOUS BUTTON
        if action == "prev" and index > 0:
            session["index"] = index - 1

        # SKIP BUTTON
        elif action == "skip":
            # FORCE EMPTY ANSWER (counts as skipped)
            answers[str(index)] = ""
            session["answers"] = answers

            if index < len(questions) - 1:
                session["index"] = index + 1
            else:
                return redirect(url_for("exam.result"))

        # NEXT BUTTON
        elif action == "next":
            stored = answers.get(str(index), "")
            if not stored.strip():
                flash("Please answer first!", "error")
                return redirect(url_for("exam.exam"))

            if index < len(questions) - 1:
                session["index"] = index + 1
            else:
                return redirect(url_for("exam.result"))

        return redirect(url_for("exam.exam"))

    selected = answers.get(str(index), "")
    return render_template("exam.html", question=question,
                           index=index + 1, total=len(questions),
                           selected=selected,
                           difficulty=question.get("level", "N/A"))


@exam_bp.route("/result")
def result():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))

    questions = session.get("questions", [])
    answers = session.get("answers", {}) or {}

    total = 0.0
    score = 0.0
    wrong = 0
    skipped = 0
    descriptive_reports = []

    for i, q in enumerate(questions):
        qtype = q.get("type", "MCQ")
        ans = answers.get(str(i), "") or ""

        # MCQ SCORING
        if qtype == "MCQ":
            total += 1
            if not ans:
                skipped += 1
            elif ans == q.get("correct"):
                score += 1
            else:
                wrong += 1

        # DESCRIPTIVE SCORING
        else:
            max_marks = float(q.get("max_marks", 5))
            total += max_marks

            if not ans.strip():
                skipped += 1
                descriptive_reports.append({
                    "q": q["q"],
                    "similarity": 0,
                    "originality": 100,
                    "grade": "Not Answered",
                    "marks": 0
                })
                continue

            sim = descriptive_similarity(ans, q.get("answer_key", ""))
            s = sim * 100

            if sim >= 0.75:
                marks = max_marks; grade = "Excellent"
            elif sim >= 0.50:
                marks = max_marks * 0.7; grade = "Good"
            elif sim >= 0.30:
                marks = max_marks * 0.4; grade = "Fair"
            else:
                marks = 0; grade = "Weak"

            marks = round(marks, 2)
            score += marks

            descriptive_reports.append({
                "q": q["q"],
                "similarity": round(s, 2),
                "originality": round(100 - s, 2),
                "grade": grade,
                "marks": marks
            })

    # TIME
    t = int(time.time() - session.get("start_time", time.time()))
    time_taken = f"{t//60}m {t%60}s"

    session["score"] = round(score, 2)
    session["wrong"] = wrong
    session["skipped"] = skipped
    session["total_points"] = total
    session["time_taken"] = time_taken
    session["descriptive_reports"] = descriptive_reports

    return render_template("result.html", score=session["score"], wrong=wrong,
                           skipped=skipped, total=total,
                           time_taken=time_taken,
                           descriptive_reports=descriptive_reports)


@exam_bp.route("/save_result")
def save_result():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))

    username = session["username"]
    results = load_results()

    if username not in results:
        results[username] = {"history": []}

    results[username]["history"].append({
        "score": session["score"],
        "total": session["total_points"],
        "time_taken": session["time_taken"],
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "descriptive_reports": session["descriptive_reports"]
    })

    save_results(results)
    return redirect(url_for("exam.leaderboard"))


@exam_bp.route("/leaderboard")
def leaderboard():
    results = load_results()

    def pct(x):
        u = x[1]
        s = float(u.get("score", 0))
        t = float(u.get("total", 1))
        return s / t if t else 0

    sorted_users = sorted(results.items(), key=pct, reverse=True)
    return render_template("leaderboard.html", leaderboard=sorted_users)
