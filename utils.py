# utils.py
import os
import json
import re
import time
from typing import List, Dict, Any

# ---- Light-weight module-level constants (no heavy imports here) ----
USERS_FILE = "users.json"
RESULTS_FILE = "results.json"
QUESTIONS_FILE = "questions.json"

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
    q_text = str(q.get("q") or "").strip()
    if not q_text:
        return {}
    level = str(q.get("level") or "Easy").strip() or "Easy"
    qtype = _fix_type_to_capital(q.get("type"))
    if qtype == "MCQ":
        opts = q.get("a")
        if not isinstance(opts, list):
            alt = q.get("options")
            if isinstance(alt, list):
                opts = alt
            else:
                opts = []
        opts = [str(x).strip() for x in opts if str(x).strip()]
        correct = str(q.get("correct") or "").strip()
        return {"q": q_text, "type": "MCQ", "a": opts, "correct": correct, "level": level}
    ak = _coerce_answer_key_to_string(q.get("answer_key"))
    if ak and not ak.lower().startswith("keywords:"):
        ak = "keywords: " + ak
    try:
        max_marks = int(q.get("max_marks", 5))
    except Exception:
        max_marks = 5
    return {"q": q_text, "type": "DESCRIPTIVE", "answer_key": ak, "max_marks": max_marks, "level": level}

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
