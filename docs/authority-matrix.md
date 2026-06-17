# 权限矩阵 / Authority Matrix

> 生效版本: `phase-1a-policy-foundation` (2026-06-17)  
> 策略来源: `core/peerpedia_core/policies/articles.py`

PeerPedia 有三层文章可见性：**draft**（草稿）→ **sedimentation**（沉淀池）→ **published**（已发布）。
权限在所有三层上检查；写操作始终是仅限作者的。

## 文章状态（Article Statuses）

| 状态 | 含义 | 可见性 |
|------|------|--------|
| `draft` | 作者编辑中的草稿 | 仅作者（+ 认证用户可通过作者筛选查看自己的） |
| `sedimentation` | 在沉淀池中等待社区评审 | 所有人（含未认证） |
| `published` | 已通过沉淀池，存档 | 所有人（含未认证） |

## 操作权限矩阵

行 = 操作，列 = 调用者身份。✅ = 允许，❌ = 拒绝。

### 读操作

| 操作 | 路由 | 匿名 | 认证（非作者） | 作者 |
|------|------|------|---------------|------|
| 查看文章详情 | `GET /articles/{id}` | ✅ 仅 sedimentation/published | ✅ 同上 | ✅ 含 draft |
| 列出文章 | `GET /articles` | ✅ 仅 sedimentation/published | ✅ 含自己 draft | ✅ 含自己 draft |
| 查看文章源码 | `GET /articles/{id}/source` | ✅ 同上 | ✅ 同上 | ✅ 含 draft |
| 下载源码文件 | `GET /articles/{id}/download/source` | ✅ 同上 | ✅ 同上 | ✅ 含 draft |
| 下载编译 PDF | `GET /articles/{id}/download/pdf` | ✅ 同上 | ✅ 同上 | ✅ 含 draft |
| 下载完整 git 仓库 | `GET /articles/{id}/download/repo` | ✅ 仅 published | ✅ 仅 published | ✅ 含 draft/sedimentation |
| 查看文章 diff | `GET /articles/{id}/diff/{a}/{b}` | ✅ 同上 | ✅ 同上 | ✅ 含 draft |
| 查看文章历史 | `GET /articles/{id}/history` | ✅ 同上 | ✅ 同上 | ✅ 含 draft |
| 查看 HEAD | `GET /articles/{id}/head` | ✅ 同上 | ✅ 同上 | ✅ 含 draft |

### 写操作

| 操作 | 路由 | 匿名 | 认证（非作者） | 作者 |
|------|------|------|---------------|------|
| 创建文章 | `POST /articles` | ❌ | ✅ | ✅ |
| 编辑文章 | `PUT /articles/{id}` | ❌ | ❌ | ✅ |
| 删除文章 | `DELETE /articles/{id}` | ❌ | ❌ | ✅ |
| 回滚到历史提交 | `POST /articles/{id}/rollback/{hash}` | ❌ | ❌ | ✅ |
| 延长沉淀期 | `PUT /articles/{id}/sink-extension` | ❌ | ❌ | ✅ |
| 同步 (bundle) | `POST /articles/{id}/sync` | ❌ | ❌ | ✅ |

### 生命周期操作

| 操作 | 路由 | 匿名 | 认证（非作者） | 作者 | 额外条件 |
|------|------|------|---------------|------|----------|
| 发布到沉淀池 | `POST /articles/{id}/publish` | ❌ | ❌ | ✅ | HEAD commit 必须有 pool-scoped 自审记录 |
| 分叉文章 | `POST /articles/{id}/fork` | ❌ | ❌ | ✅（状态 = published） | 不能重复分叉同一篇文章 |

## 状态常量

```python
# 规则定义于 core/peerpedia_core/policies/articles.py

PUBLIC_READABLE_STATUSES   = {"sedimentation", "published"}   # 匿名可见
FORKABLE_STATUSES          = {"published"}                    # 可分叉
REPO_DOWNLOADABLE_STATUSES = {"published"}                    # git repo 可下载
```

## 异常映射

所有权限检查抛出 `peerpedia_core.exceptions` 中的语义异常：

| 异常 | HTTP 状态码 | 含义 |
|------|------------|------|
| `NotFoundError` | 404 | 文章不存在 |
| `NotAuthorizedError` | 403 | 用户无此操作权限 |
| `ConflictError` | 409 | 操作冲突（如重复分叉） |
| `BadRequestError` | 400 | 输入无效（如缺少自审） |

映射集中在 `backend/peerpedia_api/main.py` 的 `peerpedia_error_handler` 中，使用 `isinstance` 链确保子类正确继承父类的状态码。

## 设计原则

1. **Core 层无 HTTP 概念** — 异常名描述"什么错了"，不描述"HTTP 返回什么"
2. **默认拒绝** — 不匹配任何允许规则的访问一律拒绝
3. **每个路由调用对应的 assert_can_* 函数** — 不重复 `current_user.id in get_author_ids(...)` 检查
4. **沉淀池文章不可分叉** — 下载完整 git 仓库被视为等价于 fork，也受相同限制
