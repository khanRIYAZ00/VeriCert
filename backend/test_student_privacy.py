import os
import tempfile
import unittest

from fastapi.testclient import TestClient

fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["VERICERT_DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ.setdefault("VERICERT_TOKEN_SECRET", "test-only-secret-with-at-least-32-bytes")

from .auth import hash_password
from .database import SessionLocal, init_database
from .main import app, rate_limiter
from .models import Club, Event, Issuance, PasswordResetToken, SecurityAuditLog, TemplateVersion, User


class StudentPrivacyTests(unittest.TestCase):
    def setUp(self):
        init_database()

        db = SessionLocal()
        try:
            db.query(PasswordResetToken).delete()
            db.query(SecurityAuditLog).delete()
            db.query(Issuance).delete()
            db.query(Event).delete()
            db.query(TemplateVersion).delete()
            db.query(Club).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()

        self.client = TestClient(app)

        db = SessionLocal()
        try:
            admin = User(
                email="admin@vericert.local",
                password_hash=hash_password("A-Strong-Admin-Password!23"),
                is_platform_admin=True,
                role="platform_admin",
            )
            db.add(admin)
            db.commit()

            club = Club(name="Computer Science")
            db.add(club)
            db.commit()
            db.refresh(club)

            template = TemplateVersion(
                club_id=club.id,
                name="Certificate Template",
                version=1,
                status="published",
                artwork_key="8ef6e2242f074606a1465a83c8cfb886.png",
                artwork_mime="image/png",
                page_width=8.27,
                page_height=11.69,
                field_definitions=[],
                layout=[{
                    "key": "recipient_name",
                    "x": 0.14,
                    "y": 0.72,
                    "width": 0.5,
                    "height": 0.08,
                    "font_size": 20,
                    "bold": True,
                    "align": "left",
                }],
                created_by=1,
            )
            db.add(template)
            db.commit()
            db.refresh(template)

            event = Event(
                club_id=club.id,
                name="Tech Fest 2026",
                template_version_id=template.id,
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            student = User(
                email="23cse104@aiktc.ac.in",
                student_login="23cse104@aiktc.ac.in",
                roll_number="23CSE104",
                password_hash=hash_password("StrongPass!23"),
                email_verified=True,
                role="student",
            )
            db.add(student)
            db.commit()
            db.refresh(student)
            self.student_id = student.id
            self.admin_id = admin.id

            issuance = Issuance(
                credential_id="cred-student-001",
                club_id=club.id,
                event_id=event.id,
                template_version_id=template.id,
                recipient_email="23cse104@aiktc.ac.in",
                roll_number="23CSE104",
                recipient_values={"recipient_name": "Student Test"},
                credential_package={
                    "credential": {
                        "credential_id": "cred-student-001",
                        "issue_date": "2026-09-18",
                        "club": {"name": club.name},
                        "event": {"name": event.name},
                        "recipient": {"recipient_name": "Student Test"},
                    },
                    "hash": "dummy-hash",
                    "signature": "dummy-signature",
                },
                status="issued",
                issued_by=student.id,
            )
            db.add(issuance)
            db.commit()
        finally:
            db.close()

    def test_password_hashing_uses_argon2id_only(self):
        encoded = hash_password("Long-enough-password!42")
        self.assertTrue(encoded.startswith("$argon2id$"))
        from .auth import verify_password

        self.assertTrue(verify_password("Long-enough-password!42", encoded))
        self.assertFalse(verify_password("wrong-password", encoded))
        auth_source = (os.path.dirname(__file__) + "/auth.py")
        with open(auth_source, encoding="utf-8") as auth_file:
            source = auth_file.read().lower()
        self.assertNotIn("pbk" + "df2_hmac", source)

    def test_anonymous_roll_number_lookup_is_rejected(self):
        response = self.client.get("/certificates/download?roll_no=23CSE104")
        self.assertEqual(response.status_code, 401)

    def test_student_login_and_private_download_work(self):
        login_response = self.client.post(
            "/auth/login",
            json={"email": "23cse104@aiktc.ac.in", "password": "StrongPass!23"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        token = login_response.json()["token"]

        response = self.client.get(
            "/certificates/download?roll_no=23CSE104",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["credential_id"], "cred-student-001")
        self.assertEqual(payload[0]["event"], "Tech Fest 2026")
        self.assertEqual(payload[0]["club"], "Computer Science")

        private_download = self.client.get(
            "/certificates/1/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(private_download.status_code, 200, private_download.text)

    def test_authenticated_student_with_no_certificates_gets_empty_list(self):
        login_response = self.client.post(
            "/auth/login",
            json={"email": "23cse104@aiktc.ac.in", "password": "StrongPass!23"},
        )
        token = login_response.json()["token"]
        db = SessionLocal()
        try:
            db.query(Issuance).delete()
            db.commit()
        finally:
            db.close()
        response = self.client.get(
            "/certificates/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    def test_private_download_requires_authentication(self):
        response = self.client.get("/certificates/1/download")
        self.assertEqual(response.status_code, 401)

    def test_temporary_password_requires_password_change_and_revokes_old_token(self):
        admin_login = self.client.post(
            "/auth/login",
            json={"email": "admin@vericert.local", "password": "A-Strong-Admin-Password!23"},
        )
        admin_token = admin_login.json()["token"]
        created = self.client.post(
            "/admin/students",
            json={
                "email": "24cse200@aiktc.ac.in",
                "roll_number": "24CSE200",
                "email_verified": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        temporary_password = created.json()["temporary_password"]
        self.assertTrue(temporary_password)

        login = self.client.post(
            "/auth/login",
            json={"email": "24cse200@aiktc.ac.in", "password": temporary_password},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertTrue(login.json()["user"]["must_change_password"])
        old_token = login.json()["token"]
        denied = self.client.get("/clubs", headers={"Authorization": f"Bearer {old_token}"})
        self.assertEqual(denied.status_code, 403)

        changed = self.client.post(
            "/auth/change-password",
            json={"current_password": temporary_password, "new_password": "A-new-student-password!42"},
            headers={"Authorization": f"Bearer {old_token}"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        revoked = self.client.get("/clubs", headers={"Authorization": f"Bearer {old_token}"})
        self.assertEqual(revoked.status_code, 401)

        fresh_login = self.client.post(
            "/auth/login",
            json={"email": "24cse200@aiktc.ac.in", "password": "A-new-student-password!42"},
        )
        self.assertEqual(fresh_login.status_code, 200, fresh_login.text)
        self.assertFalse(fresh_login.json()["user"]["must_change_password"])

    def test_student_cannot_provision_accounts_and_deactivation_revokes_sessions(self):
        student_login = self.client.post(
            "/auth/login",
            json={"email": "23cse104@aiktc.ac.in", "password": "StrongPass!23"},
        )
        student_token = student_login.json()["token"]
        denied = self.client.post(
            "/admin/students",
            json={"email": "new@aiktc.ac.in", "roll_number": "NEW100"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        self.assertEqual(denied.status_code, 403)

        admin_login = self.client.post(
            "/auth/login",
            json={"email": "admin@vericert.local", "password": "A-Strong-Admin-Password!23"},
        )
        admin_token = admin_login.json()["token"]
        deactivated = self.client.post(
            f"/admin/students/{self.student_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        stale_session = self.client.get("/certificates/download", headers={"Authorization": f"Bearer {student_token}"})
        self.assertEqual(stale_session.status_code, 401)
        blocked_login = self.client.post(
            "/auth/login",
            json={"email": "23cse104@aiktc.ac.in", "password": "StrongPass!23"},
        )
        self.assertEqual(blocked_login.status_code, 403)

    def test_password_reset_is_hashed_single_use_and_revokes_sessions(self):
        import backend.main as main_module

        emailed_tokens = []
        original_sender = main_module.send_password_reset_email
        main_module.send_password_reset_email = lambda email, token: emailed_tokens.append(token)
        original_host = os.environ.get("VERICERT_SMTP_HOST")
        os.environ["VERICERT_SMTP_HOST"] = "smtp.test.invalid"
        try:
            login = self.client.post(
                "/auth/login",
                json={"email": "23cse104@aiktc.ac.in", "password": "StrongPass!23"},
            )
            old_token = login.json()["token"]
            requested = self.client.post(
                "/auth/forgot-password",
                json={"email": "23cse104@aiktc.ac.in"},
            )
            self.assertEqual(requested.status_code, 200, requested.text)
            self.assertEqual(len(emailed_tokens), 1)
            raw_token = emailed_tokens[0]

            db = SessionLocal()
            try:
                stored = db.query(PasswordResetToken).one()
                import hashlib

                self.assertEqual(stored.token_hash, hashlib.sha256(raw_token.encode()).hexdigest())
                self.assertNotIn(raw_token, stored.token_hash)
            finally:
                db.close()

            reset = self.client.post(
                "/auth/reset-password",
                json={"token": raw_token, "new_password": "Reset-student-password!42"},
            )
            self.assertEqual(reset.status_code, 200, reset.text)
            reused = self.client.post(
                "/auth/reset-password",
                json={"token": raw_token, "new_password": "Another-reset-password!43"},
            )
            self.assertEqual(reused.status_code, 400)
            stale_session = self.client.get("/clubs", headers={"Authorization": f"Bearer {old_token}"})
            self.assertEqual(stale_session.status_code, 401)
        finally:
            main_module.send_password_reset_email = original_sender
            if original_host is None:
                os.environ.pop("VERICERT_SMTP_HOST", None)
            else:
                os.environ["VERICERT_SMTP_HOST"] = original_host


if __name__ == "__main__":
    unittest.main()
