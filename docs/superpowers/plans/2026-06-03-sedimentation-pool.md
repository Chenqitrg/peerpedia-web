# Sedimentation Pool (沉淀池) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the review/decide workflow with a sedimentation pool model: anonymous ratings + discussion, auto-publish based on weighted sink score.

**Architecture:** Simplify Review model (drop scientific_correctness/clarity from UI, keep decision as internal "pool_comment"). Remove decide API. Add sink score calculation in pages.py. Rename "审稿队列" to "沉淀池".

**Tech Stack:** Python 3.14, FastAPI, Jinja2, HTMX, SQLAlchemy

---

### Task 1: Fix Failing Tests

**Files:** `tests/test_web_pages.py`

Two tests fail because collaboration checkbox and message field were removed from review.html. Update tests to match new UI.

- [ ] **Step 1: Fix test_review_page_has_collaboration_checkbox**

```python
    def test_review_page_has_collaboration_checkbox(self):
        """Review page still has the collaboration request checkbox."""
        with tempfile.TemporaryDirectory() as tmp:
            db_url, article_id = _setup_db_with_article(tmp, author="alice")
            with mock.patch("peerpedia.web.db_session.settings.database_url", db_url):
                client = TestClient(app)
                resp = client.get(f"/review/{article_id}?viewer=bob")
                assert resp.status_code == 200
                html = resp.text
                assert '发表评分' in html, f"Should have submit button: {html}"
```

- [ ] **Step 2: Fix test_collaboration_message_field_present**

```python
    def test_collaboration_message_field_present(self):
        """Review page should have a comments textarea for discussion."""
        with tempfile.TemporaryDirectory() as tmp:
            db_url, article_id = _setup_db_with_article(tmp, author="alice")
            with mock.patch("peerpedia.web.db_session.settings.database_url", db_url):
                client = TestClient(app)
                resp = client.get(f"/review/{article_id}?viewer=bob")
                assert resp.status_code == 200
                html = resp.text
                assert 'textarea' in html, f"Should have comment textarea: {html}"
                assert '五维评分' in html, f"Should have rating section: {html}"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_web_pages.py::TestCollaborationButtonOnReview -v
```
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_web_pages.py
git commit -m "fix: update collaboration tests for sedimentation pool UI"
```

---

### Task 2: Rename Review Queue → 沉淀池

**Files:** `peerpedia/web/templates/index.html`, `peerpedia/web/templates/review.html`, `peerpedia/web/templates/article.html`

- [ ] **Step 1: Rename nav link in all templates**

In index.html, article.html, review.html, submit.html, user.html — change:
```html
<a href="/review">审稿队列</a>
```
to:
```html
<a href="/review">🌊 沉淀池</a>
```

- [ ] **Step 2: Rename page title in review.html queue view**

Find `{% elif articles is defined and articles %}` section header:

```html
        <h2>🌊 沉淀池</h2>
        <p>{{ articles | length }} 篇文章等待评分。</p>
```

- [ ] **Step 3: Rename empty state**

```html
        <h2>🌊 沉淀池</h2>
        <p class="empty-state">沉淀池为空。<a href="/submit">提交第一篇。</a></p>
```

- [ ] **Step 4: Commit**

```bash
git add peerpedia/web/templates/
git commit -m "ui: rename 审稿队列 to 沉淀池"
```

---

### Task 3: Sink Score Calculation + Auto-Publish

**Files:** `peerpedia/web/routes/pages.py`

- [ ] **Step 1: Add sink score calculation to review_article_page**

Add after `reviews = get_reviews_for_article(session, article_id)`:

```python
        # Compute sink progress
        sink_pct = 0
        days_left = 7
        if reviews:
            dims = ["originality", "rigor", "completeness", "pedagogy", "impact"]
            scores = []
            for r in reviews:
                vals = [getattr(r, f"review_{d}", 0) for d in dims]
                if any(v > 0 for v in vals):
                    scores.append(sum(vals) / len(vals))
            if scores:
                avg = sum(scores) / len(scores)
                # Score 5.0 → 2 days, Score 1.0 → 180 days
                base_days = 7
                days_left = max(2, min(180, int(base_days * 5.0 / max(avg, 0.01))))
                elapsed = (base_days - days_left) if days_left < base_days else 0
                total = max(base_days, days_left)
                sink_pct = min(95, int((1 - days_left / max(base_days, 1)) * 100))
        else:
            # No reviews yet — full 7 days
            from datetime import datetime, timezone
            if article.created_at:
                age_days = (datetime.now(timezone.utc) - article.created_at).days
                days_left = max(0, 7 - age_days)
                sink_pct = min(95, int((age_days / 7) * 100))
```

- [ ] **Step 2: Pass sink_pct and days_left to template**

Add to context:
```python
                "sink_pct": sink_pct,
                "days_left": days_left,
```

- [ ] **Step 3: Auto-publish check**

After sink calculation, if `days_left <= 0`:

```python
        if days_left <= 0 and article.status == "submitted":
            update_article_status(session, article.id, "published")
            session.commit()
            article = get_article(session, article_id)  # refresh
```

- [ ] **Step 4: Run tests and verify**

```bash
pytest tests/test_web_pages.py -v
```

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/pages.py
git commit -m "feat: add sink score calculation + auto-publish to sedimentation pool"
```

---

### Task 4: Remove Decide API / Update Review API

**Files:** `peerpedia/web/routes/api_articles.py`

- [ ] **Step 1: Remove decide endpoint**

Remove `@router.post("/articles/{article_id}/decide")` and `api_decide_article()` function.

- [ ] **Step 2: Update review submit response for new UI**

In `api_submit_review`, change the HTML response to match new thread format:

```python
    return HTMLResponse(
        f'<div style="padding:12px;background:#d1fae5;border-radius:6px;margin-top:8px;">'
        f'<strong>✓ 评分已发表</strong> · 身份: 匿名者_{reviewer_id[:4].upper()}</div>'
        f'<script>setTimeout(function(){{location.reload()}},800)</script>'
    )
```

- [ ] **Step 3: Update review queue page route**

In pages.py `review_queue`, filter `status="submitted"` articles and pass sink data:

```python
@router.get("/review", response_class=HTMLResponse)
async def review_queue(request: Request):
    session = get_db_session()
    viewer = get_viewer(request)
    try:
        articles = list_articles(session, status="submitted")
        return templates.TemplateResponse(
            request=request, name="review.html",
            context={"request": request, "title": "沉淀池",
                     "articles": [a.to_dict() for a in articles],
                     "viewer": viewer, "all_users": get_all_users()},
        )
    finally:
        session.close()
```

- [ ] **Step 4: Run full tests**

```bash
pytest tests/ -q
```
Expected: all passing (353+)

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/api_articles.py peerpedia/web/routes/pages.py
git commit -m "refactor: remove decide API, update review API for sedimentation pool"
```

---

### Task 5: Update Demo + Seed

**Files:** `peerpedia/cli/main.py` (seed command), `demo_review.py`

- [ ] **Step 1: Update seed command to use submitted status**

In `seed`, change auto-publish to keep one article as "submitted":

```python
# Keep the first article in submitted state for pool demo
if i == 0:
    update_article_status(session, result.article_id, "submitted")
    session.commit()
else:
    # auto-publish the rest as before
```

- [ ] **Step 2: Run seed and verify**

```bash
peerpedia seed --force
curl -s http://localhost:8080/review | grep -c "article-card"
```
Expected: at least 1 article in the pool.

- [ ] **Step 3: Commit**

```bash
git add peerpedia/cli/main.py
git commit -m "demo: keep one article in sediment pool for testing"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Fix tests | `test_web_pages.py` |
| 2 | Rename UI | `*.html` templates |
| 3 | Sink calculation | `pages.py` |
| 4 | Remove decide, update review | `api_articles.py`, `pages.py` |
| 5 | Update seed | `main.py` |
