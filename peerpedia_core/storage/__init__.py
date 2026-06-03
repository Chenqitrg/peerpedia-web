"""PeerPedia Core — Storage module."""

from peerpedia_core.storage.git_backend import (
    DEFAULT_ARTICLES_DIR,
    commit_article,
    get_blame,
    get_commit_history,
    init_article_repo,
)

from peerpedia_core.storage.db import (
    Article,
    ArticleStatus,
    Base,
    create_article,
    get_article,
    get_engine,
    get_session,
    init_db,
    list_articles,
    update_article_cid,
    update_article_status,
)

from peerpedia_core.storage.compiler import (
    CompileResult,
    CompilerBackend,
    MarkdownBackend,
    TypstBackend,
    detect_format,
    extract_frontmatter,
)

__all__ = [
    # git backend
    "DEFAULT_ARTICLES_DIR",
    "commit_article",
    "get_blame",
    "get_commit_history",
    "init_article_repo",
    # db layer
    "Article",
    "ArticleStatus",
    "Base",
    "create_article",
    "get_article",
    "get_engine",
    "get_session",
    "init_db",
    "list_articles",
    "update_article_cid",
    "update_article_status",
    # compiler
    "CompileResult",
    "CompilerBackend",
    "MarkdownBackend",
    "TypstBackend",
    "detect_format",
    "extract_frontmatter",
]
