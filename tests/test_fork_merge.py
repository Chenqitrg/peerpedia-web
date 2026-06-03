"""Tests for fork → merge workflow."""
import pytest
import tempfile
from pathlib import Path

from peerpedia.submit import submit_article
from peerpedia_core.storage.db import (
    get_engine, init_db, get_session, get_article,
)


class TestMergeProposalCRUD:
    """MergeProposal CRUD operations — TDD Task 1."""

    def test_create_and_get_proposal(self):
        """Create a merge proposal and retrieve it."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Original\n---\n\n# Original\n")
            r1 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)
            r2 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)

            from peerpedia_core.storage.db import create_merge_proposal, get_merge_proposal

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            proposal = create_merge_proposal(
                session,
                fork_article_id=r2.article_id,
                target_article_id=r1.article_id,
                proposer_id="bob",
                description="Added new section on applications.",
            )
            session.commit()

            p = get_merge_proposal(session, proposal.id)
            assert p is not None
            assert p.status == "pending"
            assert p.fork_article_id == r2.article_id
            assert p.target_article_id == r1.article_id
            assert p.proposer_id == "bob"
            assert p.description == "Added new section on applications."
            session.close()

    def test_update_proposal_status(self):
        """Update proposal status and verify."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Article\n---\n\n# Test\n")
            r1 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)
            r2 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)

            from peerpedia_core.storage.db import create_merge_proposal, update_merge_proposal_status, get_merge_proposal

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            p = create_merge_proposal(session, fork_article_id=r2.article_id, target_article_id=r1.article_id, proposer_id="bob")
            session.commit()

            updated = update_merge_proposal_status(session, p.id, "approved", reviewer_id="alice", review_comment="Looks good.")
            session.commit()

            fetched = get_merge_proposal(session, p.id)
            assert fetched.status == "approved"
            assert fetched.reviewer_id == "alice"
            assert fetched.review_comment == "Looks good."
            session.close()

    def test_list_proposals_for_article(self):
        """List merge proposals targeting an article."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Target\n---\n\n# Test\n")
            r1 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)
            r2 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)
            r3 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)

            from peerpedia_core.storage.db import create_merge_proposal, get_merge_proposals_for_article

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            create_merge_proposal(session, fork_article_id=r2.article_id, target_article_id=r1.article_id, proposer_id="bob")
            create_merge_proposal(session, fork_article_id=r3.article_id, target_article_id=r1.article_id, proposer_id="charlie")
            session.commit()

            proposals = get_merge_proposals_for_article(session, r1.article_id)
            assert len(proposals) == 2
            session.close()


class TestMergeProposalAPI:
    """API endpoints for merge proposals — TDD Task 3."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from peerpedia.web.app import app
        return TestClient(app)

    def test_create_merge_proposal_api(self, client):
        """POST merge-proposal creates a pending proposal."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Original\n---\n\n# Original\n")
            r1 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)
            r2 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)
            a2 = get_article(session, r2.article_id)
            a2.forked_from = r1.article_id
            session.commit()
            session.close()

            original_url = settings.database_url
            settings.database_url = f"sqlite:///{db_path}"

            try:
                response = client.post(
                    f"/api/v1/articles/{r2.article_id}/merge-proposal",
                    data={
                        "target_article_id": r1.article_id,
                        "proposer_id": "bob",
                        "description": "Added new section.",
                    },
                )
                assert response.status_code == 200

                from peerpedia_core.storage.db import get_merge_proposals_for_article
                engine2 = get_engine(f"sqlite:///{db_path}")
                init_db(engine2)
                session2 = get_session(engine2)
                proposals = get_merge_proposals_for_article(session2, r1.article_id)
                assert len(proposals) == 1
                assert proposals[0].status == "pending"
                session2.close()
            finally:
                settings.database_url = original_url

    def test_review_merge_proposal_api(self, client):
        """POST review merge-proposal approves."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Original\n---\n\n# Original\n")
            r1 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)
            r2 = submit_article(source_path=source, database_url=f"sqlite:///{db_path}", articles_dir=articles_dir)

            from peerpedia_core.storage.db import create_merge_proposal, get_merge_proposal

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)
            a2 = get_article(session, r2.article_id)
            a2.forked_from = r1.article_id
            p = create_merge_proposal(session, fork_article_id=r2.article_id, target_article_id=r1.article_id, proposer_id="bob")
            session.commit()
            session.close()

            original_url = settings.database_url
            settings.database_url = f"sqlite:///{db_path}"

            try:
                response = client.post(
                    f"/api/v1/merge-proposals/{p.id}/review",
                    data={"reviewer_id": "alice", "decision": "approve"},
                )
                assert response.status_code == 200

                session2 = get_session(engine)
                updated = get_merge_proposal(session2, p.id)
                assert updated.status in ("approved", "merged")
                session2.close()
            finally:
                settings.database_url = original_url
