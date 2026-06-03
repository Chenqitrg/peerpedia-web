"""Shared database session helper for web routes."""

from peerpedia.config.settings import settings
from peerpedia_core.storage.db import get_engine, get_session, init_db


def get_db_session():
    """Get a database session, ensuring tables exist.

    Used by both API routes and page handlers. Each caller is responsible
    for closing the session (use try/finally or context manager).
    """
    engine = get_engine(settings.database_url)
    init_db(engine)
    return get_session(engine)
