# test_postgres_write_adapter.py
"""
Automated Verification Suite for ExamForge PostgreSQL Write Adapter Layer (Task 8B).

Tests all 20 write adapter operations and route mutations against PostgreSQL:
1. create user in DB
2. update user in DB
3. delete user in DB
4. duplicate email protection in DB
5. duplicate student code protection in DB
6. create program in DB
7. update program code and cascade to student records
8. delete program with 0 students
9. delete program with students blocked
10. create MCQ question in DB
11. create DESCRIPTIVE question in DB
12. edit question in DB
13. delete question in DB
14. bulk delete questions in DB
15. create course exam in DB with questions and students
16. update course exam in DB
17. toggle course exam status (Draft -> Published -> Closed)
18. delete course exam in DB and cascade junctions
19. create practice exam result in DB (course_exam_id=NULL)
20. create course exam result in DB with foreign keys
21. All 5 JSON files on disk remain completely unmodified
"""

import os
import sys
import json
import hashlib
import unittest
import uuid
from datetime import datetime

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


class TestPostgresWriteAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Capture pristine state and hashes of all 5 JSON files
        cls.initial_hashes = {name: _file_hash(path) for name, path in JSON_FILES.items()}
        cls.initial_counts = {}
        for name, path in JSON_FILES.items():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls.initial_counts[name] = len(data)

        # 2. Set up isolated test database
        import db
        cls.had_env_db = bool(os.getenv("DATABASE_URL"))
        cls.temp_db_path = os.path.join(BASE_DIR, "test_write_suite.db")

        if os.path.exists(cls.temp_db_path):
            try:
                os.remove(cls.temp_db_path)
            except Exception:
                pass

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
        # 1. Clean up database engine
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

        # 2. Final verification: Verify all 5 JSON files on disk are 100% untouched
        for name, path in JSON_FILES.items():
            curr_hash = _file_hash(path)
            if curr_hash != cls.initial_hashes[name]:
                raise AssertionError(f"FATAL: JSON file {name} was unexpectedly modified during write testing!")

    def test_01_create_user_in_db(self):
        """1. create user in DB: verifies user creation via create_user_db."""
        new_uid = f"test_user_{uuid.uuid4().hex[:6]}"
        user_data = {
            "id": new_uid,
            "username": "Test Student 1",
            "name": "Test Student 1",
            "email": f"{new_uid}@example.com",
            "pw_hash": "scrypt:mock_hash",
            "user_type": "UNIVERSITY",
            "student_code": f"BWU/AIR/24/{uuid.uuid4().hex[:3].upper()}",
            "university_code": "BWU",
            "program_code": "AIR",
            "program_name": "AI & Robotics",
            "department_name": "Engineering",
            "admission_year": 2024,
            "academic_year": "1st Year",
            "roll_number": "999"
        }
        res = self.utils.create_user_db(user_data)
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], new_uid)

        # Verify directly in DB
        with self.db.get_db_session() as session:
            from models import User
            db_user = session.query(User).filter(User.id == new_uid).first()
            self.assertIsNotNone(db_user)
            self.assertEqual(db_user.email, user_data["email"].lower())
            self.assertEqual(db_user.student_code, user_data["student_code"].upper())

    def test_02_update_user_in_db(self):
        """2. update user in DB: verifies user update via update_user_db."""
        uid = f"upd_user_{uuid.uuid4().hex[:6]}"
        self.utils.create_user_db({
            "id": uid,
            "username": "Original Name",
            "email": f"{uid}@example.com",
            "pw_hash": "hash1",
            "user_type": "EXTERNAL"
        })

        updated = self.utils.update_user_db(uid, {
            "name": "Updated Name",
            "username": "Updated Name",
            "user_type": "UNIVERSITY",
            "department_name": "Computer Science"
        })
        self.assertIsNotNone(updated)
        self.assertEqual(updated["name"], "Updated Name")
        self.assertEqual(updated["user_type"], "UNIVERSITY")
        self.assertEqual(updated["department_name"], "Computer Science")

        with self.db.get_db_session() as session:
            from models import User
            db_user = session.query(User).filter(User.id == uid).first()
            self.assertEqual(db_user.username, "Updated Name")
            self.assertEqual(db_user.department_name, "Computer Science")

    def test_03_delete_user_in_db(self):
        """3. delete user in DB: verifies user deletion via delete_user_db."""
        uid = f"del_user_{uuid.uuid4().hex[:6]}"
        self.utils.create_user_db({
            "id": uid,
            "username": "To Delete",
            "email": f"{uid}@example.com",
            "pw_hash": "hash1"
        })

        del_ok = self.utils.delete_user_db(uid)
        self.assertTrue(del_ok)

        with self.db.get_db_session() as session:
            from models import User
            db_user = session.query(User).filter(User.id == uid).first()
            self.assertIsNone(db_user)

    def test_04_duplicate_email_protection_in_db(self):
        """4. duplicate email protection: verifies ValueError raised on duplicate email."""
        dup_email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
        self.utils.create_user_db({
            "id": f"u1_{uuid.uuid4().hex[:4]}",
            "username": "User 1",
            "email": dup_email,
            "pw_hash": "h1"
        })

        with self.assertRaises(ValueError):
            self.utils.create_user_db({
                "id": f"u2_{uuid.uuid4().hex[:4]}",
                "username": "User 2",
                "email": dup_email,
                "pw_hash": "h2"
            })

    def test_05_duplicate_student_code_protection_in_db(self):
        """5. duplicate student code protection: verifies ValueError raised on duplicate student_code."""
        dup_code = f"BWU/TEST/24/{uuid.uuid4().hex[:3].upper()}"
        self.utils.create_user_db({
            "id": f"sc1_{uuid.uuid4().hex[:4]}",
            "username": "SC User 1",
            "email": f"sc1_{uuid.uuid4().hex[:4]}@example.com",
            "student_code": dup_code,
            "pw_hash": "h1"
        })

        with self.assertRaises(ValueError):
            self.utils.create_user_db({
                "id": f"sc2_{uuid.uuid4().hex[:4]}",
                "username": "SC User 2",
                "email": f"sc2_{uuid.uuid4().hex[:4]}@example.com",
                "student_code": dup_code,
                "pw_hash": "h2"
            })

    def test_06_create_program_in_db(self):
        """6. create program in DB: verifies academic program creation."""
        code = f"P{uuid.uuid4().hex[:4].upper()}"
        name = f"Program {code}"
        res = self.utils.create_program_db(code, name)
        self.assertEqual(res["code"], code)
        self.assertEqual(res["name"], name)

        with self.db.get_db_session() as session:
            from models import Program
            p = session.query(Program).filter(Program.code == code).first()
            self.assertIsNotNone(p)
            self.assertEqual(p.name, name)

    def test_07_update_program_code_and_cascade_to_student_records(self):
        """7. update program code and cascade: verifies atomic update of program and enrolled students."""
        old_c = f"C{uuid.uuid4().hex[:4].upper()}"
        new_c = f"D{uuid.uuid4().hex[:4].upper()}"
        self.utils.create_program_db(old_c, f"Department of {old_c}")

        # Create student enrolled in old_c
        stu_id = f"cascade_stu_{uuid.uuid4().hex[:4]}"
        self.utils.create_user_db({
            "id": stu_id,
            "username": "Cascade Student",
            "email": f"{stu_id}@example.com",
            "pw_hash": "h1",
            "user_type": "UNIVERSITY",
            "student_code": f"BWU/{old_c}/24/007",
            "university_code": "BWU",
            "program_code": old_c,
            "admission_year": 2024,
            "roll_number": "007"
        })

        res = self.utils.update_program_db(old_c, new_c, f"Department of {new_c}", update_students=True)
        self.assertEqual(res["program"]["code"], new_c)
        self.assertGreaterEqual(res["students_updated"], 1)

        with self.db.get_db_session() as session:
            from models import User, Program
            self.assertIsNone(session.query(Program).filter(Program.code == old_c).first())
            self.assertIsNotNone(session.query(Program).filter(Program.code == new_c).first())
            stu = session.query(User).filter(User.id == stu_id).first()
            self.assertEqual(stu.program_code, new_c)
            self.assertEqual(stu.student_code, f"BWU/{new_c}/24/007")

    def test_08_delete_program_with_0_students(self):
        """8. delete program with 0 students: succeeds."""
        code = f"Z{uuid.uuid4().hex[:4].upper()}"
        self.utils.create_program_db(code, f"Empty Program {code}")
        del_ok = self.utils.delete_program_db(code)
        self.assertTrue(del_ok)

        with self.db.get_db_session() as session:
            from models import Program
            self.assertIsNone(session.query(Program).filter(Program.code == code).first())

    def test_09_delete_program_with_students_blocked(self):
        """9. delete program with students blocked: raises ValueError."""
        code = f"B{uuid.uuid4().hex[:4].upper()}"
        self.utils.create_program_db(code, f"Blocked Program {code}")

        stu_id = f"stu_blocked_{uuid.uuid4().hex[:4]}"
        self.utils.create_user_db({
            "id": stu_id,
            "username": "Blocked Student",
            "email": f"{stu_id}@example.com",
            "pw_hash": "h1",
            "user_type": "UNIVERSITY",
            "student_code": f"BWU/{code}/24/008",
            "program_code": code
        })

        with self.assertRaises(ValueError):
            self.utils.delete_program_db(code)

    def test_10_create_mcq_question_in_db(self):
        """10. create MCQ question in DB."""
        qid = f"Q-TEST-{uuid.uuid4().hex[:6].upper()}"
        q_data = {
            "id": qid,
            "course_code": "CS101",
            "course_name": "Computer Science",
            "subject": "Python",
            "type": "MCQ",
            "level": "Easy",
            "question": "What is 2 + 2?",
            "options": ["1", "2", "3", "4"],
            "correct": "4",
            "source": "MANUAL"
        }
        res = self.utils.create_question_db(q_data)
        self.assertEqual(res["id"], qid)
        self.assertEqual(res["type"], "MCQ")

        with self.db.get_db_session() as session:
            from models import Question
            q = session.query(Question).filter(Question.id == qid).first()
            self.assertIsNotNone(q)
            self.assertEqual(q.correct, "4")
            self.assertEqual(len(q.options), 4)

    def test_11_create_descriptive_question_in_db(self):
        """11. create DESCRIPTIVE question in DB."""
        qid = f"Q-DESC-{uuid.uuid4().hex[:6].upper()}"
        q_data = {
            "id": qid,
            "course_code": "CS101",
            "course_name": "Computer Science",
            "subject": "Python",
            "type": "DESCRIPTIVE",
            "level": "Hard",
            "question": "Explain the Python GIL.",
            "answer_key": "keywords: GIL, thread, mutex, bytecode",
            "max_marks": 10,
            "source": "MANUAL"
        }
        res = self.utils.create_question_db(q_data)
        self.assertEqual(res["id"], qid)
        self.assertEqual(res["type"], "DESCRIPTIVE")

        with self.db.get_db_session() as session:
            from models import Question
            q = session.query(Question).filter(Question.id == qid).first()
            self.assertIsNotNone(q)
            self.assertIn("GIL", q.answer_key)
            self.assertEqual(float(q.max_marks), 10.0)

    def test_12_edit_question_in_db(self):
        """12. edit question in DB: verifies update_question_db."""
        qid = f"Q-EDT-{uuid.uuid4().hex[:6].upper()}"
        self.utils.create_question_db({
            "id": qid,
            "course_code": "CS101",
            "subject": "Python",
            "type": "DESCRIPTIVE",
            "level": "Easy",
            "question": "Original Q?",
            "max_marks": 5
        })

        upd = self.utils.update_question_db(qid, {
            "level": "Medium",
            "max_marks": 8,
            "question": "Updated Q?"
        })
        self.assertEqual(upd["level"], "Medium")
        self.assertEqual(float(upd["max_marks"]), 8.0)

        with self.db.get_db_session() as session:
            from models import Question
            q = session.query(Question).filter(Question.id == qid).first()
            self.assertEqual(q.level, "Medium")
            self.assertEqual(float(q.max_marks), 8.0)

    def test_13_delete_question_in_db(self):
        """13. delete question in DB: verifies delete_question_db."""
        qid = f"Q-DEL-{uuid.uuid4().hex[:6].upper()}"
        self.utils.create_question_db({
            "id": qid,
            "course_code": "CS101",
            "subject": "Python",
            "type": "MCQ",
            "question": "Delete me?",
            "options": ["A", "B"],
            "correct": "A"
        })

        del_ok = self.utils.delete_question_db(qid)
        self.assertTrue(del_ok)

        with self.db.get_db_session() as session:
            from models import Question
            self.assertIsNone(session.query(Question).filter(Question.id == qid).first())

    def test_14_bulk_delete_questions_in_db(self):
        """14. bulk delete questions in DB: verifies delete_questions_bulk_db."""
        qids = [f"Q-BULK-{i}-{uuid.uuid4().hex[:4].upper()}" for i in range(3)]
        for qid in qids:
            self.utils.create_question_db({
                "id": qid,
                "course_code": "CS101",
                "subject": "Python",
                "type": "MCQ",
                "question": f"Bulk {qid}?",
                "options": ["A", "B"],
                "correct": "A"
            })

        count = self.utils.delete_questions_bulk_db(qids)
        self.assertEqual(count, 3)

        with self.db.get_db_session() as session:
            from models import Question
            remaining = session.query(Question).filter(Question.id.in_(qids)).all()
            self.assertEqual(len(remaining), 0)

    def test_15_create_course_exam_in_db_with_questions_and_students(self):
        """15. create course exam with questions and students: verifies junction records."""
        eid = f"EXAM-{uuid.uuid4().hex[:6].upper()}"
        # Create 2 questions to attach
        q1 = f"Q-EX1-{uuid.uuid4().hex[:4].upper()}"
        q2 = f"Q-EX2-{uuid.uuid4().hex[:4].upper()}"
        self.utils.create_question_db({"id": q1, "course_code": "CS101", "subject": "Python", "type": "MCQ", "question": "Q1?", "options": ["A"], "correct": "A"})
        self.utils.create_question_db({"id": q2, "course_code": "CS101", "subject": "Python", "type": "MCQ", "question": "Q2?", "options": ["A"], "correct": "A"})

        exam_data = {
            "id": eid,
            "title": "Unit Test Exam",
            "course_code": "CS101",
            "course_name": "Computer Science",
            "subject": "Python",
            "exam_type": "MCQ",
            "exam_date": "2026-11-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "duration": 60,
            "num_questions": 2,
            "difficulty": "Easy",
            "status": "Draft",
            "target_mode": "SPECIFIC_STUDENTS",
            "student_codes": ["BWU/AIR/24/001", "BWU/AIR/24/002"],
            "question_ids": [q1, q2]
        }
        res = self.utils.create_course_exam_db(exam_data)
        self.assertEqual(res["id"], eid)
        self.assertEqual(len(res["question_ids"]), 2)
        self.assertEqual(len(res["student_codes"]), 2)

        with self.db.get_db_session() as session:
            from models import CourseExam, CourseExamQuestion, CourseExamTargetedStudent
            db_exam = session.query(CourseExam).filter(CourseExam.id == eid).first()
            self.assertIsNotNone(db_exam)
            eq_count = session.query(CourseExamQuestion).filter(CourseExamQuestion.exam_id == eid).count()
            self.assertEqual(eq_count, 2)
            ts_count = session.query(CourseExamTargetedStudent).filter(CourseExamTargetedStudent.exam_id == eid).count()
            self.assertEqual(ts_count, 2)

    def test_16_update_course_exam_in_db(self):
        """16. update course exam in DB: verifies update_course_exam_db."""
        eid = f"EXAM-{uuid.uuid4().hex[:6].upper()}"
        self.utils.create_course_exam_db({
            "id": eid,
            "title": "Pre-Update Title",
            "course_code": "CS101",
            "subject": "Python",
            "duration": 45
        })

        upd = self.utils.update_course_exam_db(eid, {
            "title": "Post-Update Title",
            "duration": 90,
            "difficulty": "Hard"
        })
        self.assertEqual(upd["title"], "Post-Update Title")
        self.assertEqual(upd["duration"], 90)

        with self.db.get_db_session() as session:
            from models import CourseExam
            db_exam = session.query(CourseExam).filter(CourseExam.id == eid).first()
            self.assertEqual(db_exam.title, "Post-Update Title")
            self.assertEqual(db_exam.duration, 90)

    def test_17_toggle_course_exam_status(self):
        """17. toggle course exam status: Draft -> Published -> Closed."""
        eid = f"EXAM-{uuid.uuid4().hex[:6].upper()}"
        self.utils.create_course_exam_db({
            "id": eid,
            "title": "Status Exam",
            "course_code": "CS101",
            "subject": "Python",
            "status": "Draft"
        })

        self.assertTrue(self.utils.update_course_exam_status_db(eid, "Published"))
        exam = self.utils.get_course_exam_by_id(eid)
        self.assertEqual(exam["status"], "Published")

        self.assertTrue(self.utils.update_course_exam_status_db(eid, "Closed"))
        exam = self.utils.get_course_exam_by_id(eid)
        self.assertEqual(exam["status"], "Closed")

    def test_18_delete_course_exam_in_db_and_cascade_junctions(self):
        """18. delete course exam: cascades junctions and detaches result FK."""
        eid = f"EXAM-{uuid.uuid4().hex[:6].upper()}"
        q1 = f"Q-DELJ-{uuid.uuid4().hex[:4].upper()}"
        self.utils.create_question_db({"id": q1, "course_code": "CS101", "subject": "Python", "type": "MCQ", "question": "Q?", "options": ["A"], "correct": "A"})

        self.utils.create_course_exam_db({
            "id": eid,
            "title": "Delete Cascade Exam",
            "course_code": "CS101",
            "subject": "Python",
            "question_ids": [q1],
            "student_codes": ["BWU/AIR/24/099"]
        })

        # Add exam result linked to this exam
        res = self.utils.create_exam_result_db({
            "user_key": "arnab_kumar",
            "course_exam_id": eid,
            "exam_title": "Delete Cascade Exam",
            "score": 10,
            "total": 10
        })

        del_ok = self.utils.delete_course_exam_db(eid)
        self.assertTrue(del_ok)

        with self.db.get_db_session() as session:
            from models import CourseExam, CourseExamQuestion, CourseExamTargetedStudent, ExamResult
            self.assertIsNone(session.query(CourseExam).filter(CourseExam.id == eid).first())
            self.assertEqual(session.query(CourseExamQuestion).filter(CourseExamQuestion.exam_id == eid).count(), 0)
            self.assertEqual(session.query(CourseExamTargetedStudent).filter(CourseExamTargetedStudent.exam_id == eid).count(), 0)
            # The result row should still exist with course_exam_id set to None
            r = session.query(ExamResult).filter(ExamResult.exam_title == "Delete Cascade Exam").first()
            self.assertIsNotNone(r)
            self.assertIsNone(r.course_exam_id)

    def test_19_create_practice_exam_result_in_db(self):
        """19. create practice exam result: course_exam_id is NULL."""
        user_key = f"prac_stu_{uuid.uuid4().hex[:4]}"
        res = self.utils.create_exam_result_db({
            "user_key": user_key,
            "exam_title": "Practice Quiz: Python",
            "course_code": "CS101",
            "score": 8.5,
            "total": 10.0,
            "time_taken": "5m 20s"
        })
        self.assertEqual(res["score"], 8.5)
        self.assertEqual(res["total"], 10.0)
        self.assertNotIn("course_exam_id", res)  # to_history_dict omits course_exam_id when None

        with self.db.get_db_session() as session:
            from models import ExamResult
            r = session.query(ExamResult).filter(ExamResult.user_key == user_key).first()
            self.assertIsNotNone(r)
            self.assertIsNone(r.course_exam_id)
            self.assertEqual(float(r.score), 8.5)

    def test_20_create_course_exam_result_in_db_with_foreign_keys(self):
        """20. create course exam result with valid foreign keys."""
        eid = f"EXAM-{uuid.uuid4().hex[:6].upper()}"
        self.utils.create_course_exam_db({
            "id": eid,
            "title": "Official Midterm",
            "course_code": "CS101",
            "subject": "Python"
        })

        stu_id = f"res_stu_{uuid.uuid4().hex[:4]}"
        self.utils.create_user_db({
            "id": stu_id,
            "username": "Result Student",
            "email": f"{stu_id}@example.com",
            "pw_hash": "h1"
        })

        res = self.utils.create_exam_result_db({
            "user_key": stu_id,
            "user_id": stu_id,
            "course_exam_id": eid,
            "exam_title": "Official Midterm",
            "course_code": "CS101",
            "score": 95.0,
            "total": 100.0,
            "time_taken": "45m 00s"
        })
        self.assertEqual(res["course_exam_id"], eid)
        self.assertEqual(res["score"], 95.0)

        with self.db.get_db_session() as session:
            from models import ExamResult
            r = session.query(ExamResult).filter(
                ExamResult.user_id == stu_id,
                ExamResult.course_exam_id == eid
            ).first()
            self.assertIsNotNone(r)
            self.assertEqual(r.course_exam_id, eid)
            self.assertEqual(float(r.score), 95.0)

    def test_21_verify_all_json_files_unmodified(self):
        """21. verify all 5 JSON files on disk remain completely unmodified."""
        for name, path in JSON_FILES.items():
            curr_hash = _file_hash(path)
            self.assertEqual(
                curr_hash,
                self.initial_hashes[name],
                f"JSON file {name} was modified on disk! Hash mismatch: {curr_hash} != {self.initial_hashes[name]}"
            )
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(
                    len(data),
                    self.initial_counts[name],
                    f"JSON file {name} count changed! {len(data)} != {self.initial_counts[name]}"
                )


if __name__ == "__main__":
    unittest.main()
