"""Tests for article submission orchestrator."""
import pytest
import tempfile
from pathlib import Path

from peerpedia.submit import (
    submit_article,
    SubmissionResult,
)


SIMPLE_TYPST = """---
title: A Simple Test Article
abstract: Just testing the submission pipeline.
categories:
  - test
  - physics
keywords:
  - submission
  - test
language: en
---

= A Simple Test Article

== Introduction

This is a test article for the submission pipeline.

== Main Result

We find that $E = mc^2$ is correct.
"""


class TestSubmitArticle:
    """End-to-end article submission tests."""

    def test_submit_typst_article(self):
        """Submit a Typst article — creates git repo + DB entry."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source_file = base / "test.typ"
            source_file.write_text(SIMPLE_TYPST)

            result = submit_article(
                source_path=source_file,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            assert isinstance(result, SubmissionResult)
            assert result.success is True
            assert result.article_id is not None
            assert result.title == "A Simple Test Article"
            assert result.git_commit_hash is not None

            # Git repo should exist
            repo_path = articles_dir / result.article_id
            assert repo_path.exists()
            assert (repo_path / ".git").is_dir()

            # Source file should be in repo
            assert (repo_path / "test.typ").exists()

    def test_submit_article_stores_db_metadata(self):
        """After submission, metadata should be retrievable from DB."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source_file = base / "article.typ"
            source_file.write_text(SIMPLE_TYPST)

            result = submit_article(
                source_path=source_file,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            # Read from DB
            from peerpedia_core.storage.db import (
                get_engine, init_db, get_session, get_article,
            )
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)
            article = get_article(session, result.article_id)
            assert article is not None
            assert article.title == "A Simple Test Article"
            assert article.categories == ["test", "physics"]
            assert article.keywords == ["submission", "test"]
            assert article.format == "typst"

    def test_submit_article_extracts_frontmatter(self):
        """Metadata from frontmatter should be stored."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source_file = base / "test.typ"
            source_file.write_text(SIMPLE_TYPST)

            result = submit_article(
                source_path=source_file,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            assert result.title == "A Simple Test Article"
            assert result.abstract == "Just testing the submission pipeline."
            assert result.categories == ["test", "physics"]

    def test_submit_without_frontmatter_prompts(self):
        """Article without frontmatter should still submit (use filename as title)."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source_file = base / "notes.typ"
            source_file.write_text("= My Notes\n\nSome content without metadata.")

            result = submit_article(
                source_path=source_file,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            assert result.success is True
            assert result.article_id is not None
            # Falls back to filename
            assert result.title == "notes"

    def test_submit_markdown_article(self):
        """Submit a Markdown article."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            md_content = """---
title: Markdown Test
abstract: Testing markdown submission.
language: en
---

# Markdown Test

Some math: $E = mc^2$
"""
            source_file = base / "notes.md"
            source_file.write_text(md_content)

            result = submit_article(
                source_path=source_file,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            assert result.success is True
            assert result.format == "markdown"
            assert result.title == "Markdown Test"
