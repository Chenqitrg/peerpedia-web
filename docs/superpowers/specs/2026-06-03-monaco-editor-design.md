# Monaco 在线编辑器 — 设计文档

> 目标：让数学家在浏览器里流畅地写作和预览 Markdown/Typst 文章。

## 架构

```
┌──────────────────┬──────────────────────────┐
│   Monaco 编辑器   │     实时预览              │
│                  │                          │
│   (Markdown /    │   Markdown: KaTeX 即时    │
│    Typst 语法     │   Typst: PDF.js 内嵌      │
│    高亮)         │                          │
│                  │                          │
├──────────────────┴──────────────────────────┤
│  标题 / 摘要 / 分类 / 关键词 / 五维自评        │
├─────────────────────────────────────────────┤
│  [保存草稿]  [提交沉淀池]                      │
└─────────────────────────────────────────────┘
```

## 编译路径

| 格式 | 预览引擎 | 延迟 | 说明 |
|------|---------|------|------|
| Markdown | 浏览器 KaTeX | 0ms 即时 | Monaco 内容 → Markdown → KaTeX 渲染 HTML |
| Typst | 服务端 typst compile + PDF.js | 500ms 防抖 | POST 源码 → 临时 PDF → PDF.js 嵌入 |

### Markdown 路径

```
Monaco onChange → 提取文本 → 前端 Markdown 解析 → KaTeX 渲染 → 右侧 HTML
```

完全在浏览器完成，无需服务端。复用 `compiler.py` 的 `_protect_math` / `_restore_math` 逻辑做前端版本。

### Typst 路径

```
Monaco onChange → 防抖 500ms → POST /api/v1/compile/preview {source, format:"typst"}
→ 服务端 typst compile → 临时 *.pdf → 返回 {pdf_url}
→ PDF.js viewer 刷新
```

临时 PDF 保存在服务端文件系统，按 session 隔离，超时清理。

## 路由

| 路由 | 说明 |
|------|------|
| `GET /edit` | 新建文章（空白编辑器） |
| `GET /edit/{article_id}` | 编辑已有文章（加载源码填充编辑器） |
| `POST /api/v1/compile/preview` | 编译预览（Typst → 临时 PDF） |

## 技术选型

| 组件 | 方案 |
|------|------|
| 编辑器 | Monaco Editor（CDN 加载，minimal VS Code 体验） |
| PDF 预览 | PDF.js（CDN 加载） |
| Markdown 渲染 | 前端 JS，复用 compiler.py 的 protect/restore 逻辑 |
| KaTeX | 已有 CDN（`/static/katex/`） |
| Typst 编译 | 服务端 `typst compile`（已有 `api_compile.py` 基础） |
| 防抖 | 前端 500ms debounce |

## 元数据面板

编辑器下方折叠面板，字段对齐现有 `submit_article` 流程：

- 标题（必填）
- 摘要
- 中文摘要（可选）
- 分类（逗号分隔）
- 关键词（逗号分隔）
- 语言（en / zh）
- 五维自评（1-5 星，可选）

## 提交流程

1. 点击「提交沉淀池」→ 元数据 + 编辑器内容打包 POST `/api/v1/articles`
2. 复用现有 `submit_article` 流程：生成 UUID → git init → commit → DB → CID
3. 成功后跳转到文章页

## 不做的事

- 不新建编辑器专用的编译管线 — 复用现有 `compiler.py` 和 `api_compile.py`
- 不新建文章模型 — 复用现有 `Article` ORM
- 不改变现有文件上传提交方式 — 新编辑器是新增入口，不是替代
- 不做 Typst WASM 编译 — 等上游
- 不做 bTeX/Instiki 适配 — 搁置

## 文件结构

```
peerpedia/web/
├── routes/
│   ├── pages.py            ← 添加 GET /edit, GET /edit/{id}
│   └── api_articles.py     ← 添加 POST /api/v1/compile/preview
├── templates/
│   └── edit.html           ← 新建，Monaco 编辑器页面
└── static/
    └── monaco/             ← Monaco 静态资源（可 CDN 替代）
```

## 测试计划

- 编辑器加载：页面渲染 Monaco Editor 实例
- Markdown 预览：输入 `# Hello $x^2$` → 右侧渲染标题 + KaTeX
- Typst 预览：输入 `= Hello` → POST 编译 → PDF.js 显示
- 提交草稿：POST /api/v1/articles → 返回 article_id
- 编辑已有文章：GET /edit/{id} → Monaco 填充源码
