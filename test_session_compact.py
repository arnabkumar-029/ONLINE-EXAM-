# test_session_compact.py
"""
Verification suite for compact session cookie fix:
1. Validates get_questions_by_ids() preserves exact order and returns full question schemas.
2. Simulates full Flask Test Client exam lifecycle:
   - Login
   - POST /start_exam with 20 and 50 questions
   - Measures exact session cookie payload size (must be < 3,000 bytes and < 4,093 bytes)
   - Follows redirect to GET /exam -> must return 200 OK (not 302 to /auth)
   - Answers questions via POST /exam
   - Navigates through exam
   - Finishes exam at /result -> evaluates score
3. Verifies zero modifications to PostgreSQL question bank (319 questions).
4. Verifies zero modifications to JSON files.
"""

import os
import sys
import json
import hashlib
import unittest
from dotenv import load_dotenv

load_dotenv()

from app import create_app
import utils
from db import is_database_configured, get_db_session
from models import Question

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILES = {
    "programs.json": os.path.join(BASE_DIR, "programs.json"),
    "users.json": os.path.join(BASE_DIR, "users.json"),
    "questions.json": os.path.join(BASE_DIR, "questions.json"),
    "course_exams.json": os.path.join(BASE_DIR, "course_exams.json"),
    "results.json": os.path.join(BASE_DIR, "results.json"),
}

def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

class TestSessionCompact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial_hashes = {name: _file_hash(path) for name, path in JSON_FILES.items()}
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()

    def test_01_get_questions_by_ids_preserves_order(self):
        """Verify get_questions_by_ids strictly preserves arbitrary input ID order."""
        all_qs = utils.load_questions()
        self.assertGreaterEqual(len(all_qs), 20)

        # Pick 5 arbitrary questions and reverse them
        sample_qs = all_qs[:5]
        expected_ids = [q["id"] for q in reversed(sample_qs)]

        fetched = utils.get_questions_by_ids(expected_ids)
        self.assertEqual(len(fetched), len(expected_ids))

        fetched_ids = [q["id"] for q in fetched]
        self.assertEqual(fetched_ids, expected_ids, "Question order must match input list exactly")

        # Verify essential fields for exam and scoring
        for q in fetched:
            self.assertIn("id", q)
            self.assertIn("q", q)
            self.assertIn("type", q)
            if q["type"] == "MCQ":
                self.assertIn("a", q)
                self.assertIn("correct", q)
            else:
                self.assertIn("answer_key", q)
                self.assertIn("max_marks", q)

    def test_02_empty_or_invalid_ids_handled_safely(self):
        """Verify empty and non-existent IDs return safely without crashing."""
        self.assertEqual(utils.get_questions_by_ids([]), [])
        self.assertEqual(utils.get_questions_by_ids(["NON_EXISTENT_ID_99999"]), [])

    def test_03_test_yourself_exam_startup_cookie_size_20_qs(self):
        """
        Verify POST /start_exam with 20 questions produces a cookie < 3000 bytes
        and GET /exam returns HTTP 200 OK.
        """
        with self.client as c:
            # Setup authenticated student session
            with c.session_transaction() as sess:
                sess["username"] = "arnab_kumar"
                sess["user_id"] = "arnab_kumar"
                sess["email"] = "arnabkumarjana7543@gmail.com"
                sess["user_type"] = "UNIVERSITY"
                sess["student_code"] = "BWU/AIR/24/029"
                sess["program_code"] = "AIR"
                sess["admission_year"] = "2024"
                sess["academic_year"] = "3rd Year"

            # POST /start_exam with 20 questions
            resp = c.post("/start_exam", data={
                "type": "MCQ",
                "level": "ALL",
                "count": "20",
                "source_mode": "all",
            }, follow_redirects=False)

            # Must redirect to /exam
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/exam", resp.headers.get("Location", ""))

            # Inspect Set-Cookie header size
            cookie_headers = resp.headers.getlist("Set-Cookie")
            session_cookie = None
            for ch in cookie_headers:
                if ch.startswith("session="):
                    session_cookie = ch
                    break

            if session_cookie:
                cookie_val = session_cookie.split(";")[0]
                cookie_bytes = len(cookie_val.encode("utf-8"))
                print(f"\n[Cookie Size - 20 Questions]: {cookie_bytes} bytes")
                self.assertLess(cookie_bytes, 4093, f"Cookie ({cookie_bytes} bytes) exceeds browser limit of 4093 bytes!")
                self.assertLess(cookie_bytes, 3000, f"Cookie ({cookie_bytes} bytes) exceeds 3000 bytes target!")

            # Verify session state has compact IDs and no questions dicts
            with c.session_transaction() as sess:
                self.assertIn("exam_question_ids", sess)
                self.assertNotIn("questions", sess)
                self.assertEqual(len(sess["exam_question_ids"]), 20)

            # Follow redirect: GET /exam MUST return 200 OK (NOT redirect to /auth)
            exam_resp = c.get("/exam")
            self.assertEqual(exam_resp.status_code, 200, "GET /exam must return 200 OK after start_exam")
            self.assertIn(b"Question 1 / 20", exam_resp.data)

    def test_04_test_yourself_exam_startup_cookie_size_50_qs(self):
        """
        Verify POST /start_exam with 50 questions produces a cookie < 3000 bytes
        and GET /exam returns HTTP 200 OK.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess["username"] = "arnab_kumar"
                sess["user_id"] = "arnab_kumar"
                sess["email"] = "arnabkumarjana7543@gmail.com"
                sess["user_type"] = "UNIVERSITY"
                sess["student_code"] = "BWU/AIR/24/029"
                sess["program_code"] = "AIR"
                sess["admission_year"] = "2024"
                sess["academic_year"] = "3rd Year"

            resp = c.post("/start_exam", data={
                "type": "MCQ",
                "level": "ALL",
                "count": "50",
                "source_mode": "all",
            }, follow_redirects=False)

            self.assertEqual(resp.status_code, 302)

            cookie_headers = resp.headers.getlist("Set-Cookie")
            session_cookie = None
            for ch in cookie_headers:
                if ch.startswith("session="):
                    session_cookie = ch
                    break

            if session_cookie:
                cookie_val = session_cookie.split(";")[0]
                cookie_bytes = len(cookie_val.encode("utf-8"))
                print(f"[Cookie Size - 50 Questions]: {cookie_bytes} bytes")
                self.assertLess(cookie_bytes, 4093, f"Cookie ({cookie_bytes} bytes) exceeds browser limit of 4093 bytes!")
                self.assertLess(cookie_bytes, 3000, f"Cookie ({cookie_bytes} bytes) exceeds 3000 bytes target!")

            with c.session_transaction() as sess:
                self.assertIn("exam_question_ids", sess)
                self.assertNotIn("questions", sess)
                self.assertEqual(len(sess["exam_question_ids"]), 50)

            exam_resp = c.get("/exam")
            self.assertEqual(exam_resp.status_code, 200)
            self.assertIn(b"Question 1 / 50", exam_resp.data)

    def test_05_exam_navigation_and_scoring(self):
        """
        Verify answering questions through POST /exam works seamlessly
        and /result computes the correct score.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess["username"] = "arnab_kumar"
                sess["user_id"] = "arnab_kumar"

            # Start 3-question MCQ exam
            c.post("/start_exam", data={
                "type": "MCQ",
                "level": "ALL",
                "count": "3",
                "source_mode": "all",
            })

            with c.session_transaction() as sess:
                qids = sess["exam_question_ids"]

            questions = utils.get_questions_by_ids(qids)
            self.assertEqual(len(questions), 3)

            # Answer Question 0 correctly
            q0_correct = questions[0].get("correct", "")
            ans_resp = c.post("/exam", data={
                "action": "next",
                "answer": q0_correct
            }, follow_redirects=True)
            self.assertEqual(ans_resp.status_code, 200)

            # Check index advanced to 1
            with c.session_transaction() as sess:
                self.assertEqual(sess["index"], 1)
                self.assertEqual(sess["answers"].get("0"), q0_correct)

            # Answer Question 1 with a deliberately wrong answer
            ans_resp2 = c.post("/exam", data={
                "action": "next",
                "answer": "DEFINITELY_WRONG_OPTION_XYZ"
            }, follow_redirects=True)
            self.assertEqual(ans_resp2.status_code, 200)

            # Skip Question 2 (last question -> redirects to /result)
            skip_resp = c.post("/exam", data={
                "action": "skip",
                "answer": ""
            }, follow_redirects=True)
            self.assertEqual(skip_resp.status_code, 200)
            self.assertIn(b"Exam Completed!", skip_resp.data)

            # Verify score in session: 1 correct, 1 wrong, 1 skipped
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("score"), 1.0)
                self.assertEqual(sess.get("wrong"), 1)
                self.assertEqual(sess.get("skipped"), 1)

    def test_06_legacy_session_backwards_compatibility(self):
        """
        Verify that if an existing user session still contains session['questions']
        (without session['exam_question_ids']), GET /exam and /result continue to work smoothly.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess["username"] = "arnab_kumar"
                sess["user_id"] = "arnab_kumar"
                sess.pop("exam_question_ids", None)
                sess["questions"] = [
                    {
                        "id": "Q-LEGACY-01",
                        "type": "MCQ",
                        "q": "What is Python?",
                        "a": ["Programming Language", "Snake", "Coffee", "OS"],
                        "correct": "Programming Language",
                        "level": "Easy"
                    }
                ]
                sess["index"] = 0
                sess["answers"] = {"0": "Programming Language"}
                sess["start_time"] = 0
                sess["total_time"] = 600

            # GET /exam should render the legacy question
            exam_resp = c.get("/exam")
            self.assertEqual(exam_resp.status_code, 200)
            self.assertIn(b"What is Python?", exam_resp.data)

            # GET /result should evaluate the legacy question
            res_resp = c.get("/result")
            self.assertEqual(res_resp.status_code, 200)
            self.assertIn(b"Exam Completed!", res_resp.data)
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("score"), 1.0)
                self.assertEqual(sess.get("wrong"), 0)

    def test_07_database_questions_untouched(self):
        """Verify PostgreSQL questions count remains intact at 319."""
        if is_database_configured():
            with get_db_session() as session:
                count = session.query(Question).count()
                self.assertEqual(count, 319, f"Expected 319 questions in PostgreSQL, found {count}")

    def test_08_json_files_untouched(self):
        """Verify all 5 JSON files on disk remain completely unmodified."""
        for name, path in JSON_FILES.items():
            current_hash = _file_hash(path)
            self.assertEqual(
                current_hash,
                self.initial_hashes[name],
                f"JSON file '{name}' was modified during test run!"
            )

if __name__ == "__main__":
    unittest.main()
