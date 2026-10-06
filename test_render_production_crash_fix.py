import json
import os
import unittest
from unittest.mock import patch
from app import app
import urllib.error
import socket

class TestRenderCrashFix(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["admin"] = True

    def test_missing_api_key_returns_json(self):
        """Verifies that missing GEMINI_API_KEY returns JSON error."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Process Scheduling",
                "qtype": "MCQ",
                "count": 2
            })
            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json, "Response must be JSON, never HTML!")
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("AI service is not configured correctly", data["error"])

    def test_invalid_api_key_returns_json(self):
        """Verifies that an invalid GEMINI_API_KEY returns JSON error without exposing the key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSy_FAKE_INVALID_KEY_123"}, clear=False):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Process Scheduling",
                "qtype": "MCQ",
                "count": 2
            })
            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json, "Response must be JSON, never HTML!")
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("AI service is not configured correctly", data["error"])
            self.assertNotIn("AIzaSy_FAKE_INVALID_KEY_123", json.dumps(data))

    def test_timeout_returns_json(self):
        """Verifies that timeout returns JSON error with expected message."""
        with patch("admin_routes._call_gemini_http", return_value=(None, "AI generation timed out. Please try again.")):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Process Scheduling",
                "qtype": "MCQ",
                "count": 2
            })
            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json, "Response must be JSON, never HTML!")
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertEqual(data["error"], "AI generation timed out. Please try again.")

    def test_provider_error_returns_json(self):
        """Verifies that provider error returns sanitized JSON error."""
        with patch("admin_routes._call_gemini_http", return_value=(None, "AI provider service is temporarily unavailable. Please try again later.")):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Process Scheduling",
                "qtype": "MCQ",
                "count": 2
            })
            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json, "Response must be JSON, never HTML!")
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("temporarily unavailable", data["error"])

    def test_successful_mcq_generation_format(self):
        """Verifies that successful MCQ generation returns exact expected JSON structure."""
        fake_ai_output = json.dumps([
            {
                "type": "MCQ",
                "question": "What is round-robin scheduling primarily designed to achieve?",
                "options": ["Maximum throughput", "Fair time-sharing", "Priority inversion", "Zero context switches"],
                "correct": "Fair time-sharing",
                "level": "Medium"
            }
        ])
        with patch("admin_routes._call_gemini_http", return_value=(fake_ai_output, None)):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "Computer Science",
                "program_code": "CSE",
                "admission_year": "2024",
                "academic_year": "3rd Year",
                "unit": "Unit 2",
                "topic": "CPU Scheduling",
                "qtype": "MCQ",
                "difficulty": "Medium",
                "count": 1
            })
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["course_code"], "CS301")
            self.assertEqual(data["program_code"], "CSE")

            q = data["questions"][0]
            self.assertEqual(q["type"], "MCQ")
            self.assertEqual(q["source"], "AI")
            self.assertEqual(q["correct"], "Fair time-sharing")
            self.assertEqual(len(q["options"]), 4)
            self.assertEqual(q["course_code"], "CS301")
            self.assertTrue(q["id"].startswith("Q-CS301-"))

    def test_successful_descriptive_generation_format(self):
        """Verifies that successful Descriptive generation returns exact expected JSON structure."""
        fake_ai_output = json.dumps([
            {
                "type": "DESCRIPTIVE",
                "question": "Explain deadlock conditions in modern operating systems.",
                "answer_key": "Mutual exclusion, Hold and wait, No preemption, Circular wait.",
                "max_marks": 5,
                "level": "Medium"
            }
        ])
        with patch("admin_routes._call_gemini_http", return_value=(fake_ai_output, None)):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "Computer Science",
                "program_code": "CSE",
                "admission_year": "2024",
                "academic_year": "3rd Year",
                "unit": "Unit 3",
                "topic": "Deadlocks",
                "qtype": "DESCRIPTIVE",
                "difficulty": "Medium",
                "count": 1
            })
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 1)

            q = data["questions"][0]
            self.assertEqual(q["type"], "DESCRIPTIVE")
            self.assertEqual(q["source"], "AI")
            self.assertIn("Circular wait", q["answer_key"])
            self.assertEqual(q["max_marks"], 5)

    def test_save_generated_questions_workflow(self):
        """Verifies that generated questions can still be saved to Question Bank via api_save_generated."""
        import utils
        sample_questions = [
            {
                "id": "Q-TEST-99999",
                "course_code": "TEST101",
                "course_name": "Testing Course",
                "subject": "Automated Testing",
                "program_code": "CSE",
                "admission_year": 2024,
                "academic_year": "3rd Year",
                "unit": "Unit 1",
                "topic": "Unit Tests",
                "type": "MCQ",
                "level": "Easy",
                "question": "What is unit testing?",
                "options": ["Testing code units", "Testing whole app", "Manual QA", "Stress test"],
                "correct": "Testing code units"
            }
        ]
        
        # Test saving
        orig_questions = utils.load_questions()
        try:
            res = self.client.post("/admin/api_save_generated", json={"questions": sample_questions})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["saved_count"], 1)

            # Verify saved in list
            updated = utils.load_questions()
            found = any(q.get("id") == "Q-TEST-99999" for q in updated)
            self.assertTrue(found, "Saved question must be present in questions.json!")
        finally:
            # Clean up test question
            utils.save_json("questions.json", [q for q in utils.load_questions() if q.get("id") != "Q-TEST-99999"])

if __name__ == "__main__":
    unittest.main()
