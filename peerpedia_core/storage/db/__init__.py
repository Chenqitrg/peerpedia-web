"""Database layer — backward-compatible re-exports.

This package replaces the old monolithic db.py. All imports from
``peerpedia_core.storage.db`` continue to work unchanged.
"""

from peerpedia_core.storage.db.engine import (
    Base,
    JSONDict,
    JSONList,
    get_engine,
    get_session,
    init_db,
)

from peerpedia_core.storage.db.models import (
    Article,
    ContributionRecord,
    EditProposal,
    Identity,
    Review,
    User,
)

from peerpedia_core.storage.db.crud import (
    create_article,
    create_contribution_record,
    create_edit_proposal,
    create_identity,
    create_review,
    create_user,
    get_article,
    get_contribution_records,
    get_edit_proposal,
    get_edit_proposals_for_article,
    get_identities_for_user,
    get_review,
    get_reviews_for_article,
    get_user,
    get_user_contribution_total,
    list_articles,
    update_article_cid,
    update_article_founding_authors,
    update_article_status,
    update_article_version,
    update_edit_proposal_status,
    update_user_last_active,
)

from peerpedia_core.protocol.messages import ArticleStatus

__all__ = [
    # engine
    "Base",
    "JSONDict",
    "JSONList",
    "get_engine",
    "get_session",
    "init_db",
    # models
    "Article",
    "ArticleStatus",
    "ContributionRecord",
    "EditProposal",
    "Identity",
    "Review",
    "User",
    # crud — article
    "create_article",
    "get_article",
    "list_articles",
    "update_article_cid",
    "update_article_founding_authors",
    "update_article_status",
    "update_article_version",
    # crud — review
    "create_review",
    "get_review",
    "get_reviews_for_article",
    # crud — contribution
    "create_contribution_record",
    "get_contribution_records",
    "get_user_contribution_total",
    # crud — edit proposal
    "create_edit_proposal",
    "get_edit_proposal",
    "get_edit_proposals_for_article",
    "update_edit_proposal_status",
    # crud — user
    "create_user",
    "get_user",
    "update_user_last_active",
    # crud — identity
    "create_identity",
    "get_identities_for_user",
]
