# Fork → Merge (派生 → 合并) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow fork authors to propose merging changes back to the original article. Original author reviews and accepts/rejects. Credit flows both ways on merge.

**Architecture:** New MergeProposal ORM model tracks merge requests. Fork author clicks "提议合并" → original author sees proposal → approves/rejects → git merge + version bump + contribution records for both.

**Tech Stack:** Python 3.14, SQLAlchemy, GitPython, FastAPI, Jinja2, HTMX

---

## File Map

```
MODIFY:
  peerpedia_core/storage/db/models.py         — MergeProposal ORM
  peerpedia_core/storage/db/crud_article.py    — CRUD for MergeProposal
  peerpedia/web/routes/api_articles.py          — merge proposal API endpoints
  peerpedia/web/templates/article.html          — merge button on fork page + proposal list on original

NEW:
  tests/test_fork_merge.py                      — 5 tests
```

---

### Task 1: MergeProposal ORM Model

**File:** `peerpedia_core/storage/db/models.py`

- [ ] **Step 1: Add MergeProposal model**

After ReviewComment model, add:

```python
# ── ORM Model: MergeProposal ─────────────────────────────────────────────

class MergeProposal(Base):
    """Proposal to merge a fork back into the original article."""

    __tablename__ = "merge_proposals"
    __table_args__ = (
        Index("ix_mp_target", "target_article_id"),
        Index("ix_mp_fork", "fork_article_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fork_article_id = Column(String(36), ForeignKey("articles.id"), nullable=False)
    target_article_id = Column(String(36), ForeignKey("articles.id"), nullable=False)
    proposer_id = Column(String(100), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending")
    # "pending" | "approved" | "rejected" | "merged"
    reviewer_id = Column(String(100), nullable=True)
    review_comment = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fork_article_id": self.fork_article_id,
            "target_article_id": self.target_article_id,
            "proposer_id": self.proposer_id,
            "description": self.description,
            "status": self.status,
            "reviewer_id": self.reviewer_id,
            "review_comment": self.review_comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
```

- [ ] **Step 2: Export MergeProposal in __init__.py**

Add `"MergeProposal"` to the models import list in `peerpedia_core/storage/db/__init__.py`.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_db.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add peerpedia_core/storage/db/models.py peerpedia_core/storage/db/__init__.py
git commit -m "feat(db): add MergeProposal ORM model for fork→merge workflow"
```

---

### Task 2: MergeProposal CRUD

**File:** `peerpedia_core/storage/db/crud_article.py`

- [ ] **Step 1: Add CRUD functions**

After ReviewComment CRUD, add:

```python
# ── MergeProposal CRUD ────────────────────────────────────────────────────────

def create_merge_proposal(
    session: Session,
    *,
    fork_article_id: str,
    target_article_id: str,
    proposer_id: str,
    description: str = "",
) -> MergeProposal:
    """Create a merge proposal from a fork back to the original."""
    from peerpedia_core.storage.db.models import MergeProposal as MP
    proposal = MP(
        id=str(uuid.uuid4()),
        fork_article_id=fork_article_id,
        target_article_id=target_article_id,
        proposer_id=proposer_id,
        description=description,
    )
    session.add(proposal)
    return proposal


def get_merge_proposal(session: Session, proposal_id: str) -> Optional["MergeProposal"]:
    """Get a merge proposal by ID."""
    from peerpedia_core.storage.db.models import MergeProposal as MP
    return session.query(MP).filter(MP.id == proposal_id).first()


def get_merge_proposals_for_article(
    session: Session,
    article_id: str,
    *,
    status: Optional[str] = None,
) -> list:
    """Get merge proposals targeting an article, newest first."""
    from peerpedia_core.storage.db.models import MergeProposal as MP
    q = session.query(MP).filter(MP.target_article_id == article_id)
    if status:
        q = q.filter(MP.status == status)
    return q.order_by(MP.created_at.desc()).all()


def update_merge_proposal_status(
    session: Session,
    proposal_id: str,
    new_status: str,
    *,
    reviewer_id: Optional[str] = None,
    review_comment: str = "",
) -> Optional["MergeProposal"]:
    """Update a merge proposal's status."""
    proposal = get_merge_proposal(session, proposal_id)
    if proposal:
        proposal.status = new_status
        proposal.resolved_at = datetime.now(timezone.utc)
        if reviewer_id:
            proposal.reviewer_id = reviewer_id
        if review_comment:
            proposal.review_comment = review_comment
    return proposal
```

- [ ] **Step 2: Export CRUD functions**

Add to `peerpedia_core/storage/db/crud.py` and `peerpedia_core/storage/db/__init__.py`:
`create_merge_proposal`, `get_merge_proposal`, `get_merge_proposals_for_article`, `update_merge_proposal_status`.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_db.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add peerpedia_core/storage/db/
git commit -m "feat(crud): add MergeProposal CRUD operations"
```

---

### Task 3: Merge Proposal API

**File:** `peerpedia/web/routes/api_articles.py`

- [ ] **Step 1: Add API endpoints**

Add after fork endpoints:

```python
@router.post("/articles/{article_id}/merge-proposal")
async def api_create_merge_proposal(
    article_id: str,
    target_article_id: str = Form(...),
    proposer_id: str = Form(...),
    description: str = Form(""),
):
    """Propose merging this fork back into the original article."""
    from fastapi.responses import HTMLResponse

    from peerpedia_core.storage.db import (
        create_merge_proposal, get_article,
    )

    session = get_db_session()
    try:
        fork = get_article(session, article_id)
        if fork is None:
            raise HTTPException(status_code=404, detail="Fork article not found")
        if fork.forked_from != target_article_id:
            raise HTTPException(status_code=400, detail="target_article_id must match forked_from")

        target = get_article(session, target_article_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Target article not found")

        proposal = create_merge_proposal(
            session,
            fork_article_id=article_id,
            target_article_id=target_article_id,
            proposer_id=proposer_id,
            description=description,
        )
        session.commit()

        return HTMLResponse(
            f'<div style="padding:12px;background:#d1fae5;border-radius:6px;">'
            f'✓ 合并提议已提交，等待原作者审核。</div>'
            f'<script>setTimeout(function(){{location.reload()}},1200)</script>'
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/merge-proposals/{proposal_id}/review")
async def api_review_merge_proposal(
    proposal_id: str,
    reviewer_id: str = Form(...),
    decision: str = Form(...),  # "approve" or "reject"
    comment: str = Form(""),
):
    """Review (approve/reject) a merge proposal."""
    import shutil
    from pathlib import Path

    from fastapi.responses import HTMLResponse

    from peerpedia.config.settings import settings as s
    from peerpedia_core.storage.db import (
        get_merge_proposal, update_merge_proposal_status,
        get_article, update_article_version, create_contribution_record,
    )
    from peerpedia_core.workflow.contribution import compute_change_type_weight
    from peerpedia_core.storage.git_backend import commit_article, init_article_repo

    session = get_db_session()
    try:
        proposal = get_merge_proposal(session, proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if proposal.status != "pending":
            raise HTTPException(status_code=400, detail="Proposal already resolved")

        new_status = "approved" if decision == "approve" else "rejected"
        update_merge_proposal_status(
            session, proposal_id, new_status,
            reviewer_id=reviewer_id, review_comment=comment,
        )

        if decision == "approve":
            # Merge: copy fork files into original repo, commit, bump version
            fork = get_article(session, proposal.fork_article_id)
            target = get_article(session, proposal.target_article_id)
            fork_repo = Path(fork.git_repo_path) if fork and fork.git_repo_path else None
            target_repo = Path(target.git_repo_path) if target and target.git_repo_path else None

            if fork_repo and target_repo:
                # Copy files from fork to target
                for f in fork_repo.glob("*.md"):
                    shutil.copy2(f, target_repo / f.name)
                for f in fork_repo.glob("*.typ"):
                    shutil.copy2(f, target_repo / f.name)
                commit_article(
                    target_repo,
                    f"Merge: {proposal.description or 'Merge from fork'} by {proposal.proposer_id}",
                    author_name=reviewer_id,
                    author_email=f"{reviewer_id}@peerpedia.local",
                )

            # Bump version
            new_version = _bump_version(target.version)
            update_article_version(session, proposal.target_article_id, new_version)

            # Contribution records for both
            weight = compute_change_type_weight("content")
            create_contribution_record(
                session, article_id=proposal.target_article_id,
                user_id=proposal.proposer_id, commit_hash="merge",
                commit_message=f"Merge proposal: {proposal.description[:80]}",
                change_type="content", contribution_weight=weight,
            )
            # Add proportional credit to original author for accepting
            create_contribution_record(
                session, article_id=proposal.target_article_id,
                user_id=reviewer_id, commit_hash="merge-review",
                commit_message=f"Reviewed merge from {proposal.proposer_id}",
                change_type="content", contribution_weight=weight // 2,
            )

            proposal.status = "merged"
            update_article_founding_authors(session, proposal.target_article_id, proposal.proposer_id)

        session.commit()

        return HTMLResponse(
            f'<div style="padding:12px;background:#d1fae5;border-radius:6px;">'
            f'✓ {decision} — 合并完成</div>'
            f'<script>setTimeout(function(){{location.reload()}},1200)</script>'
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


def _bump_version(version_str: str) -> str:
    """Bump minor version: v0.1 → v0.2, v1.5 → v1.6."""
    try:
        parts = version_str.lstrip("v").split(".")
        return f"v{parts[0]}.{int(parts[1]) + 1}"
    except Exception:
        return "v0.2"
```

- [ ] **Step 2: Import needed modules**

Ensure `update_article_founding_authors` is imported or accessible in api_articles.py.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_api_routes.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add peerpedia/web/routes/api_articles.py
git commit -m "feat(api): add merge proposal create + review endpoints"
```

---

### Task 4: UI — Merge Buttons on Fork Page

**File:** `peerpedia/web/templates/article.html`

- [ ] **Step 1: Add "提议合并" button on fork articles**

After the fork chain display, add (only when article has `forked_from`):

```html
            {% if article.forked_from and viewer and article.status == 'published' %}
            <div style="margin-bottom:12px;">
                <button onclick="showMergeForm()"
                        style="padding:6px 14px;background:#6366f1;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.9em;">
                    🔄 提议合并回原文
                </button>
                <div id="merge-form" style="display:none;margin-top:8px;padding:12px;background:#f8f9fa;border-radius:6px;">
                    <form onsubmit="submitMerge(event, '{{ article.id }}', '{{ article.forked_from }}', '{{ viewer }}')">
                        <label>改动描述:
                            <textarea name="description" rows="3" placeholder="简述你做了哪些改动..."
                                style="width:100%;margin-top:4px;"></textarea>
                        </label>
                        <button type="submit" style="margin-top:6px;">提交合并提议</button>
                    </form>
                    <span id="merge-status" style="margin-left:8px;font-size:0.85em;"></span>
                </div>
            </div>
            <script>
            function showMergeForm() {
                document.getElementById('merge-form').style.display = 'block';
            }
            function submitMerge(event, forkId, targetId, proposerId) {
                event.preventDefault();
                var desc = event.target.querySelector('textarea').value;
                var status = document.getElementById('merge-status');
                status.textContent = '提交中...';
                var formData = new URLSearchParams();
                formData.append('target_article_id', targetId);
                formData.append('proposer_id', proposerId);
                formData.append('description', desc);
                fetch('/api/v1/articles/' + forkId + '/merge-proposal', {
                    method: 'POST', body: formData
                }).then(function(r) { return r.text(); })
                  .then(function(html) {
                      status.innerHTML = html;
                      setTimeout(function() { location.reload(); }, 1500);
                  });
            }
            </script>
            {% endif %}
```

- [ ] **Step 2: Add merge proposal list on original article**

After the fork chain display, add (only when article has `fork_count > 0`):

```html
            {% if article.fork_count and article.fork_count > 0 %}
            <div id="merge-proposals"
                 hx-get="/api/v1/articles/{{ article.id }}/merge-proposals?format=html"
                 hx-trigger="load" hx-swap="innerHTML"
                 style="margin-bottom:12px;font-size:0.85em;">
            </div>
            {% endif %}
```

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/templates/article.html
git commit -m "feat(ui): add merge proposal button and list on fork/original pages"
```

---

### Task 5: Merge Proposal List Endpoint (HTML)

**File:** `peerpedia/web/routes/api_articles.py`

- [ ] **Step 1: Add HTML endpoint for merge proposal list**

```python
@router.get("/articles/{article_id}/merge-proposals")
async def api_get_merge_proposals(article_id: str, format: str = "json"):
    """Get merge proposals targeting an article."""
    from fastapi.responses import HTMLResponse

    from peerpedia_core.storage.db import get_merge_proposals_for_article, get_article

    session = get_db_session()
    try:
        proposals = get_merge_proposals_for_article(session, article_id)
        if format == "html":
            if not proposals:
                return HTMLResponse("")
            html = '<div style="margin-top:8px;"><strong>🔄 合并提议</strong>'
            for p in proposals:
                status_label = {"pending": "⏳ 待审核", "approved": "✅ 已批准", "rejected": "❌ 已拒绝", "merged": "🔀 已合并"}.get(p.status, p.status)
                html += (
                    f'<div style="padding:6px 8px;margin:4px 0;background:#fff;'
                    f'border:1px solid var(--border);border-radius:4px;">'
                    f'{status_label} · <strong>{p.proposer_id}</strong>'
                    f' · <a href="/article/{p.fork_article_id}">查看派生</a>'
                )
                if p.status == "pending" and viewer:
                    # Show approve/reject buttons for original author
                    is_target_author = viewer in (article.founding_authors if article else [])
                    if is_target_author:
                        html += (
                            f'<div style="margin-top:4px;">'
                            f'<button onclick="reviewMerge(\'{p.id}\', \'approve\', \'{viewer}\')" '
                            f'style="padding:2px 8px;background:#16a34a;color:#fff;border:none;border-radius:3px;font-size:0.75em;cursor:pointer;">✓ 同意合并</button> '
                            f'<button onclick="reviewMerge(\'{p.id}\', \'reject\', \'{viewer}\')" '
                            f'style="padding:2px 8px;background:#dc2626;color:#fff;border:none;border-radius:3px;font-size:0.75em;cursor:pointer;">✗ 拒绝</button>'
                            f'</div>'
                        )
                if p.description:
                    html += f'<div style="color:#666;font-size:0.85em;">{p.description[:200]}</div>'
                html += '</div>'
            html += '</div>'
            return HTMLResponse(html)
        return {"article_id": article_id, "proposals": [p.to_dict() for p in proposals], "total": len(proposals)}
    finally:
        session.close()
```

Also add the `reviewMerge` JS function in a script block:

```html
<script>
function reviewMerge(proposalId, decision, reviewerId) {
    var formData = new URLSearchParams();
    formData.append('reviewer_id', reviewerId);
    formData.append('decision', decision);
    fetch('/api/v1/merge-proposals/' + proposalId + '/review', {
        method: 'POST', body: formData
    }).then(function(r) { return r.text(); })
      .then(function() { location.reload(); });
}
</script>
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -q
```

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/routes/api_articles.py
git commit -m "feat(api): add merge proposal list HTML endpoint with approve/reject"
```

---

### Task 6: Tests

**File:** `tests/test_fork_merge.py` (new)

- [ ] **Step 1: Write tests**

```python
"""Tests for fork → merge workflow."""
import pytest
import tempfile
from pathlib import Path

from peerpedia.submit import submit_article
from peerpedia_core.storage.db import (
    get_engine, init_db, get_session, get_article,
    create_merge_proposal, get_merge_proposal,
    get_merge_proposals_for_article, update_merge_proposal_status,
    update_article_status,
)


class TestMergeProposalCRUD:
    """MergeProposal CRUD operations."""

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

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)

            p = create_merge_proposal(session, fork_article_id=r2.article_id, target_article_id=r1.article_id, proposer_id="bob")
            session.commit()

            updated = update_merge_proposal_status(session, p.id, "approved", reviewer_id="alice", review_comment="Looks good.")
            session.commit()

            assert updated is not None
            assert updated.status == "approved"
            assert updated.reviewer_id == "alice"
            assert updated.review_comment == "Looks good."
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
    """API endpoints for merge proposals."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from peerpedia.web.app import app
        return TestClient(app)

    def test_create_merge_proposal(self, client):
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
            # Set forked_from on r2
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

                # Verify proposal exists
                engine2 = get_engine(f"sqlite:///{db_path}")
                init_db(engine2)
                session2 = get_session(engine2)
                proposals = get_merge_proposals_for_article(session2, r1.article_id)
                assert len(proposals) == 1
                assert proposals[0].status == "pending"
                session2.close()
            finally:
                settings.database_url = original_url

    def test_review_merge_proposal(self, client):
        """POST review merge-proposal approves or rejects."""
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
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_fork_merge.py -v
```
Expected: 5 passed.

- [ ] **Step 3: Run full suite**

```bash
pytest tests/ -q
```
Expected: 361 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_fork_merge.py
git commit -m "test: add 5 tests for fork→merge workflow"
```

---

## Summary

| Task | What | Files | Tests |
|------|------|-------|-------|
| 1 | MergeProposal ORM | `models.py` | — |
| 2 | CRUD functions | `crud_article.py` | — |
| 3 | API endpoints | `api_articles.py` | — |
| 4 | UI buttons | `article.html` | — |
| 5 | Proposal list HTML | `api_articles.py` | — |
| 6 | Tests | `test_fork_merge.py` (new) | 5 |
