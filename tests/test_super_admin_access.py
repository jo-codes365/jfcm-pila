import unittest
from unittest.mock import patch

import app as library
from flask import Response


class SuperAdminAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = library.app.test_client()
        library.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.users = {
            1: {"role": "super-admin", "is_active": True},
            2: {"role": "admin", "is_active": True},
            3: {"role": None, "is_active": True},
            4: {"role": "admin", "is_active": False},
            5: {"role": None, "is_active": True},
        }
        self.query_patch = patch.object(library, "query_one", side_effect=self.query_one)
        self.query_patch.start()
        self.all_patch = patch.object(library, "query_all", return_value=[])
        self.all_patch.start()
        self.purge_patch = patch.object(library, "purge_expired_trash")
        self.purge_patch.start()

    def tearDown(self):
        self.query_patch.stop()
        self.all_patch.stop()
        self.purge_patch.stop()

    def query_one(self, sql, values=()):
        user_id = values[0] if values else None
        user = self.users.get(user_id)
        if "role" in sql and user:
            return user
        if "SELECT id FROM users" in sql and user:
            return {"id": user_id}
        return None

    def set_identity(self, user_id, principal_id=None):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["principal_id"] = principal_id or user_id
            sess["role"] = self.users[principal_id or user_id]["role"]
            sess["last_activity_at"] = library.datetime.now().isoformat()

    def test_admin_cannot_open_super_admin_user_management(self):
        self.set_identity(2)
        response = self.client.get("/admin/users")
        self.assertEqual(response.status_code, 403)

    def test_public_viewer_cannot_open_authenticated_route(self):
        self.set_identity(3)
        response = self.client.post("/settings/theme", data={"theme": "dark"})
        self.assertEqual(response.status_code, 403)

    def test_deactivated_session_is_invalidated(self):
        self.set_identity(4)
        response = self.client.post("/settings/theme", data={"theme": "dark"})
        self.assertEqual(response.status_code, 403)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_super_admin_can_select_owner_without_changing_principal(self):
        self.set_identity(1)
        response = self.client.post("/admin/users/2/workspace")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], 2)
            self.assertEqual(sess["principal_id"], 1)

    def test_create_user_accepts_optional_email_and_unrestricted_username(self):
        self.set_identity(1)
        cursor = unittest.mock.Mock()
        connection = unittest.mock.Mock()
        connection.cursor.return_value = cursor
        with patch.object(library, "get_db", return_value=connection), \
             patch.object(library, "generate_password_hash", return_value="hashed"), \
             patch.object(library, "record_audit_action"):
            response = self.client.post("/admin/users", data={
                "username": "My user!",
                "password": "secret1",
                "confirm_password": "secret1",
                "role": "admin",
                "return_to_settings": "1",
            })
        self.assertEqual(response.status_code, 302)
        cursor.execute.assert_called_once()
        self.assertEqual(cursor.execute.call_args.args[1], (None, "My user!", "hashed", "admin"))

    def test_create_user_rejects_username_shorter_than_three_characters(self):
        self.set_identity(1)
        response = self.client.post("/admin/users", data={
            "username": "ab",
            "password": "secret1",
            "confirm_password": "secret1",
            "role": "admin",
            "return_to_settings": "1",
        })
        self.assertEqual(response.status_code, 302)

    def test_admin_search_lists_files_across_workspaces(self):
        self.set_identity(2)
        cursor = unittest.mock.Mock()
        cursor.fetchall.side_effect = [[], [{
            "id": 42,
            "original_filename": "report.pdf",
            "folder_id": None,
            "mime_type": "application/pdf",
        }], []]
        connection = unittest.mock.Mock()
        connection.cursor.return_value = cursor
        with patch.object(library, "get_db", return_value=connection):
            response = self.client.get("/search-suggestions?q=report")
        self.assertEqual(response.status_code, 200)
        file_query = next(call.args[0] for call in cursor.execute.call_args_list if "FROM files" in call.args[0])
        self.assertNotIn("user_id = %s", file_query)
        self.assertEqual(response.json["suggestions"][0]["name"], "report.pdf")

    def test_regular_user_search_stays_in_their_workspace(self):
        with library.app.test_request_context("/search-suggestions?q=report"):
            library.session["user_id"] = 5
            library.g.is_admin = False
            self.assertEqual(library.workspace_owner_scope(), 5)

    def test_admin_can_download_another_users_file_by_id(self):
        self.set_identity(2)
        record = {"id": 42, "user_id": 99, "stored_filename": "stored.pdf", "original_filename": "report.pdf"}
        with patch.object(library, "file_record", return_value=record), \
             patch.object(library, "record_path", return_value=library.Path("/mock/report.pdf")), \
             patch.object(library.Path, "is_file", return_value=True), \
             patch.object(library, "send_from_directory", return_value=Response("download")), \
             patch.object(library, "record_audit_action"):
            response = self.client.get("/download/42")
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_download_another_users_file_by_id(self):
        record = {"id": 42, "user_id": 99, "stored_filename": "stored.pdf", "original_filename": "report.pdf"}
        with library.app.test_request_context("/download/42"):
            library.session["user_id"] = 5
            library.g.is_admin = False
            with patch.object(library, "file_record", return_value=record):
                self.assertIsNone(library.accessible_file(42))

    def test_workspace_member_can_download_their_file_by_id(self):
        record = {"id": 42, "user_id": 5, "stored_filename": "stored.pdf", "original_filename": "report.pdf"}
        with library.app.test_request_context("/download/42"):
            library.session["user_id"] = 5
            library.g.is_admin = False
            with patch.object(library, "file_record", return_value=record):
                self.assertIsNotNone(library.accessible_file(42))


if __name__ == "__main__":
    unittest.main()
