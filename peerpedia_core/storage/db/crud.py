"""CRUD operations for PeerPedia database models.

Each function takes a SQLAlchemy Session as the first positional argument
so callers control transaction boundaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from peerpedia_core.storage.db.models import (
    Article,
    ContributionRecord,
    EditProposal,
    Identity,
    Review,
    User,
)
from peerpedia_core.protocol.messages import ArticleStatus


# ── Article CRUD ────────────────────────────────────────────────────────────

def create_article(
    session: Session,
    *,
    id: Optional[str] = None,
    title: str,
    founding_authors: list[str],
    abstract: str,
    git_repo_path: str,
    about_person: Optional[str] = None,
    original_works: Optional[list[dict]] = None,
    abstract_zh: Optional[str] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    language: str = "en",
    format: str = "typst",
) -> Article:
    """Create a new article record in the database."""
    article = Article(
        id=id or str(uuid.uuid4()),
        title=title,
        founding_authors=founding_authors,
        about_person=about_person,
        original_works=original_works or [],
        abstract=abstract,
        abstract_zh=abstract_zh,
        categories=categories or [],
        keywords=keywords or [],
        language=language,
        status=ArticleStatus.DRAFT,
        version="v0.1",
        format=format,
        git_repo_path=git_repo_path,
    )
    session.add(article)
    return article


def get_article(session: Session, article_id: str) -> Optional[Article]:
    """Get an article by ID, or None."""
    return session.query(Article).filter(Article.id == article_id).first()


def list_articles(
    session: Session,
    *,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Article]:
    """List articles, most recent first. Optionally filter by status."""
    q = session.query(Article).order_by(Article.created_at.desc())
    if status:
        q = q.filter(Article.status == status)
    return q.offset(offset).limit(limit).all()


def update_article_status(
    session: Session, article_id: str, new_status: str
) -> Optional[Article]:
    """Update an article's status."""
    article = get_article(session, article_id)
    if article:
        article.status = new_status
        article.updated_at = datetime.now(timezone.utc)
    return article


def update_article_cid(
    session: Session, article_id: str, cid: str
) -> Optional[Article]:
    """Update an article's CID after publishing."""
    article = get_article(session, article_id)
    if article:
        article.cid = cid
        article.updated_at = datetime.now(timezone.utc)
    return article


def update_article_founding_authors(
    session: Session,
    article_id: str,
    new_author_id: str,
) -> Optional[Article]:
    """Add a new author to the article's founding_authors list (co-author join)."""
    article = get_article(session, article_id)
    if article:
        authors = list(article.founding_authors)
        if new_author_id not in authors:
            authors.append(new_author_id)
            article.founding_authors = authors
            article.updated_at = datetime.now(timezone.utc)
    return article


def update_article_version(
    session: Session,
    article_id: str,
    new_version: str,
) -> Optional[Article]:
    """Set the article version string to the given value."""
    article = get_article(session, article_id)
    if article:
        article.version = new_version
        article.updated_at = datetime.now(timezone.utc)
    return article


# ── Review CRUD ─────────────────────────────────────────────────────────────

def create_review(
    session: Session,
    *,
    article_id: str,
    reviewer_id: str,
    decision: str,
    comments: str,
    scientific_correctness: int = 0,
    clarity: int = 0,
    collaboration_request: bool = False,
    collaboration_message: str = "",
    points_earned: int = 0,
) -> Review:
    """Create a new review record."""
    review = Review(
        id=str(uuid.uuid4()),
        article_id=article_id,
        reviewer_id=reviewer_id,
        decision=decision,
        comments=comments,
        scientific_correctness=scientific_correctness,
        clarity=clarity,
        collaboration_request=1 if collaboration_request else 0,
        collaboration_message=collaboration_message,
        points_earned=points_earned,
    )
    session.add(review)
    return review


def get_review(session: Session, review_id: str) -> Optional[Review]:
    """Get a review by ID."""
    return session.query(Review).filter(Review.id == review_id).first()


def get_reviews_for_article(session: Session, article_id: str) -> list[Review]:
    """Get all reviews for an article, oldest first."""
    return (
        session.query(Review)
        .filter(Review.article_id == article_id)
        .order_by(Review.created_at.asc())
        .all()
    )


# ── ContributionRecord CRUD ─────────────────────────────────────────────────

def create_contribution_record(
    session: Session,
    *,
    article_id: str,
    user_id: str,
    commit_hash: str,
    commit_message: str = "",
    lines_added: int = 0,
    lines_deleted: int = 0,
    files_changed: Optional[list[str]] = None,
    change_type: str = "content",
    contribution_weight: int = 0,
) -> ContributionRecord:
    """Create a contribution record."""
    record = ContributionRecord(
        id=str(uuid.uuid4()),
        article_id=article_id,
        user_id=user_id,
        commit_hash=commit_hash,
        commit_message=commit_message,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        files_changed=files_changed or [],
        change_type=change_type,
        contribution_weight=contribution_weight,
    )
    session.add(record)
    return record


def get_contribution_records(
    session: Session,
    article_id: str,
) -> list[ContributionRecord]:
    """Get all contribution records for an article, oldest first."""
    return (
        session.query(ContributionRecord)
        .filter(ContributionRecord.article_id == article_id)
        .order_by(ContributionRecord.timestamp.asc())
        .all()
    )


def get_user_contribution_total(
    session: Session,
    article_id: str,
    user_id: str,
) -> int:
    """Get total contribution weight for a user on an article."""
    result = (
        session.query(func.sum(ContributionRecord.contribution_weight))
        .filter(
            ContributionRecord.article_id == article_id,
            ContributionRecord.user_id == user_id,
        )
        .scalar()
    )
    return result or 0


# ── EditProposal CRUD ───────────────────────────────────────────────────────

def create_edit_proposal(
    session: Session,
    *,
    article_id: str,
    proposer_id: str,
    proposal_type: str,
    description: str = "",
    git_branch: str = "",
    diff_stat: str = "",
    points_stake: int = 0,
) -> EditProposal:
    """Create an edit proposal record."""
    proposal = EditProposal(
        id=str(uuid.uuid4()),
        article_id=article_id,
        proposer_id=proposer_id,
        proposal_type=proposal_type,
        description=description,
        git_branch=git_branch,
        diff_stat=diff_stat,
        status="pending",
        points_stake=points_stake,
    )
    session.add(proposal)
    return proposal


def get_edit_proposal(session: Session, proposal_id: str) -> Optional[EditProposal]:
    """Get an edit proposal by ID."""
    return session.query(EditProposal).filter(EditProposal.id == proposal_id).first()


def get_edit_proposals_for_article(
    session: Session,
    article_id: str,
    *,
    status: Optional[str] = None,
) -> list[EditProposal]:
    """Get all edit proposals for an article, newest first."""
    q = (
        session.query(EditProposal)
        .filter(EditProposal.article_id == article_id)
        .order_by(EditProposal.created_at.desc())
    )
    if status:
        q = q.filter(EditProposal.status == status)
    return q.all()


def update_edit_proposal_status(
    session: Session,
    proposal_id: str,
    new_status: str,
    *,
    reviewer_id: Optional[str] = None,
    review_comment: str = "",
) -> Optional[EditProposal]:
    """Update an edit proposal's status."""
    proposal = get_edit_proposal(session, proposal_id)
    if proposal:
        proposal.status = new_status
        proposal.resolved_at = datetime.now(timezone.utc)
        if reviewer_id:
            proposal.reviewer_id = reviewer_id
        if review_comment:
            proposal.review_comment = review_comment
    return proposal


# ── User CRUD ───────────────────────────────────────────────────────────────

def create_user(
    session: Session,
    *,
    id: str,
    name: str,
    email: str,
    affiliation: Optional[str] = None,
    expertise: Optional[list[str]] = None,
    bio: Optional[str] = None,
    public_key: Optional[str] = None,
) -> User:
    """Create a new user record."""
    user = User(
        id=id,
        name=name,
        email=email,
        affiliation=affiliation,
        expertise=expertise or [],
        bio=bio,
        public_key=public_key,
    )
    session.add(user)
    return user


def get_user(session: Session, user_id: str) -> Optional[User]:
    """Get a user by ID, or None."""
    return session.query(User).filter(User.id == user_id).first()


def update_user_last_active(session: Session, user_id: str) -> Optional[User]:
    """Update a user's last_active timestamp to now."""
    user = get_user(session, user_id)
    if user:
        user.last_active = datetime.now(timezone.utc)
    return user


# ── Identity CRUD ───────────────────────────────────────────────────────────

def create_identity(
    session: Session,
    *,
    user_id: str,
    type: str,
    value: str,
    verified: bool = False,
    trust_weight: int = 10,
) -> Identity:
    """Create an identity binding for a user.

    trust_weight is scaled ×100 (e.g., 100 for ORCID = 1.0 weight).
    """
    identity = Identity(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=type,
        value=value,
        verified=1 if verified else 0,
        trust_weight=trust_weight,
    )
    session.add(identity)
    return identity


def get_identities_for_user(session: Session, user_id: str) -> list[Identity]:
    """Get all identity bindings for a user."""
    return session.query(Identity).filter(Identity.user_id == user_id).all()
