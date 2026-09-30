# utils.py
import os
import json
import re
import time
import uuid
from typing import List, Dict, Any

# ---- Light-weight module-level constants (no heavy imports here) ----
USERS_FILE = "users.json"
RESULTS_FILE = "results.json"
QUESTIONS_FILE = "questions.json"
COURSE_EXAMS_FILE = "course_exams.json"

USERNAME_NO_SPACE = re.compile(r"^\S+$")


# ---- Validation helpers ----
def is_valid_username(name: str) -> bool:
    return bool(USERNAME_NO_SPACE.match(name or ""))

def password_has_spaces(p: str) -> bool:
    return " " in (p or "")

# ---- Answer-key normalization helpers ----
def _coerce_answer_key_to_string(ak) -> str:
    if ak is None:
        return ""
    if isinstance(ak, list):
        return ", ".join(str(x).strip() for x in ak if str(x).strip())
    if isinstance(ak, dict):
        parts = []
        for v in ak.values():
            if isinstance(v, (list, tuple)):
                parts.extend(str(x).strip() for x in v if str(x).strip())
            else:
                s = str(v).strip()
                if s:
                    parts.append(s)
        return ", ".join(parts)
    return str(ak).strip()

def _normalize_answer_key_text(key: str) -> str:
    if not key:
        return ""
    k = key.strip()
    if k.lower().startswith("keywords:"):
        k = k.split(":", 1)[1].strip()
    parts = [p.strip() for p in re.split(r"[,\n;]+", k) if p.strip()]
    return " ".join(parts) if parts else k

# ---- Lazy-loaded similarity model (do NOT import heavy libs at module import time) ----
_SIM_MODEL = None
_cosine_similarity = None
_similarity_model_loaded = False

def ensure_similarity_model() -> bool:
    """
    Load the sentence-transformers model on first use.
    Returns True if model loaded successfully, False otherwise.
    """
    global _SIM_MODEL, _cosine_similarity, _similarity_model_loaded
    if _similarity_model_loaded:
        return _SIM_MODEL is not None

    _similarity_model_loaded = True
    try:
        # Import inside the function to avoid heavy startup cost
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        _SIM_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        _cosine_similarity = cosine_similarity
        return True
    except Exception as e:
        # Model not available — keep _SIM_MODEL = None
        _SIM_MODEL = None
        _cosine_similarity = None
        # Print a friendly, non-fatal log so you can see why similarity won't run.
        print("SentenceTransformer not available (deferred).", e)
        return False

def descriptive_similarity(student_answer: str, answer_key: str) -> float:
    """
    Returns a float in [0.0, 1.0] representing semantic similarity
    between student_answer and the normalized answer_key.
    If similarity model is unavailable or inputs are empty -> returns 0.0.
    """
    if not student_answer or not answer_key:
        return 0.0
    if not ensure_similarity_model():
        return 0.0
    model_text = _normalize_answer_key_text(answer_key)
    vec = _SIM_MODEL.encode([student_answer, model_text])
    score = _cosine_similarity([vec[0]], [vec[1]])[0][0]
    return max(0.0, min(1.0, float(score)))

# ---- Question type and migration helpers ----
def _fix_type_to_capital(item_type) -> str:
    if not item_type:
        return "MCQ"
    t = str(item_type).strip().upper()
    if t in ("MCQ", "DESCRIPTIVE"):
        return t
    if t in ("OBJECTIVE", "MULTIPLE CHOICE"):
        return "MCQ"
    if t in ("SUBJECTIVE", "LONG", "LONG ANSWER"):
        return "DESCRIPTIVE"
    return "MCQ"

def _migrate_one_question(raw) -> dict:
    if not isinstance(raw, dict):
        return {}

    q = dict(raw)

    q_text = str(q.get("question") or q.get("q") or "").strip()
    if not q_text:
        return {}

    level = str(q.get("level") or "Easy").strip() or "Easy"
    qtype = _fix_type_to_capital(q.get("type"))
    source = str(q.get("source") or "MANUAL").strip().upper()

    qid = str(q.get("id") or "").strip()
    if not qid:
        qid = f"Q-{uuid.uuid4().hex[:8].upper()}"

    # Course & Subject classification fields
    course_code = str(q.get("course_code") or "").strip().upper()
    course_name = str(q.get("course_name") or "").strip()
    subject = str(q.get("subject") or "").strip()
    unit = str(q.get("unit") or "").strip()
    topic = str(q.get("topic") or "").strip()

    # Migration defaults for older questions without classification
    if not course_code:
        q_lower = q_text.lower()
        if any(w in q_lower for w in ["python", "interpreter", "decorator", "gil", "list", "variable"]):
            course_code = "CS101"
            course_name = "Computer Science & Programming"
            subject = "Python Programming"
            unit = unit or "Module I"
            topic = topic or "Python Fundamentals"
        elif any(w in q_lower for w in ["india", "taj mahal", "ganges", "rajasthan", "cricket", "capital"]):
            course_code = "GEN101"
            course_name = "General Studies"
            subject = "General Knowledge"
            unit = unit or "Module I"
            topic = topic or "Indian Heritage & Geography"
        elif any(w in q_lower for w in ["photosynthesis", "renaissance", "climate", "biodiversity", "internet"]):
            course_code = "GEN102"
            course_name = "Science & Society"
            subject = "Environmental & Historical Sciences"
            unit = unit or "Module II"
            topic = topic or "General Science"
        else:
            course_code = "GEN101"
            course_name = "General Studies"
            subject = "General Knowledge"
            unit = unit or "Module I"
            topic = topic or "General Knowledge"

    if not course_name:
        course_name = course_code

    if not subject:
        subject = "General"

    if qtype == "MCQ":
        opts = q.get("options")
        if not isinstance(opts, list):
            alt = q.get("a")
            if isinstance(alt, list):
                opts = alt
            else:
                opts = []

        opts = [str(x).strip() for x in opts if str(x).strip()]
        correct = str(q.get("correct") or "").strip()

        return {
            "id": qid,
            "course_code": course_code,
            "course_name": course_name,
            "subject": subject,
            "unit": unit,
            "topic": topic,
            "type": "MCQ",
            "level": level,
            "question": q_text,
            "q": q_text,
            "options": opts,
            "a": opts,
            "correct": correct,
            "source": source
        }

    # DESCRIPTIVE
    ak = _coerce_answer_key_to_string(q.get("answer_key"))
    if ak and not ak.lower().startswith("keywords:"):
        ak = "keywords: " + ak

    try:
        max_marks = int(q.get("max_marks", 5))
    except Exception:
        max_marks = 5

    return {
        "id": qid,
        "course_code": course_code,
        "course_name": course_name,
        "subject": subject,
        "unit": unit,
        "topic": topic,
        "type": "DESCRIPTIVE",
        "level": level,
        "question": q_text,
        "q": q_text,
        "answer_key": ak,
        "max_marks": max_marks,
        "source": source
    }

def _migrate_questions_list(qs) -> List[Dict[str,Any]]:
    out = []
    if not isinstance(qs, list):
        return out
    for item in qs:
        fixed = _migrate_one_question(item)
        if fixed:
            out.append(fixed)
    return out

# ---- JSON helpers ----
def _read_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def load_json(file):
    if not os.path.exists(file):
        return [] if file == QUESTIONS_FILE else {}
    try:
        return _read_json(file)
    except Exception:
        return [] if file == QUESTIONS_FILE else {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Refresh cached questions whenever questions.json is updated
    if file == QUESTIONS_FILE:
        global _QUESTIONS_CACHE, _QUESTIONS_CACHE_ATIME
        _QUESTIONS_CACHE = data
        _QUESTIONS_CACHE_ATIME = time.time()
# ---- Public simple helpers ----
def load_users(): return load_json(USERS_FILE)
def save_users(x): save_json(USERS_FILE, x)
def load_results(): return load_json(RESULTS_FILE)
def save_results(x): save_json(RESULTS_FILE, x)

# ---- Cached questions loader (lazy + cached) ----
_QUESTIONS_CACHE: List[Dict[str,Any]] | None = None
_QUESTIONS_CACHE_ATIME: float | None = None

def _load_questions_from_disk():
    global _QUESTIONS_CACHE, _QUESTIONS_CACHE_ATIME
    raw = load_json(QUESTIONS_FILE)
    migrated = _migrate_questions_list(raw if isinstance(raw, list) else [])
    _QUESTIONS_CACHE = migrated
    _QUESTIONS_CACHE_ATIME = time.time()
    return _QUESTIONS_CACHE

def load_questions():
    """
    Public API: returns cached questions list, loading/migrating once on first call.
    Use reload_questions_from_disk() to force a refresh.
    """
    global _QUESTIONS_CACHE
    if _QUESTIONS_CACHE is not None:
        return _QUESTIONS_CACHE
    return _load_questions_from_disk()

def reload_questions_from_disk():
    """
    Force reload of questions from disk and update cache.
    """
    return _load_questions_from_disk()

# =========================================================
#  Course Exam Management Helpers
# =========================================================
from datetime import datetime

def load_course_exams() -> List[Dict[str, Any]]:
    """Load all configured course examinations from course_exams.json."""
    data = load_json(COURSE_EXAMS_FILE)
    if isinstance(data, list):
        return data
    return []

def save_course_exams(exams: List[Dict[str, Any]]):
    """Save course examinations list to course_exams.json."""
    save_json(COURSE_EXAMS_FILE, exams)

def get_course_exam_by_id(exam_id: str) -> Dict[str, Any] | None:
    """Retrieve a single course exam by unique ID."""
    if not exam_id:
        return None
    for exam in load_course_exams():
        if str(exam.get("id")) == str(exam_id):
            return exam
    return None

def parse_exam_datetimes(exam: Dict[str, Any]):
    """
    Parses exam_date and start_time / end_time into datetime objects.
    Returns (start_dt, end_dt) or (None, None) if parsing fails.
    """
    date_str = str(exam.get("exam_date") or "").strip()
    start_str = str(exam.get("start_time") or "").strip()
    end_str = str(exam.get("end_time") or "").strip()

    start_dt = None
    end_dt = None

    if date_str and start_str:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M:%S"):
            try:
                start_dt = datetime.strptime(f"{date_str} {start_str}", fmt)
                break
            except Exception:
                pass

    if date_str and end_str:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M:%S"):
            try:
                end_dt = datetime.strptime(f"{date_str} {end_str}", fmt)
                break
            except Exception:
                pass

    return start_dt, end_dt

def get_matching_questions(course_code: str, subject: str, qtype: str = "ALL", difficulty: str = "ALL") -> List[Dict[str, Any]]:
    """
    Filter questions strictly by course_code and subject (case-insensitive & stripped).
    Optionally filter by qtype ('MCQ', 'DESCRIPTIVE', 'MIXED'/'ALL')
    and difficulty ('ALL', 'Easy', 'Medium', 'Hard').
    """
    all_qs = load_questions()
    c_target = (course_code or "").strip().upper()
    s_target = (subject or "").strip().lower()

    if not c_target or not s_target:
        return []

    matched = []
    for q in all_qs:
        q_course = str(q.get("course_code") or "").strip().upper()
        q_subject = str(q.get("subject") or "").strip().lower()

        # Both course_code and subject must match strictly and must not be empty
        if not q_course or not q_subject or q_course != c_target or q_subject != s_target:
            continue

        # Type filter
        t = str(q.get("type") or "").strip().upper()
        if qtype and qtype.upper() not in ("ALL", "MIXED"):
            if t != qtype.upper():
                continue

        # Difficulty filter
        lvl = str(q.get("level") or "").strip()
        if difficulty and difficulty.upper() != "ALL":
            if lvl.lower() != difficulty.lower():
                continue

        matched.append(q)

    return matched

def get_exam_live_status(exam: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determines live temporal state for an exam based on system datetime.
    Returns dictionary with flags, labels, badge classes, and matching question count.
    """
    now = datetime.now()
    start_dt, end_dt = parse_exam_datetimes(exam)
    status = str(exam.get("status") or "Draft").strip()

    is_live = False
    is_upcoming = False
    is_completed = False

    if status == "Closed":
        time_state = "closed"
        badge_label = "CLOSED"
        badge_class = "badge-closed"
        is_completed = True
    elif status == "Draft":
        time_state = "draft"
        badge_label = "DRAFT"
        badge_class = "badge-draft"
    else:  # Published
        if start_dt and end_dt:
            if now < start_dt:
                time_state = "upcoming"
                badge_label = "UPCOMING (LOCKED)"
                badge_class = "badge-upcoming"
                is_upcoming = True
            elif start_dt <= now <= end_dt:
                time_state = "live"
                badge_label = "LIVE NOW"
                badge_class = "badge-live"
                is_live = True
            else:
                time_state = "completed"
                badge_label = "COMPLETED"
                badge_class = "badge-completed"
                is_completed = True
        elif start_dt and now < start_dt:
            time_state = "upcoming"
            badge_label = "UPCOMING (LOCKED)"
            badge_class = "badge-upcoming"
            is_upcoming = True
        elif end_dt and now > end_dt:
            time_state = "completed"
            badge_label = "COMPLETED"
            badge_class = "badge-completed"
            is_completed = True
        else:
            time_state = "live"
            badge_label = "AVAILABLE"
            badge_class = "badge-live"
            is_live = True

    matching_qs = get_matching_questions(
        course_code=exam.get("course_code"),
        subject=exam.get("subject"),
        qtype=exam.get("exam_type", "ALL"),
        difficulty=exam.get("difficulty", "ALL")
    )

    req_q = int(exam.get("num_questions") or 10)
    avail_q = len(matching_qs)

    return {
        "status": status,
        "time_state": time_state,
        "is_live": is_live,
        "is_upcoming": is_upcoming,
        "is_completed": is_completed,
        "badge_label": badge_label,
        "badge_class": badge_class,
        "start_dt": start_dt.strftime("%Y-%m-%d %H:%M") if start_dt else None,
        "end_dt": end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else None,
        "available_questions": avail_q,
        "required_questions": req_q,
        "has_enough_questions": avail_q >= req_q
    }

def get_course_exam_stats() -> Dict[str, int]:
    exams = load_course_exams()
    total_scheduled = len(exams)
    active_exams = 0
    upcoming_exams = 0
    completed_exams = 0
    draft_exams = 0

    for e in exams:
        live = get_exam_live_status(e)
        if live["status"] == "Draft":
            draft_exams += 1
        elif live["is_live"]:
            active_exams += 1
        elif live["is_upcoming"]:
            upcoming_exams += 1
        elif live["is_completed"]:
            completed_exams += 1

    return {
        "total_scheduled": total_scheduled,
        "active_exams": active_exams,
        "upcoming_exams": upcoming_exams,
        "completed_exams": completed_exams,
        "draft_exams": draft_exams
    }

def get_unique_courses_and_subjects() -> Dict[str, List[str]]:
    qs = load_questions()
    exams = load_course_exams()

    courses = set()
    course_names = set()
    subjects = set()

    for q in qs:
        c = str(q.get("course_code") or "").strip().upper()
        cn = str(q.get("course_name") or "").strip()
        s = str(q.get("subject") or "").strip()
        if c: courses.add(c)
        if cn: course_names.add(cn)
        if s: subjects.add(s)

    for e in exams:
        c = str(e.get("course_code") or "").strip().upper()
        cn = str(e.get("course_name") or "").strip()
        s = str(e.get("subject") or "").strip()
        if c: courses.add(c)
        if cn: course_names.add(cn)
        if s: subjects.add(s)

    return {
        "courses": sorted(list(courses)),
        "course_names": sorted(list(course_names)),
        "subjects": sorted(list(subjects))
    }


