# Monaco Online Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let mathematicians write and preview Markdown/Typst articles in the browser with instant live preview, then submit directly to the sedimentation pool.

**Architecture:** Single page (`/edit`) with Monaco Editor (left) + live preview (right) + metadata panel (below). Both formats are 100% client-side preview — Markdown via KaTeX, Typst via `@myriaddreamin/typst.ts` WASM SVG. Submission reuses the existing `POST /api/v1/articles` multipart endpoint.

**Tech Stack:** Monaco Editor (CDN), `@myriaddreamin/typst.ts` (CDN), KaTeX (existing), FastAPI, Jinja2

---

### Task 1: Add /edit routes in pages.py

**Files:**
- Modify: `peerpedia/web/routes/pages.py`

- [ ] **Step 1: Read the current pages.py to find the right insertion point**

Open `peerpedia/web/routes/pages.py` and find the existing route functions (e.g., `submit_page`). We'll add two new routes near `submit_page`.

- [ ] **Step 2: Add GET /edit route (new article)**

Add this function after the existing `submit_page` route:

```python
@router.get("/edit", response_class=HTMLResponse)
async def edit_page(request: Request):
    """Online editor — new article."""
    viewer = get_viewer(request)
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "request": request,
            "title": "编辑文章",
            "viewer": viewer,
            "all_users": get_all_users(),
            "article": None,  # new article — no existing data
        },
    )
```

- [ ] **Step 3: Add GET /edit/{article_id} route (edit existing article)**

Add after the route above:

```python
@router.get("/edit/{article_id}", response_class=HTMLResponse)
async def edit_article_page(request: Request, article_id: str):
    """Online editor — edit existing article, loading its source."""
    session = get_db_session()
    viewer = get_viewer(request)
    try:
        article = get_article(session, article_id)
        if article is None:
            return templates.TemplateResponse(
                request=request,
                name="edit.html",
                context={
                    "request": request,
                    "title": "文章未找到",
                    "viewer": viewer,
                    "all_users": get_all_users(),
                    "article": None,
                    "error": "文章未找到。",
                },
                status_code=404,
            )

        article_dict = article.to_dict()

        # Read source file content for the editor
        source_content = ""
        from pathlib import Path
        repo = Path(article.git_repo_path) if article.git_repo_path else None
        if repo and repo.exists():
            ext = "*.typ" if article.format == "typst" else "*.md"
            source_files = list(repo.glob(ext))
            if source_files:
                source_content = source_files[0].read_text()

        article_dict["source_content"] = source_content
        return templates.TemplateResponse(
            request=request,
            name="edit.html",
            context={
                "request": request,
                "title": f"编辑: {article.title}",
                "viewer": viewer,
                "all_users": get_all_users(),
                "article": article_dict,
            },
        )
    finally:
        session.close()
```

The existing imports (`get_article`, `get_viewer`, `get_all_users`, `templates`, `HTMLResponse`, `Request`) are already present at the top of `pages.py`.

- [ ] **Step 4: Run existing tests to verify no regressions**

```bash
cd /Users/chenqimeng/Projects/peerpedia && .venv/bin/python -m pytest tests/test_web_pages.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add peerpedia/web/routes/pages.py
git commit -m "feat: add /edit and /edit/{id} routes for Monaco online editor"
```

---

### Task 2: Create edit.html template — layout + Monaco editor

**Files:**
- Create: `peerpedia/web/templates/edit.html`

- [ ] **Step 1: Create the template file**

```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — 知诸网</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/katex/katex.min.css">
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script defer src="/static/katex/katex.min.js"></script>
    <script defer src="/static/katex/auto-render.min.js"></script>
    <!-- Monaco Editor -->
    <link rel="stylesheet" data-name="vs/editor/editor.main"
          href="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/editor/editor.main.min.css">
</head>
<body>
    <header>
        <h1>📚 知诸网</h1>
        <nav>
            <a href="/">首页</a>
            <a href="/submit">提交</a>
            <a href="/review">🌊 沉淀池</a>
            {% if viewer %}
            <a href="/user/{{ viewer }}">👤 我的主页</a>
            {% endif %}
            <span style="margin-left: auto; font-size: 0.85em;">
                <select id="viewer-picker" onchange="setViewer(this.value)"
                        style="padding: 2px 4px; border: 1px solid var(--border); border-radius: 4px;">
                    <option value="">👽 游客</option>
                    {% for u in all_users %}
                    <option value="{{ u[0] }}" {% if viewer == u[0] %}selected{% endif %}>{{ u[1] }}</option>
                    {% endfor %}
                </select>
            </span>
        </nav>
    </header>
    <script>
    function setViewer(uid) {
        if (uid) {
            document.cookie = "viewer=" + encodeURIComponent(uid) + ";path=/;max-age=86400;SameSite=Lax";
        } else {
            document.cookie = "viewer=;path=/;max-age=0;SameSite=Lax";
        }
        location.reload();
    }
    </script>

    <main>
    {% if error %}
    <p class="empty-state" style="padding:24px;">{{ error }}</p>
    {% else %}
    <div style="display:flex;gap:4px;margin-bottom:8px;align-items:center;">
        <label style="font-size:0.9em;">格式:
            <select id="format-select" onchange="switchFormat(this.value)"
                    style="padding:3px 8px;border:1px solid var(--border);border-radius:4px;">
                <option value="markdown" {% if not article or article.format == 'markdown' %}selected{% endif %}>Markdown + KaTeX</option>
                <option value="typst" {% if article and article.format == 'typst' %}selected{% endif %}>Typst (WASM)</option>
            </select>
        </label>
        <span id="preview-status" style="font-size:0.8em;color:#888;margin-left:8px;"></span>
    </div>

    <div id="editor-container" style="display:flex;gap:12px;height:60vh;min-height:400px;">
        <!-- Monaco editor -->
        <div id="monaco-editor" style="flex:1;min-width:0;border:1px solid var(--border);"></div>
        <!-- Preview -->
        <div id="preview-pane" style="flex:1;min-width:0;border:1px solid var(--border);padding:16px;overflow-y:auto;background:#fff;">
            <p style="color:#888;">预览区域。开始输入...</p>
        </div>
    </div>

    <!-- Metadata panel -->
    <details open style="margin-top:16px;">
        <summary style="cursor:pointer;font-weight:600;font-size:0.95em;">📋 文章信息</summary>
        <form id="metadata-form" style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:0.9em;">
            <div style="grid-column:1/-1;">
                <label>标题<input type="text" name="title" required
                    value="{{ article.title if article else '' }}"
                    style="width:100%;padding:6px;font-size:1em;"></label>
            </div>
            <div style="grid-column:1/-1;">
                <label>摘要<textarea name="abstract" rows="2"
                    style="width:100%;padding:6px;">{{ article.abstract if article else '' }}</textarea></label>
            </div>
            <div>
                <label>分类（逗号分隔）<input type="text" name="categories"
                    value="{{ ', '.join(article.categories) if article else '' }}"
                    style="width:100%;padding:4px;"></label>
            </div>
            <div>
                <label>关键词（逗号分隔）<input type="text" name="keywords"
                    value="{{ ', '.join(article.keywords) if article else '' }}"
                    style="width:100%;padding:4px;"></label>
            </div>
            <div>
                <label>语言
                    <select name="language" style="width:100%;padding:4px;">
                        <option value="en" {% if not article or article.language == 'en' %}selected{% endif %}>English</option>
                        <option value="zh" {% if article and article.language == 'zh' %}selected{% endif %}>中文</option>
                    </select>
                </label>
            </div>
            <div>
                <label>中文摘要（可选）<input type="text" name="abstract_zh"
                    value="{{ article.abstract_zh if article else '' }}"
                    style="width:100%;padding:4px;"></label>
            </div>
            <!-- 5D self-assessment -->
            <fieldset style="grid-column:1/-1;border:1px solid #e5e5e5;border-radius:6px;padding:10px 14px;">
                <legend style="font-weight:600;font-size:0.85em;">五维自评（可选）</legend>
                <div style="display:flex;gap:12px;flex-wrap:wrap;">
                    {% set dims = [
                        ('self_originality', '🧠', '原创性'),
                        ('self_rigor', '📐', '严格性'),
                        ('self_completeness', '🧩', '完整性'),
                        ('self_pedagogy', '📖', '教学性'),
                        ('self_impact', '💡', '影响力')
                    ] %}
                    {% for name, icon, label in dims %}
                    <label style="font-size:0.85em;display:flex;align-items:center;gap:4px;">
                        {{ icon }} {{ label }}
                        <select name="{{ name }}" style="padding:2px 4px;">
                            {% set val = article[name]|default(0) if article else 0 %}
                            <option value="0" {% if val == 0 %}selected{% endif %}>-</option>
                            <option value="1" {% if val == 1 %}selected{% endif %}>1</option>
                            <option value="2" {% if val == 2 %}selected{% endif %}>2</option>
                            <option value="3" {% if val == 3 %}selected{% endif %}>3</option>
                            <option value="4" {% if val == 4 %}selected{% endif %}>4</option>
                            <option value="5" {% if val == 5 %}selected{% endif %}>5</option>
                        </select>
                    </label>
                    {% endfor %}
                </div>
            </fieldset>
        </form>
    </details>

    <!-- Submit -->
    <div style="margin-top:16px;display:flex;gap:8px;">
        <button id="submit-btn" onclick="submitArticle()"
                style="padding:10px 28px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:1em;font-weight:600;">
            🚀 提交沉淀池
        </button>
        <span id="submit-status" style="font-size:0.9em;color:#888;align-self:center;"></span>
    </div>
    {% endif %}
    </main>

    <!-- Monaco Editor loader -->
    <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.min.js"></script>
    <script>
    require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
    require(['vs/editor/editor.main'], function() {
        var format = document.getElementById('format-select').value;
        var language = format === 'typst' ? 'plaintext' : 'markdown';
        var initialContent = {{ article.source_content|tojson if article and article.source_content else '""' }};
        if (!initialContent) {
            initialContent = language === 'markdown'
                ? '---\ntitle: \nabstract: \ncategories:\n  - \nkeywords:\n  - \nlanguage: en\n---\n\n'
                : '// Typst article\n#let title = ""\n#let abstract = ""\n\n';
        }

        window.editor = monaco.editor.create(document.getElementById('monaco-editor'), {
            value: initialContent,
            language: language,
            theme: 'vs',
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            wordWrap: 'on',
            scrollBeyondLastLine: false,
        });

        // Trigger first preview
        updatePreview();
        window.editor.onDidChangeModelContent(function() {
            updatePreview();
        });
    });

    function switchFormat(fmt) {
        var lang = fmt === 'typst' ? 'plaintext' : 'markdown';
        var model = window.editor.getModel();
        monaco.editor.setModelLanguage(model, lang);
        updatePreview();
    }

    function updatePreview() {
        var content = window.editor.getValue();
        var format = document.getElementById('format-select').value;
        var preview = document.getElementById('preview-pane');
        var status = document.getElementById('preview-status');

        if (format === 'markdown') {
            previewMarkdown(content, preview, status);
        } else {
            previewTypst(content, preview, status);
        }
    }

    // ── Markdown preview (KaTeX, instant) ────────────────────────────────
    function previewMarkdown(content, preview, status) {
        status.textContent = '';
        // Strip frontmatter
        var body = content;
        if (body.startsWith('---')) {
            var parts = body.split('---', 3);
            if (parts.length >= 3) body = parts.slice(2).join('---');
        }
        // Protect math before Markdown parsing
        var mathBlocks = [];
        var protected_ = body
            .replace(/\$\$(.+?)\$\$/gs, function(m, g) {
                mathBlocks.push({display: true, math: g});
                return 'MATHPLACEHOLDER' + (mathBlocks.length - 1);
            })
            .replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, function(m, g) {
                mathBlocks.push({display: false, math: g});
                return 'MATHPLACEHOLDER' + (mathBlocks.length - 1);
            });
        // Simple Markdown → HTML
        var html = protected_
            .replace(/^### (.+)$/gm, '<h4>$1</h4>')
            .replace(/^## (.+)$/gm, '<h3>$1</h3>')
            .replace(/^# (.+)$/gm, '<h2>$1</h2>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        html = '<p>' + html + '</p>';
        // Restore math
        mathBlocks.forEach(function(b, i) {
            var cls = b.display ? 'katex-display' : 'katex-inline';
            var delim = b.display ? '$$' : '$';
            html = html.replace('MATHPLACEHOLDER' + i,
                '<span class="' + cls + '">' + delim + b.math + delim + '</span>');
        });
        preview.innerHTML = html;
        // Render KaTeX
        if (window.renderMathInElement) {
            renderMathInElement(preview, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                ]
            });
        }
    }

    // ── Submit ───────────────────────────────────────────────────────────
    function submitArticle() {
        var status = document.getElementById('submit-status');
        var btn = document.getElementById('submit-btn');
        status.textContent = '提交中...';
        btn.disabled = true;

        var form = document.getElementById('metadata-form');
        var formData = new FormData(form);
        var content = window.editor.getValue();
        var format = document.getElementById('format-select').value;
        var ext = format === 'typst' ? '.typ' : '.md';
        var blob = new Blob([content], {type: 'text/plain'});
        formData.append('article_file', blob, 'article' + ext);
        formData.append('format', format);

        fetch('/api/v1/articles', { method: 'POST', body: formData })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                status.innerHTML = '✅ 提交成功！<a href=\"/article/' + data.article_id + '\">查看文章</a>';
                btn.disabled = false;
            })
            .catch(function(err) {
                status.textContent = '✗ 提交失败';
                btn.disabled = false;
            });
    }
    </script>

    <!-- Typst WASM preview loader (lazy, only when Typst selected) -->
    <script>
    var typstLoaded = false;
    function loadTypstWasm(callback) {
        if (typstLoaded) { callback(); return; }
        var script = document.createElement('script');
        script.type = 'module';
        script.textContent = `
            import * as typst from 'https://cdn.jsdelivr.net/npm/@myriaddreamin/typst.ts@0.5.5/dist/esm/contrib/all-in-one.bundle.js';
            window.$typst = typst;
            typstLoaded = true;
            document.getElementById('preview-status').textContent = '';
            if (callback) callback();
        `;
        document.body.appendChild(script);
        typstLoaded = true;
        setTimeout(function() { if (callback) callback(); }, 500);
    }

    function previewTypst(content, preview, status) {
        status.textContent = '编译中...';
        loadTypstWasm(function() {
            try {
                window.$typst.svg({ mainContent: content }).then(function(svg) {
                    preview.innerHTML = svg;
                    status.textContent = '';
                }).catch(function(err) {
                    preview.innerHTML = '<p style="color:#c00;">编译错误: ' + err.message + '</p>';
                    status.textContent = '✗';
                });
            } catch(e) {
                preview.innerHTML = '<p style="color:#c00;">Typst WASM 加载中，请稍候重试...</p>';
                status.textContent = '⏳';
            }
        });
    }
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify the template renders**

```bash
cd /Users/chenqimeng/Projects/peerpedia
lsof -ti:8080 | xargs kill -9 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
.venv/bin/peerpedia seed --force 2>&1 | tail -1
.venv/bin/peerpedia serve &
sleep 3
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/edit
```
Expected: `200`

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/templates/edit.html
git commit -m "feat: create edit.html with Monaco editor + Markdown/Typst preview"
```

---

### Task 3: Fix Typst WASM CDN URL + handle edge cases

**Files:**
- Modify: `peerpedia/web/templates/edit.html`

- [ ] **Step 1: Verify typst.ts CDN URL**

The typst.ts all-in-one bundle needs to be hosted somewhere accessible. Check if the npm CDN URL works:

```bash
curl -sI 'https://cdn.jsdelivr.net/npm/@myriaddreamin/typst.ts@0.5.5/dist/esm/contrib/all-in-one.bundle.js' | head -3
```

If 200, the CDN URL is valid. If not, we need to find the correct URL from the typst.ts docs or host the bundle locally.

- [ ] **Step 2: Add error boundary for Typst WASM failures**

In the `previewTypst` function, add a fallback for WASM load failures. Replace the catch block with:

```javascript
.catch(function(err) {
    preview.innerHTML = '<p style="color:#c00;">Typst 编译错误</p><pre style="font-size:0.85em;color:#888;">'
        + (err.message || String(err)).slice(0, 500) + '</pre>';
    status.textContent = '✗';
});
```

- [ ] **Step 3: Run existing tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && .venv/bin/python -m pytest tests/test_web_pages.py -v
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add peerpedia/web/templates/edit.html
git commit -m "fix: improve Typst WASM error handling and verify CDN URL"
```

---

### Task 4: Add edit link to nav bar across all templates

**Files:**
- Modify: `peerpedia/web/templates/index.html`
- Modify: `peerpedia/web/templates/article.html`
- Modify: `peerpedia/web/templates/review.html`
- Modify: `peerpedia/web/templates/user.html`
- Modify: `peerpedia/web/templates/lan_status.html`

- [ ] **Step 1: Add edit link in each template's nav**

Add `<a href="/edit">✏️ 写作</a>` right after the submit link in each template:

```html
<a href="/submit">提交</a>
<a href="/edit">✏️ 写作</a>
```

Run the sed command to add the link to all 5 templates:

```bash
cd /Users/chenqimeng/Projects/peerpedia
for f in peerpedia/web/templates/index.html peerpedia/web/templates/article.html peerpedia/web/templates/review.html peerpedia/web/templates/user.html peerpedia/web/templates/lan_status.html; do
    sed -i '' 's|<a href="/submit">提交</a>|<a href="/submit">提交</a>\n            <a href="/edit">✏️ 写作</a>|' "$f"
done
```

- [ ] **Step 2: Verify**

```bash
curl -s http://localhost:8080/ | grep "✏️ 写作"
```
Expected: match found

- [ ] **Step 3: Commit**

```bash
git add peerpedia/web/templates/index.html peerpedia/web/templates/article.html peerpedia/web/templates/review.html peerpedia/web/templates/user.html peerpedia/web/templates/lan_status.html
git commit -m "feat: add ✏️ 写作 link to nav bar on all pages"
```

---

### Task 5: End-to-end test — create and submit an article via editor

**Files:**
- Create: `tests/test_editor.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for the Monaco online editor."""

from fastapi.testclient import TestClient

from peerpedia.web.app import app

client = TestClient(app)


def test_edit_page_loads():
    """GET /edit returns the editor page."""
    response = client.get("/edit")
    assert response.status_code == 200
    assert "monaco-editor" in response.text
    assert "preview-pane" in response.text


def test_edit_page_has_metadata_form():
    """Editor page includes metadata form for submission."""
    response = client.get("/edit")
    assert response.status_code == 200
    assert 'name="title"' in response.text
    assert 'name="abstract"' in response.text


def test_edit_existing_article_loads(monkeypatch):
    """GET /edit/{id} loads existing article source into editor."""
    # Seed first, then grab an article ID
    from peerpedia.config.settings import settings
    from peerpedia_core.storage.db import get_engine, get_session, init_db, list_articles

    engine = get_engine(settings.database_url)
    init_db(engine)
    session = get_session(engine)
    try:
        articles = list_articles(session, limit=1)
        if articles:
            aid = articles[0].id
            response = client.get(f"/edit/{aid}")
            assert response.status_code == 200
            # Should have the editor with pre-filled content
            assert "monaco-editor" in response.text
    finally:
        session.close()


def test_edit_nonexistent_article():
    """GET /edit/{nonexistent} returns 404."""
    response = client.get("/edit/nonexistent-id-12345")
    assert response.status_code == 404
    assert "文章未找到" in response.text


def test_submit_via_editor():
    """Submit a new article via the editor API endpoint."""
    content = (
        "---\n"
        "title: Test Editor Article\n"
        "abstract: Testing the editor submission.\n"
        "categories:\n"
        "  - math\n"
        "keywords:\n"
        "  - test\n"
        "language: en\n"
        "---\n\n"
        "# Editor Test\n\n"
        "This was submitted from the online editor.\n\n"
        "$$E = mc^2$$\n"
    )
    response = client.post(
        "/api/v1/articles",
        data={
            "title": "Test Editor Article",
            "abstract": "Testing the editor submission.",
            "format": "markdown",
            "categories": "math",
            "keywords": "test",
            "language": "en",
        },
        files={"article_file": ("article.md", content.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "article_id" in data
    assert data["status"] == "submitted"


def test_submit_typst_via_editor():
    """Submit a Typst article via the editor API endpoint."""
    content = (
        "// Typst article\n"
        "#let title = \"Typst Test\"\n"
        "#let abstract = \"Testing typst submission.\"\n\n"
        "= Introduction\n\n"
        "This is a Typst article from the editor.\n"
    )
    response = client.post(
        "/api/v1/articles",
        data={
            "title": "Typst Test",
            "abstract": "Testing typst submission.",
            "format": "typst",
            "categories": "physics",
            "keywords": "typst,test",
            "language": "en",
        },
        files={"article_file": ("article.typ", content.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "article_id" in data
```

- [ ] **Step 2: Run the tests**

```bash
cd /Users/chenqimeng/Projects/peerpedia && .venv/bin/python -m pytest tests/test_editor.py -v
```
Expected: 6 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_editor.py
git commit -m "test: add editor page and submission tests"
```

---

### Task 6: Final verification — full test suite + manual smoke test

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/chenqimeng/Projects/peerpedia
.venv/bin/python -m pytest tests/ -q
```
Expected: all existing tests pass, 6 new editor tests pass

- [ ] **Step 2: Manual smoke test**

```bash
lsof -ti:8080 | xargs kill -9 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
rm -rf .pytest_cache
.venv/bin/peerpedia seed --force 2>&1 | tail -1
.venv/bin/peerpedia serve &
sleep 3

# Test editor page loads
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/edit
# Should print: 200

# Test editor page has Monaco
curl -s http://localhost:8080/edit | grep -c "monaco"
# Should print: > 0
```

- [ ] **Step 3: Commit any final fixes**

```bash
git add -A && git diff --cached --stat
```
If clean, done. If fixes needed, commit them.

---

## Self-Review

**1. Spec coverage:**
- ✅ Left-right split: Monaco + preview → Task 2 (edit.html layout)
- ✅ Markdown KaTeX preview → Task 2 (previewMarkdown function)
- ✅ Typst WASM → SVG preview → Task 2 (previewTypst + typst.ts CDN)
- ✅ Metadata panel → Task 2 (metadata form in edit.html)
- ✅ Submit to sedimentation pool → Task 2 (submitArticle function)
- ✅ GET /edit route → Task 1
- ✅ GET /edit/{id} route → Task 1
- ✅ No new API endpoints → confirmed, reuse POST /api/v1/articles
- ✅ Nav link to editor → Task 4

**2. Placeholder scan:** No TBD, TODO, or vague instructions. All code is shown.

**3. Type consistency:** All routes use the same viewer/get_all_users pattern as existing pages.py routes. Template uses standard Jinja2 variable names.
