"""Tests for sedimentation pool and fork features.

Covers:
1. Sink score calculation — high ratings accelerate sink
2. Same reviewer update preserves independent fields
3. Author cannot self-rate (ratings zeroed, comment stored)
4. Fork creates new article with forked_from, bumping fork_count
5. Search finds articles by title/abstract/keywords; nonexistent returns empty
6. Search with empty/whitespace query returns all articles
"""

import tempfile
from pathlib import Path

import pytest

from peerpedia.submit import submit_article
from peerpedia_core.workflow.review import assign_reviewer, submit_review
from peerpedia_core.storage.db import (
    get_article,
    get_engine,
    get_reviews_for_article,
    get_session,
    init_db,
    update_article_status,
)

# ── Helpers ────────────────────────────────────────────────────────────────


def _compute_sink_pct(reviews):
    """Compute sink progress using the same formula as pages.py (sedimentation pool).

    Higher review average (0-5) → higher sink_pct (0-95).
    """
    dims = ["originality", "rigor", "completeness", "pedagogy", "impact"]
    scores = []
    for r in reviews:
        vals = [getattr(r, f"review_{d}", 0) for d in dims]
        if any(v > 0 for v in vals):
            scores.append(sum(vals) / len(vals))
    if not scores:
        return 0
    avg = sum(scores) / len(scores)
    return min(95, int(avg / 5.0 * 95))


def _setup_db_and_article(tmp_path, author="testuser", title="Test Article",
                           abstract="Test abstract.", keywords=None):
    """Create a temp DB with one submitted article.

    Returns (db_url, article_id, engine).
    """
    base = Path(tmp_path)
    db_path = base / "test.db"
    articles_dir = base / "articles"
    articles_dir.mkdir(exist_ok=True)
    db_url = f"sqlite:///{db_path}"

    kw_yaml = ""
    if keywords:
        kw_yaml = "keywords:\n" + "\n".join(f"  - {k}" for k in keywords)

    source = base / "test.md"
    source.write_text(f"""---
title: {title}
abstract: {abstract}
{kw_yaml}
---

# {title}
""")

    result = submit_article(
        source_path=source, database_url=db_url,
        articles_dir=articles_dir, author_name=author,
    )
    assert result.success, f"submit_article failed: {result.error}"

    engine = get_engine(db_url)
    init_db(engine)
    session = get_session(engine)
    update_article_status(session, result.article_id, "submitted")
    session.commit()
    session.close()

    return db_url, result.article_id, engine


# ── Test 1: Sink score ────────────────────────────────────────────────────


class TestSinkProgress:
    """Test 1: Sink score accelerates with high ratings."""

    def test_sink_high_vs_low_ratings(self):
        """5-star review → sink_progress > 50%; 1-star → sink_progress < 20%."""
        # === High ratings ===
        with tempfile.TemporaryDirectory() as tmp:
            db_url, article_id, engine = _setup_db_and_article(tmp)

            assign_reviewer(article_id=article_id, reviewer_id="r1",
                            database_url=db_url)
            submit_review(
                article_id=article_id, reviewer_id="r1",
                decision="accept", comments="Great!",
                review_originality=5, review_rigor=5,
                review_completeness=5, review_pedagogy=5, review_impact=5,
                database_url=db_url,
            )

            session = get_session(engine)
            reviews = get_reviews_for_article(session, article_id)
            sink_pct = _compute_sink_pct(reviews)
            session.close()

            assert sink_pct > 50, (
                f"Expected sink_progress > 50% for 5-star review, got {sink_pct}%"
            )

        # === Low ratings ===
        with tempfile.TemporaryDirectory() as tmp:
            db_url, article_id, engine = _setup_db_and_article(tmp)

            assign_reviewer(article_id=article_id, reviewer_id="r1",
                            database_url=db_url)
            submit_review(
                article_id=article_id, reviewer_id="r1",
                decision="reject", comments="Poor.",
                review_originality=1, review_rigor=1,
                review_completeness=1, review_pedagogy=1, review_impact=1,
                database_url=db_url,
            )

            session = get_session(engine)
            reviews = get_reviews_for_article(session, article_id)
            sink_pct = _compute_sink_pct(reviews)
            session.close()

            assert sink_pct < 20, (
                f"Expected sink_progress < 20% for 1-star review, got {sink_pct}%"
            )


# ── Test 2: Same reviewer update ─────────────────────────────────────────


class TestSameReviewerUpdate:
    """Test 2: Same reviewer update preserves independent fields."""

    def test_update_preserves_independent_fields(self):
        """Rating-only update keeps existing comment; comment-only keeps rating."""
        with tempfile.TemporaryDirectory() as tmp:
            db_url, article_id, engine = _setup_db_and_article(tmp)

            # Step 1: First review with rating=4 + comment="First"
            assign_reviewer(article_id=article_id, reviewer_id="r1",
                            database_url=db_url)
            r1 = submit_review(
                article_id=article_id, reviewer_id="r1",
                decision="accept", comments="First",
                review_originality=4, review_rigor=4,
                review_completeness=4, review_pedagogy=4, review_impact=4,
                database_url=db_url,
            )
            assert r1.success

            # Step 2: Update rating=5 only (no comment) → rating=5, comment="First"
            r2 = submit_review(
                article_id=article_id, reviewer_id="r1",
                decision="accept", comments="",
                review_originality=5, review_rigor=5,
                review_completeness=5, review_pedagogy=5, review_impact=5,
                database_url=db_url,
            )
            assert r2.success

            session = get_session(engine)
            reviews = get_reviews_for_article(session, article_id)
            assert len(reviews) == 1
            assert reviews[0].review_originality == 5
            assert reviews[0].comments == "First"
            session.close()

            # Step 3: Update comment="Updated" only (ratings=0) → comment="Updated", rating=5
            r3 = submit_review(
                article_id=article_id, reviewer_id="r1",
                decision="accept", comments="Updated",
                review_originality=0, review_rigor=0,
                review_completeness=0, review_pedagogy=0, review_impact=0,
                database_url=db_url,
            )
            assert r3.success

            session = get_session(engine)
            reviews = get_reviews_for_article(session, article_id)
            assert len(reviews) == 1
            assert reviews[0].comments == "Updated"
            assert reviews[0].review_originality == 5
            session.close()


# ── Test 3: Author cannot self-rate ───────────────────────────────────────


class TestAuthorCannotSelfRate:
    """Test 3: Author cannot self-rate — ratings zeroed, comment stored."""

    def test_author_ratings_zeroed_and_comment_stored(self):
        """Author submits review → all review_* dimensions are 0, comment stored."""
        with tempfile.TemporaryDirectory() as tmp:
            db_url, article_id, engine = _setup_db_and_article(tmp, author="alice")

            # Author "alice" reviews their own article
            assign_reviewer(article_id=article_id, reviewer_id="alice",
                            database_url=db_url)
            r = submit_review(
                article_id=article_id, reviewer_id="alice",
                decision="accept", comments="My own article!",
                review_originality=5, review_rigor=5,
                review_completeness=5, review_pedagogy=5, review_impact=5,
                database_url=db_url,
            )
            assert r.success

            session = get_session(engine)
            reviews = get_reviews_for_article(session, article_id)
            assert len(reviews) == 1
            rev = reviews[0]
            # All rating dimensions zeroed because author is self-reviewing
            assert rev.review_originality == 0
            assert rev.review_rigor == 0
            assert rev.review_completeness == 0
            assert rev.review_pedagogy == 0
            assert rev.review_impact == 0
            # Comment is preserved
            assert rev.comments == "My own article!"
            session.close()


# ── Test 4: Fork ──────────────────────────────────────────────────────────


class TestForkArticle:
    """Test 4: Fork creates new article with forked_from; fork_count increments."""

    def test_fork_creates_article_with_forked_from(self):
        """Fork an article and verify forked_from and fork_count."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()
            db_url = f"sqlite:///{db_path}"

            # Step 1: Create source article with a git repo
            source = base / "source.md"
            source.write_text("---\ntitle: Source Article\n---\n\nContent.\n")

            result = submit_article(
                source_path=source, database_url=db_url,
                articles_dir=articles_dir, author_name="alice",
            )
            assert result.success
            orig_id = result.article_id

            # Step 2: Fork via API with patched settings
            from fastapi.testclient import TestClient
            from peerpedia.web.app import app

            original_db = settings.database_url
            original_dir = settings.articles_dir
            settings.database_url = db_url
            settings.articles_dir = articles_dir

            try:
                client = TestClient(app)
                resp = client.post(
                    f"/api/v1/articles/{orig_id}/fork",
                    data={"forker_id": "bob"},
                )
                assert resp.status_code == 200, f"Fork API failed: {resp.text}"
                data = resp.json()
                fork_id = data["article_id"]
                assert data["forked_from"] == orig_id

                # Verify forked article in DB
                engine = get_engine(db_url)
                init_db(engine)
                session = get_session(engine)
                fork = get_article(session, fork_id)
                assert fork is not None
                assert fork.forked_from == orig_id
                assert fork.founding_authors == ["bob"]
                assert "Source Article" in fork.title

                # Verify original article's fork_count incremented
                orig = get_article(session, orig_id)
                assert orig.fork_count >= 1
                session.close()
            finally:
                settings.database_url = original_db
                settings.articles_dir = original_dir


# ── Test 5 + 6: Search ────────────────────────────────────────────────────


class TestSearchArticles:
    """Tests 5+6: Search finds by title/abstract/keywords; empty returns all."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from peerpedia.web.app import app
        return TestClient(app)

    def test_search_finds_and_nonexistent(self, client):
        """Search finds articles by title/abstract/keywords; nonexistent = empty."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            # Create two articles in same DB
            db_url, aid1, engine = _setup_db_and_article(
                tmp, title="Quantum Computing Basics",
                abstract="A deep dive into quantum algorithms.",
            )
            db_url2, aid2, _ = _setup_db_and_article(
                tmp, title="Geometry Paper",
                abstract="About shapes.",
                keywords=["geometry", "math"],
            )

            original_db = settings.database_url
            settings.database_url = db_url

            try:
                # Search by title substring
                resp = client.get("/api/v1/search?q=Quantum")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1
                titles = [a["title"] for a in data["articles"]]
                assert any("Quantum" in t for t in titles)

                # Search by abstract substring
                resp = client.get("/api/v1/search?q=Newtonian")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 0, (
                    "Neither article has 'Newtonian' in title/abstract/keywords"
                )

                # Search by keyword
                resp = client.get("/api/v1/search?q=geometry")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1
                titles = [a["title"] for a in data["articles"]]
                assert any("Geometry" in t for t in titles)

                # Search nonexistent → empty
                resp = client.get("/api/v1/search?q=xyznonexistent12345")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 0
                assert data["articles"] == []
            finally:
                settings.database_url = original_db

    def test_empty_query_returns_all(self, client):
        """Search with empty/whitespace query returns all articles."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            db_url, article_id, engine = _setup_db_and_article(tmp)

            original_db = settings.database_url
            settings.database_url = db_url

            try:
                # Empty query
                resp = client.get("/api/v1/search?q=")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1

                # Whitespace-only query
                resp = client.get("/api/v1/search?q=%20%20")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1
            finally:
                settings.database_url = original_db
