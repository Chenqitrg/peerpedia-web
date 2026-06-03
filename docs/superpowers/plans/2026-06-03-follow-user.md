# Follow User — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user follow relationships, follow/unfollow API, following feed, and HTMX-driven follow button on user profiles and index page tabs.

**Architecture:** Follow ORM with composite PK (follower_id, followed_id). CRUD functions in existing db layer. API endpoints added to api_users.py. Templates use HTMX for button swap and lazy loading. No new files.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, Jinja2/HTMX

---

### Task 1: Follow ORM + CRUD + Tests

**Files:**
- Modify: `peerpedia_core/storage/db/models.py`
- Modify: `peerpedia_core/storage/db/crud.py`
- Modify: `peerpedia_core/storage/db/__init__.py`
- Create: `tests/test_follow.py`

- [ ] **Step 1: Add Follow ORM model**

In `peerpedia_core/storage/db/models.py`, after the `NodeInfo` class, add:

```python
# ── ORM Model: Follow ───────────────────────────────────────────────────────

class Follow(Base):
    """Follow relationship between users."""

    __tablename__ = "follows"

    follower_id = Column(String(100), ForeignKey("users.id"), primary_key=True)
    followed_id = Column(String(100), ForeignKey("users.id"), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "follower_id": self.follower_id,
            "followed_id": self.followed_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 2: Add Follow CRUD functions**

In `peerpedia_core/storage/db/crud.py`, append:

```python
# ── Follow CRUD ─────────────────────────────────────────────────────────────

def follow_user(
    session: Session,
    *,
    follower_id: str,
    followed_id: str,
) -> "Follow":
    """Create a follow relationship. Raises IntegrityError on duplicate."""
    from peerpedia_core.storage.db.models import Follow
    from sqlalchemy.exc import IntegrityError

    follow = Follow(
        follower_id=follower_id,
        followed_id=followed_id,
    )
    session.add(follow)
    session.flush()  # Trigger IntegrityError immediately
    return follow


def unfollow_user(
    session: Session,
    *,
    follower_id: str,
    followed_id: str,
) -> bool:
    """Remove a follow relationship. Returns True if a row was deleted."""
    from peerpedia_core.storage.db.models import Follow

    result = (
        session.query(Follow)
        .filter(
            Follow.follower_id == follower_id,
            Follow.followed_id == followed_id,
        )
        .delete()
    )
    return result > 0


def is_following(
    session: Session,
    follower_id: str,
    followed_id: str,
) -> bool:
    """Check if follower_id follows followed_id."""
    from peerpedia_core.storage.db.models import Follow

    return (
        session.query(Follow)
        .filter(
            Follow.follower_id == follower_id,
            Follow.followed_id == followed_id,
        )
        .first()
        is not None
    )


def get_following(
    session: Session,
    user_id: str,
) -> list["Follow"]:
    """Get users that user_id follows, newest first."""
    from peerpedia_core.storage.db.models import Follow

    return (
        session.query(Follow)
        .filter(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc())
        .all()
    )


def get_followers(
    session: Session,
    user_id: str,
) -> list["Follow"]:
    """Get users that follow user_id, newest first."""
    from peerpedia_core.storage.db.models import Follow

    return (
        session.query(Follow)
        .filter(Follow.followed_id == user_id)
        .order_by(Follow.created_at.desc())
        .all()
    )


def get_following_count(session: Session, user_id: str) -> int:
    """Count how many users user_id follows."""
    from peerpedia_core.storage.db.models import Follow

    return (
        session.query(Follow)
        .filter(Follow.follower_id == user_id)
        .count()
    )


def get_follower_count(session: Session, user_id: str) -> int:
    """Count how many users follow user_id."""
    from peerpedia_core.storage.db.models import Follow

    return (
        session.query(Follow)
        .filter(Follow.followed_id == user_id)
        .count()
    )
```

- [ ] **Step 3: Update __init__.py exports**

In `peerpedia_core/storage/db/__init__.py`:

Add `Follow` to models import, add all 7 CRUD functions to crud import, add to `__all__`:
```python
# models
from peerpedia_core.storage.db.models import (
    # ... existing ...
    Follow,
)

# crud
from peerpedia_core.storage.db.crud import (
    # ... existing ...
    follow_user,
    unfollow_user,
    is_following,
    get_following,
    get_followers,
    get_following_count,
    get_follower_count,
)

# __all__
    "Follow",
    "follow_user",
    "unfollow_user",
    "is_following",
    "get_following",
    "get_followers",
    "get_following_count",
    "get_follower_count",
```

- [ ] **Step 4: Write test_follow.py — DB layer tests**

Create `tests/test_follow.py`:

```python
"""Tests for user follow system."""
import pytest
from sqlalchemy.exc import IntegrityError

from peerpedia_core.storage.db import (
    get_engine,
    init_db,
    get_session,
    create_user,
    follow_user,
    unfollow_user,
    is_following,
    get_following,
    get_followers,
    get_following_count,
    get_follower_count,
)


@pytest.fixture
def db_url():
    return "sqlite:///:memory:"


@pytest.fixture
def engine(db_url):
    eng = get_engine(db_url)
    init_db(eng)
    return eng


@pytest.fixture
def users(engine):
    session = get_session(engine)
    create_user(session, id="alice", name="Alice", email="alice@test.com")
    create_user(session, id="bob", name="Bob", email="bob@test.com")
    create_user(session, id="charlie", name="Charlie", email="charlie@test.com")
    session.commit()
    session.close()


class TestFollowCRUD:

    def test_follow_user(self, engine, users):
        session = get_session(engine)
        follow = follow_user(session, follower_id="alice", followed_id="bob")
        session.commit()
        assert follow.follower_id == "alice"
        assert follow.followed_id == "bob"
        session.close()

    def test_unfollow_user(self, engine, users):
        session = get_session(engine)
        follow_user(session, follower_id="alice", followed_id="bob")
        session.commit()

        result = unfollow_user(session, follower_id="alice", followed_id="bob")
        session.commit()
        assert result is True
        assert not is_following(session, "alice", "bob")
        session.close()

    def test_unfollow_nonexistent(self, engine, users):
        session = get_session(engine)
        result = unfollow_user(session, follower_id="alice", followed_id="bob")
        session.commit()
        assert result is False
        session.close()

    def test_duplicate_follow_raises(self, engine, users):
        session = get_session(engine)
        follow_user(session, follower_id="alice", followed_id="bob")
        session.commit()
        with pytest.raises(IntegrityError):
            follow_user(session, follower_id="alice", followed_id="bob")
            session.flush()
        session.rollback()
        session.close()

    def test_is_following(self, engine, users):
        session = get_session(engine)
        assert not is_following(session, "alice", "bob")
        follow_user(session, follower_id="alice", followed_id="bob")
        session.commit()
        assert is_following(session, "alice", "bob")
        session.close()

    def test_get_following(self, engine, users):
        session = get_session(engine)
        follow_user(session, follower_id="alice", followed_id="bob")
        follow_user(session, follower_id="alice", followed_id="charlie")
        session.commit()

        following = get_following(session, "alice")
        assert len(following) == 2
        followed_ids = {f.followed_id for f in following}
        assert followed_ids == {"bob", "charlie"}
        session.close()

    def test_get_followers(self, engine, users):
        session = get_session(engine)
        follow_user(session, follower_id="alice", followed_id="charlie")
        follow_user(session, follower_id="bob", followed_id="charlie")
        session.commit()

        followers = get_followers(session, "charlie")
        assert len(followers) == 2
        follower_ids = {f.follower_id for f in followers}
        assert follower_ids == {"alice", "bob"}
        session.close()

    def test_counts(self, engine, users):
        session = get_session(engine)
        follow_user(session, follower_id="alice", followed_id="bob")
        follow_user(session, follower_id="alice", followed_id="charlie")
        follow_user(session, follower_id="bob", followed_id="alice")
        session.commit()

        assert get_following_count(session, "alice") == 2
        assert get_follower_count(session, "alice") == 1
        assert get_following_count(session, "charlie") == 0
        assert get_follower_count(session, "charlie") == 1
        session.close()
```

- [ ] **Step 5: Run DB tests**

```bash
cd ~/Projects/peerpedia && source .venv/bin/activate && python -m pytest tests/test_follow.py -v
```
Expected: 8 passed

- [ ] **Step 6: Run full suite**

```bash
cd ~/Projects/peerpedia && source .venv/bin/activate && python -m pytest tests/ -q
```
Expected: ~204 passed

- [ ] **Step 7: Commit**

```bash
git add peerpedia_core/storage/db/models.py peerpedia_core/storage/db/crud.py peerpedia_core/storage/db/__init__.py tests/test_follow.py
git commit -m "feat(db): add Follow ORM model with 7 CRUD functions

- Follow: composite PK (follower_id, followed_id) FK users.id
- follow_user, unfollow_user, is_following
- get_following, get_followers, get_following_count, get_follower_count

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Follow API Endpoints + Feed

**Files:**
- Modify: `peerpedia/web/routes/api_users.py`
- Modify: `tests/test_follow.py` (append)

- [ ] **Step 1: Add follow API endpoints to api_users.py**

Read `peerpedia/web/routes/api_users.py` to understand the existing router. Then append:

```python
# ── Follow ───────────────────────────────────────────────────────────────────

@router.post("/users/{user_id}/follow")
async def api_follow_user(user_id: str, follower_id: str = Form(...)):
    """Follow a user."""
    from peerpedia_core.storage.db import (
        follow_user,
        get_user,
        get_follower_count,
        get_following_count,
    )
    from sqlalchemy.exc import IntegrityError

    session = get_db_session()
    try:
        target = get_user(session, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            follow_user(session, follower_id=follower_id, followed_id=user_id)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="Already following")

        follower_count = get_follower_count(session, user_id)
        following_count = get_following_count(session, user_id)

        return {
            "status": "following",
            "follower_count": follower_count,
            "following_count": following_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/users/{user_id}/follow")
async def api_unfollow_user(user_id: str, follower_id: str = Form(...)):
    """Unfollow a user."""
    from peerpedia_core.storage.db import (
        unfollow_user,
        get_user,
        get_follower_count,
        get_following_count,
    )

    session = get_db_session()
    try:
        target = get_user(session, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")

        unfollow_user(session, follower_id=follower_id, followed_id=user_id)
        session.commit()

        follower_count = get_follower_count(session, user_id)
        following_count = get_following_count(session, user_id)

        return {
            "status": "not_following",
            "follower_count": follower_count,
            "following_count": following_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/users/{user_id}/following")
async def api_get_following(user_id: str):
    """Get users that user_id follows."""
    from peerpedia_core.storage.db import get_following, get_user

    session = get_db_session()
    try:
        target = get_user(session, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")

        following = get_following(session, user_id)
        return {
            "user_id": user_id,
            "users": [
                {
                    "user_id": f.followed_id,
                    "followed_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in following
            ],
            "total": len(following),
        }
    finally:
        session.close()


@router.get("/users/{user_id}/followers")
async def api_get_followers(user_id: str):
    """Get users that follow user_id."""
    from peerpedia_core.storage.db import get_followers, get_user

    session = get_db_session()
    try:
        target = get_user(session, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")

        followers = get_followers(session, user_id)
        return {
            "user_id": user_id,
            "users": [
                {
                    "user_id": f.follower_id,
                    "followed_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in followers
            ],
            "total": len(followers),
        }
    finally:
        session.close()


@router.get("/following/feed")
async def api_following_feed(user_id: str):
    """Get activity feed from followed users (last 30 days)."""
    from datetime import datetime, timezone, timedelta
    from peerpedia_core.storage.db import (
        get_following,
        get_article,
        Article,
    )

    session = get_db_session()
    try:
        following = get_following(session, user_id)
        followed_ids = [f.followed_id for f in following]

        if not followed_ids:
            return {"user_id": user_id, "events": []}

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        events = []

        for fid in followed_ids:
            # New articles by followed user
            articles = (
                session.query(Article)
                .filter(
                    Article.founding_authors.contains(fid),
                    Article.created_at >= cutoff,
                )
                .order_by(Article.created_at.desc())
                .all()
            )
            for a in articles:
                events.append({
                    "type": "new_article",
                    "user_id": fid,
                    "article_id": a.id,
                    "article_title": a.title,
                    "time": a.created_at.isoformat() if a.created_at else "",
                })

            # Version updates by followed user
            updated = (
                session.query(Article)
                .filter(
                    Article.founding_authors.contains(fid),
                    Article.updated_at >= cutoff,
                    Article.version > "v0.1",
                )
                .order_by(Article.updated_at.desc())
                .all()
            )
            for a in updated:
                # Avoid duplicate if same article appears in new_articles
                if a.created_at and a.created_at >= cutoff:
                    continue
                events.append({
                    "type": "new_version",
                    "user_id": fid,
                    "article_id": a.id,
                    "article_title": a.title,
                    "version": a.version,
                    "time": a.updated_at.isoformat() if a.updated_at else "",
                })

        # Sort by time descending, limit to 50
        events.sort(key=lambda e: e["time"], reverse=True)
        return {"user_id": user_id, "events": events[:50]}
    finally:
        session.close()
```

- [ ] **Step 2: Append API tests to test_follow.py**

```python
from fastapi.testclient import TestClient


class TestFollowAPI:

    @pytest.fixture
    def client(self):
        from peerpedia.web.app import app
        return TestClient(app)

    def test_follow_user(self, client, users):
        """POST /api/v1/users/{id}/follow creates follow relationship."""
        resp = client.post("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "following"
        assert data["follower_count"] >= 0

    def test_unfollow_user(self, client, users):
        """DELETE /api/v1/users/{id}/follow removes follow."""
        client.post("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        resp = client.delete("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_following"

    def test_follow_nonexistent_user(self, client, users):
        """Follow nonexistent user returns 404."""
        resp = client.post("/api/v1/users/nobody/follow", data={"follower_id": "alice"})
        assert resp.status_code == 404

    def test_duplicate_follow_returns_409(self, client, users):
        """Duplicate follow returns 409."""
        client.post("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        resp = client.post("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        assert resp.status_code == 409

    def test_get_following(self, client, users):
        """GET /api/v1/users/{id}/following returns list."""
        client.post("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        resp = client.get("/api/v1/users/alice/following")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_get_followers(self, client, users):
        """GET /api/v1/users/{id}/followers returns list."""
        client.post("/api/v1/users/bob/follow", data={"follower_id": "alice"})
        resp = client.get("/api/v1/users/bob/followers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_feed(self, client, users):
        """GET /api/v1/following/feed returns events."""
        resp = client.get("/api/v1/following/feed?user_id=alice")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)
```

Note: the `users` fixture is already in test_follow.py. The API tests need the users to exist in DB. Make sure the TestClient can access the in-memory DB — the web app uses `settings.database_url` which points to the default SQLite file. For TestClient tests, you may need to patch the DB URL or use a separate mechanism. Check how existing tests handle this (see `test_user_api.py` for the pattern).

The simplest approach: since existing `test_user_api.py` tests already use `TestClient` and the real DB, follow the same pattern. The `users` fixture creates users in the in-memory DB — but the app connects to the real SQLite file. So these API tests should create users through the API instead.

Adjust the TestFollowAPI class to NOT depend on the `users` fixture:

```python
class TestFollowAPI:

    @pytest.fixture(autouse=True)
    def setup_users(self):
        """Create test users via API."""
        from peerpedia.web.app import app
        client = TestClient(app)
        for uid, name in [("alice", "Alice"), ("bob", "Bob"), ("charlie", "Charlie")]:
            client.post("/api/v1/users", json={
                "id": uid, "name": name, "email": f"{uid}@test.com"
            })
        return client

    @pytest.fixture
    def client(self):
        from peerpedia.web.app import app
        return TestClient(app)

    # ... tests using self.client ...
```

- [ ] **Step 3: Run all tests**

```bash
cd ~/Projects/peerpedia && source .venv/bin/activate && python -m pytest tests/test_follow.py tests/ -v
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add peerpedia/web/routes/api_users.py tests/test_follow.py
git commit -m "feat(api): add follow/unfollow API endpoints and following feed

- POST /api/v1/users/{id}/follow — follow a user
- DELETE /api/v1/users/{id}/follow — unfollow
- GET /api/v1/users/{id}/following — who user follows
- GET /api/v1/users/{id}/followers — who follows user
- GET /api/v1/following/feed — 30-day activity feed

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: UI — Follow Button + Feed Tab

**Files:**
- Modify: `peerpedia/web/routes/pages.py`
- Modify: `peerpedia/web/templates/user.html`
- Modify: `peerpedia/web/templates/index.html`

- [ ] **Step 1: Update pages.py — pass follow state to user page**

In `peerpedia/web/routes/pages.py`, in the `user_profile` function, add follow state computation. After computing `reputation`, add:

```python
        # Follow state (for the follow button)
        is_self = False
        is_following_user = False
        current_user_id = request.query_params.get("viewer", "")
        if current_user_id and current_user_id != user_id:
            from peerpedia_core.storage.db import is_following, get_following_count, get_follower_count
            is_following_user = is_following(session, current_user_id, user_id)
            following_count = get_following_count(session, user_id)
            follower_count = get_follower_count(session, user_id)
        elif current_user_id == user_id:
            is_self = True
            from peerpedia_core.storage.db import get_following_count, get_follower_count
            following_count = get_following_count(session, user_id)
            follower_count = get_follower_count(session, user_id)
        else:
            following_count = 0
            follower_count = 0
```

Add these to the template context:
```python
                "is_self": is_self,
                "is_following": is_following_user,
                "current_user": current_user_id,
                "following_count": following_count,
                "follower_count": follower_count,
```

Also update the `home` route to support the `tab` parameter:

```python
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page — article listing from database."""
    session = get_db_session()
    try:
        tab = request.query_params.get("tab", "all")
        viewer = request.query_params.get("user", "")
        articles = list_articles(session)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": "PeerPedia",
                "articles": [a.to_dict() for a in articles],
                "tab": tab,
                "viewer": viewer,
            },
        )
    finally:
        session.close()
```

- [ ] **Step 2: Update user.html — add follow button + counts**

In `peerpedia/web/templates/user.html`, after the user name heading, add:

```html
{% if not is_self and current_user %}
<div id="follow-area" style="margin-bottom: 12px;">
  {% if is_following %}
  <button hx-delete="/api/v1/users/{{ user_id }}/follow"
          hx-vals='{"follower_id": "{{ current_user }}"}'
          hx-target="#follow-area"
          hx-swap="outerHTML"
          style="background: #28a745; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer;">
    已关注 ✓
  </button>
  {% else %}
  <button hx-post="/api/v1/users/{{ user_id }}/follow"
          hx-vals='{"follower_id": "{{ current_user }}"}'
          hx-target="#follow-area"
          hx-swap="outerHTML"
          style="background: #007bff; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer;">
    + 关注
  </button>
  {% endif %}
</div>
{% elif is_self %}
<div style="margin-bottom: 12px; color: #888;">
  粉丝 {{ follower_count }} · 关注了 {{ following_count }}
</div>
{% endif %}
```

Also add a server-side handler for the HTMX response: when POST returns `{"status": "following", ...}`, the button should swap to "已关注". When DELETE returns `{"status": "not_following", ...}`, swap to "+ 关注".

The simplest HTMX approach: the follow/unfollow API methods render a tiny HTML snippet instead of JSON for the button. But that mixes API and UI. Better: use HTMX response headers or keep the API as JSON and use the `hx-swap` with a small client-side template.

Simplest correct approach: make the follow/unfollow API return HTML directly:

```python
@router.post("/users/{user_id}/follow")
async def api_follow_user(user_id: str, follower_id: str = Form(...)):
    # ... validation ...
    # After success:
    return HTMLResponse(f'''
    <div id="follow-area" style="margin-bottom: 12px;">
      <button hx-delete="/api/v1/users/{user_id}/follow"
              hx-vals='{{"follower_id": "{follower_id}"}}'
              hx-target="#follow-area"
              hx-swap="outerHTML"
              style="background: #28a745; color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer;">
        已关注 ✓
      </button>
    </div>
    ''')
```

Same pattern for DELETE returning the "+ 关注" button HTML. This keeps it simple — HTML in, HTML out.

- [ ] **Step 3: Update index.html — add tab navigation**

In `peerpedia/web/templates/index.html`, above the article list, add:

```html
<nav class="tabs" style="margin-bottom: 16px; border-bottom: 2px solid #eee;">
  <a href="/" style="padding: 8px 16px; text-decoration: none; {{ 'border-bottom: 2px solid #007bff; color: #007bff;' if tab == 'all' else 'color: #666;' }}">全部文章</a>
  {% if viewer %}
  <a href="/?tab=following&user={{ viewer }}" style="padding: 8px 16px; text-decoration: none; {{ 'border-bottom: 2px solid #007bff; color: #007bff;' if tab == 'following' else 'color: #666;' }}">关注动态</a>
  {% endif %}
</nav>

{% if tab == 'following' and viewer %}
<div id="following-feed"
     hx-get="/api/v1/following/feed?user_id={{ viewer }}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <p>加载中...</p>
</div>
{% else %}
<!-- existing article list -->
{% endif %}
```

- [ ] **Step 4: Run all tests**

```bash
cd ~/Projects/peerpedia && source .venv/bin/activate && python -m pytest tests/ -q
```
Expected: all pass (~208 tests)

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/pages.py peerpedia/web/templates/user.html peerpedia/web/templates/index.html
git commit -m "feat(ui): add follow button, fan counts, and following feed tab

- User profile: follow/unfollow button (HTMX swap)
- User profile: follower/following counts
- Home page: tab toggle between all articles and following feed
- Following feed: HTMX lazy-load from /api/v1/following/feed

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
