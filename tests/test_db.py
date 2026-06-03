"""Tests for SQLAlchemy database layer."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from peerpedia_core.storage.db import (
    Article,
    Base,
    get_engine,
    get_session,
    init_db,
    create_article,
    get_article,
    list_articles,
    ArticleStatus,
)


class TestArticleModel:
    """SQLAlchemy Article model must store and retrieve fields."""

    def test_article_table_creation(self):
        """init_db should create the articles table."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            assert "articles" in tables

    def test_create_and_get_article(self):
        """Create an article and retrieve it by ID."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            article = create_article(
                session,
                title="Test Article",
                founding_authors=["user-1"],
                abstract="A test abstract.",
                categories=["physics", "math"],
                keywords=["test"],
                language="en",
                format="typst",
                git_repo_path="/tmp/articles/test-1",
            )
            session.commit()

            assert article.id is not None
            assert article.title == "Test Article"
            assert article.status == ArticleStatus.DRAFT

            retrieved = get_article(session, article.id)
            assert retrieved is not None
            assert retrieved.title == "Test Article"
            assert retrieved.founding_authors == ["user-1"]
            assert retrieved.categories == ["physics", "math"]

    def test_list_articles(self):
        """list_articles should return all articles ordered by created_at desc."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            a1 = create_article(
                session, title="First", founding_authors=["u1"],
                abstract="First article.", git_repo_path="/tmp/a1",
            )
            a2 = create_article(
                session, title="Second", founding_authors=["u2"],
                abstract="Second article.", git_repo_path="/tmp/a2",
            )
            session.commit()

            articles = list_articles(session)
            assert len(articles) == 2
            assert articles[0].title == "Second"
            assert articles[1].title == "First"

    def test_list_articles_empty(self):
        """list_articles on empty DB returns empty list."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            articles = list_articles(session)
            assert articles == []

    def test_article_defaults(self):
        """Article model should have correct defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            article = create_article(
                session,
                title="Defaults Test",
                founding_authors=["u1"],
                abstract="Testing defaults.",
                git_repo_path="/tmp/defaults",
            )
            session.commit()

            assert article.status == ArticleStatus.DRAFT
            assert article.version == "v0.1"
            assert article.language == "en"
            assert article.format == "typst"
            assert article.categories == []
            assert article.keywords == []
            assert article.cid is None
            assert article.pinned_by == 0
            assert isinstance(article.created_at, datetime)
