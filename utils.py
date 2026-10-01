# utils.py
import os
import json
import re
import time
import uuid
from typing import List, Dict, Any, Optional

# ---- Light-weight module-level constants (no heavy imports here) ----
USERS_FILE = "users.json"
RESULTS_FILE = "results.json"
QUESTIONS_FILE = "questions.json"
COURSE_EXAMS_FILE = "course_exams.json"

USERNAME_NO_SPACE = re.compile(r"^\S+$")


# ---- Validation helpers ----
def is_valid_username(name: str) -> bool:
    """Validates student name. Accepts names with spaces, minimum 2 characters."""
    if not name:
        return False
    return len(str(name).strip()) >= 2

def password_has_spaces(p: str) -> bool:
    return " " in (p or "")


# ---- Student Academic Identity helpers ----
STUDENT_CODE_REGEX = re.compile(r"^([A-Z0-9]+)/([A-Z0-9]+)/(\d{2})/([A-Z0-9]+)$")

PROGRAM_NAMES = {
    "AIR": "AI & Robotics",
    "CSE": "Computer Science & Engineering",
    "ECE": "Electronics & Communication Engineering",
    "IT": "Information Technology",
    "EE": "Electrical Engineering",
    "ME": "Mechanical Engineering",
    "CE": "Civil Engineering",
    "BCA": "Bachelor of Computer Applications",
    "MCA": "Master of Computer Applications",
    "BBA": "Bachelor of Business Administration",
    "MBA": "Master of Business Administration",
    "AIML": "AI & Machine Learning",
    "DS": "Data Science",
    "CS": "Computer Science",
    "BAR": "Bachelor of Arts"
}

PROGRAMS_FILE = os.path.join(os.path.dirname(__file__), "programs.json")

DEFAULT_PROGRAMS = [
    {"name": "AI & Robotics", "code": "AIR"},
    {"name": "Bachelor of Arts", "code": "BAR"},
    {"name": "Computer Science & Engineering", "code": "CSE"},
    {"name": "Electronics & Communication Engineering", "code": "ECE"},
    {"name": "Information Technology", "code": "IT"},
    {"name": "Electrical Engineering", "code": "EE"},
    {"name": "Mechanical Engineering", "code": "ME"},
    {"name": "Civil Engineering", "code": "CE"},
    {"name": "Bachelor of Computer Applications", "code": "BCA"},
    {"name": "Master of Computer Applications", "code": "MCA"},
    {"name": "Bachelor of Business Administration", "code": "BBA"},
    {"name": "Master of Business Administration", "code": "MBA"},
    {"name": "AI & Machine Learning", "code": "AIML"},
    {"name": "Data Science", "code": "DS"},
    {"name": "Computer Science", "code": "CS"}
]

def load_programs() -> List[Dict[str, str]]:
    """Loads program definitions from programs.json or initializes defaults."""
    if not os.path.exists(PROGRAMS_FILE):
        save_programs(DEFAULT_PROGRAMS)
        return list(DEFAULT_PROGRAMS)
    try:
        with open(PROGRAMS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return list(DEFAULT_PROGRAMS)
    except Exception:
        return list(DEFAULT_PROGRAMS)

def save_programs(programs: List[Dict[str, str]]) -> None:
    """Saves program definitions to programs.json."""
    with open(PROGRAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(programs, f, indent=2, ensure_ascii=False)

def get_program_by_code(code: str) -> Optional[Dict[str, str]]:
    """Finds program definition by code (case-insensitive)."""
    if not code:
        return None
    c = str(code).strip().upper()
    for p in load_programs():
        if str(p.get("code") or "").strip().upper() == c:
            return p
    return None

def get_program_by_name(name: str) -> Optional[Dict[str, str]]:
    """Finds program definition by name (case-insensitive)."""
    if not name:
        return None
    n = str(name).strip().lower()
    for p in load_programs():
        if str(p.get("name") or "").strip().lower() == n:
            return p
    return None

def get_program_name(program_code: str) -> str:
    """Returns mapped human-readable program title or fallback to uppercase code."""
    if not program_code:
        return "General"
    code = str(program_code).strip().upper()
    prog = get_program_by_code(code)
    if prog:
        return prog.get("name", code)
    return PROGRAM_NAMES.get(code, code)

def get_program_code(program_name: str) -> str:
    """Returns mapped program code for given program name."""
    if not program_name:
        return ""
    p_name = str(program_name).strip().lower()
    for p in load_programs():
        if str(p.get("name") or "").strip().lower() == p_name or str(p.get("code") or "").strip().lower() == p_name:
            return str(p.get("code") or "").strip().upper()
    for c, n in PROGRAM_NAMES.items():
        if n.strip().lower() == p_name:
            return c
    return program_name.strip().upper()

def count_students_in_program(program_code: str) -> int:
    """Counts registered university students assigned to a program code."""
    if not program_code:
        return 0
    target_code = str(program_code).strip().upper()
    users = load_users()
    count = 0
    for u, rec in users.items():
        if not isinstance(rec, dict):
            continue
        if rec.get("user_type") == "UNIVERSITY" and str(rec.get("program_code") or "").strip().upper() == target_code:
            count += 1
    return count

def calculate_academic_year(admission_year: Any) -> str:
    """Calculates student academic year (e.g. 1st Year, 2nd Year, 3rd Year) from admission year."""
    if not admission_year:
        return "N/A"
    try:
        from datetime import datetime
        current_year = datetime.now().year
        adm = int(admission_year)
        diff = current_year - adm + 1
        if diff <= 1:
            return "1st Year"
        elif diff == 2:
            return "2nd Year"
        elif diff == 3:
            return "3rd Year"
        elif diff == 4:
            return "4th Year"
        elif diff > 4:
            return f"{diff}th Year"
        else:
            return "1st Year"
    except Exception:
        return "N/A"

def parse_student_code(code: str) -> dict | None:
    """
    Parses and validates student code in format UNIVERSITY/PROGRAM/YY/ROLL.
    Example: 'BWU/AIR/24/029' ->
    {
        'student_code': 'BWU/AIR/24/029',
        'university_code': 'BWU',
        'program_code': 'AIR',
        'program_name': 'AI & Robotics',
        'admission_year': 2024,
        'roll_number': '029',
        'academic_year': '3rd Year'
    }
    Returns None if format is invalid.
    """
    if not code:
        return None
    c = str(code).strip().upper()
    m = STUDENT_CODE_REGEX.match(c)
    if not m:
        return None
    univ, prog, yy_str, roll = m.groups()
    yy = int(yy_str)
    admission_year = 2000 + yy if yy < 70 else 1900 + yy
    prog_name = get_program_name(prog)
    academic_year = calculate_academic_year(admission_year)
    return {
        "student_code": c,
        "university_code": univ,
        "program_code": prog,
        "program_name": prog_name,
        "admission_year": admission_year,
        "roll_number": roll,
        "academic_year": academic_year
    }

def is_student_code_taken(student_code: str, exclude_id: str = None) -> bool:
    """Checks whether a student code has already been registered (case-insensitive)."""
    if not student_code:
        return False
    target = str(student_code).strip().upper()
    users = load_users()
    for ukey, udata in users.items():
        if not isinstance(udata, dict):
            continue
        uid = str(udata.get("id") or ukey)
        if exclude_id and (uid == str(exclude_id) or ukey.lower() == str(exclude_id).lower()):
            continue
        sc = str(udata.get("student_code") or "").strip().upper()
        if sc and sc == target:
            return True
    return False

def is_email_taken(email: str, exclude_id: str = None) -> bool:
    """Checks whether an email has already been registered across the system (case-insensitive)."""
    if not email:
        return False
    target = str(email).strip().lower()
    users = load_users()
    for ukey, udata in users.items():
        if not isinstance(udata, dict):
            continue
        uid = str(udata.get("id") or ukey)
        if exclude_id and (uid == str(exclude_id) or ukey.lower() == str(exclude_id).lower()):
            continue
        rec_email = str(udata.get("email") or "").strip().lower()
        if rec_email and rec_email == target:
            return True
    return False

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

    # Program, Admission Year & Academic Year classification
    program_code = str(q.get("program_code") or "").strip().upper()
    program_name = str(q.get("program_name") or "").strip()
    if program_code:
        if program_code == "ALL":
            program_name = "All Programs"
        elif not program_name:
            program_name = get_program_name(program_code)

    raw_adm = q.get("admission_year")
    if raw_adm in (None, ""):
        admission_year = None
    elif str(raw_adm).strip().upper() in ("ALL", "ALL BATCHES"):
        admission_year = "ALL"
    else:
        try:
            admission_year = int(raw_adm)
        except (ValueError, TypeError):
            admission_year = str(raw_adm).strip()

    academic_year = str(q.get("academic_year") or "").strip()
    if academic_year.upper() in ("ALL", "ALL YEARS"):
        academic_year = "ALL"

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
            "program_code": program_code,
            "program_name": program_name,
            "admission_year": admission_year,
            "academic_year": academic_year,
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
        "program_code": program_code,
        "program_name": program_name,
        "admission_year": admission_year,
        "academic_year": academic_year,
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
def normalize_user_record(username: str, data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    rec = dict(data)
    # Ensure internal unique technical id exists
    if "id" not in rec or not rec["id"]:
        rec["id"] = username
    # Ensure name and username fields are populated
    if "name" not in rec or not rec["name"]:
        rec["name"] = rec.get("username") or username
    if "username" not in rec or not rec["username"]:
        rec["username"] = rec.get("name") or username

    utype = rec.get("user_type")
    if not utype:
        if username.lower() in ("admin", "adminc") or rec.get("is_admin"):
            utype = "ADMIN"
        elif rec.get("student_code") or rec.get("program_code") or rec.get("university_code"):
            utype = "UNIVERSITY"
        else:
            utype = "EXTERNAL"
    rec["user_type"] = utype

    if utype == "UNIVERSITY":
        sc = rec.get("student_code", "")
        if sc and ("university_code" not in rec or "program_code" not in rec or "academic_year" not in rec):
            parsed = parse_student_code(sc)
            if parsed:
                for k, v in parsed.items():
                    if k not in rec or not rec[k]:
                        rec[k] = v
        if rec.get("admission_year") and not rec.get("academic_year"):
            rec["academic_year"] = calculate_academic_year(rec["admission_year"])
        if rec.get("program_code") and not rec.get("program_name"):
            rec["program_name"] = get_program_name(rec["program_code"])

    return rec

def load_users() -> Dict[str, Dict[str, Any]]:
    raw = load_json(USERS_FILE)
    if not isinstance(raw, dict):
        return {}
    normalized = {}
    for u, data in raw.items():
        normalized[u] = normalize_user_record(u, data)
    return normalized

def save_users(x): save_json(USERS_FILE, x)
def load_results(): return load_json(RESULTS_FILE)
def save_results(x): save_json(RESULTS_FILE, x)

def find_user_by_email(email: str):
    """Returns (username, user_record) matching the given email (case-insensitive), or None."""
    if not email:
        return None
    target = email.strip().lower()
    users = load_users()
    for uname, udata in users.items():
        if isinstance(udata, dict) and str(udata.get("email") or "").strip().lower() == target:
            return uname, udata
    return None

def find_university_student_by_credentials(email: str, student_code: str, password: str = None):
    """
    Strict university student authentication verification:
    Requires ALL THREE credentials:
      1. Email
      2. Student Code
      3. Password
    Matches email, student_code, and password for an account with user_type == 'UNIVERSITY'.
    Returns (username, user_record) or None.
    """
    if not email or not student_code or not password:
        return None
    from werkzeug.security import check_password_hash
    target_email = email.strip().lower()
    target_code = student_code.strip().upper()
    users = load_users()
    for uname, udata in users.items():
        if not isinstance(udata, dict):
            continue
        rec_type = udata.get("user_type") or ("UNIVERSITY" if (udata.get("student_code") or udata.get("program_code")) else "EXTERNAL")
        if rec_type != "UNIVERSITY":
            continue
        rec_email = str(udata.get("email") or "").strip().lower()
        rec_code = str(udata.get("student_code") or "").strip().upper()
        if rec_email == target_email and rec_code == target_code:
            pw_hash = udata.get("pw_hash") or ""
            if pw_hash and check_password_hash(pw_hash, password):
                return uname, udata
    return None


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

def get_matching_questions(
    course_code: str,
    subject: str,
    qtype: str = "ALL",
    difficulty: str = "ALL",
    program_code: Optional[str] = None,
    admission_year: Any = None,
    academic_year: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter questions strictly by course_code and subject (case-insensitive & stripped).
    Optionally filter by qtype ('MCQ', 'DESCRIPTIVE', 'MIXED'/'ALL'),
    difficulty ('ALL', 'Easy', 'Medium', 'Hard'),
    and academic targeting:
      - program_code: question matches if q.program_code == program_code OR q.program_code == 'ALL'
      - admission_year: question matches if str(q.admission_year) == str(admission_year) OR q.admission_year == 'ALL' OR q.program_code == 'ALL'
      - academic_year: question matches if q.academic_year.lower() == academic_year.lower() OR q.academic_year.upper() == 'ALL' OR q.program_code == 'ALL'
    """
    all_qs = load_questions()
    c_target = (course_code or "").strip().upper()
    s_target = (subject or "").strip().lower()

    if not c_target or not s_target:
        return []

    p_target = (program_code or "").strip().upper() if program_code else None
    adm_target = str(admission_year).strip() if admission_year not in (None, "") else None
    acad_target = str(academic_year).strip().lower() if academic_year not in (None, "") else None

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

        # Academic targeting filters (when specified on target/exam)
        q_prog = str(q.get("program_code") or "").strip().upper()
        q_adm = str(q.get("admission_year") or "").strip()
        q_acad = str(q.get("academic_year") or "").strip().lower()

        # If exam specifies a target program (and not "ALL"):
        if p_target and p_target != "ALL":
            if q_prog and q_prog != p_target and q_prog != "ALL":
                continue

        # If exam specifies target admission year (and not "ALL"):
        if adm_target and adm_target.upper() != "ALL":
            if q_adm and q_adm.upper() != "ALL" and q_adm != adm_target:
                if q_prog != "ALL":
                    continue

        # If exam specifies target academic year (and not "ALL"):
        if acad_target and acad_target != "all":
            if q_acad and q_acad != "all" and q_acad != acad_target:
                if q_prog != "ALL":
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
        difficulty=exam.get("difficulty", "ALL"),
        program_code=exam.get("program_code"),
        admission_year=exam.get("admission_year"),
        academic_year=exam.get("academic_year")
    )

    req_q = int(exam.get("num_questions") or 10)
    q_ids = exam.get("question_ids")
    if isinstance(q_ids, list) and len(q_ids) > 0:
        avail_q = len(q_ids)
    else:
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

    units = set()
    topics = set()

    for q in qs:
        c = str(q.get("course_code") or "").strip().upper()
        cn = str(q.get("course_name") or "").strip()
        s = str(q.get("subject") or "").strip()
        u = str(q.get("unit") or "").strip()
        t = str(q.get("topic") or "").strip()
        if c: courses.add(c)
        if cn: course_names.add(cn)
        if s: subjects.add(s)
        if u: units.add(u)
        if t: topics.add(t)

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
        "subjects": sorted(list(subjects)),
        "units": sorted(list(units)),
        "topics": sorted(list(topics))
    }


# ==============================================================
# COURSE EXAM STUDENT ELIGIBILITY & TARGETING HELPERS
# ==============================================================

def get_available_programs() -> List[Dict[str, str]]:
    """
    Returns list of academic programs with program_code, program_name, and UI label.
    Pulls registered program definitions from programs.json, merged with any distinct codes in users.json.
    """
    progs = load_programs()
    seen_codes = set()
    programs = []

    for p in progs:
        c = str(p.get("code") or "").strip().upper()
        n = str(p.get("name") or "").strip()
        if c and c not in seen_codes:
            seen_codes.add(c)
            programs.append({
                "code": c,
                "name": n or c,
                "label": f"{n} ({c})" if n else c
            })

    users = load_users()
    for u, rec in users.items():
        if isinstance(rec, dict):
            c = str(rec.get("program_code") or "").strip().upper()
            if c and c not in seen_codes:
                seen_codes.add(c)
                n = str(rec.get("program_name") or get_program_name(c)).strip()
                programs.append({
                    "code": c,
                    "name": n or c,
                    "label": f"{n} ({c})" if n else c
                })

    programs.sort(key=lambda x: x["name"])
    return programs


def get_available_admission_years() -> List[int]:
    """
    Returns sorted list of available admission years derived from student records
    and default nearby academic batches.
    """
    from datetime import datetime
    curr = datetime.now().year
    years = {curr - 3, curr - 2, curr - 1, curr, curr + 1}
    users = load_users()
    for u, rec in users.items():
        if isinstance(rec, dict) and rec.get("admission_year"):
            try:
                years.add(int(rec["admission_year"]))
            except Exception:
                pass
    return sorted(list(years), reverse=True)


def get_academic_years() -> List[str]:
    """Returns standard academic years."""
    return ["1st Year", "2nd Year", "3rd Year", "4th Year"]


def get_all_students_for_eligibility() -> List[Dict[str, Any]]:
    """
    Returns list of university student profiles for eligibility checking and specific student targeting.
    Filters out administrator accounts and external/practice accounts.
    """
    users = load_users()
    students = []
    for u, rec in users.items():
        if not isinstance(rec, dict):
            continue
        # Exclude administrative accounts
        if u.lower() in ("admin", "adminc") or rec.get("is_admin"):
            continue
        # Only university students participate in course exams
        if rec.get("user_type") != "UNIVERSITY":
            continue

        sc = str(rec.get("student_code") or "").strip()
        p_code = str(rec.get("program_code") or "").strip().upper()
        p_name = str(rec.get("program_name") or get_program_name(p_code)).strip()
        adm_yr = rec.get("admission_year") or ""
        acad_yr = rec.get("academic_year") or calculate_academic_year(adm_yr)
        email = str(rec.get("email") or "").strip()

        disp_name = str(rec.get("name") or rec.get("username") or u)
        user_id = str(rec.get("id") or u)

        students.append({
            "id": user_id,
            "username": disp_name,
            "name": disp_name,
            "email": email,
            "user_type": "UNIVERSITY",
            "student_code": sc,
            "program_code": p_code,
            "program_name": p_name,
            "admission_year": adm_yr,
            "academic_year": acad_yr,
            "roll_number": str(rec.get("roll_number") or "").strip(),
            "display_text": f"{sc} — {disp_name} ({p_name})" if sc else f"{disp_name} ({email})"
        })

    # Sort by program, admission year, roll number
    students.sort(key=lambda s: (s["program_code"], str(s["admission_year"]), s["student_code"], s["username"]))
    return students


def count_eligible_students(program_code: str, admission_year: Any, academic_year: str) -> int:
    """
    Counts how many registered students match the specified:
      - program_code
      - admission_year
      - academic_year
    """
    students = get_all_students_for_eligibility()
    p_target = str(program_code or "").strip().upper()
    adm_target = str(admission_year or "").strip()
    acad_target = str(academic_year or "").strip().lower()

    count = 0
    for s in students:
        s_p = str(s.get("program_code") or "").strip().upper()
        s_adm = str(s.get("admission_year") or "").strip()
        s_acad = str(s.get("academic_year") or "").strip().lower()

        if s_p and s_p == p_target and s_adm == adm_target and s_acad == acad_target:
            count += 1
    return count


def get_student_identity_from_session_or_db(session_obj) -> Dict[str, Any]:
    """
    Securely resolves the authenticated student's academic identity from session or users.json.
    Never trusts client parameters; guarantees that session holds valid student academic data.
    """
    user_key = session_obj.get("student_id") or session_obj.get("user_id") or session_obj.get("username") or ""
    users = load_users()
    rec = users.get(user_key, {})
    if not rec:
        s_email = str(session_obj.get("email") or "").strip().lower()
        if s_email:
            for k, udata in users.items():
                if str(udata.get("email") or "").strip().lower() == s_email:
                    rec = udata
                    user_key = k
                    break

    display_name = rec.get("username") or rec.get("name") or session_obj.get("username") or user_key
    user_id = str(rec.get("id") or user_key)
    user_type = rec.get("user_type") or session_obj.get("user_type") or "EXTERNAL"
    sc = rec.get("student_code") or session_obj.get("student_code") or ""
    p_code = rec.get("program_code") or session_obj.get("program_code") or ""
    p_name = rec.get("program_name") or get_program_name(p_code) or session_obj.get("program_name") or ""
    adm_yr = rec.get("admission_year") or session_obj.get("admission_year") or ""
    acad_yr = rec.get("academic_year") or calculate_academic_year(adm_yr) or session_obj.get("academic_year") or ""
    email = rec.get("email") or session_obj.get("email", "")

    # Always keep session synchronized with authoritative DB record
    if user_key:
        session_obj["username"] = display_name
        session_obj["name"] = display_name
        session_obj["student_id"] = user_id
        session_obj["user_id"] = user_id
        session_obj["user_type"] = user_type
        session_obj["email"] = email
        session_obj["student_code"] = sc
        session_obj["program_code"] = p_code
        session_obj["program_name"] = p_name
        session_obj["admission_year"] = adm_yr
        session_obj["academic_year"] = acad_yr

    return {
        "id": user_id,
        "username": display_name,
        "name": display_name,
        "email": email,
        "user_type": user_type,
        "student_code": sc,
        "program_code": p_code,
        "program_name": p_name,
        "admission_year": adm_yr,
        "academic_year": acad_yr
    }


def is_student_eligible_for_exam(student_info: Dict[str, Any], exam: Dict[str, Any]) -> bool:
    """
    Determines if a student is authorized to view and attempt a specific course examination.
    Enforces target_mode:
      - 'SPECIFIC_STUDENTS': student_code or username must be in exam['student_codes']
      - 'PROGRAM_BATCH_YEAR': student must match program_code, admission_year, and academic_year (or ALL)
      - 'ALL_STUDENTS': available to all registered university students
    Unconfigured legacy exams (without target fields) return False to prevent unauthorized cross-program visibility.
    """
    if not student_info:
        return False

    # External practice students are NEVER eligible for official course exams
    if student_info.get("user_type") != "UNIVERSITY":
        return False

    target_mode = (exam.get("target_mode") or "").strip().upper()
    exam_prog = str(exam.get("program_code") or "").strip().upper()
    exam_adm = str(exam.get("admission_year") or "").strip()
    exam_acad = str(exam.get("academic_year") or "").strip().lower()

    # 1. Specific Students Mode
    if target_mode == "SPECIFIC_STUDENTS":
        target_codes = [str(c).strip().upper() for c in exam.get("student_codes", [])]
        s_code = str(student_info.get("student_code") or "").strip().upper()
        s_user = str(student_info.get("username") or "").strip().upper()
        s_id = str(student_info.get("id") or "").strip().upper()
        return bool((s_code and s_code in target_codes) or (s_user and s_user in target_codes) or (s_id and s_id in target_codes))

    if target_mode == "ALL_STUDENTS":
        return True

    # 2. Program + Batch + Year Mode (Default)
    if exam_prog or exam_adm or exam_acad:
        s_prog = str(student_info.get("program_code") or "").strip().upper()
        s_adm = str(student_info.get("admission_year") or "").strip()
        s_acad = str(student_info.get("academic_year") or "").strip().lower()

        match_prog = (not exam_prog or exam_prog == "ALL" or (s_prog and s_prog == exam_prog))
        match_adm = (not exam_adm or exam_adm == "ALL" or (s_adm and s_adm == exam_adm))
        match_acad = (not exam_acad or exam_acad in ("all", "all years") or (s_acad and s_acad == exam_acad))

        return bool(match_prog and match_adm and match_acad)

    # 3. Unconfigured / Legacy Course Exam -> False (Must be configured by admin before visible)
    if target_mode == "PROGRAM_BATCH_YEAR":
        return False

    return False


def get_student_exam_result(username: str, exam: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Returns the most recent completed submission record for the given student and exam,
    matching either by course_exam_id or exam_title.
    Checks under username, student_id, or email for backward and forward compatibility.
    """
    if not username or not exam:
        return None
    results = load_results()
    user_data = results.get(username)
    if not user_data:
        users = load_users()
        for k, udata in users.items():
            if k == username or str(udata.get("id")) == username or str(udata.get("username")).lower() == username.lower() or str(udata.get("email")).lower() == username.lower():
                user_data = results.get(k) or results.get(str(udata.get("id"))) or results.get(str(udata.get("username")))
                if user_data:
                    break
    if not user_data or not isinstance(user_data, dict):
        return None

    history = user_data.get("history", []) if isinstance(user_data, dict) else []
    exam_id = str(exam.get("id") or "").strip()
    exam_title = str(exam.get("title") or "").strip().lower()

    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("course_exam_id") or "").strip()
        entry_title = str(entry.get("exam_title") or "").strip().lower()

        if exam_id and entry_id and entry_id == exam_id:
            return entry
        if exam_title and entry_title and entry_title == exam_title:
            return entry
    return None




