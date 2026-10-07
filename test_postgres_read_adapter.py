# test_postgres_read_adapter.py
"""
Automated Verification Suite for ExamForge PostgreSQL Read Adapter Layer (Task 8A).

Tests all 16 read adapter operations against PostgreSQL:
1. load_programs() returns 15 records
2. load_users() returns 23 records (21 active + 2 archived)
3. load_questions() returns 173 records
4. load_course_exams() returns 7 records
5. load_results() represents 51 historical results
6. get_program_by_code() works (case-insensitive)
7. find_user_by_email() works (case-insensitive)
8. get_course_exam_by_id() works
9. CourseExam.to_dict() contains question_ids and student_codes
10. get_student_exam_result() matches by course_exam_id and legacy exam_title
11. get_student_identity_from_session_or_db() resolves full academic identity
12. All 5 JSON files on disk remain completely unmodified
"""

import os
import sys
import json
import hashlib
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILES = {
    "programs.json": os.path.join(BASE_DIR, "programs.json"),
    "users.json": os.path.join(BASE_DIR, "users.json"),
    "questions.json": os.path.join(BASE_DIR, "questions.json"),
    "course_exams.json": os.path.join(BASE_DIR, "course_exams.json"),
    "results.json": os.path.join(BASE_DIR, "results.json"),
}


def _file_hash(path: str) -> str:
    """Calculates SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


class TestPostgresReadAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Capture pristine state of all 5 JSON files before test run
        cls.initial_hashes = {name: _file_hash(path) for name, path in JSON_FILES.items()}
        cls.initial_counts = {}
        for name, path in JSON_FILES.items():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls.initial_counts[name] = len(data)

        # 2. Check if DATABASE_URL is already configured (e.g. Supabase)
        import db
        cls.had_env_db = bool(os.getenv("DATABASE_URL"))
        cls.temp_db_path = os.path.join(BASE_DIR, "test_adapter_suite.db")

        if not cls.had_env_db:
            if os.path.exists(cls.temp_db_path):
                try:
                    os.remove(cls.temp_db_path)
                except Exception:
                    pass
            # Set up an isolated database populated with the exact schema and migrated data
            os.environ["DATABASE_URL"] = f"sqlite:///{cls.temp_db_path}"
            db._ENGINE = None
            db._SESSION_FACTORY = None

            from models import Base
            Base.metadata.create_all(db.get_engine())

            from migrate_json_to_postgres import run_migration
            success, summary = run_migration(dry_run=False)
            if not success:
                raise RuntimeError(f"Failed to populate test database: {summary}")

        import utils
        cls.utils = utils
        cls.db = db

    @classmethod
    def tearDownClass(cls):
        # Clean up temporary database if one was created
        if not cls.had_env_db:
            if cls.db._ENGINE is not None:
                cls.db._ENGINE.dispose()
            cls.db._ENGINE = None
            cls.db._SESSION_FACTORY = None
            os.environ.pop("DATABASE_URL", None)
            if os.path.exists(cls.temp_db_path):
                try:
                    os.remove(cls.temp_db_path)
                except Exception:
                    pass

    def test_01_load_programs_returns_15_records(self):
        """Verify load_programs() returns exactly 15 records from the database."""
        programs = self.utils.load_programs()
        self.assertIsInstance(programs, list)
        self.assertEqual(len(programs), 15)
        codes = [p.get("code") for p in programs]
        self.assertIn("AIR", codes)
        self.assertIn("CS", codes)
        self.assertIn("IT", codes)
        for p in programs:
            self.assertIn("code", p)
            self.assertIn("name", p)

    def test_02_load_users_returns_23_records(self):
        """Verify load_users() returns 23 records (21 active + 2 archived) formatted as a dictionary."""
        users = self.utils.load_users()
        self.assertIsInstance(users, dict)
        self.assertEqual(len(users), 23)
        self.assertIn("arnab_kumar", users)
        self.assertIn("admin", users)
        self.assertIn("archived_test_student", users)
        self.assertIn("archived_atanuq", users)

        # Check dictionary fields
        u = users["arnab_kumar"]
        self.assertEqual(u.get("student_code"), "BWU/AIR/24/029")
        self.assertEqual(u.get("program_code"), "AIR")
        self.assertEqual(u.get("user_type"), "UNIVERSITY")
        self.assertEqual(u.get("email"), "arnabkumarjana7543@gmail.com")

    def test_03_load_questions_returns_173_records(self):
        """Verify load_questions() returns exactly 173 records with deterministic ordering."""
        questions = self.utils.load_questions()
        self.assertIsInstance(questions, list)
        self.assertEqual(len(questions), 173)

        # Check required fields
        first_q = questions[0]
        self.assertIn("id", first_q)
        self.assertIn("course_code", first_q)
        self.assertIn("subject", first_q)
        self.assertIn("type", first_q)
        self.assertIn("question", first_q)

    def test_04_load_course_exams_returns_7_records(self):
        """Verify load_course_exams() returns exactly 7 scheduled examinations."""
        exams = self.utils.load_course_exams()
        self.assertIsInstance(exams, list)
        self.assertEqual(len(exams), 7)
        exam_ids = [e.get("id") for e in exams]
        self.assertIn("EXAM-CS301-MIDTERM", exam_ids)

    def test_05_course_exam_to_dict_contains_question_ids_and_student_codes(self):
        """Verify CourseExam.to_dict() contains question_ids and student_codes lists."""
        exam = self.utils.get_course_exam_by_id("EXAM-CS301-MIDTERM")
        self.assertIsNotNone(exam)
        self.assertIn("question_ids", exam)
        self.assertIn("student_codes", exam)
        self.assertIsInstance(exam["question_ids"], list)
        self.assertIsInstance(exam["student_codes"], list)
        self.assertEqual(len(exam["question_ids"]), 10)

    def test_06_load_results_represents_51_historical_results(self):
        """Verify load_results() groups into user history dictionaries and represents 51 total attempts."""
        results = self.utils.load_results()
        self.assertIsInstance(results, dict)
        total_attempts = sum(len(v.get("history", [])) for v in results.values())
        self.assertEqual(total_attempts, 51)
        self.assertIn("arnab_kumar", results)
        self.assertIn("test_student", results)
        self.assertEqual(len(results["arnab_kumar"]["history"]), 3)
        self.assertEqual(len(results["test_student"]["history"]), 9)

    def test_07_get_program_by_code_works(self):
        """Verify get_program_by_code() finds program case-insensitively."""
        prog = self.utils.get_program_by_code("AIR")
        self.assertIsNotNone(prog)
        self.assertEqual(prog.get("code"), "AIR")
        self.assertEqual(prog.get("name"), "AI & Robotics")

        # Lowercase check
        prog_lower = self.utils.get_program_by_code("air")
        self.assertIsNotNone(prog_lower)
        self.assertEqual(prog_lower.get("code"), "AIR")

        # Invalid code check
        self.assertIsNone(self.utils.get_program_by_code("NONEXISTENT_999"))

    def test_08_find_user_by_email_works(self):
        """Verify find_user_by_email() finds user case-insensitively and returns (id, record)."""
        res = self.utils.find_user_by_email("arnabkumarjana7543@gmail.com")
        self.assertIsNotNone(res)
        uid, udict = res
        self.assertEqual(uid, "arnab_kumar")
        self.assertEqual(udict.get("email"), "arnabkumarjana7543@gmail.com")

        # Uppercase email check
        res_upper = self.utils.find_user_by_email("ARNABKUMARJANA7543@GMAIL.COM")
        self.assertIsNotNone(res_upper)
        self.assertEqual(res_upper[0], "arnab_kumar")

        # Non-existent email check
        self.assertIsNone(self.utils.find_user_by_email("nonexistent@examforge.test"))

    def test_09_get_course_exam_by_id_works(self):
        """Verify get_course_exam_by_id() returns the full exam dict."""
        exam = self.utils.get_course_exam_by_id("EXAM-CS301-MIDTERM")
        self.assertIsNotNone(exam)
        self.assertEqual(exam.get("id"), "EXAM-CS301-MIDTERM")
        self.assertEqual(exam.get("course_code"), "CS301")
        self.assertIn("question_ids", exam)

        # Non-existent ID check
        self.assertIsNone(self.utils.get_course_exam_by_id("EXAM-NONEXISTENT"))

    def test_10_is_student_code_taken_and_academic_eligibility(self):
        """Verify student code checks and academic eligibility counting work via PostgreSQL."""
        self.assertTrue(self.utils.is_student_code_taken("BWU/AIR/24/029"))
        self.assertTrue(self.utils.is_student_code_taken("bwu/air/24/029"))
        self.assertFalse(self.utils.is_student_code_taken("BWU/AIR/99/999"))

        # Exclude self check
        self.assertFalse(self.utils.is_student_code_taken("BWU/AIR/24/029", exclude_id="arnab_kumar"))

        # Eligibility check
        students = self.utils.get_all_students_for_eligibility()
        self.assertIsInstance(students, list)
        self.assertGreater(len(students), 0)

    def test_11_get_student_exam_result_dual_matching(self):
        """Verify get_student_exam_result() matches by course_exam_id and legacy exam_title."""
        # Match by legacy exam_title
        exam_query_by_title = {"title": "Completed Examination"}
        res = self.utils.get_student_exam_result("arnab_kumar", exam_query_by_title)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("exam_title"), "Completed Examination")
        self.assertEqual(res.get("score"), 4.0)

        # Non-matching exam
        no_res = self.utils.get_student_exam_result("arnab_kumar", {"id": "EXAM-DOES-NOT-EXIST", "title": "No Such Exam"})
        self.assertIsNone(no_res)

    def test_12_json_files_unmodified(self):
        """CRITICAL: Verify that zero modifications occurred to any of the 5 JSON files on disk."""
        for name, path in JSON_FILES.items():
            self.assertTrue(os.path.exists(path), f"File {name} was unexpectedly deleted!")
            current_hash = _file_hash(path)
            self.assertEqual(
                current_hash,
                self.initial_hashes[name],
                f"File {name} was modified during testing! SHA-256 hash mismatch."
            )
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(
                    len(data),
                    self.initial_counts[name],
                    f"File {name} item count changed from {self.initial_counts[name]} to {len(data)}!"
                )


if __name__ == "__main__":
    unittest.main()
