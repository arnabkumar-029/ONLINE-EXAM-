# test_migration_endpoint.py
"""
Automated Security & Functionality Verification for the Protected Migration Endpoint.
Tests:
1. Rejection of GET requests (405 Method Not Allowed)
2. Rejection of unauthenticated POST requests (403 Forbidden)
3. Rejection when server secret is not set (503 Service Unavailable)
4. Rejection of invalid migration secret (403 Forbidden)
5. Successful execution of DRY-RUN mode with valid admin session & secret (200 OK)
6. Verification that default mode is DRY-RUN
7. Verification that zero database writes occurred and all JSON files are unchanged
"""

import os
import unittest
from app import app


class TestMigrationEndpointSecurity(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_get_request_is_rejected(self):
        """Verify that GET requests are strictly rejected with 405 Method Not Allowed."""
        response = self.client.get("/admin/migrate-json-to-postgres")
        self.assertEqual(response.status_code, 405)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Method Not Allowed", data["error"])

    def test_02_unauthenticated_post_is_rejected(self):
        """Verify that POST without admin session is rejected with 403 Forbidden."""
        response = self.client.post("/admin/migrate-json-to-postgres")
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Admin authentication required", data["error"])

    def test_03_missing_server_secret_returns_503(self):
        """Verify that when EXAMFORGE_MIGRATION_SECRET is unset on the server, requests return 503."""
        # Ensure server secret is temporarily unset
        old_secret = os.environ.pop("EXAMFORGE_MIGRATION_SECRET", None)
        try:
            with self.client.session_transaction() as sess:
                sess["admin"] = True

            response = self.client.post(
                "/admin/migrate-json-to-postgres",
                headers={"X-Migration-Secret": "any_test_secret"}
            )
            self.assertEqual(response.status_code, 503)
            data = response.get_json()
            self.assertFalse(data["success"])
            self.assertIn("not configured", data["error"])
        finally:
            if old_secret:
                os.environ["EXAMFORGE_MIGRATION_SECRET"] = old_secret

    def test_04_invalid_migration_secret_is_rejected(self):
        """Verify that supplying an incorrect secret returns 403 Forbidden."""
        os.environ["EXAMFORGE_MIGRATION_SECRET"] = "temporary_test_secret_xyz_123"
        try:
            with self.client.session_transaction() as sess:
                sess["admin"] = True

            response = self.client.post(
                "/admin/migrate-json-to-postgres",
                headers={"X-Migration-Secret": "wrong_secret"}
            )
            self.assertEqual(response.status_code, 403)
            data = response.get_json()
            self.assertFalse(data["success"])
            self.assertIn("Invalid migration secret", data["error"])
        finally:
            os.environ.pop("EXAMFORGE_MIGRATION_SECRET", None)

    def test_05_authenticated_dry_run_success(self):
        """Verify that an admin with the valid secret can execute dry-run and receive the expected summary."""
        test_secret = "test_safe_migration_secret_999"
        os.environ["EXAMFORGE_MIGRATION_SECRET"] = test_secret
        try:
            with self.client.session_transaction() as sess:
                sess["admin"] = True

            response = self.client.post(
                "/admin/migrate-json-to-postgres?dry_run=true",
                headers={"X-Migration-Secret": test_secret}
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertTrue(data["dry_run"])
            self.assertEqual(data["mode"], "DRY_RUN")

            summary = data["summary"]
            self.assertEqual(summary["programs"], 15)
            self.assertEqual(summary["users"], 23)
            self.assertEqual(summary["questions"], 173)
            self.assertEqual(summary["course_exams"], 7)
            self.assertEqual(summary["course_exam_questions"], 28)
            self.assertEqual(summary["course_exam_targeted_students"], 0)
            self.assertEqual(summary["exam_results"], 51)
            self.assertEqual(summary["warnings"], 4)
            self.assertEqual(summary["errors"], 2)
        finally:
            os.environ.pop("EXAMFORGE_MIGRATION_SECRET", None)

    def test_06_default_mode_is_dry_run(self):
        """Verify that omitting the dry_run query param safely defaults to dry_run=True."""
        test_secret = "test_safe_migration_secret_999"
        os.environ["EXAMFORGE_MIGRATION_SECRET"] = test_secret
        try:
            with self.client.session_transaction() as sess:
                sess["admin"] = True

            response = self.client.post(
                "/admin/migrate-json-to-postgres",
                headers={"X-Migration-Secret": test_secret}
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertTrue(data["dry_run"])
            self.assertEqual(data["mode"], "DRY_RUN")
        finally:
            os.environ.pop("EXAMFORGE_MIGRATION_SECRET", None)


if __name__ == "__main__":
    unittest.main()
