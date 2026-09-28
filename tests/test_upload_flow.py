import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app as library


class UploadFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = library.app.test_client()
        library.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.temporary_uploads = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temporary_uploads.name)
        self.user = {"role": "admin", "is_active": True}
        self.query_patch = patch.object(
            library,
            "query_one",
            side_effect=lambda sql, _values=(): self.user if "SELECT role" in sql else None,
        )
        self.query_patch.start()
        self.purge_patch = patch.object(library, "purge_expired_trash")
        self.purge_patch.start()
        self.connection = Mock()
        self.cursor = Mock()
        self.connection.cursor.return_value = self.cursor

    def tearDown(self):
        self.query_patch.stop()
        self.purge_patch.stop()
        self.temporary_uploads.cleanup()

    def set_admin_session(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 7
            sess["principal_id"] = 7
            sess["role"] = "admin"
            sess["last_activity_at"] = library.datetime.now().isoformat()

    def upload_file(self, filename, content_type):
        self.set_admin_session()
        with patch.object(library, "UPLOAD_FOLDER", self.upload_root), \
             patch.object(library, "get_db", return_value=self.connection), \
             patch.object(library, "record_audit_action"):
            response = self.client.post(
                "/upload",
                data={"file": (io.BytesIO(b"test file bytes"), filename, content_type)},
                headers={"X-Requested-With": "XMLHttpRequest"},
                content_type="multipart/form-data",
            )
        return response

    def assert_upload_succeeded(self, response, filename, expected_mime):
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["results"][0]["status"], "success")
        self.assertEqual(payload["results"][0]["name"], filename)
        stored_name = self.cursor.execute.call_args.args[1][2]
        self.assertTrue(stored_name.endswith("_" + filename))
        self.assertEqual(self.cursor.execute.call_args.args[1][4], expected_mime)
        self.assertTrue((self.upload_root / "7" / stored_name).is_file())

    def test_upload_accepts_jpg_image(self):
        response = self.upload_file("photo.jpg", "image/jpeg")
        self.assert_upload_succeeded(response, "photo.jpg", "image/jpeg")

    def test_upload_accepts_jpeg_image(self):
        response = self.upload_file("photo.jpeg", "image/jpeg")
        self.assert_upload_succeeded(response, "photo.jpeg", "image/jpeg")

    def test_upload_accepts_existing_pdf_file_type(self):
        response = self.upload_file("document.pdf", "application/pdf")
        self.assert_upload_succeeded(response, "document.pdf", "application/pdf")

    def test_configured_limit_is_enforced_by_upload_route(self):
        self.set_admin_session()
        with patch.object(library, "UPLOAD_FOLDER", self.upload_root), \
             patch.object(library, "get_db", return_value=self.connection), \
             patch.object(library, "current_upload_limit_mb", return_value=1):
            response = self.client.post(
                "/upload",
                data={"file": (io.BytesIO(b"x" * (1024 * 1024 + 1)), "large.jpg", "image/jpeg")},
                headers={"X-Requested-With": "XMLHttpRequest"},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["results"][0]["status"], "error")
        self.assertIn("1 MB", payload["results"][0]["message"])
        self.cursor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
