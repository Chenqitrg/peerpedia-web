# Self-Review: Five-Dimension Self-Assessment for Article Submission

> 2026-06-03 | Status: DRAFT
> Replaces: `note_type` categorical field — dimensions capture both type and quality

## 1. Problem

PeerPedia submission page looks like a generic CMS form. No academic identity. Visitors can't tell this is for scholarly writing. Adding a self-assessment step to submission gives the form academic character and provides a baseline for community review comparison.

## 2. The Five Dimensions

Instead of a categorical `note_type`, five 1-5 rating dimensions define the "shape" of content. Default is 0 (not self-rated).

### 🧠 原创性 (Originality)

| ★ | Label | Description |
|---|-------|-------------|
| 1 | 搬运/翻译 | Mirrored or translated from existing source |
| 2 | 学习笔记 | Personal study notes based on existing materials |
| 3 | 随笔习作 | Informal essay, exercise solutions |
| 4 | 综述评论 | Survey, review, or commentary |
| 5 | 原创研究 | Original research contribution |

### 📐 严格性 (Rigor)

| ★ | Label | Description |
|---|-------|-------------|
| 1 | 非正式讨论 | Informal discussion, brainstorming |
| 2 | 直觉科普 | Intuitive/popular science explanation |
| 3 | 标准推导 | Standard derivations and reasoning |
| 4 | 严格证明 | Full mathematical rigor with proofs |
| 5 | 公理形式 | Axiomatic/formal treatment |

### 🧩 完整性 (Completeness)

| ★ | Label | Description |
|---|-------|-------------|
| 1 | 草稿片段 | Fragments, rough draft |
| 2 | 部分覆盖 | Partial coverage of topic |
| 3 | 核心完整 | Core content complete |
| 4 | 全面覆盖 | Comprehensive coverage |
| 5 | 详尽完备 | Exhaustive, including edge cases |

### 📖 教学性 (Pedagogy)

| ★ | Label | Description |
|---|-------|-------------|
| 1 | 个人备忘 | Personal notes, useful only to author |
| 2 | 需领域基础 | Requires field-specific background |
| 3 | 有基础可读 | Readable with basic prerequisites |
| 4 | 教学导向 | Clear pedagogical structure |
| 5 | 零基础入门 | Self-contained, no prerequisites |

### 💡 影响力 (Impact)

| ★ | Label | Description |
|---|-------|-------------|
| 1 | 个人参考 | Personal reference only |
| 2 | 小众专题 | Niche topic, few people care |
| 3 | 领域相关 | Relevant to the field |
| 4 | 领域核心 | Cannot understand the field without this |
| 5 | 奠基/开创 | Foundational, opens new directions |

Note: Impact self-ratings are subjective. Future versions pair these with objective data (citation count, fork count).

## 3. Data Model

### Article table — 5 new columns + 1 future-use column

```sql
ALTER TABLE articles ADD COLUMN self_originality INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN self_rigor INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN self_completeness INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN self_pedagogy INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN self_impact INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN forked_from TEXT;  -- nullable, future use
```

### Remove

- `note_type` — not added. The five dimensions replace it.

### ORM model (models.py)

```python
class Article(Base):
    # ... existing fields ...
    self_originality = Column(Integer, nullable=False, default=0)
    self_rigor = Column(Integer, nullable=False, default=0)
    self_completeness = Column(Integer, nullable=False, default=0)
    self_pedagogy = Column(Integer, nullable=False, default=0)
    self_impact = Column(Integer, nullable=False, default=0)
    forked_from = Column(String(36), nullable=True)
```

### to_dict()

Add all 6 new fields to `Article.to_dict()`.

## 4. API Changes

### POST /api/v1/articles (submit)

Add 5 optional form fields:
- `self_originality` (int, default 0)
- `self_rigor` (int, default 0)
- `self_completeness` (int, default 0)
- `self_pedagogy` (int, default 0)
- `self_impact` (int, default 0)

### submit_article() orchestrator

Accept and pass through the 5 self-rating fields to `create_article()`.

## 5. UI Changes

### Submit page (submit.html)

Add a self-assessment section before the abstract field:

```html
<div class="self-review">
  <h3>📊 自评 <span>帮助读者了解这篇内容的完成度和定位</span></h3>
  <!-- Five star-rating rows, one per dimension -->
  <!-- Each star clickable, hover shows label -->
</div>
```

Star rating interaction: 5 clickable stars per dimension. Hover shows the label for that level (e.g., hover ★★★ shows "标准推导"). Click sets the value. Visual feedback: filled stars = selected level, empty stars = unselected.

### Article page (article.html)

Below article meta, show self-rating bar:

```
┌──────────────────────────────────────────┐
│ 原创性 ★★★★☆ 4  严格性 ★★★★★ 5            │
│ 完整性 ★★★☆☆ 3  教学性 ★★★★☆ 4  影响力 ★★☆☆☆ 2 │
│                      (作者自评)            │
└──────────────────────────────────────────┘
```

All-zero case: show "作者未自评" in muted text.

Placeholder area for future community review scores: show "社区审稿后此处显示评分对比" when no reviews exist.

## 6. Existing Data Migration

All existing articles get `self_* = 0` and `forked_from = NULL`. No backfill needed. Demo articles in `demo_review.py` can optionally set meaningful self-ratings.

## 7. Test Plan

### test_submit.py — 2 tests
- Submit article with all 5 self-ratings set → verify stored in DB
- Submit article without self-ratings → verify defaults to 0

### test_api_routes.py — 1 test
- POST /api/v1/articles with self-rating fields → verify response includes them

### test_web_pages.py — 2 tests
- Article page renders self-ratings when set
- Article page shows "未自评" when all zero

## 8. Out of Scope

- Community review dimensions (future: reviewer also rates same 5 dimensions)
- Self vs community comparison UI
- Fork button and fork workflow
- `forked_from` resolution logic
- Impact objective data (citation/fork counts)

## 9. Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 54 | 5 self-review dimensions | Originality, rigor, completeness, pedagogy, impact cover both type and quality |
| 55 | No categorical `note_type` | Vector of 5 dimensions defines content shape more precisely than a single enum |
| 56 | Default 0 = not self-rated | Optional but visible — unrated articles show "未自评" badge |
| 57 | `forked_from` field added now | Schema ready for future fork feature; costs nothing to add column early |
| 58 | Impact dimension pairs with objective data later | Self-rated impact is annotated as subjective; citation/fork counts provide ground truth |
