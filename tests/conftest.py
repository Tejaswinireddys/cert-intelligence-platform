"""Test fixtures — fresh in-memory SQLite per test session."""
import os
import tempfile

import pytest

os.environ.setdefault("CIP_MODE", "MOCK")


@pytest.fixture(autouse=True, scope="session")
def _db():
    # Use a temp-file SQLite so all sessions share the same DB within the run.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["CIP_DATABASE_URL"] = f"sqlite:///{path}"

    from cip.config import get_settings
    get_settings.cache_clear()

    from cip import db
    db.init_engine(f"sqlite:///{path}")
    db.create_all()
    yield
    try:
        os.remove(path)
    except OSError:
        pass
