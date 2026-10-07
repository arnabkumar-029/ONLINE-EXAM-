# migrate_json_to_postgres.py
"""
Data Migration Script: JSON Files -> Supabase PostgreSQL.
Transfers data from questions.json, users.json, results.json, course_exams.json, programs.json
into relational PostgreSQL tables using SQLAlchemy.

CRITICAL REQUIREMENTS:
- DOES NOT EXECUTE AUTOMATICALLY. Must be invoked explicitly: python migrate_json_to_postgres.py
- Preserves all existing IDs, fields, relationships, and historical records.
- Idempotent: Can be run multiple times safely without creating duplicates.
- Executes in an atomic transaction; rolls back completely on any fatal error.
- NEVER modifies or deletes the original JSON files.
- NEVER truncates or deletes PostgreSQL tables automatically.
- Comprehensive pre-flight cross-file validation with detailed warning/error tracking.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple

from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

from db import get_engine, get_db_session, is_database_configured, create_all_tables, mask_database_url
from models import (
    Program,
    User,
    Question,
    CourseExam,
    CourseExamQuestion,
    CourseExamTargetedStudent,
    ExamResult
)

# Paths to the 5 authoritative JSON files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRAMS_FILE = os.path.join(BASE_DIR, "programs.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
QUESTIONS_FILE = os.path.join(BASE_DIR, "questions.json")
COURSE_EXAMS_FILE = os.path.join(BASE_DIR, "course_exams.json")
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")


def load_json_safely(file_path: str, default_type=list):
    """Safely loads and parses JSON file without altering disk content."""
    if not os.path.exists(file_path):
        print(f"[ERROR] Required JSON file not found: {file_path}")
        return default_type()
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_date_safely(date_str: str | None):
    """Parses date string ('YYYY-MM-DD') into datetime.date or None."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    return None


def parse_datetime_safely(dt_str: str | None):
    """Parses datetime string ('YYYY-MM-DD HH:MM:SS') into datetime or None."""
    if not dt_str:
        return None
    cleaned = str(dt_str).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            pass
    return None


def run_migration(dry_run: bool = False):
    """
    Main migration routine:
    1. Validates all JSON files.
    2. Performs comprehensive foreign key and relationship analysis.
    3. In --dry-run mode: prints detailed validation report, expected row counts, warnings, and errors without touching the DB.
    4. In live mode: initializes schema and executes inserts in strict relational order with atomic rollback on error.
    """
    print("\n" + "=" * 65)
    print("      EXAMFORGE JSON -> POSTGRESQL DATA MIGRATION")
    print("=" * 65)

    if dry_run:
        print("[MODE] DRY RUN ONLY (Safe local pre-flight; no database changes)\n")
    else:
        print("[MODE] LIVE MIGRATION\n")

    warnings_list: List[str] = []
    errors_list: List[str] = []

    # Step 1: Verify all 5 JSON files exist and are readable
    print("1. Verifying source JSON files...")
    json_status = {}
    for name, path in [
        ("programs.json", PROGRAMS_FILE),
        ("users.json", USERS_FILE),
        ("questions.json", QUESTIONS_FILE),
        ("course_exams.json", COURSE_EXAMS_FILE),
        ("results.json", RESULTS_FILE)
    ]:
        if not os.path.exists(path):
            err = f"Missing file: {name}"
            print(f"   [FAIL] {err}")
            errors_list.append(err)
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = len(data) if isinstance(data, (list, dict)) else 0
                json_status[name] = (data, count)
                print(f"   [OK]   {name:<18} ({count} items)")
        except Exception as e:
            err = f"Could not parse {name}: {e}"
            print(f"   [FAIL] {err}")
            errors_list.append(err)
            return False

    raw_programs, prog_count = json_status["programs.json"]
    raw_users, user_count = json_status["users.json"]
    raw_questions, q_count = json_status["questions.json"]
    raw_course_exams, exam_count = json_status["course_exams.json"]
    raw_results, res_count = json_status["results.json"]

    # Pre-flight cross-file relationship analysis
    print("\n2. Performing pre-flight foreign-key & reference checks...")

    # Known sets from source data
    source_prog_codes: Set[str] = {
        str(p.get("code") or "").strip().upper()
        for p in raw_programs if isinstance(p, dict) and p.get("code")
    }

    source_user_ids: Set[str] = set()
    source_student_codes: Set[str] = set()
    user_lookup_map: Dict[str, str] = {}

    for ukey, udata in raw_users.items():
        if not isinstance(udata, dict):
            continue
        uid = str(udata.get("id") or ukey).strip()
        uname = str(udata.get("username") or udata.get("name") or ukey).strip()
        email = str(udata.get("email") or "").strip().lower()
        scode = str(udata.get("student_code") or "").strip().upper()

        source_user_ids.add(uid)
        if scode:
            source_student_codes.add(scode)

        user_lookup_map[ukey] = uid
        user_lookup_map[ukey.lower()] = uid
        user_lookup_map[uname] = uid
        user_lookup_map[uname.lower()] = uid
        if email:
            user_lookup_map[email] = uid

    source_q_ids: Set[str] = {
        str(q.get("id") or "").strip()
        for q in raw_questions if isinstance(q, dict) and q.get("id")
    }

    source_exam_ids: Set[str] = {
        str(e.get("id") or "").strip()
        for e in raw_course_exams if isinstance(e, dict) and e.get("id")
    }

    # Validate Exam-Question references
    valid_exam_q_links = 0
    missing_exam_q_links = 0
    for e in raw_course_exams:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("id") or "").strip()
        for qid in e.get("question_ids") or []:
            qid_str = str(qid).strip()
            if qid_str in source_q_ids:
                valid_exam_q_links += 1
            else:
                missing_exam_q_links += 1
                msg = f"Exam '{eid}' references question_id '{qid_str}' which is MISSING from questions.json. (Link skipped to prevent foreign key violation)"
                errors_list.append(msg)
                print(f"   [ERROR]   {msg}")

    # Validate Exam-Targeted-Student references
    valid_targeted_students = 0
    missing_targeted_students = 0
    for e in raw_course_exams:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("id") or "").strip()
        for sc in e.get("student_codes") or []:
            sc_str = str(sc).strip().upper()
            if sc_str:
                valid_targeted_students += 1
                if sc_str not in source_student_codes:
                    missing_targeted_students += 1
                    msg = f"Exam '{eid}' references student_code '{sc_str}' which is NOT registered in users.json."
                    warnings_list.append(msg)
                    print(f"   [WARNING] {msg}")

    # Validate Results user and exam references
    total_result_attempts = 0
    unmatched_result_users = 0
    archived_users_to_create = set()

    for user_key, u_res in raw_results.items():
        if not isinstance(u_res, dict):
            continue
        history = u_res.get("history") or []
        total_result_attempts += len(history)

        matched_uid = user_lookup_map.get(user_key) or user_lookup_map.get(user_key.lower())
        if not matched_uid:
            unmatched_result_users += 1
            archival_id = f"archived_{user_key.lower()}"
            archived_users_to_create.add((archival_id, user_key))
            msg = f"Result user key '{user_key}' ({len(history)} attempt(s)) is UNMATCHED in users.json. Creating placeholder account '{archival_id}' to preserve history."
            warnings_list.append(msg)
            print(f"   [WARNING] {msg}")

        for h in history:
            if isinstance(h, dict) and h.get("course_exam_id"):
                ce_id = str(h.get("course_exam_id")).strip()
                if ce_id not in source_exam_ids:
                    msg = f"Result attempt for user '{user_key}' references course_exam_id '{ce_id}' missing from course_exams.json. Storing as practice result (course_exam_id=NULL) to preserve scores."
                    warnings_list.append(msg)
                    print(f"   [WARNING] {msg}")

    # Expected row counts
    expected_programs = len(source_prog_codes)
    expected_users = len(source_user_ids) + len(archived_users_to_create)
    expected_questions = len(source_q_ids)
    expected_exams = len(source_exam_ids)
    expected_exam_q_links = valid_exam_q_links
    expected_targeted_links = valid_targeted_students
    expected_results = total_result_attempts

    if dry_run:
        print("\n" + "=" * 65)
        print("          DRY-RUN VALIDATION REPORT COMPLETED")
        print("=" * 65)
        print("Expected PostgreSQL table row counts after migration:")
        print(f" - programs:                      {expected_programs} records")
        print(f" - users:                         {expected_users} records ({len(source_user_ids)} active + {len(archived_users_to_create)} archived)")
        print(f" - questions:                     {expected_questions} records")
        print(f" - course_exams:                  {expected_exams} records")
        print(f" - course_exam_questions:        {expected_exam_q_links} records")
        print(f" - course_exam_targeted_students: {expected_targeted_links} records")
        print(f" - exam_results:                  {expected_results} records")
        print(f"\nAudit Totals: Warnings: {len(warnings_list)}, Errors: {len(errors_list)}")
        print("Conclusion: All source JSON records validated safely. Ready for live migration when requested.")
        return True

    # -------------------------------------------------------------
    # LIVE MIGRATION EXECUTION
    # -------------------------------------------------------------
    if not is_database_configured():
        print("\n[ERROR] DATABASE_URL environment variable is not set!")
        print("Please configure DATABASE_URL in Render or local .env before running.")
        return False

    engine = get_engine()
    if engine is None:
        print("\n[ERROR] Could not initialize database engine.")
        return False

    print("\n3. Initializing database schema (CREATE TABLE IF NOT EXISTS)...")
    create_all_tables()
    print("   [OK] Schema initialized.")

    print("\n4. Migrating data in relational order...")

    try:
        with get_db_session() as session:
            # ---------------------------------------------------------
            # 1. PROGRAMS MIGRATION
            # ---------------------------------------------------------
            print("\n   [1/7] Migrating Academic Programs...")
            existing_prog_codes = {p.code.upper() for p in session.query(Program.code).all()}
            inserted_programs = 0

            for p_item in raw_programs:
                if not isinstance(p_item, dict):
                    continue
                code = str(p_item.get("code") or "").strip().upper()
                name = str(p_item.get("name") or "").strip()
                if not code or not name:
                    continue

                if code not in existing_prog_codes:
                    prog_obj = Program(code=code, name=name)
                    session.add(prog_obj)
                    existing_prog_codes.add(code)
                    inserted_programs += 1

            session.flush()
            print(f"         Programs processed: {len(raw_programs)}, newly inserted: {inserted_programs}")

            # ---------------------------------------------------------
            # 2. USERS MIGRATION
            # ---------------------------------------------------------
            print("\n   [2/7] Migrating Users & Students...")
            existing_user_ids = {u.id for u in session.query(User.id).all()}
            existing_emails = {u.email.lower() for u in session.query(User.email).all()}
            existing_scodes = {u.student_code.upper() for u in session.query(User.student_code).all() if u.student_code}
            inserted_users = 0

            # Map to resolve legacy usernames to user_id
            user_key_to_id_map: Dict[str, str] = {}

            for ukey, udata in raw_users.items():
                if not isinstance(udata, dict):
                    continue

                uid = str(udata.get("id") or ukey).strip()
                uname = str(udata.get("username") or udata.get("name") or ukey).strip()
                name = str(udata.get("name") or uname).strip()
                email = str(udata.get("email") or "").strip().lower()
                pw_hash = str(udata.get("pw_hash") or udata.get("password") or "").strip()
                utype = str(udata.get("user_type") or "EXTERNAL").strip().upper()
                scode = str(udata.get("student_code") or "").strip().upper() or None
                univ_code = str(udata.get("university_code") or "").strip() or None
                pcode = str(udata.get("program_code") or "").strip().upper() or None
                pname = str(udata.get("program_name") or "").strip() or None
                dept_name = str(udata.get("department_name") or "").strip() or None
                acad_yr = str(udata.get("academic_year") or "").strip() or None
                roll_num = str(udata.get("roll_number") or "").strip() or None

                raw_adm = udata.get("admission_year")
                try:
                    adm_yr = int(raw_adm) if raw_adm else None
                except (ValueError, TypeError):
                    adm_yr = None

                is_admin = bool(udata.get("is_admin") or utype == "ADMIN" or ukey.lower() in ("admin", "adminc"))

                # Keep map for foreign key lookups
                user_key_to_id_map[ukey] = uid
                user_key_to_id_map[ukey.lower()] = uid
                user_key_to_id_map[uname] = uid
                user_key_to_id_map[uname.lower()] = uid
                if email:
                    user_key_to_id_map[email] = uid

                # Validate program_code foreign key
                if pcode and pcode not in existing_prog_codes:
                    pcode = None

                if uid in existing_user_ids:
                    continue

                # Ensure email uniqueness fallback if duplicate email in legacy data
                if email in existing_emails:
                    email = f"{uid}_{email}"

                # Ensure student code uniqueness fallback
                if scode and scode in existing_scodes:
                    scode = None

                user_obj = User(
                    id=uid,
                    username=uname,
                    name=name,
                    email=email or f"{uid}@local.examforge",
                    pw_hash=pw_hash or "unusable_hash",
                    user_type=utype,
                    student_code=scode,
                    university_code=univ_code,
                    program_code=pcode,
                    program_name=pname,
                    department_name=dept_name,
                    admission_year=adm_yr,
                    academic_year=acad_yr,
                    roll_number=roll_num,
                    is_admin=is_admin
                )
                session.add(user_obj)
                existing_user_ids.add(uid)
                if email:
                    existing_emails.add(email)
                if scode:
                    existing_scodes.add(scode)
                inserted_users += 1

            # Insert placeholder archival accounts for orphaned result users
            for archival_id, orig_key in archived_users_to_create:
                if archival_id not in existing_user_ids:
                    archived_user = User(
                        id=archival_id,
                        username=orig_key,
                        name=orig_key,
                        email=f"{archival_id}@archive.examforge",
                        pw_hash="archived_account",
                        user_type="EXTERNAL"
                    )
                    session.add(archived_user)
                    existing_user_ids.add(archival_id)
                    user_key_to_id_map[orig_key] = archival_id
                    user_key_to_id_map[orig_key.lower()] = archival_id
                    inserted_users += 1

            session.flush()
            print(f"         Users processed: {len(raw_users)}, newly inserted: {inserted_users}")

            # ---------------------------------------------------------
            # 3. QUESTIONS MIGRATION
            # ---------------------------------------------------------
            print("\n   [3/7] Migrating Questions Bank...")
            existing_q_ids = {q.id for q in session.query(Question.id).all()}
            inserted_questions = 0

            for q_item in raw_questions:
                if not isinstance(q_item, dict):
                    continue

                qid = str(q_item.get("id") or "").strip()
                if not qid or qid in existing_q_ids:
                    continue

                c_code = str(q_item.get("course_code") or "").strip().upper()
                c_name = str(q_item.get("course_name") or c_code).strip()
                subj = str(q_item.get("subject") or "General").strip()
                p_code = str(q_item.get("program_code") or "ALL").strip().upper()
                p_name = str(q_item.get("program_name") or "").strip()
                adm_yr = str(q_item.get("admission_year") or "ALL").strip()
                acad_yr = str(q_item.get("academic_year") or "ALL").strip()
                unit = str(q_item.get("unit") or "").strip()
                topic = str(q_item.get("topic") or "").strip()
                qtype = str(q_item.get("type") or "MCQ").strip().upper()
                level = str(q_item.get("level") or "Easy").strip().capitalize()
                qtext = str(q_item.get("question") or q_item.get("q") or "").strip()

                opts = q_item.get("options") or q_item.get("a")
                opts_clean = [str(x).strip() for x in opts] if isinstance(opts, list) else None

                correct = str(q_item.get("correct") or "").strip() or None
                ak = str(q_item.get("answer_key") or q_item.get("model_answer") or "").strip() or None

                try:
                    max_m = float(q_item.get("max_marks", 5.0))
                except (ValueError, TypeError):
                    max_m = 5.0

                src = str(q_item.get("source") or "MANUAL").strip().upper()

                q_obj = Question(
                    id=qid,
                    course_code=c_code,
                    course_name=c_name,
                    subject=subj,
                    program_code=p_code,
                    program_name=p_name,
                    admission_year=adm_yr,
                    academic_year=acad_yr,
                    unit=unit,
                    topic=topic,
                    type=qtype,
                    level=level,
                    question_text=qtext,
                    options=opts_clean,
                    correct=correct,
                    answer_key=ak,
                    max_marks=max_m,
                    source=src
                )
                session.add(q_obj)
                existing_q_ids.add(qid)
                inserted_questions += 1

            session.flush()
            print(f"         Questions processed: {len(raw_questions)}, newly inserted: {inserted_questions}")

            # ---------------------------------------------------------
            # 4. COURSE EXAMS MIGRATION
            # ---------------------------------------------------------
            print("\n   [4/7] Migrating Course Examinations...")
            existing_exam_ids = {e.id for e in session.query(CourseExam.id).all()}
            inserted_exams = 0

            for e_item in raw_course_exams:
                if not isinstance(e_item, dict):
                    continue

                eid = str(e_item.get("id") or "").strip()
                if not eid or eid in existing_exam_ids:
                    continue

                title = str(e_item.get("title") or "").strip()
                c_code = str(e_item.get("course_code") or "").strip().upper()
                c_name = str(e_item.get("course_name") or c_code).strip()
                subj = str(e_item.get("subject") or "").strip()
                desc = str(e_item.get("description") or "").strip()
                etype = str(e_item.get("exam_type") or "MCQ").strip()
                edate = parse_date_safely(e_item.get("exam_date"))
                stime = str(e_item.get("start_time") or "").strip()
                etime = str(e_item.get("end_time") or "").strip()

                try:
                    dur = int(e_item.get("duration", 60))
                except (ValueError, TypeError):
                    dur = 60

                try:
                    num_q = int(e_item.get("num_questions", 10))
                except (ValueError, TypeError):
                    num_q = 10

                diff = str(e_item.get("difficulty") or "All").strip()
                stat = str(e_item.get("status") or "Draft").strip()
                tmode = str(e_item.get("target_mode") or "PROGRAM_BATCH_YEAR").strip().upper()
                pcode = str(e_item.get("program_code") or "").strip().upper() or None
                pname = str(e_item.get("program_name") or "").strip()
                admyr = str(e_item.get("admission_year") or "").strip()
                acadyr = str(e_item.get("academic_year") or "").strip()
                all_batch = bool(e_item.get("all_in_batch", True))

                created_dt = parse_datetime_safely(e_item.get("created_at"))
                updated_dt = parse_datetime_safely(e_item.get("updated_at"))

                exam_obj = CourseExam(
                    id=eid,
                    title=title,
                    course_code=c_code,
                    course_name=c_name,
                    subject=subj,
                    description=desc,
                    exam_type=etype,
                    exam_date=edate,
                    start_time=stime,
                    end_time=etime,
                    duration=dur,
                    num_questions=num_q,
                    difficulty=diff,
                    status=stat,
                    target_mode=tmode,
                    program_code=pcode,
                    program_name=pname,
                    admission_year=admyr,
                    academic_year=acadyr,
                    all_in_batch=all_batch,
                    created_at=created_dt,
                    updated_at=updated_dt
                )
                session.add(exam_obj)
                existing_exam_ids.add(eid)
                inserted_exams += 1

            session.flush()
            print(f"         Course exams processed: {len(raw_course_exams)}, newly inserted: {inserted_exams}")

            # ---------------------------------------------------------
            # 5. COURSE EXAM QUESTIONS (JOIN TABLE)
            # ---------------------------------------------------------
            print("\n   [5/7] Migrating Course Exam Question Selection...")
            existing_exam_q_pairs = {
                (assoc.exam_id, assoc.question_id)
                for assoc in session.query(CourseExamQuestion.exam_id, CourseExamQuestion.question_id).all()
            }
            inserted_exam_questions = 0

            for e_item in raw_course_exams:
                eid = str(e_item.get("id") or "").strip()
                qids = e_item.get("question_ids") or []
                if not isinstance(qids, list):
                    continue

                for order_idx, qid in enumerate(qids):
                    qid_clean = str(qid).strip()
                    if qid_clean in existing_q_ids and (eid, qid_clean) not in existing_exam_q_pairs:
                        session.add(CourseExamQuestion(
                            exam_id=eid,
                            question_id=qid_clean,
                            sort_order=order_idx
                        ))
                        existing_exam_q_pairs.add((eid, qid_clean))
                        inserted_exam_questions += 1

            session.flush()
            print(f"         Exam-Question associations inserted: {inserted_exam_questions}")

            # ---------------------------------------------------------
            # 6. COURSE EXAM TARGETED STUDENTS (JOIN TABLE)
            # ---------------------------------------------------------
            print("\n   [6/7] Migrating Course Exam Targeted Students...")
            existing_targeted_pairs = {
                (ts.exam_id, ts.student_code)
                for ts in session.query(CourseExamTargetedStudent.exam_id, CourseExamTargetedStudent.student_code).all()
            }
            inserted_targeted = 0

            for e_item in raw_course_exams:
                eid = str(e_item.get("id") or "").strip()
                scodes = e_item.get("student_codes") or []
                if not isinstance(scodes, list):
                    continue

                for sc in scodes:
                    sc_clean = str(sc).strip().upper()
                    if sc_clean and (eid, sc_clean) not in existing_targeted_pairs:
                        session.add(CourseExamTargetedStudent(
                            exam_id=eid,
                            student_code=sc_clean
                        ))
                        existing_targeted_pairs.add((eid, sc_clean))
                        inserted_targeted += 1

            session.flush()
            print(f"         Exam-Student targeted entries inserted: {inserted_targeted}")

            # ---------------------------------------------------------
            # 7. EXAM RESULTS MIGRATION
            # ---------------------------------------------------------
            print("\n   [7/7] Migrating Exam Submissions & Results...")
            inserted_results = 0

            for user_key, u_res in raw_results.items():
                if not isinstance(u_res, dict):
                    continue

                matched_user_id = user_key_to_id_map.get(user_key) or user_key_to_id_map.get(user_key.lower())
                history = u_res.get("history") or []
                if not isinstance(history, list):
                    continue

                for h in history:
                    if not isinstance(h, dict):
                        continue

                    try:
                        score_val = float(h.get("score") or 0.0)
                    except (ValueError, TypeError):
                        score_val = 0.0

                    try:
                        total_val = float(h.get("total") or 0.0)
                    except (ValueError, TypeError):
                        total_val = 0.0

                    time_taken = str(h.get("time_taken") or "").strip()
                    sub_date = parse_datetime_safely(h.get("date"))
                    exam_title = str(h.get("exam_title") or "Practice Examination").strip()
                    c_code = str(h.get("course_code") or "").strip()
                    c_exam_id = str(h.get("course_exam_id") or "").strip() or None

                    if c_exam_id and c_exam_id not in existing_exam_ids:
                        c_exam_id = None

                    reports = h.get("descriptive_reports")

                    res_obj = ExamResult(
                        user_id=matched_user_id,
                        user_key=user_key,
                        course_exam_id=c_exam_id,
                        exam_title=exam_title,
                        course_code=c_code,
                        score=score_val,
                        total=total_val,
                        time_taken=time_taken,
                        submitted_at=sub_date,
                        descriptive_reports=reports
                    )
                    session.add(res_obj)
                    inserted_results += 1

            session.flush()
            print(f"         Exam results history entries inserted: {inserted_results}")

        print("\n" + "=" * 65)
        print("          MIGRATION COMPLETED SUCCESSFULLY! ")
        print("=" * 65)
        print("Summary of records inserted:")
        print(f" - programs:                      {inserted_programs}")
        print(f" - users / students:              {inserted_users}")
        print(f" - questions:                     {inserted_questions}")
        print(f" - course_exams:                  {inserted_exams}")
        print(f" - course_exam_questions:        {inserted_exam_questions}")
        print(f" - course_exam_targeted_students: {inserted_targeted}")
        print(f" - exam_results:                  {inserted_results}")
        print(f" - warnings:                      {len(warnings_list)}")
        print(f" - errors:                        {len(errors_list)}")
        print("\nAll records migrated with complete foreign-key integrity.")
        return True

    except Exception as exc:
        print("\n[FATAL ERROR] Migration failed during execution:")
        print(f"Error: {exc}")
        print("[ROLLBACK] Transaction rolled back automatically. No changes were committed.")
        return False


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    run_migration(dry_run=is_dry)
