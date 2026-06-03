# Monaco 编辑器迁移 — 设计文档

> 日期: 2026-06-04
> 目标: 将在线编辑器的 CodeMirror 替换为 Monaco Editor，获得 VS Code 级 Markdown 编辑体验
> 参考: VS Code Markdown 扩展（MIT）、Monaco Editor（MIT）

## 动机

当前编辑器使用 CodeMirror，功能基础：
- Markdown 语法高亮 ✅
- `$$` 公式自动闭合 ✅（自定义 Enter 逻辑）
- 基础缩进 ✅

缺少的功能：
- 自动补全（括号、`**`、链接等）❌
- 智能缩进（列表续行、引用续行）❌
- 语法分色渲染（标题/加粗/代码不同颜色）❌
- 快捷键（Ctrl+B/I/K 等）❌
- 同步滚动 ❌

用户表示 VS Code 的 Markdown 编辑体验是最好的。Monaco Editor 是 VS Code 的内核，开源 MIT 协议，可以放心使用。

## 方案

**方案 A + 引用补全**（已确认）：
1. Monaco 内建 Markdown 能力全部打开 → 自动获得 VS Code 级体验
2. 只写一个自定义补全：`peerpedia:` 引用补全
3. 同步滚动、快捷键、主题切换 → 少量 JS 配置
4. 本地托管精简版 Monaco（~1.8MB）

## 架构

```
edit.html (重写，单文件 ~400 行)
├── Monaco Editor (左侧 50%)
│   ├── Markdown tokenizer (内建分色渲染)
│   ├── autoClosingPairs ($$, **, *, (), [], {})
│   ├── CompletionItemProvider (wordBased + peerpedia:)
│   ├── addAction (Ctrl+B/I/K/`/1)
│   └── onDidScrollChange → 同步滚动
├── 预览面板 (右侧 50%)
│   ├── marked.js + KaTeX 实时渲染
│   └── 同步滚动响应
├── 浮动工具栏 (顶部)
│   ├── 格式切换 (Markdown/Typst)
│   ├── 主题切换 (vs/vs-dark)
│   ├── 元数据展开/折叠
│   └── 提交按钮
└── 元数据面板 (底部折叠)
    ├── 标题/摘要/分类/关键词/语言
    └── 五维自评星星
```

无导航栏，全屏沉浸式布局。

## 详细设计

### 1. 页面布局

```
┌─────────────────────────────────────────────────────────┐
│  [Markdown ▼]  [☀️ 主题]  [📋 元数据]  [🚀 提交]       │
├──────────────────────────┬──────────────────────────────┤
│                          │                              │
│     Monaco Editor        │     实时预览                  │
│     (Markdown 语法高亮)   │     (KaTeX 渲染)             │
│                          │                              │
│     • 自动补全            │                              │
│     • 智能缩进            │                              │
│     • 颜色渲染            │                              │
│                          │                              │
├──────────────────────────┴──────────────────────────────┤
│  [元数据面板 — 默认收起，点击 📋 展开]                    │
│  标题 / 摘要 / 分类 / 关键词 / 语言 / 五维自评            │
└─────────────────────────────────────────────────────────┘
```

- **无导航栏** — 顶部只有一行透明浮动工具栏
- **编辑/预览 50:50** — 等比分割，随窗口自适应
- **元数据折叠** — 默认隐藏，写作时零干扰
- **全屏高度** — 编辑器 `calc(100vh - 40px)`

### 2. Monaco 编辑器配置

```javascript
monaco.editor.create(container, {
    language: 'markdown',
    theme: currentTheme,                // 'vs' | 'vs-dark'
    fontSize: 16,
    lineHeight: 26,
    fontFamily: "'Source Han Sans SC', 'PingFang SC', monospace",
    lineNumbers: 'on',
    wordWrap: 'on',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    // 自动补全 & 闭合
    autoClosingBrackets: 'always',
    autoClosingQuotes: 'always',
    autoClosingOvertype: 'always',
    autoClosingPairs: [
        { open: '$$', close: '$$' },
        { open: '**', close: '**' },
    ],
    autoSurround: 'quotes',
    wordBasedSuggestions: 'currentDocument',
    quickSuggestions: true,
    suggestOnTriggerCharacters: true,
    // 格式 & 缩进
    tabSize: 2,
    insertSpaces: true,
    detectIndentation: false,
    formatOnPaste: true,
    // 渲染
    matchBrackets: 'always',
    bracketPairColorization: { enabled: true },
    renderWhitespace: 'selection',
    wrappingIndent: 'same',
})
```

### 3. Markdown 颜色渲染（Monaco 内建 tokenizer）

| 语法 | 渲染效果 |
|---|---|
| `# 标题` | 蓝色加粗 |
| `**加粗**` | 黑色粗体 |
| `*斜体*` | 灰色斜体 |
| `` `代码` `` | 红色背景 |
| `[链接](url)` | 蓝色下划线 |
| `> 引用` | 绿色半透明背景 |
| `---` 分割线 | 灰色 |

全部是 Monaco Markdown 模式内建，不需要自定义 tokenizer。

### 4. 自动补全

#### 内建补全（Monaco 自带）

| 触发 | 行为 |
|---|---|
| `` ` `` | 自动闭合，再按一次跳过 |
| `(` `[` `{` | 自动补右括号 |
| `**` | 输入第二个 `*` 自动补 `**▌**` |
| `$$` | 输入第二个 `$` 自动补 `$$▌$$` |
| `*word*` | 选中文字后按 `*` 自动包裹 |
| `- ` 换行 | 自动续 `- ` |
| `1. ` 换行 | 自动递增 `2. ` `3. ` |
| `> ` 换行 | 自动续引用 `> ` |
| 空行 | 打断列表/引用续行 |

#### 自定义补全：peerpedia: 引用

输入 `peerpedia:` 触发文章搜索补全：

```
peerpedia:▌
    ↓ 弹出悬浮列表
┌─────────────────────────────────────┐
│ peerpedia:c9191d58  Tensor Network.. │
│ peerpedia:abc123    Quantum Error..  │
└─────────────────────────────────────┘
    ↓ 选中
[Quantum Error Correction](peerpedia:abc123)
```

实现：

```javascript
monaco.languages.registerCompletionItemProvider('markdown', {
    triggerCharacters: [':'],
    provideCompletionItems: function(model, position) {
        var line = model.getLineContent(position.lineNumber);
        var prefix = line.substring(0, position.column);
        var match = prefix.match(/peerpedia:(\w*)$/);
        if (!match) return { suggestions: [] };
        // fetch /api/v1/search?q=match[1] → 构建 CompletionList
    }
});
```

### 5. 快捷键映射

| 快捷键 | 动作 | 行为 |
|---|---|---|
| Ctrl+B | 加粗 | 选中包裹 `**text**`，无选中插入 `**▌**` |
| Ctrl+I | 斜体 | 同上 `*text*` |
| Ctrl+K | 链接 | 包裹 `[text](url)` |
| Ctrl+Shift+X | 删除线 | `~~text~~` |
| Ctrl+` | 行内代码 | `` `code` `` |
| Ctrl+1 | 标题 | 当前行变 `# 标题` |
| Tab / Shift-Tab | 缩进/反缩进 | Monaco 自带 |

实现方式：`editor.addAction({ id, keybindings, run })`。

### 6. 同步滚动

双向同步，防抖 50ms：

```javascript
var syncing = false;
editor.onDidScrollChange(function(e) {
    if (syncing) return;
    syncing = true;
    var ratio = e.scrollTop / (editor.getScrollHeight() - editor.getLayoutInfo().height);
    previewPane.scrollTop = ratio * (previewPane.scrollHeight - previewPane.clientHeight);
    setTimeout(function() { syncing = false; }, 50);
});

previewPane.addEventListener('scroll', function() {
    if (syncing) return;
    syncing = true;
    var ratio = previewPane.scrollTop / (previewPane.scrollHeight - previewPane.clientHeight);
    editor.setScrollTop(ratio * (editor.getScrollHeight() - editor.getLayoutInfo().height));
    setTimeout(function() { syncing = false; }, 50);
});
```

### 7. 主题切换

```javascript
function toggleTheme() {
    currentTheme = currentTheme === 'vs' ? 'vs-dark' : 'vs';
    monaco.editor.setTheme(currentTheme);
    // 同步更新页面 body class 为后续全局日/夜模式做准备
    document.body.className = currentTheme === 'vs-dark' ? 'dark' : '';
}
```

工具栏按钮图标随主题切换 ☀️/🌙。

### 8. 保留功能

以下功能从当前 edit.html 原样保留，不做改动：

- 格式切换（Markdown/Typst），Typst 路径保持 plaintext 语言
- 元数据表单（标题/摘要/分类/关键词/语言/中文摘要）
- 五维自评星星评分（交互逻辑不变）
- 提交流程（POST /api/v1/articles multipart）
- viewer cookie 身份

### 9. Monaco 本地托管

#### 精简打包

Monaco npm 包 + webpack/MonacoEditorWebpackPlugin，只引入：

- `editor/edcore.main.js` — 核心编辑器
- `basic-languages/markdown/markdown.js` — Markdown 语法
- `basic-languages/css/css.js` — CSS 语法

目标体积 ~1.8MB，放 `/static/monaco/`。

#### 开发阶段

先用 CDN 快速迭代：

```html
<script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.min.js"></script>
```

功能验证通过后再做本地打包。

## 文件变更

| 文件 | 操作 | 说明 |
|---|---|---|
| `peerpedia/web/templates/edit.html` | 重写 | CodeMirror → Monaco，全屏沉浸布局 |
| `peerpedia/web/static/monaco/` | 新增 | 精简版 Monaco 静态文件 |
| `peerpedia/web/routes/pages.py` | 不改 | /edit 路由不变 |
| `peerpedia/web/routes/api_search.py` | 不改 | 引用补全复用现有 /search 端点 |

## 不做的事

- 不新增后端 API
- 不改变文章提交和编译管线
- 不改变 CodeMirror 的 submit.html（文件上传提交保持不变）
- 不做 Typst 的自动补全和语法高亮（Monaco 内建不支持 Typst，先用 plaintext）
- 不做全局日/夜模式（仅编辑器主题切换）

## 测试计划

1. **编辑器加载** — `GET /edit` 200，包含 Monaco 实例
2. **Markdown 补全** — 输入 `**` 自动补 `**▌**`
3. **`$$` 闭合** — 输入 `$$` 自动补 `$$▌$$`
4. **列表续行** — `- aaa` 回车自动续 `- ▌`
5. **快捷键** — Ctrl+B 包裹加粗
6. **主题切换** — 按钮切换 `vs` ↔ `vs-dark`
7. **预览渲染** — 编辑 `# Hello` → 右侧显示 h1
8. **同步滚动** — 编辑区滚动 → 预览区同步
9. **引用补全** — 输入 `peerpedia:` 弹出候选列表
10. **提交** — POST /api/v1/articles → 返回 article_id
11. **编辑已有** — GET /edit/{id} → 编辑器填充源码
12. **回归** — 现有 27 个测试文件全部通过
