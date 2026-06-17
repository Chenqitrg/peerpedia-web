# SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
# SPDX-License-Identifier: CC-BY-NC-SA-4.0

"""Tests for article permission policy functions."""

from peerpedia_core.exceptions import ConflictError, NotAuthorizedError, NotFoundError
from peerpedia_core.policies.articles import (
    FORKABLE_STATUSES,
    PUBLIC_READABLE_STATUSES,
    assert_can_fork_article,
    assert_can_read_article,
    assert_can_sync_article,
    get_article_or_raise,
    visible_statuses_for_user,
)
from peerpedia_core.storage.db.engine import get_session
from peerpedia_core.storage.db.models import Article, ArticleAuthor, User


def _user(**kwargs):
    """Create a User with required fields filled in."""
    defaults = {"password_hash": "", "name": "Test User", "anonymous_name": "anon", "affiliation": "Test"}
    defaults.update(kwargs)
    return User(**defaults)


class TestVisibilityRules:
    def test_public_readable_includes_sedimentation_and_published(self):
        assert PUBLIC_READABLE_STATUSES == {"sedimentation", "published"}

    def test_forkable_statuses_is_published_only(self):
        assert FORKABLE_STATUSES == {"published"}

    def test_visible_statuses_anonymous(self):
        result = visible_statuses_for_user(None)
        assert result == {"sedimentation", "published"}

    def test_visible_statuses_authenticated(self):
        u = _user(username="test")
        result = visible_statuses_for_user(u)
        assert result == {"draft", "sedimentation", "published"}


class TestGetArticleOrRaise:
    def test_returns_article_when_exists(self, db_engine):
        s = get_session(db_engine)
        a = Article(id="a-exists", status="draft", fork_count=0)
        s.add(a)
        s.commit()

        result = get_article_or_raise(s, "a-exists")
        assert result.id == "a-exists"

    def test_raises_not_found_when_missing(self, db_engine):
        import pytest

        s = get_session(db_engine)
        with pytest.raises(NotFoundError, match="Article not found"):
            get_article_or_raise(s, "nonexistent")


class TestReadPermissions:
    def test_can_read_published_article(self, db_engine):
        s = get_session(db_engine)
        a = Article(id="a-pub", status="published", fork_count=0)
        s.add(a)
        s.commit()

        result = assert_can_read_article(s, "a-pub", None)
        assert result.id == "a-pub"

    def test_can_read_own_draft(self, db_engine):
        s = get_session(db_engine)
        u = _user(id="u-draft", username="draft_user")
        s.add(u)
        a = Article(id="a-draft", status="draft", fork_count=0)
        s.add(a)
        s.flush()
        s.add(ArticleAuthor(article_id="a-draft", author_id="u-draft", position=0))
        s.commit()

        result = assert_can_read_article(s, "a-draft", u)
        assert result.id == "a-draft"

    def test_cannot_read_others_draft(self, db_engine):
        import pytest

        s = get_session(db_engine)
        u = _user(id="u-other", username="other")
        s.add(u)
        a = Article(id="a-other-draft", status="draft", fork_count=0)
        s.add(a)
        s.commit()

        with pytest.raises(NotAuthorizedError, match="Article is private"):
            assert_can_read_article(s, "a-other-draft", u)


class TestWritePermissions:
    def test_author_can_sync(self, db_engine):
        s = get_session(db_engine)
        u = _user(id="u-sync", username="sync_user")
        s.add(u)
        a = Article(id="a-sync", status="draft", fork_count=0)
        s.add(a)
        s.flush()
        s.add(ArticleAuthor(article_id="a-sync", author_id="u-sync", position=0))
        s.commit()

        result = assert_can_sync_article(s, "a-sync", u)
        assert result.id == "a-sync"

    def test_non_author_cannot_sync(self, db_engine):
        import pytest

        s = get_session(db_engine)
        u = _user(id="u-nosync", username="no_sync")
        s.add(u)
        a = Article(id="a-nosync", status="draft", fork_count=0)
        s.add(a)
        s.commit()

        with pytest.raises(NotAuthorizedError):
            assert_can_sync_article(s, "a-nosync", u)


class TestForkPermissions:
    def test_can_fork_published(self, db_engine):
        s = get_session(db_engine)
        u = _user(id="u-fork", username="fork_user")
        s.add(u)
        a = Article(id="a-fork", status="published", fork_count=0)
        s.add(a)
        s.commit()

        result = assert_can_fork_article(s, "a-fork", u)
        assert result.id == "a-fork"

    def test_cannot_fork_draft(self, db_engine):
        import pytest

        s = get_session(db_engine)
        u = _user(id="u-nofork", username="no_fork")
        s.add(u)
        a = Article(id="a-nofork", status="draft", fork_count=0)
        s.add(a)
        s.commit()

        with pytest.raises(NotAuthorizedError, match="Only published articles can be forked"):
            assert_can_fork_article(s, "a-nofork", u)

    def test_cannot_fork_twice(self, db_engine):
        import pytest

        s = get_session(db_engine)
        u = _user(id="u-dup", username="dup_fork")
        s.add(u)
        a = Article(id="a-dup-fork", status="published", fork_count=0)
        s.add(a)
        s.flush()
        # Simulate an existing fork by the same user
        fork = Article(
            id="fork-existing",
            status="draft",
            fork_count=0,
            forked_from="a-dup-fork",
        )
        s.add(fork)
        s.flush()
        s.add(ArticleAuthor(article_id="fork-existing", author_id="u-dup", position=0))
        s.commit()

        with pytest.raises(ConflictError, match="Already forked"):
            assert_can_fork_article(s, "a-dup-fork", u)
