import unittest
import json
import re
from unittest.mock import patch, MagicMock
from app import create_app
import utils

class TestBatchGeneration(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Save snapshot of questions for clean restore
        self._orig_questions = list(utils.load_questions())

        # Simulate admin login session
        with self.client.session_transaction() as sess:
            sess["admin"] = True
            sess["user_id"] = "ADMIN001"

    def tearDown(self):
        # Restore questions snapshot
        utils.save_json("questions.json", self._orig_questions)
        utils.reload_questions_from_disk()

    def test_case_1_count_5(self):
        """Case 1: Count = 5 -> Generate 5 -> Preview 5 -> Save once."""
        call_count = 0
        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal call_count
            call_count += 1
            items = [{
                "type": "MCQ",
                "question": f"Case 1 Question {i+1} on OS Processes?",
                "options": ["Process A", "Process B", "Process C", "Process D"],
                "correct": "Process A",
                "level": "Easy"
            } for i in range(5)]
            return json.dumps(items), None

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Process Management",
                "qtype": "MCQ",
                "count": 5
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 5)
            self.assertEqual(len(data["questions"]), 5)
            self.assertEqual(call_count, 1) # 1 batch of 5

            # Save once
            save_res = self.client.post("/admin/api_save_generated", json={"questions": data["questions"]})
            self.assertEqual(save_res.status_code, 200)
            save_data = save_res.get_json()
            self.assertTrue(save_data["success"])
            self.assertEqual(save_data["saved_count"], 5)
            self.assertIn("5 questions saved successfully", save_data["message"])

    def test_case_2_count_10(self):
        """Case 2: Count = 10 -> Internally 2 x 5 -> Preview 10 -> Save once."""
        call_count = 0
        batch_sizes = []

        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal call_count
            call_count += 1
            match = re.search(r"Generate exactly (\d+)", prompt)
            if not match:
                match = re.search(r"Total:\s*(\d+)\s*questions", prompt)
            if match:
                batch_sizes.append(int(match.group(1)))

            items = [{
                "type": "MCQ",
                "question": f"Case 2 Question {(call_count-1)*5 + i + 1} on Threads?",
                "options": ["A", "B", "C", "D"],
                "correct": "A",
                "level": "Medium"
            } for i in range(5)]
            return json.dumps(items), None

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 2",
                "topic": "Multithreading",
                "qtype": "MCQ",
                "count": 10
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 10)
            self.assertEqual(len(data["questions"]), 10)
            self.assertEqual(call_count, 2) # 2 batches of 5
            self.assertEqual(batch_sizes, [5, 5])

            # Save once
            save_res = self.client.post("/admin/api_save_generated", json={"questions": data["questions"]})
            self.assertEqual(save_res.status_code, 200)
            save_data = save_res.get_json()
            self.assertTrue(save_data["success"])
            self.assertEqual(save_data["saved_count"], 10)
            self.assertIn("10 questions saved successfully", save_data["message"])

    def test_case_3_count_20(self):
        """Case 3: Count = 20 -> Internally 4 x 5 -> Preview 20 -> Save once."""
        call_count = 0
        batch_sizes = []

        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal call_count
            call_count += 1
            match = re.search(r"Generate exactly (\d+)", prompt)
            if not match:
                match = re.search(r"Total:\s*(\d+)\s*questions", prompt)
            if match:
                batch_sizes.append(int(match.group(1)))

            items = [{
                "type": "MCQ",
                "question": f"Case 3 Question {(call_count-1)*5 + i + 1} on Deadlocks?",
                "options": ["Opt1", "Opt2", "Opt3", "Opt4"],
                "correct": "Opt1",
                "level": "Medium"
            } for i in range(5)]
            return json.dumps(items), None

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 3",
                "topic": "Deadlocks",
                "qtype": "MCQ",
                "count": 20
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 20)
            self.assertEqual(len(data["questions"]), 20)
            self.assertEqual(call_count, 4) # 4 batches of 5
            self.assertEqual(batch_sizes, [5, 5, 5, 5])

            # Save once
            save_res = self.client.post("/admin/api_save_generated", json={"questions": data["questions"]})
            self.assertEqual(save_res.status_code, 200)
            save_data = save_res.get_json()
            self.assertTrue(save_data["success"])
            self.assertEqual(save_data["saved_count"], 20)
            self.assertIn("20 questions saved successfully", save_data["message"])

    def test_case_4_count_50(self):
        """Case 4: Count = 50 -> Internally 10 x 5 -> Preview 50 -> Save once -> Confirm 50 added to Question Bank."""
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

            # 5 items per batch
            batch_items = []
            for i in range(5):
                q_num = (call_count - 1) * 5 + i + 1
                batch_items.append({
                    "type": "MCQ",
                    "question": f"Case 4 50-batch question {q_num} on AI in Robotics?",
                    "options": [f"Option A{q_num}", f"Option B{q_num}", f"Option C{q_num}", f"Option D{q_num}"],
                    "correct": f"Option A{q_num}",
                    "level": "Medium"
                })
            return json.dumps(batch_items), None

        initial_count = len(utils.load_questions())

        with patch("admin_routes._call_gemini_http", side_effect=mock_call_gemini):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "program_code": "CSE",
                "admission_year": "2024",
                "academic_year": "3rd Year",
                "unit": "Unit 5",
                "topic": "AI IN ROBOTICS",
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
            # Verify 10 calls of 5 made for 50 questions
            self.assertEqual(call_count, 10)
            self.assertEqual(batch_sizes_requested, [5] * 10)

            # Save once: all 50 saved in single operation
            save_res = self.client.post("/admin/api_save_generated", json={"questions": data["questions"]})
            self.assertEqual(save_res.status_code, 200)
            save_data = save_res.get_json()
            self.assertTrue(save_data["success"])
            self.assertEqual(save_data["saved_count"], 50)
            self.assertIn("50 questions saved successfully", save_data["message"])

            # Verify in Question Bank
            updated_questions = utils.load_questions()
            self.assertEqual(len(updated_questions), initial_count + 50)

    def test_batch_failure_reports_batch_number(self):
        """Test that failure in batch 3 returns clean JSON mentioning Batch 3 of 10."""
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
            } for i in range(5)]
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
            self.assertIn("Batch 3 of 10", data["error"])
            self.assertIn("timed out", data["error"].lower())

    def test_deduplication_and_topup_batch(self):
        """Test deduplication across batches triggers top-up to fulfill requested 10 questions."""
        batch_counter = 0

        def mock_call_gemini(prompt, api_key, model="gemini-2.5-flash", timeout=22.0):
            nonlocal batch_counter
            batch_counter += 1
            if batch_counter == 1:
                # 5 questions
                return json.dumps([
                    {
                        "type": "MCQ",
                        "question": f"Unique question {i}",
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "level": "Easy"
                    } for i in range(5)
                ]), None
            elif batch_counter == 2:
                # 3 unique, 2 duplicates from batch 1
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
                    } for i in range(3)
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
                "count": 10
            })

            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["count"], 10)
            self.assertEqual(len(data["questions"]), 10)
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

    def test_missing_api_key_returns_json(self):
        """Verifies missing API key returns a clean JSON error response."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Overview",
                "qtype": "MCQ",
                "count": 5
            })
            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("not configured", data["error"].lower())

    def test_malformed_ai_json_returns_clean_json(self):
        """Verifies unparseable garbage output from AI returns clean JSON error."""
        with patch("admin_routes._call_gemini_http", return_value=("NOT JSON AT ALL", None)):
            res = self.client.post("/admin/api_generate", json={
                "course_code": "CS301",
                "course_name": "Operating Systems",
                "subject": "CS",
                "unit": "Unit 1",
                "topic": "Overview",
                "qtype": "MCQ",
                "count": 5
            })
            self.assertEqual(res.status_code, 400)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertFalse(data["success"])
            self.assertIn("invalid", data["error"].lower())

    def test_gemini_rest_request_payload_format(self):
        """Verifies that _call_gemini_http configures gemini-3.7-flash with thinkingLevel: 'low' and responseMimeType."""
        import admin_routes
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "candidates": [{
                    "content": {
                        "parts": [{"text": json.dumps([{"question": "test"}])}]
                    }
                }]
            }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            text, err = admin_routes._call_gemini_http(
                prompt="test prompt",
                api_key="TEST_API_KEY",
                model="gemini-3.7-flash",
                timeout=22.0
            )
            self.assertIsNone(err)
            self.assertIsNotNone(text)

            # Inspect urllib.request.Request passed to urlopen
            call_args, call_kwargs = mock_urlopen.call_args
            req_obj = call_args[0]
            self.assertIn("gemini-3.7-flash", req_obj.full_url)
            self.assertIn("key=TEST_API_KEY", req_obj.full_url)
            
            payload = json.loads(req_obj.data.decode("utf-8"))
            gen_cfg = payload["generationConfig"]
            self.assertEqual(gen_cfg["responseMimeType"], "application/json")
            self.assertEqual(gen_cfg["thinkingConfig"]["thinkingLevel"], "low")

    def test_gemini_25_backward_compatibility(self):
        """Verifies backward compatibility for gemini-2.5-flash with thinkingBudget: 0."""
        import admin_routes
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "candidates": [{
                    "content": {
                        "parts": [{"text": json.dumps([{"question": "test"}])}]
                    }
                }]
            }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            text, err = admin_routes._call_gemini_http(
                prompt="test prompt",
                api_key="TEST_API_KEY",
                model="gemini-2.5-flash",
                timeout=22.0
            )
            self.assertIsNone(err)
            call_args, _ = mock_urlopen.call_args
            req_obj = call_args[0]
            payload = json.loads(req_obj.data.decode("utf-8"))
            self.assertEqual(payload["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0)

    def test_rate_limit_backoff_and_retry(self):
        """Verifies that HTTP 429 triggers exponential backoff and succeeds on retry."""
        import admin_routes
        import urllib.error

        attempts = 0
        def fake_urlopen(req, timeout=22.0):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                # Raise 429 HTTPError on attempts 1 and 2
                fp = MagicMock()
                fp.read.return_value = json.dumps({"error": {"message": "Rate limit exceeded", "details": [{"reason": "RESOURCE_EXHAUSTED"}]}}).encode("utf-8")
                headers = MagicMock()
                headers.get.return_value = None
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", headers, fp)
            else:
                # Succeed on attempt 3
                mock_resp = MagicMock()
                mock_resp.read.return_value = json.dumps({
                    "candidates": [{"content": {"parts": [{"text": json.dumps([{"question": "success"}])}]}}]
                }).encode("utf-8")
                mock_resp.__enter__.return_value = mock_resp
                return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep") as mock_sleep:
            text, err = admin_routes._call_gemini_http("test", "TEST_KEY", model="gemini-3.7-flash")
            self.assertIsNone(err)
            self.assertIsNotNone(text)
            self.assertEqual(attempts, 3)
            # Verify exponential backoff calls: 1.0s, 2.0s
            self.assertEqual(mock_sleep.call_count, 2)
            self.assertEqual(mock_sleep.call_args_list[0][0][0], 1.0)
            self.assertEqual(mock_sleep.call_args_list[1][0][0], 2.0)

    def test_rate_limit_respects_retry_after_header(self):
        """Verifies that HTTP 429 respects Retry-After header when present."""
        import admin_routes
        import urllib.error

        attempts = 0
        def fake_urlopen(req, timeout=22.0):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                fp = MagicMock()
                fp.read.return_value = json.dumps({"error": {"message": "Rate limit exceeded"}}).encode("utf-8")
                headers = MagicMock()
                headers.get.side_effect = lambda k: "2.5" if k == "Retry-After" else None
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", headers, fp)
            else:
                mock_resp = MagicMock()
                mock_resp.read.return_value = json.dumps({
                    "candidates": [{"content": {"parts": [{"text": json.dumps([{"question": "success"}])}]}}]
                }).encode("utf-8")
                mock_resp.__enter__.return_value = mock_resp
                return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep") as mock_sleep:
            text, err = admin_routes._call_gemini_http("test", "TEST_KEY", model="gemini-3.7-flash")
            self.assertIsNone(err)
            self.assertEqual(attempts, 2)
            mock_sleep.assert_called_once_with(2.5)

    def test_rate_limit_max_retries_exceeded(self):
        """Verifies that exceeding 3 retries stops and returns clean rate limit error."""
        import admin_routes
        import urllib.error

        attempts = 0
        def fake_urlopen(req, timeout=22.0):
            nonlocal attempts
            attempts += 1
            fp = MagicMock()
            fp.read.return_value = json.dumps({"error": {"message": "Rate limit exceeded"}}).encode("utf-8")
            headers = MagicMock()
            headers.get.return_value = None
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", headers, fp)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep"):
            text, err = admin_routes._call_gemini_http("test", "TEST_KEY", model="gemini-3.7-flash")
            self.assertIsNone(text)
            self.assertIn("rate limit reached", err.lower())
            # 1 initial + 3 retries = 4 total attempts
            self.assertEqual(attempts, 4)

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
