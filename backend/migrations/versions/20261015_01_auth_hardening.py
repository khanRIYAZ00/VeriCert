"""Add hardened account state and migrate legacy password records.

Revision ID: 20261015_01
Revises:
"""

import secrets

from alembic import op
from argon2 import PasswordHasher, Type
import sqlalchemy as sa
from sqlalchemy import inspect, text

from backend.database import Base
from backend import models  # noqa: F401

revision = "20261015_01"
down_revision = None
branch_labels = None
depends_on = None

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def _has_index(connection, name: str, unique: bool) -> bool:
    return any(
        index["name"] == name and bool(index.get("unique")) == unique
        for index in inspect(connection).get_indexes("users")
    )


def upgrade() -> None:
    connection = op.get_bind()
    Base.metadata.create_all(bind=connection)

    columns = {column["name"] for column in inspect(connection).get_columns("users")}
    additions = {
        "student_login": sa.Column("student_login", sa.String(255), nullable=True),
        "roll_number": sa.Column("roll_number", sa.String(128), nullable=True),
        "role": sa.Column("role", sa.String(32), nullable=False, server_default="student"),
        "is_active": sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        "email_verified": sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        "must_change_password": sa.Column(
            "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        "password_changed_at": sa.Column("password_changed_at", sa.DateTime(), nullable=True),
        "token_version": sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("users", column)

    connection.execute(
        text(
            "UPDATE users "
            "SET role = CASE WHEN is_platform_admin THEN 'platform_admin' ELSE 'student' END"
        )
    )
    connection.execute(
        text(
            "UPDATE users SET role = 'club_admin' "
            "WHERE is_platform_admin = FALSE "
            "AND id IN (SELECT DISTINCT user_id FROM memberships)"
        )
    )

    legacy_users = connection.execute(
        text("SELECT id FROM users WHERE password_hash NOT LIKE '$argon2id$%'")
    ).fetchall()
    for (user_id,) in legacy_users:
        replacement_hash = _password_hasher.hash(secrets.token_urlsafe(32))
        connection.execute(
            text(
                "UPDATE users SET password_hash = :password_hash, "
                "must_change_password = TRUE, token_version = token_version + 1 "
                "WHERE id = :user_id"
            ),
            {"password_hash": replacement_hash, "user_id": user_id},
        )

    if not _has_index(connection, "ix_users_student_login", unique=True):
        op.create_index("ix_users_student_login", "users", ["student_login"], unique=True)

    duplicate_roll_numbers = connection.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "SELECT roll_number FROM users "
            "WHERE roll_number IS NOT NULL "
            "GROUP BY lower(roll_number) HAVING COUNT(*) > 1"
            ")"
        )
    ).scalar_one()
    if duplicate_roll_numbers:
        raise RuntimeError(
            "Cannot enforce unique student identifiers: duplicate roll numbers exist. "
            "Resolve duplicates, then rerun the database migration."
        )
    if not _has_index(connection, "uq_users_roll_number", unique=True):
        op.create_index("uq_users_roll_number", "users", ["roll_number"], unique=True)

    if not any(
        index["name"] == "ix_users_role"
        for index in inspect(connection).get_indexes("users")
    ):
        op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    raise RuntimeError("The authentication hardening migration is irreversible.")
