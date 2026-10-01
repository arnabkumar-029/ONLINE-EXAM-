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
    user_key = session.get("student_id") or session.get("user_id") or username
    results = load_results()
    history_data = results.get(user_key, {}).get("history") or results.get(username, {}).get("history", [])
    return render_template("user_history.html", username=username,
                           history=history_data)


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
                           difficulty=question.get("level", "N/A"),
                           total_time=session.get("total_time", 600))


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
    user_key = session.get("student_id") or session.get("user_id") or username
    results = load_results()

    # If results has existing history directly under username (for older accounts), keep using it; else use user_key
    target_key = username if (username in results and user_key not in results) else user_key

    if target_key not in results:
        results[target_key] = {"history": []}

    results[target_key]["history"].append({
        "score": session["score"],
        "total": session["total_points"],
        "time_taken": session["time_taken"],
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "descriptive_reports": session["descriptive_reports"],
        "exam_title": session.get("course_exam_title", "Practice Examination"),
        "course_code": session.get("course_code", ""),
        "course_exam_id": session.get("course_exam_id", None)
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

@exam_bp.route("/start_exam", methods=["POST"])
def start_exam():
    if "username" not in session:
        return redirect(url_for("auth.auth_page"))

    from utils import load_questions
    import random, time

    qtype = request.form.get("type") or "MCQ"
    level = request.form.get("level") or request.form.get("difficulty") or "ALL"
    count = int(request.form.get("count") or request.form.get("num_questions") or 5)

    source_mode = (request.form.get("source_mode") or "all").strip().lower()
    selected_course = (request.form.get("course_code") or "").strip().upper()
    selected_subject = (request.form.get("subject") or "").strip()
    selected_subjects = request.form.getlist("subjects")
    if not selected_subjects and request.form.get("subjects"):
        selected_subjects = [s.strip() for s in request.form.get("subjects").split(",") if s.strip()]

    all_qs = load_questions()

    # ✅ 1. FILTER QUESTION SOURCE
    if source_mode == "course" and selected_course:
        source_filtered = [
            q for q in all_qs
            if (q.get("course_code") or "").strip().upper() == selected_course
        ]
    elif source_mode == "subject" and selected_course and selected_subject:
        source_filtered = [
            q for q in all_qs
            if (q.get("course_code") or "").strip().upper() == selected_course
            and (q.get("subject") or "").strip().lower() == selected_subject.lower()
        ]
    elif source_mode == "combine" and selected_course and selected_subjects:
        sub_set = {s.strip().lower() for s in selected_subjects}
        source_filtered = [
            q for q in all_qs
            if (q.get("course_code") or "").strip().upper() == selected_course
            and (q.get("subject") or "").strip().lower() in sub_set
        ]
    else:
        # "all" mode: all questions (including legacy unclassified questions)
        source_filtered = all_qs

    # ✅ 2. FILTER QUESTION TYPE
    qtype_upper = str(qtype).upper()
    if qtype_upper == "MCQ":
        filtered = [q for q in source_filtered if str(q.get("type", "")).upper() == "MCQ"]
    elif qtype_upper == "DESCRIPTIVE":
        filtered = [q for q in source_filtered if str(q.get("type", "")).upper() == "DESCRIPTIVE"]
    else:  # MIX / MIXED
        filtered = source_filtered

    # ✅ 3. FILTER DIFFICULTY LEVEL
    if str(level).upper() != "ALL":
        filtered = [q for q in filtered if str(q.get("level", "")).lower() == str(level).lower()]

    # ❌ If no questions match
    if not filtered:
        flash("No questions found matching your selected criteria! Try selecting another subject or difficulty.", "error")
        return redirect(url_for("auth.choose_exam"))

    # ✅ 4. LIMIT COUNT & BALANCED MIXED SELECTION
    if count > len(filtered):
        count = len(filtered)

    if qtype_upper in ("MIX", "MIXED"):
        mcqs = [q for q in filtered if str(q.get("type", "")).upper() == "MCQ"]
        descs = [q for q in filtered if str(q.get("type", "")).upper() == "DESCRIPTIVE"]
        if mcqs and descs:
            half = count // 2
            mcq_sample = random.sample(mcqs, min(half, len(mcqs)))
            desc_need = count - len(mcq_sample)
            desc_sample = random.sample(descs, min(desc_need, len(descs)))
            selected_qs = mcq_sample + desc_sample
            if len(selected_qs) < count:
                rem = [q for q in filtered if q not in selected_qs]
                selected_qs.extend(random.sample(rem, min(count - len(selected_qs), len(rem))))
            random.shuffle(selected_qs)
        else:
            selected_qs = random.sample(filtered, count)
    else:
        selected_qs = random.sample(filtered, count)

    # ✅ CALCULATE DYNAMIC EXAM DURATION (Question-wise and Type-wise)
    # MCQ: 1.5 minutes (90s) per question
    # Descriptive: 3 minutes (180s) per question
    total_seconds = 0
    for q in selected_qs:
        if q.get("type", "").upper() == "DESCRIPTIVE":
            total_seconds += 180  # 3 mins for descriptive
        else:
            total_seconds += 90   # 1.5 mins for MCQ

    total_seconds = max(60, total_seconds)

    # ✅ SAVE TO SESSION
    session["questions"] = selected_qs
    session["index"] = 0
    session["answers"] = {}
    session["start_time"] = int(time.time())
    session["total_time"] = total_seconds
    session.pop("course_exam_id", None)
    session.pop("course_exam_title", None)
    session.pop("course_code", None)

    return redirect(url_for("exam.exam"))


# =========================================================
#  OFFICIAL COURSE EXAMINATIONS (LISTING & SECURITY ENGINE)
# =========================================================

def _format_exam_date(date_str: str) -> str:
    """Format e.g. '2026-09-28' -> '28 September 2026'"""
    try:
        from datetime import datetime
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return dt.strftime("%d %B %Y")
    except Exception:
        return str(date_str)

def _format_exam_time(time_str: str) -> str:
    """Format e.g. '10:00' -> '10:00 AM'"""
    try:
        from datetime import datetime
        dt = datetime.strptime(str(time_str).strip(), "%H:%M")
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return str(time_str)

def _format_upcoming_available_on(date_str: str, time_str: str) -> dict:
    """Format for locked holographic badge: '28 SEP 2026' and '10:00 AM'"""
    f_date = str(date_str).upper()
    f_time = str(time_str)
    try:
        from datetime import datetime
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        f_date = dt.strftime("%d %b %Y").upper()
    except Exception:
        pass
    try:
        from datetime import datetime
        tm = datetime.strptime(str(time_str).strip(), "%H:%M")
        f_time = tm.strftime("%I:%M %p").lstrip("0")
    except Exception:
        pass
    return {"date": f_date, "time": f_time}


@exam_bp.route("/course-exams")
def course_exams():
    """
    Renders official course exams for students, divided into:
      SECTION 1: LIVE EXAMS (Active live exams within schedule window, not completed)
      SECTION 2: UPCOMING EXAMS (Chronologically ordered future exams, locked with countdown)
      SECTION 3: COMPLETED / PAST EXAMS (Completed attempts with scores, or closed/missed exams)
    """
    if "username" not in session:
        flash("Please log in to view course examinations.", "error")
        return redirect(url_for("auth.auth_page"))

    from datetime import datetime
    from utils import (
        load_course_exams,
        load_results,
        parse_exam_datetimes,
        get_exam_live_status,
        get_student_identity_from_session_or_db,
        is_student_eligible_for_exam,
        get_student_exam_result
    )

    student_info = get_student_identity_from_session_or_db(session)
    if student_info.get("user_type") != "UNIVERSITY":
        flash("Official university examinations are available only to registered university students.", "error")
        return redirect(url_for("auth.exam_options"))

    username = student_info.get("username", "")

    now = datetime.now()
    all_exams = load_course_exams()

    live_exams = []
    upcoming_exams = []
    past_exams = []

    courses_set = set()
    subjects_set = set()

    for e in all_exams:
        # STRICT SERVER-SIDE ELIGIBILITY CHECK: Never expose cross-program or unauthorized exams
        if not is_student_eligible_for_exam(student_info, e):
            continue

        status_val = str(e.get("status") or "").strip()
        # Never expose Draft exams to students
        if status_val.lower() == "draft":
            continue

        c_code = (e.get("course_code") or "").strip().upper()
        c_name = (e.get("course_name") or "").strip()
        subj = (e.get("subject") or "").strip()
        if c_code: courses_set.add(c_code)
        elif c_name: courses_set.add(c_name)
        if subj: subjects_set.add(subj)

        start_dt, end_dt = parse_exam_datetimes(e)
        live_info = get_exam_live_status(e)

        f_date = _format_exam_date(e.get("exam_date", ""))
        f_start_time = _format_exam_time(e.get("start_time", ""))
        f_end_time = _format_exam_time(e.get("end_time", ""))
        avail_on = _format_upcoming_available_on(e.get("exam_date", ""), e.get("start_time", ""))

        exam_type_display = e.get("exam_type", "MCQ")
        if str(exam_type_display).lower() == "mixed":
            exam_type_display = "MCQ + Descriptive"

        # Check if student has already completed this exam
        submission = get_student_exam_result(username, e)
        is_taken = (submission is not None)

        submission_score = None
        submission_total = None
        submission_pct = None
        submission_date = None
        submission_time_taken = None
        if submission:
            try:
                submission_score = float(submission.get("score", 0))
                submission_total = float(submission.get("total", 0))
                if submission_total > 0:
                    submission_pct = round((submission_score / submission_total) * 100, 1)
            except Exception:
                pass
            submission_date = submission.get("date", "")
            submission_time_taken = submission.get("time_taken", "")

        # Check if exam is within the active live window
        is_live_now = False
        if start_dt and end_dt:
            is_live_now = (start_dt <= now <= end_dt)
        elif start_dt:
            is_live_now = (now >= start_dt)
        else:
            is_live_now = True

        # Check if exam schedule has completely expired
        is_expired = False
        if end_dt and now > end_dt:
            is_expired = True

        # Countdown calculation for upcoming exams
        starts_in_str = ""
        target_iso = ""
        if start_dt:
            target_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
            if now < start_dt:
                diff = start_dt - now
                days = diff.days
                hours = diff.seconds // 3600
                minutes = (diff.seconds % 3600) // 60
                if days > 0:
                    starts_in_str = f"Starts in: {days} Days {hours} Hours"
                elif hours > 0:
                    starts_in_str = f"Starts in: {hours} Hours {minutes} Mins"
                else:
                    starts_in_str = f"Starts in: {minutes} Mins"

        decorated = {
            **e,
            "live": live_info,
            "formatted_date": f_date,
            "formatted_start_time": f_start_time,
            "formatted_end_time": f_end_time,
            "available_on_date": avail_on["date"],
            "available_on_time": avail_on["time"],
            "exam_type_display": exam_type_display,
            "start_dt_obj": start_dt,
            "end_dt_obj": end_dt,
            "start_iso": target_iso,
            "starts_in": starts_in_str,
            "is_taken": is_taken,
            "submission_score": submission_score,
            "submission_total": submission_total,
            "submission_pct": submission_pct,
            "submission_date": submission_date,
            "submission_time_taken": submission_time_taken,
            "is_live_now": is_live_now,
            "is_expired": is_expired,
            "can_start": is_live_now and not is_taken and status_val.lower() == "published"
        }

        # CATEGORIZE INTO 3 STRICT SECTIONS:
        # SECTION 3: COMPLETED / PAST EXAMS
        if is_taken:
            decorated["completion_status"] = "Completed"
            past_exams.append(decorated)
        elif is_expired or status_val.lower() == "closed":
            decorated["completion_status"] = "Closed"
            past_exams.append(decorated)
        # SECTION 2: UPCOMING EXAMS
        elif start_dt and now < start_dt:
            upcoming_exams.append(decorated)
        # SECTION 1: LIVE EXAMS
        else:
            live_exams.append(decorated)

    # Sort upcoming chronologically (earliest first)
    upcoming_exams.sort(key=lambda x: x["start_dt_obj"] if x["start_dt_obj"] else datetime.max)
    # Sort live exams by start date/time
    live_exams.sort(key=lambda x: x["start_dt_obj"] if x["start_dt_obj"] else datetime.min)
    # Sort past/completed exams descending (most recent first)
    past_exams.sort(key=lambda x: x["end_dt_obj"] if x["end_dt_obj"] else datetime.min, reverse=True)

    return render_template(
        "course_exams.html",
        live_exams=live_exams,
        today_exams=live_exams,  # backward compatibility alias
        upcoming_exams=upcoming_exams,
        past_exams=past_exams,
        all_courses=sorted(list(courses_set)),
        all_subjects=sorted(list(subjects_set)),
        current_time=now.strftime("%d %B %Y, %I:%M %p"),
        student_info=student_info,
    )


@exam_bp.route("/course-exam/<string:exam_id>", methods=["GET", "POST"])
@exam_bp.route("/start_course_exam/<string:exam_id>", methods=["GET", "POST"])
def start_course_exam(exam_id):
    """
    Secure server-side endpoint for students attempting an official course exam.
    Strictly verifies:
      1. Student session authentication
      2. Valid exam ID in course_exams.json
      3. Student academic eligibility (program, batch, academic year or specific student inclusion)
      4. Not already completed/submitted by the student
      5. Current date & time >= start_time (locks future attempts)
      6. Current date & time <= end_time (locks ended exams)
      7. Exam is active / published
      8. Availability of questions matching course_code + subject
    """
    # 1. Verify student is logged in
    if "username" not in session:
        flash("Please log in to attempt a course examination.", "error")
        return redirect(url_for("auth.auth_page"))

    import time
    import random
    from datetime import datetime
    from utils import (
        get_course_exam_by_id,
        load_questions,
        parse_exam_datetimes,
        get_matching_questions,
        get_student_identity_from_session_or_db,
        is_student_eligible_for_exam,
        get_student_exam_result
    )

    # 2. Find exam & verify exists
    exam = get_course_exam_by_id(exam_id)
    if not exam:
        flash("Invalid examination ID. The requested exam does not exist.", "error")
        return redirect(url_for("exam.course_exams"))

    # 3. Verify student eligibility strictly on the server-side
    student_info = get_student_identity_from_session_or_db(session)
    if student_info.get("user_type") != "UNIVERSITY":
        flash("Official university examinations are available only to registered university students.", "error")
        return redirect(url_for("auth.exam_options"))

    if not is_student_eligible_for_exam(student_info, exam):
        flash("You are not eligible for this examination.", "error")
        return redirect(url_for("exam.course_exams"))

    # 4. Verify student has not already completed this exam
    existing_result = get_student_exam_result(session["username"], exam)
    if existing_result:
        flash("You have already completed this examination.", "info")
        return redirect(url_for("exam.course_exams"))

    # 5. Verify exam is active / published
    if str(exam.get("status") or "").strip().lower() != "published":
        flash("This examination is not active.", "error")
        return redirect(url_for("exam.course_exams"))

    # 6. Verify schedule datetime
    start_dt, end_dt = parse_exam_datetimes(exam)
    now = datetime.now()

    # Reject future / locked exams with exact required message
    if start_dt and now < start_dt:
        flash("Exam is not available yet. Please return at the scheduled time.", "error")
        return redirect(url_for("exam.course_exams"))

    # Reject expired exams
    if end_dt and now > end_dt:
        flash("This examination has already closed.", "error")
        return redirect(url_for("exam.course_exams"))

    # 5. Question availability strictly matching course_code + subject
    course_code = (exam.get("course_code") or "").strip()
    subject = (exam.get("subject") or "").strip()
    exam_type = exam.get("exam_type", "ALL")
    difficulty = exam.get("difficulty", "ALL")

    matching_qs = get_matching_questions(
        course_code=course_code,
        subject=subject,
        qtype=exam_type,
        difficulty=difficulty,
        program_code=exam.get("program_code"),
        admission_year=exam.get("admission_year"),
        academic_year=exam.get("academic_year")
    )

    explicit_ids = exam.get("question_ids")
    if isinstance(explicit_ids, list) and len(explicit_ids) > 0:
        all_qs = load_questions()
        qs_by_id = {str(q.get("id")): q for q in all_qs if q.get("id")}
        explicit_qs = [qs_by_id[str(qid)] for qid in explicit_ids if str(qid) in qs_by_id]
        if explicit_qs:
            matching_qs = explicit_qs

    if not matching_qs:
        flash(f"No questions are currently available for Course {course_code} ({subject}). Please contact your instructor.", "error")
        return redirect(url_for("exam.course_exams"))

    # 6. Sample questions up to configured count strictly from matching pool
    req_count = int(exam.get("num_questions") or 10)
    count = min(req_count, len(matching_qs))

    # Balanced mix for Mixed exam type
    if str(exam_type).upper() == "MIXED":
        mcqs = [q for q in matching_qs if q.get("type") == "MCQ"]
        descs = [q for q in matching_qs if q.get("type") == "DESCRIPTIVE"]
        if mcqs and descs:
            half = count // 2
            mcq_sample = random.sample(mcqs, min(half, len(mcqs)))
            desc_need = count - len(mcq_sample)
            desc_sample = random.sample(descs, min(desc_need, len(descs)))
            selected_qs = mcq_sample + desc_sample
            if len(selected_qs) < count:
                rem = [q for q in matching_qs if q not in selected_qs]
                selected_qs.extend(random.sample(rem, min(count - len(selected_qs), len(rem))))
            random.shuffle(selected_qs)
        else:
            selected_qs = random.sample(matching_qs, count)
    else:
        selected_qs = random.sample(matching_qs, count)

    # 7. Configure session duration & metadata
    duration_minutes = int(exam.get("duration") or 60)
    total_seconds = max(60, duration_minutes * 60)

    session["questions"] = selected_qs
    session["index"] = 0
    session["answers"] = {}
    session["start_time"] = int(time.time())
    session["total_time"] = total_seconds
    session["course_exam_id"] = exam["id"]
    session["course_exam_title"] = exam["title"]
    session["course_code"] = course_code
    session["subject"] = subject
    session["exam_type"] = exam.get("exam_type", "Mixed")

    return redirect(url_for("exam.exam"))
