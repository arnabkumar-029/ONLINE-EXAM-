# utils.py
import os
import json
import re
import time
import uuid
from typing import List, Dict, Any, Optional
from db import is_database_configured, get_db_session
from models import (
    Program,
    User,
    Question,
    CourseExam,
    CourseExamQuestion,
    CourseExamTargetedStudent,
    ExamResult,
)
from sqlalchemy import func
from sqlalchemy.orm import selectinload

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
    """Loads program definitions from PostgreSQL (if configured) or programs.json."""
    if is_database_configured():
        with get_db_session() as session:
            progs = session.query(Program).order_by(Program.id.asc()).all()
            return [p.to_dict() for p in progs]

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
    """Saves program definitions to PostgreSQL (if configured) or programs.json."""
    if is_database_configured():
        with get_db_session() as session:
            existing = {p.code.upper(): p for p in session.query(Program).all()}
            for item in programs:
                c = str(item.get("code") or "").strip().upper()
                n = str(item.get("name") or "").strip()
                if not c or not n:
                    continue
                if c in existing:
                    existing[c].name = n
                else:
                    new_prog = Program(code=c, name=n)
                    session.add(new_prog)
                    existing[c] = new_prog
            session.commit()
        return

    with open(PROGRAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(programs, f, indent=2, ensure_ascii=False)

def get_program_by_code(code: str) -> Optional[Dict[str, str]]:
    """Finds program definition by code (case-insensitive)."""
    if not code:
        return None
    c = str(code).strip().upper()
    if is_database_configured():
        with get_db_session() as session:
            prog = session.query(Program).filter(func.upper(Program.code) == c).first()
            return prog.to_dict() if prog else None

    for p in load_programs():
        if str(p.get("code") or "").strip().upper() == c:
            return p
    return None

def get_program_by_name(name: str) -> Optional[Dict[str, str]]:
    """Finds program definition by name (case-insensitive)."""
    if not name:
        return None
    n = str(name).strip().lower()
    if is_database_configured():
        with get_db_session() as session:
            prog = session.query(Program).filter(func.lower(Program.name) == n).first()
            return prog.to_dict() if prog else None

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
    if is_database_configured():
        with get_db_session() as session:
            query = session.query(User).filter(func.upper(User.student_code) == target)
            if exclude_id:
                query = query.filter(User.id != str(exclude_id))
            return query.first() is not None

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
    if is_database_configured():
        with get_db_session() as session:
            query = session.query(User).filter(func.lower(User.email) == target)
            if exclude_id:
                query = query.filter(User.id != str(exclude_id))
            return query.first() is not None

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
    """
    Saves JSON data. If database is configured and file corresponds to a database table,
    writes to PostgreSQL without modifying pristine JSON files on disk.
    """
    if is_database_configured():
        basename = os.path.basename(file)
        if basename == QUESTIONS_FILE or basename == "questions.json":
            if isinstance(data, list):
                with get_db_session() as session:
                    existing_qs = {q.id: q for q in session.query(Question).all()}
                    seen_ids = set()
                    for raw in data:
                        fixed = _migrate_one_question(raw)
                        if not fixed:
                            continue
                        qid = fixed["id"]
                        seen_ids.add(qid)
                        if qid in existing_qs:
                            q = existing_qs[qid]
                            q.course_code = fixed["course_code"]
                            q.course_name = fixed["course_name"]
                            q.subject = fixed["subject"]
                            q.program_code = fixed.get("program_code") or "ALL"
                            q.program_name = fixed.get("program_name") or ""
                            q.admission_year = str(fixed.get("admission_year") or "ALL")
                            q.academic_year = str(fixed.get("academic_year") or "ALL")
                            q.unit = fixed.get("unit") or ""
                            q.topic = fixed.get("topic") or ""
                            q.type = fixed.get("type", "MCQ")
                            q.level = fixed.get("level", "Easy")
                            q.question_text = fixed.get("question") or fixed.get("q") or ""
                            q.options = fixed.get("options") if fixed.get("type") == "MCQ" else None
                            q.correct = fixed.get("correct") if fixed.get("type") == "MCQ" else None
                            q.answer_key = fixed.get("answer_key") if fixed.get("type") == "DESCRIPTIVE" else None
                            q.max_marks = float(fixed.get("max_marks", 5.0))
                            q.source = fixed.get("source", "MANUAL")
                        else:
                            new_q = Question(
                                id=qid,
                                course_code=fixed["course_code"],
                                course_name=fixed["course_name"],
                                subject=fixed["subject"],
                                program_code=fixed.get("program_code") or "ALL",
                                program_name=fixed.get("program_name") or "",
                                admission_year=str(fixed.get("admission_year") or "ALL"),
                                academic_year=str(fixed.get("academic_year") or "ALL"),
                                unit=fixed.get("unit") or "",
                                topic=fixed.get("topic") or "",
                                type=fixed.get("type", "MCQ"),
                                level=fixed.get("level", "Easy"),
                                question_text=fixed.get("question") or fixed.get("q") or "",
                                options=fixed.get("options") if fixed.get("type") == "MCQ" else None,
                                correct=fixed.get("correct") if fixed.get("type") == "MCQ" else None,
                                answer_key=fixed.get("answer_key") if fixed.get("type") == "DESCRIPTIVE" else None,
                                max_marks=float(fixed.get("max_marks", 5.0)),
                                source=fixed.get("source", "MANUAL")
                            )
                            session.add(new_q)
                            existing_qs[qid] = new_q

                    to_delete = [qid for qid in existing_qs if qid not in seen_ids]
                    if to_delete:
                        session.query(CourseExamQuestion).filter(CourseExamQuestion.question_id.in_(to_delete)).delete(synchronize_session=False)
                        session.query(Question).filter(Question.id.in_(to_delete)).delete(synchronize_session=False)

                    session.commit()
                global _QUESTIONS_CACHE, _QUESTIONS_CACHE_ATIME
                _QUESTIONS_CACHE = None
                _QUESTIONS_CACHE_ATIME = time.time()
            return
        elif basename == USERS_FILE or basename == "users.json":
            save_users(data)
            return
        elif basename == COURSE_EXAMS_FILE or basename == "course_exams.json":
            save_course_exams(data)
            return
        elif basename == RESULTS_FILE or basename == "results.json":
            save_results(data)
            return
        elif basename == "programs.json":
            save_programs(data)
            return

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Refresh cached questions whenever questions.json is updated
    if file == QUESTIONS_FILE or file == "questions.json":
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
        if sc and ("university_code" not in rec or "program_code" not in rec):
            parsed = parse_student_code(sc)
            if parsed:
                for k, v in parsed.items():
                    if k != "academic_year" and (k not in rec or not rec[k]):
                        rec[k] = v
        if rec.get("program_code") and not rec.get("program_name"):
            rec["program_name"] = get_program_name(rec["program_code"])

    return rec

def load_users() -> Dict[str, Dict[str, Any]]:
    if is_database_configured():
        with get_db_session() as session:
            users = session.query(User).all()
            return {u.id: u.to_dict() for u in users}

    raw = load_json(USERS_FILE)
    if not isinstance(raw, dict):
        return {}
    normalized = {}
    for u, data in raw.items():
        normalized[u] = normalize_user_record(u, data)
    return normalized

def save_users(users: Dict[str, Dict[str, Any]]):
    """Saves user records to PostgreSQL (if configured) or users.json."""
    if is_database_configured():
        with get_db_session() as session:
            existing = {u.id: u for u in session.query(User).all()}
            for k, udata in users.items():
                if not isinstance(udata, dict):
                    continue
                uid = str(udata.get("id") or k)
                username = str(udata.get("username") or udata.get("name") or uid).strip()
                name = str(udata.get("name") or username).strip()
                email = str(udata.get("email") or f"{uid.lower()}@examforge.local").strip().lower()
                pw_h = str(udata.get("pw_hash") or udata.get("password") or "")
                utype = str(udata.get("user_type") or "EXTERNAL").strip().upper()
                scode = str(udata.get("student_code") or "").strip().upper() or None
                ucode = str(udata.get("university_code") or "").strip().upper() or None
                pcode = str(udata.get("program_code") or "").strip().upper() or None
                pname = udata.get("program_name") or (get_program_name(pcode) if pcode else None)
                dname = str(udata.get("department_name") or "").strip() or None
                adm_yr = udata.get("admission_year")
                adm_yr_int = int(adm_yr) if adm_yr not in (None, "") and str(adm_yr).isdigit() else None
                acad_yr = str(udata.get("academic_year") or "").strip() or None
                roll = str(udata.get("roll_number") or "").strip() or None
                is_admin = bool(udata.get("is_admin", False))

                if pcode:
                    if not session.query(Program).filter(func.upper(Program.code) == pcode).first():
                        session.add(Program(code=pcode, name=pname or pcode))
                        session.flush()

                if uid in existing:
                    u = existing[uid]
                    u.username = username
                    u.name = name
                    u.email = email
                    u.pw_hash = pw_h
                    u.user_type = utype
                    u.student_code = scode
                    u.university_code = ucode
                    u.program_code = pcode
                    u.program_name = pname
                    u.department_name = dname
                    u.admission_year = adm_yr_int
                    u.academic_year = acad_yr
                    u.roll_number = roll
                    u.is_admin = is_admin
                else:
                    u = User(
                        id=uid,
                        username=username,
                        name=name,
                        email=email,
                        pw_hash=pw_h,
                        user_type=utype,
                        student_code=scode,
                        university_code=ucode,
                        program_code=pcode,
                        program_name=pname,
                        department_name=dname,
                        admission_year=adm_yr_int,
                        academic_year=acad_yr,
                        roll_number=roll,
                        is_admin=is_admin
                    )
                    session.add(u)
                    existing[uid] = u
            session.commit()
        return

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def load_results():
    if is_database_configured():
        with get_db_session() as session:
            all_results = session.query(ExamResult).order_by(ExamResult.id.asc()).all()
            grouped = {}
            for r in all_results:
                key = r.user_key or r.user_id
                if key not in grouped:
                    grouped[key] = {"history": []}
                grouped[key]["history"].append(r.to_history_dict())
            return grouped

    return load_json(RESULTS_FILE)

def save_results(results: Dict[str, Any]):
    """Saves results dictionary to PostgreSQL (if configured) or results.json."""
    if is_database_configured():
        for ukey, udata in results.items():
            if isinstance(udata, dict) and "history" in udata:
                for entry in udata["history"]:
                    create_exam_result_db({**entry, "user_key": ukey, "user_id": ukey})
        return

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def find_user_by_email(email: str):
    """Returns (username, user_record) matching the given email (case-insensitive), or None."""
    if not email:
        return None
    target = email.strip().lower()
    if is_database_configured():
        with get_db_session() as session:
            user = session.query(User).filter(func.lower(User.email) == target).first()
            if user:
                return user.id, user.to_dict()
            return None

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

    if is_database_configured():
        with get_db_session() as session:
            user = session.query(User).filter(
                func.lower(User.email) == target_email,
                func.upper(User.student_code) == target_code,
                User.user_type == "UNIVERSITY"
            ).first()
            if user and user.pw_hash and check_password_hash(user.pw_hash, password):
                return user.id, user.to_dict()
            return None

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
    Public API: returns questions list.
    From PostgreSQL (ordered by created_at DESC, id DESC) if configured,
    or cached/migrated list from questions.json if offline.
    """
    if is_database_configured():
        with get_db_session() as session:
            qs = session.query(Question).order_by(
                Question.created_at.desc(),
                Question.id.desc()
            ).all()
            return [q.to_dict() for q in qs]

    global _QUESTIONS_CACHE
    if _QUESTIONS_CACHE is not None:
        return _QUESTIONS_CACHE
    return _load_questions_from_disk()

def reload_questions_from_disk():
    """
    Force reload of questions from disk or database and update cache.
    """
    if is_database_configured():
        return load_questions()
    return _load_questions_from_disk()

# =========================================================
#  Course Exam Management Helpers
# =========================================================
from datetime import datetime

def load_course_exams() -> List[Dict[str, Any]]:
    """Load all configured course examinations from PostgreSQL (if configured) or course_exams.json."""
    if is_database_configured():
        with get_db_session() as session:
            exams = session.query(CourseExam).options(
                selectinload(CourseExam.question_associations),
                selectinload(CourseExam.targeted_students)
            ).order_by(CourseExam.created_at.desc(), CourseExam.id.asc()).all()
            return [e.to_dict() for e in exams]

    data = load_json(COURSE_EXAMS_FILE)
    if isinstance(data, list):
        return data
    return []

def save_course_exams(exams: List[Dict[str, Any]]):
    """Save course examinations list to PostgreSQL (if configured) or course_exams.json."""
    if is_database_configured():
        for e in exams:
            eid = str(e.get("id") or "")
            if eid and get_course_exam_by_id(eid):
                update_course_exam_db(eid, e)
            else:
                create_course_exam_db(e)
        return

    with open(COURSE_EXAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(exams, f, indent=2, ensure_ascii=False)

def get_course_exam_by_id(exam_id: str) -> Dict[str, Any] | None:
    """Retrieve a single course exam by unique ID."""
    if not exam_id:
        return None
    eid = str(exam_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            exam = session.query(CourseExam).options(
                selectinload(CourseExam.question_associations),
                selectinload(CourseExam.targeted_students)
            ).filter(CourseExam.id == eid).first()
            return exam.to_dict() if exam else None

    for exam in load_course_exams():
        if str(exam.get("id")) == eid:
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


def group_questions_by_course_subject(questions: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Groups questions into separate Course/Subject collections.
    Uses question metadata (subject, course_name, course_code) to determine the group name.
    Falls back to 'UNASSIGNED' if no classification is available.
    Preserves question integrity, prevents duplication across boxes, and ensures legacy questions do not crash.
    """
    from collections import OrderedDict
    groups = OrderedDict()
    for q in questions:
        subj = str(q.get("subject") or "").strip()
        cname = str(q.get("course_name") or "").strip()
        code = str(q.get("course_code") or "").strip().upper()

        if subj and subj.lower() not in ["general", "none", "n/a", "unassigned"]:
            group_name = subj
        elif cname and cname.lower() not in ["general", "none", "n/a", "unassigned"]:
            group_name = cname
        elif subj:
            group_name = subj
        elif code:
            group_name = code
        else:
            group_name = "UNASSIGNED"

        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(q)
    return groups


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
    return ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "6th Year", "7th Year"]


def get_all_students_for_eligibility() -> List[Dict[str, Any]]:
    """
    Returns list of university student profiles for eligibility checking and specific student targeting.
    Filters out administrator accounts and external/practice accounts.
    """
    if is_database_configured():
        with get_db_session() as session:
            users = session.query(User).filter(
                User.user_type == "UNIVERSITY",
                User.is_admin == False,
                func.lower(User.id).notin_(["admin", "adminc"])
            ).all()
            students = []
            for u in users:
                sc = (u.student_code or "").strip()
                p_code = (u.program_code or "").strip().upper()
                p_name = (u.program_name or get_program_name(p_code)).strip()
                adm_yr = u.admission_year or ""
                acad_yr = u.academic_year or calculate_academic_year(adm_yr)
                email = (u.email or "").strip()
                disp_name = str(u.name or u.username or u.id)
                user_id = str(u.id)

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
                    "roll_number": str(u.roll_number or "").strip(),
                    "display_text": f"{sc} — {disp_name} ({p_name})" if sc else f"{disp_name} ({email})"
                })

            students.sort(key=lambda s: (s["program_code"], str(s["admission_year"]), s["student_code"], s["username"]))
            return students

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
    Securely resolves the authenticated student's academic identity from session or users table / users.json.
    Never trusts client parameters; guarantees that session holds valid student academic data.
    """
    user_key = session_obj.get("student_id") or session_obj.get("user_id") or session_obj.get("username") or ""
    s_email = str(session_obj.get("email") or "").strip().lower()

    if is_database_configured():
        rec = None
        with get_db_session() as session:
            user = None
            if user_key:
                user = session.query(User).filter(
                    (User.id == str(user_key)) |
                    (func.lower(User.username) == str(user_key).lower())
                ).first()
            if not user and s_email:
                user = session.query(User).filter(func.lower(User.email) == s_email).first()

            if user:
                rec = user.to_dict()

        if not rec:
            rec = {}

        display_name = rec.get("username") or rec.get("name") or session_obj.get("username") or user_key
        user_id = str(rec.get("id") or user_key)
        user_type = rec.get("user_type") or session_obj.get("user_type") or "EXTERNAL"
        sc = rec.get("student_code") or session_obj.get("student_code") or ""
        p_code = rec.get("program_code") or session_obj.get("program_code") or ""
        p_name = rec.get("program_name") or get_program_name(p_code) or session_obj.get("program_name") or ""
        dept_name = rec.get("department_name") or session_obj.get("department_name") or ""
        adm_yr = rec.get("admission_year") or session_obj.get("admission_year") or ""
        acad_yr = rec.get("academic_year") or calculate_academic_year(adm_yr) or session_obj.get("academic_year") or ""
        roll = rec.get("roll_number") or session_obj.get("roll_number") or ""
        email = rec.get("email") or session_obj.get("email", "")
        is_admin_flag = bool(rec.get("is_admin", False))

        if user_key or user_id:
            session_obj["username"] = display_name
            session_obj["name"] = display_name
            session_obj["student_id"] = user_id
            session_obj["user_id"] = user_id
            session_obj["user_type"] = user_type
            session_obj["email"] = email
            session_obj["student_code"] = sc
            session_obj["program_code"] = p_code
            session_obj["program_name"] = p_name
            session_obj["department_name"] = dept_name
            session_obj["admission_year"] = adm_yr
            session_obj["academic_year"] = acad_yr
            session_obj["roll_number"] = roll
            session_obj["is_admin"] = is_admin_flag

        return {
            "id": user_id,
            "username": display_name,
            "name": display_name,
            "email": email,
            "user_type": user_type,
            "student_code": sc,
            "program_code": p_code,
            "program_name": p_name,
            "department_name": dept_name,
            "admission_year": adm_yr,
            "academic_year": acad_yr,
            "roll_number": roll,
            "is_admin": is_admin_flag
        }

    users = load_users()
    rec = users.get(user_key, {})
    if not rec:
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
    dept_name = rec.get("department_name") or session_obj.get("department_name") or ""
    adm_yr = rec.get("admission_year") or session_obj.get("admission_year") or ""
    acad_yr = rec.get("academic_year") or calculate_academic_year(adm_yr) or session_obj.get("academic_year") or ""
    roll = rec.get("roll_number") or session_obj.get("roll_number") or ""
    email = rec.get("email") or session_obj.get("email", "")
    is_admin_flag = bool(rec.get("is_admin", False))

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
        session_obj["department_name"] = dept_name
        session_obj["admission_year"] = adm_yr
        session_obj["academic_year"] = acad_yr
        session_obj["roll_number"] = roll
        session_obj["is_admin"] = is_admin_flag

    return {
        "id": user_id,
        "username": display_name,
        "name": display_name,
        "email": email,
        "user_type": user_type,
        "student_code": sc,
        "program_code": p_code,
        "program_name": p_name,
        "department_name": dept_name,
        "admission_year": adm_yr,
        "academic_year": acad_yr,
        "roll_number": roll,
        "is_admin": is_admin_flag
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

    if is_database_configured():
        exam_id = str(exam.get("id") or "").strip()
        exam_title = str(exam.get("title") or "").strip()

        with get_db_session() as session:
            u_target = str(username).strip()
            user = session.query(User).filter(
                (User.id == u_target) |
                (func.lower(User.username) == u_target.lower()) |
                (func.lower(User.email) == u_target.lower())
            ).first()

            possible_user_ids = {u_target}
            if user:
                possible_user_ids.add(user.id)
                if user.username:
                    possible_user_ids.add(user.username)

            query = session.query(ExamResult).filter(
                (ExamResult.user_id.in_(list(possible_user_ids))) |
                (ExamResult.user_key.in_(list(possible_user_ids))) |
                (func.lower(ExamResult.user_key) == u_target.lower())
            )

            if exam_id and exam_title:
                query = query.filter(
                    (ExamResult.course_exam_id == exam_id) |
                    (func.lower(ExamResult.exam_title) == exam_title.lower())
                )
            elif exam_id:
                query = query.filter(ExamResult.course_exam_id == exam_id)
            elif exam_title:
                query = query.filter(func.lower(ExamResult.exam_title) == exam_title.lower())
            else:
                return None

            res = query.order_by(
                ExamResult.submitted_at.desc().nullslast(),
                ExamResult.id.desc()
            ).first()

            return res.to_history_dict() if res else None

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


# ==============================================================
#  POSTGRESQL WRITE ADAPTER LAYER (TASK 8B)
# ==============================================================

def create_user_db(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new user account in PostgreSQL (if configured) or users.json.
    Enforces uniqueness of email and student_code.
    """
    uid = str(user_data.get("id") or f"user_{uuid.uuid4().hex[:10]}")
    username = str(user_data.get("username") or user_data.get("name") or uid).strip()
    name = str(user_data.get("name") or username).strip()
    email = str(user_data.get("email") or "").strip().lower()
    pw_h = str(user_data.get("pw_hash") or user_data.get("password") or "")
    user_type = str(user_data.get("user_type") or "EXTERNAL").strip().upper()

    student_code = str(user_data.get("student_code") or "").strip().upper() or None
    univ_code = str(user_data.get("university_code") or "").strip().upper() or None
    prog_code = str(user_data.get("program_code") or "").strip().upper() or None
    prog_name = user_data.get("program_name") or (get_program_name(prog_code) if prog_code else None)
    dept_name = str(user_data.get("department_name") or "").strip() or None

    adm_yr = user_data.get("admission_year")
    admission_year = int(adm_yr) if adm_yr not in (None, "") and str(adm_yr).isdigit() else None
    academic_year = str(user_data.get("academic_year") or "").strip() or None
    roll_number = str(user_data.get("roll_number") or "").strip() or None
    is_admin = bool(user_data.get("is_admin", False))

    if is_database_configured():
        with get_db_session() as session:
            if email:
                existing_email = session.query(User).filter(func.lower(User.email) == email).first()
                if existing_email:
                    raise ValueError("Email already exists.")

            if student_code:
                existing_sc = session.query(User).filter(func.upper(User.student_code) == student_code).first()
                if existing_sc:
                    raise ValueError("Student Code already exists.")

            if prog_code:
                existing_p = session.query(Program).filter(func.upper(Program.code) == prog_code).first()
                if not existing_p:
                    session.add(Program(code=prog_code, name=prog_name or prog_code))
                    session.flush()

            user = User(
                id=uid,
                username=username,
                name=name,
                email=email,
                pw_hash=pw_h,
                user_type=user_type,
                student_code=student_code,
                university_code=univ_code,
                program_code=prog_code,
                program_name=prog_name,
                department_name=dept_name,
                admission_year=admission_year,
                academic_year=academic_year,
                roll_number=roll_number,
                is_admin=is_admin
            )
            session.add(user)
            session.commit()
            return user.to_dict()

    users = load_users()
    rec = normalize_user_record(uid, user_data)
    users[uid] = rec
    save_users(users)
    return rec


def update_user_db(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates an existing user in PostgreSQL (if configured) or users.json.
    """
    target = str(user_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            user = session.query(User).filter(
                (User.id == target) |
                (func.lower(User.username) == target.lower()) |
                (func.lower(User.email) == target.lower())
            ).first()
            if not user:
                return None

            if "email" in updates:
                new_email = str(updates["email"]).strip().lower()
                if new_email and new_email != (user.email or "").lower():
                    dup = session.query(User).filter(func.lower(User.email) == new_email, User.id != user.id).first()
                    if dup:
                        raise ValueError("Email already exists.")
                    user.email = new_email

            if "student_code" in updates:
                new_sc = str(updates["student_code"] or "").strip().upper() or None
                if new_sc and new_sc != (user.student_code or "").upper():
                    dup = session.query(User).filter(func.upper(User.student_code) == new_sc, User.id != user.id).first()
                    if dup:
                        raise ValueError("Student Code already exists.")
                    user.student_code = new_sc
                elif updates["student_code"] is None:
                    user.student_code = None

            if "name" in updates or "username" in updates:
                name_val = str(updates.get("name") or updates.get("username") or user.name).strip()
                user.name = name_val
                user.username = name_val

            if "pw_hash" in updates or "password" in updates:
                pw_val = str(updates.get("pw_hash") or updates.get("password") or user.pw_hash)
                user.pw_hash = pw_val

            if "user_type" in updates:
                user.user_type = str(updates["user_type"]).strip().upper()

            if "university_code" in updates:
                user.university_code = str(updates["university_code"] or "").strip().upper() or None

            if "program_code" in updates:
                p_c = str(updates["program_code"] or "").strip().upper() or None
                if p_c:
                    existing_p = session.query(Program).filter(func.upper(Program.code) == p_c).first()
                    if not existing_p:
                        session.add(Program(code=p_c, name=updates.get("program_name") or get_program_name(p_c)))
                        session.flush()
                user.program_code = p_c
                if p_c and "program_name" not in updates:
                    user.program_name = get_program_name(p_c)

            if "program_name" in updates:
                user.program_name = updates["program_name"]

            if "department_name" in updates:
                user.department_name = str(updates["department_name"] or "").strip() or None

            if "admission_year" in updates:
                adm_yr = updates["admission_year"]
                user.admission_year = int(adm_yr) if adm_yr not in (None, "") and str(adm_yr).isdigit() else None

            if "academic_year" in updates:
                user.academic_year = str(updates["academic_year"] or "").strip() or None

            if "roll_number" in updates:
                user.roll_number = str(updates["roll_number"] or "").strip() or None

            if "is_admin" in updates:
                user.is_admin = bool(updates["is_admin"])

            session.commit()
            return user.to_dict()

    users = load_users()
    target_key = None
    for k, v in users.items():
        if k == user_id or str(v.get("id")) == user_id or str(v.get("username")).lower() == user_id.lower():
            target_key = k
            break
    if not target_key:
        return None
    users[target_key].update(updates)
    save_users(users)
    return users[target_key]


def delete_user_db(user_id: str) -> bool:
    """
    Deletes user by ID in PostgreSQL (if configured) or users.json.
    """
    target = str(user_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            user = session.query(User).filter(
                (User.id == target) |
                (func.lower(User.username) == target.lower()) |
                (func.lower(User.email) == target.lower()) |
                (func.upper(User.student_code) == target.upper())
            ).first()
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    users = load_users()
    target_key = None
    for k, v in users.items():
        if k == user_id or str(v.get("id")) == user_id or str(v.get("username")).lower() == user_id.lower() or str(v.get("email")).lower() == user_id.lower():
            target_key = k
            break
    if target_key:
        del users[target_key]
        save_users(users)
        return True
    return False


def create_program_db(code: str, name: str) -> Dict[str, str]:
    """
    Creates an academic program in PostgreSQL (if configured) or programs.json.
    """
    c = str(code).strip().upper()
    n = str(name).strip()
    if not c or not n:
        raise ValueError("Program code and name are required.")

    if is_database_configured():
        with get_db_session() as session:
            if session.query(Program).filter(func.upper(Program.code) == c).first():
                raise ValueError("Program Code already exists.")
            if session.query(Program).filter(func.lower(Program.name) == n.lower()).first():
                raise ValueError("Program Name already exists.")
            prog = Program(code=c, name=n)
            session.add(prog)
            session.commit()
            return prog.to_dict()

    programs = load_programs()
    for p in programs:
        if str(p.get("code") or "").strip().upper() == c:
            raise ValueError("Program Code already exists.")
        if str(p.get("name") or "").strip().lower() == n.lower():
            raise ValueError("Program Name already exists.")
    programs.append({"name": n, "code": c})
    save_programs(programs)
    return {"name": n, "code": c}


def update_program_db(old_code: str, new_code: str, new_name: str, update_students: bool = False) -> Dict[str, Any]:
    """
    Updates an academic program in PostgreSQL (if configured) or programs.json.
    """
    old_c = str(old_code).strip().upper()
    new_c = str(new_code).strip().upper()
    n = str(new_name).strip()
    if not old_c or not new_c or not n:
        raise ValueError("Original code, new code, and new name are required.")

    if is_database_configured():
        with get_db_session() as session:
            prog = session.query(Program).filter(func.upper(Program.code) == old_c).first()
            if not prog:
                raise ValueError(f"Program with code '{old_c}' not found.")

            if new_c != old_c:
                dup = session.query(Program).filter(func.upper(Program.code) == new_c, Program.id != prog.id).first()
                if dup:
                    raise ValueError("Program Code already exists.")

            dup_n = session.query(Program).filter(func.lower(Program.name) == n.lower(), Program.id != prog.id).first()
            if dup_n:
                raise ValueError("Program Name already exists.")

            student_count = session.query(User).filter(func.upper(User.program_code) == old_c).count()
            if new_c != old_c and student_count > 0:
                if not update_students:
                    raise ValueError(f"Warning: {student_count} student(s) currently use '{old_c}'. Controlled update confirmation required.")
                students = session.query(User).filter(func.upper(User.program_code) == old_c).all()
                for s in students:
                    s.program_code = new_c
                    s.program_name = n
                    adm_yr = str(s.admission_year or "24")[-2:]
                    roll = str(s.roll_number or "001")
                    univ = str(s.university_code or "BWU")
                    s.student_code = f"{univ}/{new_c}/{adm_yr}/{roll}"

            prog.code = new_c
            prog.name = n
            session.commit()
            return {
                "program": prog.to_dict(),
                "students_updated": student_count if (new_c != old_c and update_students) else 0
            }

    programs = load_programs()
    prog_idx = -1
    for i, p in enumerate(programs):
        if str(p.get("code") or "").strip().upper() == old_c:
            prog_idx = i
            break
    if prog_idx == -1:
        raise ValueError(f"Program with code '{old_c}' not found.")

    if new_c != old_c:
        for i, p in enumerate(programs):
            if i != prog_idx and str(p.get("code") or "").strip().upper() == new_c:
                raise ValueError("Program Code already exists.")
    for i, p in enumerate(programs):
        if i != prog_idx and str(p.get("name") or "").strip().lower() == n.lower():
            raise ValueError("Program Name already exists.")

    student_count = count_students_in_program(old_c)
    if new_c != old_c and student_count > 0:
        if not update_students:
            raise ValueError(f"Warning: {student_count} student(s) currently use '{old_c}'.")
        users = load_users()
        for u, rec in users.items():
            if isinstance(rec, dict) and rec.get("user_type") == "UNIVERSITY" and str(rec.get("program_code") or "").strip().upper() == old_c:
                rec["program_code"] = new_code
                rec["program_name"] = new_name
                adm_yr = str(rec.get("admission_year") or "24")[-2:]
                roll = str(rec.get("roll_number") or "001")
                univ = str(rec.get("university_code") or "BWU")
                rec["student_code"] = f"{univ}/{new_code}/{adm_yr}/{roll}"
        save_users(users)

    programs[prog_idx] = {"name": n, "code": new_c}
    save_programs(programs)
    return {
        "program": {"name": n, "code": new_c},
        "students_updated": student_count if (new_c != old_c and update_students) else 0
    }


def delete_program_db(code: str) -> bool:
    """
    Deletes an academic program if no students are assigned.
    """
    c = str(code).strip().upper()
    if not c:
        return False

    if is_database_configured():
        with get_db_session() as session:
            prog = session.query(Program).filter(func.upper(Program.code) == c).first()
            if not prog:
                return False
            enrolled = session.query(User).filter(func.upper(User.program_code) == c).count()
            if enrolled > 0:
                raise ValueError("This program is currently assigned to students and cannot be deleted.")
            session.delete(prog)
            session.commit()
            return True

    programs = load_programs()
    prog_to_delete = None
    for p in programs:
        if str(p.get("code") or "").strip().upper() == c:
            prog_to_delete = p
            break
    if not prog_to_delete:
        return False

    if count_students_in_program(c) > 0:
        raise ValueError("This program is currently assigned to students and cannot be deleted.")

    programs = [p for p in programs if str(p.get("code") or "").strip().upper() != c]
    save_programs(programs)
    return True


def create_question_db(q_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a single question in PostgreSQL (if configured) or questions.json.
    """
    fixed = _migrate_one_question(q_data)
    if not fixed:
        raise ValueError("Invalid question data.")

    if is_database_configured():
        with get_db_session() as session:
            qid = str(fixed.get("id") or f"Q-{uuid.uuid4().hex[:8].upper()}")
            if session.query(Question).filter(Question.id == qid).first():
                qid = f"Q-{uuid.uuid4().hex[:8].upper()}"
                fixed["id"] = qid

            q = Question(
                id=qid,
                course_code=fixed["course_code"],
                course_name=fixed["course_name"],
                subject=fixed["subject"],
                program_code=fixed.get("program_code") or "ALL",
                program_name=fixed.get("program_name") or "",
                admission_year=str(fixed.get("admission_year") or "ALL"),
                academic_year=str(fixed.get("academic_year") or "ALL"),
                unit=fixed.get("unit") or "",
                topic=fixed.get("topic") or "",
                type=fixed.get("type", "MCQ"),
                level=fixed.get("level", "Easy"),
                question_text=fixed.get("question") or fixed.get("q") or "",
                options=fixed.get("options") if fixed.get("type") == "MCQ" else None,
                correct=fixed.get("correct") if fixed.get("type") == "MCQ" else None,
                answer_key=fixed.get("answer_key") if fixed.get("type") == "DESCRIPTIVE" else None,
                max_marks=float(fixed.get("max_marks", 5.0)),
                source=fixed.get("source", "MANUAL")
            )
            session.add(q)
            session.commit()
            global _QUESTIONS_CACHE
            _QUESTIONS_CACHE = None
            return q.to_dict()

    questions = load_questions()
    questions.insert(0, fixed)
    save_json(QUESTIONS_FILE, questions)
    return fixed


def create_questions_bulk_db(q_list: List[Dict[str, Any]]) -> int:
    """
    Bulk inserts questions into PostgreSQL (if configured) or questions.json.
    """
    migrated_list = []
    for item in q_list:
        fixed = _migrate_one_question(item)
        if fixed:
            migrated_list.append(fixed)

    if not migrated_list:
        return 0

    if is_database_configured():
        with get_db_session() as session:
            existing_ids = {q.id for q in session.query(Question.id).all()}
            count = 0
            for fixed in migrated_list:
                qid = str(fixed.get("id") or "")
                if not qid or qid in existing_ids:
                    qid = f"Q-{uuid.uuid4().hex[:8].upper()}"
                    fixed["id"] = qid
                existing_ids.add(qid)

                q = Question(
                    id=qid,
                    course_code=fixed["course_code"],
                    course_name=fixed["course_name"],
                    subject=fixed["subject"],
                    program_code=fixed.get("program_code") or "ALL",
                    program_name=fixed.get("program_name") or "",
                    admission_year=str(fixed.get("admission_year") or "ALL"),
                    academic_year=str(fixed.get("academic_year") or "ALL"),
                    unit=fixed.get("unit") or "",
                    topic=fixed.get("topic") or "",
                    type=fixed.get("type", "MCQ"),
                    level=fixed.get("level", "Easy"),
                    question_text=fixed.get("question") or fixed.get("q") or "",
                    options=fixed.get("options") if fixed.get("type") == "MCQ" else None,
                    correct=fixed.get("correct") if fixed.get("type") == "MCQ" else None,
                    answer_key=fixed.get("answer_key") if fixed.get("type") == "DESCRIPTIVE" else None,
                    max_marks=float(fixed.get("max_marks", 5.0)),
                    source=fixed.get("source", "MANUAL")
                )
                session.add(q)
                count += 1
            session.commit()
            global _QUESTIONS_CACHE
            _QUESTIONS_CACHE = None
            return count

    questions = load_questions()
    questions.extend(migrated_list)
    save_json(QUESTIONS_FILE, questions)
    return len(migrated_list)


def update_question_db(question_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates an existing question in PostgreSQL (if configured) or questions.json.
    """
    qid = str(question_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            q = session.query(Question).filter(Question.id == qid).first()
            if not q:
                return None

            if "level" in updates:
                q.level = updates["level"]
            if "max_marks" in updates:
                try:
                    q.max_marks = float(updates["max_marks"])
                except Exception:
                    q.max_marks = 5.0
            if "question" in updates or "q" in updates:
                q.question_text = updates.get("question") or updates.get("q") or q.question_text
            if "options" in updates:
                q.options = updates["options"]
            if "correct" in updates:
                q.correct = updates["correct"]
            if "answer_key" in updates:
                q.answer_key = updates["answer_key"]
            if "course_code" in updates:
                q.course_code = updates["course_code"]
            if "course_name" in updates:
                q.course_name = updates["course_name"]
            if "subject" in updates:
                q.subject = updates["subject"]

            session.commit()
            global _QUESTIONS_CACHE
            _QUESTIONS_CACHE = None
            return q.to_dict()

    questions = load_questions()
    for q in questions:
        if str(q.get("id")) == qid:
            q.update(updates)
            save_json(QUESTIONS_FILE, questions)
            return q
    return None


def delete_question_db(question_id: str) -> bool:
    """
    Deletes a question by ID in PostgreSQL (if configured) or questions.json.
    """
    qid = str(question_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            q = session.query(Question).filter(Question.id == qid).first()
            if not q:
                return False
            session.query(CourseExamQuestion).filter(CourseExamQuestion.question_id == qid).delete(synchronize_session=False)
            session.delete(q)
            session.commit()
            global _QUESTIONS_CACHE
            _QUESTIONS_CACHE = None
            return True

    questions = load_questions()
    for i, q in enumerate(questions):
        if str(q.get("id")) == qid:
            questions.pop(i)
            save_json(QUESTIONS_FILE, questions)
            return True
    return False


def delete_questions_bulk_db(question_ids: List[str]) -> int:
    """
    Bulk deletes questions by IDs in PostgreSQL (if configured) or questions.json.
    """
    if not question_ids:
        return 0
    clean_ids = [str(qid).strip() for qid in question_ids if qid]
    if not clean_ids:
        return 0

    if is_database_configured():
        with get_db_session() as session:
            session.query(CourseExamQuestion).filter(CourseExamQuestion.question_id.in_(clean_ids)).delete(synchronize_session=False)
            count = session.query(Question).filter(Question.id.in_(clean_ids)).delete(synchronize_session=False)
            session.commit()
            global _QUESTIONS_CACHE
            _QUESTIONS_CACHE = None
            return count

    questions = load_questions()
    del_set = set(clean_ids)
    remaining = [q for q in questions if str(q.get("id")) not in del_set]
    count = len(questions) - len(remaining)
    save_json(QUESTIONS_FILE, remaining)
    return count


def create_course_exam_db(exam_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new course exam in PostgreSQL (if configured) or course_exams.json.
    """
    eid = str(exam_data.get("id") or "").strip()
    if not eid:
        course_c = str(exam_data.get("course_code") or "EXAM").strip().upper()
        eid = f"EXAM-{course_c}-{uuid.uuid4().hex[:6].upper()}"
        exam_data["id"] = eid

    if is_database_configured():
        exam_date_val = None
        raw_date = exam_data.get("exam_date")
        if raw_date:
            if isinstance(raw_date, str) and raw_date.strip():
                try:
                    exam_date_val = datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
                except Exception:
                    pass
            elif hasattr(raw_date, "strftime"):
                exam_date_val = raw_date

        created_at_val = datetime.now()
        raw_created = exam_data.get("created_at")
        if raw_created and isinstance(raw_created, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    created_at_val = datetime.strptime(raw_created.strip(), fmt)
                    break
                except Exception:
                    pass

        with get_db_session() as session:
            exam = CourseExam(
                id=eid,
                title=str(exam_data.get("title") or "").strip(),
                course_code=str(exam_data.get("course_code") or "").strip().upper(),
                course_name=str(exam_data.get("course_name") or exam_data.get("course_code") or "").strip(),
                subject=str(exam_data.get("subject") or "").strip(),
                description=str(exam_data.get("description") or "").strip(),
                exam_type=str(exam_data.get("exam_type") or "MCQ").strip(),
                exam_date=exam_date_val,
                start_time=str(exam_data.get("start_time") or "").strip(),
                end_time=str(exam_data.get("end_time") or "").strip(),
                duration=int(exam_data.get("duration") or 60),
                num_questions=int(exam_data.get("num_questions") or 10),
                difficulty=str(exam_data.get("difficulty") or "All").strip(),
                status=str(exam_data.get("status") or "Draft").strip(),
                target_mode=str(exam_data.get("target_mode") or "PROGRAM_BATCH_YEAR").strip().upper(),
                program_code=str(exam_data.get("program_code") or "").strip().upper() or None,
                program_name=exam_data.get("program_name") or (get_program_name(exam_data.get("program_code")) if exam_data.get("program_code") else None),
                admission_year=str(exam_data.get("admission_year") or "").strip() or None,
                academic_year=str(exam_data.get("academic_year") or "").strip() or None,
                all_in_batch=bool(exam_data.get("all_in_batch", True)),
                created_at=created_at_val,
                updated_at=created_at_val
            )
            session.add(exam)
            session.flush()

            qids = exam_data.get("question_ids") or []
            if isinstance(qids, list):
                for sort_idx, qid in enumerate(dict.fromkeys(qids)):
                    if session.query(Question).filter(Question.id == str(qid)).first():
                        session.add(CourseExamQuestion(
                            exam_id=exam.id,
                            question_id=str(qid),
                            sort_order=sort_idx
                        ))

            scodes = exam_data.get("student_codes") or []
            if isinstance(scodes, list):
                for sc in dict.fromkeys(scodes):
                    if sc:
                        session.add(CourseExamTargetedStudent(
                            exam_id=exam.id,
                            student_code=str(sc).strip().upper()
                        ))

            session.commit()
            return exam.to_dict()

    exams = load_course_exams()
    exams.append(exam_data)
    save_course_exams(exams)
    return exam_data


def update_course_exam_db(exam_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates a course exam in PostgreSQL (if configured) or course_exams.json.
    """
    eid = str(exam_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            exam = session.query(CourseExam).options(
                selectinload(CourseExam.question_associations),
                selectinload(CourseExam.targeted_students)
            ).filter(CourseExam.id == eid).first()
            if not exam:
                return None

            if "title" in updates: exam.title = updates["title"]
            if "course_code" in updates: exam.course_code = updates["course_code"].strip().upper()
            if "course_name" in updates: exam.course_name = updates["course_name"].strip()
            if "subject" in updates: exam.subject = updates["subject"].strip()
            if "description" in updates: exam.description = updates["description"].strip()
            if "exam_type" in updates: exam.exam_type = updates["exam_type"].strip()
            if "start_time" in updates: exam.start_time = updates["start_time"].strip()
            if "end_time" in updates: exam.end_time = updates["end_time"].strip()
            if "duration" in updates: exam.duration = int(updates["duration"])
            if "num_questions" in updates: exam.num_questions = int(updates["num_questions"])
            if "difficulty" in updates: exam.difficulty = updates["difficulty"].strip()
            if "status" in updates: exam.status = updates["status"].strip()
            if "target_mode" in updates: exam.target_mode = updates["target_mode"].strip().upper()
            if "program_code" in updates:
                exam.program_code = str(updates["program_code"] or "").strip().upper() or None
                if exam.program_code and "program_name" not in updates:
                    exam.program_name = get_program_name(exam.program_code)
            if "program_name" in updates: exam.program_name = updates["program_name"]
            if "admission_year" in updates:
                exam.admission_year = str(updates["admission_year"] or "").strip() or None
            if "academic_year" in updates:
                exam.academic_year = str(updates["academic_year"] or "").strip() or None
            if "all_in_batch" in updates: exam.all_in_batch = bool(updates["all_in_batch"])

            if "exam_date" in updates:
                raw_d = updates["exam_date"]
                if isinstance(raw_d, str) and raw_d.strip():
                    try:
                        exam.exam_date = datetime.strptime(raw_d.strip(), "%Y-%m-%d").date()
                    except Exception:
                        pass
                elif hasattr(raw_d, "strftime"):
                    exam.exam_date = raw_d

            if "question_ids" in updates and isinstance(updates["question_ids"], list):
                session.query(CourseExamQuestion).filter(CourseExamQuestion.exam_id == eid).delete(synchronize_session=False)
                for sort_idx, qid in enumerate(dict.fromkeys(updates["question_ids"])):
                    if session.query(Question).filter(Question.id == str(qid)).first():
                        session.add(CourseExamQuestion(
                            exam_id=eid,
                            question_id=str(qid),
                            sort_order=sort_idx
                        ))

            if "student_codes" in updates and isinstance(updates["student_codes"], list):
                session.query(CourseExamTargetedStudent).filter(CourseExamTargetedStudent.exam_id == eid).delete(synchronize_session=False)
                for sc in dict.fromkeys(updates["student_codes"]):
                    if sc:
                        session.add(CourseExamTargetedStudent(
                            exam_id=eid,
                            student_code=str(sc).strip().upper()
                        ))

            exam.updated_at = datetime.now()
            session.commit()
            return exam.to_dict()

    exams = load_course_exams()
    for e in exams:
        if str(e.get("id")) == eid:
            e.update(updates)
            save_course_exams(exams)
            return e
    return None


def update_course_exam_status_db(exam_id: str, status: str) -> bool:
    """
    Updates the status of a course exam (e.g. 'Draft', 'Published', 'Closed').
    """
    eid = str(exam_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            exam = session.query(CourseExam).filter(CourseExam.id == eid).first()
            if not exam:
                return False
            exam.status = status.strip()
            exam.updated_at = datetime.now()
            session.commit()
            return True

    exams = load_course_exams()
    for e in exams:
        if str(e.get("id")) == eid:
            e["status"] = status.strip()
            save_course_exams(exams)
            return True
    return False


def delete_course_exam_db(exam_id: str) -> bool:
    """
    Deletes course exam, safely cascades junction rows, detaches any ExamResult foreign keys.
    """
    eid = str(exam_id).strip()
    if is_database_configured():
        with get_db_session() as session:
            exam = session.query(CourseExam).filter(CourseExam.id == eid).first()
            if not exam:
                return False
            session.query(ExamResult).filter(ExamResult.course_exam_id == eid).update(
                {ExamResult.course_exam_id: None},
                synchronize_session=False
            )
            session.query(CourseExamQuestion).filter(CourseExamQuestion.exam_id == eid).delete(synchronize_session=False)
            session.query(CourseExamTargetedStudent).filter(CourseExamTargetedStudent.exam_id == eid).delete(synchronize_session=False)
            session.delete(exam)
            session.commit()
            return True

    exams = load_course_exams()
    filtered = [e for e in exams if str(e.get("id")) != eid]
    if len(filtered) < len(exams):
        save_course_exams(filtered)
        return True
    return False


def set_course_exam_questions_db(exam_id: str, question_ids: List[str]) -> bool:
    """
    Updates question selection for an exam.
    """
    eid = str(exam_id).strip()
    clean_qids = list(dict.fromkeys(str(q).strip() for q in question_ids if q))

    if is_database_configured():
        with get_db_session() as session:
            exam = session.query(CourseExam).filter(CourseExam.id == eid).first()
            if not exam:
                return False
            session.query(CourseExamQuestion).filter(CourseExamQuestion.exam_id == eid).delete(synchronize_session=False)
            for sort_idx, qid in enumerate(clean_qids):
                if session.query(Question).filter(Question.id == qid).first():
                    session.add(CourseExamQuestion(
                        exam_id=eid,
                        question_id=qid,
                        sort_order=sort_idx
                    ))
            exam.updated_at = datetime.now()
            session.commit()
            return True

    exams = load_course_exams()
    for e in exams:
        if str(e.get("id")) == eid:
            e["question_ids"] = clean_qids
            save_course_exams(exams)
            return True
    return False


def create_exam_result_db(result_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates an exam result attempt in PostgreSQL (if configured) or results.json.
    Ensures user_id foreign key constraint is satisfied.
    """
    if is_database_configured():
        user_key = str(result_data.get("user_key") or result_data.get("user_id") or result_data.get("username") or "").strip()
        exam_id = result_data.get("course_exam_id")
        exam_id_str = str(exam_id).strip() if exam_id else None
        exam_title = str(result_data.get("exam_title") or "Practice Examination").strip()
        course_code = str(result_data.get("course_code") or "").strip().upper() or None

        sub_at = datetime.now()
        raw_date = result_data.get("date") or result_data.get("submitted_at")
        if raw_date and isinstance(raw_date, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    sub_at = datetime.strptime(raw_date.strip(), fmt)
                    break
                except Exception:
                    pass

        with get_db_session() as session:
            user = None
            if user_key:
                user = session.query(User).filter(
                    (User.id == user_key) |
                    (func.lower(User.username) == user_key.lower()) |
                    (func.lower(User.email) == user_key.lower())
                ).first()

            if not user:
                placeholder_id = user_key or f"user_{uuid.uuid4().hex[:10]}"
                user = User(
                    id=placeholder_id,
                    username=placeholder_id,
                    name=placeholder_id,
                    email=f"{placeholder_id.lower()}@examforge.local",
                    pw_hash="!",
                    user_type="EXTERNAL"
                )
                session.add(user)
                session.flush()

            valid_exam_id = None
            if exam_id_str:
                exam_row = session.query(CourseExam).filter(CourseExam.id == exam_id_str).first()
                if exam_row:
                    valid_exam_id = exam_row.id

            res = ExamResult(
                user_id=user.id,
                user_key=user_key or user.id,
                course_exam_id=valid_exam_id,
                exam_title=exam_title,
                course_code=course_code,
                score=float(result_data.get("score") or 0.0),
                total=float(result_data.get("total") or 0.0),
                time_taken=str(result_data.get("time_taken") or "").strip(),
                submitted_at=sub_at,
                descriptive_reports=result_data.get("descriptive_reports")
            )
            session.add(res)
            session.commit()
            return res.to_history_dict()

    results = load_results()
    user_key = str(result_data.get("user_key") or result_data.get("user_id") or result_data.get("username") or "anonymous").strip()
    if user_key not in results:
        results[user_key] = {"history": []}

    item = {
        "score": float(result_data.get("score", 0.0)),
        "total": float(result_data.get("total", 0.0)),
        "time_taken": str(result_data.get("time_taken", "")),
        "date": result_data.get("date") or time.strftime("%Y-%m-%d %H:%M:%S"),
        "descriptive_reports": result_data.get("descriptive_reports"),
        "exam_title": result_data.get("exam_title", "Practice Examination"),
        "course_code": result_data.get("course_code", ""),
        "course_exam_id": result_data.get("course_exam_id", None)
    }
    results[user_key]["history"].append(item)
    save_results(results)
    return item
