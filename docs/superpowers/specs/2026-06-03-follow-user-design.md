# Follow User — Design Spec

> 日期: 2026-06-03
> 状态: 设计完成，待用户审核
> 依赖: Phase 3 全部完成（196 tests），User 表已存在

---

## 1. Overview

用户关注功能：读者可以关注感兴趣的作者，在首页「关注动态」tab 按时间线查看关注作者的新文章和版本更新。

---

## 2. Data Model

### 2.1 Follow ORM

```python
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

复合主键 `(follower_id, followed_id)`，天然保证同一对关系唯一。

### 2.2 CRUD

```python
def follow_user(session, *, follower_id, followed_id) -> Follow
def unfollow_user(session, *, follower_id, followed_id) -> bool  # True if deleted
def is_following(session, follower_id, followed_id) -> bool
def get_following(session, user_id) -> list[Follow]     # 关注了谁
def get_followers(session, user_id) -> list[Follow]     # 谁关注我
def get_following_count(session, user_id) -> int
def get_follower_count(session, user_id) -> int
```

---

## 3. API

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/users/{user_id}/follow` | 关注。body: `follower_id` |
| `DELETE` | `/api/v1/users/{user_id}/follow` | 取关。body: `follower_id` |
| `GET` | `/api/v1/users/{user_id}/following` | 返回 `{users: [...], total: N}` |
| `GET` | `/api/v1/users/{user_id}/followers` | 返回 `{users: [...], total: N}` |
| `GET` | `/api/v1/following/feed?user_id=X` | 关注动态 |

### 3.1 关注动态 feed

返回混合时间线，按时间倒序，近 30 天：

```json
{
    "user_id": "alice",
    "events": [
        {
            "type": "new_article",
            "user_id": "bob",
            "user_name": "Bob",
            "article_id": "a1b2c3",
            "article_title": "Quantum Error Correction",
            "time": "2026-06-03T10:30:00Z"
        },
        {
            "type": "new_version",
            "user_id": "charlie",
            "user_name": "Charlie",
            "article_id": "d4e5f6",
            "article_title": "Holographic Duality",
            "version": "v2.1",
            "time": "2026-06-02T15:00:00Z"
        }
    ]
}
```

事件类型：
- `new_article`: 关注作者提交了新文章（`Article.created_at` 在近 30 天）
- `new_version`: 关注作者的文章版本号递增（`Article.version` 改变且 `updated_at` 在近 30 天；用 `version > "v0.1"` 过滤掉初始版本）

---

## 4. UI

### 4.1 用户主页 `/user/{user_id}`

名字旁边加关注按钮：

```html
{% if is_self %}
  <!-- 自己的主页，不显示关注按钮 -->
{% elif is_following %}
  <button hx-delete="/api/v1/users/{{ user_id }}/follow"
          hx-vals='{"follower_id": "{{ current_user }}"}'
          hx-swap="outerHTML">已关注</button>
{% else %}
  <button hx-post="/api/v1/users/{{ user_id }}/follow"
          hx-vals='{"follower_id": "{{ current_user }}"}'
          hx-swap="outerHTML">+ 关注</button>
{% endif %}
```

名字下方显示粉丝/关注数：

```
粉丝 12  ·  关注了 5
```

点击数字 HTMX 懒加载展开列表。

### 4.2 首页 `/`

在文章列表上方增加 tab 切换：

```html
<nav class="tabs">
  <a href="/" class="{{ 'active' if tab == 'all' }}">全部文章</a>
  <a href="/?tab=following&user=alice" class="{{ 'active' if tab == 'following' }}">关注动态</a>
</nav>
```

`tab=following` 时调用 feed API 渲染事件列表，每条渲染为可点击跳转的卡片。

### 4.3 关注/取关交互

全部走 HTMX，无需刷新：
- 点击「+ 关注」→ POST → 按钮变「已关注」
- 点击「已关注」→ DELETE → 按钮变「+ 关注」

---

## 5. 文件变更

### 新建文件

无。全部在已有文件中扩展。

### 修改文件

| 文件 | 变更 |
|------|------|
| `peerpedia_core/storage/db/models.py` | 新增 Follow ORM |
| `peerpedia_core/storage/db/crud.py` | 新增 7 个 follow CRUD 函数 |
| `peerpedia_core/storage/db/__init__.py` | 导出 Follow + CRUD |
| `peerpedia/web/routes/api_users.py` | 新增 4 个 follow API 端点 |
| `peerpedia/web/routes/pages.py` | user 页面加 `is_following` 上下文；首页加 `tab` 参数 |
| `peerpedia/web/templates/user.html` | 关注按钮 + 粉丝/关注数 |
| `peerpedia/web/templates/index.html` | tab 切换 + 关注动态列表 |
| `tests/test_follow.py` | ~12 新测试 |

### 不改的文件

- citations.py, lan.py, collaboration.py, review.py, compiler.py 等全部不动

---

## 6. 测试计划

### test_follow.py（~12 tests）

**DB 层（5 tests）：**
- follow_user 创建关系
- unfollow_user 删除关系
- 重复 follow 报错（复合主键约束）
- get_following / get_followers 返回正确列表
- is_following 正确判断

**API 层（5 tests）：**
- POST follow 成功
- DELETE unfollow 成功
- GET following 返回列表
- GET followers 返回列表
- GET feed 返回混合事件

**边界（2 tests）：**
- 取关不存在的用户返回 404
- 关注不存在的用户返回 404

### 回归

- 预计 196 + 12 = ~208 tests

---

## 7. 架构约束

- 不引入新模块文件 — 全部在已有文件中扩展
- 关注关系存储在本地 SQLite，暂不做 LAN 同步（未来可加入 catalog.md）
- HTMX 驱动交互，零 JavaScript 手写
- Follow 按钮状态跟随 HTMX swap，无需页面刷新

---

## 8. 决策记录

| # | 决策 | 结论 |
|---|---|---|
| 50 | Follow 数据模型 | 复合主键 (follower_id, followed_id)，单表 |
| 51 | 关注动态范围 | 近 30 天，类型：new_article + new_version |
| 52 | UI 交互方式 | HTMX 按钮 swap，无需 JS |
| 53 | LAN 同步 | MVP 不同步关注关系（本地行为） |
