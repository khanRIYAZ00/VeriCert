import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("VERICERT_DATABASE_URL", "sqlite:///./vericert.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_database() -> None:
    Path("storage/templates").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # `create_all` does not alter an existing SQLite database. Keep this small
    # migration here so installations made before roll-number downloads continue
    # to work without a manual database reset.
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("issuances")}
    with engine.begin() as connection:
        if "roll_number" not in columns:
            connection.execute(text("ALTER TABLE issuances ADD COLUMN roll_number VARCHAR(128)"))
        indexes = inspect(connection).get_indexes("issuances")
        for index in indexes:
            if index.get("column_names") == ["roll_number"]:
                connection.execute(text(f'DROP INDEX IF EXISTS "{index["name"]}"'))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_issuances_roll_number ON issuances (roll_number)"))
