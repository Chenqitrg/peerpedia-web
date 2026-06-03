# Code Compactness & Modularity Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce boilerplate, eliminate duplication, and split oversized files across the PeerPedia codebase — ~250 lines of duplication removed, ~400 lines reorganized.

**Architecture:** Phase 1 adds shared infrastructure (session context manager, version bump, dimension constants). Phase 2 applies that infrastructure to existing workflow/web modules. Phase 3 cleans up specific long functions. Phase 4 splits the 1109-line `api_articles.py` into 5 focused route modules, all registered through the existing `api.py` facade.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.x, FastAPI, Pytest

---

### Task 1: Session scope context manager

**Files:**
- Create: `peerpedia_core/storage/db/session_utils.py`
- Test: `tests/test_db.py` (add test)

- [ ] **Step 1: Create the context manager**

```python
# peerpedia_core/storage/db/session_utils.py
"""Database session utilities.

Provides a context manager for session lifecycle so callers don't
repeat engine/session/rollback boilerplate.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from peerpedia_core.storage.db.engine import get_engine, get_session, init_db


@contextmanager
def db_session_scope(database_url: str) -> Generator[Session, None, None]:
    """Context manager that yields a SQLAlchemy Session with auto-commit/rollback.

    Usage:
        with db_session_scope(database_url) as session:
            article = get_article(session, article_id)
            # session commits on exit; rolls back on exception
    """
    engine = get_engine(database_url)
    init_db(engine)
    session = get_session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 2: Add test to tests/test_db.py**

Read `tests/test_db.py` to find the last line, then append:

```python
def test_db_session_scope_commits(tmp_path):
    """Session scope commits on clean exit."""
    from peerpedia_core.storage.db.session_utils import db_session_scope
    from peerpedia_core.storage.db.models import User

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    with db_session_scope(db_url) as session:
        user = User(id="test1", name="Test", email="test@test.com")
        session.add(user)

    # New session: user should be persisted
    with db_session_scope(db_url) as session:
        found = session.query(User).filter(User.id == "test1").first()
        assert found is not None
        assert found.name == "Test"


def test_db_session_scope_rolls_back(tmp_path):
    """Session scope rolls back on exception."""
    from peerpedia_core.storage.db.session_utils import db_session_scope
    from peerpedia_core.storage.db.models import User

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    try:
        with db_session_scope(db_url) as session:
            user = User(id="test2", name="Test", email="test@test.com")
            session.add(user)
            raise RuntimeError("forced error")
    except RuntimeError:
        pass

    with db_session_scope(db_url) as session:
        found = session.query(User).filter(User.id == "test2").first()
        assert found is None
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_db.py::test_db_session_scope_commits tests/test_db.py::test_db_session_scope_rolls_back -v
```
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add peerpedia_core/storage/db/session_utils.py tests/test_db.py
git commit -m "feat: add db_session_scope context manager for session lifecycle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Cache sessionmaker in get_session()

**Files:**
- Modify: `peerpedia_core/storage/db/engine.py:84-87`

- [ ] **Step 1: Cache the sessionmaker factory**

Replace lines 84-87 in `peerpedia_core/storage/db/engine.py`:

```python
def get_session(engine: Engine) -> Session:
    """Create a new session bound to the given engine."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()
```

With:

```python
_factory_cache: dict = {}


def get_session(engine: Engine) -> Session:
    """Create a new session bound to the given engine.

    sessionmaker is cached per engine so the factory class is not
    recreated on every call.
    """
    key = engine.url
    if key not in _factory_cache:
        _factory_cache[key] = sessionmaker(bind=engine, expire_on_commit=False)
    return _factory_cache[key]()
```

- [ ] **Step 2: Run full test suite to verify no regressions**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/ -x -q 2>&1 | tail -5
```
Expected: all tests pass (or same failures as before)

- [ ] **Step 3: Commit**

```bash
git add peerpedia_core/storage/db/engine.py
git commit -m "perf: cache sessionmaker factory per engine URL

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Consolidate JSONList / JSONDict

**Files:**
- Modify: `peerpedia_core/storage/db/engine.py:20-49`

- [ ] **Step 1: Replace two classes with one parameterized factory**

Replace lines 20-49 (both JSONList and JSONDict classes) with:

```python
# ── JSON column types for list/dict fields ───────────────────────────────────

def _make_json_type():
    """Factory for JSON column TypeDecorators (avoids duplicate implementations)."""
    class _JSONType(TypeDecorator):
        impl = Text
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            return json.dumps(value, ensure_ascii=False)

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            return json.loads(value)

    return _JSONType


JSONList = _make_json_type()
"""Store Python list as JSON string in SQLite."""

JSONDict = _make_json_type()
"""Store Python dict as JSON string in SQLite."""
```

Verify the import in `models.py` line 23 still works:
```python
from peerpedia_core.storage.db.engine import Base, JSONList
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_db.py tests/test_submit.py -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add peerpedia_core/storage/db/engine.py
git commit -m "refactor: deduplicate JSONList/JSONDict via shared factory

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Extract REVIEW_DIMENSIONS constant

**Files:**
- Create: `peerpedia_core/workflow/review_dimensions.py`
- Modify: `peerpedia/web/routes/pages.py:95,160`

- [ ] **Step 1: Create the constants module**

```python
# peerpedia_core/workflow/review_dimensions.py
"""Shared review dimension definitions.

Used by community review aggregation, sedimentation pool calculation,
and review submission — ensures the 5-dimension model has a single source of truth.
"""

REVIEW_DIMENSIONS = ["originality", "rigor", "completeness", "pedagogy", "impact"]
"""Ordered list of the 5 peer-review quality dimensions."""

REVIEW_DIM_COLUMN_PREFIX = "review_"
"""ORM column prefix for dimension fields on the Review model (e.g., review_originality)."""
```

- [ ] **Step 2: Replace line 95 in pages.py**

Read `pages.py` lines 93-107. Replace the `dims = [...]` line:

Old (line 95):
```python
            dims = ["originality", "rigor", "completeness", "pedagogy", "impact"]
```

New:
```python
            from peerpedia_core.workflow.review_dimensions import REVIEW_DIMENSIONS
            dims = REVIEW_DIMENSIONS
```

- [ ] **Step 3: Replace line 160 in pages.py**

Read `pages.py` lines 158-163. Replace the `dims = [...]` line:

Old (line 160):
```python
            dims = ["originality", "rigor", "completeness", "pedagogy", "impact"]
```

New:
```python
            from peerpedia_core.workflow.review_dimensions import REVIEW_DIMENSIONS
            dims = REVIEW_DIMENSIONS
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_web_pages.py tests/test_community_review.py tests/test_sedimentation_pool.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia_core/workflow/review_dimensions.py peerpedia/web/routes/pages.py
git commit -m "refactor: extract REVIEW_DIMENSIONS constant to shared module

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Extract shared bump_minor_version function

**Files:**
- Create: `peerpedia_core/workflow/versioning.py`
- Modify: `peerpedia/web/routes/api_articles.py:329-335` (remove `_bump_version`)
- Modify: `peerpedia/web/routes/api_articles.py:287` (update caller)
- Modify: `peerpedia_core/workflow/edit_proposal.py:254-260` (replace inline logic)

- [ ] **Step 1: Create the versioning module**

```python
# peerpedia_core/workflow/versioning.py
"""Version string utilities for article version bumps.

Version strings follow the format v<major>.<minor> (e.g., v0.1 → v0.2).
"""


def bump_minor_version(version_str: str) -> str:
    """Bump the minor version component: v0.1 → v0.2, v1.5 → v1.6.

    Falls back to 'v0.2' if the version string cannot be parsed.
    """
    try:
        parts = version_str.lstrip("v").split(".")
        minor = int(parts[1]) + 1 if len(parts) > 1 else 1
        return f"v{parts[0]}.{minor}"
    except (ValueError, IndexError):
        return "v0.2"
```

- [ ] **Step 2: Replace _bump_version in api_articles.py**

Delete lines 329-335 in `api_articles.py` (the entire `_bump_version` function).

At the top of `api_articles.py`, add the import in the existing import block:

```python
from peerpedia_core.workflow.versioning import bump_minor_version
```

At line 287, replace:
```python
            new_version = _bump_version(target.version)
```
With:
```python
            new_version = bump_minor_version(target.version)
```

- [ ] **Step 3: Replace inline version bump in edit_proposal.py**

In `edit_proposal.py`, add the import near the top (after the existing `from peerpedia_core.workflow.contribution import ...` line):

```python
from peerpedia_core.workflow.versioning import bump_minor_version
```

Replace lines 253-260:
Old:
```python
        # Bump version
        current_version = article.version or "v0.1"
        try:
            parts = current_version.lstrip("v").split(".")
            minor = int(parts[1]) if len(parts) > 1 else 1
            new_version = f"v{parts[0]}.{minor + 1}"
        except (ValueError, IndexError):
            new_version = "v0.2"
```
New:
```python
        # Bump version
        new_version = bump_minor_version(article.version or "v0.1")
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_edit_proposal.py tests/test_fork_merge.py tests/test_api_routes.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia_core/workflow/versioning.py peerpedia/web/routes/api_articles.py peerpedia_core/workflow/edit_proposal.py
git commit -m "refactor: extract bump_minor_version to shared versioning module

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Refactor workflow modules to use db_session_scope

**Files:**
- Modify: `peerpedia_core/workflow/review.py`
- Modify: `peerpedia_core/workflow/edit_proposal.py`
- Modify: `peerpedia_core/workflow/collaboration.py`

Each of `assign_reviewer`, `submit_review`, `make_decision`, `create_proposal`, `review_proposal`, `merge_proposal`, `accept_collaboration`, `get_collaboration_status` repeats the same engine/session/rollback boilerplate. Replace with `db_session_scope`.

- [ ] **Step 1: Refactor review.py**

Read the current `review.py`. Each function has this pattern:

```python
engine = get_engine(database_url)
init_db(engine)
session = get_session(engine)
try:
    ...
    session.commit()
except Exception as e:
    session.rollback()
    return ErrorResult(success=False, ...)
finally:
    session.close()
```

Replace with (example for `assign_reviewer`):

```python
def assign_reviewer(
    article_id: str,
    reviewer_id: str,
    *,
    database_url: str,
) -> AssignResult:
    """Verify article is in a valid state for rating (sedimentation pool model)."""
    from peerpedia_core.storage.db.session_utils import db_session_scope

    try:
        with db_session_scope(database_url) as session:
            article = get_article(session, article_id)
            if article is None:
                return AssignResult(success=False, article_id=article_id, error="Article not found")

            if article.status not in (ArticleStatus.SUBMITTED, ArticleStatus.IN_REVIEW, ArticleStatus.DRAFT):
                return AssignResult(
                    success=False,
                    article_id=article_id,
                    error=f"Cannot rate: article status is '{article.status}', must be 'submitted'",
                )

            return AssignResult(
                success=True,
                article_id=article_id,
                reviewer_id=reviewer_id,
                new_status=article.status,
            )
    except Exception as e:
        return AssignResult(success=False, article_id=article_id, error=str(e))
```

Do the same transformation for `submit_review`, `make_decision`. For `submit_review`: the function does `session.commit()` mid-function (after creating the review), then continues — `db_session_scope` only commits on exit. This is fine because `db_session_scope` commits on clean exit, and the function doesn't need an intermediate commit. If an explicit mid-function commit is needed, call `session.flush()` instead.

Remove the imports that are no longer needed:
```python
from peerpedia_core.storage.db import (
    get_engine,      # REMOVE
    get_session,     # REMOVE
    init_db,         # REMOVE
    ...
)
```

- [ ] **Step 2: Refactor edit_proposal.py**

Apply the same pattern to `create_proposal`, `review_proposal`, `merge_proposal`. Each function's `engine = get_engine(...)` / `init_db(engine)` / `session = get_session(engine)` / `try...finally: session.close()` block becomes a `with db_session_scope(database_url) as session:` block.

Remove unused imports: `get_engine`, `get_session`, `init_db`.

- [ ] **Step 3: Refactor collaboration.py**

Apply the same pattern to `accept_collaboration` and `get_collaboration_status`.

Remove unused imports: `get_engine`, `get_session`, `init_db`.

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_review_workflow.py tests/test_edit_proposal.py tests/test_collaboration.py tests/test_sedimentation_pool.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia_core/workflow/review.py peerpedia_core/workflow/edit_proposal.py peerpedia_core/workflow/collaboration.py
git commit -m "refactor: use db_session_scope in review, edit_proposal, collaboration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Add get_article_or_404 helper

**Files:**
- Create: `peerpedia/web/routes/_helpers.py`
- Modify: `peerpedia/web/routes/api_articles.py` (use helper in 13 places)

- [ ] **Step 1: Create the helpers module**

```python
# peerpedia/web/routes/_helpers.py
"""Shared route helpers — reduce boilerplate in API handlers."""

from fastapi import HTTPException

from peerpedia_core.storage.db import get_article


def get_article_or_404(session, article_id: str):
    """Get an article by ID, or raise HTTP 404.

    Usage:
        article = get_article_or_404(session, article_id)
    """
    article = get_article(session, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
```

- [ ] **Step 2: Apply helper in api_articles.py**

Import at the top:
```python
from peerpedia.web.routes._helpers import get_article_or_404
```

Replace every occurrence of:
```python
article = get_article(session, article_id)
if article is None:
    raise HTTPException(status_code=404, detail="Article not found")
```
With:
```python
article = get_article_or_404(session, article_id)
```

There are 13 occurrences — replace all of them. Remove the now-unused `get_article` import if no other code uses it directly (check: `api_articles.py` uses `get_article` elsewhere, keep it for now — it will be cleaned up in the file-split tasks).

- [ ] **Step 3: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_api_routes.py tests/test_web_pages.py -v
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add peerpedia/web/routes/_helpers.py peerpedia/web/routes/api_articles.py
git commit -m "refactor: add get_article_or_404 helper, remove 13x boilerplate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Collapse follow-count branches in pages.py

**Files:**
- Modify: `peerpedia/web/routes/pages.py:311-331`

- [ ] **Step 1: Replace the duplicated if/else block**

Read lines 311-331 in `pages.py`. Replace:

Old:
```python
        # Follow state — always compute counts, even without viewer
        is_self = False
        is_following_user = False
        following_count = 0
        follower_count = 0
        if viewer:
            from peerpedia_core.storage.db import (
                get_follower_count,
                get_following_count,
                is_following,
            )
            if viewer == user_id:
                is_self = True
            else:
                is_following_user = is_following(session, viewer, user_id)
            following_count = get_following_count(session, user_id)
            follower_count = get_follower_count(session, user_id)
        else:
            from peerpedia_core.storage.db import get_follower_count, get_following_count
            following_count = get_following_count(session, user_id)
            follower_count = get_follower_count(session, user_id)
```

New:
```python
        # Follow state
        from peerpedia_core.storage.db import (
            get_follower_count,
            get_following_count,
            is_following,
        )
        is_self = bool(viewer) and viewer == user_id
        is_following_user = not is_self and bool(viewer) and is_following(session, viewer, user_id)
        following_count = get_following_count(session, user_id)
        follower_count = get_follower_count(session, user_id)
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_user_profile.py tests/test_follow.py tests/test_web_pages.py -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/routes/pages.py
git commit -m "refactor: collapse duplicated follow-count branches in user_profile

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Fix ReputationV1._aggregate_activity redundant args

**Files:**
- Modify: `peerpedia_core/reputation/v1.py:121,150`

- [ ] **Step 1: Remove redundant arguments**

In `compute()` (line 121), change:
```python
activity = self._aggregate_activity(session, user_id, Article, Review,
                                    ContributionRecord, func)
```
To:
```python
activity = self._aggregate_activity(session, user_id)
```

In `_aggregate_activity()` (line 150), change signature:
```python
def _aggregate_activity(self, session, user_id: str, Article, Review,
                        ContributionRecord, func) -> dict:
```
To:
```python
def _aggregate_activity(self, session, user_id: str) -> dict:
```

The ORM classes (`Article`, `Review`, `ContributionRecord`) and `func` are already in scope as local variables inside `compute()` (imported at lines 110-117). `_aggregate_activity` is called from `compute()`, so these names are accessible via closure. No import changes needed.

- [ ] **Step 2: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_reputation.py -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add peerpedia_core/reputation/v1.py
git commit -m "refactor: remove redundant ORM class args from _aggregate_activity

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Merge import blocks in api_users.py

**Files:**
- Modify: `peerpedia/web/routes/api_users.py:9-18`

- [ ] **Step 1: Combine three import blocks into one**

Replace lines 9-18:
Old:
```python
from peerpedia_core.storage.db import (
    create_identity as db_create_identity,
)
from peerpedia_core.storage.db import (
    create_user as db_create_user,
)
from peerpedia_core.storage.db import (
    get_identities_for_user,
    get_user,
)
```

New:
```python
from peerpedia_core.storage.db import (
    create_identity as db_create_identity,
    create_user as db_create_user,
    get_identities_for_user,
    get_user,
)
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_user_api.py -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/routes/api_users.py
git commit -m "style: merge three import blocks from same module in api_users.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Split api_articles.py — extract api_comments.py

**Files:**
- Create: `peerpedia/web/routes/api_comments.py`
- Modify: `peerpedia/web/routes/api_articles.py` (remove comment routes)
- Modify: `peerpedia/web/routes/api.py` (register new router)

- [ ] **Step 1: Create api_comments.py**

Extract these routes from `api_articles.py`:
- `api_get_comments` (line 874)
- `api_create_comment` (line 904)
- `api_resolve_comment` (line 949)
- `api_get_comments_html` (line 970)

```python
# peerpedia/web/routes/api_comments.py
"""API routes for line-level diff review comments."""

from fastapi import APIRouter, Form, HTTPException

from peerpedia.web.routes._helpers import get_article_or_404
from peerpedia.web.db_session import get_db_session
from peerpedia_core.storage.db import (
    create_review_comment,
    get_comments_for_article,
    resolve_review_comment,
)

router = APIRouter()


@router.get("/articles/{article_id}/comments")
async def api_get_comments(
    article_id: str,
    commit_hash: str = "",
    resolved: bool = None,
):
    """Get review comments for an article, optionally filtered by commit."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        comments = get_comments_for_article(
            session,
            article_id,
            commit_hash=commit_hash or None,
            resolved=resolved,
        )
        return {
            "article_id": article_id,
            "comments": [c.to_dict() for c in comments],
            "total": len(comments),
        }
    finally:
        session.close()


@router.post("/articles/{article_id}/comments")
async def api_create_comment(
    article_id: str,
    commit_hash: str = Form(...),
    author_id: str = Form(...),
    body: str = Form(...),
    file_path: str = Form(""),
    line_start: int = Form(0),
    line_end: int = Form(None),
    comment_type: str = Form("comment"),
    suggestion: str = Form(""),
):
    """Add a line-level comment to a commit diff."""
    if comment_type not in ("comment", "suggestion"):
        raise HTTPException(status_code=400, detail="comment_type must be 'comment' or 'suggestion'")

    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        comment = create_review_comment(
            session,
            article_id=article_id,
            commit_hash=commit_hash,
            author_id=author_id,
            body=body,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            comment_type=comment_type,
            suggestion=suggestion,
        )
        session.commit()
        return {"comment": comment.to_dict(), "status": "created"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/articles/{article_id}/comments/{comment_id}/resolve")
async def api_resolve_comment(article_id: str, comment_id: str):
    """Mark a review comment as resolved."""
    session = get_db_session()
    try:
        comment = resolve_review_comment(session, comment_id, resolved=True)
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        session.commit()
        return {"comment_id": comment_id, "resolved": True}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/articles/{article_id}/comments/html")
async def api_get_comments_html(
    article_id: str,
    commit_hash: str = "",
):
    """Get comments as HTML fragment for HTMX swap."""
    from fastapi.responses import HTMLResponse

    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        comments = get_comments_for_article(
            session,
            article_id,
            commit_hash=commit_hash or None,
        )
        if not comments:
            return HTMLResponse(
                '<p style="color:#888;font-size:0.85em;margin-top:8px;">'
                '此版本暂无评论。</p>'
            )

        html = '<div class="comments-html">'
        html += f'<h4 style="margin:12px 0 4px;">💬 评论 ({len(comments)})</h4>'
        for c in comments:
            cd = c.to_dict()
            suggestion_badge = ""
            if cd["comment_type"] == "suggestion":
                suggestion_badge = (
                    ' <span style="background:#fef3c7;color:#92400e;'
                    'padding:1px 4px;border-radius:2px;font-size:0.75em;">建议</span>'
                )
            resolved_badge = ""
            if cd["resolved"]:
                resolved_badge = (
                    ' <span style="color:#16a34a;font-size:0.75em;">✓ 已解决</span>'
                )
            line_info = f"L{cd['line_start']}"
            if cd["line_end"] and cd["line_end"] != cd["line_start"]:
                line_info += f"-{cd['line_end']}"

            html += (
                f'<div style="padding:6px 8px;margin:4px 0;background:#fff;'
                f'border:1px solid var(--border);border-radius:4px;font-size:0.85em;">'
                f'<strong>{cd["author_id"]}</strong> '
                f'<span style="color:#888;">{line_info}</span>'
                f'{suggestion_badge}{resolved_badge}'
                f'<div style="margin-top:2px;">{cd["body"]}</div>'
            )
            if cd["suggestion"]:
                html += (
                    f'<pre style="background:#f8f9fa;padding:4px;margin-top:4px;'
                    f'font-size:0.8em;overflow-x:auto;border-radius:3px;">'
                    f'<code>{cd["suggestion"]}</code></pre>'
                )
            if not cd["resolved"]:
                html += (
                    f'<button '
                    f'hx-post="/api/v1/articles/{article_id}/comments/{cd["id"]}/resolve" '
                    f'hx-swap="outerHTML" '
                    f'style="margin-top:4px;padding:2px 8px;font-size:0.75em;'
                    f'background:#16a34a;color:#fff;border:none;border-radius:3px;'
                    f'cursor:pointer;">✓ 标记已解决</button>'
                )
            html += '</div>'
        html += '</div>'
        return HTMLResponse(html)
    finally:
        session.close()
```

- [ ] **Step 2: Remove comment routes from api_articles.py**

Delete lines 871-1043 from `api_articles.py` (the entire `# ── Review Comments` section and the comments/html endpoint).

- [ ] **Step 3: Register new router in api.py**

In `peerpedia/web/routes/api.py`, add:
```python
from peerpedia.web.routes.api_comments import router as comments_router
```
And:
```python
router.include_router(comments_router)
```
After the existing `collab_router` line.

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_api_routes.py tests/test_web_pages.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/api_comments.py peerpedia/web/routes/api_articles.py peerpedia/web/routes/api.py
git commit -m "refactor: extract comment routes to api_comments.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Split api_articles.py — extract api_compile.py

**Files:**
- Create: `peerpedia/web/routes/api_compile.py`
- Modify: `peerpedia/web/routes/api_articles.py` (remove compile routes)
- Modify: `peerpedia/web/routes/api.py` (register)

- [ ] **Step 1: Create api_compile.py**

Extract from `api_articles.py`:
- `_compile_error` helper (lines 459-465)
- `_resolve_compile_backend` helper (lines 468-503)
- `api_compile_article` route (lines 505-568)

The two helpers become module-private in `api_compile.py`. The route function keeps its public name.

```python
# peerpedia/web/routes/api_compile.py
"""API routes for article compilation (Typst → PDF, Markdown → HTML)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from peerpedia.web.routes._helpers import get_article_or_404
from peerpedia.web.db_session import get_db_session
from peerpedia_core.storage.compiler import MarkdownBackend, TypstBackend
from peerpedia_core.workflow.citations import inject_citation_links

router = APIRouter()


def _compile_error(message: str, status: int = 200):
    """Return an HTML error response for compile failures."""
    return HTMLResponse(
        content=f'<div class="compile-error"><p>⚠️ {message}</p></div>',
        status_code=status,
    )


def _resolve_compile_backend(repo, article_format: str, article_title: str = ""):
    """Resolve the compiler backend and find the best source file."""
    from peerpedia_core.storage.compiler import extract_frontmatter

    ext = "*.typ" if article_format == "typst" else "*.md"
    source_files = list(repo.glob(ext))
    if not source_files:
        raise HTTPException(
            status_code=400,
            detail=f"源文件未找到 (格式: {article_format})",
        )

    if len(source_files) == 1:
        picked = source_files[0]
    else:
        picked = source_files[0]
        for f in source_files:
            try:
                fm = extract_frontmatter(f.read_text())
                if fm.get("title") == article_title:
                    picked = f
                    break
            except Exception:
                continue

    backend = TypstBackend() if article_format == "typst" else MarkdownBackend()
    return backend, picked


@router.get("/articles/{article_id}/compile")
async def api_compile_article(article_id: str, fmt: str = "html"):
    """Compile an article on demand. fmt: 'html' (default) or 'pdf'."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)

        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            return _compile_error(f"源文件目录不存在。路径: {article.git_repo_path}")

        try:
            backend, source_file = _resolve_compile_backend(
                repo, article.format, article_title=article.title,
            )
        except HTTPException as e:
            return _compile_error(str(e.detail))

        result = backend.compile(source_file, repo)
        if not result.success:
            return _compile_error(f"编译失败: {result.error}")

        if fmt == "pdf" and result.output_path:
            return FileResponse(
                result.output_path, media_type="application/pdf",
                filename=f"{article.title}.pdf",
            )
        elif result.html_content:
            return HTMLResponse(content=inject_citation_links(result.html_content))
        elif result.output_path and article.format == "typst":
            pdf_url = f"/api/v1/articles/{article_id}/compile?fmt=pdf"
            viewer_html = (
                '<div style="text-align:center;padding:40px 20px;'
                'background:#f8f9fa;border-radius:8px;border:2px dashed #ddd;">'
                '<p style="font-size:3em;margin:0 0 16px 0;">📄</p>'
                '<p style="font-size:1.1em;margin:0 0 8px 0;color:#333;">'
                'Typst 文章已编译为 PDF</p>'
                '<p style="font-size:0.9em;color:#888;margin:0 0 20px 0;">'
                '点击下方按钮查看或下载</p>'
                f'<a href="{pdf_url}" target="_blank" '
                'style="display:inline-block;padding:10px 24px;background:#2563eb;'
                'color:white;border-radius:6px;text-decoration:none;margin:4px;">'
                '在新标签页中查看</a>'
                f'<a href="{pdf_url}" download '
                'style="display:inline-block;padding:10px 24px;background:#16a34a;'
                'color:white;border-radius:6px;text-decoration:none;margin:4px;">'
                '下载 PDF</a>'
                '</div>'
            )
            return HTMLResponse(content=viewer_html)
        elif result.output_path:
            output = Path(result.output_path)
            return {"content": output.read_text(), "format": article.format}
        else:
            return _compile_error("编译未产生输出。")
    finally:
        session.close()
```

- [ ] **Step 2: Remove compile code from api_articles.py**

Delete lines 459-568 from `api_articles.py` (the `_compile_error`, `_resolve_compile_backend`, and `api_compile_article` sections).

Remove the now-unused imports from `api_articles.py`:
- `from peerpedia_core.storage.compiler import MarkdownBackend, TypstBackend` (if not used elsewhere)
- `from peerpedia_core.workflow.citations import inject_citation_links` (moves to api_compile.py — check if still needed in api_articles.py for other routes)

`inject_citation_links` is only used in `api_compile_article`, so it can be removed from `api_articles.py`. `MarkdownBackend` and `TypstBackend` are only used in `_resolve_compile_backend`, so they can be removed from `api_articles.py`.

- [ ] **Step 3: Register in api.py**

Add to `api.py`:
```python
from peerpedia.web.routes.api_compile import router as compile_router
router.include_router(compile_router)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_api_routes.py tests/test_compiler.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/api_compile.py peerpedia/web/routes/api_articles.py peerpedia/web/routes/api.py
git commit -m "refactor: extract compile routes to api_compile.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Split api_articles.py — extract api_contributions.py

**Files:**
- Create: `peerpedia/web/routes/api_contributions.py`
- Modify: `peerpedia/web/routes/api_articles.py` (remove contribution/commit/diff/blame routes)
- Modify: `peerpedia/web/routes/api.py` (register)

- [ ] **Step 1: Create api_contributions.py**

Extract from `api_articles.py`:
- `_render_contribution_timeline_html` (lines 582-625)
- `api_get_contribution_timeline` (lines 628-667)
- `api_get_commit_history` (lines 673-693)
- `api_get_commit_history_html` (lines 696-774)
- `api_get_diff` (lines 780-808)
- `api_get_diff_between` (lines 811-835)
- `api_get_blame` (lines 838-868)

```python
# peerpedia/web/routes/api_contributions.py
"""API routes for contribution timeline, git commit history, diffs, and blame."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from peerpedia.web.routes._helpers import get_article_or_404
from peerpedia.web.db_session import get_db_session
from peerpedia_core.storage.db import (
    get_article,
    get_contribution_records,
)
from peerpedia_core.storage.git_backend import (
    get_blame,
    get_commit_history,
    get_diff,
    get_diff_between,
)
from peerpedia_core.workflow.contribution import (
    compute_contribution_breakdown,
    compute_contribution_timeline,
)

router = APIRouter()


def _render_contribution_timeline_html(article_id: str, timeline: list, breakdown: dict, total: int) -> str:
    """Render contribution timeline as an HTML fragment."""
    if total == 0:
        return '<p style="color: #888;">暂无贡献记录。文章发布后可在此查看贡献历史。</p>'

    bar_items = []
    colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948"]
    for i, (uid, pct) in enumerate(breakdown.items()):
        color = colors[i % len(colors)]
        bar_items.append(
            f'<div style="background:{color};width:{pct}%;display:inline-block;'
            f'text-align:center;color:white;font-size:0.75em;overflow:hidden;'
            f'white-space:nowrap;line-height:24px;" title="{uid}: {pct}%">{uid} {pct}%</div>'
        )

    html = '<div class="contribution-timeline-html">'
    html += '<div class="contribution-breakdown" style="margin-bottom:16px;">'
    html += '<h4 style="margin:0 0 8px 0;">📊 贡献占比</h4>'
    html += f'<div style="border-radius:4px;overflow:hidden;">{"".join(bar_items)}</div>'
    html += '</div>'

    html += '<h4 style="margin:0 0 8px 0;">📋 贡献记录 ({})</h4>'.format(total)
    html += '<div class="timeline-list" style="max-height:300px;overflow-y:auto;">'
    for entry in timeline:
        ts = entry.get("timestamp", "")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        ts_short = str(ts)[:10] if ts else ""
        uid = entry.get("user_id", "unknown")
        msg = entry.get("commit_message", "")[:80]
        lines = f"+{entry.get('lines_added', 0)}/-{entry.get('lines_deleted', 0)}"
        html += (
            f'<div style="padding:6px 0;border-bottom:1px solid #eee;font-size:0.85em;">'
            f'<span style="color:#888;">{ts_short}</span> '
            f'<strong>{uid}</strong> '
            f'<span style="color:#666;">{msg}</span> '
            f'<span style="color:#28a745;">{lines}</span>'
            f'</div>'
        )
    html += '</div></div>'
    return html


@router.get("/articles/{article_id}/contributions")
async def api_get_contribution_timeline(article_id: str, format: str = "json"):
    """Get contribution timeline and breakdown for an article."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        records = get_contribution_records(session, article_id)
        record_dicts = [r.to_dict() for r in records]
        timeline = compute_contribution_timeline(record_dicts)
        breakdown = compute_contribution_breakdown(record_dicts)

        if format == "html":
            return HTMLResponse(_render_contribution_timeline_html(
                article_id, timeline, breakdown, len(records),
            ))

        return {
            "article_id": article_id,
            "timeline": timeline,
            "breakdown": breakdown,
            "total_records": len(records),
        }
    finally:
        session.close()


@router.get("/articles/{article_id}/commits")
async def api_get_commit_history(article_id: str):
    """Get git commit history for an article."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            raise HTTPException(status_code=404, detail="Git repository not found")

        commits = get_commit_history(repo)
        return {"article_id": article_id, "commits": commits, "total": len(commits)}
    finally:
        session.close()


@router.get("/articles/{article_id}/commits/html")
async def api_get_commit_history_html(article_id: str):
    """Get git commit history as an HTML fragment for HTMX swap."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            return HTMLResponse('<p style="color:#888;">Git 仓库未找到。</p>')

        commits = get_commit_history(repo)
        records = get_contribution_records(session, article_id)

        if not commits and not records:
            return HTMLResponse('<p style="color:#888;">暂无提交记录。</p>')

        html = '<div class="commit-list-html">'
        for i, c in enumerate(commits):
            short_hash = c["hash"][:8]
            msg = c["message"][:80]
            author = c["author"]
            ts = c["timestamp"][:10] if c["timestamp"] else ""
            active = "active" if i == 0 else ""
            files_count = len(c.get("stats", {}).get("files", []))
            event_icon = ""
            if "Merge:" in msg:
                event_icon = "🔀 "
            elif "Fork" in msg:
                event_icon = "🍴 "
            html += (
                f'<div class="commit-item {active}" data-hash="{c["hash"]}"'
                f' onclick="loadDiff(\'{article_id}\', \'{c["hash"]}\')"'
                f' style="padding:8px;border-bottom:1px solid #eee;cursor:pointer;'
                f'font-size:0.85em;border-radius:4px;transition:background 0.15s;">'
                f'<code style="color:#2563eb;font-size:0.8em;">{event_icon}{short_hash}</code> '
                f'<strong>{author}</strong>'
                f'<div style="color:#666;font-size:0.85em;margin-top:2px;">{msg}</div>'
                f'<span style="color:#888;font-size:0.75em;">{ts}'
            )
            if files_count:
                html += f' · {files_count} file(s)'
            html += '</span></div>'

        for r in records:
            msg = (r.commit_message or "")[:80]
            if not msg:
                continue
            uid = r.user_id or "unknown"
            ts = r.timestamp.isoformat()[:10] if r.timestamp else ""
            icon = "🔀 " if "merge" in msg.lower() else "📝 "
            html += (
                f'<div class="commit-item"'
                f' style="padding:8px;border-bottom:1px solid #eee;'
                f'font-size:0.85em;border-radius:4px;opacity:0.8;">'
                f'<code style="color:#16a34a;font-size:0.8em;">{icon}</code> '
                f'<strong>{uid}</strong>'
                f'<div style="color:#666;font-size:0.85em;margin-top:2px;">{msg}</div>'
                f'<span style="color:#888;font-size:0.75em;">{ts}</span>'
                f'</div>'
            )

        html += '</div>'
        return HTMLResponse(html)
    finally:
        session.close()


@router.get("/articles/{article_id}/diff/{commit_hash}")
async def api_get_diff(article_id: str, commit_hash: str):
    """Get the diff for a specific commit as unified diff text."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            raise HTTPException(status_code=404, detail="Git repository not found")

        diff_data = get_diff(repo, commit_hash)
        return diff_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diff failed: {e}")
    finally:
        session.close()


@router.get("/articles/{article_id}/diff/{hash1}/{hash2}")
async def api_get_diff_between(article_id: str, hash1: str, hash2: str):
    """Get the diff between two commits."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            raise HTTPException(status_code=404, detail="Git repository not found")

        diff_data = get_diff_between(repo, hash1, hash2)
        return diff_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diff failed: {e}")
    finally:
        session.close()


@router.get("/articles/{article_id}/blame")
async def api_get_blame(article_id: str):
    """Get git blame data for an article's main source file."""
    session = get_db_session()
    try:
        article = get_article_or_404(session, article_id)
        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo is None or not repo.exists():
            raise HTTPException(status_code=404, detail="Git repository not found")

        ext = "*.typ" if article.format == "typst" else "*.md"
        source_files = list(repo.glob(ext))
        if not source_files:
            raise HTTPException(status_code=404, detail="No source files found")

        blame_data = get_blame(repo, str(source_files[0].name))
        return {"article_id": article_id, "file": source_files[0].name, "blame": blame_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blame failed: {e}")
    finally:
        session.close()
```

- [ ] **Step 2: Remove from api_articles.py**

Delete lines 582-868 from `api_articles.py` (`_render_contribution_timeline_html` through `api_get_blame`).

Remove unused imports from `api_articles.py`:
- `get_contribution_records` (moves to api_contributions.py)
- `compute_contribution_breakdown`, `compute_contribution_timeline` (move)
- `get_commit_history`, `get_diff`, `get_diff_between`, `get_blame` (move)
- `HTMLResponse` — check if still needed in api_articles.py (it is — fork, merge proposal, and review endpoints return HTML)

- [ ] **Step 3: Register in api.py**

Add to `api.py`:
```python
from peerpedia.web.routes.api_contributions import router as contributions_router
router.include_router(contributions_router)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_api_routes.py tests/test_contribution.py tests/test_git_diff.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/api_contributions.py peerpedia/web/routes/api_articles.py peerpedia/web/routes/api.py
git commit -m "refactor: extract contribution/commit/diff/blame routes to api_contributions.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Split api_articles.py — extract api_search.py

**Files:**
- Create: `peerpedia/web/routes/api_search.py`
- Modify: `peerpedia/web/routes/api_articles.py` (remove search route)
- Modify: `peerpedia/web/routes/api.py` (register)

- [ ] **Step 1: Create api_search.py**

Extract the `api_search` route (lines 1049-1109):

```python
# peerpedia/web/routes/api_search.py
"""API route for article search."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from peerpedia.web.db_session import get_db_session
from peerpedia_core.storage.db import Article, list_articles

router = APIRouter()


@router.get("/search")
async def api_search(q: str = "", format: str = "json"):
    """Search articles by title, abstract, and keywords."""
    session = get_db_session()
    try:
        if not q.strip():
            articles = list_articles(session)
        else:
            pattern = f"%{q.strip()}%"
            articles = (
                session.query(Article)
                .filter(
                    Article.title.ilike(pattern)
                    | Article.abstract.ilike(pattern)
                    | Article.keywords.contains(q.strip())
                )
                .order_by(Article.created_at.desc())
                .limit(50)
                .all()
            )

        if format == "html":
            if not articles:
                return HTMLResponse(
                    '<p class="empty-state" style="padding:24px;">'
                    f'未找到与 "{q}" 相关的文章。</p>'
                )
            html = '<h2>文章</h2>'
            for a in articles:
                ad = a.to_dict()
                authors = ", ".join(ad.get("founding_authors", []))
                abstract = (ad.get("abstract") or "")[:200]
                status = ad.get("status", "")
                html += (
                    f'<article class="article-card">'
                    f'<h3><a href="/article/{ad["id"]}">{ad["title"]}</a></h3>'
                    f'<p class="meta">'
                    f'{authors} · {ad["format"]} · '
                    f'<span class="status {status}">{status}</span>'
                    f' · {str(ad.get("created_at", ""))[:10]}'
                    f'</p>'
                )
                if abstract:
                    html += f'<p class="abstract">{abstract}</p>'
                html += '</article>'
            return HTMLResponse(html)

        return {
            "q": q,
            "articles": [a.to_dict() for a in articles],
            "total": len(articles),
        }
    finally:
        session.close()
```

- [ ] **Step 2: Remove from api_articles.py**

Delete lines 1046-1109 from `api_articles.py` (the entire `# ── Search` section).

- [ ] **Step 3: Register in api.py**

Add to `api.py`:
```python
from peerpedia.web.routes.api_search import router as search_router
router.include_router(search_router)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && python -m pytest tests/test_api_routes.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/api_search.py peerpedia/web/routes/api_articles.py peerpedia/web/routes/api.py
git commit -m "refactor: extract search route to api_search.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Verify final state — run full test suite

- [ ] **Step 1: Clear caches and run all tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
python -m pytest tests/ -v 2>&1 | tail -40
```
Expected: all tests pass (same pass/fail count as before refactor)

- [ ] **Step 2: Verify api_articles.py line count**

```bash
wc -l peerpedia/web/routes/api_articles.py
```
Expected: ~450 lines (down from 1109)

- [ ] **Step 3: Verify new module line counts**

```bash
wc -l peerpedia/web/routes/api_comments.py peerpedia/web/routes/api_compile.py peerpedia/web/routes/api_contributions.py peerpedia/web/routes/api_search.py
```
Expected: each under 200 lines

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: final verification — all tests pass after modularization

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:** Each finding from the code review maps to a task:
- Critical #2 (db_session_scope) → Task 1, 6
- Critical #3 (sessionmaker cache) → Task 2
- Minor #13 (JSON types) → Task 3
- Important #6 (review dims) → Task 4
- Important #5 (bump_version) → Task 5
- Minor #12 (get_article_or_404) → Task 7
- Important #9 (follow-count) → Task 8
- Important #8 (ReputationV1 args) → Task 9
- Minor #15 (import blocks) → Task 10
- Critical #1 (split api_articles.py) → Tasks 11-14

**2. Placeholder scan:** No TBD, TODO, or "implement later" patterns. All code is shown inline.

**3. Type consistency:** `db_session_scope` yields `Session` throughout. `bump_minor_version` takes `str → str` in all callers. `get_article_or_404` returns `Article` or raises HTTPException. Router names are `*_router` consistently.
