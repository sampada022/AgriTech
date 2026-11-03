"""One SQLite file via SQLModel. WAL lets pollers read while the analysis worker writes.

The path is derived from settings.data_dir (not a frozen constant), so tests can redirect it to a
throwaway folder by setting DATA_DIR before the app is imported.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings


def db_file() -> Path:
    return Path(os.environ.get("AGRISCOUT_DB") or (get_settings().data_dir / "agriscout.db"))


def reports_dir() -> Path:
    return get_settings().data_dir / "reports"  # PDF farmer reports, one stored file per generated version


# Back-compat name some modules still import directly; resolved once, which is fine because the
# process only ever runs under one settings configuration.
REPORTS = reports_dir()


@lru_cache
def get_engine() -> Engine:
    get_settings().data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_file()}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )

    @event.listens_for(engine, "connect")
    def _configure(connection, _record):  # noqa: ANN001
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


# Back-compat name: most of this codebase's existing modules import `engine` directly.
engine = get_engine()


def create_tables() -> None:
    from . import aero_models, models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(get_engine())
    REPORTS.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """Back-compat alias for the old entry point name."""
    create_tables()


def new_session() -> Session:
    return Session(get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with new_session() as session:
        yield session
