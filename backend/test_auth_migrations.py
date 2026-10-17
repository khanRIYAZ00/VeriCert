import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sqlalchemy import create_engine, text


class AuthMigrationTests(unittest.TestCase):
    def test_legacy_passwords_are_invalidated_and_accounts_can_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy.db"
            engine = create_engine(f"sqlite:///{database_path}")
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE TABLE users ("
                        "id INTEGER PRIMARY KEY, "
                        "email VARCHAR(255) NOT NULL UNIQUE, "
                        "password_hash VARCHAR(255) NOT NULL, "
                        "is_platform_admin BOOLEAN NOT NULL DEFAULT 0, "
                        "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO users (id, email, password_hash, is_platform_admin) "
                        "VALUES (1, 'legacy-admin@example.test', 'old-salt$legacy-digest', 1)"
                    )
                )
            engine.dispose()

            environment = os.environ.copy()
            environment["VERICERT_DATABASE_URL"] = f"sqlite:///{database_path}"
            environment["VERICERT_TOKEN_SECRET"] = "migration-test-secret-at-least-32-bytes"
            project_root = Path(__file__).resolve().parent.parent
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from backend.database import init_database; init_database(); init_database()",
                ],
                cwd=project_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            engine = create_engine(f"sqlite:///{database_path}")
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        "SELECT password_hash, must_change_password, token_version, role, "
                        "is_active, email_verified FROM users WHERE id = 1"
                    )
                ).one()
                revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                reset_table_exists = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM sqlite_master "
                        "WHERE type = 'table' AND name = 'password_reset_tokens'"
                    )
                ).scalar_one()

            self.assertTrue(row.password_hash.startswith("$argon2id$"))
            self.assertTrue(row.must_change_password)
            self.assertEqual(row.token_version, 1)
            self.assertEqual(row.role, "platform_admin")
            self.assertTrue(row.is_active)
            self.assertFalse(row.email_verified)
            self.assertEqual(revision, "20261015_01")
            self.assertEqual(reset_table_exists, 1)


if __name__ == "__main__":
    unittest.main()
