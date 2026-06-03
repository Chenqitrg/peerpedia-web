# Self-Review Five-Dimension Self-Assessment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five-dimension self-assessment to article submission, replacing categorical `note_type` with a vector-based content description.

**Architecture:** Five new int columns (0-5) on the Article model, passed through `create_article()` → `submit_article()` → `POST /api/v1/articles`. Submit page gets star-rating UI. Article page shows self-ratings. `forked_from` column added for future use. No backend logic changes beyond data passthrough.

**Tech Stack:** Python 3.14, SQLAlchemy, FastAPI, Jinja2, HTMX

---

## File Map

```
MODIFY:
  peerpedia_core/storage/db/models.py          — 6 new columns + to_dict()
  peerpedia_core/storage/db/crud_article.py     — create_article() new params
  peerpedia/submit.py                           — submit_article() passthrough + SubmissionResult
  peerpedia/web/routes/api_articles.py           — POST /articles new form fields
  peerpedia/web/templates/submit.html            — star rating UI
  peerpedia/web/templates/article.html           — self-rating display
  demo_review.py                                 — set self-ratings on demo articles

NEW:
  tests/test_self_review.py                      — 5 tests
```

---

### Task 1: Data Model — 6 New Columns

**Files:**
- Modify: `peerpedia_core/storage/db/models.py`

- [ ] **Step 1: Add columns to Article ORM model**

In `peerpedia_core/storage/db/models.py`, after line 51 (`mirror_by`), add:

```python
    # Self-review dimensions (0-5, 0 = not self-rated)
    self_originality = Column(Integer, nullable=False, default=0)
    self_rigor = Column(Integer, nullable=False, default=0)
    self_completeness = Column(Integer, nullable=False, default=0)
    self_pedagogy = Column(Integer, nullable=False, default=0)
    self_impact = Column(Integer, nullable=False, default=0)
    forked_from = Column(String(36), nullable=True)
```

- [ ] **Step 2: Update to_dict()**

In `Article.to_dict()`, after `"mirror_by":` line, add:

```python
            "self_originality": self.self_originality,
            "self_rigor": self.self_rigor,
            "self_completeness": self.self_completeness,
            "self_pedagogy": self.self_pedagogy,
            "self_impact": self.self_impact,
            "forked_from": self.forked_from,
```

- [ ] **Step 3: Run existing tests to verify no regression**

```bash
cd /Users/chenqimeng/Projects/peerpedia && source .venv/bin/activate
python -m pytest tests/test_db.py -v
```

Expected: all existing tests pass (new columns have defaults, don't break old code).

- [ ] **Step 4: Commit**

```bash
git add peerpedia_core/storage/db/models.py
git commit -m "feat(db): add self-review dimensions + forked_from to Article

- 5 self-rating columns (originality, rigor, completeness, pedagogy, impact)
- All default to 0 (not self-rated), range 1-5
- forked_from column for future fork feature

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: CRUD — Pass Self-Ratings Through create_article()

**Files:**
- Modify: `peerpedia_core/storage/db/crud_article.py`

- [ ] **Step 1: Add self-rating params to create_article()**

In `peerpedia_core/storage/db/crud_article.py`, update `create_article()`:

Add params after `format: str = "typst"`:

```python
    self_originality: int = 0,
    self_rigor: int = 0,
    self_completeness: int = 0,
    self_pedagogy: int = 0,
    self_impact: int = 0,
```

Add to `Article()` constructor call:

```python
        self_originality=self_originality,
        self_rigor=self_rigor,
        self_completeness=self_completeness,
        self_pedagogy=self_pedagogy,
        self_impact=self_impact,
```

- [ ] **Step 2: Run existing tests**

```bash
python -m pytest tests/test_db.py tests/test_submit.py -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add peerpedia_core/storage/db/crud_article.py
git commit -m "feat(crud): add self-rating params to create_article()

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: submit_article() — Pass Through Self-Ratings

**Files:**
- Modify: `peerpedia/submit.py`

- [ ] **Step 1: Update submit_article() signature and pass-through**

Add params to `submit_article()` after `author_email`:

```python
    self_originality: int = 0,
    self_rigor: int = 0,
    self_completeness: int = 0,
    self_pedagogy: int = 0,
    self_impact: int = 0,
```

Update `create_article()` call to include self-ratings:

```python
        article = create_article(
            session, id=article_id, title=title,
            founding_authors=[author_name], abstract=abstract,
            abstract_zh=abstract_zh, categories=categories,
            keywords=keywords, language=language, format=fmt,
            about_person=about_person, git_repo_path=str(repo_path),
            self_originality=self_originality,
            self_rigor=self_rigor,
            self_completeness=self_completeness,
            self_pedagogy=self_pedagogy,
            self_impact=self_impact,
        )
```

Add to `SubmissionResult` return dataclass fields:

```python
    self_originality: int = 0
    self_rigor: int = 0
    self_completeness: int = 0
    self_pedagogy: int = 0
    self_impact: int = 0
```

Update the return statement:

```python
    return SubmissionResult(
        success=True, article_id=article_id, title=title,
        abstract=abstract, categories=categories, format=fmt,
        git_repo_path=str(repo_path), git_commit_hash=commit_hash,
        cid=cid,
        self_originality=self_originality,
        self_rigor=self_rigor,
        self_completeness=self_completeness,
        self_pedagogy=self_pedagogy,
        self_impact=self_impact,
    )
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_submit.py -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add peerpedia/submit.py
git commit -m "feat(submit): pass self-rating dimensions through submit_article()

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: API — Accept Self-Rating Form Fields

**Files:**
- Modify: `peerpedia/web/routes/api_articles.py`

- [ ] **Step 1: Add form params to POST /articles**

In `api_create_article()`, add 5 optional form params after `article_file`:

```python
    self_originality: int = Form(0),
    self_rigor: int = Form(0),
    self_completeness: int = Form(0),
    self_pedagogy: int = Form(0),
    self_impact: int = Form(0),
```

Update `submit_article()` call:

```python
        result = submit_article(
            source_path=tmp_path,
            database_url=settings.database_url,
            articles_dir=settings.articles_dir,
            self_originality=self_originality,
            self_rigor=self_rigor,
            self_completeness=self_completeness,
            self_pedagogy=self_pedagogy,
            self_impact=self_impact,
        )
```

- [ ] **Step 2: Run API tests**

```bash
python -m pytest tests/test_api_routes.py -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/routes/api_articles.py
git commit -m "feat(api): accept self-rating fields in POST /articles

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Submit Page — Star Rating UI

**Files:**
- Modify: `peerpedia/web/templates/submit.html`

- [ ] **Step 1: Add self-review section to submit form**

In `submit.html`, after the format selector and before the abstract textarea, add:

```html
            <fieldset class="self-review" style="border:1px solid #e5e5e5;border-radius:8px;padding:16px;margin-bottom:12px;">
                <legend style="font-weight:600;">📊 自评 <span style="font-weight:400;color:#888;font-size:0.9em;">— 帮助读者了解内容定位（可选）</span></legend>

                <div class="star-rating" data-dimension="self_originality" style="margin-bottom:10px;">
                    <span style="display:inline-block;width:100px;font-size:0.85em;">🧠 原创性</span>
                    <span class="stars" style="cursor:pointer;">
                        <span data-value="1" title="搬运/翻译">☆</span>
                        <span data-value="2" title="学习笔记">☆</span>
                        <span data-value="3" title="随笔习作">☆</span>
                        <span data-value="4" title="综述评论">☆</span>
                        <span data-value="5" title="原创研究">☆</span>
                    </span>
                    <span class="star-label" style="font-size:0.75em;color:#888;margin-left:8px;"></span>
                    <input type="hidden" name="self_originality" value="0">
                </div>

                <div class="star-rating" data-dimension="self_rigor" style="margin-bottom:10px;">
                    <span style="display:inline-block;width:100px;font-size:0.85em;">📐 严格性</span>
                    <span class="stars" style="cursor:pointer;">
                        <span data-value="1" title="非正式讨论">☆</span>
                        <span data-value="2" title="直觉科普">☆</span>
                        <span data-value="3" title="标准推导">☆</span>
                        <span data-value="4" title="严格证明">☆</span>
                        <span data-value="5" title="公理形式">☆</span>
                    </span>
                    <span class="star-label" style="font-size:0.75em;color:#888;margin-left:8px;"></span>
                    <input type="hidden" name="self_rigor" value="0">
                </div>

                <div class="star-rating" data-dimension="self_completeness" style="margin-bottom:10px;">
                    <span style="display:inline-block;width:100px;font-size:0.85em;">🧩 完整性</span>
                    <span class="stars" style="cursor:pointer;">
                        <span data-value="1" title="草稿片段">☆</span>
                        <span data-value="2" title="部分覆盖">☆</span>
                        <span data-value="3" title="核心完整">☆</span>
                        <span data-value="4" title="全面覆盖">☆</span>
                        <span data-value="5" title="详尽完备">☆</span>
                    </span>
                    <span class="star-label" style="font-size:0.75em;color:#888;margin-left:8px;"></span>
                    <input type="hidden" name="self_completeness" value="0">
                </div>

                <div class="star-rating" data-dimension="self_pedagogy" style="margin-bottom:10px;">
                    <span style="display:inline-block;width:100px;font-size:0.85em;">📖 教学性</span>
                    <span class="stars" style="cursor:pointer;">
                        <span data-value="1" title="个人备忘">☆</span>
                        <span data-value="2" title="需领域基础">☆</span>
                        <span data-value="3" title="有基础可读">☆</span>
                        <span data-value="4" title="教学导向">☆</span>
                        <span data-value="5" title="零基础入门">☆</span>
                    </span>
                    <span class="star-label" style="font-size:0.75em;color:#888;margin-left:8px;"></span>
                    <input type="hidden" name="self_pedagogy" value="0">
                </div>

                <div class="star-rating" data-dimension="self_impact" style="margin-bottom:0;">
                    <span style="display:inline-block;width:100px;font-size:0.85em;">💡 影响力</span>
                    <span class="stars" style="cursor:pointer;">
                        <span data-value="1" title="个人参考">☆</span>
                        <span data-value="2" title="小众专题">☆</span>
                        <span data-value="3" title="领域相关">☆</span>
                        <span data-value="4" title="领域核心">☆</span>
                        <span data-value="5" title="奠基/开创">☆</span>
                    </span>
                    <span class="star-label" style="font-size:0.75em;color:#888;margin-left:8px;"></span>
                    <input type="hidden" name="self_impact" value="0">
                </div>
            </fieldset>
```

- [ ] **Step 2: Add star-rating JavaScript**

Add after the `setViewer` script block in `submit.html`:

```html
<script>
// Star rating interaction
document.querySelectorAll('.star-rating').forEach(function(rating) {
    var stars = rating.querySelectorAll('.stars span');
    var label = rating.querySelector('.star-label');
    var input = rating.querySelector('input[type=hidden]');

    stars.forEach(function(star, index) {
        star.addEventListener('mouseenter', function() {
            // Highlight stars up to hovered one
            stars.forEach(function(s, i) {
                s.textContent = i <= index ? '★' : '☆';
                s.style.color = i <= index ? '#f59e0b' : '#ccc';
            });
            label.textContent = star.title;
        });
        star.addEventListener('click', function() {
            var val = parseInt(star.dataset.value);
            input.value = val;
            label.textContent = star.title;
        });
    });

    rating.addEventListener('mouseleave', function() {
        var val = parseInt(input.value);
        stars.forEach(function(s, i) {
            s.textContent = i < val ? '★' : '☆';
            s.style.color = i < val ? '#f59e0b' : '#ccc';
        });
        label.textContent = val > 0 ? stars[val - 1].title : '';
    });
});
</script>
```

- [ ] **Step 3: Clear caches and verify page renders**

```bash
lsof -ti:8080 | xargs kill -9 2>/dev/null
find ~/Projects/peerpedia -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
source .venv/bin/activate && peerpedia serve --port 8080 &
sleep 2
curl -s http://localhost:8080/submit | grep -c "star-rating"
```

Expected: output is `5` (five star-rating blocks).

- [ ] **Step 4: Commit**

```bash
git add peerpedia/web/templates/submit.html
git commit -m "feat(ui): add 5-dimension star-rating self-review to submit form

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Article Page — Display Self-Ratings

**Files:**
- Modify: `peerpedia/web/templates/article.html`

- [ ] **Step 1: Add self-rating display below article meta**

In `article.html`, after the `</div>` closing `article-meta` and before the tab buttons, add:

```html
            {% set has_self_review = article.self_originality or article.self_rigor or article.self_completeness or article.self_pedagogy or article.self_impact %}
            {% if has_self_review %}
            <div class="self-review-display" style="display:flex;gap:16px;padding:10px 14px;background:#f8f9fa;border-radius:6px;margin-bottom:16px;flex-wrap:wrap;font-size:0.85em;">
                <span title="原创性">🧠 {{ article.self_originality }}/5</span>
                <span title="严格性">📐 {{ article.self_rigor }}/5</span>
                <span title="完整性">🧩 {{ article.self_completeness }}/5</span>
                <span title="教学性">📖 {{ article.self_pedagogy }}/5</span>
                <span title="影响力">💡 {{ article.self_impact }}/5</span>
                <span style="color:#888;">(作者自评)</span>
            </div>
            {% else %}
            <p style="color:#aaa;font-size:0.85em;margin-bottom:12px;">作者未自评 · 社区审稿后此处显示评分对比</p>
            {% endif %}
```

- [ ] **Step 2: Verify article page renders self-ratings**

```bash
# Create test article with self-ratings
source .venv/bin/activate && python -c "
import tempfile, uuid
from pathlib import Path
from peerpedia.config.settings import settings
from peerpedia.submit import submit_article

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / 'test.md'
    src.write_text('---\ntitle: Self Review Test\nabstract: Testing.\n---\n\n# Test\n')
    result = submit_article(
        source_path=src,
        database_url=settings.database_url,
        articles_dir=settings.articles_dir,
        self_originality=4, self_rigor=3, self_completeness=2,
        self_pedagogy=5, self_impact=1,
    )
    aid = result.article_id
    print(f'Article: {aid}')

# Check article page
curl -s http://localhost:8080/article/$aid | grep -o 'self-review-display'
curl -s http://localhost:8080/article/$aid | grep -c '作者自评'
"
```

Expected: finds `self-review-display` and `作者自评`.

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/templates/article.html
git commit -m "feat(ui): display self-ratings on article page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Tests

**Files:**
- Create: `tests/test_self_review.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for five-dimension self-review feature."""
import pytest
import tempfile
from pathlib import Path

from peerpedia.submit import submit_article
from peerpedia_core.storage.db import get_engine, get_session, init_db, get_article


class TestSelfReviewSubmit:
    """Self-rating dimensions are stored correctly on submit."""

    def test_submit_with_all_self_ratings(self):
        """Submit article with all 5 self-ratings set, verify stored."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Rated Article\nabstract: Test.\n---\n\n# Test\n")

            result = submit_article(
                source_path=source,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
                self_originality=4,
                self_rigor=3,
                self_completeness=2,
                self_pedagogy=5,
                self_impact=1,
            )

            assert result.success is True
            assert result.self_originality == 4
            assert result.self_rigor == 3
            assert result.self_completeness == 2
            assert result.self_pedagogy == 5
            assert result.self_impact == 1

            # Verify in DB
            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)
            article = get_article(session, result.article_id)
            assert article.self_originality == 4
            assert article.self_rigor == 3
            assert article.self_completeness == 2
            assert article.self_pedagogy == 5
            assert article.self_impact == 1
            session.close()

    def test_submit_without_self_ratings_defaults_to_zero(self):
        """Submit article without self-ratings - all should be 0."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Unrated Article\n---\n\n# Test\n")

            result = submit_article(
                source_path=source,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            assert result.success is True
            assert result.self_originality == 0
            assert result.self_rigor == 0
            assert result.self_completeness == 0
            assert result.self_pedagogy == 0
            assert result.self_impact == 0

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)
            article = get_article(session, result.article_id)
            assert article.self_originality == 0
            session.close()

    def test_to_dict_includes_self_ratings(self):
        """Article.to_dict() includes all self-rating fields."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Dict Test\n---\n\n# Test\n")

            result = submit_article(
                source_path=source,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
                self_originality=5, self_rigor=5,
                self_completeness=5, self_pedagogy=5, self_impact=5,
            )

            engine = get_engine(f"sqlite:///{db_path}")
            init_db(engine)
            session = get_session(engine)
            article = get_article(session, result.article_id)
            d = article.to_dict()
            assert d["self_originality"] == 5
            assert d["self_rigor"] == 5
            assert d["self_completeness"] == 5
            assert d["self_pedagogy"] == 5
            assert d["self_impact"] == 5
            assert d["forked_from"] is None
            session.close()


class TestSelfReviewAPI:
    """API accepts and returns self-rating fields."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from peerpedia.web.app import app
        return TestClient(app)

    def test_api_submit_with_self_ratings(self, client):
        """POST /api/v1/articles with self-rating fields stores them."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            original_url = settings.database_url
            settings.database_url = f"sqlite:///{db_path}"

            try:
                md = "---\ntitle: API Self Review\nabstract: Testing API.\n---\n\n# Test\n"
                response = client.post(
                    "/api/v1/articles",
                    data={
                        "title": "API Self Review",
                        "abstract": "Testing API.",
                        "format": "markdown",
                        "self_originality": "3",
                        "self_rigor": "4",
                        "self_completeness": "2",
                        "self_pedagogy": "5",
                        "self_impact": "1",
                    },
                    files={"article_file": ("test.md", md.encode(), "text/markdown")},
                )
                assert response.status_code == 200
                data = response.json()
                aid = data["article_id"]

                from peerpedia_core.storage.db import get_engine, init_db, get_session, get_article
                engine = get_engine(f"sqlite:///{db_path}")
                init_db(engine)
                session = get_session(engine)
                article = get_article(session, aid)
                assert article.self_originality == 3
                assert article.self_rigor == 4
                assert article.self_completeness == 2
                assert article.self_pedagogy == 5
                assert article.self_impact == 1
                session.close()
            finally:
                settings.database_url = original_url


class TestSelfReviewWebPages:
    """Article page renders self-ratings."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from peerpedia.web.app import app
        return TestClient(app)

    def test_article_page_shows_self_ratings(self, client):
        """Article page renders self-rating display."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Rated Page Test\n---\n\n# Test\n")

            result = submit_article(
                source_path=source,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
                self_originality=4, self_rigor=3,
                self_completeness=2, self_pedagogy=5, self_impact=1,
            )

            original_url = settings.database_url
            settings.database_url = f"sqlite:///{db_path}"

            try:
                response = client.get(f"/article/{result.article_id}")
                assert response.status_code == 200
                assert "作者自评" in response.text
                assert "self-review-display" in response.text
            finally:
                settings.database_url = original_url

    def test_article_page_shows_not_rated_when_all_zero(self, client):
        """Article page shows 'not rated' when all self-ratings are 0."""
        with tempfile.TemporaryDirectory() as tmp:
            from peerpedia.config.settings import settings

            base = Path(tmp)
            db_path = base / "test.db"
            articles_dir = base / "articles"
            articles_dir.mkdir()

            source = base / "test.md"
            source.write_text("---\ntitle: Unrated Page Test\n---\n\n# Test\n")

            result = submit_article(
                source_path=source,
                database_url=f"sqlite:///{db_path}",
                articles_dir=articles_dir,
            )

            original_url = settings.database_url
            settings.database_url = f"sqlite:///{db_path}"

            try:
                response = client.get(f"/article/{result.article_id}")
                assert response.status_code == 200
                assert "作者未自评" in response.text
            finally:
                settings.database_url = original_url
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && source .venv/bin/activate
python -m pytest tests/test_self_review.py -v
```

Expected: 5 passed.

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -q
```

Expected: 346 passed (341 existing + 5 new).

- [ ] **Step 4: Commit**

```bash
git add tests/test_self_review.py
git commit -m "test: add 5 tests for self-review feature

- submit with all self-ratings → stored in DB
- submit without self-ratings → defaults to 0
- to_dict() includes self-rating fields
- API POST accepts self-rating form fields
- Article page renders self-ratings / not-rated state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Update demo_review.py

**Files:**
- Modify: `demo_review.py`

- [ ] **Step 1: Add self-ratings to demo articles**

In each `submit_article()` call, add realistic self-ratings. For example, in Scene 1 (Gauge Theory):

```python
    result = submit_article(
        source_path=src,
        database_url=DB_URL,
        articles_dir=ARTICLES_DIR,
        author_name="zhangliang",
        author_email="zhang@peerpedia.local",
        self_originality=4,  # 综述评论 — it's a pedagogical survey
        self_rigor=4,        # 严格证明
        self_completeness=3,  # 核心完整
        self_pedagogy=4,     # 教学导向
        self_impact=3,       # 领域相关
    )
```

Do the same for all 3 `submit_article()` calls in the demo script, with different self-ratings for each article type.

- [ ] **Step 2: Commit**

```bash
git add demo_review.py
git commit -m "demo: add realistic self-ratings to demo articles

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Summary

| Task | What | Files | Tests |
|------|------|-------|-------|
| 1 | Data model | `models.py` | — |
| 2 | CRUD | `crud_article.py` | — |
| 3 | Orchestrator | `submit.py` | — |
| 4 | API | `api_articles.py` | — |
| 5 | Submit UI | `submit.html` | — |
| 6 | Article page UI | `article.html` | — |
| 7 | Tests | `test_self_review.py` (new) | 5 |
| 8 | Demo data | `demo_review.py` | — |
