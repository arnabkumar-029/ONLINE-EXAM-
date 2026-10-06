import unittest
import json
import re
from unittest.mock import patch, MagicMock
from app import create_app

class TestBatchGeneration(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Simulate admin login session
        with self.client.session_transaction() as sess:
            sess["admin"] = True
            sess["user_id"] = "ADMIN001"

    def test_batch_split_50_questions(self):
        """Test that requesting 50 questions splits into 5 batches of 10 sequentially."""
        call_count = 0
        batch_sizes_requested = []

        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal call_count
            call_count += 1
            match = re.search(r"Generate exactly (\d+)", prompt)
            if not match:
                match = re.search(r"Total:\s*(\d+)\s*questions", prompt)
            if match:
                batch_sizes_requested.append(int(match.group(1)))

            # Return 10 unique MCQ questions per batch
            batch_items = []
            for i in range(10):
                q_num = (call_count - 1) * 10 + i + 1
                batch_items.append({
                    "type": "MCQ",
                    "question": f"Batch question {q_num} on Process Scheduling?",
                    "options": [f"Option A{q_num}", f"Option B{q_num}", f"Option C{q_num}", f"Option D{q_num}"],
                    "correct": f"Option A{q_num}",
                    "level": "Medium"
                })
            return json.dumps(batch_items), None

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "Computer Science",
                "program_code": "CSE",
                "admission_year": "2024",
                "academic_year": "3rd Year",
                "unit": "Unit 1",
                "topic": "Process Scheduling",
                "qtype": "MCQ",
                "difficulty": "Medium",
                "count": 50
            })

            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 50)
            self.assertEqual(len(data["questions"]), 50)
            # Verify 5 calls made for 50 questions
            self.assertEqual(call_count, 5)
            self.assertEqual(batch_sizes_requested, [10, 10, 10, 10, 10])

    def test_batch_failure_reports_batch_number(self):
        """Test that failure in batch 3 returns clean JSON mentioning Batch 3 of 5."""
        current_batch = 0

        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal current_batch
            current_batch += 1
            if current_batch == 3:
                return None, "AI request timed out after 22.0s"
            
            items = [{
                "type": "MCQ",
                "question": f"Question {current_batch}_{i}",
                "options": ["A", "B", "C", "D"],
                "correct": "A",
                "level": "Easy"
            } for i in range(10)]
            return json.dumps(items), None

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Threads",
                "qtype": "MCQ",
                "count": 50
            })

            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("Batch 3 of 5", data["error"])
            self.assertIn("timed out", data["error"].lower())

    def test_deduplication_and_topup_batch(self):
        """Test deduplication across batches triggers top-up to fulfill requested 20 questions."""
        batch_counter = 0

        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal batch_counter
            batch_counter += 1
            if batch_counter == 1:
                # 10 questions
                return json.dumps([
                    {
                        "type": "MCQ",
                        "question": f"Unique question {i}",
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "level": "Easy"
                    } for i in range(10)
                ]), None
            elif batch_counter == 2:
                # 8 unique, 2 duplicates from batch 1
                items = [
                    {
                        "type": "MCQ",
                        "question": "Unique question 0", # duplicate
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "level": "Easy"
                    },
                    {
                        "type": "MCQ",
                        "question": "Unique question 1", # duplicate
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "level": "Easy"
                    }
                ]
                items.extend([
                    {
                        "type": "MCQ",
                        "question": f"Batch 2 question {i}",
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "level": "Easy"
                    } for i in range(8)
                ])
                return json.dumps(items), None
            elif batch_counter == 3:
                # Top-up batch for missing 2 questions
                return json.dumps([
                    {
                        "type": "MCQ",
                        "question": f"Topup question {i}",
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "level": "Easy"
                    } for i in range(2)
                ]), None

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 2",
                "topic": "Deadlocks",
                "qtype": "MCQ",
                "count": 20
            })

            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 20)
            self.assertEqual(len(data["questions"]), 20)
            self.assertEqual(batch_counter, 3) # 2 main batches + 1 top-up batch

    def test_all_question_fields_preserved(self):
        """Verifies that all normalized fields are preserved in batch results."""
        fake_items = [
            {
                "type": "MCQ",
                "question": "What is virtual memory?",
                "options": ["RAM abstraction", "Hard drive", "Cache", "ROM"],
                "correct": "RAM abstraction",
                "level": "Medium"
            },
            {
                "type": "DESCRIPTIVE",
                "question": "Explain paging mechanism.",
                "answer_key": "Page table, frames, TLB.",
                "max_marks": 5,
                "level": "Hard"
            }
        ]
        with patch("admin_routes._call_gemini_http", return_value=(json.dumps(fake_items), None)):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "Computer Science",
                "program_code": "CSE",
                "program_name": "B.Tech CSE",
                "admission_year": "2024",
                "academic_year": "3rd Year",
                "unit": "Unit 4",
                "topic": "Virtual Memory",
                "qtype": "MIXED",
                "difficulty": "Medium",
                "count": 2
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(len(data["questions"]), 2)

            mcq = data["questions"][0]
            self.assertEqual(mcq["course_code"], "CS301")
            self.assertEqual(mcq["course_name"], "Operating Systems")
            self.assertEqual(mcq["subject"], "Computer Science")
            self.assertEqual(mcq["program_code"], "CSE")
            self.assertEqual(int(mcq["admission_year"]), 2024)
            self.assertEqual(mcq["academic_year"], "3rd Year")
            self.assertEqual(mcq["unit"], "Unit 4")
            self.assertEqual(mcq["topic"], "Virtual Memory")
            self.assertEqual(mcq["type"], "MCQ")
            self.assertEqual(mcq["source"], "AI")
            self.assertEqual(len(mcq["options"]), 4)
            self.assertEqual(mcq["correct"], "RAM abstraction")

            desc = data["questions"][1]
            self.assertEqual(desc["type"], "DESCRIPTIVE")
            self.assertEqual(desc["source"], "AI")
            self.assertEqual(desc["answer_key"], "Page table, frames, TLB.")
            self.assertEqual(desc["max_marks"], 5)

    def test_gunicorn_conf_timeout_setting(self):
        """Verifies that gunicorn.conf.py provides at least 120s timeout buffer."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("gunicorn_conf_module", "gunicorn.conf.py")
        gconf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gconf)
        self.assertGreaterEqual(gconf.timeout, 120)
        self.assertEqual(gconf.workers, 1)

if __name__ == "__main__":
    unittest.main()
