import unittest
from unittest.mock import patch

import app as library


class SuperAdminAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = library.app.test_client()
        library.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.users = {
            1: {"role": "super-admin", "is_active": True},
            2: {"role": "admin", "is_active": True},
            3: {"role": None, "is_active": True},
            4: {"role": "admin", "is_active": False},
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


if __name__ == "__main__":
    unittest.main()
