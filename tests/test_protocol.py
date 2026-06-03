"""Tests for Layer 0 protocol — message schemas and signing."""

import pytest
from peerpedia_core.protocol import (
    ArticleMeta,
    ArticleStatus,
    Decision,
    EditProposal,
    EditType,
    Identity,
    IdentityType,
    ReviewMessage,
    UserProfile,
    generate_keypair,
    sign_message,
    verify_signature,
    hash_content,
    compute_article_cid,
)


class TestMessageSchemas:
    """Layer 0 message formats must be instantiable with minimal fields."""

    def test_user_profile_defaults(self):
        user = UserProfile(
            id="test-1",
            name="Test User",
            email="test@example.com",
        )
        assert user.id == "test-1"
        assert user.expertise == []
        assert user.identities == []

    def test_user_profile_with_identity(self):
        user = UserProfile(
            id="test-1",
            name="Test User",
            email="test@example.com",
            identities=[
                Identity(
                    type=IdentityType.ORCID,
                    value="0000-0001-2345-6789",
                    verified=True,
                    trust_weight=1.0,  # ORCID gets max weight, set by reputation module
                )
            ],
        )
        assert len(user.identities) == 1
        assert user.identities[0].trust_weight == 1.0

    def test_article_meta_defaults(self):
        article = ArticleMeta(
            id="test-article-1",
            title="Test Article",
            founding_authors=["user-1"],
            abstract="A test abstract.",
        )
        assert article.status == ArticleStatus.DRAFT
        assert article.version == "v0.1"
        assert article.format == "typst"
        assert article.language == "en"

    def test_review_message(self):
        review = ReviewMessage(
            id="review-1",
            article_id="article-1",
            reviewer_id="user-2",
            decision=Decision.ACCEPT,
            comments="Looks good.",
            scientific_correctness=5,
            clarity=4,
        )
        assert review.decision == Decision.ACCEPT
        assert review.scientific_correctness == 5

    def test_edit_proposal(self):
        proposal = EditProposal(
            id="prop-1",
            article_id="article-1",
            proposer_id="user-3",
            proposal_type=EditType.MINOR,
            description="Fix typo in abstract.",
            git_branch="edit/prop-1",
        )
        assert proposal.proposal_type == EditType.MINOR
        assert proposal.points_stake == 0  # minor edits don't require stake


class TestSigning:
    """Signing and verification must be deterministic."""

    def test_sign_and_verify(self):
        private, public = generate_keypair()
        message = {"test": "data", "number": 42}

        signature = sign_message(message, private)
        assert verify_signature(message, signature, private)

    def test_tampered_message_fails(self):
        private, public = generate_keypair()
        message = {"test": "data"}

        signature = sign_message(message, private)
        tampered = {"test": "different"}
        assert not verify_signature(tampered, signature, private)

    def test_hash_content_deterministic(self):
        h1 = hash_content("hello world")
        h2 = hash_content("hello world")
        assert h1 == h2

    def test_hash_content_different(self):
        h1 = hash_content("hello world")
        h2 = hash_content("hello WORLD")
        assert h1 != h2


class TestAddressing:
    """CID computation must be deterministic."""

    def test_compute_cid_deterministic(self):
        cid1 = compute_article_cid(
            typst_source="#set page(width: 10cm)\nHello",
            metadata={"title": "Test"},
            git_commit_hash="abc123",
        )
        cid2 = compute_article_cid(
            typst_source="#set page(width: 10cm)\nHello",
            metadata={"title": "Test"},
            git_commit_hash="abc123",
        )
        assert cid1 == cid2

    def test_compute_cid_different_content(self):
        cid1 = compute_article_cid("Hello", {}, "abc123")
        cid2 = compute_article_cid("World", {}, "abc123")
        assert cid1 != cid2
